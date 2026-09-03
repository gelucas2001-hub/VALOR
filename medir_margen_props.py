#!/usr/bin/env python3
"""Cuanto margen cobra Bet365 en la escalera de jugador. El paso 0.

Antes de construir un simulador para combinadas hay que saber si queda
espacio: si el margen de las patas se come cualquier ventaja realista,
no hay nada que construir. Lucas lo pidio asi y es la pregunta correcta.

La escalera es de un solo lado —solo "mas de N"— asi que el margen no se
puede sacar sumando las dos caras. Se saca comparando la probabilidad
implicita del precio contra la frecuencia REAL con que paso.

EL POOL IMPORTA, Y MUCHO

Bet365 cotiza ~50 jugadores por partido, y el 30% de los cotizados NO
terminan siendo titulares. Apostar la escalera entera pierde 53%: un
tercio de eso es que se le apuesta a gente que no juega, no margen. Por
eso se mide SOLO TITULARES, que es la unica comparacion honesta.

RESULTADO (2026-09-03, 3583 escalones, de los cuales 2596 de titulares)

    metrica  linea     n   precio  implicita    real   sobreprecio
    al_arco    0.5   361     3.11      40.8%   27.1%     +13.6 pp
    remates    0.5   347     1.51      71.9%   60.2%     +11.7 pp
    remates    1.5   361     3.36      45.7%   33.2%     +12.4 pp
    remates    2.5   347     7.73      28.3%   16.7%     +11.6 pp
    remates    3.5   262    10.08      21.3%   13.0%      +8.3 pp

Diez a doce puntos de probabilidad en cada escalon. Sobre una base del
30% eso es ~35% de margen relativo.

LA COMPARACION QUE DECIDE

    margen de la casa      +10 a +12 pp
    nuestra ventaja        +1.15 pp de CLV (TRASPASO §22bis)

Un decimo. Y una combinada de dos patas multiplica el margen, no lo
divide: se verifico sobre boletas reales que la cuota combinada es el
producto exacto de las patas (9.01 = 1.75x1.62x1.70x1.87).

EL REPARO QUE PODRIA SALVARLO, Y NO SE PUEDE RESOLVER

El "real" sale de los remates que cuenta ESPN. Si ESPN cuenta menos que
la fuente con la que Bet365 liquida (Opta cuenta los remates bloqueados,
por ejemplo), parte de ese sobreprecio es error de medicion y no margen.
Que el 0.5 de remates de un titular de por 60% y no ~72% empuja en esa
direccion.

No se puede separar sin datos de liquidacion. O sea que la conclusion
honesta es doble: el margen parece diez veces nuestra ventaja, Y no
podemos medir nuestra ventaja real en este mercado con los datos que
tenemos. Las dos llevan al mismo lado.

Ojo: el CLV de §22bis NO depende de esto. Compara precio contra cierre y
no mira resultados, asi que sigue en pie. Lo que queda en duda son los
ROI de medir_props.py.

    python medir_margen_props.py
"""
import json
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_props as M


def main():
    props = json.loads(M.PROPS.read_text(encoding="utf-8"))
    plant = json.loads(M.PLANTELES.read_text(encoding="utf-8"))
    series = M.series_props(props)
    hist = M.historia(series)
    filas = M.candidatas(hist, series, M.indice_jugadores(plant.get("equipos") or {}))
    tit = {}
    for _f, eid, jug in hist:
        for pid, x in jug.items():
            tit[(str(eid), pid)] = len(x) > 6 and bool(x[6])

    def roi(g):
        v = [(x["precio"] - 1) if x["paso"] else -1.0 for x in g]
        n = len(v); m = sum(v) / n
        return m * 100, (sum((y - m) ** 2 for y in v) / n / n) ** 0.5 * 100, n

    print("\n  MARGEN DE LA ESCALERA DE JUGADOR — Bet365\n")
    for et, g in (("toda la escalera", filas),
                  ("solo titulares", [f for f in filas if tit.get((str(f["ev"]), f["pid"]))]),
                  ("los que no arrancaron", [f for f in filas
                                             if not tit.get((str(f["ev"]), f["pid"]))])):
        if len(g) < 30:
            continue
        r, ee, n = roi(g)
        print(f"  apostar ciego · {et:>22} {n:>5} · ROI {r:>+8.2f}% ±{ee:.2f}")

    print(f"\n  {'metrica':>9} {'linea':>6} {'n':>5} {'precio':>8} "
          f"{'implicita':>10} {'real':>7} {'sobreprecio':>12}")
    por = {}
    for f in filas:
        if tit.get((str(f["ev"]), f["pid"])):
            por.setdefault((f["met"], f["linea"]), []).append(f)
    sobre = []
    for (met, ln), g in sorted(por.items()):
        if len(g) < 60:
            continue
        imp = st.mean(1 / x["precio"] for x in g)
        real = st.mean(x["paso"] for x in g)
        sobre.append(imp - real)
        print(f"  {met:>9} {ln:>6} {len(g):>5} {st.mean(x['precio'] for x in g):>8.2f} "
              f"{imp*100:>9.1f}% {real*100:>6.1f}% {(imp-real)*100:>+11.1f} pp")
    if sobre:
        print(f"\n  sobreprecio medio: {st.mean(sobre)*100:+.1f} pp")
        print(f"  nuestra ventaja medida (§22bis): +1.15 pp de CLV")
        print(f"  razon: la casa cobra {st.mean(sobre)/0.0115:.0f} veces lo que ganamos\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
