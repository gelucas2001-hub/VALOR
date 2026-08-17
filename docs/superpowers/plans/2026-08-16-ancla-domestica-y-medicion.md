# Ancla doméstica y medición contra el mercado — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir el sesgo medido de +12.3pp hacia el local en Libertadores anclando la fuerza de cada equipo a su liga local, y empezar a registrar pronósticos contra la línea del mercado para poder medir si le ganamos.

**Architecture:** Hoy `fuerzas_equipos()` ajusta ataque/defensa usando solo partidos de la misma competición, y regulariza a los equipos con poca muestra hacia 1.0 (el promedio de esa competición). En copas eso significa 6 partidos por equipo, y el resultado es que el modelo cree que todos los equipos son parecidos — la localía termina decidiendo. La corrección: usar la fuerza del equipo **en su liga local** (donde tiene ~23 partidos) como el valor hacia el que empuja la regularización, en vez de 1.0. Es un cambio quirúrgico sobre la función que ya existe, no un motor nuevo.

En paralelo, y primero, se construye el registro de pronósticos: cada corrida del cron guarda qué dijimos nosotros y qué decía la línea, y resuelve los partidos ya terminados. Sin eso no hay forma de saber si el arreglo mejora algo ni de sostener la afirmación "estamos por encima del mercado".

**Tech Stack:** Python 3.12, biblioteca estándar únicamente (sin dependencias externas — el cron de GitHub Actions no instala nada). API pública de ESPN.

**Spec:** `docs/superpowers/specs/2026-08-16-rediseno-desde-cero-design.md` (revisión 3), sección "Correcciones al modelo (prioridad)".

## Global Constraints

- **Sin dependencias externas.** `actualizar.py` corre en GitHub Actions sin `pip install`. Solo biblioteca estándar. No agregar `requirements.txt`.
- **Sin claves de API.** Todo sale de endpoints públicos de ESPN.
- **No romper el contrato de `data/partidos.json`.** `index.html` lo lee tal cual; cualquier campo nuevo se agrega, ninguno existente cambia de nombre ni de tipo.
- **Presupuesto de pedidos.** El cron corre 2 veces por día. Todo lo que se consulte por equipo debe cachearse en disco si no cambia entre corridas.
- **Comentarios y mensajes de commit en español**, explicando el porqué, siguiendo el estilo del archivo.
- **Nunca hardcodear el resultado esperado de un test para que pase.** Si un número no da, se investiga.

## Hechos verificados contra la API (2026-08-16)

El spec ya fue corregido con todo esto; se repite acá porque el plan tiene que poder leerse solo.

- **`/teams/{id}/schedule` devuelve solo la competición consultada.** Palmeiras da 7 eventos bajo `conmebol.libertadores` y 23 bajo `bra.1`. Por eso hace falta consultar la liga local aparte.
- **`defaultLeague` de `/teams/{id}` revela la liga local.** Palmeiras→`bra.1`, Liga de Quito→`ecu.1`, Cerro Porteño→`par.1`, Independiente del Valle→`ecu.1`.
- **Hay cuotas de cierre históricas gratis** en `football-data.co.uk` para Liga Profesional (6.295 partidos desde 2012; 314/314 de la temporada actual). No cubre copas.
- **El cruce de nombres entre fuentes es peligroso si es difuso:** "Independiente Rivadavia" matchea con "Independiente" por substring. La tabla va explícita.
- **ESPN no tiene lesiones del fútbol argentino** (endpoint responde vacío) ni **xG por equipo** (solo por jugador destacado). Ambas cosas quedan fuera de alcance.

## Por qué ancla doméstica y no Elo literal

El video de referencia usa Elo, que resume la fuerza de un equipo en **un solo número**. El modelo de goles necesita **dos** (ataque y defensa) porque un 2-1 y un 1-0 informan cosas distintas sobre el mismo equipo. Convertir Elo→(ataque,defensa) requeriría un supuesto extra sin respaldo. Anclar a la fuerza doméstica conserva la separación, reusa la maquinaria existente, y ataca la misma causa raíz (falta de muestra dentro de la copa).

**Aproximación asumida:** la escala de goles sigue siendo la de la copa (`mu_local`/`mu_visita` de la propia competición); la liga local solo aporta el ataque/defensa **relativo**. Esto ignora que un 1.4 de ataque en Brasil vale más que un 1.4 en Paraguay. Calibrar factores de calidad por liga es un plan aparte, posterior a medir cuánto mejora este cambio solo.

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `actualizar.py` (modificar) | Suma `liga_domestica()`, `anclas_domesticas()`, y un parámetro `anclas` a `fuerzas_equipos()`. Escribe el registro de pronósticos. |
| `data/cache_ligas.json` (crear, generado) | `{team_id: "bra.1"}`. Persiste entre corridas: la liga de un equipo no cambia en la temporada. |
| `data/historial_pronosticos.json` (crear, generado) | Pronóstico nuestro + línea del mercado por partido, y su resolución. Crece con el tiempo. |
| `medir_sesgo.py` (crear) | Script suelto de medición: sesgo por competición contra la línea. Se corre a mano antes y después para probar que el arreglo funcionó. No es parte del cron. |

---

### Task 1: Script de medición del sesgo (la vara)

Se construye **primero** para poder demostrar que el cambio del modelo mejora algo. Sin esto, la Tarea 5 no tiene con qué comparar.

**Files:**
- Create: `medir_sesgo.py`

**Interfaces:**
- Consumes: `backtest.matriz`, `backtest.suma_si` (ya existen), `data/partidos.json`.
- Produces: función `sesgo_por_competicion(partidos) -> dict` con forma `{comp: {"n": int, "local": float, "empate": float, "visita": float, "magnitud": float}}`, donde los valores son puntos porcentuales medios de diferencia entre modelo y línea sin margen.

- [ ] **Step 1: Escribir el script con su propia verificación**

