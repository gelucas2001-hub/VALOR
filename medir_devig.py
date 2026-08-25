#!/usr/bin/env python3
"""¿Qué método de quitar el margen de la casa acierta?

Una cuota no es una probabilidad. Las tres del 1X2 suman más de 1, y esa
diferencia es la ganancia de la casa. Para comparar el modelo contra el
mercado hay que sacarle ese margen — y **cómo** se lo sacás cambia el
número contra el que después se mide todo: el EV, la marca dorada, el
CLV, el Brier contra el mercado.

Por qué existe:

El 2026-08-25 se encontró que el repo usaba dos métodos a la vez.
`medir_clv.py` y `medir_historico.py` usaban Shin (1993); `index.html`
—lo que ve el usuario, y lo que decide si un partido lleva marca de
valor— usaba el proporcional. O sea que se medía el modelo con una vara
y se marcaba valor con otra.

Salió de leer "Using the Wisdom of the Crowd to Find Value in a Football
Match Betting Market", de Joseph Buchdahl: gratis y legal en
football-data.co.uk, el mismo sitio del que `historico.py` ya baja los
datos. Buchdahl dedica varias páginas a mostrar que repartir el margen
parejo entre las tres opciones está mal, porque las casas le cargan más
margen a las cuotas altas.

Cómo se decide, que es lo que hace honesta a la medición:

Las cuotas de cierre son la mejor estimación disponible de la
probabilidad real. Si les sacamos el margen de dos maneras distintas y
comparamos cuál queda más cerca de lo que efectivamente pasó, eso
contesta cuál método está bien. No hay ajuste de por medio: la `z` de
Shin sale de las cuotas del propio partido, nunca del resultado, así
que no hay forma de filtrar futuro al pasado.

El error se mide **contra el ruido binomial, no contra cero**: en el
tramo de cuotas altas hay 56 casos, y con 56 monedas la frecuencia
observada se aparta varios puntos por puro azar.

    python medir_devig.py

Resultado medido el 2026-08-25 sobre 11.854 partidos de Argentina y
Brasil, de 2012 a 2026:

- con cuotas de Pinnacle (margen 3.1%): Shin le erra menos (6.28 contra
  7.84 unidades de ruido);
- con el promedio del mercado (margen 6.9%, parecido al 7.7% de
  DraftKings que usa la app): Shin le erra **la mitad** (6.18 contra
  11.21).

El patrón es el que importa: cuando el margen sube, el error del
proporcional casi se duplica y el de Shin no se mueve. La app trabaja
con cuotas de DraftKings, que es la condición donde el proporcional es
peor.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import historico as H
import medir_clv as C

# Los dos métodos, tomados de donde ya viven. No se reimplementan acá:
# si se separan de los que usa el resto del repo, esto deja de medir lo
# que el repo hace.
devig_proporcional = C.devig
devig_shin = C.devig_shin

# Tramos de cuota. Los bordes están donde la muestra alcanza para que la
# frecuencia observada signifique algo; el último junta todo lo raro.
CORTES = [(1.0, 1.5), (1.5, 2.2), (2.2, 3.2), (3.2, 4.5),
          (4.5, 7.0), (7.0, 15.0), (15.0, 999)]

# Debajo de esto un tramo no dice nada y no se reporta.
MINIMO = 30


def ruido_binomial(p, n):
    """Cuánto se mueve una frecuencia observada por puro azar.

    Es la vara contra la que se compara el error. Sin esto, un tramo con
    56 casos parece roto siempre: 56 monedas no salen mitad y mitad.
    """
    if not n or n <= 0:
        return None
    return math.sqrt(max(p * (1 - p), 0.0) / n)


def acumular(partidos, lo, hi):
    """Lo que dijo cada método y lo que pasó, en un tramo de cuota.

    Cada partido aporta hasta tres casos (local, empate, visita), y cada
    uno cae en el tramo de SU propia cuota. El orden de las
    probabilidades y el de los resultados es el mismo — [local, empate,
    visita] — y ahí está el cuidado: si se cruzan, el favorito parece
    perder siempre y la conclusión se da vuelta entera.
    """
    tot = {"n": 0, "obs": 0, "prop": 0.0, "shin": 0.0}
    for p in partidos or []:
        cuotas = p.get("cuotas")
        if not cuotas:
            continue
        a = devig_proporcional(cuotas)
        b = devig_shin(cuotas)
        if not a or not b:
            continue
        real = H.desenlace(p)
        for i in range(3):
            if lo <= cuotas[i] < hi:
                tot["n"] += 1
                tot["obs"] += real[i]
                tot["prop"] += a[i]
                tot["shin"] += b[i]
    return tot


def resumen_tramo(tot):
    """El error de cada método en un tramo, en unidades de ruido."""
    n = (tot or {}).get("n") or 0
    if n <= 0:
        return None
    real = tot["obs"] / n
    prop = tot["prop"] / n
    shin = tot["shin"] / n
    ruido = ruido_binomial(real, n)
    if not ruido:
        return None
    ep = abs(prop - real) / ruido
    es = abs(shin - real) / ruido
    return {"n": n, "real": real, "prop": prop, "shin": shin,
            "ruido": ruido, "err_prop": ep, "err_shin": es,
            "gana": "shin" if es < ep else "prop"}


def comparar(partidos, cortes=None):
    """El veredicto: sumando todos los tramos, cuál le erra menos."""
    if not partidos:
        return None
    tramos = []
    for lo, hi in (cortes or CORTES):
        r = resumen_tramo(acumular(partidos, lo, hi))
        if r and r["n"] >= (MINIMO if cortes is None else 1):
            r["lo"], r["hi"] = lo, hi
            tramos.append(r)
    if not tramos:
        return None
    tp = sum(t["err_prop"] for t in tramos)
    ts = sum(t["err_shin"] for t in tramos)
    return {"tramos": tramos, "total_prop": tp, "total_shin": ts,
            "gana": "shin" if ts < tp else "prop"}


def cargar(fuentes):
    """Partidos con cuota de cierre de una fuente puntual."""
    original = H.FUENTES
    H.FUENTES = fuentes
    try:
        out = []
        for liga in H.LIGAS:
            out += [p for p in H.normalizar(H.bajar(liga)) if p.get("cuotas")]
        return out
    finally:
        H.FUENTES = original


def margen_medio(partidos):
    if not partidos:
        return None
    return sum(sum(1.0 / c for c in p["cuotas"]) - 1.0
               for p in partidos) / len(partidos)


def informe(partidos, etiqueta):
    m = margen_medio(partidos)
    print(f"\n{'='*74}")
    print(f"  {etiqueta}")
    print(f"  {len(partidos)} partidos · margen medio del libro: {m*100:.2f}%")
    print(f"{'='*74}")
    c = comparar(partidos)
    if not c:
        print("  sin muestra.")
        return None
    print(f"  {'cuota':>13} {'casos':>6} {'prop':>7} {'shin':>7} {'REAL':>7} "
          f"{'ruido':>6} {'e.prop':>7} {'e.shin':>7}")
    for t in c["tramos"]:
        print(f"  {t['lo']:5.1f}-{t['hi']:6.1f} {t['n']:6} "
              f"{t['prop']*100:6.2f}% {t['shin']*100:6.2f}% {t['real']*100:6.2f}% "
              f"{t['ruido']*100:5.2f}% {t['err_prop']:7.2f} {t['err_shin']:7.2f}"
              f"   <- {t['gana']}")
    print(f"\n  error total (unidades de ruido):  "
          f"proporcional={c['total_prop']:.2f}   shin={c['total_shin']:.2f}")
    print(f"  gana: {'SHIN' if c['gana']=='shin' else 'PROPORCIONAL'}")
    return c


def separacion(partidos):
    """Cuánto se mueve la probabilidad de mercado al cambiar de método.

    Importa porque la `ventaja` de la app es una resta directa contra
    esta probabilidad, y la marca dorada se enciende a los 6 puntos. Un
    corrimiento de un punto no es cosmético a esa escala.
    """
    difs = []
    for p in partidos or []:
        a, b = devig_proporcional(p["cuotas"]), devig_shin(p["cuotas"])
        if a and b:
            difs += [abs(x - y) for x, y in zip(a, b)]
    if not difs:
        return None
    difs.sort()
    n = len(difs)
    return {"media": sum(difs) / n, "p95": difs[int(n * 0.95)],
            "max": difs[-1], "sobre_1pp": sum(1 for d in difs if d > 0.01) / n}


def main():
    for etiqueta, fuentes in (
            ("PINNACLE — la referencia de la industria, margen bajo",
             (("pinnacle", "PSC"),)),
            ("PROMEDIO DEL MERCADO — margen alto, como el DraftKings que usa la app",
             (("promedio", "AvgC"),))):
        partidos = cargar(fuentes)
        if not partidos:
            continue
        informe(partidos, etiqueta)
        s = separacion(partidos)
        if s:
            print(f"\n  cuánto se mueve la probabilidad de mercado al cambiar de método:")
            print(f"    media {s['media']*100:.2f} pp · p95 {s['p95']*100:.2f} pp · "
                  f"máx {s['max']*100:.2f} pp")
            print(f"    se mueve más de 1 punto en el {s['sobre_1pp']*100:.1f}% de los casos")

    print(f"\n{'='*74}")
    print("  El umbral de la marca dorada es 6 puntos (VALOR_MIN). A esa")
    print("  escala, el método de devig no es un detalle de implementación.")
    print(f"{'='*74}\n")


if __name__ == "__main__":
    main()
