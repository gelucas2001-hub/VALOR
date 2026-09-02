#!/usr/bin/env python3
"""Las líneas de JUGADOR contra PLATA, al precio real de Bet365.

Por qué existe, y por qué es el hueco más grande del proyecto:

`medir_jugadores.py` mide si las líneas de jugador están **calibradas**
—y ya dijo que remates se desvía 2.09 veces el ruido, al arco 1.59, y
goles y asistencias están bien—. Pero calibrar no es ganar plata, y esa
confusión ya costó tres semanas en el eje de Resultado (TRASPASO §5).
Contra dinero, este mercado **nunca se midió**.

Y es el mercado más blando al que llegamos: nadie en Bet365 le dedica a
"remates de Almada en Liga Profesional" el esfuerzo que le dedica al
1X2 de Premier. Si hay ventaja en algún lado, es acá — o en ningún
lado, y saberlo también sirve.

Lo que hace posible medirlo, y no es obvio:

`data/props_jugadores.json` no guarda la línea sola: guarda **la
escalera de precios entera** (1.5 → 1.02, 2.5 → 1.10, … 10.5 → 21.0) y
**varias fotos por partido**. O sea que hay precio real para calcular
ROI, y hay movimiento de línea para calcular CLV — que es el
instrumento que concluye rápido: en el 1X2 el CLV cerró con 362
apuestas mientras el ROI seguía en ±14.

El cruce de nombres, que es la parte peligrosa:

Bet365 escribe "Lucas Beltran" y ESPN "Lucas Beltrán". El cruce es
**solo por igualdad exacta después de normalizar**, nunca por parecido
— regla dura de CLAUDE.md. Y acá hay una razón extra para no aflojarla:
mirando los que no cruzan se ve que "Clever Ferreira" y "Pablo
Ferreira", o "Wesley Fofana" y "Malick Fofana", son **personas
distintas**. Un cruce difuso les fundiría la historia y el resultado no
se vería como un error: se vería como datos.

Encima del cruce exacto hay un segundo candado: el id que salga tiene
que **haber jugado ese partido**. Un jugador que no jugó anula la
apuesta en la vida real, así que dejarlo afuera no es un descarte, es
la regla del mercado.

    python medir_props.py
    python medir_props.py --umbral 0.05
"""

import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent

PROPS = RAIZ / "data" / "props_jugadores.json"
PLANTELES = RAIZ / "data" / "planteles.json"

# Las dos métricas que Bet365 publica por jugador.
METRICAS = ("remates", "al_arco")

# Ventanas de ventaja a probar. La apuesta se marca cuando la ventaja
# esperada cae adentro: el piso saca el ruido, el techo saca lo que solo
# puede venir de un error nuestro (una ventaja del 40% contra una casa
# no es una ventaja, es una línea que leímos mal).
UMBRAL_MIN = 0.04
UMBRAL_MAX = 0.25


def norma(s):
    """Sin acentos, sin apóstrofos, sin guiones, en minúscula.

    No hace nada más. Todo lo que se le agregue a esta función es una
    forma nueva de fundir dos jugadores distintos.
    """
    s = unicodedata.normalize("NFD", str(s)).lower()
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.replace("'", " ").replace("-", " ").split())


def indice_jugadores(planteles):
    """{nombre normalizado: id de ESPN}, solo los nombres INEQUÍVOCOS.

    Si dos jugadores reclaman el mismo nombre normalizado, ese nombre
    queda **afuera** del índice en vez de irse con el último que pasó.
    Es la misma decisión que toma `equipos.py` con Paris SG y Paris FC.
    """
    por_nombre = defaultdict(set)
    for js in (planteles or {}).values():
        for j in js or []:
            if j.get("nombre") and j.get("id"):
                por_nombre[norma(j["nombre"])].add(str(j["id"]))
    return {n: next(iter(v)) for n, v in por_nombre.items() if len(v) == 1}


