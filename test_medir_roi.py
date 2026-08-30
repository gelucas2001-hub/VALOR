#!/usr/bin/env python3
"""Tests de medir_roi.py — la regla de valor de la app, contra plata.

Por qué importa que estos tests existan: el ROI es el número que decide
si el producto sirve, y es fácil de calcular mal de maneras que se ven
bien. Los dos errores clásicos:

- **Contar la apuesta ganada como +cuota en vez de +(cuota-1).** Infla
  el ROI por el monto apostado en cada acierto.
- **Reportar un ROI positivo sin su incertidumbre.** Con 40 apuestas,
  +11% y −11% son el mismo resultado. Ya pasó en este repo con córners
  (§6vicies quater), y por eso ahí hay un test que exige que NO se
  marque como significativo.

Corré:  python test_medir_roi.py
"""

import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

import medir_roi as R

ok = mal = 0


def test(nombre, fn):
    global ok, mal
    try:
        fn()
        print(f"  ok   {nombre}")
        ok += 1
    except AssertionError as e:
        print(f"  FALLA {nombre}\n         {e}")
        mal += 1


def fila(modelo, mercado, cuotas, real, liga="arg"):
    """Una fila como la que devuelve medir_historico.evaluar()."""
    return {"fecha": date(2024, 1, 1), "modelo": modelo, "mercado": mercado,
            "cuotas": cuotas, "real": real, "liga": liga,
            "home": "A", "away": "B"}


# ── La regla: a qué se apuesta ────────────────────────────────────────

def t_apuesta_dentro_de_la_ventana():
    # modelo 0.50 vs mercado 0.40 = 10pp de ventaja, dentro de [6,12]
    f = fila([0.50, 0.25, 0.25], [0.40, 0.30, 0.30], [2.4, 3.3, 3.3], [1, 0, 0])
    aps = R.apuestas([f])
    assert len(aps) == 1, f"esperaba 1 apuesta, dio {len(aps)}"
    assert aps[0]["gano"] is True, "el local ganó y la apuesta figura perdida"


def t_no_apuesta_abajo_del_piso():
    # 3pp de ventaja: adentro del propio error del modelo, no se apuesta
    f = fila([0.43, 0.28, 0.29], [0.40, 0.30, 0.30], [2.4, 3.3, 3.3], [1, 0, 0])
    assert R.apuestas([f]) == [], "apostó con ventaja por debajo de VALOR_MIN"


def t_no_apuesta_arriba_del_techo():
    # 20pp: no es una oportunidad, es el modelo equivocado
    f = fila([0.60, 0.20, 0.20], [0.40, 0.30, 0.30], [2.4, 3.3, 3.3], [1, 0, 0])
    assert R.apuestas([f]) == [], "apostó con ventaja por encima de VALOR_MAX"


def t_no_apuesta_cuota_muy_alta():
    # ventaja de 8pp pero cuota 6.0 — arriba de MAX_ODDS
    f = fila([0.25, 0.25, 0.50], [0.17, 0.25, 0.58], [6.0, 3.9, 1.7], [1, 0, 0])
    aps = R.apuestas([f])
    assert all(a["cuota"] <= R.MAX_ODDS for a in aps), \
        f"apostó a una cuota arriba de MAX_ODDS: {[a['cuota'] for a in aps]}"


# ── La cuenta: cuánto se gana ─────────────────────────────────────────

def t_ganada_paga_cuota_menos_uno():
    """El error clásico: contar +cuota en vez de +(cuota-1)."""
    aps = [{"cuota": 2.0, "gano": True, "ventaja": 0.08, "liga": "arg"}]
    r = R.roi(aps)
    assert abs(r["roi"] - 1.0) < 1e-9, \
        f"una ganada a cuota 2.0 debe dar +100% de ROI, dio {r['roi']*100:.1f}%"


def t_perdida_pierde_todo_lo_apostado():
    aps = [{"cuota": 2.0, "gano": False, "ventaja": 0.08, "liga": "arg"}]
    r = R.roi(aps)
    assert abs(r["roi"] + 1.0) < 1e-9, \
        f"una perdida debe dar -100% de ROI, dio {r['roi']*100:.1f}%"


def t_mitad_y_mitad_a_cuota_dos_da_cero():
    aps = [{"cuota": 2.0, "gano": True, "ventaja": 0.08, "liga": "arg"},
           {"cuota": 2.0, "gano": False, "ventaja": 0.08, "liga": "arg"}]
    r = R.roi(aps)
    assert abs(r["roi"]) < 1e-9, f"50/50 a cuota 2.0 es ROI cero, dio {r['roi']}"


