#!/usr/bin/env python3
"""Corregir la exageración de λ, y medir si sirve. Train/test temporal.

El hallazgo que lo motiva (`medir_compresion.py`, 2026-08-30):

    franja λ      n   predicho    real   desvío
     0.0-2.0    1583      1.80    2.07    +0.27
     2.4-2.6     931      2.49    2.31    -0.18
     3.0-3.3     129      3.11    2.44    -0.67

    pendiente de real contra predicho: 0.368 ± 0.108

El modelo predice un rango de 1.80 a 3.11 goles donde la realidad va de
2.07 a 2.44. **Estira su rango ~2.7 veces más que la realidad.** Donde
dice mucho gol pasan menos y donde dice poco gol pasan más.

Que no es un artefacto está verificado contra el ruido, como manda el
repo: un modelo PERFECTO simulado con la misma muestra y la misma
distribución de λ da pendiente 0.944 ± 0.091; uno que exagera 2.7x da
0.335 ± 0.091. El real (0.368) está en el segundo grupo.

Por qué nunca se vio: en agregado se cancela. `medir_historico.py`
parte por banda de probabilidad del 1X2 y `barrido_lambda.py` mide over
2.5 en total (0.357 real contra 0.375 predicho — bien). Ninguno parte
por λ predicho, que es la única vista donde el defecto aparece.

La corrección que se prueba acá:

    λ_corregido = μ + k · (λ_modelo − μ)

con μ = la media de λ de la liga (estimada SOLO con train) y k barrido.
k=1 es producción; k≈0.37 es lo que sugiere la pendiente medida. El
reparto entre local y visitante se mantiene proporcional: se corrige la
magnitud del total, no quién ataca más.

Qué se mide, y por qué las tres cosas:

- **Brier de over/under 2.5** — el efecto directo sobre goles.
- **ROI de over/under** — porque mejorar el Brier no es ganar plata, y
  este repo ya se comió esa lección con `medir_encogimiento.py`.
- **Brier del 1X2** como control de daño: escalar λ mueve todas las
  probabilidades, y una mejora en goles que rompa el 1X2 no sirve.

Disciplina, la de siempre: k se elige con train (<2022) y se confirma
con test (>=2022). Si el ganador de train se da vuelta en test, no es
un hallazgo.

    python barrido_escala_lambda.py eng
"""

import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent
CORTE = date(2022, 1, 1)

# k=1.00 es producción (sin tocar nada). La pendiente medida sugiere
# ~0.37; la grilla lo cubre con margen para los dos lados, así que un
# óptimo en el borde se vería.
ESCALAS = [0.30, 0.40, 0.50, 0.60, 0.70, 0.85, 1.00, 1.15]


def escalar(lh, la, mu, k):
    """λ corregido hacia la media de la liga, manteniendo el reparto.

    Se escala el TOTAL y después se reparte con la misma proporción que
    tenía. Escalar lh y la por separado cambiaría también quién ataca
    más, que es una corrección distinta y no es la que se midió.
    """
    total = lh + la
    if total <= 0:
        return lh, la
    nuevo = mu + k * (total - mu)
    nuevo = max(0.4, nuevo)
    f = nuevo / total
    return lh * f, la * f