def series_props(props):
    """{(evento, metrica, nombre): [fotos ordenadas por hora]}."""
    salida = {}
    for clave, fotos in (props or {}).items():
        partes = clave.split("__", 2)
        if len(partes) != 3 or not fotos:
            continue
        ev, met, nombre = partes
        salida[(ev.replace("espn", ""), met, nombre)] = sorted(
            fotos, key=lambda f: f.get("t") or "")
    return salida


def escalera(foto):
    """[(linea, precio)] ordenada, descartando lo que no es número."""
    out = []
    for ln, precio in (foto.get("lineas") or {}).items():
        try:
            out.append((float(ln), float(precio)))
        except (TypeError, ValueError):
            continue
    return sorted(out)


def historia(series, sin_red=False):
    """[(fecha, event_id, {pid: fila})] de los partidos ya jugados.

    `medir_jugadores.historia()` saca las fechas de `_fechas_conocidas`,
    que sin red solo conoce los partidos que FALTAN jugar — o sea justo
    los que no sirven. Acá se le suman las fechas que trae el propio
    `props_jugadores.json`: cada foto guarda la fecha del partido, y son
    exactamente los partidos que importan para esta medición. Con eso el
    script corre sin red sobre los partidos con props, y con red suma
    todos los demás, que son los que alimentan la serie previa.
    """
    import medir_jugadores as J
    import medir_lineas as L

    disc = json.loads(J.DISCIPLINA.read_text(encoding="utf-8")) \
        if J.DISCIPLINA.exists() else {}
    fechas = L._fechas_conocidas(sin_red=sin_red)
    for (ev, _met, _nombre), fotos in (series or {}).items():
        f = (fotos[0] or {}).get("fecha")
        if f:
            fechas.setdefault(str(ev), f[:10])
    out = []
    for eid, v in disc.items():
        jg = (v or {}).get("_jugadores")
        f = fechas.get(str(eid))
        if jg and f:
            out.append((f, str(eid), jg))
    out.sort()
    return out


def candidatas(historia, series, indice, pos_de=None):
    """Una fila por escalón de precio, con lo que sabíamos ANTES.

    Mismo recorrido que `medir_jugadores.evaluar()`: los parámetros por
    puesto se calculan con los partidos previos, nunca con el que se
    está evaluando. La diferencia es que acá cada jugador no aporta una
    línea sino toda la escalera de la casa.
    """
    import actualizar as A
    import medir_jugadores as J
    import medir_lineas as L

    pos_de = J._posiciones() if pos_de is None else pos_de
    acumulado = defaultdict(list)
    filas = []

    for fecha, eid, jugadores in historia:
        # Parámetros por puesto con lo anterior, igual que el pipeline.
        por_pos = {}
        for pid, serie in acumulado.items():
            p = pos_de.get(pid)
            if not p or len(serie) < J.MINIMO:
                continue
            for m in METRICAS:
                (por_pos.setdefault(p, {}).setdefault(m, {})
                 [pid]) = J.valores(serie[-A.SERIE_N:], m)
        par_pos = {}
        for p, muestras in por_pos.items():
            pr = A.parametros_metricas(muestras)
            if pr:
                par_pos[p] = pr

        for (ev, met, nombre), fotos in series.items():
            if ev != str(eid) or met not in METRICAS:
                continue
            pid = indice.get(norma(nombre))
            # Los dos candados: nombre inequívoco, y que haya jugado.
            if not pid or pid not in jugadores:
                continue
            serie = acumulado.get(pid) or []
            if len(serie) < J.MINIMO:
                continue
            par = (par_pos.get(pos_de.get(pid)) or {}).get(met)
            if not par or not par.get("disp"):
                continue
            vals = J.valores(serie[-A.SERIE_N:], met)
            mu = J.esperado(vals, par)
            if mu is None:
                continue
            real = float(jugadores[pid][J._IDX[met]])
            abre, cierra = escalera(fotos[0]), dict(escalera(fotos[-1]))
            for linea, precio in abre:
                p = L.prob_mayor(mu, par["disp"], linea)
                if p is None or precio <= 1:
                    continue
                filas.append({
                    "fecha": fecha, "ev": ev, "pid": pid, "met": met,
                    "linea": linea, "precio": precio,
                    "cierre": cierra.get(linea),
                    "p": p, "ev_esperado": p * precio - 1,
                    "paso": 1 if real > linea else 0,
                })

        for pid, fila in jugadores.items():
            acumulado[pid].append(fila)

    return filas


