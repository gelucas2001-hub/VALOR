#!/usr/bin/env python3
"""Tests del plantel — los jugadores y sus números.

Existen por un motivo puntual: el análisis nombraba bajas sin poder
pesarlas. "No está Acuña" y "no está Montiel" pesan distinto si uno
jugó 2 de 5 partidos y el otro 5 de 5, y esa diferencia estaba a un
pedido de distancia y no se usaba.

La trampa que estos tests protegen es la misma que la de forma_general:
las estadísticas de ESPN son POR COMPETICIÓN. Pedir el plantel de River
con el slug de la Sudamericana da 3 partidos jugados; con el de la Liga
Argentina da 5. Ninguno de los dos solo dice la verdad.

    python test_plantel.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import actualizar

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def atleta(nombre, pos="F", ident="1", **stats):
    """Un jugador con la forma exacta que devuelve /roster: las
    estadísticas anidadas en splits.categories[].stats[]."""
    cats = {"appearances": "general", "foulsCommitted": "general",
            "yellowCards": "general", "redCards": "general",
            "totalGoals": "offensive", "goalAssists": "offensive",
            "totalShots": "offensive", "shotsOnTarget": "offensive"}
    porcat = {}
    for k, v in stats.items():
        porcat.setdefault(cats.get(k, "general"), []).append(
            {"name": k, "value": float(v)})
    return {
        "id": ident, "displayName": nombre,
        "position": {"abbreviation": pos},
        "statistics": {"splits": {"categories": [
            {"name": c, "stats": ss} for c, ss in porcat.items()]}},
    }


print("\nstats_jugador() — sacar los números de la maraña de /roster\n")

a = atleta("Hugo Rodallega", "F", "77", appearances=26, totalGoals=13,
           goalAssists=4, totalShots=50, shotsOnTarget=22, yellowCards=3)
s = actualizar.stats_jugador(a)

prueba("trae el nombre", s["nombre"] == "Hugo Rodallega")
prueba("trae el id", s["id"] == "77")
prueba("trae la posicion", s["pos"] == "F")
prueba("partidos jugados", s["pj"] == 26)
prueba("goles", s["goles"] == 13)
prueba("asistencias", s["asist"] == 4)
prueba("remates", s["remates"] == 50)
prueba("remates al arco", s["al_arco"] == 22)
prueba("amarillas", s["amarillas"] == 3)

# Un jugador sin estadísticas (recién llegado, o que no jugó nunca) no
# puede romper: se cuenta como cero, no como ausente.
vacio = actualizar.stats_jugador({"id": "9", "displayName": "Nadie",
                                  "position": {"abbreviation": "M"}})
prueba("jugador sin estadisticas da ceros, no rompe",
       vacio["pj"] == 0 and vacio["goles"] == 0)

# Un roster real trae posiciones sin abreviatura de vez en cuando.
sin_pos = actualizar.stats_jugador({"id": "9", "displayName": "Nadie"})
prueba("jugador sin posicion no rompe", sin_pos["pos"] == "")

print("\nfusionar_planteles() — la liga y la copa son el mismo jugador\n")

# El mismo jugador aparece en los dos rosters, con números de cada
# competición. Sumarlos es el punto: es la única forma de que 'jugó 5 de
# 5' signifique algo cuando el equipo juega dos torneos a la vez.
liga = [actualizar.stats_jugador(atleta("Montiel", "D", "10",
                                        appearances=5, totalGoals=1)),
        actualizar.stats_jugador(atleta("Acuña", "D", "20", appearances=2))]
copa = [actualizar.stats_jugador(atleta("Montiel", "D", "10",
                                        appearances=3, totalGoals=1)),
        actualizar.stats_jugador(atleta("Colidio", "F", "30",
                                        appearances=4, totalGoals=2))]

f = actualizar.fusionar_planteles(liga, copa)
por_id = {j["id"]: j for j in f}

prueba("junta los dos rosters sin duplicar al mismo jugador", len(f) == 3)
prueba("suma los partidos del mismo jugador", por_id["10"]["pj"] == 8)
prueba("suma los goles del mismo jugador", por_id["10"]["goles"] == 2)
prueba("conserva al que solo esta en un roster", por_id["30"]["goles"] == 2)
prueba("conserva nombre y posicion al fusionar",
       por_id["10"]["nombre"] == "Montiel" and por_id["10"]["pos"] == "D")

# Orden: el que más juega primero. La pestaña Plantel muestra los
# primeros, y un plantel de 40 con los suplentes arriba no sirve.
prueba("ordena por partidos jugados, de mas a menos",
       [j["id"] for j in f] == ["10", "30", "20"])

prueba("una lista vacia no rompe la fusion",
       len(actualizar.fusionar_planteles(liga, [])) == 2)

print("\nslugs_plantel() — de qué competiciones hay que pedir el roster\n")

# El bug que motivó esta función, encontrado el 2026-08-20 corriendo el
# cron de verdad: River juega el 23/08 por Liga y el 26/08 por
# Sudamericana. El plantel se cargó con el primer partido (Liga), y el
# segundo se salteó por "ya lo tengo" — así que los goles de copa nunca
# se sumaron. Driussi quedó con 3 PJ / 1 gol en vez de 5 / 3.
prueba("una copa pide la copa y ademas la liga domestica",
       actualizar.slugs_plantel("conmebol.sudamericana", "arg.1")
       == ["conmebol.sudamericana", "arg.1"])
prueba("un partido de liga pide igual la liga, sin duplicar",
       actualizar.slugs_plantel("arg.1", "arg.1") == ["arg.1"])
prueba("sin liga domestica conocida, solo la competicion del partido",
       actualizar.slugs_plantel("arg.1", None) == ["arg.1"])
prueba("la copa nacional tambien suma la liga",
       actualizar.slugs_plantel("arg.copa", "arg.1") == ["arg.copa", "arg.1"])

# El otro lado del mismo problema, encontrado el 2026-08-23: Estudiantes
# de Río Cuarto ascendió a Liga Profesional (arg.1), pero el
# defaultLeague que ESPN cachea para el club todavía dice arg.2
# (Primera Nacional, la categoría de la que salió). El partido real es
# de arg.1 — ya es la liga — así que sumar arg.2 no agrega copa contra
# liga, suma DOS CATEGORÍAS DISTINTAS del mismo jugador. Un mediocampista
# terminó con 52 PJ (16 reales en arg.1 + 36 de la categoría vieja).
prueba("un partido de LIGA no suma otra liga distinta, aunque el cache la marque",
       actualizar.slugs_plantel("arg.1", "arg.2") == ["arg.1"])

print("\nsolo_los_que_jugaron() — no mandar al móvil lo que no se usa\n")

# Un tercio de cada roster nunca jugó (juveniles, recién llegados). Se
# filtran en el backend, no en la app: el archivo lo baja un teléfono.
mezcla = [
    actualizar.stats_jugador(atleta("Titular", "F", "1", appearances=20, totalGoals=8)),
    actualizar.stats_jugador(atleta("Nunca jugó", "M", "2")),
    actualizar.stats_jugador(atleta("Un partido", "D", "3", appearances=1)),
]
filtrado = actualizar.solo_los_que_jugaron(mezcla)
prueba("saca a los que no jugaron nunca", len(filtrado) == 2)
prueba("conserva al que jugó aunque sea uno",
       any(j["nombre"] == "Un partido" for j in filtrado))

# Si NINGUNO jugó (equipo recién ascendido, torneo sin empezar), filtrar
# dejaría la pestaña vacía sin motivo. Mejor mostrar el plantel entero.
ninguno = [actualizar.stats_jugador(atleta("A", "F", "1")),
           actualizar.stats_jugador(atleta("B", "M", "2"))]
prueba("si nadie jugó, devuelve el plantel entero en vez de nada",
       len(actualizar.solo_los_que_jugaron(ninguno)) == 2)
prueba("lista vacía no rompe", actualizar.solo_los_que_jugaron([]) == [])

print("\nslugs_de_equipos() — juntar competiciones sin contar dos veces\n")

# La otra cara del mismo bug. Si se acumulara por partido, un equipo con
# DOS partidos de la misma competición en la ventana (dos fechas de Liga
# en la misma semana) se sumaría a sí mismo: 5 PJ + 5 PJ = 10. Por eso
# lo que se acumula son los SLUGS, no los planteles.
partidos_demo = [
    ("16", "arg.1", "arg.1"),                       # River, Liga
    ("16", "conmebol.sudamericana", "arg.1"),       # River, copa
    ("16", "arg.1", "arg.1"),                       # River, otra fecha de Liga
    ("5488", "conmebol.sudamericana", "col.1"),     # Santa Fe
]
mapa = actualizar.slugs_de_equipos(partidos_demo)

prueba("junta las competiciones distintas de un mismo equipo",
       mapa["16"] == ["arg.1", "conmebol.sudamericana"])
prueba("dos partidos de la misma competicion no la repiten",
       mapa["16"].count("arg.1") == 1)
prueba("cada equipo tiene su propia lista",
       mapa["5488"] == ["col.1", "conmebol.sudamericana"])
prueba("sin partidos, mapa vacio", actualizar.slugs_de_equipos([]) == {})

print("\npeso_goleador() — cuánto del equipo es un solo jugador\n")

# El pedido original de Lucas, textual: "por ahí Racing te dice que
# tiene una tasa alta de gol, pero su delantero del cual residen el 50%
# de los goles del equipo está lesionado". Sin este número, la baja de
# un goleador y la de un suplente se leen igual.
plantel = [
    actualizar.stats_jugador(atleta("Rodallega", "F", "1", appearances=26, totalGoals=13)),
    actualizar.stats_jugador(atleta("Fernández", "F", "2", appearances=25, totalGoals=5)),
    actualizar.stats_jugador(atleta("Bustos", "F", "3", appearances=26, totalGoals=5)),
    actualizar.stats_jugador(atleta("Suplente", "M", "4", appearances=3, totalGoals=0)),
]
p = actualizar.peso_goleador(plantel)

prueba("el peso es la fraccion de goles del equipo", abs(p["1"] - 13/23) < 1e-9)
prueba("el que no hizo goles pesa cero", p["4"] == 0.0)
prueba("los pesos suman 1 cuando todos los goles estan en el plantel",
       abs(sum(p.values()) - 1.0) < 1e-9)

# Un equipo sin goles (arranque de torneo) no puede dividir por cero.
sin_goles = [actualizar.stats_jugador(atleta("X", "M", "1", appearances=2))]
prueba("un equipo sin goles no divide por cero",
       actualizar.peso_goleador(sin_goles) == {"1": 0.0})
prueba("un plantel vacio no rompe", actualizar.peso_goleador([]) == {})


# ── El once que arranco de verdad ──────────────────────────────────
# La app dibujaba un once INFERIDO con una nota que decia que ESPN no
# publica el titular. Es cierto para un partido por jugarse y falso para
# uno jugado: `rosters[]` trae starter, jersey, formationPlace y
# formation. Verificado contra la API el 2026-09-01.
print("")
print("El once del ultimo partido")
print("")


def tit(nombre, pid, pos, dorsal, starter=True):
    return {"starter": starter, "jersey": dorsal,
            "athlete": {"id": pid, "displayName": nombre},
            "position": {"abbreviation": pos}}


def lado(team_id, formacion, titulares, banco=2):
    r = [tit("T%d" % i, str(100 + i), q, str(i + 1))
         for i, q in enumerate(titulares)]
    r += [tit("S%d" % i, str(200 + i), "M", "0", starter=False)
          for i in range(banco)]
    return {"team": {"id": team_id}, "formation": formacion, "roster": r}


ONCE_433 = ["G", "RB", "LB", "CM", "CD-R", "CD-L", "RM", "LM", "F", "RF", "LF"]
crudo = {"rosters": [lado("99", "4-3-3", ONCE_433)]}
o = actualizar.once_partido(crudo)

prueba("saca los once que arrancaron, y solo esos", len(o["99"]["jugadores"]) == 11)
prueba("con el dorsal, que es lo que se dibuja en la cancha",
       o["99"]["jugadores"][0]["dorsal"] == "1")
prueba("y con el esquema que publica ESPN", o["99"]["esquema"] == "4-3-3")
prueba("el suplente no entra en el once",
       all(not j["nombre"].startswith("S") for j in o["99"]["jugadores"]))

# Un lado incompleto se descarta ENTERO: un dibujo con ocho jugadores
# miente sobre el equipo tanto como uno con cuatro delanteros.
incompleto = {"rosters": [lado("99", "4-3-3", ONCE_433[:8])]}
prueba("un lado con menos de once no se dibuja a medias",
       actualizar.once_partido(incompleto) == {})
prueba("un resumen sin rosters no rompe", actualizar.once_partido({}) == {})

# `ultimo_once` recorre hacia atras: el partido mas nuevo sin rosters
# cargados no puede dejar al equipo sin once.
jugados = [
    {"id": "e3", "fecha": "2026-08-31T00:00Z", "local": True,
     "home": "Propio", "away": "Rival Nuevo", "marcador": "3-0"},
    {"id": "e2", "fecha": "2026-08-23T00:00Z", "local": False,
     "home": "Rival Viejo", "away": "Propio", "marcador": "1-2"},
]
cache = {"e3": {"_once": {}}, "e2": {"_once": o}}
u = actualizar.ultimo_once("99", jugados, cache)
prueba("cae al partido anterior cuando el ultimo no trae rosters",
       u["fecha"] == "2026-08-23")
prueba("y dice contra quien fue: un once sin fecha se lee como el de hoy",
       u["rival"] == "Rival Viejo" and u["local"] is False)
prueba("sin ningun once devuelve None, no un diccionario vacio",
       actualizar.ultimo_once("99", jugados, {"e3": {}, "e2": {}}) is None)

print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
