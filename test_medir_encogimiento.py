#!/usr/bin/env python3
"""Tests de medir_encogimiento.py — ¿conviene tirar el modelo hacia la
tasa base, y cuánto?

Por qué existe:

`TRASPASO.md` §5 midió el 2026-08-24 que encoger las probabilidades del
modelo hacia la frecuencia histórica mejora fuera de muestra, y dejó los
valores `k = 0.30` para arg y `0.20` para bra. Pero esos números se
midieron con `VIDA_MEDIA_DIAS` en 180, y hoy la constante está en 300.
Y el propio hallazgo de aquella medición dice que **cuanto más larga la
ventana, menos encogimiento hace falta** (0.40 → 0.30 al pasar de 45 a
180). O sea: los valores publicados están medidos en un régimen que ya
no corre, y aplicarlos tal cual sería usar un número vencido.

Lo que estos tests protegen, que es donde esta medición se rompe:

- **La partición temporal no puede filtrar futuro.** El `k` se elige con
  una época y se mide en otra. Si un partido del período de prueba entra
  al ajuste, el resultado se ve buenísimo y no significa nada — es el
  mismo error que `ventana_previa()` ya protege un nivel más abajo.
- **Un óptimo en el borde de la grilla no encontró nada** (regla dura de
  CLAUDE.md, quemada dos veces el 2026-08-24). Con una diferencia: acá
  `k = 0` es un borde con significado — quiere decir "no encoger" — y hay
  que poder distinguirlo del borde ciego de arriba.
- **La diferencia se compara contra el ruido, no contra cero.** Dos
  Brier medidos sobre los mismos partidos están pareados: la desviación
  que importa es la de la diferencia partido por partido, no la de cada
  uno por separado. Sin eso, cualquier k parece mejorar algo.
- **El encogimiento tiene que ser una mezcla de verdad**: k=0 deja el
  modelo intacto, k=1 lo borra, y en el medio sigue sumando 1.

    python test_medir_encogimiento.py
"""

import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
import medir_encogimiento as E

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


def fila(anio, modelo, base, real, mercado=None):
    return {"fecha": date(anio, 6, 1), "modelo": list(modelo),
            "base": list(base), "real": list(real),
            "mercado": list(mercado or [1 / 3, 1 / 3, 1 / 3])}


print("\nencoger() — la mezcla entre el modelo y la tasa base\n")

M = [0.70, 0.20, 0.10]
B = [0.45, 0.28, 0.27]

prueba("k=0 deja el modelo intacto", E.encoger(M, B, 0.0) == M)
prueba("k=1 lo reemplaza por la tasa base", E.encoger(M, B, 1.0) == B)
prueba("k=0.5 cae justo en el medio",
       cerca(E.encoger(M, B, 0.5)[0], 0.575))
prueba("sigue sumando 1", cerca(sum(E.encoger(M, B, 0.37)), 1.0))
prueba("nunca se sale del intervalo entre los dos",
       all(min(M[i], B[i]) <= E.encoger(M, B, 0.3)[i] <= max(M[i], B[i])
           for i in range(3)))


print("\npartir() — elegir con una época, medir en otra\n")

filas = [fila(a, M, B, [1, 0, 0]) for a in range(2012, 2027)]
aj, pr = E.partir(filas, 2022)

prueba("el ajuste queda entero antes del corte",
       all(f["fecha"].year < 2022 for f in aj))
prueba("la prueba queda entera desde el corte",
       all(f["fecha"].year >= 2022 for f in pr))
prueba("no se pierde ni se duplica ningún partido",
       len(aj) + len(pr) == len(filas))
prueba("y las dos partes tienen partidos", aj and pr)


print("\nmejor_k() — el barrido, y el borde de la grilla\n")

# Un modelo demasiado confiado: dice 90% y pasa el 50% de las veces.
# Encogerlo hacia una base honesta tiene que ayudar.
confiado = ([fila(2015, [0.90, 0.05, 0.05], [0.50, 0.25, 0.25], [1, 0, 0])] * 5 +
            [fila(2015, [0.90, 0.05, 0.05], [0.50, 0.25, 0.25], [0, 0, 1])] * 5)
