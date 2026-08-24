#!/usr/bin/env python3
"""Tests de medir_arbitros.py

Se midio que las tarjetas no dependen del marcador (r = -0.05 con los
goles, +0.01 con la diferencia). El sospechoso que queda es el arbitro.
ESPN lo devuelve en el mismo /summary que ya se pide.

Este script contesta una sola pregunta, y tiene que poder contestar que
NO: la diferencia entre arbitros, hoy, se explica sola por el azar. Los
tests existen para que el script no pueda decir "hay efecto" cuando no
lo hay, que es la forma facil de enganarse midiendo.

    python test_medir_arbitros.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_arbitros as m

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def partido(arb, a, b, met="tarjetas"):
    return {"_arbitro": arb, "9": {met: a}, "5": {met: b}}


print("")
print("pares_arbitro() — el total del partido junto a quien lo dirigio")
print("")

CACHE = {
    "e1": partido("Juez A", 2, 3),
    "e2": partido("Juez B", 0, 1),
    "e3": partido("", 4, 4),                       # sin arbitro informado
    "e4": {"9": {"tarjetas": 1}, "5": {"tarjetas": 1}},   # registro viejo
    "e5": {"_arbitro": "Juez C", "9": {"tarjetas": 2}},   # falta un equipo
    "_meta": "no es un partido",
}
# `_jugadores` es un diccionario, igual que un equipo: filtrar por tipo
# no alcanza, contaria como un tercer equipo y el partido se descartaria
# entero. Paso exactamente eso en dispersion_total().
CACHE["e6"] = {"_arbitro": "Juez D", "_jugadores": {"7": [1, 0]},
               "9": {"tarjetas": 3}, "5": {"tarjetas": 2}}

p = m.pares_arbitro(CACHE, "tarjetas")
prueba("las claves de partido no cuentan como un equipo",
       ("Juez D", 5.0) in p)
prueba("suma los dos equipos", ("Juez A", 5.0) in p)
prueba("toma todos los partidos con arbitro", len(p) == 3)
prueba("descarta el partido sin arbitro informado", all(a for a, _ in p))
prueba("descarta el registro viejo sin la clave", len(p) == 3)
prueba("descarta el partido con un solo equipo", all(v > 0 for _, v in p))
prueba("ignora las claves de metadatos", "_meta" not in str(p))
prueba("un cache vacio no rompe", m.pares_arbitro({}, "tarjetas") == [])

print("")
print("dispersion_entre() — cuanto se separan los promedios de cada uno")
print("")

iguales = [("A", 4.0), ("A", 4.0), ("B", 4.0), ("B", 4.0),
           ("C", 4.0), ("C", 4.0), ("D", 4.0), ("D", 4.0),
           ("E", 4.0), ("E", 4.0)]
prueba("si todos promedian igual, la dispersion es cero",
       m.dispersion_entre(iguales) == 0.0)

distintos = [("A", 1.0), ("A", 1.0), ("B", 5.0), ("B", 5.0),
             ("C", 9.0), ("C", 9.0), ("D", 3.0), ("D", 3.0),
             ("E", 7.0), ("E", 7.0)]
prueba("si se separan, es mayor que cero", m.dispersion_entre(distintos) > 5)

prueba("un arbitro con un solo partido no aporta un promedio",
       m.dispersion_entre(iguales + [("Z", 99.0)]) == 0.0)
prueba("con pocos arbitros no devuelve un numero",
       m.dispersion_entre([("A", 1.0), ("A", 2.0)]) is None)
prueba("sin datos no rompe", m.dispersion_entre([]) is None)

print("")
print("pvalor() — la prueba que puede decir que no")
print("")

# El caso que importa: valores repartidos al azar entre arbitros. El
# script TIENE que decir que no se distingue. Si dijera que si, estaria
# inventando un efecto y esa es la falla cara.
import random
random.seed(5)
al_azar = [(f"J{i % 12}", float(random.randint(0, 8))) for i in range(60)]
pv = m.pvalor(al_azar, vueltas=400, semilla=1)
prueba("con datos al azar no encuentra efecto", pv > 0.05)

# Y el opuesto: si el arbitro DE VERDAD manda, tiene que detectarlo.
mandado = [(f"J{i % 12}", float((i % 12) * 2)) for i in range(60)]
prueba("si el arbitro manda de verdad, lo detecta",
       m.pvalor(mandado, vueltas=400, semilla=1) < 0.05)

prueba("es reproducible con la misma semilla",
       m.pvalor(al_azar, vueltas=200, semilla=9)
       == m.pvalor(al_azar, vueltas=200, semilla=9))
prueba("sin muestra suficiente no inventa un p",
       m.pvalor([("A", 1.0), ("A", 2.0)], vueltas=50, semilla=1) is None)

print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