```python
"""Mide cuánto se aparta el modelo de la línea del mercado, por competición.

No es parte del cron. Se corre a mano antes y después de tocar el modelo
para comprobar que un cambio mejora de verdad y no de palabra:

    python medir_sesgo.py

Un sesgo positivo en "local" significa que el modelo le da más
probabilidad al local que el mercado. La línea se compara SIN margen
(devig proporcional): la cuota cruda implica probabilidades que suman
~1.077, y compararse contra eso haría ver ventaja donde solo hay comisión.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from backtest import matriz, suma_si

PARTIDOS = Path("data/partidos.json")


def probs_modelo(m):
    """(p_local, p_empate, p_visita) según Dixon-Coles para ese partido."""
    M = matriz(m["lh"], m["la"], m["rho"])
    return (suma_si(M, lambda i, j: i > j),
            suma_si(M, lambda i, j: i == j),
            suma_si(M, lambda i, j: i < j))


def probs_mercado(mk):
    """Igual, según la cuota de referencia, con el margen ya descontado."""
    crudas = [1 / mk["local"], 1 / mk["empate"], 1 / mk["visitante"]]
    total = sum(crudas)
    return tuple(x / total for x in crudas)


def sesgo_por_competicion(partidos):
    por_comp = {}
    for m in partidos:
        mk = m.get("mercado")
        if not mk or not mk.get("local"):
            continue
        pm = probs_modelo(m)
        pq = probs_mercado(mk)
        d = por_comp.setdefault(m["comp"], {"n": 0, "local": 0.0, "empate": 0.0,
                                            "visita": 0.0, "magnitud": 0.0})
        d["n"] += 1
        for k, i in (("local", 0), ("empate", 1), ("visita", 2)):
            d[k] += pm[i] - pq[i]
        d["magnitud"] += max(abs(pm[i] - pq[i]) for i in range(3))
    for d in por_comp.values():
        for k in ("local", "empate", "visita", "magnitud"):
            d[k] /= d["n"]
    return por_comp


def main():
    partidos = json.loads(PARTIDOS.read_text(encoding="utf-8"))
    if isinstance(partidos, dict):
        partidos = partidos.get("partidos", [])
    res = sesgo_por_competicion(partidos)
    print(f"{'competición':34} {'n':>3} {'local':>8} {'empate':>8} {'visita':>8} {'|dif|':>8}")
    for comp in sorted(res):
        d = res[comp]
        print(f"{comp:34} {d['n']:3} {d['local']*100:+7.1f}pp {d['empate']*100:+7.1f}pp "
              f"{d['visita']*100:+7.1f}pp {d['magnitud']*100:7.1f}pp")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correrlo y verificar que reproduce el sesgo ya medido**

Run: `python medir_sesgo.py`

Expected: la fila de CONMEBOL Libertadores muestra un sesgo en `local` de **+12.3pp** (±0.5pp de tolerancia por si el cron actualizó datos), y Liga Profesional muestra un valor negativo chico (alrededor de −2.3pp). Si Libertadores no da cerca de +12pp, **parar**: o los datos cambiaron mucho o el script tiene un error — investigar antes de seguir.

- [ ] **Step 3: Commit**

```bash
git add medir_sesgo.py
git commit -m "Script para medir el sesgo del modelo contra la línea del mercado

Se construye antes de tocar el modelo para tener con qué comparar. Mide
la diferencia media en puntos porcentuales contra la línea sin margen,
por competición. Hoy da +12.3pp hacia el local en Libertadores, que es
el problema que vamos a corregir."
```

---

### Task 2: Descubrir la liga local de cada equipo

**Files:**
- Modify: `actualizar.py` (agregar constante junto a `CACHE_DISCIPLINA` en la línea 33, y la función nueva después de `historial()`, que termina en la línea 226)

**Interfaces:**
- Consumes: `api(path)` (ya existe, línea 109).
- Produces: `liga_domestica(team_id, slug_consulta, cache) -> str | None` — devuelve el slug de la liga local (`"bra.1"`) o `None` si ESPN no lo informa. Muta `cache` in-place.

- [ ] **Step 1: Agregar la constante del cache**

En `actualizar.py`, justo debajo de la línea 33 (`CACHE_DISCIPLINA = ...`):

```python
CACHE_LIGAS = Path("data/cache_ligas.json")   # team_id -> slug de su liga
                                               # local ("bra.1"). Persiste entre
                                               # corridas: un equipo no cambia de
                                               # liga en mitad de la temporada.
```

- [ ] **Step 2: Agregar la función, después de `historial()`**

```python
def liga_domestica(team_id, slug_consulta, cache):
    """Slug de la liga local del equipo, vía el campo defaultLeague.

    Hace falta porque /teams/{id}/schedule bajo el slug de una copa
    devuelve SOLO los partidos de esa copa (verificado: Palmeiras da 7
    eventos bajo conmebol.libertadores y 23 bajo bra.1). Para saber
    cuánto vale un equipo necesitamos su liga, donde sí tiene muestra.

    Devuelve None si ESPN no informa defaultLeague; el llamador debe
    seguir andando sin ancla en ese caso.
    """
    clave = str(team_id)
    if clave in cache:
        return cache[clave]          # puede ser None cacheado: no reintentar
    slug = None
    try:
        d = api(f"{SITE_V2}/{slug_consulta}/teams/{team_id}")
        slug = ((d.get("team") or {}).get("defaultLeague") or {}).get("slug")
    except Exception:
        return None                  # error de red: NO cachear, reintentar luego
    cache[clave] = slug
    return slug
```

- [ ] **Step 3: Verificar contra la API real**

Run:

```bash
python -c "
import actualizar as A
c = {}
for tid, nom in [('2029','Palmeiras'),('4816','Liga de Quito'),('2671','Cerro Porteno'),('17','Rosario Central')]:
    print(nom, '->', A.liga_domestica(tid, 'conmebol.libertadores', c))
print('cache:', c)
"
```

Expected: `Palmeiras -> bra.1`, `Liga de Quito -> ecu.1`, `Cerro Porteno -> par.1`, `Rosario Central -> arg.1`, y el cache con las cuatro entradas.

- [ ] **Step 4: Verificar que el cache evita el segundo pedido**

Run:

```bash
python -c "
import actualizar as A
c = {}
A.liga_domestica('2029','conmebol.libertadores',c); n1 = A._req_count
A.liga_domestica('2029','conmebol.libertadores',c); n2 = A._req_count
print('pedidos antes/despues:', n1, n2)
assert n1 == n2, 'el cache no esta cortando el pedido'
print('OK')
"
```

Expected: los dos números iguales y `OK`.

- [ ] **Step 5: Commit**

(El spec ya fue corregido por separado en el commit `docs: corregir el spec con lo que la API dijo realmente` — no hace falta tocarlo acá.)

```bash
git add actualizar.py
git commit -m "Descubrir la liga local de cada equipo vía defaultLeague

