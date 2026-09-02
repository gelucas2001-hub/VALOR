#!/usr/bin/env python3
"""Tests de mercado_extra.py — la cuota que ESPN no publica.

Qué protegen, y por qué cada uno existe:

- **Que un partido no se cruce con el equivocado.** El cruce contra
  odds-api.io no se puede hacer por nombre: "Racing Club" es Racing de
  Avellaneda para nosotros y "Racing Club De Lens" para ellos. Se cruza
  por FIXTURE (liga + fecha + los dos equipos), y si en ese día hay más
  de un candidato compatible, la respuesta correcta es **ninguno**. Un
  partido sin cruzar se ve; uno mal cruzado se ve como cuotas.
- **Que una línea de un solo lado no se trate como si tuviera dos.**
  Los córners vienen con over y under —por eso se les puede sacar el
  margen— pero los remates de jugador vienen solo con el "over".
  Confundirlos haría creer que hay margen quitado donde no lo hay, que
  es el error de §6vicies con el devig.
- **Que sin clave no se rompa nada.** La fuente nueva agrega mercados;
  si falta, todo tiene que seguir igual que antes.

    python test_mercado_extra.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import mercado_extra as ME

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
    return a is not None and abs(a - b) < tol


# Los bloques tal como los devuelve odds-api.io, recortados del pedido
# real de Unión–Sarmiento del 2026-08-26.
BLOQUES = [
    {"name": "ML", "odds": [{"home": "1.800", "draw": "3.200",
                             "away": "4.500"}]},
    {"name": "Double Chance", "odds": [{"1X": "1.181", "12": "1.363",
                                        "X2": "1.950"}]},
    {"name": "Both Teams To Score", "odds": [{"yes": "1.909",
                                              "no": "1.909"}]},
    {"name": "Goals Over/Under",
     "odds": [{"hdp": 2.5, "over": "2.000", "under": "1.800"}]},
    {"name": "Alternative Total Goals",
     "odds": [{"hdp": 0.5, "over": "1.071", "under": "9.000"},
              {"hdp": 1.5, "over": "1.300", "under": "3.400"},
              {"hdp": 3.5, "over": "3.500", "under": "1.285"},
              # De cuarto: parte la apuesta en dos mitades. No binaria.
              {"hdp": 2.25, "over": "1.850", "under": "1.950"},
              # Entera: puede empatar y devolver ("push"). No binaria.
              {"hdp": 2, "over": "1.500", "under": "2.500"}]},
    {"name": "Corners Totals",
     "odds": [{"hdp": 9.5, "over": "1.800", "under": "2.000"}]},
    {"name": "Corners",
     "odds": [{"hdp": 10, "over": "2.250", "under": "1.909"}]},
    {"name": "Alternative Corners",       # todas enteras: push, no entran
     "odds": [{"hdp": 6, "over": "1.125", "under": "10.000"},
              {"hdp": 7, "over": "1.250", "under": "6.000"}]},
    {"name": "Team Corners Home",
     "odds": [{"hdp": 6.5, "over": "2.000", "under": "1.727"}]},
    {"name": "Corners Totals Home",       # duplicado exacto del anterior
     "odds": [{"hdp": 6.5, "over": "2.000", "under": "1.727"}]},
    {"name": "Team Corners Away",
     "odds": [{"hdp": 3.5, "over": "2.100", "under": "1.666"}]},
    {"name": "Corners Totals HT",         # NO es del partido entero
     "odds": [{"hdp": 4.5, "over": "1.925", "under": "1.875"}]},
    {"name": "Player Shots",
     "odds": [{"label": "Victor Malcorra (1)", "hdp": 0.5, "over": "1.010"},
              {"label": "Victor Malcorra (1)", "hdp": 1.5, "over": "1.083"},
              {"label": "Victor Malcorra (1)", "hdp": 2.5, "over": "1.285"},
              {"label": "Diego Churin (2)", "hdp": 0.5, "over": "1.083"},
              {"label": "Diego Churin (2)", "hdp": 1.5, "over": "1.400"}]},
    {"name": "Player Shots on Target O/U",
     "odds": [{"label": "Victor Malcorra (1)", "hdp": 0.5, "over": "1.400"}]},
]


print("")
print("cuota() — un precio, o nada")
print("")

prueba("una cuota de texto se vuelve numero", cerca(ME.cuota("1.800"), 1.8))
prueba("un numero pasa igual", cerca(ME.cuota(2.5), 2.5))
prueba("una cuota imposible no pasa", ME.cuota("1.000") is None)
prueba("ni una negativa", ME.cuota("-2") is None)
prueba("ni basura", ME.cuota("abc") is None)
prueba("ni None", ME.cuota(None) is None)


print("")
print("dos_lados() — over y under, que es lo que permite quitar margen")
print("")

d = ME.dos_lados([{"hdp": 2.5, "over": "2.000", "under": "1.800"},
                  {"hdp": 1.5, "over": "1.300", "under": "3.400"}])
prueba("indexa por linea", set(d) == {"1.5", "2.5"})
prueba("guarda over y under en ese orden",
       cerca(d["2.5"][0], 2.0) and cerca(d["2.5"][1], 1.8))
prueba("la clave es texto, para que sobreviva al JSON",
       all(isinstance(k, str) for k in d))
prueba("0.5 y .5 dan la misma clave",
       set(ME.dos_lados([{"hdp": 0.5, "over": "2", "under": "2"}])) == {"0.5"})
prueba("una linea entera no queda como '10.0'",
       set(ME.dos_lados([{"hdp": 10, "over": "2", "under": "2"}])) == {"10"})

# Media linea sin el otro lado NO entra: sin los dos no hay margen que
# quitar, y media cuota invita a compararse contra la cruda.
prueba("una linea sin under se descarta",
       ME.dos_lados([{"hdp": 2.5, "over": "2.000"}]) == {})
prueba("y una sin over tambien",
       ME.dos_lados([{"hdp": 2.5, "under": "1.800"}]) == {})
prueba("una lista vacia da vacio", ME.dos_lados([]) == {})
prueba("y None tampoco explota", ME.dos_lados(None) == {})


print("")
print("binaria() — solo X.5 pasa: nada que empate ni se parta")
print("")

prueba("0.5 es binaria", ME.binaria("0.5"))
prueba("2.5 tambien", ME.binaria(2.5))
prueba("una linea entera NO es binaria (puede empatar y devolver)",
       not ME.binaria("2"))
prueba("ni una de cuarto (parte la apuesta en dos)",
       not ME.binaria("2.25"))
prueba("ni una de tres cuartos", not ME.binaria("2.75"))
prueba("basura no es binaria", not ME.binaria("x"))
prueba("None tampoco", not ME.binaria(None))


print("")
print("extraer() — los mercados que nos importan, y solo esos")
print("")

x = ME.extraer(BLOQUES)

prueba("el 1X2 entra", cerca(x["1x2"]["local"], 1.8))
prueba("con las tres patas",
       cerca(x["1x2"]["empate"], 3.2) and cerca(x["1x2"]["visitante"], 4.5))
prueba("la doble oportunidad viene COTIZADA, no sumada",
       cerca(x["dc"]["1X"], 1.181))
prueba("ambos marcan tambien", cerca(x["btts"]["si"], 1.909))

# EL punto de todo esto: las lineas de gol que ESPN no publica.
prueba("entran las lineas de gol de las dos fuentes",
       {"0.5", "1.5", "2.5", "3.5"} <= set(x["goles"]))
prueba("y 1.5 tiene precio real, que es lo que faltaba",
       cerca(x["goles"]["1.5"][0], 1.3))
prueba("3.5 tambien", cerca(x["goles"]["3.5"][1], 1.285))

# EL test de la parte binaria. Bet365 cotiza lineas de cuarto y enteras
# ademas de las X.5, pero nuestro motor (TESTS, el Brier, el registro)
# es binario: gana o pierde. Una de cuarto parte la apuesta en dos
# mitades y una entera puede empatar y devolver ("push") — comparar el
# modelo contra esas seria un error que no tira ninguna excepcion.
prueba("la linea de cuarto (2.25) NO entra", "2.25" not in x["goles"])
prueba("la linea entera (2) NO entra", "2" not in x["goles"])
prueba("solo quedaron binarias",
       all(ME.binaria(ln) for ln in x["goles"]))

prueba("los corners del partido entran", "9.5" in x["corners"]["total"])
# El bloque "Corners" del fixture trae hdp=10, entera: la saca el mismo
# filtro que las de Alternative Corners.
prueba("pero las lineas enteras (10, 6, 7) no, son push",
       not any(v in x["corners"]["total"] for v in ("10", "6", "7")))
prueba("los del local", cerca(x["corners"]["local"]["6.5"][0], 2.0))
prueba("los del visitante", cerca(x["corners"]["visita"]["3.5"][0], 2.1))

# EL test de que no se mezcle el primer tiempo con el partido entero.
prueba("el primer tiempo NO se cuela en el total del partido",
       "4.5" not in x["corners"]["total"])

# Dos nombres para el mismo mercado no pueden contarse dos veces ni
# pelearse: "Team Corners Home" y "Corners Totals Home" son lo mismo.
prueba("un mercado duplicado no rompe ni duplica",
       len(x["corners"]["local"]) == 1)


print("")
print("extraer() — el jugador viene de UN solo lado")
print("")

prueba("los remates por jugador entran", "Victor Malcorra" in x["remates"])
prueba("con su escalera de lineas",
       set(x["remates"]["Victor Malcorra"]["lineas"]) == {"0.5", "1.5", "2.5"})
prueba("y el precio de cada escalon",
       cerca(x["remates"]["Victor Malcorra"]["lineas"]["1.5"], 1.083))

# (1) es local y (2) visitante en la etiqueta de odds-api.
prueba("el (1) de la etiqueta es el local",
       x["remates"]["Victor Malcorra"]["lado"] == "L")
prueba("y el (2) el visitante",
       x["remates"]["Diego Churin"]["lado"] == "V")
prueba("el nombre queda sin el (1)",
       "(" not in "".join(x["remates"]))

prueba("los remates al arco van aparte de los remates",
       "Victor Malcorra" in x["al_arco"])
prueba("y no se pisan",
       not cerca(x["al_arco"]["Victor Malcorra"]["lineas"]["0.5"],
                 x["remates"]["Victor Malcorra"]["lineas"]["0.5"]))

# EL test que impide tratar una escalera de un lado como si tuviera dos.
prueba("la escalera de jugador NO es un par over/under",
       not isinstance(x["remates"]["Victor Malcorra"]["lineas"]["0.5"],
                      (list, tuple)))

prueba("sin bloques, un extracto vacio pero valido", ME.extraer([]) == {})
prueba("y None tampoco explota", ME.extraer(None) == {})


print("")
print("cruzar_fixture() — el partido correcto, o ninguno")
print("")

# Sus eventos, con SUS nombres. Los dos Racing estan a proposito.
EVENTOS = [
    {"id": 1, "home": "Union de Santa Fe", "away": "CA Sarmiento Junin",
     "date": "2026-08-28T22:00:00Z"},
    {"id": 2, "home": "CA River Plate (ARG)", "away": "CA Banfield",
     "date": "2026-08-29T20:00:00Z"},
    {"id": 3, "home": "Racing Club Avellaneda", "away": "CA Tigre",
     "date": "2026-08-29T20:00:00Z"},
]

p1 = {"home": "Unión (Santa Fe)", "away": "Sarmiento (Junín)",
      "date": "2026-08-28"}
prueba("un fixture cruza con el suyo",
       ME.cruzar_fixture(p1, EVENTOS) == 1)

# La fecha de ESPN es local; la de ellos UTC. Un partido de noche en
# America cae al dia siguiente en UTC, y tiene que cruzar igual.
p2 = {"home": "River Plate", "away": "Banfield", "date": "2026-08-29"}
prueba("cruza aunque UTC lo corra un dia", ME.cruzar_fixture(p2, EVENTOS) == 2)

p3 = {"home": "Racing Club", "away": "Tigre", "date": "2026-08-29"}
prueba("Racing de Avellaneda cruza con el suyo",
       ME.cruzar_fixture(p3, EVENTOS) == 3)

# EL test. Si el mismo dia hay dos candidatos igual de compatibles, la
# respuesta correcta es None: mejor sin cuota que con la del otro.
AMBIGUOS = [
    {"id": 10, "home": "CA Central Cordoba SE", "away": "CA Tigre",
     "date": "2026-08-29T20:00:00Z"},
    {"id": 11, "home": "Central Cordoba", "away": "CA Tigre",
     "date": "2026-08-29T20:00:00Z"},
]
pc = {"home": "Central Córdoba (Santiago del Estero)", "away": "Tigre",
      "date": "2026-08-29"}
prueba("dos candidatos igual de buenos NO eligen ninguno",
       ME.cruzar_fixture(pc, AMBIGUOS) is None)

prueba("otro dia no cruza",
       ME.cruzar_fixture({"home": "Unión (Santa Fe)",
                          "away": "Sarmiento (Junín)",
                          "date": "2026-09-15"}, EVENTOS) is None)
prueba("un equipo que no juega ese dia no cruza",
       ME.cruzar_fixture({"home": "Boca Juniors", "away": "Lanús",
                          "date": "2026-08-28"}, EVENTOS) is None)
prueba("dado vuelta (local por visitante) NO cruza",
       ME.cruzar_fixture({"home": "Sarmiento (Junín)",
                          "away": "Unión (Santa Fe)",
                          "date": "2026-08-28"}, EVENTOS) is None)
prueba("sin eventos no cruza", ME.cruzar_fixture(p1, []) is None)
prueba("sin partido tampoco", ME.cruzar_fixture(None, EVENTOS) is None)


print("")
print("tokens() — que el ruido no borre el nombre")
print("")

# Se aprendio midiendo: sacar "atletico" como ruido dejaba a Atletico-MG
# y a Athletico-PR sin un solo token, y los dos dejaban de cruzar.
prueba("el tipo de sociedad es ruido", "ca" not in ME.tokens("CA Banfield"))
prueba("pero el nombre queda", "banfield" in ME.tokens("CA Banfield"))
prueba("'atletico' NO es ruido: en Brasil es el nombre",
       "atletico" in ME.tokens("Atlético-MG"))
prueba("y por eso Atletico-MG cruza con el suyo",
       ME.compat("Atlético-MG", "Atletico Mineiro MG") > 0)
prueba("Athletico-PR tambien, por la provincia",
       ME.compat("Athletico-PR", "CA Paranaense PR") > 0)
prueba("dos equipos distintos no se parecen",
       ME.compat("Boca Juniors", "River Plate") == 0)


print("")
print("clave() — sin clave no se rompe nada")
print("")

prueba("sin variable de entorno devuelve None",
       ME.clave({"OTRA": "x"}) is None)
prueba("con la variable, la devuelve",
       ME.clave({"ODDS_API_KEY": "abc"}) == "abc")
prueba("una vacia cuenta como que no esta",
       ME.clave({"ODDS_API_KEY": "   "}) is None)


print("\nla competicion sin mapear tiene que HACER RUIDO\n")

# jpn.1 entro el 2026-09-02 y nadie la sumo a LIGAS: sus partidos
# salieron con la cuota de DraftKings y no se guardo una sola linea de
# jugador. Los props no se recuperan hacia atras.
import io as _io, contextlib as _ctx
_err = _io.StringIO()
with _ctx.redirect_stderr(_err):
    vacio = ME.eventos_de("jpn.1", "clave-falsa")
prueba("una liga que no esta en LIGAS no pide nada", vacio == [])
prueba("pero AVISA por stderr en vez de callarse",
       "jpn.1" in _err.getvalue() and "props" in _err.getvalue())
_err2 = _io.StringIO()
with _ctx.redirect_stderr(_err2):
    ME.eventos_de("jpn.1", "clave-falsa", avisar=False)
prueba("y el aviso se puede apagar para los tests", _err2.getvalue() == "")

print("\nbloques_sin_usar() — que mas manda Bet365 en la MISMA respuesta\n")

# El pedido trae todos los mercados de la casa; extraer() consume los
# que conoce y tira el resto. Con la señal del proyecto viviendo en los
# props, saber que mas llega es la diferencia entre poder preguntar y no.
BLOQUES = [{"name": "ML", "odds": []},
           {"name": "Player Shots", "odds": []},
           {"name": "Player Fouls Committed", "odds": []},
           {"name": "Player Cards", "odds": []},
           {"name": "Corners Totals", "odds": []}]
libres = ME.bloques_sin_usar(BLOQUES)
prueba("lo que ya leemos no aparece como sin usar",
       "ML" not in libres and "Player Shots" not in libres
       and "Corners Totals" not in libres)
prueba("y lo que descartamos si aparece",
       libres == ["Player Cards", "Player Fouls Committed"])
prueba("sin bloques no inventa nada", ME.bloques_sin_usar([]) == [])
prueba("un bloque sin nombre no rompe",
       ME.bloques_sin_usar([{"odds": []}, None]) == [])


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
