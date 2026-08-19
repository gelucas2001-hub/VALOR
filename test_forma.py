#!/usr/bin/env python3
"""Tests de forma() — la forma reciente que se le entrega al análisis.

Existen por un motivo puntual: la forma no tenía fecha, así que un análisis
no podía distinguir cinco partidos en cinco semanas de cinco en cinco meses.
Se le agregó la fecha, y tiene que salir en el MISMO formato que usa h2h
(DD/MM/AA) — si aparece un tercer formato en el expediente, el que lo lee
tiene que adivinar cuál es cuál.

    python test_forma.py
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


def jugado(fecha, gf, gc, local=True, rival="Rival"):
    return {"fecha": fecha, "id": "1", "local": local, "gf": gf, "gc": gc,
            "rival_id": "99", "home": "Local" if local else rival,
            "away": rival if local else "Local"}


print("\nforma() — fecha en la forma reciente\n")

f = actualizar.forma([jugado("2026-08-16T23:00Z", 2, 1)])
prueba("cada partido trae fecha", "d" in f[0])
prueba("formato DD/MM/AA", f[0].get("d") == "16/08/26")

# El punto del cambio: mismo formato que h2h, no uno nuevo.
dd = "2026-08-16"[:10]
como_h2h = f"{dd[8:10]}/{dd[5:7]}/{dd[2:4]}"
prueba("coincide con el formato de h2h", f[0].get("d") == como_h2h)

# Un día y un mes de un solo dígito no pueden salir sin el cero adelante,
# o el orden alfabético deja de coincidir con el cronológico.
f = actualizar.forma([jugado("2026-01-05T20:00Z", 0, 0)])
prueba("día y mes con cero adelante", f[0].get("d") == "05/01/26")

# Una fecha vacía llega desde la API cuando el evento no la trae. No debe
# reventar: el resto del partido sigue siendo información válida.
f = actualizar.forma([jugado("", 1, 0)])
prueba("fecha vacía no rompe", len(f) == 1 and f[0].get("d") == "")

# Lo que ya funcionaba tiene que seguir igual.
f = actualizar.forma([jugado("2026-08-16T23:00Z", 2, 1, local=True, rival="Boca")])
prueba("gana de local", f[0]["r"] == "W" and f[0]["local"] is True)
prueba("marcador desde la óptica del equipo", f[0]["marcador"] == "2-1")
prueba("rival correcto", f[0]["rival"] == "Boca")

f = actualizar.forma([jugado("2026-08-16T23:00Z", 0, 3, local=False, rival="River")])
prueba("pierde de visitante", f[0]["r"] == "L" and f[0]["local"] is False)

f = actualizar.forma([jugado(f"2026-08-{d:02d}T20:00Z", 1, 1) for d in range(1, 10)])
prueba("corta en 5 partidos", len(f) == 5)

print("\nforma_general() — la forma sin importar torneo\n")

# Un equipo con partidos recientes en dos competencias: la Liga (semanal,
# fresca) y una copa de baja frecuencia (vieja). forma_general tiene que
# mezclar las dos y ordenar por fecha real, no por competencia.
liga = [jugado("2026-08-16T23:00Z", 2, 0, rival="Boca"),
        jugado("2026-08-09T20:00Z", 1, 1, rival="River")]
copa = [jugado("2026-05-28T23:00Z", 3, 0, rival="Blooming"),
        jugado("2026-05-21T23:00Z", 1, 1, rival="Bragantino")]

fg = actualizar.forma_general(liga, copa)
prueba("junta las dos competencias", len(fg) == 4)
prueba("ordena por fecha, no por competencia",
       [p["d"] for p in fg] == ["16/08/26", "09/08/26", "28/05/26", "21/05/26"])
prueba("el más reciente es el de la Liga", fg[0]["rival"] == "Boca")

fg = actualizar.forma_general(liga, copa, n=2)
prueba("corta en n incluso mezclando competencias", len(fg) == 2)
prueba("el corte respeta el orden por fecha",
       [p["rival"] for p in fg] == ["Boca", "River"])

# Competencia sin partidos (el equipo no juega esa copa esta temporada):
# historial() ya devuelve lista vacía, forma_general no debe romperse.
fg = actualizar.forma_general(liga, [])
prueba("una lista vacía no rompe la mezcla", len(fg) == 2)

print("\njugados_de_resultados() — la forma doméstica, sin pedido nuevo\n")

# La forma de resultados_temporada(): home/away son IDS, no nombres, y
# fecha es un date, no string -- así sale del scoreboard crudo.
import datetime as _dt
crudos = [
    {"fecha": _dt.date(2026, 8, 16), "home": "15", "away": "5",
     "gh": 2, "ga": 1, "id": "1", "home_nombre": "Racing Club", "away_nombre": "Boca Juniors"},
    {"fecha": _dt.date(2026, 8, 9), "home": "3", "away": "15",
     "gh": 0, "ga": 0, "id": "2", "home_nombre": "Argentinos Juniors", "away_nombre": "Racing Club"},
    {"fecha": _dt.date(2026, 8, 2), "home": "999", "away": "888",
     "gh": 3, "ga": 3, "id": "3", "home_nombre": "Otro", "away_nombre": "Otro2"},
]

jr = actualizar.jugados_de_resultados("15", crudos)
prueba("filtra solo los partidos del equipo pedido", len(jr) == 2)
prueba("ordena del más reciente al más viejo",
       [j["fecha"] for j in jr] == ["2026-08-16", "2026-08-09"])
prueba("de local: gf/gc sin invertir", jr[0]["local"] is True and jr[0]["gf"] == 2 and jr[0]["gc"] == 1)
prueba("de visitante: gf/gc invertidos respecto de home/away", jr[1]["local"] is False and jr[1]["gf"] == 0 and jr[1]["gc"] == 0)
prueba("fecha en formato ISO (para fecha_corta)", jr[0]["fecha"] == "2026-08-16")

# El resultado tiene que poder alimentar forma() directo, sin adaptar nada más.
f = actualizar.forma(jr)
prueba("alimenta forma() sin adaptar nada más", f[0]["rival"] == "Boca Juniors" and f[1]["rival"] == "Argentinos Juniors")

jr_vacio = actualizar.jugados_de_resultados("15", [])
prueba("lista de resultados vacía no rompe", jr_vacio == [])

print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
