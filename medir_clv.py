#!/usr/bin/env python3
"""CLV — ¿la línea se mueve hacia nosotros?

Por qué existe:

Se midió que el modelo captura el 44% de lo que sabe el mercado (289
partidos contra la cuota de cierre real). Con eso, esperar a que los
resultados digan si hay ventaja tarda cientos de apuestas, y para
entonces ya perdiste la plata averiguándolo.

El CLV contesta mucho más rápido. La idea: si nuestro modelo sabe algo
que el mercado todavía no puso en el precio, entonces cuando le
discrepamos a la cuota, la cuota debería MOVERSE hacia nosotros antes
del inicio. Si eso pasa de forma sostenida, hay ventaja aunque la
apuesta puntual se pierda. Si no pasa, no la hay aunque ganes.

Cómo se junta el dato:

ESPN BORRA el bloque de cuotas cuando el partido termina — verificado
el 2026-08-23 sobre 11 partidos ya jugados de arg.1: ninguno lo
conservaba. Por eso no se puede medir hacia atrás. `actualizar.py` va
guardando una foto en cada corrida (data/cuotas.json), y la última
antes del inicio es la de cierre.

O sea que este script no tiene nada que decir hasta que pasen unas
cuantas fechas. Eso es lo esperable, no un error.

    python medir_clv.py
"""

import json
import sys
from math import comb
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import backtest        # la matriz Dixon-Coles ya validada; no se reescribe

RAIZ = Path(__file__).resolve().parent
CUOTAS = RAIZ / "data" / "cuotas.json"

# Cuántos casos hacen falta para arriesgar un veredicto.
MIN_CASOS = 30

# Debajo de esto, el azar no lo explica solo.
UMBRAL = 0.05

# Discrepancias más chicas que esto son ruido de redondeo, no una
# opinión: no aportan dirección, así que no se cuentan.
MIN_DISCREPANCIA = 0.02


def devig(cuotas):
    """Probabilidades justas a partir de las cuotas de un mercado.

    Una cuota no es una probabilidad: las tres del 1X2 suman más de 1, y
    ahí vive la ganancia de la casa. Comparar el modelo contra la
    probabilidad implícita SIN sacar el margen está sesgado a nuestro
    favor, porque cualquier cuota parece generosa.
    """
    if not cuotas or any(not c or c <= 0 for c in cuotas):
        return None
    inv = [1.0 / c for c in cuotas]
    tot = sum(inv)
    if tot <= 0:
        return None
    return [x / tot for x in inv]


def devig_shin(cuotas, tol=1e-12):
    """Probabilidades justas por el metodo de Shin (1993).

    El devig proporcional le saca el mismo porcentaje a todas las
    opciones. Shin parte de que el margen existe porque la casa se cubre
    de apostadores informados, y de ahi sale que hay que sacarle
    proporcionalmente MAS al que paga mucho. Corrige el sesgo
    favorito-longshot: la probabilidad implicita de un batacazo esta
    sistematicamente inflada si se reparte el margen parejo.

    Se resuelve `z` (la proporcion de dinero informado) por biseccion y
    no con scipy: el repo es de biblioteca estandar. La suma es monotona
    decreciente en z, asi que bisecar es exacto y sin dependencias.
    """
    if not cuotas or any(not c or c <= 0 for c in cuotas):
        return None
    raw = [1.0 / c for c in cuotas]
    libro = sum(raw)
    # Sin margen (o mercado de dos vias) Shin no tiene nada que corregir.
    if len(cuotas) < 3 or libro <= 1.0:
        return [x / libro for x in raw]

    def probs(z):
        if z >= 1.0:
            return raw
        return [((z * z + 4 * (1 - z) * r * r / libro) ** 0.5 - z) / (2 * (1 - z))
                for r in raw]

    lo, hi = 0.0, 0.99
    # f(0) = sqrt(libro) - 1 > 0 y decrece con z: la raiz esta en medio.
    for _ in range(200):
        med = (lo + hi) / 2
        if sum(probs(med)) - 1.0 > 0:
            lo = med
        else:
            hi = med
        if hi - lo < tol:
            break
    p = probs((lo + hi) / 2)
    tot = sum(p)
    return [x / tot for x in p] if tot > 0 else None


def _probs_modelo(foto):
    """Lo que decía el modelo en el momento de esa foto."""
    m = backtest.matriz(foto["lh"], foto["la"], foto.get("rho") or 0.0)
    linea = foto.get("totalLinea")
    over = (backtest.suma_si(m, lambda i, j: i + j > linea)
            if linea is not None else None)
    return {
        "1X2 local":     backtest.suma_si(m, lambda i, j: i > j),
        "1X2 empate":    backtest.suma_si(m, lambda i, j: i == j),
        "1X2 visitante": backtest.suma_si(m, lambda i, j: i < j),
        "Over":          over,
    }


