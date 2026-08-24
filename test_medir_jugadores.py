#!/usr/bin/env python3
"""Tests de medir_jugadores.py — la calibración de las líneas de JUGADOR.

Por qué existe:

`medir_lineas.py` mide los totales del PARTIDO (córners, tarjetas,
remates de los dos equipos sumados). Las líneas de jugador — "¿remata
más de 1.5?", "¿patea al arco al menos una vez?" — nunca se midieron,
aunque `index.html` las viene mostrando con su porcentaje.

Es el mismo agujero que se descubrió el 2026-08-24 en el modelo de
goles y en el mercado de estadísticas, una capa más abajo. Lucas
preguntó el 2026-08-24 si la app servía para el mercado de remates de
jugador, y la respuesta honesta era "nadie lo comprobó".

Lo que estos tests protegen:

- que la medición no mire el futuro: la serie de un jugador y los
  parámetros de su puesto salen SOLO de partidos anteriores;
- que un jugador que no jugó no cuente como un cero;
- que la muestra corta se declare en vez de disimularse — el 78% de las
  predicciones se hacen con dos partidos de historia;
- que el veredicto que la app va a mostrar se compare contra el ruido y
  no contra cero. Con n=618, un modelo PERFECTO ya da 3.5 puntos de
  desvío solo por azar: llamar "malo" a un 4.0 sería inventar un
  problema.

    python test_medir_jugadores.py
"""

import datetime
import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_jugadores as J

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


print("\nserie_previa() — solo lo anterior, y solo lo que jugó\n")

# [remates, al_arco, faltas, amarillas, goles, asist, titular]
hist = [
    ("2026-05-01", "a", [3, 1, 2, 0, 0, 0, 1]),
    ("2026-05-08", "b", [1, 0, 1, 1, 0, 0, 1]),
    ("2026-05-15", "c", [5, 2, 0, 0, 1, 0, 1]),
]

prueba("toma los partidos anteriores en orden",
       J.serie_previa(hist, "2026-05-15")[0] == [3, 1, 2, 0, 0, 0, 1])
prueba("no incluye el partido que se está prediciendo",
       len(J.serie_previa(hist, "2026-05-15")) == 2)
prueba("un partido del mismo día no cuenta",
       J.serie_previa(hist, "2026-05-01") == [])
prueba("sin historia devuelve vacío", J.serie_previa([], "2026-05-15") == [])

# El tope existe porque un jugador de hace seis meses no describe al de hoy.
largo = [(f"2026-01-{d:02d}", str(d), [d, 0, 0, 0, 0, 0, 1]) for d in range(1, 21)]
prueba("recorta a los últimos N partidos",
       len(J.serie_previa(largo, "2026-02-01", tope=8)) == 8)
prueba("y los que recorta son los más nuevos",
       J.serie_previa(largo, "2026-02-01", tope=3)[-1][0] == 20)


print("\nvalores() — leer una métrica de la serie\n")

s = J.serie_previa(hist, "2026-05-15")
prueba("lee remates por su posición", J.valores(s, "remates") == [3.0, 1.0])
prueba("lee al_arco por la suya", J.valores(s, "al_arco") == [1.0, 0.0])
prueba("una métrica que no existe no rompe", J.valores(s, "inventada") == [])


print("\nesperado() — el promedio encogido hacia el puesto\n")

par = {"media": 1.0, "k": 4.0, "disp": 1.1}
prueba("sin partidos propios se apoya entero en el puesto",
       abs(J.esperado([], par) - 1.0) < 1e-9)
prueba("con partidos propios se mueve hacia ellos",
       J.esperado([5.0, 5.0], par) > 1.0)
prueba("pero nunca los alcanza con k alto",
       J.esperado([5.0, 5.0], {"media": 1.0, "k": 40.0, "disp": 1.1}) < 1.5)
prueba("nunca cae fuera del rango entre lo propio y el puesto",
       1.0 <= J.esperado([3.0], par) <= 3.0)


print("\nlinea_de() — la línea que se ofrece sale del esperado\n")

prueba("un esperado de 2.4 da la línea 1.5", J.linea_de(2.4) == 1.5)
prueba("un esperado de 2.6 da la línea 2.5", J.linea_de(2.6) == 2.5)
prueba("nunca baja de 0.5, que es el piso del mercado", J.linea_de(0.1) == 0.5)
prueba("un esperado de cero tampoco la hunde", J.linea_de(0.0) == 0.5)


print("\nveredicto() — comparar contra el ruido, no contra cero\n")

# Lo que hace distinto a este script: con n chico, un modelo perfecto
# desvía igual. El veredicto tiene que saberlo.
prueba("un desvío por debajo del ruido esperado se llama fiable",
       J.veredicto(desvio=3.0, ruido=3.5)["nivel"] == "bien")
prueba("uno muy por encima se llama no fiable",
       J.veredicto(desvio=7.1, ruido=3.5)["nivel"] == "mal")
prueba("y el del medio queda declarado como dudoso",
       J.veredicto(desvio=4.8, ruido=3.5)["nivel"] == "regular")
prueba("el mismo desvío cambia de veredicto si el ruido cambia",
       J.veredicto(desvio=4.8, ruido=3.5)["nivel"]
       != J.veredicto(desvio=4.8, ruido=6.0)["nivel"])
prueba("sin ruido estimado no inventa un veredicto",
       J.veredicto(desvio=4.8, ruido=None) is None)
prueba("el veredicto trae texto para la pantalla",
       isinstance(J.veredicto(desvio=7.1, ruido=3.5).get("texto"), str))


print("\nruido_esperado() — cuánto desvía un modelo PERFECTO con esta n\n")

ps = [0.5] * 200
r = J.ruido_esperado(ps, reps=200, semilla=1)
prueba("con muestra chica el ruido es grande", r > 1.0)
r2 = J.ruido_esperado([0.5] * 4000, reps=200, semilla=1)
prueba("con muestra grande el ruido baja", r2 < r)
prueba("es reproducible con la misma semilla",
       J.ruido_esperado(ps, reps=100, semilla=3)
       == J.ruido_esperado(ps, reps=100, semilla=3))
prueba("sin probabilidades no rompe", J.ruido_esperado([], reps=10) is None)


print("\nresumen() — lo que se publica para la app\n")

filas = ([{"p": 0.6, "paso": 1} for _ in range(60)]
         + [{"p": 0.6, "paso": 0} for _ in range(40)])
r = J.resumen(filas, largos=[2] * 100)
prueba("declara sobre cuántas predicciones va", r["n"] == 100)
prueba("declara el desvío", "desvio" in r)
prueba("declara el ruido con el que hay que compararlo", "ruido" in r)
prueba("declara el veredicto", r["nivel"] in ("bien", "regular", "mal"))
prueba("declara cuántos partidos tenía la serie típica", r["serie"] == 2)
prueba("sin filas devuelve None", J.resumen([], largos=[]) is None)


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
