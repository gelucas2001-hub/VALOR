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


def jugador(nombre, ident, pos="F", pj=0, goles=0, asist=0, peso=0.0,
            serie=None):
    j = {"id": ident, "nombre": nombre, "pos": pos, "pj": float(pj),
         "goles": float(goles), "asist": float(asist), "remates": 0.0,
         "al_arco": 0.0, "faltas": 0.0, "amarillas": 0.0, "rojas": 0.0,
         "peso_goles": peso}
    if serie:
        j["serie"] = serie
    return j


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

# Los tres esperados de estadística salieron el 2026-09-03. Son un pronóstico
# NUESTRO de córners/faltas/tarjetas, o sea la misma métrica que `senal`
# afirma y el mismo baseline contra el que `medir_senal.py` mide el aporte.
# Con ellos adentro, la capa 3 comparaba el modelo contra sí mismo.
for prohibido in ("corners", "cornersH", "fouls", "cards"):
    prueba(f"no filtra el esperado {prohibido}", prohibido not in e)

print("\nla evidencia admisible de `senal` viaja medida\n")

EST = {"16": {"pj": 6, "remates": 14.8, "corners": 5.0, "faltas": 14.6,
              "tarjetas": 2.0, "al_arco": 4.2,
              "concede": {"corners": 3.83, "faltas": 12.2},
              "local": {"corners": 5.0}, "visita": {"corners": 5.0},
              "n": {"corners": 6, "faltas": 3},
              "desvio": {"corners": 3.22}},
       "5488": {"pj": 6, "remates": 11.0, "corners": 4.1, "faltas": 16.0,
                "tarjetas": 2.4, "al_arco": 3.1,
                "concede": {"corners": 5.2, "faltas": 13.0},
                "n": {"corners": 6, "faltas": 6}}}
con_est = expediente.expediente(PARTIDO, PLANTELES, EST)
m = con_est.get("metricasH") or {}
prueba("metricasH viaja cuando hay medición", bool(m))
prueba("trae lo que produce", (m.get("produce") or {}).get("corners") == 5.0)
prueba("trae lo que concede", (m.get("concede") or {}).get("corners") == 3.83)
prueba("trae el split por sede", "local" in m and "visita" in m)
prueba("trae n, que es lo que permite callarse", (m.get("n") or {}).get("corners") == 6)
prueba("trae el desvio", (m.get("desvio") or {}).get("corners") == 3.22)

sin_est = expediente.expediente(PARTIDO, PLANTELES, {})
prueba("sin medición no inventa metricas", "metricasH" not in sin_est)
prueba("sin medición avisa que las cuatro van en null",
       any("evidencia admisible" in a for a in sin_est.get("_avisos", [])))
prueba("con n chico avisa que un promedio es una racha",
       any("racha" in a for a in con_est.get("_avisos", [])))
prueba("el leeme ya no describe el lexico derogado",
       "ritmo_goleador" not in con_est["_leeme"]
       or "DEROGADAS" in con_est["_leeme"])
prueba("el leeme describe el lexico vigente",
       "corners_total" in con_est["_leeme"]
       and "generador" in con_est["_leeme"])

print("\nel plantel llega ordenado y sin relleno\n")

muchos = {"16": [jugador(f"J{i}", str(i), pj=i) for i in range(1, 40)]}
grande = expediente.expediente(PARTIDO, muchos)
pjs = [j["pj"] for j in grande["plantelH"]]
prueba("ordenado por partidos jugados, de más a menos", pjs == sorted(pjs, reverse=True))
prueba("no manda un plantel de 40 al análisis", len(grande["plantelH"]) <= 25)
prueba("manda a los que más jugaron, no a los primeros de la lista",
       grande["plantelH"][0]["pj"] == 39)


print("")
print("recortar_plantel() — la serie reciente, no solo el acumulado")
print("")

