# VALOR — informe de traspaso

**Para:** la IA que arranque el proyecto de cero en una carpeta nueva.
**Escrito:** 2026-08-17. **Repo de origen:** `gelucas2001-hub/VALOR`.

> **Actualización 2026-08-18 — leer antes que el resto del documento.**
> Después de escrito esto, se hizo el brainstorm visual que la sección
> 11 (Fase 1, pasos 5-8) pedía como pendiente — **ya no está pendiente.**
> Se hizo en Claude Design, con opciones comparadas y elegidas por
> Lucas, y produjo dos cosas que este documento todavía no menciona:
>
> 1. **El elemento firma está resuelto** (una V con barras ascendientes,
>    no el cupón). Ver la sección corregida más abajo y `DESIGN.md`.
> 2. **Un handoff completo con una funcionalidad nueva, verificada y
>    lista para implementar: la resolución automática del registro.**
>    Vive en `docs/design-handoff/` — está en el repo, no hace falta ir
>    a buscarlo a ningún lado externo. Ver la sección 6bis, nueva.
>
> La Fase 1 de la sección 11 (brainstorm) está **completa**. Empezá
> directo por la Fase 2 (docs/design-handoff/ + reglas) — ver el orden
> corregido al final de la sección 11.

> **Actualización 2026-08-19 — leer antes que el resto del documento.**
> La Fase 4 (sección 11, contenido) **ya no es un hueco**: hay una skill
> versionada en el repo, `.claude/skills/valor-analisis-inclinacion/`,
> que hace el research y escribe `inclinacion`/`contexto`/`veredicto`
> siguiendo la regla de alineación. **Se edita ahí, no en Claude.ai.**
> `data/analisis.json` tiene 12 partidos cargados (era 0). Ver la
> sección 10 corregida y la 6quinsexies para el resto: qué se agregó
> (`forma_general`, "Otros mercados", `divergen()`).
>
> **Actualización 2026-08-20 — el plantel ya no es un hueco.** El cron
> escribe `data/planteles.json` (42 equipos, 1152 jugadores con partidos
> jugados, goles y peso goleador), la pestaña Plantel lo muestra con la
> cancha del handoff, y `expediente.py` se lo pasa a la skill. Con eso,
> la skill pasó a **v2.0**: una lectura por equipo (campos `local` y
> `visitante`, nuevos en `analisis.json`) y bajas pesadas contra el
> plantel en vez de enumeradas. Ver la sección 6septies.

Este documento existe porque Lucas decidió rehacer el proyecto desde
cero, pero **el motor matemático y el pipeline de datos están validados
y medidos, y tirarlos sería destruir la única parte que costó semanas
de medición.** Lo que se rehace es la **interfaz**. Lo demás se
**hereda**.

Leé este archivo entero antes de escribir una línea de código.

---

## 0. Lo primero: qué salió mal, para no repetirlo

Esto no es autocrítica decorativa. Es la parte más útil del documento.

**El error central: se escribió la interfaz copiando maquetas aprobadas
en vez de diseñarla.** Las maquetas eran comps de 320px hechas para
*decidir una dirección*, no para ser el diseño final. Copiarlas 1:1 dio
una app correcta y genérica. Cuando el usuario dijo "le falta trabajo",
la respuesta fue parchar (agregar un elemento firma, después ajustar
espaciados) en vez de rehacer el proceso. Parchar dos veces sobre una
base copiada no arregla una base copiada.

**Errores concretos que costaron tiempo y no deben repetirse:**

1. **Afirmar sin medir.** Se afirmó que `/teams/{id}/schedule` traía
   todas las competiciones de un equipo. Es falso. Se afirmó que no se
   podía medir contra el mercado retroactivamente. Es falso
   (football-data.co.uk publica cuotas de cierre gratis). **Regla: si
   vas a afirmar algo sobre los datos, medilo primero.**

2. **Elegir constantes a ojo.** El spec pedía marcar "valor" a partir de
   3 puntos porcentuales de diferencia contra el mercado — pero el mismo
   documento medía que el modelo se aparta 9-15pp en promedio. O sea: el
   umbral estaba *dentro del propio error*. **Regla: toda constante de
   producto se barre sobre datos reales antes de fijarla.**

3. **Comparar mediciones entre corridas distintas.** El cron reescribe
   `data/partidos.json` dos veces por día. Medir "antes" a la mañana y
   "después" a la tarde compara partidos distintos. El mismo código dio
   +12.3pp y +8.7pp el mismo día. **Regla: para comparar antes/después,
   congelá un snapshot y usá el mismo archivo en las dos mediciones.**

4. **Mostrar capturas que el usuario no ve.** Se sacaron capturas, se
   miraron, y se le describieron al usuario sin mandárselas. El usuario
   no tenía forma de evaluar nada. **Regla: si evaluás algo visual,
   mandale el archivo.**

5. **Skills instaladas y no usadas.** Había skills de brainstorming y
   diseño instaladas que nunca se invocaron; se fue directo a escribir
   código. **Regla: si hay una skill que cubre la tarea, usala antes de
   empezar, no después de que el resultado no guste.**

6. **Tres IAs editando el mismo archivo en paralelo.** Claude Code,
   Antigravity y otra terminal tocaron `index.html` sin saber una de la
   otra. Se perdió trabajo y se borró funcionalidad. **Regla: una
   herramienta por área, o ramas separadas.**

---

## 1. Qué es VALOR

Una PWA de pronósticos de fútbol argentino y sudamericano, con un motor
de value betting abajo sosteniéndola.

**La distinción de producto más importante, y la que más vueltas
costó:** son dos preguntas distintas.

- *"¿Qué va a pasar en este partido?"* → el **pronóstico**. Es la
  promesa principal. Se mide por **tasa de acierto**.
- *"¿A qué conviene apostar?"* → el **valor**. A veces coincide con el
  pronóstico, muchas veces no. Se mide por **rentabilidad**.

**VALOR es un pronosticador, con un motor de value betting abajo. No al
revés.** La razón es de producto: presentarse como herramienta de value
betting obliga al usuario común a entender EV, banca y varianza antes de
obtener algo útil. Presentarse como pronosticador no le exige nada.

**Pero nunca se contradicen en pantalla.** Un intento anterior mostraba
"creemos que gana River, pero jugá a Racing a 5.75". Lucas lo rechazó
así: *"Es como decir, es probable que gane River pero paga poco, así que
preferimos que juegues una ruleta rusa a Racing."* Tenía razón, y el
problema de fondo es peor: ese 27% se apoyaba en un modelo que medimos
equivocándose 9-15pp.

**Alcance:** Liga Profesional Argentina, Copa Argentina, CONMEBOL
Libertadores, CONMEBOL Sudamericana. Volumen real: ~5 partidos por fecha
en Liga, hasta 8-10 en día fuerte de copas.

**Audiencia:** hoy es para Lucas. Pensado para que abrirlo a más gente
no requiera rehacer nada, pero sin construir multi-usuario todavía.

---

## 2. Lo que se hereda tal cual — NO REESCRIBIR

Estos archivos están validados y medidos. **Copialos, no los
reescribas.** Reescribir el motor arriesga errores numéricos
silenciosos: un signo cambiado en Dixon-Coles no tira una excepción,
solo da probabilidades sutilmente mal para siempre.

| Archivo | Qué hace |
|---|---|
| `actualizar.py` | Baja datos de ESPN y calcula λ. Corre solo, 2×/día, en GitHub Actions. **Es el motor.** |
| `backtest.py` | Calibración contra resultados reales |
| `medir_sesgo.py` | Cuánto nos apartamos de la línea del mercado, por competición |
| `medir_vs_mercado.py` | Brier contra la cuota de cierre real |
| `calibrar_ligas.py` | Cuánto vale cada liga sudamericana |
| `.github/workflows/actualizar.yml` | El cron |
| `data/*.json` | Los datos. Los escribe el cron. **No editar a mano.** |
| `icons/`, `manifest.json` | PWA |

