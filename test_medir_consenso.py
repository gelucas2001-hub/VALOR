#!/usr/bin/env python3
"""Tests de medir_consenso.py — la estrategia sin modelo.

El método (arXiv 1710.02824, vía `OddsComparisonBettor` de la librería
`sports-betting`): no se predice nada. Se toma el consenso del mercado
como probabilidad real, se le resta `alpha` para descontar el margen, y
se apuesta donde una casa concreta paga más de lo que ese consenso
justifica.

Lo que estos tests protegen es lo mismo de siempre: que la cuenta esté
bien y que el número no se reporte sin su incertidumbre.

    python test_medir_consenso.py
"""

import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

import medir_consenso as C

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


def partido(consenso, casa, real, liga="eng"):
    return {"fecha": date(2024, 1, 1), "liga": liga, "gh": 1, "ga": 0,
            "por_casa": {"promedio": consenso, "bet365": casa},
            "_real": real}


def t_apuesta_donde_la_casa_paga_mas_que_el_consenso():
    # consenso 2.00 -> p=0.50; menos alpha 0.05 -> 0.45
    # bet365 paga 2.40 -> 0.45*2.40 = 1.08 > 1 -> apuesta
    p = partido([2.00, 3.50, 4.00], [2.40, 3.50, 4.00], [1, 0, 0])
    aps = C.apuestas([p], alpha=0.05)
    assert len(aps) == 1, f"esperaba 1 apuesta, dio {len(aps)}"
    assert abs(aps[0]["cuota"] - 2.40) < 1e-9, "no apostó a la cuota de la casa"
    assert aps[0]["gano"] is True


def t_no_apuesta_cuando_la_casa_paga_igual_o_menos():
    # bet365 igual al consenso: con alpha > 0 nunca hay valor
    p = partido([2.00, 3.50, 4.00], [2.00, 3.50, 4.00], [1, 0, 0])
    assert C.apuestas([p], alpha=0.05) == [], "apostó sin que la casa se desvíe"


def t_alpha_cero_apuesta_de_mas():
    """Sin alpha, el margen del consenso se lee como ventaja."""
    p = partido([2.00, 3.50, 4.00], [2.05, 3.55, 4.05], [1, 0, 0])
    assert len(C.apuestas([p], alpha=0.0)) > 0
    assert C.apuestas([p], alpha=0.05) == [], \
        "con alpha razonable no debería quedar valor en una desviación mínima"


def t_ignora_partidos_sin_las_dos_fuentes():
    p = {"fecha": date(2024, 1, 1), "liga": "eng", "gh": 1, "ga": 0,
         "por_casa": {"promedio": [2.0, 3.5, 4.0]}}
    assert C.apuestas([p], alpha=0.05) == [], "apostó sin la casa contra la que comparar"


def t_el_resultado_sale_del_marcador():
    """Si el desenlace se leyera mal, todo el ROI sería basura."""
    p = partido([2.00, 3.50, 4.00], [2.40, 4.20, 4.80], [0, 0, 1])
    p["gh"], p["ga"] = 0, 2          # gana el visitante
    aps = C.apuestas([p], alpha=0.05)
    ganadas = [a for a in aps if a["gano"]]
    assert all(a["i"] == 2 for a in ganadas), \
        f"marcó como ganada una apuesta que no era la del visitante: {aps}"


def t_roi_pide_incertidumbre():
    aps = [{"cuota": 2.0, "gano": i % 2 == 0, "i": 0} for i in range(100)]
    r = C.roi(aps)
    assert r["se"] and r["se"] > 0, "no devolvió error estándar"
    assert abs(r["roi"]) < 1e-9, "50/50 a cuota 2.0 debe dar ROI cero"


def t_sin_apuestas_no_inventa():
    r = C.roi([])
    assert r["n"] == 0 and r["roi"] is None


for nombre, fn in list(globals().items()):
    if nombre.startswith("t_"):
        test(nombre[2:].replace("_", " "), fn)

print(f"\n{ok} ok, {mal} fallando\n")
sys.exit(1 if mal else 0)
