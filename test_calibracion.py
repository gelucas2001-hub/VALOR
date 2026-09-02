#!/usr/bin/env python3
"""Tests del medidor de calibración.

La pregunta que responde el script: cuando la app dice 70%, ¿pasa el
70% de las veces? Es distinta de "¿acierta?" — un modelo puede acertar
mucho y estar mal calibrado, y ahí el EV que calcula es una ilusión.

Salió de un reporte de Lucas usando la app varios días. Medido después
sobre la escalera: la franja "Lo más probable" promete 79% y da 62%.
Estos tests protegen los números con los que se decide si el modelo hay
que tocarlo — un medidor con un bug te hace corregir lo que no está roto.

    python test_calibracion.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_calibracion as C

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


print("\nbanda_de() — a qué franja de probabilidad pertenece\n")

prueba("0.05 cae en la banda más baja", C.banda_de(0.05) == (0.0, 0.1))
prueba("0.62 cae en 60-70", C.banda_de(0.62) == (0.6, 0.7))
prueba("el borde exacto va a la banda de arriba", C.banda_de(0.70) == (0.7, 0.8))
prueba("1.0 no se sale de la última banda", C.banda_de(1.0) == (0.9, 1.0))
prueba("0.0 entra en la primera", C.banda_de(0.0) == (0.0, 0.1))


print("\ncalibrar() — predicho contra observado\n")

# Un modelo perfectamente calibrado: dice 0.8 diez veces y pasa 8.
perfecto = [(0.8, True)] * 8 + [(0.8, False)] * 2
c = C.calibrar(perfecto)
b = c[(0.8, 0.9)]
prueba("agrupa en la banda correcta", b["n"] == 10)
prueba("el predicho es el promedio de las probabilidades", abs(b["pred"] - 0.8) < 1e-9)
prueba("el observado es la frecuencia real", abs(b["real"] - 0.8) < 1e-9)
prueba("sin desvío cuando está calibrado", abs(b["desvio"]) < 1e-9)

# Sobreconfianza: dice 0.8 y pasa 0.5. El desvío tiene que ser negativo
# (prometió de más), que es la dirección que encontramos en la escalera.
sobre = [(0.8, True)] * 5 + [(0.8, False)] * 5
d = C.calibrar(sobre)[(0.8, 0.9)]
prueba("detecta sobreconfianza", d["desvio"] < 0)
prueba("mide cuánta sobreconfianza", abs(d["desvio"] - (-0.3)) < 1e-9)

# Y la dirección contraria, para que el signo no quede al azar.
bajo = [(0.3, True)] * 6 + [(0.3, False)] * 4
e = C.calibrar(bajo)[(0.3, 0.4)]
prueba("detecta subestimación con signo positivo", e["desvio"] > 0)

prueba("sin datos no rompe", C.calibrar([]) == {})

# Bandas separadas no se mezclan.
mixto = [(0.2, False), (0.2, False), (0.9, True), (0.9, True)]
m = C.calibrar(mixto)
prueba("cada banda cuenta por su lado", len(m) == 2)
prueba("la banda baja tiene sus casos", m[(0.2, 0.3)]["n"] == 2)


print("\nbrier() — el resumen en un número\n")

# Brier es el error cuadrático medio. 0 es perfecto, 0.25 es decir
# siempre 50%, y 1 es equivocarse con total confianza.
prueba("predicción perfecta da 0", C.brier([(1.0, True), (0.0, False)]) == 0.0)
prueba("decir siempre 50% da 0.25", C.brier([(0.5, True), (0.5, False)]) == 0.25)
prueba("equivocarse confiado da 1", C.brier([(1.0, False)]) == 1.0)
prueba("sin datos devuelve None", C.brier([]) is None)


print("\nfiabilidad() — cuánta muestra hace falta para creerle a una banda\n")

# Con 4 casos, una banda que se desvía 20 puntos no dice nada: el error
# estándar es enorme. El script tiene que distinguir señal de ruido, o
# induce a tocar el modelo por azar — justo lo que el repo prohíbe.
prueba("con muestra chica, no es confiable", not C.fiabilidad(0.8, 0.6, 4))
prueba("con muestra grande y desvío grande, sí", C.fiabilidad(0.8, 0.6, 200))
prueba("con muestra grande y desvío chico, no hay señal",
       not C.fiabilidad(0.80, 0.79, 200))
prueba("cero casos no divide por cero", not C.fiabilidad(0.8, 0.6, 0))

print("\npatron() y CAMBIOS_MODELO — no promediar dos modelos distintos\n")

# El caso real: el 2026-09-02 este script gritaba SOBRE-DISPERSION sobre
# 85 partidos que cruzaban por el medio la correccion de escala del
# 2026-08-30. Partido en dos, el defecto esta de un lado y no del otro.
SOBRE = ([(0.85, False)] * 30 + [(0.85, True)] * 70 +
         [(0.15, True)] * 30 + [(0.15, False)] * 70)
pat = C.patron(C.calibrar(SOBRE))
prueba("patron() ve la sobre-dispersion: altas por debajo", pat[0] < -0.02)
prueba("y bajas por encima", pat[1] > 0.02)

SANO = ([(0.85, True)] * 85 + [(0.85, False)] * 15 +
        [(0.15, True)] * 15 + [(0.15, False)] * 85)
pat2 = C.patron(C.calibrar(SANO))
prueba("y no la inventa cuando el modelo esta calibrado",
       abs(pat2[0]) < 0.02 and abs(pat2[1]) < 0.02)
prueba("sin muestra en las puntas devuelve None",
       C.patron(C.calibrar([(0.5, True)] * 5)) is None)
prueba("sin datos tampoco rompe", C.patron({}) is None)

prueba("hay al menos un cambio de modelo declarado", len(C.CAMBIOS_MODELO) >= 1)
prueba("cada entrada es fecha ISO + motivo escrito",
       all(len(f) == 10 and f[4] == "-" and f[7] == "-" and m.strip()
           for f, m in C.CAMBIOS_MODELO))
prueba("estan en orden cronologico: el ultimo es el corte vigente",
       [f for f, _ in C.CAMBIOS_MODELO] == sorted(f for f, _ in C.CAMBIOS_MODELO))

# El filtro por fecha es lo que hace posible no mezclar.
_d, _, _n = C.cargar_pares(desde=C.CAMBIOS_MODELO[-1][0])
_h, _, _m = C.cargar_pares(hasta=C.CAMBIOS_MODELO[-1][0])
_t, _, _tot = C.cargar_pares()
prueba("los dos tramos suman el total y no se pisan", _n + _m == _tot)
prueba("y ninguno se queda con todo", _n > 0 and _m > 0)

print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
