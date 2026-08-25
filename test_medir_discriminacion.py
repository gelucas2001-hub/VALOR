#!/usr/bin/env python3
"""Tests de medir_discriminacion.py — ¿la app tiene opinión propia?

Por qué existe:

`medir_lineas.py` mide **calibración**: cuando decimos 60%, ¿pasa el
60%? Es necesario y no alcanza, y el 2026-08-25 se vio por qué.

Un pronóstico que le publica a TODOS los equipos el promedio de la liga
está perfectamente calibrado y no sirve para apostar absolutamente
nada. Calibra porque el promedio de la liga es, por definición, lo que
pasa en promedio. Y no sirve porque la casa también sabe el promedio de
la liga: no tenemos nada que agregar.

Eso es exactamente lo que estaba pasando con córners, remates y al
arco. Los 68 equipos recibían el mismo número (córners de 4.70 a 4.96,
un cuarto de córner entre el que más tira y el que menos), porque
`parametros_metricas()` devolvía `k = K_TOPE` — su forma honesta de
decir "con esta muestra no distingo un equipo de otro".

Lo que estos tests protegen:

- **Que calibración y discriminación no se confundan nunca más.** Hay un
  test que construye el pronóstico degenerado —siempre la media— y
  exige que la discriminación dé cero. Si algún día alguien "arregla"
  esto haciendo que ese caso puntúe bien, falla acá.
- **Que el piso de detección baje con la muestra**, que es lo que
  convierte "no se ve" en "todavía no se ve".
- **Que una métrica sin diferencias reales dé `k` en el tope**, y una
  con diferencias grandes dé `k` chico. Si se invierte, la tabla entera
  miente.
- **Que la señal se estime descontando el ruido de promediar pocos
  partidos.** Sin esa resta, cualquier métrica parece discriminar: los
  promedios de 4 partidos se separan solos por azar.

    python test_medir_discriminacion.py
"""

import random
import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_discriminacion as D

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


def liga(n_equipos, n_partidos, media, sd_equipo, sd_partido, semilla=7):
    """Una liga sintética con diferencias entre equipos CONOCIDAS.

    `sd_equipo` es cuánto se distinguen los equipos de verdad; si vale
    cero, son todos iguales y la medición tiene que decirlo.
    """
    r = random.Random(semilla)
    out = {}
    for t in range(n_equipos):
        propio = media + r.gauss(0, sd_equipo)
        out[str(t)] = [propio + r.gauss(0, sd_partido) for _ in range(n_partidos)]
    return out


print("\npiso_deteccion() — cuánta muestra hace falta para ver algo\n")

prueba("con más partidos por equipo el piso baja",
       D.piso_deteccion(10.0, 20) < D.piso_deteccion(10.0, 5))
prueba("y baja en proporción directa",
       cerca(D.piso_deteccion(10.0, 20), D.piso_deteccion(10.0, 5) / 4))
prueba("sin partidos no hay piso", D.piso_deteccion(10.0, 0) is None)


print("\nseparacion() — señal real, ya descontado el ruido de la muestra\n")

# Equipos IDÉNTICOS. Cualquier diferencia que se vea entre sus promedios
# es ruido de promediar pocos partidos, y tiene que quedar descontada.
#
# Con UNA sola liga sintética esto no se puede afirmar, y el primer
# intento de estos tests se estrelló justo ahí: pedía `entre <= 0.15` y
# la semilla 7 daba +0.198. El código estaba bien — con 60 equipos de 4
# partidos, la estimación de `entre` baila ±0.3 alrededor de cero por
# puro azar. Un umbral mágico adentro de esa banda no mide nada.
#
# Así que se mira la DISTRIBUCIÓN sobre varias semillas: tiene que
# quedar centrada en cero (cruzando para los dos lados) y quedar chica
# contra el piso de detección, que es lo que "invisible" quiere decir.
muchas = [D.separacion(liga(60, 4, 5.0, 0.0, 2.5, semilla=s))
          for s in range(7, 27)]