/teams/{id}/schedule bajo el slug de una copa devuelve solo partidos de
esa copa — Palmeiras da 7 ahí y 23 en bra.1. Para anclar la fuerza de un
equipo necesitamos su liga local, y defaultLeague nos la dice. Se cachea
en disco porque no cambia entre corridas.

Corrige de paso una afirmación falsa del spec, que daba por hecho que el
calendario ya venía con todas las competiciones."
```

---

### Task 3: Calcular el ancla de fuerza en la liga local

**Files:**
- Modify: `actualizar.py` (función nueva después de `fuerzas_equipos()`, que termina en la línea 436)

**Interfaces:**
- Consumes: `liga_domestica()` (Tarea 2), `resultados_temporada()` (línea 345), `fuerzas_equipos()` (línea 383).
- Produces: `ancla_de(team_id, slug_consulta, season, hoy, cache_ligas, cache_dom) -> tuple[float, float] | None` — `(ataque, defensa)` del equipo en su liga local, o `None` si no hay liga conocida o muestra suficiente.

- [ ] **Step 1: Agregar la función**

```python
MIN_PARTIDOS_ANCLA = 8     # partidos en la liga local para que el ancla valga.
                            # Más exigente que MIN_PARTIDOS_FUERZA (3) porque el
                            # ancla se propaga a todos los partidos de copa de ese
                            # equipo: si está mal, contamina más.


def ancla_de(team_id, slug_consulta, season, hoy, cache_ligas, cache_dom):
    """(ataque, defensa) del equipo en SU liga local, o None.

    Es el valor hacia el que la regularización va a empujar a este equipo
    en la copa, en vez de empujarlo a 1.0 (el promedio de la copa). Un
    equipo con 6 partidos de Libertadores no tiene fuerza medible ahí,
    pero sí tiene 23 partidos en su liga.

    Devuelve None (y el llamador cae al comportamiento viejo) cuando no
    se conoce la liga, la liga no responde, o el equipo tiene menos de
    MIN_PARTIDOS_ANCLA partidos en ella.
    """
    slug_liga = liga_domestica(team_id, slug_consulta, cache_ligas)
    if not slug_liga or slug_liga == slug_consulta:
        return None            # ya lo estamos ajustando en esa misma competición

    if slug_liga not in cache_dom:
        try:
            print(f"  · fuerza doméstica — {slug_liga}")
            resultados = resultados_temporada(slug_liga, season, hoy)
            cache_dom[slug_liga] = fuerzas_equipos(resultados, hoy)
        except Exception:
            cache_dom[slug_liga] = ({}, 1.0, 1.0, {})   # liga que no responde
    fuerzas, _mu_l, _mu_v, pj = cache_dom[slug_liga]

    if pj.get(str(team_id), 0) < MIN_PARTIDOS_ANCLA:
        return None
    return fuerzas.get(str(team_id))
```

- [ ] **Step 2: Verificar con equipos reales de distinta liga**

Run:

```bash
python -c "
import datetime, actualizar as A
hoy = datetime.date.today(); cl, cd = {}, {}
for tid, nom in [('2029','Palmeiras'),('2671','Cerro Porteno'),('4816','Liga de Quito')]:
    a = A.ancla_de(tid, 'conmebol.libertadores', hoy.year, hoy, cl, cd)
    print(f'{nom:16}', 'sin ancla' if a is None else f'ataque {a[0]:.3f} defensa {a[1]:.3f}')
"
```

Expected: al menos Palmeiras devuelve un par de números (tiene 23 partidos en `bra.1`). Los valores deben caer en un rango sano — **entre 0.4 y 2.5 ambos**. Si alguno se va fuera de ese rango, parar e investigar: la regularización de `fuerzas_equipos` debería impedirlo, y un valor extremo indica un problema de datos.

- [ ] **Step 3: Verificar que un equipo de la misma competición no se ancla a sí mismo**

Run:

```bash
python -c "
import datetime, actualizar as A
hoy = datetime.date.today(); cl, cd = {}, {}
# Rosario Central juega arg.1; consultado DESDE arg.1 no debe anclarse
print('desde arg.1:', A.ancla_de('17','arg.1',hoy.year,hoy,cl,cd))
assert A.ancla_de('17','arg.1',hoy.year,hoy,cl,cd) is None
print('OK: no se ancla a si mismo')
"
```

Expected: `None` y `OK`. Sin este corte, ajustaríamos dos veces sobre los mismos partidos.

- [ ] **Step 4: Commit**

```bash
git add actualizar.py
git commit -m "Calcular la fuerza de cada equipo en su liga local