# El caso Driussi, textual de Lucas: "estaba lesionado hace rato, este
# torneo ni siquiera debuto". El plantel decia pj=5 goles=3 y la skill
# escribio "esta jugando y convirtiendo": los numeros eran de ANTES de
# la lesion. El acumulado de temporada no puede distinguir eso; la serie
# de los ultimos partidos si — quien no jugo no tiene serie.
CON_SERIE = [
    {"nombre": "El que juega", "pos": "F", "pj": 5, "goles": 3, "asist": 0,
     "peso_goles": 0.4, "serie": {"remates": [2, 1, 3], "goles": [1, 0, 1],
                                  "pj": 3, "tit": 3, "esp": {"remates": 2.1}}},
    {"nombre": "El lesionado", "pos": "F", "pj": 5, "goles": 3, "asist": 0,
     "peso_goles": 0.4},
]
r = expediente.recortar_plantel(CON_SERIE)
prueba("pasa la serie del que viene jugando", r[0].get("serie") is not None)
prueba("y el que no jugo queda sin serie", r[1].get("serie") is None)
prueba("los dos tienen el mismo acumulado (por eso hacia falta)",
       r[0]["pj"] == r[1]["pj"] and r[0]["goles"] == r[1]["goles"])
prueba("la serie llega partido por partido",
       r[0]["serie"]["goles"] == [1, 0, 1])
prueba("dice en cuantos jugo de los recientes", r[0]["serie"]["pj"] == 3)
prueba("y en cuantos fue titular", r[0]["serie"]["tit"] == 3)
prueba("no arrastra el esperado del modelo de lineas",
       "esp" not in r[0]["serie"])
prueba("un plantel sin series no rompe",
       expediente.recortar_plantel([{"nombre": "X", "pos": "M", "pj": 1}]) is not None)


print("\nel umbral de `senal` lo aplica el expediente, no el criterio\n")

# El defecto que originó esto (TRASPASO §34): la skill promediaba tres
# estimadores a ojo y declaró null una señal a +16% mientras afirmaba
# otra a +11%, en la misma tanda. La cuenta no es trabajo de criterio.
VARA = {"corners": 9.3, "faltas": 24.1, "tarjetas": 4.6, "remates": 26.9}


def met(**kw):
    """Un bloque metricas* armado a mano, con los mismos valores en las
    tres vistas salvo que se pida lo contrario."""
    base = {"corners": 4.6, "faltas": 12.0, "tarjetas": 2.3, "remates": 13.4}
    base.update(kw.pop("produce", {}))
    o = {"produce": dict(base), "concede": dict(base),
         "local": dict(base), "visita": dict(base),
         "n": {m: 6 for m in base}}
    for k, v in kw.items():
        o.setdefault(k, {}).update(v)
    return o


plano = expediente.veredicto_senal(met(), met(), VARA)
prueba("en la media de la liga no afirma nada",
       all(f["fallo"] is None for f in plano.values()))
prueba("y dice que fue por estar cerca de la media",
       "cerca de la media" in plano["faltas"]["por_que"])

# faltas: umbral 10% de gap. 13.4+13.4 = 26.8 contra una vara de 24.1
# es +11%, o sea justo del lado de adentro.
arriba = expediente.veredicto_senal(
    met(produce={"faltas": 13.4}, local={"faltas": 13.4}, concede={"faltas": 13.4}),
    met(produce={"faltas": 13.4}, visita={"faltas": 13.4}, concede={"faltas": 13.4}),
    VARA)
prueba("por encima del umbral afirma 'muchas'", arriba["faltas"]["fallo"] == "muchas")
abajo = expediente.veredicto_senal(
    met(produce={"faltas": 10.0}, local={"faltas": 10.0}, concede={"faltas": 10.0}),
    met(produce={"faltas": 10.0}, visita={"faltas": 10.0}, concede={"faltas": 10.0}),
    VARA)
prueba("por debajo afirma 'pocas'", abajo["faltas"]["fallo"] == "pocas")

# tarjetas: no se afirma NUNCA. Medido — no supera su tasa base en
# ningun umbral de la grilla de calibrar_senal.py.
extremo = expediente.veredicto_senal(
    met(produce={"tarjetas": 6.0}, local={"tarjetas": 6.0}, concede={"tarjetas": 6.0}),
    met(produce={"tarjetas": 6.0}, visita={"tarjetas": 6.0}, concede={"tarjetas": 6.0}),
    VARA)
