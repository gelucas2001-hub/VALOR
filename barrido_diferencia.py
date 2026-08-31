#!/usr/bin/env python3
"""¿El modelo exagera la DIFERENCIA entre los dos equipos? Train/test.

El segundo eje del mismo defecto. `medir_compresion.py` encontró que el
modelo estira el TOTAL de goles 2.7 veces más que la realidad, y eso ya
está corregido (`corregir_escala` en actualizar.py). Pero esa corrección
mantiene la proporción entre local y visitante: arregla cuántos goles
hay, no quién gana.

La sobre-dispersión del 1X2 vive en el otro eje. `medir_calibracion.py`,
sobre lo que la app efectivamente publicó:

    Probabilidades altas (60%+):  -6.6% de desvío
    Probabilidades bajas (<40%):  +9.8% de desvío
    1X2 local:  decimos 43.5%, pasa 25.4%   (-18.1%)

Es el "1X2 de favoritos sobreconfiados" que TRASPASO.md arrastra
documentado desde el 2026-08-24 sin causa identificada. La causa
candidata: λ_local y λ_visita están más separados de lo que la realidad
los separa.

La corrección que se prueba acá conserva el total y encoge la brecha:

    total = lh + la           (no se toca)
    diff  = lh - la
    diff' = k · diff
    lh'   = (total + diff') / 2 ,  la' = (total - diff') / 2

k=1.00 es producción. k<1 acerca a los equipos; k=0 los iguala.

Se mide el Brier del 1X2 (el que debería mejorar) y el de over/under
como control de daño: encoger la diferencia no debería tocar el total,
y si lo toca es que la cuenta está mal.

    python barrido_diferencia.py arg
"""

import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent
CORTE = date(2022, 1, 1)

# k = cuánto se conserva de la diferencia. 1.00 es producción.
KS = [0.50, 0.65, 0.75, 0.85, 0.95, 1.00, 1.10]


def encoger_diferencia(lh, la, k):
    """Acerca los dos λ entre sí SIN mover el total."""
    if k == 1.0:
        return lh, la
    total, diff = lh + la, (lh - la) * k
    return max(0.05, (total + diff) / 2), max(0.05, (total - diff) / 2)


def main(argv):
    import actualizar as A
    import backtest
    import historico as H
    import medir_historico as MH

    liga = (argv[1] if len(argv) > 1 else "arg").lower()
    if liga not in H.LIGAS:
        raise SystemExit(f"liga desconocida: {liga}")
    rho = (A.COMPETICIONES.get(liga + ".1") or {}).get("rho", 0.0)

    print("\n" + "=" * 74)
    print(f"  ¿EXAGERAMOS LA DIFERENCIA ENTRE EQUIPOS? — {liga}")
    print("=" * 74)
    print(f"\n  k = cuánto se conserva de (λ_local − λ_visita). 1.00 es producción.")
    print(f"  El total de goles NO se toca.")
    print(f"\n  train < {CORTE} elige · test >= {CORTE} confirma\n")
    print("  ajustando walk-forward...", flush=True)

    filas = MH.evaluar(H.partidos(liga), progreso=2000)
    tr = [f for f in filas if f["fecha"] < CORTE]
    te = [f for f in filas if f["fecha"] >= CORTE]
    print(f"  {len(filas)} partidos · train {len(tr)} · test {len(te)}\n")

    def briers(fs, k):
        b3 = bou = 0.0
        for f in fs:
            lh, la = encoger_diferencia(f["lh"], f["la"], k)
            m = backtest.matriz(lh, la, rho)
            p3 = [backtest.suma_si(m, lambda i, j: i > j),
                  backtest.suma_si(m, lambda i, j: i == j),
                  backtest.suma_si(m, lambda i, j: i < j)]
            b3 += sum((p3[i] - f["real"][i]) ** 2 for i in range(3))
            pou = [backtest.suma_si(m, lambda i, j: i + j > 2.5),
                   backtest.suma_si(m, lambda i, j: i + j < 2.5)]
            bou += sum((pou[i] - f["real_ou"][i]) ** 2 for i in range(2))
        return b3 / len(fs), bou / len(fs)

    print(f"  {'k':>5} │ {'Brier 1X2 tr':>12} {'Brier 1X2 te':>12} │ {'Brier O/U te':>12}")
    print("  " + "-" * 50)
    res = []
    for k in KS:
        b3tr, _ = briers(tr, k)
        b3te, boute = briers(te, k)
        res.append({"k": k, "tr": b3tr, "te": b3te, "ou": boute})
        marca = "  ← producción" if k == 1.0 else ""
        print(f"  {k:5.2f} │ {b3tr:12.5f} {b3te:12.5f} │ {boute:12.5f}{marca}")

    prod = next(x for x in res if x["k"] == 1.00)
    mtr = min(res, key=lambda x: x["tr"])
    mte = min(res, key=lambda x: x["te"])
    print("\n  " + "=" * 70)
    print(f"  mejor k en TRAIN: {mtr['k']:.2f} · en TEST: {mte['k']:.2f} · producción: 1.00")
    if mtr["k"] == 1.00:
        print("\n  Producción gana en train. La diferencia entre equipos NO está")
        print("  exagerada: el hallazgo es que no hay hallazgo.")
    else:
        mejora = prod["te"] - mtr["te"]
        print(f"\n  Con k={mtr['k']:.2f} el Brier de test da {mtr['te']:.5f} contra "
              f"{prod['te']:.5f} de producción ({'mejora' if mejora > 0 else 'empeora'}).")
        print(f"  Control O/U: {mtr['ou']:.5f} contra {prod['ou']:.5f} — debería")
        print("  moverse poco, porque el total no se toca.")
        print("\n  Falta el test pareado antes de tocar nada.")
    print("  " + "=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
