#!/usr/bin/env python3
"""¿La `inclinacion` del análisis sirve, o el modelo solo anda mejor?

Existe porque el proyecto tomó una decisión de diseño fuerte y nunca la
midió: cuando el análisis contradice al modelo, **gana el análisis** — la
app descarta toda apuesta que contradiga esa dirección. Es lo que Método
le promete al usuario. Si el análisis acierta menos que el modelo, esa
regla está filtrando apuestas buenas con una lectura peor.

Lo que se mide, en orden de cuánta muestra necesita:

  1. DISTRIBUCIÓN — sirve desde el primer puñado de partidos. Si el
     análisis dice "L" el 86% de las veces y el local gana el 45%, eso
     es sesgo de proceso, no mala suerte.
  2. ACIERTO contra baselines — necesita ~30 partidos para decir algo.
     Solo contra un baseline significa algo: "acertó 2 de 6" no dice
     nada, "acertó menos que apostar siempre al local" sí.
  3. LA REGLA DE ALINEACIÓN — el número que justifica este script.
     Solo cuenta los partidos donde análisis y modelo difieren. Es el
     más lento de llenar, porque las divergencias son pocas.

**No se puede backtestear.** La skill hace research web: si se corre
sobre un partido viejo, la web ya sabe el resultado. Los números salen
solo de análisis escritos ANTES del partido, así que la muestra crece
fecha a fecha y no de golpe.

    python medir_analisis.py
"""

import json
import sys
from pathlib import Path

for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

RAIZ = Path(__file__).resolve().parent
ANALISIS = RAIZ / "data" / "analisis.json"
HISTORIAL = RAIZ / "data" / "historial_pronosticos.json"

# Debajo de esto, cualquier porcentaje de acierto es ruido. Se sigue
# mostrando, pero con la advertencia puesta: el error más caro que puede
# cometer este script es que alguien "corrija" la skill por una racha.
MUESTRA_MINIMA = 30


def real_de(resultado):
    """[goles local, goles visitante] -> 'L' / 'E' / 'V'."""
    if not resultado or len(resultado) < 2:
        return None
    h, a = resultado[0], resultado[1]
    if h is None or a is None:
        return None
    return "L" if h > a else ("V" if a > h else "E")


def pct(parte, total):
    """Porcentaje, o None si no hay sobre qué calcularlo."""
    return None if not total else round(100.0 * parte / total, 1)


def siempre(direccion, reales):
    """Cuántas acertaría la estrategia sin trabajo: apostar siempre a lo
    mismo. Es el piso contra el que el análisis tiene que valer algo."""
    return sum(1 for r in reales if r == direccion)


def distribucion(inclinaciones):
    """Cuántas veces se eligió cada dirección, contando los null aparte.

    Es la medición que sirve con muestra chica: la distribución esperada
    de resultados en el fútbol sudamericano ronda 45/28/27 (L/E/V). Un
    análisis que dice "L" nueve de cada diez veces está equivocado como
    proceso, sin importar cómo salgan esos partidos.
    """
    if not inclinaciones:
        return {}
    d = {"L": 0, "E": 0, "V": 0, None: 0}
    for i in inclinaciones:
        d[i if i in ("L", "E", "V") else None] += 1
    d["_con_direccion"] = d["L"] + d["E"] + d["V"]
    return d


def comparar(casos):
    """casos: [(inclinacion, lean del modelo, resultado real)].

    El bloque `div_*` es el que responde por la regla de alineación: en
    los partidos donde las dos lecturas difieren, ¿cuál tenía razón?
    Los partidos donde coinciden no dicen nada sobre la regla — la regla
    solo actúa cuando hay conflicto.
    """
    r = {"n": 0, "ok_analisis": 0, "ok_modelo": 0,
         "n_div": 0, "div_analisis": 0, "div_modelo": 0}
    for inc, lean, real in casos:
        r["n"] += 1
        r["ok_analisis"] += inc == real
        r["ok_modelo"] += lean == real
        if inc != lean:
            r["n_div"] += 1
            r["div_analisis"] += inc == real
            r["div_modelo"] += lean == real
    return r


def cargar_casos():
    """Los partidos que tienen las tres cosas: análisis con dirección,
    pronóstico del modelo, y resultado. Es la intersección, y es chica."""
    from backtest import matriz, suma_si

    with open(ANALISIS, encoding="utf-8") as f:
        an = json.load(f)
    with open(HISTORIAL, encoding="utf-8") as f:
        hist = json.load(f)

    casos, sin_direccion, pendientes = [], 0, 0
    for k, v in an.items():
        if k == "_schema":
            continue
        h = hist.get(k)
        if not h:
            continue
        real = real_de(h.get("resultado"))
        if real is None:
            pendientes += 1
            continue
        inc = v.get("inclinacion")
        if inc is None:
            sin_direccion += 1
            continue
        M = matriz(h["lh"], h["la"], h.get("rho", 0))
        p = {"L": suma_si(M, lambda i, j: i > j),
             "E": suma_si(M, lambda i, j: i == j),
             "V": suma_si(M, lambda i, j: i < j)}
        lean = max(p, key=p.get)
        casos.append((inc, lean, real, h, k))
    return casos, sin_direccion, pendientes, an


