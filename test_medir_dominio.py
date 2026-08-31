#!/usr/bin/env python3
"""Tests de medir_dominio.py — ¿el ancla larga sirve fuera de córners?

Por qué existe, y qué se rompe si estos tests no están:

- **La fuga de futuro.** El pronóstico de un partido no puede usar ese
  partido. Una fuga no se ve como un error: se ve como un modelo
  buenísimo. Acá el riesgo es doble, porque la media de la liga también
  se acumula sobre la marcha y es fácil calcularla sobre todo el
  archivo sin darse cuenta.
- **El `k` prestado.** Si el pronóstico largo elige su mejor `k` y al
  corto se le deja uno cualquiera, el largo gana por construcción. Cada
  uno elige el suyo, en train.
- **El borde de la grilla.** Un `k` óptimo en el extremo significa que
  el barrido no encontró nada, solo dónde dejamos de mirar. Regla dura
  de CLAUDE.md, quemada dos veces el 2026-08-24 — y acá el borde de
  abajo (k=0, "no encoger") tiene significado propio, así que hay que
  poder distinguirlo del borde ciego de arriba.
- **La diferencia contra el ruido.** Dos errores medidos sobre las
  mismas apariciones están pareados; la desviación que importa es la de
  la diferencia fila por fila.

    python test_medir_dominio.py
"""

import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
import medir_dominio as D

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


def partido(dia, home, away, met, vh, va):
    return {"fecha": date(2020, 1, 1) + __import__("datetime").timedelta(days=dia),
            "home": home, "away": away, "est": {met: {"h": vh, "a": va}}}


print("\napariciones() — una fila por equipo, en orden\n")

PS = [partido(2, "B", "A", "corners", 9, 1),
      partido(1, "A", "B", "corners", 5, 3)]
fil = D.apariciones(PS, "corners")

prueba("cada partido aporta dos filas, una por equipo", len(fil) == 4)
prueba("vienen ordenadas por fecha, no en el orden del archivo",
       [f[0] for f in fil] == sorted(f[0] for f in fil))
prueba("el valor de local va con el equipo local",
       (fil[0][1], fil[0][2]) == ("A", 5.0))
prueba("y el de visitante con el visitante",
       (fil[1][1], fil[1][2]) == ("B", 3.0))
prueba("un partido sin esa métrica no aporta filas",
       D.apariciones([{"fecha": date(2020, 1, 1), "home": "A", "away": "B",
                       "est": {"corners": {"h": 4, "a": 2}}}], "tarjetas") == [])


print("\nencoger() — la media del equipo tirada hacia la liga\n")

prueba("k=0 deja la media del equipo intacta", cerca(D.encoger(8.0, 10, 5.0, 0), 8.0))
prueba("k enorme la reemplaza por la liga",
       abs(D.encoger(8.0, 10, 5.0, 10**6) - 5.0) < 1e-3)
prueba("nunca se sale del intervalo entre las dos",
       5.0 <= D.encoger(8.0, 10, 5.0, 7) <= 8.0)
prueba("con más partidos encoge menos",
       D.encoger(8.0, 40, 5.0, 7) > D.encoger(8.0, 4, 5.0, 7))
prueba("sin partidos del equipo devuelve la liga", cerca(D.encoger(8.0, 0, 5.0, 7), 5.0))


print("\npronosticos() — sin mirar el partido que predice\n")

# Un equipo constante en 10 y otro constante en 2. La media de la liga
# sube a 6 con el tiempo, pero cada fila solo puede ver lo anterior.
SERIE = [partido(d, "A", "B", "corners", 10, 2) for d in range(12)]
datos = D.pronosticos(D.apariciones(SERIE, "corners"), ventana=4, min_previos=3)

prueba("no predice hasta tener min_previos del equipo", len(datos) == (12 - 3) * 2)
prueba("la media corta del equipo A es la suya, no la de la liga",
       all(cerca(d[2], 10.0) for d in datos if cerca(d[0], 10.0)))
prueba("la ventana corta nunca supera su tope",
       max(d[3] for d in datos) == 4)