**Referencia del motor verificado:** tag `motor-verificado`
(commit `539588f`, 2026-08-16).

**Rama de respaldo, no borrar:** `ui-antigravity` — trabajo previo
descartado que se conserva por si algo hace falta.

---

## 3. El pipeline de datos

### Cómo corre

GitHub Actions, `.github/workflows/actualizar.yml`:

- **Cron:** `0 12 * * *` y `0 18 * * *` UTC → 09:00 y 15:00 hora
  Argentina (UTC-3). Más `workflow_dispatch` para dispararlo a mano.
- **Runner:** `ubuntu-latest`, Python **3.12**.
- Corre `python actualizar.py`, hace `git add data/`, commitea como
  `valor-bot` y pushea.
- Necesita `permissions: contents: write`.

### Restricciones duras — no negociables

- **`actualizar.py` usa SOLO biblioteca estándar.** Corre en GitHub
  Actions sin `pip install`. Nada de `requests`, `numpy`, `pandas`.
- **Sin claves de API.** Todo sale de endpoints públicos.
- **No cambiar el contrato de `data/partidos.json`.** Agregar campos sí;
  renombrar o cambiar tipos rompe el frontend.

### De dónde salen los datos

**ESPN, API pública no documentada.** Dos hosts, con fallback: algunas
redes bloquean el primero (Akamai) y el segundo sirve las mismas
respuestas.

```
https://site.api.espn.com
https://site.web.api.espn.com      (fallback)
```

Dos prefijos de ruta:

```
apis/site/v2/sports/soccer    → scoreboard, teams/{id}/schedule, summary, teams/{id}
apis/v2/sports/soccer         → standings
```

Endpoints concretos en uso:

| Endpoint | Para qué |
|---|---|
| `{SITE}/{slug}/scoreboard?dates={desde}-{hasta}` | Partidos y **cuotas de DraftKings** |
| `{SITE}/{slug}/teams/{id}/schedule` | Partidos jugados: condición, goles, rival |
| `{SITE}/{slug}/teams/{id}` | Campo `defaultLeague` → la liga local del equipo |
| `{SITE}/{slug}/summary?event={id}` | Córners, faltas, tarjetas. **Un pedido por partido — es caro, por eso está cacheado** |
| `{CORE}/{slug}/standings?season={año}` | Tabla de posiciones |

Manda un `User-Agent` de navegador; sin eso responde mal.

**Slugs de competición:**

```python
"arg.1"                    Liga Profesional Argentina   rho 0.05  conf 75
"conmebol.libertadores"    CONMEBOL Libertadores        rho 0.00  conf 65
"conmebol.sudamericana"    CONMEBOL Sudamericana        rho 0.00  conf 65
"arg.copa"                 Copa Argentina               rho 0.00  conf 60
```

**Segunda fuente, para medir contra el mercado:**
`https://www.football-data.co.uk/new/ARG.csv` — CSV gratis, sin clave,
6.295 partidos de Liga Profesional desde 2012 con **cuota de cierre**.
No cubre copas.

### Trampa conocida al cruzar fuentes

Los nombres de equipo difieren entre ESPN y football-data, y **el cruce
difuso es peligroso**: hace matchear "Independiente Rivadavia" con
"Independiente" y ensucia resultados en silencio. `medir_vs_mercado.py`
tiene una tabla explícita de 30 equipos y **corta con error si falta
alguno**. Mantenerlo así.

---

## 4. El modelo matemático

### Núcleo

**Dixon-Coles sobre Poisson.** Se estiman λ (goles esperados) de local y
visitante, se arma la matriz de marcadores 0-9 × 0-9, y de ahí sale la
probabilidad de cualquier mercado sumando celdas.

La corrección `tau` de Dixon-Coles ajusta los cuatro marcadores bajos
(0-0, 0-1, 1-0, 1-1) que Poisson puro estima mal. El parámetro `rho`
está calibrado por competición (ver tabla de slugs arriba).

**Advertencia registrada:** `rho = 0.00` en las tres copas es un valor
**por defecto no validado**, no un resultado medido. Queda pendiente
calibrarlo — ahora hay 889 partidos de muestra y una vara para medirlo.

### Ajuste de fuerzas

`fuerzas_equipos()` estima ataque y defensa por equipo, iterativamente,
con dos mecanismos:

- **Decaimiento temporal:** `VIDA_MEDIA_DIAS = 45`. Un partido de hace 45
  días pesa la mitad que uno de hoy.
- **Regularización por prior:** `PRIOR_FUERZA = 3` "partidos fantasma"
  que empujan hacia un valor de referencia.
- `MIN_PARTIDOS_FUERZA = 3` — con menos que eso, el equipo no se estima.

### El problema grande que se resolvió: el ancla doméstica

**Síntoma medido:** el modelo tenía sesgo sistemático hacia el local en
copas — Libertadores **+12.3pp**, Copa Argentina +5.5pp, Sudamericana
+0.4pp, Liga Profesional −2.3pp. Caso extremo: modelo 52.0% vs mercado
22.6%.

**Causa raíz:** las fuerzas se ajustaban *solo con partidos de la misma
competición*. Con 6 partidos por equipo en copas, la regularización
empujaba todo al promedio: el modelo creía que Cerro Porteño y Palmeiras
eran parecidos, y la localía terminaba decidiendo.

**Solución en dos partes:**

1. **Ancla doméstica.** Un equipo llega a la Libertadores con la fuerza
   que se ganó en su liga local, donde tiene ~23 partidos en vez de ~6.
   Esa fuerza reemplaza al 1.0 hacia el que empujaba la regularización.
   La liga local se descubre con `defaultLeague` de `/teams/{id}`
   (verificado: Palmeiras→`bra.1`, Cerro Porteño→`par.1`, Liga de
   Quito→`ecu.1`). `MIN_PARTIDOS_ANCLA = 8`.

   Se implementa como **ancla del prior, no como Elo**: Elo resume la
   fuerza en un solo número, y el modelo de goles necesita ataque y
   defensa por separado.

2. **Factores de calidad de liga.** El ancla sola **empeoró**
   Sudamericana (magnitud 20.8 → 24.7pp), porque un 1.30 de ataque en
   Brasil y un 1.30 en Paraguay no son lo mismo. `calibrar_ligas.py`
   estima un multiplicador por liga usando 805 cruces de copa de 3
   temporadas. `MIN_CRUCES = 40` como piso: sin ese piso, `bra.2` daba
   1.352 con 20 cruces — más alto que `bra.1` (1.235), o sea el modelo
   "aprendía" que la segunda división brasileña es mejor que la primera.

**Resultado medido:** sesgo de Libertadores **+8.7pp → +3.5pp**.

### La vara: cuánto sabemos realmente

`medir_vs_mercado.py`, evaluación **walk-forward** (las λ de cada partido
se calculan solo con partidos anteriores a esa fecha — nunca ve el
resultado que predice), contra la cuota de cierre real:

```
Brier (más bajo = mejor)
  no saber nada (1/3)   0.667
  nuestro modelo        0.645
  cuota de cierre       0.623
```

**Traducción: el mercado mejora 0.044 sobre no saber nada; nosotros
mejoramos 0.022, o sea el 48% de eso. Le seguimos perdiendo al cierre.**

Esto no es un fracaso, es el número real y honesto. La app lo dice en la
pantalla de Método en vez de esconderlo.

### Otras piezas del motor

- **Devig proporcional.** La cuota cruda implica probabilidades que suman
  ~1.077 (**margen de la casa: 7.7% mediano**, medido sobre DraftKings).
  Compararse contra cuota cruda haría ver ventaja donde solo hay
  comisión. Siempre descontar el margen primero.
