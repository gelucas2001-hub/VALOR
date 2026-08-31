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


# ── Riesgo: el ROI medio esconde cómo fue el camino ───────────────────
#
# Dos estrategias con el mismo ROI no son la misma estrategia si una
# llegó derecho y la otra pasó por una caída del 40% en el medio. Es lo
# que separa algo jugable de algo que se abandona a mitad de camino.

def ap(cuota, gano, dia=1):
    """Una apuesta ficticia. `dia` ordena la secuencia — el drawdown
    depende del orden, así que los tests necesitan controlarlo."""
    from datetime import timedelta
    return {"cuota": cuota, "gano": gano, "ventaja": 0.08, "liga": "arg",
            "fecha": date(2024, 1, 1) + timedelta(days=dia)}


def t_una_racha_ganadora_no_tiene_caida():
    aps = [ap(2.0, True, i + 1) for i in range(10)]
    assert R.roi(aps)["drawdown"] == 0, "inventó una caída en una racha sin perdidas"


def t_cinco_perdidas_seguidas_son_cinco_unidades_de_caida():
    aps = [ap(2.0, False, i + 1) for i in range(5)]
    assert abs(R.roi(aps)["drawdown"] - 5.0) < 1e-9, \
        f"drawdown mal medido: {R.roi(aps)['drawdown']}"


def t_la_caida_se_mide_desde_el_pico_no_desde_el_arranque():
    # sube 4 (4 ganadas a cuota 2), después pierde 3: la caída es 3, no 1
    aps = [ap(2.0, True, i + 1) for i in range(4)] + \
          [ap(2.0, False, i + 5) for i in range(3)]
    d = R.roi(aps)["drawdown"]
    assert abs(d - 3.0) < 1e-9, f"esperaba 3 unidades desde el pico, dio {d}"


def t_el_drawdown_depende_del_orden_cronologico():
    """Las mismas apuestas en otro orden dan otra caída — por eso se ordena."""
    ganadas = [ap(2.0, True, 1), ap(2.0, True, 2)]
    perdidas = [ap(2.0, False, 3), ap(2.0, False, 4)]
    # perdidas primero en la lista, pero con fechas posteriores
    revuelto = perdidas + ganadas
    assert abs(R.roi(revuelto)["drawdown"] - 2.0) < 1e-9, \
        "no ordenó por fecha antes de medir la caída"


def t_sharpe_cero_cuando_no_hay_ventaja():
    aps = [ap(2.0, i % 2 == 0, i + 1) for i in range(100)]
    assert abs(R.roi(aps)["sharpe"]) < 1e-9, "50/50 a cuota 2.0 debe dar Sharpe cero"


def t_sharpe_positivo_cuando_se_gana_mas_de_lo_que_se_pierde():
    aps = [ap(3.0, i % 3 == 0, i + 1) for i in range(99)]   # 33% a cuota 3 = break-even
    aps += [ap(3.0, True, 100), ap(3.0, True, 101)]          # dos ganadas de más
    assert R.roi(aps)["sharpe"] > 0, "no detectó ventaja real"


def t_sin_variacion_no_se_inventa_un_sharpe_infinito():
    """Todas ganadas a la misma cuota: desvío cero, no se divide por cero."""
    aps = [ap(2.0, True, i + 1) for i in range(5)]
    s = R.roi(aps)["sharpe"]
    assert s is None or s == float("inf") or s > 0, f"sharpe roto: {s}"


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