def roi(filas, umbral=UMBRAL_MIN, techo=UMBRAL_MAX):
    """ROI de apostar el over cuando la ventaja cae en la ventana."""
    jugadas = [f for f in filas if umbral <= f["ev_esperado"] <= techo]
    if not jugadas:
        return None
    ganancias = [(f["precio"] - 1) if f["paso"] else -1.0 for f in jugadas]
    n = len(ganancias)
    media = sum(ganancias) / n
    var = sum((g - media) ** 2 for g in ganancias) / n if n > 1 else 0.0
    return {"n": n, "roi": media * 100,
            "ee": (var / n) ** 0.5 * 100 if n else 0.0,
            "aciertos": sum(f["paso"] for f in jugadas) / n * 100}


def _dos_escalas(jugadas):
    """El movimiento de precio medido en las dos escalas, y por qué hay dos.

    La original es el cociente, `precio/cierre - 1`. Es la intuitiva
    —"la cuota bajó un 10%"— y es **asimétrica**: hacia arriba no tiene
    techo y hacia abajo está acotada en -100%. Con cuotas largas adentro
    eso no es un detalle. El 2026-09-02, con 96 apuestas, una sola línea
    que fue de 13.00 a 3.50 (+271%) movió el promedio de +3.32% a +6.11%
    y cuadruplicó el error estándar: la significancia contra la deriva
    CAYÓ de 2.6 a 1.5 errores estándar sin que la señal se hubiera
    movido. Un número que empeora porque apareció un acierto grande no
    está midiendo lo que dice medir.

    La segunda es la diferencia de probabilidad implícita,
    `1/cierre - 1/precio`, en puntos porcentuales. Dice lo mismo
    —positivo es que la línea se movió hacia nosotros— pero es simétrica
    y está acotada de los dos lados, así que ninguna cuota larga sola
    puede dominarla.

    Se devuelven las dos: `pp` es la buena y es la que manda en pantalla,
    `clv` queda para poder comparar contra los números ya publicados en
    TRASPASO §22.
    """
    ratios = [f["precio"] / f["cierre"] - 1 for f in jugadas]
    pps = [1 / f["cierre"] - 1 / f["precio"] for f in jugadas]
    n = len(ratios)

    def resumen(vs):
        media = sum(vs) / n
        var = sum((v - media) ** 2 for v in vs) / n if n > 1 else 0.0
        return media * 100, (var / n) ** 0.5 * 100

    clv_r, ee_r = resumen(ratios)
    clv_p, ee_p = resumen(pps)
    return {"n": n, "clv": clv_r, "ee": ee_r, "pp": clv_p, "ee_pp": ee_p}


def deriva(filas):
    """El CLV de TODOS los escalones, elijamos o no la apuesta.

    Es la vara del CLV y sin ella el número no dice nada. Si la casa
    achica el margen a medida que se acerca el partido, **todos** los
    precios bajan y cualquier selección muestra CLV positivo sin haber
    elegido bien. Lo que dice si elegimos bien es la DIFERENCIA entre el
    CLV de lo que apostamos y esta deriva de fondo.

    Es la misma disciplina que el resto del repo: comparar contra la
    tasa base, no contra cero.
    """
    con_cierre = [f for f in filas if f.get("cierre") and f["cierre"] > 1]
    if not con_cierre:
        return None
    return _dos_escalas(con_cierre)