- **EV y Kelly.** Fracción de Kelly escalada por confianza de la
  competición. Tope de stake al 4% de banca.
- **Probabilidad conjunta exacta para combinadas.** Dos patas del mismo
  partido están correlacionadas; multiplicar las probabilidades por
  separado da un número falso. Se suma sobre la matriz. **Medido: la
  corrección supera 2pp en solo 4 de 16 combinadas, con máximo 6.2pp** —
  o sea que importa, pero menos de lo que se suponía.
- **Registro de pronósticos.** `registrar_pronosticos()` guarda λ, rho y
  mercado devigado por partido, y resuelve los terminados. Alimenta el
  marcador de acierto propio vs. acierto del mercado.

### Evaluado y descartado (no volver a intentarlo sin fuente nueva)

- **Lesiones de ESPN:** el endpoint responde **vacío** para equipos
  argentinos. No hay fuente gratuita. El contexto de bajas es carga
  manual.
- **xG de ESPN:** `/summary` trae `expectedGoals` **solo por jugador
  destacado**, no por equipo. Sumar dos o tres líderes no da el xG del
  equipo. Lo que sí viene completo por equipo: remates, remates al arco,
  posesión.
- **API-Football:** es paga. Descartada por la restricción de costo cero.
- **Ventaja de localía individual por equipo:** ruido con la muestra
  disponible.

### Pendientes reales del modelo

1. **Calibrar `rho` para copas** (hoy 0.00 sin validar).
2. **Validar `VIDA_MEDIA_DIAS` y `PRIOR_FUERZA`** con train/test split.
   Nunca se hizo; son valores razonables pero no medidos.
3. **Descontar partidos afectados por expulsión** — idea del propio
   Lucas, tras notar que Palmeiras empató 1-1 con un jugador menos desde
   el minuto 70.
4. **Usar remates además de goles** para estimar fuerza. Es una pregunta
   empírica, ahora respondible porque existe la vara del punto anterior.
5. **Calibrar la probabilidad antes de publicarla.** Hoy se publica la
   cruda. Lo correcto sería `cruda → calibración → publicada`. **No se
   implementó por muestra insuficiente:** las franjas de
   `data/backtest.json` tienen entre 1 y 27 partidos. Corregir con un bin
   de 1 partido agrega ruido y disfraza de precisión algo que no la
   tiene. **Condición para activarlo: al menos 30 partidos por franja.**

---

## 5. Las reglas de recomendación (medidas, no opinadas)

Esta sección es el corazón del producto y **cada número acá se barrió
sobre los 30 partidos reales antes de fijarse**. Se reprodujo por dos
caminos independientes — un script Python sobre `backtest.py` y el motor
en JavaScript del frontend — con resultado idéntico (20 marcas sobre 90
picks, 2 alertas sobre 25 partidos con cuota).

### Regla 1 — Escalera de riesgo

Cada partido ofrece **la misma lectura a tres niveles de riesgo**. No son
tres opiniones distintas: son tres formas de jugar la misma lectura.

| Franja | Probabilidad |
|---|---|
| Lo más probable | 68-93% |
| Intermedia | 45-68% |
| Arriesgada | 12-45% |

**Verificado: las tres franjas tienen candidato en 30 de 30 partidos.**

(Un intento anterior etiquetó como "lo más seguro" a un 54%. Eso es cara
o cruz, no seguridad.)

### Regla 2 — Los escalones son pronósticos; el valor se marca aparte

Las apuestas seguras casi nunca tienen valor: el margen de 7.7% se come
la ventaja justo en las cuotas bajas. Si se filtrara cada escalón por
valor, solo sobreviviría el arriesgado — que es exactamente el problema
que Lucas rechazó. Entonces: los escalones responden *"¿qué es lo más
probable?"*, y **la marca de valor aparece solo donde además el precio
está a favor**.

### Regla 3 — Alineación: nada contradice nuestra propia lectura

Si el modelo señala "valor" en algo que va en contra de lo que creemos
que va a pasar, eso no es valor: es error del modelo. No se muestra.

**Para que esto no sea circular, la lectura debe venir de donde el
modelo no llega — el análisis cualitativo.** Si la lectura la produjera
el propio modelo, filtrar por alineación sería el modelo dándose la
razón a sí mismo. De ahí se sigue: **solo se marca valor en partidos con
análisis cargado.**

### Regla 4 — Umbral de cuota, no cuota de referencia

Mostrar "@2.20 de DraftKings" es una trampa: DraftKings no opera en
Argentina, el usuario va a Betsson, encuentra 2.05 y no sabe si sigue
conviniendo. Se muestra **"conviene si te pagan más de X"**.

**X no es la cuota justa: es la justa más el margen de seguridad.** A la
justa exacta la ventaja es **cero**.

```
umbral = (1 / probabilidad) × (1 + 0.04)
```

### Regla 5 — Selección dentro de cada franja

La franja sola no alcanza. Si dentro de "lo más probable" se elige el
porcentaje más alto, el sistema recomienda siempre lo mismo y algo
inservible: verificado, los más probables eran "local no pierde por 2+"
(91.4%) y "más de 0.5 goles" (89.4%) — mercados que pagan 1.09.

1. **Lista corta de mercados que la gente juega y entiende:** 1X2, doble
   oportunidad (las tres), más/menos de 1.5-2.5-3.5 goles, ambos marcan
   sí/no. **Quedan fuera** marcador exacto, hándicaps y las líneas de 0.5
   goles (pagan 1.05-1.12: ruido disfrazado de apuesta).
2. **Dentro de la franja, el de mayor ventaja sobre el mercado**, pidiendo
   al menos 2pp — **pero solo dentro de la banda creíble (≤12pp)**. Sin
   ese techo la regla elegía cosas como Botafogo–Cienciano con **+53pp**
   de diferencia, que no es una oportunidad encontrada sino el modelo
   equivocado: elegir por ahí es elegir justo el pick con más chance de
   estar mal.
3. **Si ninguno califica, el más cercano al centro de la franja**,
   mostrado sin marca de valor.

**Verificado: la regla reparte entre 13 mercados distintos sobre 90
picks.** No repite siempre lo mismo.

### Constantes de valor — barridas, no elegidas

```
VALOR_MIN = 0.06     piso de la banda de mostaza
VALOR_MAX = 0.12     techo
ALERTA_MIN = 0.10    el mercado nos saca esto en nuestra propia lectura
MIN_EV = 0.04
EV_ABSURDO = 0.25    arriba de esto no se recomienda monto
MAX_ODDS = 4.5
```

**Por qué el piso es 6pp y no 3pp:** el spec pedía 3pp, pero el modelo se
aparta 9-15pp de la línea limpia en promedio. Un piso de 3pp está
*dentro del propio error*. Barrido real:

```
piso    picks marcados   % de picks   partidos con marca
 3pp          29             32%          19 de 30
 4pp          25             28%          18 de 30
 5pp          23             26%          17 de 30
 6pp          20             22%          16 de 30   ← elegido
 7pp          18             20%          15 de 30
 8pp          15             17%          12 de 30
```

**Una sola marca de valor por partido**, la de mayor ventaja. Sin esa
regla quedaban dos escalones dorados en el mismo partido, y una señal
que aparece en todos lados no informa nada.

**Control de cordura:** Método dice que arriba de +25% de EV lo más
probable es que nuestro λ esté mal. Herramientas debe respetarlo y **no
recomendar monto** en ese caso, o la app se desmiente a sí misma en dos
pantallas.

### 5bis. El barrido rehecho — y el problema que encontró

Medido el 2026-08-18 con `node barrer_valor.js`, sobre el snapshot
congelado de 34 partidos. Las funciones salen de `index.html`, no de una
copia.

