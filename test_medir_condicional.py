#!/usr/bin/env python3
"""Tests de medir_condicional.py — goles dado el resultado.

Por qué existe:

La medición contesta si el modelo sabe de goles CONDICIONADO al
resultado cuando ya está medido que en general no sabe. Es una
pregunta donde es fácil contestarse que sí sin querer, y estos tests
tapan las tres formas de hacerlo:

- **La vara tiene que ser condicionada.** Si se compara P(G|R) contra
  la tasa base GLOBAL de G, el modelo gana solo por saber que los
  partidos que terminan en victoria tienen más goles que el promedio —
  algo que ya sabe cualquiera que mire la tabla de frecuencias, sin
  modelo. El aporte se mide contra la frecuencia dentro del mismo
  subconjunto.
- **Condicionar tiene que ser la matriz, no una regla aparte.** P(G|R)
  sale de P(G∩R)/P(R) leído del mismo objeto que ya usa `combinada()`.
  Si eso se calcula mal, el número se ve razonable igual.
- **El delta se compara contra su propio ruido, y pareado.** Los dos
  pronósticos se evalúan sobre los MISMOS partidos, así que la
  desviación que importa es la de la diferencia. Sin eso, con un tercio
  de la muestra cualquier condición parece aportar algo.

    python test_medir_condicional.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_condicional as C

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
    return abs(a - b) < tol


def mat(pesos, mx=9):
    """Una matriz de marcadores con la masa puesta a mano."""
    m = [[0.0] * (mx + 1) for _ in range(mx + 1)]
    for (i, j), p in pesos.items():
        m[i][j] = p
    return m


def buscar(salida, condicion, mercado):
    for f in salida:
        if f["condicion"] == condicion:
            for x in f["mercados"]:
                if x["mercado"] == mercado:
                    return x
    return None


print("\naporte() — cuánto le saca el pronóstico a la tasa base\n")

RS = [1] * 30 + [0] * 30
prueba("publicar la tasa base no aporta nada",
       cerca(C.aporte([0.5] * 60, RS), 0.0))
prueba("acertar siempre aporta el 100%",
       cerca(C.aporte([1.0] * 30 + [0.0] * 30, RS), 100.0))
prueba("equivocarse siempre da negativo",
       C.aporte([0.0] * 30 + [1.0] * 30, RS) < 0)
prueba("sin nada que predecir (todos iguales) no devuelve un número",
       C.aporte([0.7] * 10, [1] * 10) is None)


print("\nmedir() — condicionar es leer la matriz, no una regla aparte\n")

# Dos partidos que el modelo ve idénticos en goles —P(más de 2.5) = 0.5
# en los dos— pero opuestos una vez que se sabe quién ganó.
GOLEADA = mat({(3, 0): 0.5, (1, 1): 0.5})   # gana el local ⇒ over 2.5
CERRADO = mat({(1, 0): 0.5, (2, 2): 0.5})   # gana el local ⇒ under 2.5
DATOS = [(GOLEADA, (3, 0))] * 40 + [(CERRADO, (1, 0))] * 40

sal = C.medir(DATOS, remuestreos=200)
loc = buscar(sal, "gana el local", "Más de 2.5 goles")

prueba("toma solo los partidos donde la condición pasó", loc["n"] == 80)
prueba("el modelo de hoy, sin condicionar, no aporta nada acá",
       cerca(loc["aporte_unc"], 0.0))
prueba("condicionado acierta perfecto", cerca(loc["aporte_cond"], 100.0))
prueba("y el delta es todo lo que agrega condicionar",
       cerca(loc["delta"], 100.0))
prueba("el delta positivo se distingue del ruido",
       loc["ee_delta"] >= 0 and loc["delta"] > 2 * loc["ee_delta"])

# Las mismas matrices con los resultados cruzados: el modelo condiciona
# con convicción y le erra siempre. Tiene que dar negativo, no "poco
# positivo" — un pronóstico seguro y equivocado es peor que la vara.
INV = [(GOLEADA, (1, 0))] * 40 + [(CERRADO, (3, 0))] * 40
peor = buscar(C.medir(INV, remuestreos=200), "gana el local",
              "Más de 2.5 goles")
prueba("si condiciona al revés, el aporte es negativo",
       peor is not None and peor["aporte_cond"] < 0)
prueba("y peor que no condicionar, que ahí sí era neutro",
       peor is not None and cerca(peor["aporte_unc"], 0.0)
       and peor["delta"] < 0)


print("\nla vara: la tasa base del subconjunto, no la global\n")

# Se agregan empates 0-0: la frecuencia GLOBAL de más de 2.5 baja, pero
# adentro de las victorias del local sigue siendo 0.5. Si la vara fuera
# la global, el aporte sin condicionar dejaría de ser cero.
SECO = mat({(0, 0): 1.0})
CON_EMPATES = DATOS + [(SECO, (0, 0))] * 80
sal2 = C.medir(CON_EMPATES, remuestreos=200)
loc2 = buscar(sal2, "gana el local", "Más de 2.5 goles")

prueba("los partidos de otra condición no entran al subconjunto",
       loc2["n"] == 80)
prueba("la tasa base es la de adentro del subconjunto",
       cerca(loc2["base"], 0.5))
prueba("y el aporte sin condicionar sigue siendo cero",
       cerca(loc2["aporte_unc"], 0.0))
prueba("una condición sin variación en el mercado no se reporta",
       buscar(sal2, "empate", "Más de 2.5 goles") is None)


print("\n_favorito() — el lado que el modelo elige, no el local\n")

prueba("con el local más probable, condiciona a que gane el local",
       C._favorito(mat({(1, 0): 0.7, (0, 1): 0.3}))(1, 0) is True)
prueba("con el visitante más probable, condiciona al visitante",
       C._favorito(mat({(1, 0): 0.3, (0, 1): 0.7}))(0, 1) is True)
prueba("y en ese caso la victoria del local NO cuenta",
       C._favorito(mat({(1, 0): 0.3, (0, 1): 0.7}))(1, 0) is False)


print("\nbootstrap() — el ruido, y pareado\n")

# Ruido puro: el resultado no tiene nada que ver con lo que dice el
# modelo. El aporte real es ~0 y lo único que importa es que la medición
# diga cuánto se mueve.
rnd = [1, 0] * 40
ruido = [0.3 + 0.4 * (k % 3) / 2 for k in range(80)]
ee_c, ee_u, ee_d = C.bootstrap(ruido, ruido, rnd, remuestreos=300)
prueba("un pronóstico sin señal igual tiene error estándar", ee_c > 0)
prueba("dos pronósticos idénticos no tienen diferencia entre ellos",
       cerca(ee_d, 0.0))
prueba("y eso es lo que el pareado tiene que ver: no la suma de los dos",
       ee_d < ee_c + ee_u)
prueba("el mismo llamado da el mismo número (semilla fija)",
       C.bootstrap(ruido, ruido, rnd, remuestreos=300) == (ee_c, ee_u, ee_d))


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