entres = sorted(x["entre"] for x in muchas)
mediana = entres[len(entres) // 2]
iguales = liga(60, 4, media=5.0, sd_equipo=0.0, sd_partido=2.5)
r = D.separacion(iguales)

prueba("equipos iguales: la señal queda centrada en cero",
       abs(mediana) < 0.15)
prueba("y cruza para los dos lados, o sea que no está sesgada",
       entres[0] < 0 < entres[-1])
prueba("el k queda en el tope en la mediana",
       sorted(x["k"] for x in muchas)[len(muchas) // 2] >= D.K_TOPE * 0.9)

# Y acá el hallazgo incómodo, que también se testea porque es lo que
# obliga a existir a `falsa_senal()`: con cuatro partidos por equipo el
# estimador NO es confiable. Sobre 40 ligas de equipos idénticos
# reportó "se distingue" 14 veces. No es un defecto del código — es lo
# que la muestra da de sí — pero significa que un `entre` positivo con
# esta cantidad de partidos no alcanza para afirmar nada.
def falsas(pj, n=40):
    xs = [D.separacion(liga(60, pj, 5.0, 0.0, 2.5, semilla=s))
          for s in range(7, 7 + n)]
    return sum(1 for x in xs if x["veredicto"] == "se distingue")


f4, f20 = falsas(4), falsas(20)
prueba("con 4 partidos por equipo el estimador da falsa señal seguido",
       f4 >= 8)
prueba("y con 20 deja de darla", f20 == 0)
prueba("o sea que el problema es la muestra, no el método", f20 < f4)


print("\nfalsa_senal() — el techo que hay que superar para creerle\n")

techo4 = D.falsa_senal(60, 4)
techo20 = D.falsa_senal(60, 20)
prueba("devuelve un techo positivo", techo4 and techo4 > 0)
prueba("y con más partidos por equipo el techo baja", techo20 < techo4)

# Equipos idénticos: casi ninguno tiene que superar su propio techo.
# Es la definición del percentil 95, y es lo que hace que la referencia
# sirva para algo.
cruzan = sum(1 for x in muchas
             if x["piso"] and abs(x["entre"]) / x["piso"] > techo4)
prueba("equipos iguales casi nunca superan el techo", cruzan <= 3)

# Equipos realmente distintos sí tienen que superarlo, o la referencia
# estaría tapando hallazgos de verdad.
d = D.separacion(liga(60, 4, 5.0, 2.0, 2.5, semilla=5))
prueba("equipos distintos lo superan holgadamente",
       abs(d["entre"]) / d["piso"] > techo4 * 2)
prueba("sin muestra no devuelve un techo inventado",
       D.falsa_senal(60, 1) is None)

# Equipos MUY distintos entre sí. Tiene que verse aunque haya ruido.
distintos = liga(60, 4, media=5.0, sd_equipo=2.0, sd_partido=2.5)
r2 = D.separacion(distintos)
prueba("equipos distintos: la señal aparece", r2["entre"] > 1.0)
prueba("y el k baja a algo utilizable", r2["k"] < 20)
prueba("con veredicto de que se distingue", r2["veredicto"] == "se distingue")

prueba("más señal siempre da menos k", r2["k"] < r["k"])
prueba("sin equipos suficientes no inventa un número",
       D.separacion({"a": [1, 2], "b": [1, 2]}) is None)


print("\nLo mismo, con MÁS partidos por equipo\n")

# La misma liga de equipos apenas distintos, vista con 4 y con 30
# partidos. Con 4 el ruido la tapa; con 30 tiene que asomar. Es la
# diferencia entre "no hay señal" y "todavía no la vemos".
sutil4 = liga(60, 4, media=5.0, sd_equipo=0.7, sd_partido=2.5, semilla=11)
sutil30 = liga(60, 30, media=5.0, sd_equipo=0.7, sd_partido=2.5, semilla=11)
a, b = D.separacion(sutil4), D.separacion(sutil30)
prueba("con 30 partidos el piso de detección es mucho más bajo",
       b["piso"] < a["piso"] / 3)
prueba("y la señal sutil se ve mejor con más muestra", b["k"] < a["k"])


print("\ndiscriminacion() — el test que separa esto de la calibración\n")

# EL caso. Un pronóstico que le da a todos los equipos el promedio de
# la liga está perfectamente calibrado y no discrimina nada. Si esto
# alguna vez puntúa bien, la métrica dejó de medir lo que dice medir.
r = random.Random(3)
reales = [5.0 + r.gauss(0, 2.5) for _ in range(400)]
media = sum(reales) / len(reales)

plano = D.discriminacion([(media, x) for x in reales])
prueba("el pronóstico que siempre dice la media no discrimina nada",
       plano is None or cerca(plano["pendiente"], 0.0) or plano["sd_pred"] < 1e-9)

# Un pronóstico que SÍ sabe algo: la mitad de la diferencia real.
sabe = D.discriminacion([(media + (x - media) * 0.5, x) for x in reales])
prueba("uno que acierta la mitad de la diferencia da pendiente ~2",
       1.5 < sabe["pendiente"] < 2.5)

perfecto = D.discriminacion([(x, x) for x in reales])
prueba("uno perfecto da pendiente 1", cerca(perfecto["pendiente"], 1.0, 1e-6))
prueba("y explica toda la variación", perfecto["r2"] > 0.999)

prueba("sin casos no devuelve nada", D.discriminacion([]) is None)
prueba("con un solo caso tampoco", D.discriminacion([(1.0, 2.0)]) is None)


print("\nspread() — cuánto se separan los números que la app publicaría\n")

prueba("con k en el tope, todos los equipos reciben casi lo mismo",
       D.spread(distintos, media=5.0, k=D.K_TOPE) < 0.3)
prueba("con k chico, los números se abren",
       D.spread(distintos, media=5.0, k=2.0) >
       D.spread(distintos, media=5.0, k=D.K_TOPE))
prueba("y ese es el número que delata el problema, no la calibración",
       D.spread(iguales, media=5.0, k=D.K_TOPE) < 0.3)


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