**La forma del barrido se reproduce.** Al 3pp da 32% de los picks
marcados, idéntico a lo que decía la tabla original medida sobre 30
partidos:

```
piso    marcados   % de picks   partidos con marca
 3pp        33         32%        21 de 34
 4pp        32         31%        21 de 34
 5pp        32         31%        21 de 34
 6pp        27         26%        19 de 34   ← el que rige
 7pp        22         22%        17 de 34
 8pp        16         16%        13 de 34
10pp         8          8%         8 de 34
```

**Dos números del TRASPASO se confirman y uno no.** La alerta se
enciende en el **7%** de los partidos con cuota (decía 8%). El margen
de las casas da mediana **7,68%** (decía 7,7%). Pero el apartamiento
del modelo respecto de la línea limpia da **media 8,5%, mediana 7,3%,
percentil 90 15,3%** — el documento decía "9-15pp en promedio", y la
media queda apenas por debajo de ese rango.

**El problema, y es el mismo que motivó subir el piso de 3pp a 6pp:**
la mediana del apartamiento es **7,3pp** y el piso es **6pp**. O sea
que el piso actual también está por debajo del apartamiento típico.
El argumento que descartó el 3pp le aplica igual al 6pp.

**No se tocó la constante.** Elegir 8pp porque "queda arriba de la
mediana" sería exactamente el error que el repo prohíbe: mover un
número para que la medición se vea bien. Y además la pregunta está mal
planteada — apartarse del mercado no es lo mismo que equivocarse. La
única forma honesta de fijar el piso es medir **si los picks marcados
ganan más que los no marcados**, y para eso hacen falta resultados.

**Ese camino ahora existe:** la resolución automática del registro
(sección 6ter) acumula resultados sola. Cuando haya volumen, el piso
se decide con datos de cobro, no con distancia al mercado. Hasta
entonces el 6pp se queda, declarado como provisorio.

### Regla de ritmo

**Siempre hay pronóstico, no siempre hay recomendación.** Habrá días sin
nada que recomendar, y está bien — pero la app nunca debe quedarse sin
opinión, o el usuario deja de abrirla.

**Corolario importante:** un partido sin análisis cargado **muestra la
escalera como pronóstico, sin ninguna marca de valor** — no una pantalla
vacía. Con `analisis.json` vacío, la alternativa dejaría la app entera
sin contenido.

---

## 6. La línea gráfica

**Dirección:** prensa deportiva argentina vieja — tapas de El Gráfico,
cupones de Prode, programas de cancha.

**Explícitamente rechazado por Lucas, no volver a proponerlo:**
- crema + serif + terracota ("vintage americano" genérico)
- negro + verde ácido
- negro + celeste + insignias + "PRO AI" (cliché de SaaS de IA)

### Paleta — un color, un solo trabajo, siempre

| Color | Hex | Trabajo, único |
|---|---|---|
| Fondo | `#1B1611` | Casi negro tibio, noche de cancha. **No** negro frío de terminal |
| Hueco | `#171310` | Más hondo: masthead, cajas hundidas |
| Panel | `#221C15` | Tarjeta |
| Tinta | `#EEE3CE` | Texto, datos neutros, y **estado seleccionado** |
| Mostaza | `#D6963A` | **Valor**: acá hay algo mejor que el precio. Y nada más |
| Terracota | `#C06848` | **Alerta**: cuidado, esto no rinde. Y nada más |
| Salvia | `#6B7A5E` | Decorativo. Solo el filete bajo el masthead |

Escala de grises tibios para jerarquía de texto: `#D8CDB4`, `#B8AD95`,
`#8C7F68`, `#6E6350`, `#5C513F`. Líneas: `#241D16`, `#2A2318`.

**Reglas duras:**
- Nunca un tercer color funcional.
- Nunca semáforo verde/amarillo/rojo.
- **Nunca mostaza para selección de UI.** El día activo es tinta, no
  mostaza. Confundir "seleccionado" con "hay valor" es el error que más
  caro paga el usuario.
- En Historial el "color" viene de **intensidad tipográfica** — ganado en
  tinta plena, perdido casi apagado — nunca de mostaza ni terracota.

### Tipografía

- **Anton** — nombres de equipo, títulos de liga, wordmark. Tapa de
  revista deportiva.
- **JetBrains Mono** — todo número que se compare o se confíe.
- **Archivo** — cuerpo, UI, prosa de análisis.

### Chrome y densidad

- **Pestañas silenciosas:** línea inferior + color de texto. Nunca botón
  con caja.
- **Filas planas** en listas largas. Nada de tarjeta dentro de tarjeta.
- **El bloque de análisis es tipografía sola, sin caja** — nota de
  revista, no tarjeta de dashboard.
- Grano/textura solo en el masthead, nunca sobre filas de datos.
- La curva acumulada del Registro es la única línea curva de la app.

### El elemento firma — estado: RESUELTO (2026-08-18)

El spec lo definía como "la pieza memorable de VALOR, todavía sin
encontrar". Se intentó una idea acá mismo, en este repo — **el cupón de
Prode** — y no convenció en dos ejecuciones distintas (ver el hallazgo
2 de la sección 0, más abajo, que sigue siendo válido como lección de
proceso aunque la firma ya esté resuelta).

**Se resolvió en Claude Design, con un brainstorm real: cuatro
candidatos aislados, comparados antes de integrar ninguno.** Ganó una
**V** con cuatro barras ascendientes en verde oliva recortadas dentro
del trazo derecho — la escalera de riesgo, hecha símbolo. El cupón no
volvió a proponerse.

**El SVG real y la explicación completa están en `DESIGN.md`, sección
"Marca".** No la reinventes ni la vuelvas a buscar: está verificada
(extraída del prototipo final, no retipeada) y aprobada por Lucas.

Un detalle de proceso que vale la pena repetir en el futuro: la entrega
del handoff **cambió de marca entre una versión y la siguiente**
(troquelado → V) y el README del bundle no se actualizó — seguía
llamando "decisión final" a la versión vieja. Se corrigió a mano. **Si
volvés a pedir un handoff externo, confirmá que la documentación
coincide con el prototipo antes de darla por buena.**

---

## 6bis. El handoff de Claude Design — verificado, listo para implementar

`docs/design-handoff/VALOR.dc.html` + `docs/design-handoff/README.md`
son la entrega final de una ronda de diseño hecha en Claude Design,
conectado a este mismo repo por GitHub. **No es un mockup a medias: se
verificó línea por línea, no se aceptó de palabra.** Lo que sigue es lo
que se comprobó corriendo código, no leyendo promesas:

- **El motor matemático no fue tocado.** Se extrajeron las funciones
  (`matrix`, `sumIf`, `ev`, `kelly`, `tau`, `pois`) del prototipo y las
  del `index.html` del repo, se corrieron ambas sobre los 30 partidos
  reales: **diferencia máxima 0** en las 90 probabilidades resultantes.
  Motor idéntico, bit a bit.
- **La resolución automática del registro es una funcionalidad nueva,
  con lógica probada.** Hoy el registro depende de que el usuario marque
  a mano si acertó — y eso nunca se llena. La solución: cruzar cada
  apuesta anotada contra `formH`/`formA` de partidos futuros del mismo
  equipo (el marcador aparece ahí, un refresco después de jugarse).
  Verificado con Node contra los datos reales: **sin los dos candados
  del algoritmo, 3 de 30 partidos cruzan con el resultado equivocado
  (fase de grupos, mismos rivales repetidos). Con los candados, 0 de
  30.** Está documentado con el algoritmo completo, los dos candados
  explicados, y por qué hacen falta.
- **Los tokens de diseño (color, tipografía, espaciado, movimiento)
  están medidos, no elegidos a ojo** — ocho rondas de exploración con
  Lucas eligiendo en cada una.
