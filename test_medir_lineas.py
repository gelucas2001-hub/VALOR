#!/usr/bin/env python3
"""Tests de medir_lineas.py — la calibración del mercado de estadísticas.

Por qué existe:

El mercado de córners, tarjetas y remates estaba construido, escondido
en la pestaña Plantel, y **nunca medido**. Hay `medir_analisis.py`,
`medir_arbitros.py`, `medir_clv.py`, `medir_sesgo.py` y
`medir_historico.py`; no había `medir_lineas.py`. O sea que la app venía
diciendo "62% de que pase 9.5 córners" sin que nadie hubiera comprobado
que cuando dice 62%, pasa el 62%.

Es exactamente el agujero que el 2026-08-24 se descubrió en el modelo de
goles — tres semanas midiendo todo menos si servía — repetido en el
mercado nuevo.

Lo que estos tests protegen:

- que `prob_mayor` sea el MISMO cálculo que corre en `index.html`, y no
  una segunda implementación que se le parezca. Un modelo que se
  bifurca en dos versiones miente sin avisar;
- las tres campanas: binomial negativa cuando la métrica se despatarra
  más que Poisson, binomial cuando es más regular, Poisson en el medio;
- que la medición no mire el futuro.

    python test_medir_lineas.py
"""

import datetime
import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_lineas as L

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


print("\nprob_mayor() — la chance de pasar una línea\n")

# Una línea de 4.5 quiere decir "5 o más": el lado estricto, sin empate.
# Con Poisson de media 3, P(X >= 5) se puede calcular a mano.
import math
esperado = 1 - sum(math.exp(-3) * 3**k / math.factorial(k) for k in range(5))
prueba("Poisson coincide con el cálculo a mano",
       abs(L.prob_mayor(3.0, 1.0, 4.5) - esperado) < 1e-9)

prueba("una línea más alta es menos probable",
       L.prob_mayor(9.0, 1.75, 10.5) < L.prob_mayor(9.0, 1.75, 8.5))
prueba("más esperado, más chance de pasar la misma línea",
       L.prob_mayor(11.0, 1.75, 9.5) > L.prob_mayor(8.0, 1.75, 9.5))
prueba("siempre entre 0 y 1",
       all(0 <= L.prob_mayor(m, d, l) <= 1
           for m in (0.5, 3, 9, 20) for d in (0.5, 1.0, 3.0) for l in (0.5, 9.5, 30.5)))

# El punto de todo el bloque: no usar Poisson para todo. Una métrica
# despatarrada (remates, disp 2.95) tiene colas más gordas, y una
# regular (tarjetas, disp 0.72) más flacas.
prueba("la binomial negativa engorda la cola de arriba",
       L.prob_mayor(13.6, 3.0, 19.5) > L.prob_mayor(13.6, 1.0, 19.5))
prueba("la binomial la adelgaza",
       L.prob_mayor(4.5, 0.7, 8.5) < L.prob_mayor(4.5, 1.0, 8.5))
prueba("cerca de 1 se comporta como Poisson",
       abs(L.prob_mayor(9.0, 1.0, 9.5) - L.prob_mayor(9.0, 1.02, 9.5)) < 0.01)

prueba("sin media no inventa", L.prob_mayor(None, 1.0, 9.5) is None)
prueba("una media de cero tampoco", L.prob_mayor(0, 1.0, 9.5) is None)
prueba("sin línea tampoco", L.prob_mayor(9.0, 1.0, None) is None)
prueba("una línea negativa siempre se pasa", L.prob_mayor(9.0, 1.0, -1) == 1)


print("\nes el MISMO cálculo que el de index.html\n")

# Si las dos implementaciones se separan, la medición deja de decir algo
# sobre lo que el usuario ve. Se comparan sobre una grilla, no sobre un
# caso suelto.
casos = [(mu, d, l) for mu in (2.0, 4.5, 9.0, 13.6)
         for d in (0.72, 1.0, 1.75, 2.95) for l in (1.5, 4.5, 9.5, 14.5)]
try:
    jsv = L.prob_mayor_js(casos)
    peor = max(abs(L.prob_mayor(*c) - j) for c, j in zip(casos, jsv))
    prueba(f"coincide con el JS en {len(casos)} casos (peor {peor:.2e})", peor < 1e-9)
except FileNotFoundError:
    prueba("node disponible para comparar contra el JS", False)


print("\ncalibracion() — cuando decimos 60%, ¿pasa el 60%?\n")

filas = [{"p": 0.9, "paso": 1} for _ in range(90)] + \
        [{"p": 0.9, "paso": 0} for _ in range(10)]
b = L.calibracion(filas)
prueba("una predicción perfecta no muestra desvío",
       abs(b[0]["dicho"] - b[0]["paso"]) < 1e-9)

malas = [{"p": 0.9, "paso": 1} for _ in range(50)] + \
        [{"p": 0.9, "paso": 0} for _ in range(50)]
b2 = L.calibracion(malas)
prueba("un exceso de confianza se ve", b2[0]["dicho"] - b2[0]["paso"] > 0.35)
prueba("cada banda declara sobre cuántos casos va", b2[0]["n"] == 100)
prueba("sin datos no rompe", L.calibracion([]) == [])


print("\nno mirar el futuro\n")

hist = [{"fecha": datetime.date(2026, 3, d), "eid": str(d)} for d in (1, 5, 9)]
prev = L.previos(hist, datetime.date(2026, 3, 5))
prueba("solo lo estrictamente anterior",
       [x["eid"] for x in prev] == ["1"])
prueba("un partido del mismo día no cuenta",
       L.previos(hist, datetime.date(2026, 3, 1)) == [])


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