r = E.mejor_k(confiado, E.GRILLA)
prueba("a un modelo pasado de confianza le encuentra encogimiento", r["k"] > 0)

# Un modelo ya perfecto: encogerlo solo puede empeorarlo.
justo = ([fila(2015, [0.50, 0.25, 0.25], [0.50, 0.25, 0.25], [1, 0, 0])] * 5 +
         [fila(2015, [0.50, 0.25, 0.25], [0.50, 0.25, 0.25], [0, 0, 1])] * 5)
r2 = E.mejor_k(justo, E.GRILLA)
prueba("a uno que ya está calibrado no le inventa encogimiento",
       r2["k"] == 0.0)
prueba("y k=0 NO se reporta como borde ciego: es una respuesta",
       r2["borde"] is False)

# Un caso que empuja al tope de la grilla: el modelo es basura y la base
# acierta. Ahí sí hay que avisar que la grilla se quedó corta.
basura = [fila(2015, [0.02, 0.02, 0.96], [0.60, 0.20, 0.20], [1, 0, 0])] * 10
r3 = E.mejor_k(basura, [0.0, 0.1, 0.2, 0.3])
prueba("si el óptimo pega contra el techo de la grilla, avisa",
       r3["k"] == 0.3 and r3["borde"] is True)

prueba("sin partidos no devuelve un k inventado", E.mejor_k([], E.GRILLA) is None)


print("\nbrier_medio() y la diferencia pareada contra el ruido\n")

prueba("un pronóstico perfecto da Brier 0",
       cerca(E.brier_medio([fila(2015, [1, 0, 0], B, [1, 0, 0])], 0.0), 0.0))
prueba("el tercio parejo da 2/3",
       cerca(E.brier_medio([fila(2015, [1/3, 1/3, 1/3], B, [1, 0, 0])], 0.0),
             2 / 3))

# Dos series idénticas: la diferencia es exactamente cero y sin ruido.
iguales = [fila(2015, M, M, [1, 0, 0]) for _ in range(50)]
d = E.diferencia_pareada(iguales, 0.0, 0.0)
prueba("misma predicción dos veces: la diferencia es cero", cerca(d["dif"], 0.0))
prueba("y su ruido también, así que no puede ser significativa",
       cerca(d["ee"], 0.0) and d["significativa"] is False)

# Una mejora chica sobre pocos partidos no alcanza; la misma mejora
# sostenida sobre muchos, sí. Es el punto entero de mirar el ruido.
mixtas = ([fila(2015, [0.9, 0.05, 0.05], [0.5, 0.25, 0.25], [1, 0, 0])] * 5 +
          [fila(2015, [0.9, 0.05, 0.05], [0.5, 0.25, 0.25], [0, 0, 1])] * 5)
poca = E.diferencia_pareada(mixtas, 0.0, 0.4)
mucha = E.diferencia_pareada(mixtas * 40, 0.0, 0.4)
prueba("con la misma señal, más partidos achican el ruido",
       mucha["ee"] < poca["ee"])
prueba("y el veredicto puede cambiar solo por tamaño de muestra",
       not poca["significativa"] and mucha["significativa"])
prueba("sin partidos no devuelve una diferencia", E.diferencia_pareada([], 0, 0) is None)


print("\natraso() — la métrica que importa, no la captura\n")

# La captura infla cuando el mercado le gana poco a la tasa base. El
# atraso contra el cierre no: es la distancia cruda a la que hay que
# apostar de verdad.
f = [fila(2015, [0.5, 0.25, 0.25], [0.45, 0.28, 0.27], [1, 0, 0],
          mercado=[0.55, 0.25, 0.20])] * 20
a = E.atraso(f, 0.0)
prueba("es positivo cuando el mercado predice mejor que nosotros", a > 0)
prueba("y no depende de la tasa base, que es lo que rompía la captura",
       cerca(a, E.atraso([dict(x, base=[0.9, 0.05, 0.05]) for x in f], 0.0)))


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