- **Encontraron un hueco real en los datos que nadie había visto:** la
  tabla del Grupo A de Libertadores trae 4 equipos y le falta uno de los
  que juega ese partido (Cruzeiro). Verificado contra `data/partidos.json`
  real. Diseñaron Posiciones y Plantel para declarar el hueco en vez de
  esconderlo.

**Orden de implementación recomendado, por valor:**

1. ~~**Resolución automática del registro primero.**~~ **HECHO
   (2026-08-18).** Está en `index.html`, en la región marcada
   `/* ==== INICIO RESOLUCION ==== */`, con `test_registro.js` (17
   casos, `node test_registro.js`) corriendo contra el snapshot
   congelado `tests/partidos-snapshot.json`. Ver la sección 6ter.
2. ~~**El rediseño visual completo** de las cuatro pantallas.~~
   **HECHO (2026-08-18).** Las cuatro están construidas contra el
   prototipo. Ver la sección 6quater.

**Una limitación del archivo, no del diseño:** `VALOR.dc.html` usa un
motor de plantillas propio de Claude Design que no corre completo fuera
de su entorno (un solo error de consola conocido: la curva del Registro
no reemplaza `{{ reg.puntos }}`). Es un documento para **leer**, no para
ejecutar y copiar. La lógica de JS común (motor, `TESTS`, `resolver`,
`buscarResultado`) sí se transplanta literal — el propio README lo
señala.

**Antes de escribir código de la fase visual: confirmá que `README.md`
sigue describiendo lo que hay en `VALOR.dc.html`.** Ya pasó una vez que
no coincidían (ver la nota en la sección anterior sobre la marca).

---

## 6ter. Resolución automática — implementada, y lo que se midió

Implementada el 2026-08-18 siguiendo el algoritmo del handoff **sin
cambiarlo**. Lo que sigue es lo que se comprobó corriendo código.

**Reproduce la medición del handoff.** Sobre los 34 partidos de
`data/partidos.json` del 2026-08-17 (el handoff midió sobre 30): sin el
candado de fecha cruzan mal **3** — Independiente Rivadavia vs
Fluminense, Cerro Porteño vs Palmeiras, Club Olimpia vs Vasco da Gama.
Con los dos candados, **0**. El handoff decía 3 y nombraba Cerro
Porteño vs Palmeiras: coincide.

**La orientación del marcador se verificó sin fixtures a mano.** Un
partido puede aparecer en dos historiales independientes (el del local
y el del visitante, este último con el marcador al revés). De 78
partidos que aparecen en las dos fuentes, 75 se jugaron una sola vez y
**coinciden sin una sola excepción**. Ese test es el que atrapa un
error de signo.

**Hallazgo nuevo, no estaba en el handoff:** los otros 3 son cruces
**repetidos con el mismo local**. Olimpia y Vasco se cruzaron tres
veces dentro de los últimos cinco de Olimpia, dos de ellas en Brasil
(0-0 y 3-0). El desempate por `k` se queda con el más reciente, que es
lo correcto en ese caso, pero **es una grieta real del cruce por
historial**: si anotás el primero de dos partidos con el mismo local y
después se juega el segundo, el cruce puede traer el marcador del
segundo. Pasa solo en fase de grupos y solo con localía repetida.

**La solución de fondo ya estaba señalada por el handoff, y conviene
hacerla:** que `actualizar.py` persista los marcadores finales en
`data/resultados.json` (`{matchId: "2-1"}`). Eso vuelve el cruce exacto
y hace innecesarios los dos candados. **Dejar el cruce por historial
como respaldo**, no borrarlo: cubre los partidos anteriores a que ese
archivo exista.

**Contradicción de documentación, sin resolver:** `DESIGN.md` dice
"mostaza = valor, y nada más" y "terracota = alerta, y nada más"; el
handoff le asigna mostaza a *ganada* y terracota a *perdida* en el
Registro. Se siguió el handoff porque `index.html` ya usaba esos dos
colores para ganada/perdida en los botones del Registro desde antes.
La regla de `DESIGN.md` sobre intensidad tipográfica habla del
**Historial** (la pestaña del partido), que es otra pantalla. Vale
aclararlo en `DESIGN.md` antes de la fase visual.

---

## 6quater. La fase visual — hecha, y contra qué se construyó

**El README del handoff está desactualizado en dos puntos. Se verificó
contra `VALOR.dc.html` antes de escribir código, y manda el prototipo:**

1. El README dice que la portada lleva el **wordmark troquelado**. El
   prototipo (`:29-31`) usa **la V**, y reserva el troquelado para
   `REGISTRO` y `MÉTODO` (máscaras `tq-rg`, `tq-mt`). Coincide con
   `DESIGN.md`. Es el mismo desajuste que ya había pasado con la marca:
   el README no se actualizó cuando el prototipo cambió.
2. El README dice "seis pestañas" y después lista cinco, llamando "el
   resumen" a Pronósticos. El prototipo (`:1536`) tiene las seis con
   Pronósticos por nombre, como esta sección 7.

**Decisión de color tomada por Lucas:** el resultado de una apuesta
(ganada/perdida) **no se pinta** — va por intensidad tipográfica, como
Historial. Mostaza y terracota se quedan exclusivas de valor y alerta.
La única excepción es la curva acumulada, que sigue en mostaza porque
es la trayectoria, no una apuesta puntual. Está documentado en
`DESIGN.md § Resultado ≠ valor`, con la tabla de qué cambió.

**Corrección al hallazgo de datos del handoff — medido.** El handoff
decía haber encontrado un hueco: «la tabla del Grupo A de Libertadores
trae 4 equipos y le falta uno de los que juega ese partido
(Cruzeiro)», y diseñó Posiciones y Plantel para declararlo.
**Verificado sobre los 34 partidos: Cruzeiro está en el Grupo D de la
misma Libertadores.** Ese partido es un cruce entre grupos, no un
agujero de datos.

De 24 partidos donde uno de los dos equipos no figura en la tabla:

```
19   el equipo está en otro grupo/zona de la MISMA competición   → tabla completa, cruce de llave
 5   no figura en ninguna tabla de esa competición               → hueco real
```

En Liga Profesional el patrón es sistemático: Zona A y Zona B son
tablas separadas, así que el rival de la otra zona nunca va a estar.
La nota del handoff, tal cual, habría dicho «la fuente devolvió estas
15 líneas y ninguna es suya» en partidos donde la fuente está
perfecta. **Se partió en dos casos** (`quienFalta()` en `index.html`):
«Juegan cruzado» cuando el rival está en otro grupo, «Falta uno» solo
cuando de verdad no está. Los tres casos verificados en navegador:
Flamengo–Cruzeiro da cruzado, Tolima–Independiente del Valle da falta,
Lanús–Independiente no da nota.

**Regla violada en el código viejo, corregida:** la tabla de Posiciones
resaltaba el puesto de tus equipos en **mostaza**. `DESIGN.md` dice
«Nunca mostaza para selección de UI» y lo llama «el error que más caro
paga el usuario». Ahora va en tinta, como el prototipo.

**Lo que NO se copió del prototipo, y por qué:** las casillas de cuota
de `index.html` tienen una barra de tinta que dibuja la probabilidad con
escala fija al 70%. El prototipo usa casillas planas. Se conservó la
barra: es información real que el prototipo no tiene, y borrarla sería
perder funcionalidad para parecerse más a una maqueta.

**Verificado en navegador, a 375px, con datos reales:** cero errores de
consola; las cuatro pantallas y las seis pestañas sin desborde
horizontal — medido intentando `scrollTo(500,0)` y confirmando que
`scrollX` queda en 0, no solo leyendo `scrollWidth`, que reporta de más
mientras la tira de pestañas todavía está animando.

---

