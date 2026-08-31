#!/usr/bin/env python3
"""¿En qué EJE del partido sabemos más? La base de la escalera nueva.

De dónde sale: la escalera de riesgo se documentó como "tres formas de
jugar la misma lectura", pero la intención original era otra y mejor —
mostrar que un partido tiene varios ejes (quién gana, cuántos goles, si
ambos marcan) y que en algunos hay más convicción que en otros. Si el
1X2 está parejo, quizás el eje de goles no lo está.

Para que eso sea honesto hace falta saber DÓNDE sabemos más, medido y
no supuesto. Eso es lo que contesta este script: Brier por mercado,
walk-forward, contra la tasa base de ese mismo mercado.

La vara importa. Un mercado donde el 80% de las veces pasa lo mismo
tiene Brier bajo sin que el modelo aporte nada — hay que compararlo
contra su propia tasa base, no entre mercados.

    python medir_ejes.py arg
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent

MERCADOS = [
    ("Gana el local",      "Resultado", lambda i, j: i > j),
    ("Empate",             "Resultado", lambda i, j: i == j),
    ("Gana el visitante",  "Resultado", lambda i, j: i < j),
    ("Local o empate",     "Resultado", lambda i, j: i >= j),
    ("Visita o empate",    "Resultado", lambda i, j: i <= j),
    ("Gana alguno",        "Resultado", lambda i, j: i != j),
    ("Más de 1.5 goles",   "Goles",     lambda i, j: i + j > 1.5),
    ("Más de 2.5 goles",   "Goles",     lambda i, j: i + j > 2.5),
    ("Más de 3.5 goles",   "Goles",     lambda i, j: i + j > 3.5),
    ("Ambos marcan",       "Ambos",     lambda i, j: i > 0 and j > 0),
]


def main(argv):
    import actualizar as A
    import backtest
    import historico as H
    import medir_historico as MH

    liga = (argv[1] if len(argv) > 1 else "arg").lower()
    rho = (A.COMPETICIONES.get(liga + ".1") or {}).get("rho", 0.0)
    print(f"\n  ¿EN QUÉ EJE SABEMOS MÁS? — {liga}\n")
    print("  ajustando walk-forward...", flush=True)
    filas = MH.evaluar(H.partidos(liga), progreso=2000)

    idx = {(p["fecha"], p["home"], p["away"]): (p["gh"], p["ga"])
           for p in H.partidos(liga)}
    datos = []
    for f in filas:
        g = idx.get((f["fecha"], f["home"], f["away"]))
        if g:
            m = backtest.matriz(f["lh"], f["la"], rho)
            datos.append((m, g))
    print(f"  {len(datos)} partidos\n")

    print(f"  {'mercado':20} {'nuestro':>9} {'tasa base':>10} {'aporte':>9}")
    print("  " + "-" * 52)
    fam_ant = None
    for nombre, fam, test in MERCADOS:
        if fam != fam_ant:
            print(f"  {fam}")
            fam_ant = fam
        ps, rs = [], []
        for m, (i, j) in datos:
            ps.append(backtest.suma_si(m, test))
            rs.append(1 if test(i, j) else 0)
        n = len(ps)
        base = sum(rs) / n
        b_mod = sum((p - r) ** 2 for p, r in zip(ps, rs)) / n
        b_base = sum((base - r) ** 2 for r in rs) / n
        aporte = (b_base - b_mod) / b_base * 100 if b_base else 0
        marca = "  ←" if aporte > 3 else ("  ✗" if aporte <= 0 else "")
        print(f"    {nombre:18} {b_mod:9.4f} {b_base:10.4f} {aporte:+8.1f}%{marca}")

    print("\n  'aporte' = cuánto mejora el modelo sobre saber solo la")
    print("  frecuencia histórica de ese mercado. Negativo = el modelo")
    print("  resta: conviene publicar la tasa base y no nuestra opinión.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