# ── La incertidumbre: sin esto el número miente ───────────────────────

def t_reporta_error_estandar():
    aps = [{"cuota": 2.0, "gano": i % 2 == 0, "ventaja": 0.08, "liga": "arg"}
           for i in range(100)]
    r = R.roi(aps)
    assert r["se"] > 0, "no devolvió error estándar"
    assert 0.05 < r["se"] < 0.15, \
        f"el error estándar de 100 apuestas a cuota 2.0 debería rondar 0.10, dio {r['se']:.3f}"


def t_muestra_chica_no_es_significativa():
    """El caso que ya se equivocó una vez en este repo, con córners."""
    # 40 apuestas con +11% de ROI: parece bueno y es ruido
    aps = ([{"cuota": 2.3, "gano": True, "ventaja": 0.08, "liga": "arg"}] * 19 +
           [{"cuota": 2.3, "gano": False, "ventaja": 0.08, "liga": "arg"}] * 21)
    r = R.roi(aps)
    assert not r["significativo"], \
        f"marcó como significativo un ROI de {r['roi']*100:+.1f}% con solo {r['n']} apuestas"


def t_sin_apuestas_no_inventa_numero():
    r = R.roi([])
    assert r["n"] == 0
    assert r["roi"] is None, "inventó un ROI sin una sola apuesta"


# ── El mercado de GOLES, que nunca se había medido contra plata ───────

def fila_ou(modelo_ou, cuotas_ou, real_ou, liga="eng"):
    return {"fecha": date(2024, 1, 1), "modelo_ou": modelo_ou,
            "cuotas_ou": cuotas_ou, "real_ou": real_ou, "liga": liga,
            "home": "A", "away": "B"}


# El par 1.95/1.90 devigado con Shin da [0.4935, 0.5065] — de ahí
# salen los números de abajo. Ponerlos a ojo hacía que los fixtures
# cayeran fuera de la ventana [0.06, 0.12] y el test "pasara" por el
# motivo equivocado.
def t_ou_apuesta_al_over_con_ventaja():
    # 0.58 − 0.4935 = 8.65pp, dentro de la ventana
    f = fila_ou([0.58, 0.42], [1.95, 1.90], [1, 0])
    aps = R.apuestas_ou([f])
    assert len(aps) == 1, f"esperaba 1 apuesta, dio {len(aps)}"
    assert aps[0]["gano"] is True, "el over entró y figura perdido"
    assert abs(aps[0]["cuota"] - 1.95) < 1e-9, "no usó la cuota del over"


def t_ou_apuesta_al_under_cuando_la_ventaja_esta_del_otro_lado():
    # 0.60 − 0.5065 = 9.35pp
    f = fila_ou([0.40, 0.60], [1.95, 1.90], [0, 1])
    aps = R.apuestas_ou([f])
    assert len(aps) == 1 and abs(aps[0]["cuota"] - 1.90) < 1e-9, \
        "no apostó al under con la ventaja de ese lado"


def t_ou_no_apuesta_sin_ventaja():
    # modelo casi igual al mercado
    f = fila_ou([0.50, 0.50], [1.95, 1.90], [1, 0])
    assert R.apuestas_ou([f]) == [], "apostó sin ventaja real"


def t_ou_ignora_filas_sin_mercado_de_goles():
    """arg y bra no tienen over/under en la fuente. No se inventa."""
    f = {"fecha": date(2024, 1, 1), "modelo_ou": None, "cuotas_ou": None,
         "real_ou": None, "liga": "arg"}
    assert R.apuestas_ou([f]) == [], "inventó una apuesta sin cuotas de goles"


def t_ou_devigea_antes_de_comparar():
    """Sin quitar el margen, cualquier cuota parece generosa.

    El fixture está elegido para que la respuesta DEPENDA del devig:
    con margen quitado (over = 0.4935) la ventaja es 6.65pp y entra en
    la ventana; sin quitarlo (0.5128) sería 4.72pp y quedaría afuera.
    Si alguien saca el devig, este test falla — que es el punto.
    """
    f = fila_ou([0.56, 0.44], [1.95, 1.90], [1, 0])
    aps = R.apuestas_ou([f])
    assert aps, "no apostó: sugiere que comparó contra la cuota con margen"
    assert 0.06 <= aps[0]["ventaja"] <= 0.07, \
        f"la ventaja sugiere que no se quitó el margen: {aps[0]['ventaja']:.4f}"


for nombre, fn in list(globals().items()):
    if nombre.startswith("t_"):
        test(nombre[2:].replace("_", " "), fn)

print(f"\n{ok} ok, {mal} fallando\n")
sys.exit(1 if mal else 0)