Reusa fuerzas_equipos() sobre la liga doméstica, donde un equipo tiene
~23 partidos en vez de los ~6 que tiene en la copa. Pide 8 partidos
mínimo porque este valor se propaga a todos los partidos de copa del
equipo. No ancla cuando la liga consultada es la misma que la local:
ahí ya estamos ajustando con esos partidos."
```

---

### Task 4: Usar el ancla como prior de la regularización

**Files:**
- Modify: `actualizar.py:383-436` (`fuerzas_equipos`), `actualizar.py:463-469` (el `get_fuerzas` dentro de `main()`)

**Interfaces:**
- Consumes: `ancla_de()` (Tarea 3).
- Produces: `fuerzas_equipos(resultados, hoy, anclas=None)` — mismo retorno de siempre `(fuerzas, mu_local, mu_visita, partidos_por_equipo)`. `anclas` es `{team_id: (ataque, defensa)}`; los equipos ausentes se regularizan a 1.0 como antes.

- [ ] **Step 1: Cambiar la firma y la docstring**

En `actualizar.py:383`, reemplazar la línea `def fuerzas_equipos(resultados, hoy):` por:

```python
def fuerzas_equipos(resultados, hoy, anclas=None):
```

Y agregar al final de la docstring existente (después de `...>1 ataque fuerte / <1 defensa débil."""`), antes del cuerpo:

```python
    """...(docstring existente)...

    anclas: {team_id: (ataque, defensa)} — hacia dónde empujan los
    PRIOR_FUERZA partidos fantasma. Sin ancla un equipo con poca muestra
    se va hacia 1.0 (el promedio de ESTA competición), que en copas es
    justamente el problema: hace ver parecidos a Palmeiras y a un equipo
    chico, y ahí la localía termina decidiendo el partido. Con ancla se
    va hacia lo que ese equipo vale en su liga local.
    """
```

- [ ] **Step 2: Usar el ancla en el prior**

En `fuerzas_equipos`, dentro del bucle `for _ in range(40):`, reemplazar la línea 415:

```python
        num_a = {t: PRIOR_FUERZA for t in equipos}; den_a = {t: PRIOR_FUERZA for t in equipos}
```

por:

```python
        # num = PRIOR * ancla y den = PRIOR: sin partidos reales la razón da
        # exactamente el ancla; con muestra grande el prior pesa poco. Sin
        # ancla, ancla=1.0 y queda idéntico al comportamiento anterior.
        anc = anclas or {}
        num_a = {t: PRIOR_FUERZA * anc.get(t, (1.0, 1.0))[0] for t in equipos}
        den_a = {t: PRIOR_FUERZA for t in equipos}
```

Y la línea 421:

```python
        num_d = {t: PRIOR_FUERZA for t in equipos}; den_d = {t: PRIOR_FUERZA for t in equipos}
```

por:

```python
        num_d = {t: PRIOR_FUERZA * anc.get(t, (1.0, 1.0))[1] for t in equipos}
        den_d = {t: PRIOR_FUERZA for t in equipos}
```

- [ ] **Step 3: Verificar que sin anclas el resultado no cambió**

Este es el test más importante de la tarea: el cambio no debe alterar nada cuando no hay anclas.

Run:

```bash
python -c "
import datetime, actualizar as A
hoy = datetime.date.today()
r = A.resultados_temporada('arg.1', hoy.year, hoy)
f1 = A.fuerzas_equipos(r, hoy)[0]
f2 = A.fuerzas_equipos(r, hoy, anclas={})[0]
f3 = A.fuerzas_equipos(r, hoy, anclas=None)[0]
assert f1 == f2 == f3, 'el default cambio el resultado'
print('OK: sin anclas da identico a antes,', len(f1), 'equipos')
"
```

Expected: `OK: sin anclas da identico a antes, N equipos`.

- [ ] **Step 4: Verificar que el ancla mueve el resultado en la dirección correcta**

Run:

```bash
python -c "
import datetime, actualizar as A
hoy = datetime.date.today()
r = A.resultados_temporada('conmebol.libertadores', hoy.year, hoy)
base = A.fuerzas_equipos(r, hoy)[0]
# forzamos un ancla de ataque alto para Palmeiras y vemos si sube
alto = A.fuerzas_equipos(r, hoy, anclas={'2029': (1.8, 0.7)})[0]
if '2029' in base:
    print('ataque base', round(base['2029'][0],3), '-> con ancla', round(alto['2029'][0],3))
    assert alto['2029'][0] > base['2029'][0], 'el ancla no subio el ataque'
    assert alto['2029'][1] < base['2029'][1], 'el ancla no bajo la defensa'
    print('OK: el ancla mueve ataque y defensa en la direccion pedida')
else:
    print('Palmeiras sin partidos en la muestra actual; probar con otro id de la tabla')
"
```

Expected: el ataque con ancla mayor que el base, la defensa menor, y `OK`.

- [ ] **Step 5: Conectar el ancla en `main()`**

En `main()`, reemplazar el bloque `get_fuerzas` (líneas 463-469) por:

```python
    cache_fuerzas = {}   # slug -> (fuerzas, mu_local, mu_visita, partidos_por_equipo)
    cache_dom = {}       # slug de liga local -> lo mismo, para las anclas
    cache_ligas = {}     # team_id -> slug de su liga local (persiste en disco)
    if CACHE_LIGAS.exists():
        try:
            cache_ligas = json.loads(CACHE_LIGAS.read_text(encoding="utf-8"))
        except Exception:
            cache_ligas = {}

    def get_fuerzas(slug):
        if slug not in cache_fuerzas:
            print(f"  · calibrando fuerzas de ataque/defensa — {slug}")
            resultados = resultados_temporada(slug, season, hoy)
            # Ancla: cada equipo se regulariza hacia lo que vale en su liga
            # local, no hacia el promedio de esta copa. En arg.1 no aplica
            # (la liga local ES esta competición) y ancla_de devuelve None.
            equipos = {p["home"] for p in resultados} | {p["away"] for p in resultados}
            anclas = {}
            for tid in equipos:
                a = ancla_de(tid, slug, season, hoy, cache_ligas, cache_dom)
                if a:
                    anclas[tid] = a
            if anclas:
                print(f"    ancladas {len(anclas)} de {len(equipos)} fuerzas a la liga local")
            cache_fuerzas[slug] = fuerzas_equipos(resultados, hoy, anclas=anclas)
        return cache_fuerzas[slug]
```

- [ ] **Step 6: Guardar el cache de ligas al final de `main()`**

Buscar donde `main()` guarda `CACHE_DISCIPLINA` y agregar al lado, con el mismo estilo:

```python
    CACHE_LIGAS.write_text(json.dumps(cache_ligas, ensure_ascii=False, indent=1),
                           encoding="utf-8")
```

- [ ] **Step 7: Correr el pipeline completo**

Run: `python actualizar.py`

Expected: termina sin error, imprime al menos una línea `ancladas N de M fuerzas a la liga local` para Libertadores y Sudamericana (y **ninguna** para arg.1), y `data/cache_ligas.json` queda creado con entradas.

- [ ] **Step 8: Commit**

```bash
git add actualizar.py data/cache_ligas.json data/partidos.json
git commit -m "Anclar la fuerza de copa a la liga local de cada equipo

En copas cada equipo tiene ~6 partidos, y la regularización lo empujaba
hacia 1.0 — el promedio de la copa. Resultado: el modelo veía parecidos
a Palmeiras y a cualquier equipo chico, y la localía terminaba decidiendo
(sesgo medido de +12.3pp hacia el local en Libertadores).

Ahora los partidos fantasma del prior empujan hacia lo que el equipo vale
en SU liga, donde tiene ~23 partidos. Sin ancla el cálculo queda idéntico
al anterior, así que arg.1 no se toca."
```

---

### Task 5: Medir que el arreglo funcionó

**Files:**
- Ninguno nuevo. Se corre `medir_sesgo.py` de la Tarea 1.

**IMPORTANTE — cómo NO medir esto.** El cron reescribe `data/partidos.json` dos veces por día, así que dos corridas separadas en el tiempo miden **partidos distintos**. Medido en la práctica el 2026-08-16: el mismo código dio +12.3pp por la mañana y +8.7pp después de una actualización del cron, sin haber tocado una línea. Comparar "antes" y "después" contra archivos distintos produciría una conclusión inventada.

La comparación tiene que ser **sobre el mismo archivo**, cambiando solo el código.

- [ ] **Step 1: Congelar un snapshot ANTES de tocar el modelo**

Hacerlo antes de empezar la Tarea 4 (o recuperar el de ese momento desde git):

```bash
cp data/partidos.json data/_snapshot_antes.json
python medir_sesgo.py data/_snapshot_antes.json
```

Anotar los cuatro números de la columna `local`. Ese es el "antes".

- [ ] **Step 2: Regenerar ese mismo conjunto de partidos con el modelo nuevo**

El snapshot tiene λ viejos, así que no alcanza con volver a medirlo — hay que recalcular las λ de **esos mismos partidos** con el ancla puesta. La forma más simple y honesta: correr `python actualizar.py` y quedarse solo con los partidos que están en las dos versiones, comparando por `id`:

```bash
python -c "
import json, sys
sys.path.insert(0, '.')
import medir_sesgo as MS
antes = json.load(open('data/_snapshot_antes.json', encoding='utf-8'))
ahora = json.load(open('data/partidos.json', encoding='utf-8'))
if isinstance(antes, dict): antes = antes.get('partidos', [])
if isinstance(ahora, dict): ahora = ahora.get('partidos', [])
comunes = {m['id'] for m in antes} & {m['id'] for m in ahora}
print(f'partidos en ambas versiones: {len(comunes)}')
for etiqueta, datos in (('ANTES', antes), ('DESPUES', ahora)):
    r = MS.sesgo_por_competicion([m for m in datos if m['id'] in comunes])
    print(f'--- {etiqueta} ---')
    for c in sorted(r):
        print(f'  {c:34} n={r[c][\"n\"]:3} local {r[c][\"local\"]*100:+6.1f}pp  |dif| {r[c][\"magnitud\"]*100:5.1f}pp')
"
```

Expected: el sesgo de `local` en CONMEBOL Libertadores **baja en valor absoluto** entre ANTES y DESPUÉS, sobre el mismo conjunto de partidos. Cualquier mejora es señal; una caída a la mitad o más es un buen resultado.

**Ojo con el tamaño de muestra:** con 8 partidos por copa, el ruido es grande. Una mejora de menos de 2pp no es concluyente — no la vendas como éxito.

- [ ] **Step 2: Interpretar honestamente**

Registrar el número real en el commit, sea cual sea:

- Si el sesgo bajó: el ancla funcionó. Anotar cuánto.
- Si bajó poco (menos de 2pp): el ancla ayuda pero falta el factor de calidad por liga (un 1.4 brasileño ≠ un 1.4 paraguayo). Anotarlo como el siguiente plan, **no** subir `PRIOR_FUERZA` a ojo para forzar el número.
- Si subió: hay un error. Revisar que las anclas se estén aplicando al equipo correcto — `resultados_temporada` devuelve ids como string y `fuerzas` los usa como clave; un desajuste string/int haría que ningún ancla matchee (y el log de la Tarea 4 Step 7 diría "ancladas 0").

**No tocar constantes para que el número dé mejor.** Si no mejoró, el hallazgo es que no mejoró.

- [ ] **Step 3: Commit del resultado medido**

```bash
git add data/partidos.json
git commit -m "Medición del ancla doméstica: sesgo de Libertadores de +12.3pp a X.Xpp

[Reemplazar X.X por el número real medido y describir en una línea qué
significa. Si no mejoró lo suficiente, decirlo acá y anotar que el
siguiente paso es calibrar factores de calidad por liga.]"
```

---

### Task 6: Medirse contra la cuota de cierre histórica

**El spec decía que esto era imposible.** Se afirmó que sin precios históricos no se puede comparar contra el mercado, porque ESPN borra las cuotas al terminar el partido. Eso es cierto de ESPN, pero `football-data.co.uk` publica un CSV gratis con la Liga Profesional Argentina: **6.295 partidos desde 2012**, y la temporada actual con **314 de 314 partidos con cuota de cierre** (verificado 2026-08-16). CSV plano por HTTP, sin clave, parseable con `csv` de la biblioteca estándar.

La cuota de **cierre** es el rival correcto: es el precio final, el que ya absorbió lesiones, alineaciones y plata informada. Ganarle a eso es la prueba dura.

**No cubre copas** (es un dataset de ligas), así que no sirve para validar el arreglo de Libertadores — para eso está la Tarea 5. Sirve para responder, hoy y con cientos de partidos, si el modelo le gana al mercado en Liga Profesional.

**Files:**
- Create: `medir_vs_mercado.py`

**Interfaces:**
- Consumes: `backtest.matriz`, `backtest.suma_si`, `actualizar.fuerzas_equipos`, `actualizar.resultados_temporada`.
- Produces: script suelto, no importado por nadie. No toca el cron.

- [ ] **Step 1: Escribir la tabla de equivalencia de nombres, completa y explícita**

Los nombres difieren entre las dos fuentes. **No usar cruce difuso**: se probó y produce un falso positivo silencioso — "Independiente Rivadavia" matchea con "Independiente" por substring, y ahí los resultados salen mal sin avisar. La tabla va explícita, y si aparece un equipo que no está, el script corta.

Crear `medir_vs_mercado.py` con:

```python
"""¿Le gana nuestro modelo a la cuota de cierre del mercado?

