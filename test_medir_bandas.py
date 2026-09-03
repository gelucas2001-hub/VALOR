#!/usr/bin/env python3
"""Tests de medir_bandas.py — la banda de cuota 4 a 10.

El script contesta una pregunta de Lucas y la contesta que NO. Un script
que devuelve un resultado negativo necesita tests igual que uno que
devuelve uno positivo: si mañana se rompe y empieza a decir que sí,
nadie lo va a mirar con la misma desconfianza.

Lo que se protege acá es sobre todo la ARITMÉTICA de la vara, porque de
ella depende que un resultado negativo sea creíble: que el ROI cuente
bien, que la banda agrupe por el borde correcto, y que las tres
selecciones de un partido salgan las tres.

    python test_medir_bandas.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")

import medir_bandas as B

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


def fila(cuotas, real, modelo=None, mercado=None, fecha="2024-01-01", liga="eng"):
    return {"cuotas": cuotas, "real": real,
            "modelo": modelo or [0.5, 0.3, 0.2],
            "mercado": mercado or [0.5, 0.3, 0.2],
            "fecha": fecha, "liga": liga, "n_previos": 100}


print("\nbanda_de() — los bordes, que es donde se cuenta mal\n")

prueba("1.99 cae en 1.5-2.0", B.banda_de(1.99) == (1.5, 2.0))
prueba("el borde exacto va a la banda de arriba", B.banda_de(2.0) == (2.0, 3.0))
prueba("4.0 abre la banda que motivó el script", B.banda_de(4.0) == (4.0, 6.0))
prueba("9.99 sigue adentro de 6-10", B.banda_de(9.99) == (6.0, 10.0))
prueba("10.0 ya no", B.banda_de(10.0) == (10.0, 999.0))
prueba("una cuota imposible no rompe", B.banda_de(0.5) is None)


print("\nselecciones() — un partido son TRES filas, no una\n")

f = fila([2.0, 3.5, 4.0], [1, 0, 0])
sel = B.selecciones([f])
prueba("salen las tres", len(sel) == 3)
prueba("con su lado bien puesto",
       [s["lado"] for s in sel] == ["local", "empate", "visita"])
prueba("y solo la que ocurrió cuenta como que pasó",
       [s["paso"] for s in sel] == [True, False, False])
prueba("una cuota rota se descarta sin tirar el partido",
       len(B.selecciones([fila([2.0, None, 4.0], [1, 0, 0])])) == 2)
prueba("una cuota de 1.00 tampoco entra: no es un precio",
       len(B.selecciones([fila([1.0, 3.5, 4.0], [1, 0, 0])])) == 2)


print("\nroi() — la vara. Si esto miente, todo el script miente\n")

# Cuota 2.00, mitad y mitad: rinde exactamente cero.
PAR = B.selecciones([fila([2.0, 3.0, 3.0], [1, 0, 0]),
                     fila([2.0, 3.0, 3.0], [0, 1, 0])])
loc = [s for s in PAR if s["lado"] == "local"]
prueba("acertar la mitad a cuota 2.00 da ROI cero", cerca(B.roi(loc)["roi"], 0.0))
prueba("y cuenta las dos", B.roi(loc)["n"] == 2)

perd = B.selecciones([fila([5.0, 3.0, 3.0], [0, 1, 0])] * 4)
perd = [s for s in perd if s["lado"] == "local"]
prueba("perder todas da -100%", cerca(B.roi(perd)["roi"], -100.0))
prueba("sin apuestas no inventa un número", B.roi([]) is None)


print("\nresumen() — las tres columnas que deciden\n")

# Decimos 30%, el mercado clava el 25%, y pasó una de cada cuatro.
# Ojo con el fixture: si el mercado dijera 20%, los dos Brier darían
# IGUAL — 0.30 y 0.20 están a la misma distancia de 0.25 — y el test
# pasaría por casualidad o fallaría sin que nada esté roto.
FS = ([fila([5.0, 3.0, 3.0], [1, 0, 0], modelo=[0.30, 0.4, 0.3], mercado=[0.25, 0.4, 0.35])]
      + [fila([5.0, 3.0, 3.0], [0, 1, 0], modelo=[0.30, 0.4, 0.3], mercado=[0.25, 0.4, 0.35])] * 3)
loc = [s for s in B.selecciones(FS) if s["lado"] == "local"]
r = B.resumen(loc)
prueba("promedia lo que decimos nosotros", cerca(r["nuestra"], 0.30))
prueba("y lo que dice el mercado", cerca(r["mercado"], 0.25))
prueba("y cuenta lo que pasó de verdad", cerca(r["real"], 0.25))
prueba("el Brier del mercado es mejor cuando el mercado acierta más",
       r["brier_m"] < r["brier_n"])
prueba("sin datos no devuelve ceros: devuelve None", B.resumen([]) is None)


print("\nla guarda contra el autoengaño\n")

# El bolsillo del local perdedor daba +5.52% en train y -7.85% en test.
# Sin el corte se reportaba como hallazgo. El corte es del 60% de las
# FECHAS distintas, no de las filas: si fuera de las filas, una jornada
# con muchos partidos correría el borde.
FECHAS = [fila([5.0, 3.0, 3.0], [1, 0, 0], fecha=f"2024-01-{d:02d}")
          for d in range(1, 11)]
sel = B.selecciones(FECHAS)
distintas = sorted({s["fecha"] for s in sel})
prueba("el corte sale de las fechas distintas, no de las filas",
       len(distintas) == 10 and len(sel) == 30)
prueba("el piso de muestra existe y no es simbólico", B.MIN_BANDA >= 100)
prueba("las bandas cubren desde 1.00 sin huecos",
       B.BANDAS[0][0] == 1.0 and all(B.BANDAS[i][1] == B.BANDAS[i+1][0]
                                     for i in range(len(B.BANDAS) - 1)))

print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