def dejar_uno_afuera(filas, umbral=UMBRAL_MIN, techo=UMBRAL_MAX):
    """El CLV recalculado sacando un partido por vez.

    Existe porque el 2026-08-31 el CLV daba +4.28% sobre la deriva, dos
    errores estándar, y parecía la primera señal positiva del proyecto.
    Sacando UN partido caía a +0.17%: cinco apuestas de un solo evento
    sostenían todo. El error estándar no lo detectaba porque asume que
    las apuestas son independientes, y las de un mismo partido no lo
    son — comparten equipos, hora y quién movió esa pizarra.

    Con pocos partidos, esto dice más que el intervalo. Si el número se
    desarma al sacar uno, no hay señal: hay un partido.
    """
    evs = sorted({f["ev"] for f in filas})
    out = []
    for e in evs:
        resto = [f for f in filas if f["ev"] != e]
        c, d = clv(resto, umbral, techo), deriva(resto)
        if c:
            out.append({"sin": e, "n": c["n"], "clv": c["clv"], "pp": c["pp"],
                        "dif": c["pp"] - d["pp"] if d else None})
    return out


def sin_movimiento(filas, umbral=UMBRAL_MIN, techo=UMBRAL_MAX):
    """Qué fracción de las apuestas tiene la línea CLAVADA entre fotos.

    Si la casa no movió el precio entre nuestra primera foto y la
    última, el CLV de esa apuesta es cero por construcción y no aporta
    información: el instrumento no está midiendo nada ahí. Con las fotos
    de hoy —dos por día, ninguna pegada al inicio— eso pasa en la
    mayoría de los casos, y conviene verlo antes de leer el promedio.
    """
    jugadas = [f for f in filas
               if umbral <= f["ev_esperado"] <= techo
               and f.get("cierre") and f["cierre"] > 1]
    if not jugadas:
        return None
    quietas = sum(1 for f in jugadas if abs(f["precio"] - f["cierre"]) < 1e-9)
    return {"n": len(jugadas), "quietas": quietas,
            "pct": quietas / len(jugadas) * 100}


def clv(filas, umbral=UMBRAL_MIN, techo=UMBRAL_MAX):
    """¿La línea se movió hacia nosotros entre la primera foto y la última?

    Apostamos a `precio`; si al cierre esa misma línea paga MENOS, el
    mercado se movió hacia nuestro lado. Es lo único que dice si hay
    ventaja sin esperar cientos de apuestas.
    """
    jugadas = [f for f in filas
               if umbral <= f["ev_esperado"] <= techo
               and f.get("cierre") and f["cierre"] > 1]
    if not jugadas:
        return None
    return _dos_escalas(jugadas)


