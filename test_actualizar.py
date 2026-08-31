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


# ── snapshot_props() ────────────────────────────────────────────────

PARTIDO_CON_PROPS = {
    "id": "espn1", "date": "2026-08-26", "comp": "Liga Profesional Argentina",
    "home": "River", "away": "Boca",
    "mercadoExtra": {
        "remates": {"Junior Sornoza": {"lado": "L", "lineas": {"1.5": 1.9, "2.5": 3.2}}},
    },
}

prueba("primera foto: crea la entrada",
       len(A.snapshot_props({}, [PARTIDO_CON_PROPS], "t1")) == 1)

_una = A.snapshot_props({}, [PARTIDO_CON_PROPS], "t1")
prueba("guarda liga, línea y cuota",
       list(_una.values())[0][0]["lineas"] == {"1.5": 1.9, "2.5": 3.2})

_dos = A.snapshot_props(_una, [PARTIDO_CON_PROPS], "t2")
prueba("sin cambios, no agrega una foto nueva",
       len(list(_dos.values())[0]) == 1)

_movido = {**PARTIDO_CON_PROPS, "mercadoExtra": {
    "remates": {"Junior Sornoza": {"lado": "L", "lineas": {"1.5": 1.85, "2.5": 3.2}}}}}
_tres = A.snapshot_props(_una, [_movido], "t2")
prueba("la línea se movió: agrega una foto nueva",
       len(list(_tres.values())[0]) == 2)

prueba("sin mercadoExtra, no rompe y no agrega nada",
       A.snapshot_props({}, [{"id": "espn2"}], "t1") == {})


print("")
print("corregir_escala() — el modelo exageraba su rango de goles")
print("")

# Medido el 2026-08-30 (medir_compresion.py, barrido_escala_lambda.py):
# el modelo predice un rango de 1.80 a 3.11 goles donde la realidad va
# de 2.07 a 2.44. La corrección lo encoge hacia la media de la liga.

_MU = 2.5

prueba("con k=1 no toca nada (es el comportamiento viejo)",
       A.corregir_escala(1.6, 1.1, _MU, 1.0) == (1.6, 1.1))

lh, la = A.corregir_escala(2.0, 1.5, _MU, 0.5)
prueba("un partido de mucho gol se acerca a la media",
       abs((lh + la) - (_MU + 0.5 * (3.5 - _MU))) < 1e-9)

lh2, la2 = A.corregir_escala(0.9, 0.7, _MU, 0.5)
prueba("y uno de poco gol tambien, desde el otro lado",
       abs((lh2 + la2) - (_MU + 0.5 * (1.6 - _MU))) < 1e-9)

lh3, la3 = A.corregir_escala(2.0, 1.0, _MU, 0.5)
prueba("el reparto local/visitante se mantiene: corrige cuanto, no quien",
       abs(lh3 / (lh3 + la3) - 2.0 / 3.0) < 1e-9)

prueba("un k de liga que no esta medido no corrige nada",
       A.escala_de("competicion.inventada") == 1.0)

prueba("y las medidas traen su valor",
       0 < A.escala_de("arg.1") < 1.0)

prueba("una liga sin centro medido tampoco se corrige",
       A.centro_de("competicion.inventada") is None)

prueba("sin centro, corregir_escala devuelve el lambda intacto aunque haya k",
       A.corregir_escala(2.0, 1.5, None, 0.5) == (2.0, 1.5))

# El centro NO es mu_local+mu_visita: medido sobre arg, eso da 2.025
# mientras la media real de lambda es 2.266, porque lambda es
# multiplicativo y E[a*d] no vale 1. Centrar mal metia -0.11 goles de
# sesgo en cada partido, sin excepcion ni aviso.
prueba("el centro de cada liga es el mismo con el que se midio su k",
       abs(A.centro_de("arg.1") - 2.266) < 1e-9
       and abs(A.centro_de("eng.1") - 2.785) < 1e-9)

_c = A.centro_de("arg.1")
_lh, _la = A.corregir_escala(_c * 0.6, _c * 0.4, _c, A.escala_de("arg.1"))
prueba("un partido que ya esta en el centro no se mueve",
       abs((_lh + _la) - _c) < 1e-9)

lh4, la4 = A.corregir_escala(0.2, 0.1, _MU, 0.0)
prueba("nunca devuelve un lambda que rompa la matriz", lh4 > 0 and la4 > 0)


print("")
print("encoger_diferencia() — el modelo separaba de mas a los equipos")
print("")

# Segundo eje del mismo defecto. corregir_escala arregla CUANTOS goles
# hay; esto arregla CUANTA diferencia hay entre los dos equipos. Medido
# el 2026-08-30: solo pasa en arg (+2.4 e.e.), no en bra/eng/fra.

prueba("con k=1 no toca nada", A.encoger_diferencia(2.0, 1.0, 1.0) == (2.0, 1.0))

_l, _v = A.encoger_diferencia(2.0, 1.0, 0.5)
prueba("el TOTAL de goles no se mueve", abs((_l + _v) - 3.0) < 1e-9)
prueba("y la brecha se achica a la mitad", abs((_l - _v) - 0.5) < 1e-9)

_l0, _v0 = A.encoger_diferencia(2.0, 1.0, 0.0)
prueba("k=0 iguala a los dos equipos", abs(_l0 - _v0) < 1e-9)

prueba("una liga sin diferencia medida no se corrige",
       A.diferencia_de("competicion.inventada") == 1.0)
prueba("arg si se corrige, y por debajo de 1",
       0.5 < A.diferencia_de("arg.1") < 1.0)
prueba("bra NO se corrige: ahi el modelo no exagera",
       A.diferencia_de("bra.1") == 1.0)
prueba("eng tampoco", A.diferencia_de("eng.1") == 1.0)

_lx, _vx = A.encoger_diferencia(0.4, 0.35, 0.0)
prueba("nunca devuelve un lambda que rompa la matriz", _lx > 0 and _vx > 0)

print(f"\n{ok} ok, {fallan} fallan")
sys.exit(1 if fallan else 0)
