#!/usr/bin/env python3
"""Tests de medir_devig.py — ¿qué método de quitar el margen acierta?

Por qué existe:

Una cuota no es una probabilidad: las tres del 1X2 suman más de 1, y esa
diferencia es la ganancia de la casa. Para comparar el modelo contra el
mercado hay que sacarle ese margen, y **cómo** se lo sacás cambia el
número contra el que después medís todo.

El 2026-08-25 se descubrió que el repo usaba dos métodos distintos a la
vez: `medir_clv.py` y `medir_historico.py` usaban Shin (1993), y
`index.html` — o sea lo que ve el usuario y lo que decide la marca
dorada — usaba el proporcional. Medíamos el modelo con una vara y
marcábamos valor con otra.

Esto salió de leer "Using the Wisdom of the Crowd" de Joseph Buchdahl
(gratis y legal en football-data.co.uk, el mismo sitio del que
`historico.py` ya baja los datos), que dedica varias páginas a mostrar
que repartir el margen parejo entre las tres opciones está mal: las
casas le cargan más margen a las cuotas altas.

Lo que estos tests protegen:

- que la comparación sea **pareada**: los dos métodos ven exactamente
  las mismas cuotas y los mismos resultados, o no compara nada;
- que las probabilidades y los resultados estén **alineados** en el
  mismo orden [local, empate, visita]. Un cruce ahí invierte la
  conclusión entera sin que nada falle;
- que el error se mida contra el **ruido binomial** y no contra cero:
  con 56 casos en el tramo de cuotas altas, una frecuencia observada se
  aparta varios puntos por puro azar;
- que Shin conserve su propiedad definitoria — sacarle
  proporcionalmente más margen a la cuota alta — porque si se rompe,
  todo lo demás mide otra cosa.

    python test_medir_devig.py
"""

import math
import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_devig as D

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


print("\nruido_binomial() — cuánto se mueve una frecuencia por azar\n")

prueba("con muestra chica el ruido es grande",
       D.ruido_binomial(0.5, 30) > D.ruido_binomial(0.5, 3000))
prueba("es el error estándar binomial",
       abs(D.ruido_binomial(0.25, 100) - math.sqrt(0.25 * 0.75 / 100)) < 1e-12)
prueba("una frecuencia de cero no rompe", D.ruido_binomial(0.0, 100) == 0.0)
prueba("sin casos no inventa un número", D.ruido_binomial(0.5, 0) is None)


print("\nacumular() — solo las cuotas del tramo, y alineadas\n")

# [local, empate, visita]. El local es favorito y gana.
partidos = [
    {"cuotas": [1.30, 5.50, 9.00], "gh": 2, "ga": 0},
    {"cuotas": [1.35, 5.00, 8.50], "gh": 0, "ga": 1},
]

t = D.acumular(partidos, 1.0, 1.5)
prueba("cuenta un caso por partido en el tramo del favorito", t["n"] == 2)
prueba("y observa que el favorito ganó una de las dos", t["obs"] == 1)

t2 = D.acumular(partidos, 7.0, 15.0)
prueba("el tramo de cuota alta toma la visita", t2["n"] == 2)
prueba("y observa la única victoria visitante", t2["obs"] == 1)

t3 = D.acumular(partidos, 4.0, 6.0)
prueba("el tramo del medio toma el empate", t3["n"] == 2)
prueba("y no hubo ninguno", t3["obs"] == 0)

prueba("un tramo sin cuotas no devuelve nada", D.acumular(partidos, 20, 30)["n"] == 0)

# Esta es la que protege la conclusión entera: si las probabilidades y
# los resultados se cruzan de orden, el favorito parece perder siempre.
solo_local = [{"cuotas": [1.10, 12.0, 20.0], "gh": 3, "ga": 0}] * 50
t4 = D.acumular(solo_local, 1.0, 1.5)
prueba("cuando el favorito gana siempre, el tramo lo refleja",
       t4["obs"] == t4["n"] == 50)