## 6quinquies. El cambio de guardia — hecho (2026-08-18)

La interfaz nueva dejó de llamarse `app.html`: **es `index.html`.** El
archivo viejo (negro frío, cian, verde semáforo) se borró; su contenido
sigue en el historial de git si alguna vez hace falta.

Se hizo con `git rm index.html && git mv app.html index.html`. **Ojo con
la historia:** como `index.html` ya existía, git no lo anota como rename
sino como borrado más modificación. `git log --follow index.html`
devuelve la historia de la interfaz **vieja**, no la de esta. Para la de
la app actual: `git log -- app.html`, hasta el commit del cambio.

**Lo que arrastró el cambio de nombre**, porque cuatro scripts leen el
HTML publicado en vez de una copia — que es exactamente por qué se
enteraron del rename:

| Archivo | Qué lee |
|---|---|
| `test_registro.js` | La región `/* ==== INICIO RESOLUCION ==== */` |
| `test_alineacion.js` | Las funciones de lectura y sello |
| `barrer_valor.js` | Las constantes de valor que rigen hoy |
| `doble_via.py` | El motor, para compararlo contra el de Python |

Más `CLAUDE.md`, `DESIGN.md` y este documento. Los de
`docs/design-handoff/` y `docs/superpowers/specs/` se dejaron como
estaban: son actas de una entrega cerrada y dicen `app.html` porque eso
era cierto cuando se escribieron.

**Verificado después del cambio:** `node test_registro.js` 22 ok,
`node test_alineacion.js` 19 ok, `python doble_via.py` diferencia máxima
6,7e-16. Y `manifest.json`, que se había quedado con `#070B14` — el azul
de la línea descartada — ahora arranca en `#1B1611`: la pantalla de
carga del PWA ya no destella el color viejo.

---

## 6quinsexies. Lo que se agregó el 2026-08-19

**Problema de fondo que motivó todo esto:** la forma reciente de un
equipo se calculaba *por competición*. Un equipo con partidos
infrecuentes en copa (fase de grupos, 1 partido cada 3-4 semanas)
mostraba una "forma" de meses de antigüedad el día del análisis, sin
nada de su actualidad real en el torneo local.

- **`forma_general()`** (`actualizar.py`) — junta la forma de todas las
  competiciones de un equipo y ordena por fecha real, no por
  competición. Para equipos en Libertadores/Sudamericana, reutiliza los
  resultados de liga doméstica que `ancla_de()` **ya pedía** para el
  ancla — sin pedido de red nuevo. Verificado en vivo: Cerro Porteño
  (Paraguay) pasó de mostrar forma vieja/duplicada a forma real y
  fresca de `par.1`. 23/23 tests en `test_forma.py`.
- **"Otros mercados"** (`index.html`, `otrosMercados()`) — la escalera
  de riesgo solo mostraba 3 mercados; si los tres caían en la misma
  familia (ej. los tres de Goles), el usuario no veía 1X2 ni Ambos
  Marcan. La sección nueva muestra **todos** los mercados calculados,
  reusando los mismos valores — nunca agrega una segunda marca dorada.
- **`divergen()`** (`index.html`) — si la lectura del modelo (`lectura().lean`)
  y la inclinación humana (`inclinacionDe()`) señalan direcciones
  distintas, la pestaña Pronósticos ahora lo dice explícito en vez de
  mostrar los dos sin explicar por qué no coinciden.
- **La skill de análisis pasó a vivir en el repo**, versionada:
  `.claude/skills/valor-analisis-inclinacion/SKILL.md`. Se corrigieron
  dos errores reales que Lucas encontró leyendo el contenido generado
  (no un chequeo automático): una racha de Platense mal leída — el DT
  nuevo ya había jugado dos partidos, no "seguía acomodándose" — y una
  búsqueda floja que no identificó a Coudet como DT de River. Se
  agregó **principio I** a la skill: cruzar cualquier afirmación de
  racha/momento contra el propio `formH_general`/`formA_general` del
  expediente antes de escribirla, porque ese dato ya está cargado y
  fechado — no hace falta que lo confirme una búsqueda externa que
  puede estar vieja o incompleta.

---

## 6septies. El plantel y la skill v2.0 (2026-08-20)

Todo esto salió de una sola auditoría de Lucas: leyó el análisis de
River–Independiente Santa Fe y dijo que solo nombraba bajas, que la
mayoría no valían nada (Acuña y Driussi hacía más de un mes que
faltaban; Arambarri había jugado un partido), y que del rival no sabía
nada — "¿cómo juega? ¿viene bien? ¿es fuerte de local?".

Resultaron ser **tres causas distintas**, y esto importa porque
arreglar solo la última no hubiera servido:

1. **Un bug de cableado.** La app mostraba `formH`/`formA` (filtrado
   por competencia, viejo en copa) donde ya existía `formH_general`.
   River aparecía con cinco resultados de la fase de grupos mientras el
   dato fresco —cuatro derrotas 0-1— estaba en el mismo archivo, sin
   usar. Dos líneas en `tabHistorial()` y `tarjeta()`.
2. **Faltaba el dato para pesar.** Sin partidos jugados ni goles por
   jugador, "no está Montiel" y "no está Arambarri" se escriben igual.
   Ahora el cron escribe `data/planteles.json`.
3. **La skill nunca pidió describir el juego.** Recién con (2) resuelto
   tenía sentido tocarla.

**`data/planteles.json`** — 42 equipos, 1152 jugadores, ~300 KB. Sale
de `/{slug}/teams/{id}/roster`, que medido en vivo devuelve 38-40
jugadores con estadísticas completas en **un pedido de ~0.5s** (la app
afirmaba que hacían falta 50 pedidos; era falso, se corrigió). La
trampa de siempre: las estadísticas son **por competición**, igual que
la forma. Se resolvió acumulando los slugs por equipo
(`slugs_de_equipos()`) y fusionando después — acumular planteles por
partido haría que un equipo con dos fechas de la misma liga se sume a
sí mismo. Verificado: Driussi pasó de 3 PJ/1 gol a 5 PJ/3 goles, y el
costo total subió de 592 a 594 requests.

**La pestaña Plantel** dibuja la cancha del handoff de Claude Design,
con el once inferido por partidos jugados. El prototipo tenía un 4-3-3
fijo; al derivarlo de datos reales, 13 de 42 equipos daban esquemas
imposibles (el peor, 7-0-3) porque ESPN clasifica mal a varios
jugadores. Con cupos por línea acotados a rangos reales: 0 de 42, y
siguen apareciendo nueve esquemas distintos. La pantalla dice que es
una inferencia, no un dato.

**La skill v2.0** (`.claude/skills/valor-analisis-inclinacion/`):

- `expediente.py` ahora entrega `plantelH`/`plantelA` (los 25 que más
  jugaron, con `pj`, goles, asistencias y `peso_goles`) y `pjMaxH`/
  `pjMaxA` como escala. El recorte del modelo sigue intacto y hay un
  test que lo verifica (`test_expediente.py`).
- **Principio J:** toda ausencia se cruza contra el plantel antes de
  escribirse. Se descarta la que no mueve el partido, se nombran dos o
  tres como mucho, se dice por qué pesa con el número, y una ausencia
  de más de un mes es el estado del equipo, no una novedad.
- **Campos `local` y `visitante`** en `analisis.json`, uno por equipo,
  que la app muestra bajo el nombre de cada uno. El cambio es
  estructural a propósito: con un campo único nada obligaba a hablar
  del rival y el hueco no se veía. Son aditivos — los análisis viejos
  siguen andando, y hay un test que lo cubre.
- **Sección 4bis:** cómo describir a qué juega un equipo sin inventar,
  usando los marcadores como retrato y `peso_goles` para saber si el
  ataque es un equipo o un jugador.
