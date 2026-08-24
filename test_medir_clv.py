#!/usr/bin/env python3
"""Tests de medir_clv.py

El CLV (closing line value) es la unica metrica que dice si hay ventaja
sin esperar cientos de apuestas. La idea: si nuestro modelo sabe algo
que el mercado todavia no puso en el precio, entonces cuando le
discrepamos a la cuota, la cuota deberia MOVERSE hacia nosotros antes
del inicio.

Estos tests existen para que el script pueda decir que NO. Se le pasa
ruido y tiene que no encontrar nada; se le pasa una senal de verdad y
tiene que encontrarla.

    python test_medir_clv.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_clv as m

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


print("")
print("devig() — sacarle el margen a la cuota para poder comparar")
print("")

# Una cuota no es una probabilidad: las tres del 1X2 suman mas de 1
# porque ahi vive la ganancia de la casa. Sin sacarlo, cualquier
# comparacion contra el modelo esta sesgada a favor nuestro.
p = m.devig([2.65, 2.90, 2.95])
prueba("devuelve tres probabilidades", len(p) == 3)
prueba("suman exactamente 1", abs(sum(p) - 1) < 1e-9)
prueba("la mas barata es la mas probable", p[0] > p[1] and p[0] > p[2])
prueba("un mercado sin margen no se distorsiona",
       all(abs(x - 1/3) < 1e-9 for x in m.devig([3.0, 3.0, 3.0])))
prueba("una cuota faltante invalida el mercado", m.devig([2.0, None, 3.0]) is None)
prueba("una cuota imposible tambien", m.devig([2.0, 0, 3.0]) is None)
prueba("una lista vacia no rompe", m.devig([]) is None)

print("")
print("movimientos() — cuanto se movio la linea entre la primera foto y la ultima")
print("")

def hist(*fotos):
    return [dict(t=f"t{i}", lh=1.4, la=1.0, rho=0.05,
                 local=f[0], empate=f[1], visitante=f[2],
                 totalLinea=2.5, totalOver=2.0, totalUnder=1.8)
            for i, f in enumerate(fotos)]

CU = {"e1": hist((2.65, 2.90, 2.95), (2.40, 3.00, 3.10))}
mv = m.movimientos(CU)
prueba("saca una fila por mercado del partido", len(mv) >= 3)
loc = next(x for x in mv if x["mercado"] == "1X2 local")
prueba("la apertura es de la primera foto", abs(loc["cuota_open"] - 2.65) < 1e-9)
prueba("el cierre es de la ultima", abs(loc["cuota_close"] - 2.40) < 1e-9)
prueba("el local se acorto, asi que su probabilidad de cierre subio",
       loc["p_close"] > loc["p_open"])
prueba("trae la probabilidad del modelo", 0 < loc["p_modelo"] < 1)

prueba("un partido con una sola foto no aporta movimiento",
       m.movimientos({"e2": hist((2.0, 3.0, 4.0))}) == [])
prueba("sin cuotas no rompe", m.movimientos({}) == [])

print("")
print("veredicto() — puede y debe decir que no")
print("")

import random
random.seed(4)
# Ruido puro: nuestra discrepancia no tiene nada que ver con el movimiento.
ruido = [{"mercado": "x", "p_modelo": random.random(), "p_open": 0.5,
          "p_close": 0.5 + random.uniform(-0.05, 0.05), "cuota_open": 2.0}
         for _ in range(120)]
v = m.veredicto(ruido)
prueba("con ruido no encuentra ventaja", not v["hay_senal"])
prueba("informa el p-valor", 0 <= v["p"] <= 1)
prueba("y cuantos casos miro", v["n"] == 120)

# Senal real: la linea siempre se mueve hacia donde apuntaba el modelo.
senal = []
for _ in range(120):
    base = 0.5
    d = random.uniform(-0.15, 0.15)
    senal.append({"mercado": "x", "p_modelo": base + d, "p_open": base,
                  "p_close": base + d * 0.6, "cuota_open": 2.0})
prueba("si la linea se mueve hacia nosotros, lo detecta", m.veredicto(senal)["hay_senal"])

prueba("con muy pocos casos no concluye", m.veredicto(ruido[:5])["hay_senal"] is False)
prueba("sin casos no rompe", m.veredicto([])["n"] == 0)

# El numero que le importa al bolsillo: cuota tomada por probabilidad de
# cierre, menos 1. Positivo = conseguiste mejor precio que el cierre.
print("")
print("clv_medio() — el numero que va al bolsillo")
print("")
prueba("cuota mejor que el cierre da CLV positivo",
       m.clv_medio([{"cuota_open": 2.50, "p_close": 0.50}]) > 0)
prueba("cuota peor que el cierre da CLV negativo",
       m.clv_medio([{"cuota_open": 1.80, "p_close": 0.50}]) < 0)
prueba("cuota igual al cierre da cero",
       abs(m.clv_medio([{"cuota_open": 2.00, "p_close": 0.50}])) < 1e-9)
prueba("sin casos devuelve None", m.clv_medio([]) is None)

print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
