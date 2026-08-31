#!/usr/bin/env python3
"""¿La mejora del Brier se despega del ruido? Test PAREADO.

Comparar dos Brier sueltos no sirve: el error estándar de cada uno es
grande y se solapan. Pero son los MISMOS partidos con dos valores de k,
así que la comparación correcta es sobre la diferencia por partido —
donde la varianza común se cancela.
"""
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backtest
import barrido_escala_lambda as B
import historico as H
import medir_historico as MH

LIGA = sys.argv[1] if len(sys.argv) > 1 else "arg"
K = float(sys.argv[2]) if len(sys.argv) > 2 else 0.50

filas = MH.evaluar(H.partidos(LIGA), progreso=None)
tr = [f for f in filas if f["fecha"] < B.CORTE]
te = [f for f in filas if f["fecha"] >= B.CORTE]
mu = sum(f["lh"] + f["la"] for f in tr) / len(tr)

def brier_de(f, k):
    lh, la = B.escalar(f["lh"], f["la"], mu, k)
    m = backtest.matriz(lh, la, f.get("rho", 0.0) or 0.0)
    pou = [backtest.suma_si(m, lambda i, j: i + j > 2.5),
           backtest.suma_si(m, lambda i, j: i + j < 2.5)]
    b_ou = sum((pou[i] - f["real_ou"][i]) ** 2 for i in range(2))
    p3 = [backtest.suma_si(m, lambda i, j: i > j),
          backtest.suma_si(m, lambda i, j: i == j),
          backtest.suma_si(m, lambda i, j: i < j)]
    b_3 = sum((p3[i] - f["real"][i]) ** 2 for i in range(3))
    return b_ou, b_3

d_ou, d_3 = [], []
for f in te:
    a_ou, a_3 = brier_de(f, K)
    p_ou, p_3 = brier_de(f, 1.00)
    d_ou.append(p_ou - a_ou)      # positivo = la corrección mejora
    d_3.append(p_3 - a_3)

def resumen(d, etiqueta):
    n = len(d)
    m = sum(d) / n
    var = sum((x - m) ** 2 for x in d) / n
    se = (var / n) ** 0.5
    z = m / se if se else 0
    veredicto = ("MEJORA, y se despega del ruido" if z > 2 else
                 "EMPEORA, y se despega" if z < -2 else
                 "dentro del ruido")
    print(f"  {etiqueta:12} diferencia media {m:+.5f} ± {2*se:.5f}  "
          f"({z:+.1f} errores estándar)  {veredicto}")

print(f"\n  {LIGA} · test (n={len(te)}) · k={K} contra producción (k=1.00)")
print("  positivo = la corrección mejora\n")
resumen(d_ou, "goles O/U")
resumen(d_3, "1X2")
print()
