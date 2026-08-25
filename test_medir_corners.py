#!/usr/bin/env python3
"""Tests de medir_corners.py — el mercado de córners contra plata.

Qué protegen, y por qué cada uno existe:

- **Que el margen se quite antes de comparar.** Comparar la
  probabilidad del modelo contra la cruda de la casa hace ver ventaja
  donde solo hay comisión. Con 8.4% de margen medio, casi cualquier
  pronóstico "encuentra valor" si nadie lo descuenta.
- **Que un ROI no se pueda reportar sin su error estándar.** El
  2026-08-25 la medición dio +11.2% de ROI sobre 41 apuestas con ±13.9%
  de azar. Es ruido. Hay un test que exige que ese caso NO salga
  marcado como significativo.
- **Que la moneda siga estando en la comparación.** En over/under la
  casa pone la línea cerca del 50%, así que el mercado mismo apenas le
  gana a tirar una moneda (+0.0008 de Brier, medido). Sin esa
  referencia, "estamos a la par del mercado" se lee como un logro
  cuando puede ser un empate en cero — es la misma vara falsa de
  §6septdecies del traspaso.

    python test_medir_corners.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_corners as MC

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def cerca(a, b, tol=1e-9):
    return a is not None and abs(a - b) < tol


print("")
print("probabilidades() — el margen sale antes de comparar")
print("")

# Un par simétrico sin margen: 2.00 y 2.00 es 50/50 exacto.
p = MC.probabilidades([2.0, 2.0])
prueba("un par justo da 50/50", cerca(p[0], 0.5) and cerca(p[1], 0.5))
prueba("las dos suman 1 siempre", cerca(sum(p), 1.0))

# El par real de un partido de Liga Profesional: 8.4% de margen.
p2 = MC.probabilidades([1.80, 1.90])
prueba("con margen, siguen sumando 1", cerca(sum(p2), 1.0))
prueba("y el favorito queda por encima del 50%", p2[0] > 0.5)
# Sin quitar el margen, la cruda del primero seria 0.556; quitandolo, menos.
prueba("quitar el margen BAJA la probabilidad del favorito",
       p2[0] < 1 / 1.80)

prueba("una cuota rota no inventa un numero",
       MC.probabilidades([1.0, 1.9]) is None)
prueba("un par incompleto tampoco", MC.probabilidades([1.9]) is None)
prueba("y una lista vacia tampoco", MC.probabilidades([]) is None)


print("")
print("margen() — cuanto se queda la casa")
print("")

prueba("un par justo no tiene margen", cerca(MC.margen([2.0, 2.0]), 0.0))
prueba("el par real de corners ronda el 8%",
       0.07 < MC.margen([1.80, 1.90]) < 0.10)
prueba("sin par no hay margen", MC.margen([2.0]) is None)


print("")
print("lado() — a que apostar, comparando contra la limpia")
print("")

# El modelo dice 61% donde el mercado limpio dice 51.4%: 9.6 puntos.
l = MC.lado(0.61, [1.80, 1.90], umbral=0.06)
prueba("con ventaja suficiente, apuesta al mas", l and l[0] == "mas")
prueba("y devuelve la cuota del lado que eligio", l and cerca(l[1], 1.80))

# El mismo par, con el modelo del otro lado.
l2 = MC.lado(0.30, [1.80, 1.90], umbral=0.06)
prueba("si le ve menos, apuesta al menos", l2 and l2[0] == "menos")
prueba("con la cuota del menos", l2 and cerca(l2[1], 1.90))

# EL test que impide el error mas caro de este mercado. Si alguien
# comparara contra la cuota CRUDA (1/1.80 = 0.5556) en vez de contra la
# limpia (0.514), un modelo que dice 57% "encontraria" un 1.4% de
# ventaja que en realidad es margen de la casa. Con 8.4% de margen, casi
# cualquier pronostico encuentra valor si nadie lo descuenta.
prueba("un modelo apenas arriba de la cuota cruda NO apuesta",
       MC.lado(0.57, [1.80, 1.90], umbral=0.06) is None)
prueba("y uno que empata con la limpia tampoco",
       MC.lado(0.514, [1.80, 1.90], umbral=0.06) is None)

prueba("sin probabilidad del modelo no apuesta",
       MC.lado(None, [1.80, 1.90]) is None)
prueba("sin cuotas tampoco", MC.lado(0.9, None) is None)

# El umbral tiene que morder.
prueba("un umbral mas alto filtra mas",
       MC.lado(0.56, [1.80, 1.90], umbral=0.02) is not None
       and MC.lado(0.56, [1.80, 1.90], umbral=0.20) is None)


print("")
print("retorno() y resultado() — la plata, con su azar al lado")
print("")

prueba("ganar a 1.80 deja 0.80", cerca(MC.retorno(1.80, True), 0.80))
prueba("perder deja -1", cerca(MC.retorno(1.80, False), -1.0))

# Una tanda que gana siempre: ROI positivo y grande.
r = MC.resultado([(2.0, True)] * 20)
prueba("veinte aciertos a 2.00 dan 100% de ROI", cerca(r["roi"], 1.0))
prueba("y sin varianza, el error estandar es cero", cerca(r["ee"], 0.0))

# EL test. El caso real medido: +11.2% de ROI sobre 41 apuestas con un
# error estandar de 13.9%. NO puede salir marcado como significativo.
import random
_r = random.Random(3)
# 41 apuestas a ~1.95, con 61% de aciertos: reproduce la tanda medida.
_aps = [(1.95, i < 25) for i in range(41)]
_r.shuffle(_aps)
res = MC.resultado(_aps)
prueba("la tanda real da un ROI positivo", res["roi"] > 0.05)
prueba("pero NO es significativa, que es lo que hay que reportar",
       not res["significativo"])
prueba("y su error estandar es del orden del propio ROI",
       res["ee"] > res["roi"] / 2)

# Una tanda igual de rentable pero DIEZ veces mas larga si tiene que
# poder detectarse: es la diferencia entre no saber y saber.
largo = MC.resultado(_aps * 10)
prueba("la misma ventaja con 410 apuestas ya se detecta",
       largo["significativo"])
prueba("porque el error estandar bajo, no porque cambio el ROI",
       cerca(largo["roi"], res["roi"], 1e-9) and largo["ee"] < res["ee"])

prueba("sin apuestas no devuelve un ROI inventado",
       MC.resultado([]) is None)


print("")
print("apuestas_necesarias() — decir cuanto falta, no solo que falta")
print("")

n = MC.apuestas_necesarias(0.112)
prueba("para el +11.2% medido pide unas 300 apuestas", 250 < n < 350)
prueba("una ventaja mas chica pide muchas mas",
       MC.apuestas_necesarias(0.05) > n)
prueba("y una mas grande, muchas menos",
       MC.apuestas_necesarias(0.30) < n)
prueba("crece con el cuadrado de lo chica que es la ventaja",
       abs(MC.apuestas_necesarias(0.05) / MC.apuestas_necesarias(0.10) - 4) < 0.2)
prueba("un ROI de cero no tiene respuesta",
       MC.apuestas_necesarias(0) is None)


print("")
print("contra_el_cierre() — con la moneda a la vista")
print("")

# Un mercado que sabe: acierta el lado el 70% de las veces.
_fs_bueno = ([{"p": 0.7, "q": 0.7, "paso": True}] * 70
             + [{"p": 0.7, "q": 0.7, "paso": False}] * 30)
c = MC.contra_el_cierre(_fs_bueno)
prueba("un mercado informativo le gana a la moneda",
       c["mercado_sobre_moneda"] > 0.01)

# El caso REAL, y el que obliga a que la moneda este en la tabla: un
# mercado puesto justo en 50/50. Le gana a la moneda por nada.
_fs_real = ([{"p": 0.52, "q": 0.51, "paso": True}] * 46
            + [{"p": 0.52, "q": 0.51, "paso": False}] * 54)
c2 = MC.contra_el_cierre(_fs_real)
prueba("un mercado puesto en el punto de la moneda casi no le gana",
       abs(c2["mercado_sobre_moneda"]) < 0.01)
prueba("y ahi 'estar a la par del mercado' no dice nada",
       abs(c2["atraso"]) < 0.01)

perf = MC.contra_el_cierre([{"p": 1.0, "q": 0.5, "paso": True}] * 10)
prueba("un modelo perfecto tiene Brier cero", cerca(perf["modelo"], 0.0))
prueba("y le saca ventaja al mercado", perf["atraso"] < 0)

prueba("el atraso viene con su error estandar", "ee" in (c or {}))
prueba("sin filas no devuelve nada", MC.contra_el_cierre([]) is None)


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