def main():
    casos, sin_direccion, pendientes, an = cargar_casos()
    total_an = len([k for k in an if k != "_schema"])

    print(f"\n{'='*66}")
    print("  ¿Sirve la inclinación del análisis?")
    print(f"{'='*66}")
    print(f"\n  {total_an} análisis escritos · {len(casos)} ya jugados y con "
          f"dirección · {pendientes} sin jugar · {sin_direccion} en null")

    if not casos:
        print("\n  Todavía no hay ningún partido analizado que ya se haya "
              "jugado.\n  Volvé después de la próxima fecha.\n")
        return 0

    reales = [c[2] for c in casos]
    incs = [c[0] for c in casos]
    r = comparar([(c[0], c[1], c[2]) for c in casos])

    # ── 1. Distribución ──────────────────────────────────────────────
    print(f"\n{'─'*66}")
    print("  1. DISTRIBUCIÓN — lo que más rápido delata un sesgo")
    print(f"{'─'*66}\n")
    # Se cuenta sobre TODOS los análisis, no solo los jugados: el sesgo
    # de la skill al elegir dirección no depende de que el partido ya
    # se haya jugado.
    todas = [v.get("inclinacion") for k, v in an.items() if k != "_schema"]
    d = distribucion(todas)
    dr = distribucion(reales)
    print(f"  {'':10} {'análisis':>18}   {'resultados reales':>18}")
    for k, et in (("L", "Local"), ("E", "Empate"), ("V", "Visitante")):
        pa = pct(d.get(k, 0), d.get("_con_direccion", 0))
        pr = pct(dr.get(k, 0), dr.get("_con_direccion", 0))
        print(f"  {et:10} {d.get(k,0):>3} ({str(pa)+'%' if pa is not None else '—':>7})"
              f"   {dr.get(k,0):>10} ({str(pr)+'%' if pr is not None else '—':>7})")
    print(f"  {'null':10} {d.get(None,0):>3}")
    print("\n  Referencia del fútbol sudamericano: ~45% local, ~28% empate, "
          "~27% visitante.")
    if d.get("_con_direccion"):
        peor = max("LEV", key=lambda k: d.get(k, 0))
        p = pct(d.get(peor, 0), d["_con_direccion"])
        if p and p >= 70:
            print(f"  ⚠ El análisis elige '{peor}' el {p}% de las veces. Eso no "
                  "es una racha:\n    es un sesgo de proceso, y se ve aunque la "
                  "muestra sea chica.")

    # ── 2. Acierto contra baselines ──────────────────────────────────
    print(f"\n{'─'*66}")
    print("  2. ACIERTO — solo significa algo contra un baseline")
    print(f"{'─'*66}\n")
    n = r["n"]
    filas = [
        ("El análisis", r["ok_analisis"]),
        ("El modelo", r["ok_modelo"]),
        ("Apostar siempre al local", siempre("L", reales)),
        ("Apostar siempre al empate", siempre("E", reales)),
        ("Apostar siempre al visitante", siempre("V", reales)),
    ]
    for et, v in filas:
        print(f"  {et:30} {v:>2} de {n}  ({pct(v,n)}%)")
    if n < MUESTRA_MINIMA:
        print(f"\n  ⚠ {n} partidos es muy poco para leer estos porcentajes. "
              f"Hacen falta ~{MUESTRA_MINIMA}.\n    No cambies la skill por "
              "estos números: mirá la distribución de arriba.")

    # ── 3. La regla de alineación ────────────────────────────────────
    print(f"\n{'─'*66}")
    print("  3. LA REGLA DE ALINEACIÓN — el número que justifica este script")
    print(f"{'─'*66}\n")
    print("  Cuando el análisis contradice al modelo, la app le da la razón")
    print("  al análisis y descarta lo que lo contradiga. ¿Tiene razón?\n")
    if r["n_div"] == 0:
        print("  Todavía no hubo ni un partido donde las dos lecturas "
              "difieran.\n")
        print("  Eso ya dice algo, y no es bueno: si el análisis nunca")
        print("  contradice al modelo, no está aportando una segunda lectura")
        print("  — está repitiendo la primera. La regla de alineación no")
        print("  suma ni resta: está inerte. Ver principio K de la skill.")
    else:
        print(f"  Difirieron en {r['n_div']} de {n} partidos "
              f"({pct(r['n_div'], n)}%)\n")
        print(f"    Tenía razón el análisis: {r['div_analisis']}")
        print(f"    Tenía razón el modelo:   {r['div_modelo']}")
        print(f"    Ninguno de los dos:      "
              f"{r['n_div'] - r['div_analisis'] - r['div_modelo']}")
        if r["n_div"] < 10:
            plural = "divergencia" if r["n_div"] == 1 else "divergencias"
            print(f"\n  ⚠ Con {r['n_div']} {plural} no se puede concluir "
                  "nada todavía.")
        elif r["div_modelo"] > r["div_analisis"]:
            print("\n  ⚠ El modelo viene acertando más que el análisis cuando")
            print("    difieren. Si esto se sostiene, la regla de alineación")
            print("    está costando plata: filtra apuestas buenas.")

    # Coincidencia: la otra cara del principio K.
    coinc = pct(n - r["n_div"], n)
    print(f"\n  El análisis coincidió con el modelo en {n - r['n_div']} de {n} "
          f"({coinc}%).")
    if coinc is not None and coinc >= 80:
        print("  Cuanto más alto ese número, menos información nueva está")
        print("  aportando el análisis por encima de lo que el modelo ya ve.")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
