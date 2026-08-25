#!/usr/bin/env python3
"""Tests de equipos.py — cruzar los nombres del CSV con los de ESPN.

Qué protegen, y por qué cada uno existe:

- **Que un cruce dudoso NO se resuelva.** El peor resultado posible acá
  no es un nombre sin cruzar: es un nombre cruzado con el club
  equivocado. "Paris SG" y "Paris FC" juegan la misma liga esta
  temporada, y cualquier cruce por parecido o por prefijo le pega la
  historia de uno al otro sin un solo mensaje. Un nombre sin cruzar se
  ve; un nombre mal cruzado se ve como datos.
- **Que dos equipos no puedan reclamar el mismo nombre.** Si dos ids
  normalizan igual, el índice tiene que dejar ese nombre AFUERA, no
  quedarse con el último que pasó. Brentford y Brest comparten la
  abreviatura BRE — por eso no se cruza por abreviatura, y hay un test
  que lo fija.
- **Que lo que no cruza se cuente.** Es la regla que ya costó 1521
  partidos en `historico.py`: un descarte silencioso no se ve como un
  error, se ve como menos datos.

    python test_equipos.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import equipos as EQ

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


# Los equipos tal como los devuelve ESPN, con los campos que importan.
# Son los reales de eng.1 y fra.1, verificados contra /standings el
# 2026-08-25 — incluidos los dos Paris, que son el caso peligroso.
ESPN_ENG = [
    {"id": "349", "display": "AFC Bournemouth", "short": "Bournemouth",
     "name": "AFC Bournemouth", "abbr": "BOU"},
    {"id": "331", "display": "Brighton & Hove Albion", "short": "Brighton",
     "name": "Brighton & Hove Albion", "abbr": "BHA"},
    {"id": "337", "display": "Brentford", "short": "Brentford",
     "name": "Brentford", "abbr": "BRE"},
    {"id": "382", "display": "Manchester City", "short": "Man City",
     "name": "Manchester City", "abbr": "MNC"},
    {"id": "360", "display": "Manchester United", "short": "Man United",
     "name": "Manchester United", "abbr": "MAN"},
    {"id": "393", "display": "Nottingham Forest", "short": "Nottm Forest",
     "name": "Nottingham Forest", "abbr": "NFO"},
    {"id": "367", "display": "Tottenham Hotspur", "short": "Spurs",
     "name": "Tottenham Hotspur", "abbr": "TOT"},
    {"id": "380", "display": "Wolverhampton Wanderers", "short": "Wolves",
     "name": "Wolverhampton Wanderers", "abbr": "WOL"},
    {"id": "363", "display": "Chelsea", "short": "Chelsea",
     "name": "Chelsea", "abbr": "CHE"},
]
ESPN_FRA = [
    {"id": "160", "display": "Paris Saint-Germain", "short": "PSG",
     "name": "Paris Saint-Germain", "abbr": "PSG"},
    {"id": "6851", "display": "Paris FC", "short": "Paris FC",
     "name": "Paris FC", "abbr": "PAR"},
    {"id": "3236", "display": "Le Havre AC", "short": "Le Havre AC",
     "name": "Le Havre AC", "abbr": "HAC"},
    {"id": "169", "display": "Stade Rennais", "short": "Rennes",
     "name": "Stade Rennais", "abbr": "REN"},
    {"id": "174", "display": "AS Monaco", "short": "Monaco",
     "name": "AS Monaco", "abbr": "MON"},
    {"id": "172", "display": "AJ Auxerre", "short": "Auxerre",
     "name": "AJ Auxerre", "abbr": "AUX"},
    {"id": "6997", "display": "Brest", "short": "Brest",
     "name": "Brest", "abbr": "BRE"},
]


print("")
print("normalizar() — la misma forma para los dos lados")
print("")

prueba("baja a minusculas", EQ.normalizar("Chelsea") == "chelsea")
prueba("saca la puntuacion",
       EQ.normalizar("Nott'm Forest") == EQ.normalizar("Nottm Forest"))
prueba("y por eso Nott'm Forest no necesita alias",
       EQ.normalizar("Nott'm Forest") == "nottm forest")
prueba("saca los acentos", EQ.normalizar("Saint-Étienne") == "saint etienne")
prueba("colapsa los espacios de mas",
       EQ.normalizar("  Man   City  ") == "man city")
prueba("el ampersand queda como separador",
       EQ.normalizar("Brighton & Hove Albion") == "brighton hove albion")
prueba("un nombre vacio da vacio", EQ.normalizar("") == "")
prueba("y None tampoco explota", EQ.normalizar(None) == "")

# Lo que NO puede hacer: acortar, recortar, ni quedarse con la primera
# palabra. Si normalizar() achicara los nombres, "Paris SG" y "Paris FC"
# terminarian siendo el mismo.
prueba("no recorta a la primera palabra",
       EQ.normalizar("Paris SG") != EQ.normalizar("Paris FC"))


print("")
print("indice() — de nombre de ESPN al id, sin adivinar")
print("")

idx = EQ.indice(ESPN_ENG)
prueba("el displayName entra", idx.get("chelsea") == "363")
prueba("el shortDisplayName tambien", idx.get("wolves") == "380")
prueba("y el name largo", idx.get("manchester city") == "382")
prueba("los tres apuntan al mismo id",
       idx.get("man city") == idx.get("manchester city") == "382")

# EL test que fija una decision de diseno. Brentford (eng) y Brest (fra)
# comparten la abreviatura BRE. Cruzar por abreviatura es barato y
# rompe en silencio en cuanto se mezclan dos ligas.
prueba("la abreviatura NO entra al indice", "bre" not in idx)
prueba("ninguna abreviatura entra",
       not any(EQ.normalizar(e["abbr"]) in idx for e in ESPN_ENG
               if EQ.normalizar(e["abbr"]) not in
               {EQ.normalizar(e["display"]), EQ.normalizar(e["short"]),
                EQ.normalizar(e["name"])}))

prueba("un indice vacio no explota", EQ.indice([]) == {})


print("")
print("indice() — dos equipos no pueden reclamar el mismo nombre")
print("")

# Caso inventado a proposito: dos ids distintos con el mismo nombre
# corto. La respuesta correcta NO es quedarse con el ultimo.
_chocan = [
    {"id": "1", "display": "Racing Club", "short": "Racing",
     "name": "Racing Club", "abbr": "RAC"},
    {"id": "2", "display": "Racing Santander", "short": "Racing",
     "name": "Racing Santander", "abbr": "RSA"},
]
ic = EQ.indice(_chocan)
prueba("el nombre ambiguo queda AFUERA del indice", "racing" not in ic)
prueba("pero los nombres propios de cada uno siguen",
       ic.get("racing club") == "1" and ic.get("racing santander") == "2")

amb = EQ.ambiguos(_chocan)
prueba("y la ambiguedad se puede listar", "racing" in amb)
prueba("con los dos ids que la causaron",
       set(amb.get("racing") or []) == {"1", "2"})
prueba("sin choques, no hay ambiguos", EQ.ambiguos(ESPN_ENG) == {})


print("")
print("cruzar() — el CSV contra ESPN")
print("")

prueba("un nombre identico cruza", EQ.cruzar("Chelsea", idx) == "363")
prueba("un nombre corto de ESPN cruza", EQ.cruzar("Wolves", idx) == "380")
prueba("Man City cruza sin alias", EQ.cruzar("Man City", idx) == "382")
prueba("Nott'm Forest cruza solo por puntuacion",
       EQ.cruzar("Nott'm Forest", idx) == "393")

# Los tres que SI necesitan tabla escrita a mano.
prueba("Tottenham necesita alias y lo tiene",
       EQ.cruzar("Tottenham", idx) == "367")
idxf = EQ.indice(ESPN_FRA)
prueba("Paris SG necesita alias y lo tiene",
       EQ.cruzar("Paris SG", idxf) == "160")
prueba("Le Havre necesita alias y lo tiene",
       EQ.cruzar("Le Havre", idxf) == "3236")

# EL test. El error caro de este archivo.
prueba("Paris SG NO cae en Paris FC", EQ.cruzar("Paris SG", idxf) != "6851")
prueba("Paris FC NO cae en Paris SG", EQ.cruzar("Paris FC", idxf) != "160")
prueba("y Paris FC cruza con el suyo", EQ.cruzar("Paris FC", idxf) == "6851")

# Un equipo que no esta en la liga este ano no se cruza con nadie.
prueba("un descendido no cruza con el mas parecido",
       EQ.cruzar("Leicester", idx) is None)
prueba("ni un nombre inventado",
       EQ.cruzar("Club Atletico Inexistente", idx) is None)
prueba("ni uno vacio", EQ.cruzar("", idx) is None)

# El alias apunta a un nombre de ESPN, no a un id: si el equipo no esta
# en la liga que se le paso, el alias no puede inventarlo.
prueba("un alias sin su equipo en el indice no cruza",
       EQ.cruzar("Tottenham", idxf) is None)


print("")
print("ALIAS — la tabla escrita a mano, chica y justificada")
print("")

prueba("la tabla es chica: menos de veinte entradas", len(EQ.ALIAS) < 20)
prueba("todas las claves estan normalizadas",
       all(k == EQ.normalizar(k) for k in EQ.ALIAS))
prueba("ningun alias apunta a un nombre vacio",
       all(v and v.strip() for v in EQ.ALIAS.values()))
prueba("ningun alias se apunta a si mismo",
       all(EQ.normalizar(v) != k for k, v in EQ.ALIAS.items()))

# Un alias que ya cruzaria solo es ruido, y peor: tapa el dia que ESPN
# cambie el nombre y nadie se entere.
_todos = EQ.indice(ESPN_ENG + ESPN_FRA)
_redundantes = [k for k in EQ.ALIAS if k in _todos]
prueba("ningun alias de eng/fra es redundante con el indice",
       not _redundantes)


print("")
print("reporte() — lo que no cruza se cuenta, no se descarta")
print("")

rep = EQ.reporte(["Chelsea", "Wolves", "Tottenham", "Leicester",
                  "Southampton"], idx)
prueba("cuenta los que cruzaron", rep["cruzan"] == 3)
prueba("y los que no", len(rep["sin_cruzar"]) == 2)
prueba("nombrando cuales",
       set(rep["sin_cruzar"]) == {"Leicester", "Southampton"})
prueba("el mapa devuelve los ids", rep["mapa"]["Wolves"] == "380")
prueba("y los que no cruzan no estan en el mapa",
       "Leicester" not in rep["mapa"])
prueba("sin nombres, un reporte vacio pero valido",
       EQ.reporte([], idx)["cruzan"] == 0)


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
