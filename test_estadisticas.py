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

print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
