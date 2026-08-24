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
print("devig_shin() — el margen no se reparte parejo")
print("")

# El devig proporcional le saca el mismo porcentaje a las tres opciones.
# Shin (1993) parte de que el margen refleja apuestas informadas y le saca
# proporcionalmente MAS al que paga mucho — corrige el sesgo
# favorito-longshot, por el que la probabilidad implicita de un
# batacazo esta siempre inflada. El repo que lo usa como referencia lo
# llama "la estimacion mas defendible del precio de cierre".
CUOTAS = [1.50, 4.20, 7.00]
prop = m.devig(CUOTAS)
shin = m.devig_shin(CUOTAS)

prueba("devuelve una probabilidad por opcion", len(shin) == 3)
prueba("suman exactamente 1", abs(sum(shin) - 1) < 1e-6)
prueba("respeta el orden (el favorito sigue siendo el favorito)",
       shin[0] > shin[1] > shin[2])
prueba("al favorito le deja MAS que el proporcional", shin[0] > prop[0])
prueba("al batacazo le saca MAS que el proporcional", shin[2] < prop[2])
prueba("y la diferencia no es de redondeo", abs(shin[2] - prop[2]) > 1e-4)

# Sin margen no hay nada que sacar: los dos metodos tienen que coincidir.
justas = [3.0, 3.0, 3.0]
prueba("un mercado sin margen no se distorsiona",
       all(abs(a - b) < 1e-6 for a, b in zip(m.devig_shin(justas), m.devig(justas))))

# Un mercado de dos opciones no tiene la asimetria que Shin corrige.
dos = m.devig_shin([1.80, 2.10])
prueba("un mercado de dos vias sigue sumando 1", abs(sum(dos) - 1) < 1e-6)

prueba("una cuota faltante invalida el mercado", m.devig_shin([2.0, None, 3.0]) is None)
prueba("una cuota imposible tambien", m.devig_shin([2.0, 0, 3.0]) is None)
prueba("una lista vacia no rompe", m.devig_shin([]) is None)

# Con margenes grandes la cuenta tiene que seguir cerrando.
prueba("con margen alto sigue sumando 1",
       abs(sum(m.devig_shin([1.20, 6.00, 15.0])) - 1) < 1e-6)
prueba("con un favorito extremo sigue sumando 1",
       abs(sum(m.devig_shin([1.02, 25.0, 60.0])) - 1) < 1e-6)

print("")
print("movimientos() usa Shin, no el proporcional")
print("")

# Medido sobre 6310 partidos de arg.1 con cuota de cierre real
# (football-data.co.uk). El Brier global no cambia de forma
# significativa (t = -0.69), pero el SESGO por banda si:
#
#   banda            proporcional      Shin
#   favorito <2.0       -2.09          -0.97
#   parejo 2.0-3.5      +0.08          +0.09
#   tapado 3.5-5        +0.89          +0.38
#   batacazo >5         +0.86          -0.06
#
# Las bandas extremas son justo donde viven las apuestas de valor, y el
# CLV se calcula como cuota x probabilidad de cierre. Con el
# proporcional, la probabilidad de cierre de un batacazo queda inflada
# casi un punto, o sea que nos estariamos auto-regalando CLV en el lado
# donde mas facil es enganarse.
CU_SHIN = {"e1": hist((1.50, 4.20, 7.00), (1.45, 4.30, 7.50))}
fila = next(x for x in m.movimientos(CU_SHIN) if x["mercado"] == "1X2 visitante")
esperado_shin = m.devig_shin([1.50, 4.20, 7.00])[2]
esperado_prop = m.devig([1.50, 4.20, 7.00])[2]

prueba("la apertura del batacazo sale de Shin",
       abs(fila["p_open"] - esperado_shin) < 1e-9)
prueba("y NO del proporcional",
       abs(fila["p_open"] - esperado_prop) > 1e-4)
prueba("Shin le da menos probabilidad al batacazo", esperado_shin < esperado_prop)

fav = next(x for x in m.movimientos(CU_SHIN) if x["mercado"] == "1X2 local")
prueba("el cierre tambien sale de Shin",
       abs(fav["p_close"] - m.devig_shin([1.45, 4.30, 7.50])[0]) < 1e-9)


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