def movimientos(cuotas):
    """Una fila por mercado y partido: lo que decía el modelo, la cuota
    de apertura y la de cierre, las dos ya sin margen."""
    filas = []
    for eid, historia in (cuotas or {}).items():
        if not isinstance(historia, list) or len(historia) < 2:
            continue                       # sin dos fotos no hay movimiento
        pri, ult = historia[0], historia[-1]
        mod = _probs_modelo(pri)
        tri_a = [pri["local"], pri["empate"], pri["visitante"]]
        tri_c = [ult["local"], ult["empate"], ult["visitante"]]
        pares = [("1X2 local", 0, tri_a, tri_c),
                 ("1X2 empate", 1, tri_a, tri_c),
                 ("1X2 visitante", 2, tri_a, tri_c)]
        # El total solo se compara si la LÍNEA no se movió: si pasó de
        # 2.5 a 1.5 no son el mismo mercado, y el movimiento de la cuota
        # no significa lo que parece.
        if (pri.get("totalLinea") is not None
                and pri.get("totalLinea") == ult.get("totalLinea")):
            pares.append(("Over", 0,
                          [pri["totalOver"], pri["totalUnder"]],
                          [ult["totalOver"], ult["totalUnder"]]))
        for nombre, idx, ca, cc in pares:
            # Shin y no proporcional: medido sobre 6310 partidos con
            # cuota de cierre real, el proporcional infla el batacazo
            # +0.86 puntos y hunde al favorito -2.09. Shin deja +/-0.1 y
            # -0.97. El CLV es cuota x probabilidad de cierre, asi que
            # con el proporcional nos auto-regalariamos ventaja justo en
            # el lado donde mas facil es enganarse.
            pa, pc = devig_shin(ca), devig_shin(cc)
            pm = mod.get(nombre)
            if pa is None or pc is None or pm is None:
                continue
            filas.append({
                "evento": eid, "mercado": nombre,
                "p_modelo": pm, "p_open": pa[idx], "p_close": pc[idx],
                "cuota_open": ca[idx], "cuota_close": cc[idx],
            })
    return filas


def _binomial_cola(k, n):
    """P(X >= k) con una moneda limpia. Sin scipy: el repo es stdlib."""
    if n <= 0:
        return 1.0
    return sum(comb(n, i) for i in range(k, n + 1)) / (2 ** n)


def veredicto(filas):
    """¿La línea se movió hacia donde apuntaba el modelo, más seguido de
    lo que explicaría el azar?

    Solo cuentan los casos donde el modelo dijo algo distinto de la
    apertura Y la línea efectivamente se movió. Si acertamos la
    DIRECCIÓN del movimiento más de la mitad de las veces de forma
    sostenida, hay información.
    """
    utiles = [f for f in filas
              if abs(f["p_modelo"] - f["p_open"]) >= MIN_DISCREPANCIA
              and f["p_close"] != f["p_open"]]
    aciertos = sum(1 for f in utiles
                   if (f["p_modelo"] - f["p_open"]) * (f["p_close"] - f["p_open"]) > 0)
    n = len(utiles)
    p = _binomial_cola(aciertos, n) if n else 1.0
    return {"n": len(filas), "utiles": n, "aciertos": aciertos, "p": p,
            "hay_senal": bool(n >= MIN_CASOS and p < UMBRAL and aciertos * 2 > n)}


def clv_medio(filas):
    """Cuota tomada por probabilidad de cierre, menos 1.

    Positivo quiere decir que conseguiste un precio mejor que el que el
    mercado terminó considerando justo. Es el número que, sostenido en
    el tiempo, separa tener ventaja de tener suerte.
    """
    if not filas:
        return None
    return sum(f["cuota_open"] * f["p_close"] - 1 for f in filas) / len(filas)


def main():
    if not CUOTAS.exists():
        print("\nTodavía no hay data/cuotas.json. Corré actualizar.py.\n")
        return 0
    cuotas = json.loads(CUOTAS.read_text(encoding="utf-8"))
    fotos = sum(len(v) for v in cuotas.values())
    con_mov = sum(1 for v in cuotas.values() if len(v) >= 2)
    print("\n" + "=" * 66)
    print("  CLV — ¿la línea se mueve hacia nosotros?")
    print("=" * 66)
    print(f"\n  {len(cuotas)} partidos guardados · {fotos} fotos · "
          f"{con_mov} con al menos dos")

    filas = movimientos(cuotas)
    if not filas:
        print("\n  Todavía ningún partido tiene dos fotos distintas.")
        print("  ESPN borra la cuota cuando el partido termina, así que esto")
        print("  solo se junta hacia adelante: hacen falta varias corridas del")
        print("  cron sobre partidos que todavía no se jugaron.\n")
        return 0

    v = veredicto(filas)
    clv = clv_medio(filas)
    print(f"\n  {v['n']} comparaciones · {v['utiles']} con opinión propia "
          f"y movimiento real")
    if v["utiles"]:
        pct = v["aciertos"] / v["utiles"] * 100
        print(f"  acertamos la dirección en {v['aciertos']} de {v['utiles']} "
              f"({pct:.0f}%)")
        print(f"  el azar da eso o mejor el {v['p'] * 100:.1f}% de las veces")
    if clv is not None:
        print(f"\n  CLV medio: {clv * 100:+.2f}%")
        print("  (cuota de apertura por probabilidad de cierre, menos 1)")

    print("\n  " + "-" * 62)
    if v["hay_senal"]:
        print("  HAY SEÑAL: la línea se mueve hacia nosotros más de lo que")
        print("  explicaría el azar. Eso es ventaja real, aunque una apuesta")
        print("  suelta se pierda.")
    elif v["utiles"] < MIN_CASOS:
        print(f"  TODAVÍA NO SE PUEDE DECIR: hacen falta {MIN_CASOS} casos")
        print(f"  y hay {v['utiles']}. Dejalo juntar unas fechas más.")
    else:
        print("  NO HAY SEÑAL: la línea no se mueve hacia nosotros más de lo")
        print("  que da el azar. Mientras siga así, una marca de valor está")
        print("  señalando nuestro error más seguido que un precio mal puesto.")
    print("  " + "-" * 62 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