prueba("tarjetas no se afirma ni con el doble de la vara",
       extremo["tarjetas"]["fallo"] is None)
prueba("y explica que no se afirma nunca",
       "nunca" in extremo["tarjetas"]["por_que"])

# muestra corta: gana sobre el gap, aunque el gap sea enorme
corta = expediente.veredicto_senal(
    met(produce={"faltas": 20.0}, local={"faltas": 20.0}, concede={"faltas": 20.0},
        n={"faltas": 3}),
    met(produce={"faltas": 20.0}, visita={"faltas": 20.0}, concede={"faltas": 20.0},
        n={"faltas": 3}),
    VARA)
prueba("con muestra corta no afirma aunque el gap sea grande",
       corta["faltas"]["fallo"] is None)
prueba("y dice que fue por la muestra", "muestra corta" in corta["faltas"]["por_que"])

# estimadores que se contradicen: tambien gana sobre el gap. Es la mitad
# de la regla que no existia antes de §34.
disc = expediente.veredicto_senal(
    met(produce={"faltas": 20.0}, local={"faltas": 8.0}, concede={"faltas": 20.0}),
    met(produce={"faltas": 20.0}, visita={"faltas": 8.0}, concede={"faltas": 20.0}),
    VARA)
prueba("si los estimadores se contradicen, no afirma",
       disc["faltas"]["fallo"] is None)
prueba("y lo dice", "contradicen" in disc["faltas"]["por_que"])

print("\n`generador` se mide por partido, no por la suma\n")

# El caso real de la primera tanda: Colidio, 14 remates en 3 partidos,
# contra un segundo de 9 en 4. Por suma es +56%; por partido, +107%.
# La suma premia a quien jugo mas, que es lo contrario de la señal.
PLANTEL_DESPAREJO = [
    jugador("Colidio", "1", pj=3, serie={"remates": [7, 3, 4], "pj": 3, "tit": 2}),
    jugador("Tche Tche", "2", pj=4, serie={"remates": [1, 2, 2, 4], "pj": 4, "tit": 4}),
]
ld = expediente.liderazgo_remates(PLANTEL_DESPAREJO)
prueba("elige al lider por promedio por partido", ld["lider"]["nombre"] == "Colidio")
prueba("y la ventaja es la de por partido, no la de la suma",
       abs(ld["ventaja"] - 1.074) < 0.01)
prueba("la suma habria dado +56%, que es otra cosa",
       abs((14 / 9 - 1) - 0.556) < 0.01)

POCAS = [
    jugador("Debutante", "1", pj=1, serie={"remates": [9], "pj": 1, "tit": 1}),
    jugador("Regular", "2", pj=4, serie={"remates": [2, 2, 2, 2], "pj": 4, "tit": 4}),
    jugador("Otro", "3", pj=4, serie={"remates": [1, 1, 1, 1], "pj": 4, "tit": 4}),
]
ld2 = expediente.liderazgo_remates(POCAS)
prueba("una tasa de un solo partido no es una tasa: queda afuera",
       ld2["lider"]["nombre"] == "Regular")
prueba("sin dos candidatos con muestra, no hay liderazgo",
       expediente.liderazgo_remates(POCAS[:1]) is None)


prueba("el umbral de generador vive en el codigo, no en la prosa",
       expediente.UMBRAL_GENERADOR == 0.50)

# Antes el expediente daba `ventaja` y la skill aplicaba el 50% a ojo:
# las cuatro dimensiones de volumen tenian su fallo calculado y esta no.
prueba("entrega el veredicto ya tomado cuando califica",
       ld["califica"] is True)
AJUSTADO = [
    jugador("Puntero", "1", pj=4, serie={"remates": [3, 3, 3, 3], "pj": 4, "tit": 4}),
    jugador("Segundo", "2", pj=4, serie={"remates": [3, 2, 2, 3], "pj": 4, "tit": 4}),
]
ld3 = expediente.liderazgo_remates(AJUSTADO)
prueba("y cuando no llega al umbral, no califica",
       ld3["califica"] is False)
prueba("  y dice cuanto le falto",
       "hace falta" in ld3["por_que"])

print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