Compara la probabilidad del modelo contra la cuota de cierre real de
partidos ya jugados de Liga Profesional, usando el CSV público de
football-data.co.uk. La cuota de cierre es el precio más afinado que
existe: ya absorbió lesiones, alineaciones y apuestas informadas.

No es parte del cron. Se corre a mano:

    python medir_vs_mercado.py

Deliberadamente NO cubre Libertadores/Sudamericana: el dataset es de
ligas, no de copas. El sesgo de copas se mide con medir_sesgo.py.
"""
import csv
import io
import datetime
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from backtest import matriz, suma_si
import actualizar as A

CSV_URL = "https://www.football-data.co.uk/new/ARG.csv"

# ESPN -> football-data. Explícita a propósito: el cruce automático por
# substring hace matchear "Independiente Rivadavia" con "Independiente".
NOMBRES = {
    "Aldosivi": "Aldosivi",
    "Argentinos Juniors": "Argentinos Jrs",
    "Atlético Tucumán": "Atl. Tucuman",
    "Banfield": "Banfield",
    "Barracas Central": "Barracas Central",
    "Belgrano (Córdoba)": "Belgrano",
    "Boca Juniors": "Boca Juniors",
    "Central Córdoba (Santiago del Estero)": "Central Cordoba",
    "Defensa y Justicia": "Defensa y Justicia",
    "Deportivo Riestra": "Dep. Riestra",
    "Estudiantes de La Plata": "Estudiantes L.P.",
    "Estudiantes de Río Cuarto": "Estudiantes Rio Cuarto",
    "Gimnasia (Mendoza)": "Gimnasia Mendoza",
    "Gimnasia La Plata": "Gimnasia L.P.",
    "Huracán": "Huracan",
    "Independiente": "Independiente",
    "Independiente Rivadavia": "Ind. Rivadavia",
    "Instituto (Córdoba)": "Instituto",
    "Lanús": "Lanus",
    "Newell's Old Boys": "Newells Old Boys",
    "Platense": "Platense",
    "Racing Club": "Racing Club",
    "River Plate": "River Plate",
    "Rosario Central": "Rosario Central",
    "San Lorenzo": "San Lorenzo",
    "Sarmiento (Junín)": "Sarmiento Junin",
    "Talleres (Córdoba)": "Talleres Cordoba",
    "Tigre": "Tigre",
    "Unión (Santa Fe)": "Union de Santa Fe",
    "Vélez Sarsfield": "Velez Sarsfield",
}


def bajar_csv():
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    txt = urllib.request.urlopen(req, timeout=60).read().decode("utf-8-sig", "replace")
    return list(csv.DictReader(io.StringIO(txt)))
```

- [ ] **Step 2: Verificar que la tabla cubre a todos los equipos de las dos fuentes**

Agregar al script y correr:

```python
def verificar_nombres(filas_csv, temporada="2026"):
    """Corta si algún equipo no está mapeado. Un nombre suelto significa
    partidos descartados en silencio, que es peor que un error ruidoso."""
    del_csv = {r["Home"] for r in filas_csv if r["Season"] == temporada}
    mapeados = set(NOMBRES.values())
    faltan = del_csv - mapeados
    if faltan:
        raise SystemExit(f"equipos del CSV sin mapear: {sorted(faltan)}")
    return len(del_csv)
```

Run:

```bash
python -c "
import medir_vs_mercado as M
filas = M.bajar_csv()
n = M.verificar_nombres(filas)
print('equipos del CSV, todos mapeados:', n)
"
```

Expected: `equipos del CSV, todos mapeados: 30`, sin excepción. Si corta, agregar el nombre faltante a `NOMBRES` — no relajar la verificación.

- [ ] **Step 3: Comparar modelo contra cierre, partido por partido**

Agregar:

```python
def evaluar(temporada="2026", ventana_dias=400):
    """Para cada partido jugado con cuota de cierre: reconstruye las λ con
    los partidos ANTERIORES a esa fecha (nunca con el resultado que se va
    a predecir) y compara Brier del modelo contra Brier del mercado."""
    filas = [r for r in bajar_csv()
             if r["Season"] == temporada and (r.get("AvgCH") or "").strip()]
    verificar_nombres(filas, temporada)

    hoy = datetime.date.today()
    resultados = A.resultados_temporada("arg.1", hoy.year, hoy)
    # id de equipo -> nombre de football-data, vía el nombre de ESPN
    inv = {v: k for k, v in NOMBRES.items()}

    br_mod = br_mkt = 0.0
    n = 0
    for r in filas:
        try:
            fecha = datetime.datetime.strptime(r["Date"], "%d/%m/%Y").date()
            gh, ga = int(r["HG"]), int(r["AG"])
            cuotas = [float(r["AvgCH"]), float(r["AvgCD"]), float(r["AvgCA"])]
        except (ValueError, KeyError):
            continue
        if fecha > hoy or (hoy - fecha).days > ventana_dias:
            continue

        previos = [p for p in resultados if p["fecha"] < fecha]
        if len(previos) < 40:
            continue                      # muy poca historia para pronosticar
        fuerzas, mu_l, mu_v, pj = A.fuerzas_equipos(previos, fecha)

        ids = {}
        for p in previos:
            ids.setdefault(p["home"], None); ids.setdefault(p["away"], None)
        # el cruce id<->nombre sale del propio CSV: se resuelve por nombre
        # de football-data, así que se necesita el mapa inverso ESPN->id,
        # que se arma en el Step 4. Acá se saltea si no está.
        clave_l, clave_v = r["Home"], r["Away"]
        if clave_l not in IDS or clave_v not in IDS:
            continue
        a_l, d_l = fuerzas.get(IDS[clave_l], (1.0, 1.0))
        a_v, d_v = fuerzas.get(IDS[clave_v], (1.0, 1.0))
        lh = max(0.35, min(3.20, mu_l * a_l * d_v))
        la = max(0.30, min(3.00, mu_v * a_v * d_l))

        M_ = matriz(lh, la, A.COMPETICIONES["arg.1"]["rho"])
        pm = [suma_si(M_, lambda i, j: i > j),
              suma_si(M_, lambda i, j: i == j),
              suma_si(M_, lambda i, j: i < j)]
        crudas = [1 / c for c in cuotas]
        tot = sum(crudas)
        pq = [x / tot for x in crudas]

        real = [1 if gh > ga else 0, 1 if gh == ga else 0, 1 if gh < ga else 0]
        br_mod += sum((pm[i] - real[i]) ** 2 for i in range(3))
        br_mkt += sum((pq[i] - real[i]) ** 2 for i in range(3))
        n += 1

    return n, (br_mod / n if n else None), (br_mkt / n if n else None)
```

- [ ] **Step 4: Construir el mapa nombre-de-CSV → id de ESPN**

`fuerzas_equipos` usa ids de ESPN; el CSV trae nombres. Hace falta el puente. Agregar antes de `evaluar()`:

```python
def construir_ids():
    """{nombre de football-data: team_id de ESPN}, leyendo la tabla de
    posiciones de arg.1 (que trae id y nombre juntos)."""
    hoy = datetime.date.today()
    tabla = A.tabla_competicion("arg.1", hoy.year)
    fuera = []
    ids = {}
    for team_id, info in tabla.items():
        nombre_espn = info.get("nombre") if isinstance(info, dict) else None
        if not nombre_espn:
            continue
        fd = NOMBRES.get(nombre_espn)
        if fd:
            ids[fd] = team_id
        else:
            fuera.append(nombre_espn)
    if fuera:
        print(f"  aviso: sin mapear desde ESPN -> {sorted(fuera)}")
    return ids


IDS = {}
```

Y en `main()`, poblar `IDS` antes de evaluar:

```python
def main():
    global IDS
    IDS = construir_ids()
    print(f"equipos cruzados: {len(IDS)}")
    n, bm, bq = evaluar()
    if not n:
        raise SystemExit("no se evaluó ningún partido — revisar el cruce de nombres")
    print(f"\npartidos evaluados: {n}")
    print(f"  Brier modelo : {bm:.5f}")
    print(f"  Brier mercado: {bq:.5f}")
    dif = bq - bm
    if dif > 0:
        print(f"\n  El modelo le gana al cierre por {dif:.5f} de Brier.")
    else:
        print(f"\n  El mercado nos gana por {-dif:.5f} de Brier.")
    print("  (Brier más bajo = mejor. El cierre es un rival durísimo:")
    print("   quedar cerca ya es buena señal; ganarle es raro.)")


if __name__ == "__main__":
    main()
```

**Nota sobre `tabla_competicion`:** verificar su forma de retorno real antes de usarla (`grep -n "def tabla_competicion" -A 25 actualizar.py`). Si no devuelve el nombre del equipo junto al id, construir `IDS` recorriendo `data/partidos.json`, que sí tiene `home`/`homeId` juntos.

- [ ] **Step 5: Correr y leer el resultado con honestidad**

Run: `python medir_vs_mercado.py`

Expected: imprime la cantidad de partidos evaluados (debería ser >100) y los dos Brier.

**Cómo interpretar, sin autoengaño:**
- La cuota de cierre es el mejor predictor público que existe. **Lo más probable es que nos gane**, y eso no es un fracaso del proyecto.
- Quedar dentro de ~0.01 de Brier del cierre es un resultado respetable.
- Si el modelo diera *mucho* mejor que el cierre (más de 0.02), sospechar de una fuga de información: revisar que `previos` filtre estrictamente por `p["fecha"] < fecha` y que no se estén usando partidos posteriores.
- **No ajustar nada para mejorar este número.** El valor del script es saber dónde estamos parados.

- [ ] **Step 6: Commit**

```bash
git add medir_vs_mercado.py
git commit -m "Medirse contra la cuota de cierre real del mercado

El spec decía que era imposible porque ESPN borra las cuotas al terminar
el partido. Cierto de ESPN, falso del mundo: football-data.co.uk publica
gratis la Liga Profesional con 6.295 partidos desde 2012 y los 314 de
esta temporada con cuota de cierre.

Evalúa walk-forward (las λ de cada partido se calculan solo con partidos
anteriores) y compara Brier contra el cierre. La tabla de nombres es
explícita a propósito: el cruce difuso hacía matchear Independiente
Rivadavia con Independiente, y eso ensucia resultados en silencio.

No cubre copas: el dataset es de ligas."
```

---

### Task 7: Registrar pronósticos contra la línea del mercado

Complementa a la Tarea 6: aquella mide el pasado en Liga Profesional, ésta captura el presente **en todas las competiciones, incluidas las copas**, que es donde el dataset histórico no llega. Va al final porque conviene que empiece a grabar con el modelo ya corregido.

**Files:**
- Modify: `actualizar.py` (constante nueva junto a `CACHE_LIGAS`, función nueva antes de `main()`, y llamada al final de `main()`)
- Create (generado): `data/historial_pronosticos.json`

**Interfaces:**
- Consumes: la lista `partidos` que `main()` acaba de armar, `api()` (línea 109), `COMPETICIONES` (línea 96), `SITE_V2`.
- Produces: `registrar_pronosticos(partidos, season, hoy)` — sin retorno; escribe `data/historial_pronosticos.json`.

- [ ] **Step 1: Agregar la constante**

Junto a `CACHE_LIGAS`:

```python
HISTORIAL_PRON = Path("data/historial_pronosticos.json")  # qué dijimos nosotros y
                                                           # qué decía la línea, por
                                                           # partido. Crece con el
                                                           # tiempo; nunca se borra.
```

- [ ] **Step 2: Agregar la función, antes de `main()`**

```python
def registrar_pronosticos(partidos, season, hoy):
    """Guarda, por partido, qué probabilidad le dimos nosotros y cuál
    implicaba la línea — y resuelve los que ya se jugaron.

    Existe porque ESPN borra las cuotas cuando el partido termina: si no
    las capturamos ahora, después no hay forma de saber qué decía el
    mercado. Sin esto no se puede sostener "le ganamos al mercado" con
    algo más que una opinión.

    La probabilidad del modelo se calcula acá con las mismas λ y rho que
    ve el frontend, para que lo registrado sea exactamente lo que el
    usuario vio.
    """
    hist = {}
    if HISTORIAL_PRON.exists():
        try:
            hist = json.loads(HISTORIAL_PRON.read_text(encoding="utf-8"))
        except Exception:
            hist = {}

    # 1. anotar los partidos de hoy que todavía no estaban
    for m in partidos:
        mk = m.get("mercado")
        if m["id"] in hist or not mk or not mk.get("local"):
            continue
        crudas = [1 / mk["local"], 1 / mk["empate"], 1 / mk["visitante"]]
        tot = sum(crudas)
        hist[m["id"]] = {
            "fecha": m["date"], "comp": m["comp"],
            "home": m["home"], "away": m["away"],
            "lh": m["lh"], "la": m["la"], "rho": m["rho"],
            "mercado": [round(x / tot, 4) for x in crudas],   # sin margen
            "cuotas": [mk["local"], mk["empate"], mk["visitante"]],
            "resultado": None,
        }

    # 2. resolver los que ya se jugaron
    pendientes = [k for k, v in hist.items() if v["resultado"] is None]
    if pendientes:
        por_comp = {}
        for k in pendientes:
            por_comp.setdefault(hist[k]["comp"], []).append(k)
        slug_de = {meta["nombre"]: slug for slug, meta in COMPETICIONES.items()}
        for comp, claves in por_comp.items():
            slug = slug_de.get(comp)
            if not slug:
                continue
            # Se consulta el scoreboard del día de cada partido pendiente:
            # resultados_temporada() no devuelve el event_id, y la clave de
            # este archivo ES el event_id, así que hay que cruzar por ahí.
            for k in claves:
                try:
                    d = api(f"{SITE_V2}/{slug}/scoreboard?dates="
                            f"{hist[k]['fecha'].replace('-','')}")
                except Exception:
                    continue
                for ev in d.get("events", []):
                    if f"espn{ev.get('id')}" != k:
                        continue
                    c = (ev.get("competitions") or [{}])[0]
                    if not c.get("status", {}).get("type", {}).get("completed"):
                        break
                    loc = next((x for x in c.get("competitors", [])
                                if x.get("homeAway") == "home"), None)
                    vis = next((x for x in c.get("competitors", [])
                                if x.get("homeAway") == "away"), None)
                    try:
                        gh, ga = int(float(loc["score"])), int(float(vis["score"]))
                    except (TypeError, ValueError, KeyError):
                        break
                    hist[k]["resultado"] = [gh, ga]
                    break

    HISTORIAL_PRON.write_text(json.dumps(hist, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    resueltos = sum(1 for v in hist.values() if v["resultado"])
    print(f"· pronósticos registrados: {len(hist)} ({resueltos} ya resueltos)")
```

- [ ] **Step 3: Llamarla al final de `main()`**

Después de que `main()` escriba `data/partidos.json`, agregar:

```python
    registrar_pronosticos(partidos, season, hoy)
```

- [ ] **Step 4: Correr y verificar el archivo**

Run: `python actualizar.py`

Expected: imprime `· pronósticos registrados: N (M ya resueltos)` con N igual a la cantidad de partidos con cuota (hoy ~33).

Run:

```bash
python -c "
import json
h = json.load(open('data/historial_pronosticos.json', encoding='utf-8'))
print('partidos:', len(h))
k = next(iter(h)); v = h[k]
print('ejemplo:', k, v['home'], 'vs', v['away'])
print(' mercado sin margen:', v['mercado'], '-> suma', round(sum(v['mercado']),4))
assert abs(sum(v['mercado']) - 1.0) < 0.001, 'el devig no suma 1'
assert all(x in v for x in ('lh','la','rho','cuotas','resultado')), 'faltan campos'
print('OK')
"
```

Expected: la suma del mercado sin margen da 1.0 (±0.001) y `OK`.

- [ ] **Step 5: Verificar que correr dos veces no duplica ni pisa**

Run: `python actualizar.py` (segunda vez) y comparar el conteo impreso.

Expected: el mismo N que la corrida anterior (los partidos ya anotados no se re-anotan), y ninguna entrada perdió su `resultado` si ya lo tenía.

- [ ] **Step 6: Commit**

```bash
git add actualizar.py data/historial_pronosticos.json
git commit -m "Registrar nuestro pronóstico y la línea del mercado por partido

ESPN borra las cuotas cuando el partido termina, así que si no las
capturamos en el momento, después no hay con qué compararse. Este
archivo guarda, por partido, la probabilidad que implicaba la línea (ya
sin margen) y las λ con las que pronosticamos nosotros, y se completa
con el resultado real cuando se juega.

Es la base para poder decir 'acertamos más que el mercado' con un
número medido y no con una postura."
```

---

## Self-Review

**Cobertura del spec.** Este plan implementa los puntos 1, 2 y 3 de "Correcciones al modelo" del spec: ancla cruzando competiciones (Tareas 2-4), el mercado como vara de comparación (Tareas 1 y 6), y la base del seguimiento de acierto (Tarea 6). El punto 4 (lesiones cuantificadas) queda explícitamente fuera, como dice el spec. El rediseño del frontend y la auto-resolución del Registro son planes aparte.

**Riesgo conocido, anotado a propósito.** La Tarea 5 puede dar que el sesgo bajó poco. Eso no es un fallo del plan: la aproximación de usar la escala de goles de la copa (y no un factor de calidad por liga) está declarada arriba, y el paso 2 de esa tarea dice explícitamente qué hacer si pasa — anotarlo, no forzar constantes.

**Consistencia de tipos.** `resultados_temporada` devuelve ids de equipo como string (vienen de `loc["team"]["id"]`), `fuerzas_equipos` los usa como clave tal cual, y `ancla_de` normaliza con `str(team_id)` antes de consultar `pj`. El diccionario `anclas` se arma iterando sobre los ids que ya están en `resultados`, así que las claves coinciden por construcción. El Step 2 de la Tarea 5 nombra este desajuste como primer sospechoso si el ancla no aplica.

**Costo de pedidos.** La Tarea 3 agrega un pedido por equipo nuevo (cacheado en disco de por vida) más uno por liga local por corrida. Con ~30 equipos en copas repartidos en ~8 ligas: ~30 pedidos la primera vez, ~8 por corrida después. Aceptable para un cron que corre dos veces por día.