def main(argv):
    import medir_jugadores as J

    umbral = UMBRAL_MIN
    if "--umbral" in argv:
        umbral = float(argv[argv.index("--umbral") + 1])

    props = json.loads(PROPS.read_text(encoding="utf-8")) if PROPS.exists() else {}
    plant = json.loads(PLANTELES.read_text(encoding="utf-8")) if PLANTELES.exists() else {}
    indice = indice_jugadores(plant.get("equipos") or {})
    series = series_props(props)
    hist = historia(series, sin_red="--sin-red" in argv)

    print("\n  LÍNEAS DE JUGADOR CONTRA PLATA — precio real de Bet365\n")
    print(f"  {len(series)} series de props · {len(indice)} nombres inequívocos "
          f"en ESPN · {len(hist)} partidos resueltos")

    filas = candidatas(hist, series, indice)
    if not filas:
        print("\n  Sin apuestas candidatas: no cruzó ningún partido con "
              "props, resultado y serie previa suficiente.\n")
        return 1

    evs = sorted({f["ev"] for f in filas})
    print(f"  {len(filas)} escalones evaluados en {len(evs)} partidos\n")

    print(f"  {'umbral':>7} {'apuestas':>9} {'aciertos':>9} {'ROI':>9} {'e.e.':>8} "
          f"{'CLV pp':>9} {'e.e.':>8}")
    print("  " + "-" * 64)
    for u in (0.02, 0.04, 0.06, 0.10, 0.15):
        r, c = roi(filas, u), clv(filas, u)
        if not r:
            continue
        cs = f"{c['pp']:+8.2f}  {c['ee_pp']:7.2f}" if c else "       —        "
        print(f"  {u*100:6.0f}% {r['n']:9d} {r['aciertos']:8.1f}% "
              f"{r['roi']:+8.2f}% {r['ee']:7.2f} {cs}")

    print(f"\n  por métrica, con umbral {umbral*100:.0f}%\n")
    for m in METRICAS:
        sub = [f for f in filas if f["met"] == m]
        r, c = roi(sub, umbral), clv(sub, umbral)
        if not r:
            print(f"    {m:10} sin apuestas en esta ventana")
            continue
        cs = (f"CLV {c['pp']:+.2f} pp ±{c['ee_pp']:.2f}" if c
              else "CLV sin dos fotos")
        print(f"    {m:10} {r['n']:5d} apuestas · ROI {r['roi']:+7.2f}% "
              f"±{r['ee']:.2f} · {cs}")

    d, c = deriva(filas), clv(filas, umbral)
    if d:
        print("\n  la vara del CLV: la deriva de TODOS los escalones\n")
        print(f"    {d['n']} escalones sin elegir · {d['pp']:+.2f} pp ±{d['ee_pp']:.2f}")
        if c:
            dif = c["pp"] - d["pp"]
            ee = (c["ee_pp"] ** 2 + d["ee_pp"] ** 2) ** 0.5
            print(f"    los {c['n']} que apostaríamos  · {c['pp']:+.2f} pp ±{c['ee_pp']:.2f}")
            if ee:
                print(f"\n    elegimos mejor por {dif:+.2f} pp ±{ee:.2f} "
                      f"({abs(dif)/ee:.1f} e.e.)")
            print("\n    en la escala vieja del cociente, para poder comparar")
            print(f"    contra TRASPASO §22: elegidas {c['clv']:+.2f}% ±{c['ee']:.2f}"
                  f" · deriva {d['clv']:+.2f}% ±{d['ee']:.2f}")
        print("\n    Si esa diferencia no se despega de cero, el CLV de arriba")
        print("    es la casa achicando el margen sobre la hora — no nosotros")
        print("    eligiendo bien.")

    q = sin_movimiento(filas, umbral)
    if q:
        print(f"\n  de esas {q['n']} apuestas, {q['quietas']} tienen la línea "
              f"CLAVADA ({q['pct']:.0f}%):")
        print("  ahí el CLV es cero por construcción y no mide nada.")

    fuera = dejar_uno_afuera(filas, umbral)
    if len(fuera) > 2:
        print("\n  dejando UN partido afuera por vez:\n")
        for f in fuera:
            ds = f"{f['dif']:+.2f} pp" if f["dif"] is not None else "—"
            print(f"    sin {f['sin']}: {f['n']:4d} apuestas · "
                  f"CLV {f['pp']:+.2f} pp · sobre su deriva {ds}")
        peor = min(fuera, key=lambda f: f["dif"] if f["dif"] is not None else f["pp"])
        peor_v = peor["dif"] if peor["dif"] is not None else peor["pp"]
        print(f"\n    El peor caso deja la diferencia en {peor_v:+.2f} pp. Si ahí se")
        print("    desarma, no hay señal: hay un partido. El error estándar no")
        print("    lo ve porque asume apuestas independientes, y las de un")
        print("    mismo partido no lo son.")

    print("\n  El ROI es al precio REAL, con el margen de la casa adentro:")
    print("  no se le quita nada. Con esta muestra el ROI casi seguro no")
    print("  concluye; el CLV concluye antes, y si da negativo cierra el")
    print("  tema sin esperar mil apuestas.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