t5 = D.acumular(solo_local, 15.0, 30.0)
prueba("y el tramo de la visita no observa ninguna",
       t5["obs"] == 0 and t5["n"] == 50)


print("\nlos dos métodos: qué los distingue\n")

cuotas = [1.30, 5.50, 9.00]
prop = D.devig_proporcional(cuotas)
shin = D.devig_shin(cuotas)

prueba("los dos suman 1", abs(sum(prop) - 1) < 1e-9 and abs(sum(shin) - 1) < 1e-9)
prueba("Shin le da MÁS probabilidad al favorito", shin[0] > prop[0])
prueba("y MENOS a la cuota alta, que es su razón de ser", shin[2] < prop[2])

# Sin margen no hay nada que repartir: los dos tienen que coincidir.
justas = [1 / 0.5, 1 / 0.3, 1 / 0.2]
pj, sj = D.devig_proporcional(justas), D.devig_shin(justas)
prueba("sin margen los dos métodos coinciden",
       all(abs(a - b) < 1e-6 for a, b in zip(pj, sj)))

# Cuanto más margen, más se separan. Es lo que hace que importe qué casa
# se use como referencia: DraftKings tiene el doble de margen que Pinnacle.
poco = [1.0 / (0.5 * 1.02), 1.0 / (0.3 * 1.02), 1.0 / (0.2 * 1.02)]
mucho = [1.0 / (0.5 * 1.10), 1.0 / (0.3 * 1.10), 1.0 / (0.2 * 1.10)]
sep_poco = abs(D.devig_shin(poco)[2] - D.devig_proporcional(poco)[2])
sep_mucho = abs(D.devig_shin(mucho)[2] - D.devig_proporcional(mucho)[2])
prueba("con más margen los dos métodos se separan más", sep_mucho > sep_poco)


print("\nresumen_tramo() — el error medido contra el ruido\n")

r = D.resumen_tramo({"n": 1000, "obs": 300, "prop": 320.0, "shin": 305.0})
prueba("declara la frecuencia observada", abs(r["real"] - 0.30) < 1e-9)
prueba("declara lo que dijo cada método",
       abs(r["prop"] - 0.32) < 1e-9 and abs(r["shin"] - 0.305) < 1e-9)
prueba("el error va en unidades de ruido, no en puntos sueltos",
       r["err_prop"] > r["err_shin"] > 0)
prueba("con este caso gana Shin, que es el que menos le erra",
       r["gana"] == "shin")

# El mismo apartamiento con muestra chica no significa lo mismo.
chico = D.resumen_tramo({"n": 40, "obs": 12, "prop": 12.8, "shin": 12.2})
grande = D.resumen_tramo({"n": 4000, "obs": 1200, "prop": 1280.0, "shin": 1220.0})
prueba("el mismo desvío pesa más con muestra grande",
       grande["err_prop"] > chico["err_prop"])
prueba("un tramo sin casos no devuelve resumen",
       D.resumen_tramo({"n": 0, "obs": 0, "prop": 0.0, "shin": 0.0}) is None)


print("\ncomparar() — el veredicto sale de sumar los tramos\n")

falsos = [
    {"cuotas": [1.30, 5.50, 9.00], "gh": 2, "ga": 0},
    {"cuotas": [2.10, 3.30, 3.70], "gh": 1, "ga": 1},
    {"cuotas": [4.50, 3.60, 1.85], "gh": 0, "ga": 2},
]
c = D.comparar(falsos, cortes=[(1.0, 2.0), (2.0, 4.0), (4.0, 999)])
prueba("devuelve un tramo por corte con casos", len(c["tramos"]) >= 1)
prueba("declara el error total de cada método",
       "total_prop" in c and "total_shin" in c)
prueba("y nombra un ganador", c["gana"] in ("prop", "shin"))
prueba("sin partidos no inventa un veredicto", D.comparar([]) is None)


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
