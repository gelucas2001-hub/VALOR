#!/usr/bin/env python3
"""Tests de medir_props.py — las líneas de jugador contra plata.

Qué protegen, que es donde esta medición se rompe:

- **El cruce de nombres.** Bet365 y ESPN escriben distinto, pero
  "Clever Ferreira" y "Pablo Ferreira" son personas distintas. Solo
  igualdad exacta después de normalizar, y un nombre que reclaman dos
  jugadores queda AFUERA en vez de irse con el último.
- **La vara del CLV.** Si la casa achica el margen sobre la hora, todos
  los precios bajan y cualquier selección muestra CLV positivo sin
  haber elegido nada. Por eso se mide también la deriva de los
  escalones que NO apostamos: lo que dice si elegimos bien es la
  diferencia.
- **El ROI al precio real.** Sin quitarle el margen: es la plata que se
  cobra, no una probabilidad limpia.
- **La ventana de ventaja tiene techo.** Una ventaja del 40% contra una
  casa no es una ventaja, es una línea que leímos mal.

    python test_medir_props.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_props as P

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def cerca(a, b, tol=1e-6):
    return abs(a - b) < tol


print("\nnorma() — lo justo, y nada más\n")

prueba("saca acentos", P.norma("Lucas Beltrán") == "lucas beltran")
prueba("saca apóstrofos", P.norma("N'Golo Kante") == "n golo kante")
prueba("saca guiones", P.norma("Pierre-Emerick") == "pierre emerick")
prueba("normaliza espacios", P.norma("  Ángel   Di  María ") == "angel di maria")
prueba("NO acorta nombres: dos jugadores distintos no se funden",
       P.norma("Clever Ferreira") != P.norma("Pablo Ferreira"))
prueba("y no toca el orden de las palabras",
       P.norma("Willian Jose") != P.norma("Jose Willian"))


print("\nindice_jugadores() — un nombre ambiguo queda afuera\n")

PLANTEL = {
    "1": [{"id": "10", "nombre": "Lucas Beltrán"},
          {"id": "11", "nombre": "Thiago Almada"}],
    "2": [{"id": "20", "nombre": "Juan Pérez"}],
    "3": [{"id": "30", "nombre": "Juan Perez"}],
}
idx = P.indice_jugadores(PLANTEL)

prueba("cruza por igualdad exacta normalizada", idx.get("lucas beltran") == "10")
prueba("el acento no rompe el cruce", idx.get("thiago almada") == "11")
prueba("un nombre que reclaman DOS jugadores queda afuera del índice",
       "juan perez" not in idx)
prueba("y no se lo queda el último que pasó",
       idx.get("juan perez") not in ("20", "30"))
prueba("sin id o sin nombre no entra",
       P.indice_jugadores({"1": [{"id": "9"}, {"nombre": "X"}]}) == {})


print("\nseries_props() y escalera() — leer la foto de la casa\n")

PROPS = {
    "espn999__remates__Thiago Almada": [
        {"t": "2026-08-26T14:30", "fecha": "2026-08-26",
         "lineas": {"2.5": 1.80, "1.5": 1.20}},
        {"t": "2026-08-26T07:07", "fecha": "2026-08-26",
         "lineas": {"2.5": 2.00, "1.5": 1.25}},
    ],
}
ser = P.series_props(PROPS)
clave = ("999", "remates", "Thiago Almada")

prueba("la clave se parte en evento, métrica y nombre", clave in ser)
prueba("el 'espn' del id se saca para poder cruzar con el caché",
       list(ser)[0][0] == "999")
prueba("las fotos quedan ordenadas por hora, no como vinieron",
       [f["t"] for f in ser[clave]] == ["2026-08-26T07:07", "2026-08-26T14:30"])
prueba("la escalera sale ordenada por línea",
       P.escalera(ser[clave][0]) == [(1.5, 1.25), (2.5, 2.0)])
prueba("una línea que no es número no rompe la escalera",
       P.escalera({"lineas": {"2.5": 1.8, "ajaja": "x"}}) == [(2.5, 1.8)])
prueba("sin fotos la serie no existe",
       P.series_props({"espn1__remates__X": []}) == {})


print("\nroi() — al precio real, con el margen adentro\n")

def fila(ev_esp, precio, paso, cierre=None):
    return {"ev_esperado": ev_esp, "precio": precio, "paso": paso,
            "cierre": cierre, "met": "remates"}

# Cuatro apuestas a 2.00: dos aciertan, dos no. Rinde exactamente cero.
PAR = [fila(0.10, 2.0, 1), fila(0.10, 2.0, 1), fila(0.10, 2.0, 0), fila(0.10, 2.0, 0)]
r = P.roi(PAR, 0.04)
prueba("acertar la mitad a cuota 2.00 da ROI cero", cerca(r["roi"], 0.0))
prueba("cuenta las apuestas jugadas", r["n"] == 4)
prueba("y los aciertos", cerca(r["aciertos"], 50.0))

prueba("perder todas da -100%",
       cerca(P.roi([fila(0.10, 3.0, 0)] * 5, 0.04)["roi"], -100.0))
prueba("una ventaja por debajo del piso no se juega",
       P.roi([fila(0.01, 2.0, 1)], 0.04) is None)
prueba("y una absurdamente alta tampoco: es una línea mal leída",
       P.roi([fila(0.90, 2.0, 1)], 0.04) is None)
prueba("el techo se puede mover a propósito",
       P.roi([fila(0.90, 2.0, 1)], 0.04, techo=1.0) is not None)


print("\nclv() y deriva() — la vara sin la cual el CLV no dice nada\n")

# Apostamos a 2.20 y cierra 2.00: el mercado se movió hacia nosotros.
JUGADAS = [fila(0.10, 2.20, 1, cierre=2.00)] * 4
c = P.clv(JUGADAS, 0.04)
prueba("apostar más caro de lo que cierra da CLV positivo", c["clv"] > 0)
prueba("y el número es el que corresponde", cerca(c["clv"], 10.0))
prueba("si cierra más caro, el CLV es negativo",
       P.clv([fila(0.10, 2.00, 1, cierre=2.20)], 0.04)["clv"] < 0)
prueba("sin foto de cierre esa fila no entra al CLV",
       P.clv([fila(0.10, 2.0, 1)], 0.04) is None)

# El confundidor: TODOS los escalones se mueven igual. Ahí el CLV de lo
# que apostamos es real pero no es mérito nuestro.
TODOS = [fila(0.001, 2.20, 0, cierre=2.00)] * 20 + JUGADAS
d = P.deriva(TODOS)
prueba("la deriva mira todos los escalones, se apuesten o no", d["n"] == 24)
prueba("cuando todo el mercado se mueve igual, la deriva lo captura",
       cerca(d["clv"], 10.0))
prueba("y ahí elegir no aporta nada: la diferencia es cero",
       cerca(P.clv(TODOS, 0.04)["clv"] - d["clv"], 0.0))

# Y el caso bueno: solo lo que elegimos se mueve.
MIXTO = [fila(0.001, 2.00, 0, cierre=2.00)] * 20 + JUGADAS
prueba("si solo se mueve lo que elegimos, la diferencia se despega",
       P.clv(MIXTO, 0.04)["clv"] - P.deriva(MIXTO)["clv"] > 5)
prueba("sin ninguna foto de cierre no hay deriva que medir",
       P.deriva([fila(0.10, 2.0, 1)]) is None)


print("\ndejar_uno_afuera() y sin_movimiento() — los dos controles que "
      "encontraron\nque la señal era un solo partido\n")

# Nueve apuestas sin movimiento y cinco de UN evento que se movieron
# fuerte: el promedio da lindo y no hay señal.
UNO = ([dict(fila(0.10, 2.0, 0, cierre=2.0), ev="A") for _ in range(9)]
       + [dict(fila(0.10, 2.4, 0, cierre=2.0), ev="B") for _ in range(5)])
fuera = P.dejar_uno_afuera(UNO, 0.04)
prueba("recalcula el CLV sacando cada partido por vez", len(fuera) == 2)
sinB = [f for f in fuera if f["sin"] == "B"][0]
prueba("sacando el partido que lo sostiene, el CLV se desarma",
       cerca(sinB["clv"], 0.0))
prueba("y sacando cualquier otro, no cambia casi nada",
       [f for f in fuera if f["sin"] == "A"][0]["clv"] > 15)

q = P.sin_movimiento(UNO, 0.04)
prueba("cuenta las apuestas con la línea clavada", q["quietas"] == 9)
prueba("y las expresa como fracción", cerca(q["pct"], 9 / 14 * 100))
prueba("una linea que se movio no cuenta como quieta",
       P.sin_movimiento([dict(fila(0.10, 2.4, 0, cierre=2.0), ev="A")],
                        0.04)["quietas"] == 0)
prueba("sin apuestas no inventa un porcentaje",
       P.sin_movimiento([fila(0.001, 2.0, 0, cierre=2.0)], 0.04) is None)


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