- Presupuesto de búsqueda de 4 a 6, con al menos dos sobre el equipo
  del que menos se sabe.

Probada en Aldosivi–Unión: encontró tres titulares lesionados del
visitante (Vargas, Malcorra, Mosqueira), los tres con `pj` alto en el
plantel, y describió a los dos equipos por su problema real —ninguno
convierte— en vez de listar nombres.

---

## 6octies. Estadísticas de equipo y de jugador (2026-08-20)

Lucas empezó a mirar apuestas de estadísticas y pidió **ver** los
números — remates, remates al arco, faltas, córners, tarjetas,
atajadas. Explícitamente **no** como mercado: no hay línea, no hay
cuota, no hay Kelly. Es información, no una recomendación.

**El hallazgo:** el pipeline ya pedía `/summary?event=` de cada partido
para calcular los córners del modelo (`disciplina_equipo`), y ese mismo
response trae **25 métricas por equipo**. Se guardaban 3 y se tiraban
22. Sumarlas no costó un pedido más — costó dejar de descartar.

- `estadisticas_equipo()` aplana las métricas de un partido. Lo que
  ESPN no trajo queda en `None`, **nunca en 0**: en pantalla un cero
  medido y un dato ausente se leen igual, y un equipo que remató 0
  veces es una noticia mientras que un partido sin estadísticas
  cargadas no lo es.
- `promedios_equipo()` promedia cada métrica sobre los partidos que sí
  la traen, con divisor propio por métrica — dividir por el total
  contaría los ausentes como cero y hundiría el promedio.
- `data/estadisticas.json`: promedios de hasta 8 partidos por equipo.

**Cuidado con el caché.** `data/cache_disciplina.json` persiste entre
corridas y los registros anteriores a este cambio tienen solo tres
campos. Si se dan por buenos, las métricas nuevas no se pueblan nunca
(el partido ya está cacheado y no se vuelve a pedir). `resumen_completo()`
los detecta y los re-pide **una sola vez**. Si ese re-pedido falla, se
sigue usando el registro viejo: sirve para los λ, y perderlo por un
error de red sería cambiar un dato bueno por ninguno.

**Lo que casi rompe el motor:** `cards` pasó a poder ser `None`, y
`disciplina_equipo()` le sumaba sin chequear. Lo agarró un test antes
de correr. Los λ dependen de esa función.

**En la app:**
- Pestaña Plantel, por jugador: se elige una estadística y la lista se
  ordena por ella. En 375px no entran ocho columnas, y además la
  pregunta real es "quién remata más acá". La columna que importa es el
  **promedio por partido**: en Aldosivi, Acevedo tiene más remates
  totales (16) pero Sosa remata más seguido (2.6 contra 1.2).
- Comparativa entre los dos equipos, enfrentada. Si falta el dato de
  uno **no se muestra nada**: enfrentar un número contra un hueco
  invita a compararlos igual.

**El límite, que hay que decirlo:** no hay cuotas de props de jugador.
ESPN no las da. Con esto se puede pronosticar un número, no decir si
una línea está mal precificada. Mientras esto sea "para ver", no
importa; si algún día se quiere marcar valor acá, lo primero es
conseguir cuotas, no más estadísticas.

---

## 7. Arquitectura de información

**Tres destinos: Fecha · Registro · Método.**

"Combinadas" **no** es un destino: el picker manual le pide al usuario
que arme algo, cuando el trabajo de la app es decirle qué hacer. La
combinada recomendada vive dentro de Pronósticos.

"Ajustes" **no** es un destino: la banca se pregunta inline en
Herramientas la primera vez que hace falta.

### Pantalla: Fecha (portada)

- Logo, slider de días, agrupado por liga, todos los partidos a la vista
  (sin acordeón: con 5-10 por día, todo entra).
- Por partido: hora, escudos + nombres, las tres cuotas, y **nuestro
  pronóstico**.
- El pronóstico **siempre existe** — no es una señal rara. Reemplaza al
  viejo "≠ Mercado", que disparaba en el 91% de los casos y no informaba
  nada.
- **La marca de valor sí es rara y va en banda.**
- Sin EV y sin monto sugerido en portada.

### Pantalla: Detalle de partido — 6 pestañas

1. **Análisis** (default) — el bloque humano en lenguaje llano: bajas,
   DT, contexto. Desde `data/analisis.json`.
2. **Pronósticos** — la lectura arriba, y debajo la escalera de riesgo.
   Cada opción con su probabilidad, su umbral de cuota, y una línea en
   castellano de cuándo se cobra ("se te paga salvo que gane Banfield").
   La combinada recomendada vive acá.
3. **Historial** — forma reciente y cruces directos.
4. **Posiciones** — tabla de la competición, con los dos equipos
   resaltados. Separada de Historial a pedido explícito de Lucas.
5. **Plantel** — la cancha con el once inferido, la lista de jugadores
   con sus estadísticas, y la comparativa de equipo (`data/planteles.json`,
   `data/estadisticas.json`). `data/equipos.json` existió con este
   propósito y se borró el 2026-08-20 sin haberse usado nunca — ver la
   sección 10.
6. **Herramientas** — explícitamente "para vos, no para la gente". Cuota
   real de tu casa → EV y stake en pesos. **La etiqueta "Kelly" no
   aparece**; el monto habla solo y el porqué está en Método.

### Pantalla: Registro

- **Marcador principal: tasa de acierto, nuestra y la del mercado, lado
  a lado.**
- Rentabilidad y CLV debajo.
- **Los resultados se resuelven solos.** Ya bajamos los marcadores de
  ESPN; pedirle al usuario que marque "Ganada/Perdida" a mano es
  fricción y es lo que hace que la gente abandone el registro a la
  semana.

### Pantalla: Método

Texto puro, sin cajas. Debe incluir: por qué probabilidad y no "va a
ganar X", por qué un umbral y no una cuota, qué es valor falso, y **cómo
nos medimos** — incluido el Brier real donde el mercado nos gana. La
transparencia es parte del producto.

---

## 8. Principio de ejecución

**El rigor va en *qué* recomendamos, nunca en lo que le exigimos
entender al usuario.**

Una cuota de 1.05 sin valor real no llega a la pantalla — no porque le
expliquemos por qué, sino porque simplemente no se muestra. La fracción
de Kelly se traduce a **énfasis editorial** ("esta la vemos clara" vs
"nos gusta, con menos convicción"), no a aritmética en pantalla.

**Postura:** seguridad en el veredicto, honestidad en el historial. La
app se la juega en cada pronóstico sin llenarse de advertencias, y por
separado muestra sin drama cuántas veces acertó.

Lucas fue explícito sobre el lenguaje: *"la gente normal no sabe lo que
es Kelly"*, y *"las apuestas suelen ser espontáneas a veces"*. El
usuario común no debe encontrarse con jerga.

---

## 9. Datos que faltan y de dónde sacarlos

Ninguno de estos se inventó en la interfaz; se dejaron como huecos
honestos.

| Falta | Dónde está | Qué hacer |
|---|---|---|
| **Estadio** | `competitions[0].venue.fullName` del scoreboard | Agregarlo en `actualizar.py` |
| **Goles en contra** | La tabla de ESPN trae `gf` pero no `gc` | Sin eso no hay diferencia de gol; mostrar G-E-P |
| **Plantel de jugadores** | `/roster`, pero las stats son un pedido por jugador (~50 por pestaña) | Bajarlo en el cron, nunca en vivo |
| **`grupo` en inglés** | ESPN devuelve `"Group B"` para todo | Traducir: "Zona" en liga local, "Grupo" en copas |

**Convención crítica de `marcador`:** en `formH`/`formA`, el primer
número es **siempre el del equipo de la fila**, no el del local.
Verificado sobre 206 partidos: 206 de 206 cierran con esta lectura, solo
109 con la otra.