def main(argv):
    import backtest
    import historico as H
    import medir_clv
    import medir_historico as MH
    import medir_roi as R

    liga = (argv[1] if len(argv) > 1 else "eng").lower()
    if liga not in H.LIGAS:
        raise SystemExit(f"liga desconocida: {liga}. Hay {sorted(H.LIGAS)}")

    print("\n" + "=" * 78)
    print(f"  CORREGIR LA EXAGERACIÓN DE λ — {liga}, train/test temporal")
    print("=" * 78)
    print(f"\n  train: < {CORTE}  (elige k y μ)   ·   test: >= {CORTE}  (confirma)")
    print("  k=1.00 es producción. La pendiente medida sugiere ~0.37.\n")
    print("  ajustando walk-forward (una sola vez)...", flush=True)

    filas = MH.evaluar(H.partidos(liga), progreso=2000)
    tr = [f for f in filas if f["fecha"] < CORTE]
    te = [f for f in filas if f["fecha"] >= CORTE]
    print(f"  {len(filas)} partidos · train {len(tr)} · test {len(te)}")

    # μ sale SOLO de train. Usar todo el historial sería mirar el futuro.
    mu = sum(f["lh"] + f["la"] for f in tr) / len(tr)
    print(f"  μ de train: {mu:.3f} goles\n")

    def rehacer(f, k):
        """Una fila con λ corregido y todas sus probabilidades rehechas."""
        lh, la = escalar(f["lh"], f["la"], mu, k)
        m = backtest.matriz(lh, la, f.get("rho", 0.0) or 0.0)
        g = dict(f)
        g["modelo"] = [backtest.suma_si(m, lambda i, j: i > j),
                       backtest.suma_si(m, lambda i, j: i == j),
                       backtest.suma_si(m, lambda i, j: i < j)]
        # SIEMPRE, no solo donde hay cuota. Atarlo a `cuotas_ou` dejaba
        # la probabilidad de goles sin recalcular en arg y bra (la
        # fuente no publica línea ahí), y el barrido devolvía el MISMO
        # Brier para todos los k — un empate perfecto que no puede
        # pasar si la corrección hace algo. No rompía nada ni avisaba:
        # solo medía el modelo sin corregir y lo llamaba corregido.
        g["modelo_ou"] = [backtest.suma_si(m, lambda i, j: i + j > 2.5),
                          backtest.suma_si(m, lambda i, j: i + j < 2.5)]
        return g

    def brier_ou(fs):
        sel = [f for f in fs if f.get("modelo_ou") and f.get("real_ou")]
        if not sel:
            return None
        return sum(sum((f["modelo_ou"][i] - f["real_ou"][i]) ** 2
                       for i in range(2)) for f in sel) / len(sel)

    def brier_1x2(fs):
        return sum(MH.brier(f["modelo"], f["real"]) for f in fs) / len(fs)

    print(f"  {'k':>5} │ {'Brier O/U tr':>12} {'Brier O/U te':>12} │ "
          f"{'ROI O/U te':>11} {'±2se':>7} {'n':>5} │ {'Brier 1X2 te':>12}")
    print("  " + "-" * 76)

    res = []
    for k in ESCALAS:
        gtr = [rehacer(f, k) for f in tr]
        gte = [rehacer(f, k) for f in te]
        b_tr, b_te = brier_ou(gtr), brier_ou(gte)
        r_ou = R.roi(R.apuestas_ou(gte))
        b1 = brier_1x2(gte)
        res.append({"k": k, "b_tr": b_tr, "b_te": b_te, "roi": r_ou, "b1": b1})
        marca = "  ← producción" if k == 1.00 else ""
        roi_txt = (f"{r_ou['roi']*100:+10.2f}% {r_ou['se']*200:6.2f} {r_ou['n']:5d}"
                   if r_ou["n"] else f"{'—':>10}  {'—':>6} {0:5d}")
        print(f"  {k:5.2f} │ {b_tr if b_tr else 0:12.5f} {b_te if b_te else 0:12.5f} │ "
              f"{roi_txt} │ {b1:12.5f}{marca}")

    # Veredicto, escrito para poder decir que no.
    print("\n  " + "=" * 74)
    conb = [x for x in res if x["b_tr"] is not None]
    if not conb:
        print("  esta liga no tiene mercado de goles en la fuente")
        return 0
    mejor_tr = min(conb, key=lambda x: x["b_tr"])
    mejor_te = min(conb, key=lambda x: x["b_te"])
    prod = next(x for x in res if x["k"] == 1.00)

    print(f"  mejor k en TRAIN: {mejor_tr['k']:.2f}   ·   "
          f"mejor k en TEST: {mejor_te['k']:.2f}   ·   producción: 1.00")
    if mejor_tr["k"] != mejor_te["k"]:
        print("\n  El ganador de train NO es el de test. Eso es la señal de que")
        print("  el efecto no es estable — la misma que apagó barrido_lambda.py.")
    gana_brier = mejor_tr["b_te"] < prod["b_te"]
    print(f"\n  Brier O/U en test con k={mejor_tr['k']:.2f}: {mejor_tr['b_te']:.5f}"
          f"   ·   con producción: {prod['b_te']:.5f}"
          f"   ({'mejora' if gana_brier else 'NO mejora'})")
    if mejor_tr["roi"]["n"] and prod["roi"]["n"]:
        print(f"  ROI O/U en test con k={mejor_tr['k']:.2f}: "
              f"{mejor_tr['roi']['roi']*100:+.2f}% ±{mejor_tr['roi']['se']*200:.2f}"
              f"   ·   con producción: {prod['roi']['roi']*100:+.2f}%")
    print(f"  Brier 1X2 en test (control de daño): {mejor_tr['b1']:.5f} "
          f"contra {prod['b1']:.5f} de producción")
    print("\n  Nada se toca hasta que mejore en test SIN romper el 1X2.")
    print("  " + "=" * 74 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
