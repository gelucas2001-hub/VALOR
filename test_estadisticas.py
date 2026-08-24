#!/usr/bin/env python3
"""Tests de las estadísticas de equipo por partido.

Lucas empezó a mirar apuestas de estadísticas (remates, al arco, faltas,
córners, tarjetas) y pidió poder verlas en la app.

El hallazgo que motivó estos tests: el pipeline YA pedía /summary de cada
partido para calcular córners y faltas, y ESE MISMO response trae 25
métricas por equipo — remates, remates al arco, posesión, pases, centros,
tackles, bloqueos. Se estaban descartando 22 de las 25 al aplanar.

O sea que esto no cuesta un solo pedido más: cuesta dejar de tirar datos
que ya llegan.

    python test_estadisticas.py
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


def equipo(tid, **stats):
    """La forma exacta que devuelve boxscore.teams[]: displayValue, no value."""
    return {"team": {"id": tid},
            "statistics": [{"name": k, "displayValue": str(v)}
                           for k, v in stats.items()]}


CRUDO = {"boxscore": {"teams": [
    equipo("9739", foulsCommitted=14, wonCorners=3, yellowCards=2, redCards=1,
           totalShots=9, shotsOnTarget=2, possessionPct=41.3, offsides=1,
           saves=4, totalTackles=18, accuratePasses=210, totalPasses=330),
    equipo("20", foulsCommitted=11, wonCorners=7, yellowCards=1, redCards=0,
           totalShots=16, shotsOnTarget=6, possessionPct=58.7, offsides=3,
           saves=1, totalTackles=12, accuratePasses=380, totalPasses=470),
]}}


print("\nestadisticas_equipo() — aplanar las 25 métricas del mismo response\n")

out = actualizar.estadisticas_equipo(CRUDO)

prueba("saca los dos equipos", set(out) == {"9739", "20"})

loc = out["9739"]
prueba("remates", loc["remates"] == 9)
prueba("remates al arco", loc["al_arco"] == 2)
prueba("córners", loc["corners"] == 3)
prueba("faltas", loc["faltas"] == 14)
prueba("posesión", loc["posesion"] == 41.3)
prueba("offsides", loc["offsides"] == 1)
prueba("atajadas", loc["atajadas"] == 4)
prueba("tackles", loc["tackles"] == 18)

# Las tarjetas se suman como en el resto del pipeline: amarillas + rojas.
prueba("tarjetas suma amarillas y rojas", loc["tarjetas"] == 3)

# La precisión de pase no viene calculada de forma confiable en todas las
# ligas; con pases dados y totales se deriva y se puede verificar.
prueba("pases y su precisión", loc["pases"] == 210 and loc["pases_tot"] == 330)

print("\nlo que falta no se inventa en cero\n")

# Un partido sin estadísticas cargadas (pasa en ligas chicas y en partidos
# recién terminados) tiene que devolver None, no ceros: un cero medido y un
# dato ausente se leen igual en pantalla y no son lo mismo.
flaco = {"boxscore": {"teams": [equipo("9739", foulsCommitted=10)]}}
f = actualizar.estadisticas_equipo(flaco)["9739"]
prueba("una métrica ausente queda en None, no en cero", f["remates"] is None)
prueba("la que sí vino se conserva", f["faltas"] == 10)

prueba("un boxscore vacío no rompe", actualizar.estadisticas_equipo({}) == {})
prueba("un response sin boxscore no rompe",
       actualizar.estadisticas_equipo({"header": {}}) == {})

# ESPN manda displayValue como texto, y en algunas ligas con separador de
# miles o con símbolo. Lo que no se puede leer como número es None.
raro = {"boxscore": {"teams": [equipo("9739", totalShots="-", possessionPct="41.3%")]}}
r = actualizar.estadisticas_equipo(raro)["9739"]
prueba("un valor no numérico no rompe ni miente", r["remates"] is None)
prueba("un porcentaje con símbolo se lee igual", r["posesion"] == 41.3)

print("\nresumen_partido() sigue dando lo que el modelo ya usaba\n")

# El motor consume corners/fouls/cards de acá. Si esto cambia de forma,
# disciplina_equipo() se rompe en silencio y los λ salen mal.
compat = actualizar.aplanar_resumen(CRUDO)
prueba("mantiene la clave corners", compat["9739"]["corners"] == 3)
prueba("mantiene la clave fouls", compat["9739"]["fouls"] == 14)
prueba("mantiene la clave cards", compat["9739"]["cards"] == 3)
prueba("y ahora además trae las nuevas", compat["9739"]["remates"] == 9)

print("\npromedios_equipo() — lo que se muestra\n")

partidos = [
    {"remates": 10, "al_arco": 4, "corners": 5, "faltas": 12, "posesion": 55.0},
    {"remates": 6,  "al_arco": 2, "corners": 3, "faltas": 10, "posesion": 45.0},
    {"remates": None, "al_arco": 3, "corners": None, "faltas": 8, "posesion": None},
]
pr = actualizar.promedios_equipo(partidos)

prueba("promedia lo que hay", pr["remates"] == 8.0)
prueba("no cuenta los ausentes como cero", pr["corners"] == 4.0)
prueba("promedia con todos cuando están todos", pr["al_arco"] == 3.0)
prueba("dice sobre cuántos partidos promedió", pr["pj"] == 3)
prueba("dice cuántos tenían el dato de cada métrica", pr["n"]["remates"] == 2)
prueba("sin partidos no rompe", actualizar.promedios_equipo([]) == {})

# Una métrica que ningún partido trajo no puede salir como 0.0.
solo_faltas = [{"faltas": 9}, {"faltas": 11}]
sf = actualizar.promedios_equipo(solo_faltas)
prueba("una métrica sin ningún dato no aparece", "remates" not in sf)
prueba("la que sí tiene datos aparece", sf["faltas"] == 10.0)

print("\ndisciplina_equipo() — el motor no se puede romper con esto\n")

# Los λ dependen de esta función. Dos formas nuevas de romperla:
# (1) `cards` ahora puede ser None (antes se forzaba a 0), y sumarle None
#     a un float revienta; (2) el caché persistente en disco tiene
#     registros viejos con solo fouls/corners/cards.
jugados = [{"id": "e1"}, {"id": "e2"}]

# Estos registros son anteriores a las 25 metricas y al arbitro, asi que
# disciplina_equipo() los da por incompletos y sale a re-pedirlos: es lo
# que tiene que hacer en produccion. En un test eso seria un pedido real
# a ESPN, lento y dependiente de la red. Se simula el pedido fallido,
# que ademas es el camino que interesa probar — que un registro viejo
# siga alimentando los lambda aunque el re-pedido no traiga nada.
_real_resumen = actualizar.resumen_partido
actualizar.resumen_partido = lambda slug, eid: None

cache_con_none = {"e1": {"9739": {"corners": 4.0, "fouls": 12.0, "cards": None,
                                  "faltas": 12.0, "tarjetas": None, "remates": 8.0}}}
r = actualizar.disciplina_equipo("arg.1", "9739", jugados[:1], cache_con_none)
prueba("una tarjeta ausente no revienta el cálculo", r is not None)
prueba("y no la cuenta como una tarjeta real", r[2] == 0.0)

# Registro viejo: tiene lo que el modelo necesita y nada más. Tiene que
# seguir sirviendo para los λ sin salir a pedir de nuevo.
cache_viejo = {"e1": {"9739": {"corners": 6.0, "fouls": 10.0, "cards": 2.0}}}
r2 = actualizar.disciplina_equipo("arg.1", "9739", jugados[:1], cache_viejo)
prueba("un registro viejo del caché sigue alimentando el modelo",
       r2 is not None and r2[0] == 6.0)

# Se devuelve el pedido real: el stub era solo para esos dos casos.
actualizar.resumen_partido = _real_resumen

print("\npromedios_equipo() — también informa la constancia (desvío)\n")

# El pedido de Lucas, textual: "no es lo mismo un jugador que remató 5
# veces en 5 partidos pero hizo 4 en 1". El promedio solo no distingue
# constante de errático — hace falta el desvío.
parejo   = [{"remates": 1}, {"remates": 1}, {"remates": 1}, {"remates": 1}, {"remates": 1}]
irregular = [{"remates": 4}, {"remates": 0}, {"remates": 0}, {"remates": 0}, {"remates": 1}]
pp = actualizar.promedios_equipo(parejo)
pi = actualizar.promedios_equipo(irregular)
prueba("los dos promedian lo mismo", pp["remates"] == pi["remates"] == 1.0)
prueba("el parejo tiene desvío bajo", pp["desvio"]["remates"] < 0.5)
prueba("el irregular tiene desvío alto", pi["desvio"]["remates"] > 1.0)
prueba("distingue a los dos aunque el promedio sea igual",
       pp["desvio"]["remates"] < pi["desvio"]["remates"])

prueba("con un solo partido el desvío no se calcula (no divide por cero)",
       "remates" not in actualizar.promedios_equipo([{"remates": 3}])["desvio"])
prueba("sin partidos no rompe (desvio)", actualizar.promedios_equipo([]) == {})

print("\nfilas_partido() — cruzar el historial con el caché de resúmenes\n")

# El historial ya trae 'local' y 'rival_id' por partido (historial() en
# actualizar.py). filas_partido() lo cruza con cache_resumen para armar,
# por cada partido, lo propio Y lo del rival — que es lo que hace falta
# para "cuánto concede el rival" y para separar de local/visitante.
jug = [
    {"id": "e1", "local": True,  "rival_id": "50"},
    {"id": "e2", "local": False, "rival_id": "60"},
    {"id": "e3", "local": True,  "rival_id": "70"},   # sin resumen cacheado
]
cache = {
    "e1": {"9739": {"remates": 10, "corners": 5}, "50": {"remates": 3, "corners": 2}},
    "e2": {"9739": {"remates": 6,  "corners": 2}, "60": {"remates": 9, "corners": 6}},
}
filas = actualizar.filas_partido(jug, cache, "9739")

prueba("una fila por partido con resumen", len(filas) == 2)
prueba("descarta el partido sin resumen cacheado", all(f["propio"] for f in filas))
prueba("conserva si fue local o visitante", filas[0]["local"] is True and filas[1]["local"] is False)
prueba("lo propio es el equipo consultado", filas[0]["propio"]["remates"] == 10)
prueba("lo del rival es del oponente en ESE partido", filas[0]["rival"]["remates"] == 3)
prueba("distingue bien el segundo partido", filas[1]["propio"]["remates"] == 6
       and filas[1]["rival"]["remates"] == 9)
prueba("una lista vacía no rompe", actualizar.filas_partido([], {}, "9739") == [])

# Un partido cacheado pero sin el equipo propio (raro, pero posible si
# ESPN no trajo estadísticas de ese lado) se descarta, no rompe.
cache_flaco = {"e1": {"50": {"remates": 3}}}
prueba("sin datos propios en el caché, se descarta esa fila",
       actualizar.filas_partido([jug[0]], cache_flaco, "9739") == [])

print("\nel caché viejo se renueva solo, sin perder lo que ya servía\n")

# El caché de resúmenes persiste en disco entre corridas. Los registros
# escritos antes del 2026-08-20 tienen solo fouls/corners/cards. Si se
# dan por buenos, las métricas nuevas no se pueblan NUNCA: el partido ya
# está en caché y no se vuelve a pedir. Hay que poder distinguirlos.
prueba("un registro viejo se reconoce como incompleto",
       not actualizar.resumen_completo({"9739": {"corners": 6.0, "fouls": 10.0,
                                                 "cards": 2.0}}))
prueba("uno nuevo se reconoce como completo",
       actualizar.resumen_completo(actualizar.aplanar_resumen(CRUDO)))
# Un partido que ESPN devolvió sin estadísticas cargadas es completo
# igual: se pidió, no hay nada, y volver a pedirlo cada corrida sería
# pagar para siempre por un dato que no existe.
prueba("un partido sin estadisticas no se re-pide para siempre",
       actualizar.resumen_completo(
           actualizar.aplanar_resumen({"boxscore": {"teams": [equipo("9739")]}})))
prueba("un registro vacío no se da por completo",
       not actualizar.resumen_completo({}))


print("")
print("muestras_por_equipo() — juntar los valores por equipo del caché")
print("")

# Para saber si el promedio de un equipo dice algo o es ruido hay que
# tener los valores sueltos, no el promedio ya hecho.
cache_m = {
    "e1": {"9": {"remates": 10, "corners": 3}, "5": {"remates": 14, "corners": 6}},
    "e2": {"9": {"remates": 8,  "corners": 5}, "5": {"remates": 12, "corners": 2}},
    "_meta": "esto no es un partido",
}
mu = actualizar.muestras_por_equipo(cache_m)
prueba("agrupa por métrica y por equipo", sorted(mu["remates"]) == ["5", "9"])
prueba("junta los valores de todos los partidos", sorted(mu["remates"]["9"]) == [8.0, 10.0])
prueba("ignora las claves de metadatos", "_meta" not in str(mu))
prueba("no arrastra los alias del motor", "fouls" not in mu)
prueba("un caché vacío no rompe", actualizar.muestras_por_equipo({}) == {})

print("")
print("parametros_metricas() — cuánta de la diferencia entre equipos es real")
print("")

# El hallazgo que motiva esto: con 3-4 partidos por equipo, la diferencia
# de remates entre dos equipos es del tamaño del ruido de muestreo.
# Mostrar "12.5 vs 18.7" como diferencia real es mentir con decimales.
#
# k es cuánto hay que tirar el promedio del equipo hacia el de la liga.
# k alto = todavía no se distingue. Se recalcula en cada corrida, así que
# se relaja solo a medida que se juntan partidos.
seniales = {t: [v] * 6 for t, v in
            {"a": 2, "b": 6, "c": 10, "d": 14, "e": 18, "f": 22, "g": 26, "h": 30}.items()}
p_sen = actualizar.parametros_metricas({"remates": seniales})["remates"]
prueba("con señal clara, k es chico", p_sen["k"] < 1.0)
prueba("informa la media de la liga", 15.5 < p_sen["media"] < 16.5)

import random
random.seed(7)
ruido = {t: [random.choice([0, 10]) for _ in range(4)] for t in "abcdefgh"}
p_rui = actualizar.parametros_metricas({"remates": ruido})["remates"]
prueba("sin señal, k es grande", p_rui["k"] > 5)
prueba("k tiene tope (no escribe un número absurdo en el JSON)",
       p_rui["k"] <= actualizar.K_TOPE)

prueba("informa la dispersión por partido", p_sen["disp"] >= 0)
prueba("informa sobre cuántos equipos midió", p_sen["equipos"] == 8)
prueba("con pocos equipos no inventa un parámetro",
       actualizar.parametros_metricas({"remates": {"a": [1, 2]}}) == {})
prueba("sin muestras no rompe", actualizar.parametros_metricas({}) == {})

print("")
print("media_encogida() — el promedio honesto de un equipo")
print("")

# Con k grande el promedio propio casi no pesa: el mejor pronóstico para
# ese equipo es el de la liga. Con k chico manda lo suyo.
prueba("sin partidos, es el de la liga",
       actualizar.media_encogida([], 10.0, 3.0) == 10.0)
prueba("con k grande tira al de la liga",
       abs(actualizar.media_encogida([20.0] * 4, 10.0, 100.0) - 10.0) < 0.5)
prueba("con k chico respeta lo del equipo",
       abs(actualizar.media_encogida([20.0] * 4, 10.0, 0.1) - 20.0) < 0.5)
prueba("queda entre el equipo y la liga, nunca fuera",
       10.0 <= actualizar.media_encogida([20.0] * 4, 10.0, 4.0) <= 20.0)
prueba("más partidos pesan más que menos partidos",
       actualizar.media_encogida([20.0] * 8, 10.0, 4.0)
       > actualizar.media_encogida([20.0] * 2, 10.0, 4.0))


print("")
print("esperados() — lo que se espera de este equipo, no lo que hizo")
print("")

PAR = {"remates": {"media": 13.0, "k": 200.0, "disp": 2.95, "equipos": 46},
       "faltas":  {"media": 11.0, "k": 7.0,   "disp": 1.42, "equipos": 46}}

# Un equipo con 3 partidos rematando 20: el promedio dice 20, pero con
# k=200 (remates no se distingue entre equipos con esta muestra) lo
# esperable sigue siendo lo de la liga.
tres = [{"remates": 20, "faltas": 18}] * 3
es = actualizar.esperados(tres, PAR)
prueba("con k alto el esperado se pega a la liga", abs(es["remates"] - 13.0) < 0.5)
prueba("con k bajo el esperado se mueve hacia el equipo", es["faltas"] > 12.5)
prueba("y no se pasa del promedio del equipo", es["faltas"] <= 18.0)
prueba("una métrica sin parámetro no se inventa", "corners" not in es)
prueba("sin partidos devuelve el de la liga", actualizar.esperados([], PAR)["remates"] == 13.0)
prueba("sin parámetros no rompe", actualizar.esperados(tres, {}) == {})

# El caso que hace falta que no se rompa: la métrica existe en params
# pero ningún partido la trajo.
sin = [{"faltas": 10}, {"faltas": 12}]
prueba("una métrica ausente en los partidos cae al de la liga",
       actualizar.esperados(sin, PAR)["remates"] == 13.0)


print("")
print("dispersion_total() — el total del partido no es la suma de dos independientes")
print("")

# Medido el 2026-08-23: la dispersión de los córners de UN equipo es
# 1.76, pero la del total del partido es 1.01. Si fueran independientes
# tendría que dar 1.76 también. No lo son: los córners son medio suma
# cero (si uno ataca, el otro no), así que el total varía MENOS de lo
# que predice sumar dos modelos sueltos. Con tarjetas pasa al revés.
#
# Quien arma líneas de total sumando dos equipos independientes se
# infla las colas y ve valor donde no hay.
def part(a, b):
    return {"9": {"corners": a}, "5": {"corners": b}}

# Suma constante: los dos se reparten 10 córners. Varía cada equipo,
# el total no varía nada.
sumacero = {f"e{i}": part(x, 10 - x) for i, x in
            enumerate([2, 3, 4, 5, 6, 7, 8, 5, 4, 6, 3, 7, 5, 4, 6, 5, 6, 4, 5, 5, 3, 7])}
dt = actualizar.dispersion_total(sumacero)
prueba("un total que no varía da dispersión cero", dt["corners"] < 0.01)
# ...aunque cada equipo por separado varíe muchísimo. Es exactamente
# el caso que rompe sumar dos modelos independientes.
import statistics as _st
_m = actualizar.muestras_por_equipo(sumacero)["corners"]
prueba("y eso pasa aunque cada equipo suelto varíe mucho",
       all(_st.variance(v) > 1.5 for v in _m.values()))

# Totales que varían de verdad.
import random
random.seed(11)
libre = {f"e{i}": part(random.randint(0, 12), random.randint(0, 12)) for i in range(40)}
prueba("un total que varía da dispersión mayor que cero",
       actualizar.dispersion_total(libre)["corners"] > 0.5)

# Un partido con un solo equipo cargado no tiene total: no se puede
# inventar la mitad que falta.
medio = dict(sumacero)
medio["roto"] = {"9": {"corners": 4}}
prueba("un partido a medias no cuenta como total",
       abs(actualizar.dispersion_total(medio)["corners"]
           - actualizar.dispersion_total(sumacero)["corners"]) < 0.01)

prueba("con pocos partidos no inventa un parámetro",
       actualizar.dispersion_total({"e1": part(3, 4)}) == {})
prueba("un caché vacío no rompe", actualizar.dispersion_total({}) == {})
prueba("ignora las claves de metadatos",
       "_meta" not in actualizar.dispersion_total(dict(sumacero, _meta="x")))


print("")
print("arbitro_de() — quién dirigió, del mismo response que ya se pedía")
print("")

# Se midió que las tarjetas NO dependen del partido: correlación -0.05
# con los goles y +0.01 con la diferencia. La varianza viene de otro
# lado, y el sospechoso de siempre es el árbitro. ESPN lo devuelve en
# gameInfo.officials, dentro del /summary que ya se pide: cero pedidos
# extra, igual que pasó con las 25 métricas.
CON_ARB = {"gameInfo": {"officials": [
    {"fullName": "Pablo Dovalo", "position": {"name": "Referee"}},
    {"fullName": "Otro Que No Dirige", "position": {"name": "Assistant Referee"}},
]}}
prueba("saca el nombre del árbitro", actualizar.arbitro_de(CON_ARB) == "Pablo Dovalo")

# El primero de la lista no siempre es el juez principal: hay que ir por
# la posición, no por el orden.
AL_REVES = {"gameInfo": {"officials": [
    {"fullName": "Un Asistente", "position": {"name": "Assistant Referee"}},
    {"fullName": "La Jueza", "position": {"name": "Referee"}},
]}}
prueba("elige al juez principal, no al primero de la lista",
       actualizar.arbitro_de(AL_REVES) == "La Jueza")

prueba("sin árbitro devuelve vacío, no None",
       actualizar.arbitro_de({"gameInfo": {"officials": []}}) == "")
prueba("sin gameInfo no rompe", actualizar.arbitro_de({}) == "")
prueba("una lista rara no rompe",
       actualizar.arbitro_de({"gameInfo": {"officials": [{"x": 1}]}}) == "")

print("")
print("el árbitro viaja con el partido, no con un equipo")
print("")

pl = actualizar.aplanar_resumen(dict(CRUDO, **CON_ARB))
prueba("queda guardado en el registro del partido", pl["_arbitro"] == "Pablo Dovalo")
prueba("y no se mete adentro de un equipo", "_arbitro" not in pl["9739"])

# Todo lo que ya leía el caché tiene que seguir andando con la clave
# nueva al lado. Si alguna de estas se rompe, se rompen los lambda.
prueba("el motor sigue leyendo lo suyo", pl["9739"]["corners"] == 3)
prueba("muestras_por_equipo ignora la clave del árbitro",
       "_arbitro" not in actualizar.muestras_por_equipo({"e1": pl}))
prueba("dispersion_total no la confunde con un equipo",
       actualizar.dispersion_total({f"e{i}": pl for i in range(30)}) != {})
prueba("disciplina_equipo sigue calculando",
       actualizar.disciplina_equipo("arg.1", "9739", [{"id": "e1"}], {"e1": pl}) is not None)

print("")
print("el caché se rellena una sola vez, no para siempre")
print("")

# Mismo problema que con las 25 métricas: los 177 partidos ya cacheados
# no tienen árbitro y no se volverían a pedir nunca, porque el partido
# ya está en el caché. Se los reconoce por la ausencia de la clave.
# Un registro tal como quedo escrito ANTES de este cambio: tiene las 25
# metricas y ninguna clave de partido. No se puede fabricar con
# aplanar_resumen(), que ahora siempre agrega el arbitro.
sin_arb = {k: v for k, v in actualizar.aplanar_resumen(CRUDO).items()
           if not k.startswith("_")}
prueba("un registro sin árbitro se reconoce como incompleto",
       not actualizar.resumen_completo(sin_arb))
prueba("uno con árbitro se reconoce como completo",
       actualizar.resumen_completo(pl))
# Un partido cuyo árbitro ESPN no informa NO se puede re-pedir siempre:
# la clave está aunque venga vacía, y eso alcanza.
vacio = actualizar.aplanar_resumen(dict(CRUDO, gameInfo={"officials": []}))
prueba("un partido sin árbitro informado no se re-pide para siempre",
       actualizar.resumen_completo(vacio))
prueba("un registro que es solo el árbitro no cuenta como completo",
       not actualizar.resumen_completo({"_arbitro": "X"}))


print("")
print("jugadores_partido() — lo que hizo cada jugador en ESE partido")
print("")

# El pedido original de Lucas, textual: "no es lo mismo un jugador que
# remato 5 veces en 5 partidos pero hizo 4 en 1". Para contestar eso
# hace falta el numero partido por partido, no el acumulado de
# temporada. Viene en el mismo /summary que ya se pide, en rosters[].
def atleta(pid, titular=True, **st):
    st.setdefault("appearances", 1)
    return {"athlete": {"id": pid}, "starter": titular,
            "stats": [{"name": k, "value": v} for k, v in st.items()]}

ROSTERS = {"rosters": [
    {"team": {"id": "9739"}, "roster": [
        atleta("1", True,  totalShots=4, shotsOnTarget=2, foulsCommitted=1,
               yellowCards=1, totalGoals=1, goalAssists=0),
        atleta("2", False, totalShots=0, shotsOnTarget=0, foulsCommitted=3,
               yellowCards=0, totalGoals=0, goalAssists=1),
        atleta("3", False, appearances=0, totalShots=0),   # no jugo
    ]},
    {"team": {"id": "20"}, "roster": [
        atleta("9", True, totalShots=2, shotsOnTarget=1, foulsCommitted=0,
               yellowCards=0, totalGoals=0, goalAssists=0),
    ]},
]}

jp = actualizar.jugadores_partido(ROSTERS)
prueba("toma a los dos equipos", set(jp) == {"1", "2", "9"})
prueba("descarta al que no jugo", "3" not in jp)

f = jp["1"]
i = actualizar.CAMPOS_JUGADOR_PARTIDO.index
prueba("remates", f[i("remates")] == 4)
prueba("remates al arco", f[i("al_arco")] == 2)
prueba("faltas", f[i("faltas")] == 1)
prueba("amarillas", f[i("amarillas")] == 1)
prueba("goles", f[i("goles")] == 1)
prueba("asistencias", jp["2"][i("asist")] == 1)
prueba("marca si fue titular", f[i("titular")] == 1)
prueba("y si entro desde el banco", jp["2"][i("titular")] == 0)

prueba("una estadistica que no vino queda en cero, no rompe",
       actualizar.jugadores_partido(
           {"rosters": [{"roster": [atleta("7")]}]})["7"][i("remates")] == 0)
prueba("sin rosters no rompe", actualizar.jugadores_partido({}) == {})
prueba("un jugador sin id se descarta",
       actualizar.jugadores_partido(
           {"rosters": [{"roster": [{"stats": [], "starter": True}]}]}) == {})

print("")
print("los jugadores viajan con el partido, como el arbitro")
print("")

pj_ = actualizar.aplanar_resumen(dict(CRUDO, **ROSTERS))
prueba("quedan guardados en el registro del partido", "_jugadores" in pj_)
prueba("con los tres que jugaron", set(pj_["_jugadores"]) == {"1", "2", "9"})
prueba("y no se meten adentro de un equipo", "_jugadores" not in pj_["9739"])
prueba("el motor sigue leyendo lo suyo", pj_["9739"]["corners"] == 3)
prueba("muestras_por_equipo los ignora",
       "_jugadores" not in actualizar.muestras_por_equipo({"e1": pj_}))
prueba("dispersion_total no los confunde con un equipo",
       actualizar.dispersion_total({f"e{i2}": pj_ for i2 in range(30)}) != {})

# Mismo mecanismo que con el arbitro: sin la clave, el partido ya
# cacheado nunca se volveria a pedir y la serie no se poblaria nunca.
prueba("un registro sin la clave se reconoce como incompleto",
       not actualizar.resumen_completo(
           {k: v for k, v in pj_.items() if k != "_jugadores"}))
prueba("uno con la clave se reconoce como completo",
       actualizar.resumen_completo(pj_))

print("")
print("serie_jugadores() — el historial partido por partido")
print("")

# Dos jugadores con el MISMO total de remates y lecturas opuestas: el
# regular y el que hizo todo en un partido. El promedio los iguala; la
# serie los separa. Es exactamente lo que Lucas pidio ver.
def part(**rem):
    r = [atleta(pid, True, totalShots=v) for pid, v in rem.items()]
    return actualizar.aplanar_resumen(dict(CRUDO, rosters=[{"roster": r}]))

cache_s = {
    "e1": part(regular=1, explosivo=0),
    "e2": part(regular=1, explosivo=4),
    "e3": part(regular=1, explosivo=0),
    "e4": part(regular=1),                    # el explosivo no jugo
}
jugd = [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}, {"id": "e4"}]
se = actualizar.serie_jugadores(jugd, cache_s)

prueba("arma una serie por jugador", set(se) == {"regular", "explosivo"})
prueba("respeta el orden de los partidos",
       se["regular"]["remates"] == [1, 1, 1, 1])
prueba("el mismo total, repartido distinto",
       sum(se["explosivo"]["remates"]) == 4
       and se["explosivo"]["remates"] == [0, 4, 0])
prueba("cuenta en cuantos jugo", se["explosivo"]["pj"] == 3)
prueba("y en cuantos fue titular", se["regular"]["tit"] == 4)
prueba("no inventa un partido que no jugo",
       len(se["explosivo"]["remates"]) == 3)
prueba("un partido sin resumen cacheado se saltea",
       actualizar.serie_jugadores(jugd + [{"id": "nada"}], cache_s)
       ["regular"]["remates"] == [1, 1, 1, 1])
prueba("corta en el tope pedido",
       len(actualizar.serie_jugadores(jugd, cache_s, tope=2)["regular"]["remates"]) == 2)
prueba("sin partidos no rompe", actualizar.serie_jugadores([], {}) == {})


print("")
print("serie_jugadores() — una serie de un solo partido no es una serie")
print("")

# planteles.json lo baja el telefono en cada carga. Una "serie" de un
# partido no distingue al regular del explosivo, que es para lo unico
# que existe, y son 140 de 442 jugadores: peso sin lectura.
uno = {"e1": part(fugaz=2, fijo=1), "e2": part(fijo=1), "e3": part(fijo=3)}
jd = [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}]
se1 = actualizar.serie_jugadores(jd, uno, minimo=2)
prueba("descarta al que aparece una sola vez", "fugaz" not in se1)
prueba("conserva al que tiene con que comparar", se1["fijo"]["pj"] == 3)
prueba("sin minimo entran todos",
       "fugaz" in actualizar.serie_jugadores(jd, uno, minimo=1))


print("")
print("parametros_jugadores() — un central no se compara contra un 9")
print("")

# A nivel equipo, k en remates da 200: dos equipos no se distinguen. A
# nivel jugador da 2.5 — un delantero y un central SI se distinguen, y
# muchisimo (1.41 remates contra 0.48). Por eso el ancla no puede ser el
# promedio de todos los jugadores: encogeria al 9 hacia abajo y al
# central hacia arriba. Se agrupa por puesto.
def jugador(pid, pos, serie):
    return {"id": pid, "pos": pos, "serie": {"remates": serie, "pj": len(serie)}}

PLA = {"t1": [jugador(f"f{i}", "F", [3, 2, 4, 3]) for i in range(10)]
             + [jugador(f"d{i}", "D", [0, 1, 0, 0]) for i in range(10)]}
pj = actualizar.parametros_jugadores(PLA)

prueba("separa por puesto", set(pj) == {"F", "D"})
prueba("el delantero tiene su propia media", pj["F"]["remates"]["media"] > 2.5)
prueba("y el defensor la suya", pj["D"]["remates"]["media"] < 0.5)
prueba("cada puesto trae su k", "k" in pj["F"]["remates"])
prueba("y su dispersión", "disp" in pj["D"]["remates"])

prueba("un jugador sin puesto no rompe",
       actualizar.parametros_jugadores(
           {"t1": [{"id": "x", "serie": {"remates": [1, 2], "pj": 2}}]}) == {})
prueba("un puesto con pocos jugadores no inventa parámetros",
       "F" not in actualizar.parametros_jugadores(
           {"t1": [jugador("f1", "F", [1, 2])]}))
prueba("sin planteles no rompe", actualizar.parametros_jugadores({}) == {})
prueba("un jugador sin serie se saltea",
       actualizar.parametros_jugadores({"t1": [{"id": "x", "pos": "F"}]}) == {})

print("")
print("esperado_jugador() — el numero al que se le puede creer")
print("")

par_F = pj["F"]
# Un delantero con 4 partidos rematando 3 por partido: como los
# delanteros SI se distinguen (k bajo), su numero se le respeta.
alto = actualizar.esperado_jugador({"remates": [3, 3, 3, 3], "pj": 4}, par_F)
prueba("le cree bastante al jugador", alto["remates"] > 2.0)
prueba("pero no del todo", alto["remates"] <= 3.0)

# Uno con un solo partido bueno tiene que quedar mas cerca del puesto.
poco = actualizar.esperado_jugador({"remates": [6], "pj": 1}, par_F)
prueba("con un solo partido se apoya en el puesto", poco["remates"] < alto["remates"] + 3)
prueba("nunca se va arriba del propio dato", poco["remates"] <= 6.0)
prueba("sin parámetros del puesto no inventa",
       actualizar.esperado_jugador({"remates": [3], "pj": 1}, {}) == {})
prueba("una métrica sin serie cae al puesto",
       actualizar.esperado_jugador({"pj": 0}, par_F)["remates"]
       == par_F["remates"]["media"])


print("")
print("snapshot_cuotas() — la cuota de hoy, guardada para comparar con la de cierre")
print("")

# ESPN BORRA el bloque de cuotas cuando el partido termina. Se verifico:
# de 11 partidos ya jugados de arg.1, CERO conservaban odds. O sea que el
# CLV no se puede medir hacia atras — hay que ir guardando la foto cada
# corrida, y la ultima antes del inicio es la de cierre.
MERC = {"prov": "DraftKings", "local": 2.65, "empate": 2.90, "visitante": 2.95,
        "totalLinea": 1.5, "totalOver": 1.54, "totalUnder": 2.40}
P1 = [{"id": "e1", "mercado": MERC, "lh": 1.4, "la": 1.0, "rho": 0.05}]

c = actualizar.snapshot_cuotas({}, P1, "2026-08-24T09:00")
prueba("crea la entrada del partido", "e1" in c)
prueba("guarda una foto", len(c["e1"]) == 1)
f = c["e1"][0]
prueba("con la hora", f["t"] == "2026-08-24T09:00")
prueba("con las tres del 1X2", (f["local"], f["empate"], f["visitante"]) == (2.65, 2.90, 2.95))
prueba("con la linea de goles", f["totalLinea"] == 1.5)
prueba("y con lo que pensaba el modelo en ese momento",
       f["lh"] == 1.4 and f["la"] == 1.0)

# Si nada se movio, no se guarda otra foto: seria peso sin informacion.
c2 = actualizar.snapshot_cuotas(c, P1, "2026-08-24T15:00")
prueba("si no se movio nada, no duplica", len(c2["e1"]) == 1)

# Si se movio la cuota, si.
P2 = [dict(P1[0], mercado=dict(MERC, local=2.40))]
c3 = actualizar.snapshot_cuotas(c2, P2, "2026-08-24T15:00")
prueba("si la cuota se movio, agrega foto", len(c3["e1"]) == 2)
prueba("y quedan en orden", c3["e1"][1]["local"] == 2.40)

# Si cambio el modelo pero no la cuota, tambien: el movimiento relativo
# entre los dos es justamente lo que se quiere medir.
P3 = [dict(P1[0], lh=1.9)]
c4 = actualizar.snapshot_cuotas(c3, P3, "2026-08-24T21:00")
prueba("si cambio el modelo, agrega foto", len(c4["e1"]) == 3)

# Nada se borra nunca: un partido que ya no esta en la grilla conserva
# su historia, que es el unico lugar donde vive la cuota de cierre.
c5 = actualizar.snapshot_cuotas(c4, [], "2026-08-25T09:00")
prueba("un partido que salio de la grilla no se borra", len(c5["e1"]) == 3)

prueba("un partido sin mercado no genera entrada",
       actualizar.snapshot_cuotas({}, [{"id": "e9", "lh": 1, "la": 1}], "t") == {})
prueba("sin partidos no rompe", actualizar.snapshot_cuotas({}, [], "t") == {})



# ══════════════════════════════════════════════════════════════════════
# Un solo número por métrica, no dos
#
# La app mostraba DOS expectativas distintas para lo mismo en la misma
# pestaña: "Lo que esperamos acá → CÓRNERS 9.0" (promedio crudo de los
# últimos partidos, vía disciplina_equipo) y "Total del partido: 9.4
# esperados" (el mismo dato encogido hacia el promedio de la liga).
#
# Y el crudo, que además es el que sale en la tarjeta del partido y en
# Análisis, es el peor de los dos. Medido sobre 179 partidos,
# walk-forward, error absoluto medio contra el total real:
#
#     córners    crudo 3.39   encogido 2.67   (err² 17.48 vs 11.08)
#     faltas     crudo 4.90   encogido 4.65
#     tarjetas   crudo 1.77   encogido 1.55
#
# Gana el encogido en las tres. Así que se unifica: un número, un método.
# ══════════════════════════════════════════════════════════════════════

print("")
print("esperado_partido() — una sola expectativa por métrica")
print("")

PAR_DEMO = {
    "corners": {"media": 5.0, "k": 20.0, "disp": 1.75},
    "faltas":  {"media": 12.0, "k": 3.0, "disp": 1.1},
    "tarjetas": {"media": 2.5, "k": 5.0, "disp": 0.72},
}
# Un equipo muy por encima de la media y otro muy por debajo: si el
# encogimiento funciona, los dos terminan cerca de la media de la liga.
ALTO = [{"corners": 9.0, "faltas": 20.0, "tarjetas": 5.0} for _ in range(3)]
BAJO = [{"corners": 1.0, "faltas": 4.0, "tarjetas": 0.0} for _ in range(3)]

e = actualizar.esperado_partido(ALTO, BAJO, PAR_DEMO)
prueba("devuelve las tres métricas que la app muestra",
       all(k in e for k in ("corners", "fouls", "cards")))
prueba("el total es la suma de los dos equipos, no de uno",
       e["corners"] > 5.0)

# El punto del encogimiento: con 3 partidos, un equipo de 9 córners no
# vale 9. La suma cruda daría 10; la encogida tiene que quedar más cerca
# del doble de la media de la liga (10 también, pero por otro camino) y
# sobre todo NO igualar el crudo cuando las muestras son desparejas.
solo_alto = actualizar.esperado_partido(ALTO, ALTO, PAR_DEMO)
prueba("dos equipos altos no llegan al crudo (18): se encogen",
       solo_alto["corners"] < 18.0)
prueba("y quedan por encima del promedio de la liga igual",
       solo_alto["corners"] > 10.0)

prueba("sin parámetros no inventa",
       actualizar.esperado_partido(ALTO, BAJO, {}) is None)
prueba("sin partidos de un equipo tampoco",
       actualizar.esperado_partido(ALTO, [], PAR_DEMO) is None)

# cornersH es la parte del local: se usa para el mercado de córners del
# local y no puede ser mayor que el total.
prueba("los córners del local son parte del total",
       0 < e["cornersH"] <= e["corners"])

# Es el MISMO cálculo que alimenta las líneas de la pestaña
# Estadísticas. Si se separan, vuelve a haber dos números para lo mismo.
esp_alto = actualizar.esperados(ALTO, PAR_DEMO)
esp_bajo = actualizar.esperados(BAJO, PAR_DEMO)
prueba("coincide con esperados(), que es lo que usan las líneas",
       abs(e["corners"] - (esp_alto["corners"] + esp_bajo["corners"])) < 1e-9)


print("")
print("la configuración de competiciones no puede desincronizarse")
print("")

# Son cuatro lugares distintos que tienen que hablar de las mismas ligas:
# COMPETICIONES, CON_FUERZAS, LIGAS_DOMESTICAS y COMPS_ORDEN en el
# index.html. Agregar una liga y olvidarse de uno no rompe nada visible
# — simplemente esa liga anda mal y nadie se entera.

CLAVES = {"nombre", "rho", "conf", "corners", "fouls", "cards"}
prueba("toda competición declara sus seis campos",
       all(CLAVES <= set(v) for v in actualizar.COMPETICIONES.values()))
prueba("ninguna se quedó sin nombre",
       all(v["nombre"].strip() for v in actualizar.COMPETICIONES.values()))

# rho fuera de rango produce probabilidades NEGATIVAS con los topes de
# lambda que la app usa: tau(0,1) = 1 + lh*rho, y lh llega a 3.20, así
# que hace falta rho > -1/3.20 = -0.3125.
prueba("ningún rho puede dar probabilidades negativas",
       all(-0.31 < v["rho"] <= 0.25 for v in actualizar.COMPETICIONES.values()))

prueba("las que ajustan fuerzas existen en COMPETICIONES",
       actualizar.CON_FUERZAS <= set(actualizar.COMPETICIONES))
prueba("las ligas domésticas también",
       actualizar.LIGAS_DOMESTICAS <= set(actualizar.COMPETICIONES))
# Una liga doméstica sin ajuste de fuerzas sería una liga entera cayendo
# al promedio simple sin que nadie lo haya decidido.
prueba("toda liga doméstica ajusta fuerzas",
       actualizar.LIGAS_DOMESTICAS <= actualizar.CON_FUERZAS)

_html = (actualizar.Path(__file__).resolve().parent / "index.html").read_text(
    encoding="utf-8")
prueba("el frontend conoce todas las competiciones",
       all(v["nombre"] in _html for v in actualizar.COMPETICIONES.values()))

# `prior` es opcional: las copas caen al PRIOR_FUERZA global a propósito,
# porque ahí el prior empuja hacia el ancla doméstica y no hacia el
# promedio, y nunca se midió. Pero si está, tiene que ser un entero
# positivo — un prior de 0 saca la regularización entera sin avisar.
prueba("los priors declarados son enteros positivos",
       all(isinstance(v["prior"], int) and v["prior"] > 0
           for v in actualizar.COMPETICIONES.values() if "prior" in v))
prueba("las dos ligas domésticas tienen prior medido",
       all("prior" in actualizar.COMPETICIONES[s]
           for s in actualizar.LIGAS_DOMESTICAS))


print("")
print("el prior por competición tiene que hacer algo")
print("")

# Si `prior` no llegara a fuerzas_equipos(), el barrido de PRIOR_FUERZA
# no habría medido nada y nadie se enteraría: el número quedaría escrito
# en COMPETICIONES sin efecto. Estos tests existen para eso.
import datetime as _dt

_HOY = _dt.date(2026, 6, 1)
# Un equipo que gana todo por goleada contra rivales que pierden todo.
_RES = ([{"fecha": _dt.date(2026, 5, d), "home": "A", "away": str(d),
          "gh": 5.0, "ga": 0.0} for d in range(1, 9)]
        + [{"fecha": _dt.date(2026, 5, d), "home": str(d), "away": "B",
            "gh": 1.0, "ga": 1.0} for d in range(10, 18)])

_flojo, _, _, _ = actualizar.fuerzas_equipos(_RES, _HOY, prior=1)
_fuerte, _, _, _ = actualizar.fuerzas_equipos(_RES, _HOY, prior=40)
prueba("con prior alto el ataque se acerca más al promedio",
       abs(_fuerte["A"][0] - 1.0) < abs(_flojo["A"][0] - 1.0))
prueba("y sigue reconociendo que A ataca mejor que el promedio",
       _fuerte["A"][0] > 1.0)
prueba("sin prior explícito usa el global, no rompe",
       actualizar.fuerzas_equipos(_RES, _HOY)[0]["A"][0] > 0)


print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