prueba("la historia larga sí crece sin tope",
       max(d[5] for d in datos) > 4)

# La prueba de fuga: si el último partido de A fuera enorme, ninguna
# fila anterior puede enterarse.
SERIE2 = [partido(d, "A", "B", "corners", 10, 2) for d in range(12)]
SERIE2.append(partido(12, "A", "B", "corners", 99, 2))
d1 = D.pronosticos(D.apariciones(SERIE, "corners"), ventana=4, min_previos=3)
d2 = D.pronosticos(D.apariciones(SERIE2, "corners"), ventana=4, min_previos=3)
prueba("agregar un partido al final no cambia ninguna predicción anterior",
       d2[:len(d1)] == d1)
# La primera predicción llega cuando A acumuló 3 apariciones; para
# entonces la liga vio exactamente 3 de A (10) y 3 de B (2), o sea 6.0.
# Un número distinto significa que contó valores que todavía no pasaron.
prueba("la media de la liga que ve cada fila es exactamente la previa",
       cerca(datos[0][1], 6.0))


print("\nelegir_k() — en train, y avisando si toca el borde\n")

# Equipos MUY distintos y constantes: no encoger es lo óptimo, y eso es
# el borde de abajo, que tiene significado propio.
MIXTO = []
for d in range(60):
    MIXTO.append(partido(d * 2, "A", "B", "corners", 12, 1))
    MIXTO.append(partido(d * 2 + 1, "C", "D", "corners", 12, 1))
dm = D.pronosticos(D.apariciones(MIXTO, "corners"), ventana=4, min_previos=3)
k, borde = D.elegir_k(dm, "largo")
prueba("con equipos muy distintos el óptimo es no encoger", k == 0)
prueba("y avisa que quedó en el borde de la grilla", borde is True)

# Equipos idénticos: toda la diferencia es ruido, conviene encoger todo.
import random as _r
_r.seed(7)
RUIDO = [partido(d, "A", "B", "corners", 5 + _r.gauss(0, 3), 5 + _r.gauss(0, 3))
         for d in range(300)]
dr = D.pronosticos(D.apariciones(RUIDO, "corners"), ventana=4, min_previos=3)
k2, borde2 = D.elegir_k(dr, "corto")
prueba("con equipos iguales conviene encoger fuerte", k2 >= 50)


print("\nbootstrap() — el ruido de la diferencia, pareado\n")

reales = [5.0, 7.0, 3.0, 6.0] * 30
iguales = [5.5] * 120
prueba("dos pronósticos idénticos no tienen diferencia que medir",
       cerca(D.bootstrap(reales, iguales, list(iguales), 200), 0.0))
ee = D.bootstrap(reales, iguales, [x + 0.4 for x in iguales], 200)
prueba("dos distintos sí tienen error estándar", ee > 0)
prueba("el mismo llamado da el mismo número (semilla fija)",
       cerca(ee, D.bootstrap(reales, iguales, [x + 0.4 for x in iguales], 200)))


print("\nmedir() — el veredicto entero\n")

prueba("con muestra chica no inventa un veredicto",
       D.medir(SERIE, "corners", 200) is None)

# Equipos estables y distintos: la historia larga tiene que ganarle
# tanto a la liga como a la ventana corta.
GRANDE = []
for d in range(400):
    GRANDE.append(partido(d, f"A{d % 6}", f"B{(d + 3) % 6}", "corners",
                          4 + (d % 6) * 2 + _r.gauss(0, 1.5),
                          4 + ((d + 3) % 6) * 2 + _r.gauss(0, 1.5)))
r = D.medir(GRANDE, "corners", 300)
prueba("el largo le gana a la media de la liga", r["mej_largo"] > 0)
prueba("y le gana también a la ventana corta", r["ganancia"] > 0)
prueba("con una ganancia que supera su propio ruido", r["ganancia"] > 2 * r["ee"])
prueba("cada pronóstico eligió su propio k",
       "k_corto" in r and "k_largo" in r)


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