---

## 10. El hueco más grande del producto — resuelto para analisis.json; equipos.json se borró (2026-08-20)

**Estado 2026-08-19:** `data/analisis.json` ya no está vacío — 12
partidos cargados, generados por la skill versionada (ver 6quinsexies).

**`data/equipos.json` se borró el 2026-08-20**, junto con el código que
lo leía en `index.html` (la variable `EQUIPOS`, su fetch, y los tres
campos `resumen`/`forma`/`localVisita`/`bajas` en la pestaña Plantel).
Nunca se cargó — quedó en `{_schema}` desde que se creó — y todo lo que
prometía terminó cubierto por otra vía, mejor: `resumen`/`forma` los
reemplaza el campo `local`/`visitante` de la skill (por partido, no
genérico); `bajas` las busca la skill y las **pesa** contra el plantel
en vez de listarlas a mano. Lo único que no tiene reemplazo es
`fichajes`, y ni eso justificaba mantener un archivo con esquema y
código de lectura sin ningún dato adentro — el riesgo real era que la
próxima IA lo viera "cargado" (con esquema) y asumiera que hacía algo.
Si algún día hace falta una ficha de equipo con identidad estable, se
diseña de cero: este archivo mezclaba cosas que caducan en días
(lesiones) con cosas que no (estilo), y por eso nadie lo mantuvo nunca.

El riesgo que motivó esta sección **se resolvió, no desapareció solo**:
la generación de `inclinacion`/`contexto`/`veredicto` ya no depende de
que Lucas escriba a mano cada partido. La hace esta misma terminal,
corriendo `.claude/skills/valor-analisis-inclinacion/SKILL.md` vía el
research (`expediente.py` + WebSearch). **Ojo con el nombre parecido:**
existe (o puede volver a existir) una skill instalada localmente como
`analisis-futbol-valor-json`, que NO es esta — esquema de salida
distinto, sin `inclinacion`, y espera como input los números del propio
modelo, lo que rompería la regla de alineación si se usara sin querer.
Antes de correr el research, confirmar el nombre exacto.

**El plantel dejó de ser un hueco el 2026-08-20.** Lo que esta sección
daba por pendiente ya está construido: el cron escribe
`data/planteles.json` (42 equipos, 1152 jugadores con `pj`, goles,
asistencias y `peso_goles`), `/roster` costó 2 requests más sobre 592, y
`expediente.py` se lo entrega a la skill. `injuries`/`status` del mismo
endpoint están
presentes en el esquema pero vacíos/no mantenidos para ligas
sudamericanas (verificado en vivo: Valentín Carboni de Racing, con
rotura de ligamento cruzado real, aparece `Active`/`[]`). Tampoco sirve
para identificar DT actual — el campo `coach` del roster es una lista
histórica vieja (verificado: devolvió a Gorosito/Cappa/Lopez/Almeyda
para River en vez de Coudet, el DT real desde marzo). Esos dos —
lesiones y DT— siguen necesitando research humano/IA, no automatizables
con esta API.

---

## 11. Cómo debería arrancar la IA nueva — en orden

**Fase 0 — Antes de escribir código**
1. Leer este documento entero.
2. Copiar del repo viejo, **sin modificar**: `actualizar.py`,
   `backtest.py`, `medir_sesgo.py`, `medir_vs_mercado.py`,
   `calibrar_ligas.py`, `data/`, `icons/`, `manifest.json`,
   `.github/workflows/actualizar.yml`.
3. Verificar que el pipeline corre: `python actualizar.py` debe
   completar sin dependencias externas.
4. Correr `python medir_vs_mercado.py` y confirmar que reproduce
   Brier ≈ 0.645 vs 0.623. **Si no reproduce, algo se rompió al copiar
   — pará y averiguá antes de seguir.**

**Fase 1 — Diseño: YA HECHA, no la repitas**
5. ~~Invocar la skill de brainstorming~~ — **ya se hizo, en Claude
   Design.** Leé `docs/design-handoff/VALOR.dc.html` y
   `docs/design-handoff/README.md` (sección 6bis explica qué es).
6. ~~Producir variantes comparadas~~ — **ya se produjeron y Lucas ya
   eligió.** No le vuelvas a pedir que elija entre direcciones de
   portada: eso ya pasó.
7. ~~Resolver el elemento firma~~ — **resuelto: la V.** Ver `DESIGN.md`.
8. El sistema de diseño (color, tipografía, espaciado, movimiento) **ya
   está escrito** en `docs/design-handoff/README.md`. Empezá por ahí,
   no lo reinventes.

Si después de leer el handoff **vos** ves algo genuinamente sin
resolver o inconsistente (como pasó con la marca — ver arriba),
mostraselo a Lucas con opciones antes de decidir solo. Pero no vuelvas a
correr el proceso completo de cero: la mayor parte del trabajo de esta
fase está terminado.

**Fase 2 — Reglas antes de pantallas**
9. ~~Portar las reglas y volver a barrerlas~~ **HECHO (2026-08-18):**
   `node barrer_valor.js`. Ver la sección 5bis — reprodujo la forma del
   barrido pero encontró un problema con el piso.
10. ~~Confirmar que el port a JavaScript da el mismo número que
    Python~~ **HECHO (2026-08-18):** `python doble_via.py`. Diferencia
    máxima **6,7e-16** sobre 476 probabilidades. El port no introdujo
    error numérico.

**Fase 3 — Interfaz: HECHA (2026-08-18)**
11. ~~Construirla pantalla por pantalla~~ **HECHO.** Las cuatro
    pantallas y las seis pestañas del detalle. Ver sección 6quater.
12. ~~Verificar en navegador~~ **HECHO:** cero errores de consola, sin
    desborde horizontal a 375px.
12bis. ~~Cambio de guardia `index.html`~~ **HECHO.** Ver 6quinquies.

**Fase 4 — Contenido: HECHA (2026-08-19/20)**
13. ~~Arreglar la skill de análisis~~ **HECHO — pero es otra skill.**
    La vieja `analisis-futbol-valor-json` quedó descartada, no
    arreglada: nació con el modelo como input, lo que viola la regla de
    alineación de raíz. La skill real es
    `.claude/skills/valor-analisis-inclinacion/SKILL.md`, versionada en
    el repo, con `expediente.py` como fuente objetiva y research propio
    (WebSearch). Ver la sección 6quinsexies.
14. ~~Cargar análisis real~~ **HECHO — 12 partidos en `data/analisis.json`.**
    La marca de valor aparece donde `inclinacion` coincide con el
    mercado. `data/equipos.json` se borró (2026-08-20): nunca se cargó
    (ver sección 10).

**Fase 5 — Modelo (opcional, con tiempo)**
15. Calibrar `rho` para copas.
16. Validar `VIDA_MEDIA_DIAS` y `PRIOR_FUERZA` con train/test.

---

## 12. Reglas de trabajo con Lucas

Salieron de esta sesión y de las anteriores. Respetarlas ahorra
fricción.

- **Español, siempre.** Commits en español explicando **el porqué**, no
  el qué.
- **Medir antes de afirmar.** El proyecto tiene historial de
  afirmaciones que resultaron falsas al chequearlas contra la API real.
- **Nunca tocar constantes del modelo para que un número dé mejor.** Si
  una medición no mejora, el hallazgo es que no mejoró.
- **Mandarle los archivos.** Si evaluás algo visual, mandale la imagen
  al chat. No se la describas.
- **Una herramienta por área.** Si va a usar otra IA en paralelo, que
  sea para algo distinto o en una rama aparte.
- **No dar por terminado sin verificar en navegador.**
- Lucas pregunta seguido "¿vamos bien?" y espera una respuesta honesta
  con lo bueno **y** lo que falta, no un informe de logros.
