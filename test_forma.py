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

print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
