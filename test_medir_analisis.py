#!/usr/bin/env python3
"""Tests del medidor de análisis.

Este script existe para responder dos preguntas que hoy nadie contesta:
si la `inclinacion` del análisis acierta, y si la regla de alineación
—que hace ganar al análisis sobre el modelo— suma o resta.

Los tests importan más de lo habitual porque de sus números salen
decisiones sobre la skill. Un medidor con un bug te hace "corregir" un
sesgo que no existe, o peor, te deja tranquilo con uno que sí.

    python test_medir_analisis.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_analisis as M

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


print("\nreal_de() — el resultado como dirección\n")

prueba("gana el local", M.real_de([2, 1]) == "L")
prueba("gana el visitante", M.real_de([0, 3]) == "V")
prueba("empate", M.real_de([1, 1]) == "E")
prueba("0-0 es empate, no ausencia de dato", M.real_de([0, 0]) == "E")
prueba("sin resultado devuelve None", M.real_de(None) is None)
prueba("un resultado incompleto no inventa", M.real_de([2]) is None)


print("\ncomparar() — quién acierta, y sobre todo cuándo difieren\n")

# El caso que importa: el análisis contradice al modelo. La app le da la
# razón al análisis y descarta apuestas contra su dirección. Si el modelo
# acierta más en estos partidos, esa regla está costando plata.
casos = [
    # (inclinacion, lean del modelo, resultado real)
    ("L", "L", "L"),   # coinciden y aciertan
    ("L", "L", "V"),   # coinciden y fallan
    ("V", "L", "V"),   # difieren: gana el análisis
    ("L", "V", "V"),   # difieren: gana el modelo
    ("E", "L", "E"),   # difieren: gana el análisis
]
r = M.comparar(casos)

prueba("cuenta todos los partidos", r["n"] == 5)
prueba("aciertos del análisis", r["ok_analisis"] == 3)
prueba("aciertos del modelo", r["ok_modelo"] == 2)
prueba("cuenta las divergencias", r["n_div"] == 3)
prueba("en las divergencias, aciertos del análisis", r["div_analisis"] == 2)
prueba("en las divergencias, aciertos del modelo", r["div_modelo"] == 1)

# Sin divergencias no hay nada que decir sobre la regla de alineación —
# y decir "el análisis va 100%" sobre cero casos sería peor que callar.
sin_div = M.comparar([("L", "L", "L"), ("V", "V", "E")])
prueba("sin divergencias, no inventa un veredicto sobre la regla",
       sin_div["n_div"] == 0 and sin_div["div_analisis"] == 0)
prueba("una lista vacía no rompe", M.comparar([])["n"] == 0)


print("\ndistribucion() — el sesgo se ve antes que el acierto\n")

# Con 7 partidos no se puede medir acierto, pero sí distribución: si el
# análisis dice "L" el 86% de las veces y el local gana el 45%, eso ya es
# un error de proceso, detectable con muestra chica.
d = M.distribucion(["L", "L", "L", "L", "V", "E", None])
prueba("cuenta cada dirección", d["L"] == 4 and d["V"] == 1 and d["E"] == 1)
prueba("cuenta los null aparte", d[None] == 1)
prueba("los null no entran en el total con dirección", d["_con_direccion"] == 6)
prueba("distribución vacía no rompe", M.distribucion([]) == {})


print("\npct() — porcentajes sin dividir por cero\n")

prueba("porcentaje normal", M.pct(3, 4) == 75.0)
prueba("cero sobre cero no revienta", M.pct(0, 0) is None)
prueba("cero sobre algo es cero", M.pct(0, 5) == 0.0)


print("\nbaselines: contra qué se compara\n")

# "El análisis acertó 2 de 6" no significa nada solo. Significa algo
# contra "siempre local", que es la estrategia sin ningún trabajo.
reales = ["L", "E", "L", "V", "E", "L"]
prueba("siempre local acierta las locales", M.siempre("L", reales) == 3)
prueba("siempre empate acierta los empates", M.siempre("E", reales) == 2)

print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
