#!/usr/bin/env python3
"""Tests del cableado de mercado_extra.py adentro de actualizar.py.

Cómo se agregan los mercados de Bet365 a cada partido: sin clave o sin
evento cruzado, no pasa nada — la app queda igual que antes. Con los
dos, se pide una vez por partido y nunca tira si la red falla (un
pedido roto no puede tirar abajo la corrida entera del cron).

    python test_actualizar.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
import actualizar as A
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


# ── mercado_extra_de() ──────────────────────────────────────────────

PARTIDO = {"date": "2026-08-26", "home": "River", "away": "Boca"}
EVENTOS = [{"id": 42, "date": "2026-08-26T20:00Z",
            "home": "CA River Plate", "away": "CA Boca Juniors"}]

prueba("sin clave, no hace nada",
       A.mercado_extra_de(PARTIDO, EVENTOS, None) is None)

prueba("sin eventos, no hace nada",
       A.mercado_extra_de(PARTIDO, [], "clave-falsa") is None)

prueba("no cruza ningun evento, no hace nada",
       A.mercado_extra_de(PARTIDO,
                           [{"id": 1, "date": "2026-08-26T20:00Z",
                             "home": "Otro equipo", "away": "Otro mas"}],
                           "clave-falsa") is None)


def _odds_de_ok(event_id, key):
    return {"1x2": {"local": 2.0, "empate": 3.2, "visitante": 3.8}}, "99"


def _odds_de_falla(event_id, key):
    raise RuntimeError("500")


_orig_odds_de = ME.odds_de
try:
    ME.odds_de = _odds_de_ok
    r = A.mercado_extra_de(PARTIDO, EVENTOS, "clave-falsa")
    prueba("cruza y devuelve los mercados",
           r == {"1x2": {"local": 2.0, "empate": 3.2, "visitante": 3.8}})
finally:
    ME.odds_de = _orig_odds_de

try:
    ME.odds_de = _odds_de_falla
    r = A.mercado_extra_de(PARTIDO, EVENTOS, "clave-falsa")
    prueba("si el pedido de odds falla, no tira: devuelve None", r is None)
finally:
    ME.odds_de = _orig_odds_de


# ── eventos_extra() ────────────────────────────────────────────────

def _eventos_de_ok(slug, key):
    return [{"id": 1}]


def _eventos_de_falla(slug, key):
    raise RuntimeError("timeout")


_orig_eventos_de = ME.eventos_de
try:
    ME.eventos_de = _eventos_de_ok
    cache = {}
    r1 = A.eventos_extra("arg.1", "clave-falsa", cache)
    r2 = A.eventos_extra("arg.1", "clave-falsa", cache)
    prueba("trae los eventos la primera vez", r1 == [{"id": 1}])
    prueba("la segunda vez usa el cache, no vuelve a pedir", r2 is r1)
finally:
    ME.eventos_de = _orig_eventos_de

try:
    ME.eventos_de = _eventos_de_falla
    cache = {}
    r = A.eventos_extra("arg.1", "clave-falsa", cache)
    prueba("si falla el pedido de eventos, no tira: devuelve lista vacia", r == [])
finally:
    ME.eventos_de = _orig_eventos_de


print(f"\n{ok} ok, {fallan} fallan")
sys.exit(1 if fallan else 0)
