#!/usr/bin/env python3
"""Tests del expediente — lo que la skill de análisis ve, y lo que no.

El expediente existe para que la lectura del análisis sea independiente
de la del modelo. Estos tests protegen las dos mitades de eso:

  - que NO se filtre nada del modelo (λ, ρ, cuotas, EV),
  - que SÍ llegue el material con el que un analista pesa una baja.

Lo segundo es lo que motivó este archivo. El 2026-08-19 Lucas leyó un
análisis que nombraba a Acuña, Driussi y Arambarri como bajas de River
sin distinguir entre uno que hace más de un mes que no está y otro que
jugó un solo partido. La skill no tenía cómo distinguirlos: el plantel
no viajaba en el expediente.

    python test_expediente.py
"""

import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
import expediente

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def jugador(nombre, ident, pos="F", pj=0, goles=0, asist=0, peso=0.0):
    return {"id": ident, "nombre": nombre, "pos": pos, "pj": float(pj),
            "goles": float(goles), "asist": float(asist), "remates": 0.0,
            "al_arco": 0.0, "faltas": 0.0, "amarillas": 0.0, "rojas": 0.0,
            "peso_goles": peso}


PARTIDO = {
    "id": "espn123", "home": "River Plate", "away": "Independiente Santa Fe",
    "homeId": "16", "awayId": "5488", "date": "2026-08-23",
    "comp": "Copa Sudamericana",
    "formH": [{"r": "L", "rival": "X", "local": True, "marcador": "0-1", "d": "16/08/26"}],
    "formA": [{"r": "W", "rival": "Y", "local": False, "marcador": "2-0", "d": "15/08/26"}],
    "h2h": [], "tabla": [],
    "lh": 1.7, "la": 0.9, "rho": -0.05, "conf": 0.8,
    "mercado": {"h": 1.8, "d": 3.4, "a": 4.2}, "note": "λ ajustado por ancla doméstica",
}

PLANTELES = {
    "16": [jugador("Sebastián Driussi", "1", "F", pj=5, goles=3, peso=0.5),
           jugador("Gonzalo Montiel", "2", "D", pj=5, peso=0.0),
           jugador("Facundo Arambarri", "3", "M", pj=1, peso=0.0)],
    "5488": [jugador("Hugo Rodallega", "4", "F", pj=26, goles=13, peso=0.56)],
}

print("\nplantel en el expediente — para poder pesar una baja\n")

e = expediente.expediente(PARTIDO, PLANTELES)

prueba("el expediente trae el plantel del local", "plantelH" in e)
prueba("el expediente trae el plantel del visitante", "plantelA" in e)
prueba("el plantel del local es el del homeId, no el del visitante",
       any(j["nombre"] == "Sebastián Driussi" for j in e.get("plantelH", [])))
prueba("el plantel del visitante es el del awayId",
       any(j["nombre"] == "Hugo Rodallega" for j in e.get("plantelA", [])))

# El campo que separa "no está Driussi" de "no está Arambarri". Sin él, la
# skill vuelve a la lista de nombres sin jerarquía que motivó todo esto.
d = next((j for j in e.get("plantelH", []) if j["nombre"] == "Sebastián Driussi"), {})
prueba("cada jugador trae partidos jugados", d.get("pj") == 5)
prueba("cada jugador trae goles", d.get("goles") == 3)
prueba("cada jugador trae el peso goleador", d.get("peso_goles") == 0.5)
prueba("cada jugador trae la posicion", d.get("pos") == "F")

# El expediente lo lee un modelo de lenguaje: cada campo que no se usa es
# ruido que compite con los que sí. Remates, faltas y tarjetas no pesan una
# baja, así que no viajan.
prueba("no manda campos que no sirven para pesar una baja",
       "remates" not in d and "faltas" not in d and "amarillas" not in d)

# "Jugó 5" no significa nada sin saber sobre cuántos. No hay un campo de
# partidos del equipo en ningún lado, así que se usa el máximo del plantel —
# y se dice que es eso, no un dato de la fuente.
prueba("dice cuántos partidos jugó el que más jugó, para dar escala",
       e.get("pjMaxH") == 5 and e.get("pjMaxA") == 26)

print("\ncuando no hay plantel — el hueco se declara, no se inventa\n")

sin = expediente.expediente(PARTIDO, {})
prueba("sin plantel no revienta", isinstance(sin, dict))
prueba("sin plantel no inventa una lista vacía que parezca un plantel",
       sin.get("plantelH") is None and sin.get("plantelA") is None)
prueba("sin plantel avisa que no lo tiene",
       any("plantel" in a.lower() for a in sin.get("_avisos", [])))

# Un solo equipo cargado es el caso real de un rival de liga que el pipeline
# todavía no sigue. El análisis puede pesar bajas de uno y no del otro — pero
# tiene que saber cuál.
solo_local = expediente.expediente(PARTIDO, {"16": PLANTELES["16"]})
prueba("con un solo plantel, avisa de qué equipo falta",
       any("Independiente Santa Fe" in a for a in solo_local.get("_avisos", [])))
prueba("con un solo plantel, el que sí está viaja igual",
       len(solo_local.get("plantelH", [])) == 3)

print("\nel recorte del modelo sigue en pie\n")

# Lo que este archivo NO puede romper: agregar campos al expediente no puede
# abrir la puerta a la salida del modelo. Si esto falla, la marca dorada de
# la app pasa a ser el modelo dándose la razón a sí mismo.
for prohibido in ("lh", "la", "rho", "conf", "mercado", "note"):
    prueba(f"no filtra {prohibido}", prohibido not in e)

print("\nel plantel llega ordenado y sin relleno\n")

muchos = {"16": [jugador(f"J{i}", str(i), pj=i) for i in range(1, 40)]}
grande = expediente.expediente(PARTIDO, muchos)
pjs = [j["pj"] for j in grande["plantelH"]]
prueba("ordenado por partidos jugados, de más a menos", pjs == sorted(pjs, reverse=True))
prueba("no manda un plantel de 40 al análisis", len(grande["plantelH"]) <= 25)
prueba("manda a los que más jugaron, no a los primeros de la lista",
       grande["plantelH"][0]["pj"] == 39)

print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
