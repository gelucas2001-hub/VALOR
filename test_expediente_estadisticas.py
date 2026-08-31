#!/usr/bin/env python3
"""Tests de expediente_estadisticas.py — el expediente de la 2ª skill.

Lo que protegen, y el primero vale por todos:

- **Que no se filtre la salida del modelo.** Si la skill ve λ o una
  cuota, su lectura deja de ser independiente y la app termina
  comparando el modelo contra sí mismo. Ya pasó una vez con la otra
  skill (TRASPASO §6nonies) y costó rehacerla. El expediente es una
  lista blanca: lo que no está, no viaja — así que el test tiene que
  fallar si alguien agrega un campo del modelo sin darse cuenta.
- **Que `concede` viaje.** Es el campo que sostiene casi toda
  conclusión útil del mercado de estadísticas: sin él la skill solo
  puede describir a un equipo, y la pregunta es sobre el cruce.
- **Que viaje la SERIE y no el promedio.** `[1,0,6]` y `[2,2,3]` tienen
  la misma media y no son el mismo jugador.
- **Que los huecos se declaren.** Un equipo sin estadísticas tiene que
  generar un aviso, no desaparecer en silencio.

    python test_expediente_estadisticas.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import expediente_estadisticas as E

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


PARTIDO = {
    "id": "espn1", "home": "Local FC", "away": "Visita FC",
    "homeId": "10", "awayId": "20",
    "comp": "Liga", "date": "2026-09-01", "hora": "16:00",
    "estadio": "Cancha", "ciudad": "Ciudad", "arbitro": "Juez",
    # Todo lo que sigue es salida del modelo o precio: NADA puede viajar.
    "lh": 1.7, "la": 1.1, "rho": -0.05, "conf": 75,
    "corners": 9.4, "fouls": 24.0, "cards": 4.8,
    "mercado": {"local": 1.85, "empate": 3.4},
    "mercadoExtra": {"remates": {"Fulano": {"lineas": {"1.5": 1.9}}}},
    "note": "λ calculados con datos de ESPN",
}

EST = {"equipos": {
    "10": {"pj": 5, "remates": 12.0, "corners": 5.0, "faltas": 11.0,
           "tarjetas": 1.4, "posesion": 48.0, "tackles": 15.0, "al_arco": 4.0,
           "concede": {"remates": 18.0, "corners": 7.0},
           "local": {"remates": 15.0}, "visita": {"remates": 9.0}},
    "20": {"pj": 4, "remates": 10.0, "al_arco": 3.0, "corners": 4.0,
           "faltas": 13.0, "tarjetas": 2.0, "posesion": 52.0, "tackles": 17.0,
           "concede": {"remates": 11.0}},
}}

PLANT = {"equipos": {
    "10": [{"id": "1", "nombre": "Rematador", "pos": "F", "pj": 20,
            "serie": {"pj": 3, "tit": 3, "remates": [1, 0, 6],
                      "al_arco": [1, 0, 2], "goles": [0, 0, 1]}},
           {"id": "2", "nombre": "Suplente", "pos": "M", "pj": 2,
            "serie": {"pj": 1, "tit": 0, "remates": [0]}}],
    "20": [{"id": "3", "nombre": "Lateral", "pos": "D", "pj": 18,
            "serie": {"pj": 2, "tit": 2, "faltas": [3, 1]}}],
}}

CAL = {"metricas": {"remates": {"nivel": "mal", "n": 618},
                    "goles": {"nivel": "bien", "n": 611}}}

e = E.expediente(PARTIDO, est=EST, planteles=PLANT, cal=CAL)
plano = repr(e)


print("\nEl recorte — lo que NO puede viajar\n")

for campo, valor in (("lh", "1.7"), ("la", "1.1"), ("rho", "-0.05"),
                     ("conf", "75")):
    prueba(f"no viaja {campo} ({E.EXCLUIDOS.get(campo, '')[:34]}…)",
           campo not in e)
prueba("no viajan las cuotas de DraftKings", "1.85" not in plano)
prueba("no viajan las de Bet365, que son las de ESTE mercado",
       "mercadoExtra" not in e and "Fulano" not in plano)
prueba("no viajan los córners que esperamos NOSOTROS",
       e.get("corners") is None and "9.4" not in plano)
prueba("ni las faltas ni las tarjetas esperadas por nosotros",
       "24.0" not in plano and "4.8" not in plano)
prueba("no viaja la nota que nombra al modelo", "note" not in e)
prueba("cada exclusión está documentada con su motivo",
       all(isinstance(v, str) and len(v) > 10 for v in E.EXCLUIDOS.values()))


print("\nLo que SÍ tiene que viajar\n")

prueba("el id y los dos equipos", e["espn_id"] == "espn1"
       and e["equipo_local"] == "Local FC")
prueba("se declara de qué mercado es", e.get("mercado") == "estadisticas")
prueba("el estadio y la hora, que cambian el juego",
       e.get("estadio") == "Cancha" and e.get("hora") == "16:00")

loc = e.get("equipoLocal") or {}
prueba("lo que el equipo PRODUCE", (loc.get("produce") or {}).get("remates") == 12.0)
prueba("y sobre todo lo que CONCEDE, que es lo que arma el cruce",
       (loc.get("concede") or {}).get("remates") == 18.0)
prueba("el split de local y visita cuando está",
       (loc.get("local") or {}).get("remates") == 15.0)
prueba("cuántos partidos hay detrás de esos promedios", loc.get("partidos") == 5)


print("\nJugadores — la serie, no el promedio\n")

js = e.get("jugadoresLocal") or []
prueba("viajan los jugadores del equipo", len(js) == 2)
prueba("ordenados por partidos jugados", js[0]["nombre"] == "Rematador")
prueba("viaja la SERIE entera, no su media",
       js[0]["serie"]["remates"] == [1, 0, 6])
prueba("y cuántos partidos tiene esa serie",
       js[0]["partidos_en_serie"] == 3 and js[0]["titular_en"] == 3)
prueba("una métrica en cero no ensucia la serie del jugador",
       "asist" not in js[0]["serie"])
prueba("el tope de plantel se respeta",
       len(E.jugadores_de(PLANT["equipos"]["10"], tope=1)) == 1)


print("\nLos huecos y los avisos\n")

prueba("la fiabilidad medida viaja, para que no afirme de más",
       (e.get("fiabilidad_medida") or {}).get("remates", {}).get("nivel") == "mal")
prueba("hay aviso sobre lo corto de las series",
       any("partidos_en_serie" in a for a in e["avisos"]))
prueba("y sobre el árbitro, que está medido en cero",
       any("CERO" in a for a in e["avisos"]))

sin_est = E.expediente(dict(PARTIDO, homeId="999"), est=EST,
                       planteles=PLANT, cal=CAL)
prueba("un equipo sin estadísticas genera aviso, no silencio",
       any("Sin estadísticas" in a for a in sin_est["avisos"]))
prueba("y no inventa el bloque del equipo que falta",
       "equipoLocal" not in sin_est)

sin_arb = E.expediente({k: v for k, v in PARTIDO.items() if k != "arbitro"},
                       est=EST, planteles=PLANT, cal=CAL)
prueba("sin árbitro no aparece el aviso del árbitro",
       not any("CERO" in a for a in sin_arb["avisos"]))


print("\nmetricas_equipo() — sin datos no arma un objeto vacío\n")

prueba("sin estadísticas devuelve None", E.metricas_equipo(None) is None)
prueba("con solo el contador de partidos tampoco arma nada",
       E.metricas_equipo({"pj": 4}) is None)
prueba("con una métrica sola ya arma",
       (E.metricas_equipo({"pj": 4, "remates": 1.0}) or {}).get("produce"))


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
