#!/usr/bin/env python3
"""Barrido out-of-sample de los parámetros que afectan a lambda (el nivel
de goles esperados), con walk-forward temporal.

Por qué existe:

`backtest.py` reconstruye lo que el modelo habría dicho y muestra que el
sesgo está en los mercados de GOLES: el modelo subestima over 2.5 (dice
30% y pasan 37-65%) y pierde contra la tasa base en casi todos los
mercados de goles de todas las ligas. El 1X2 en cambio captura ~39% de
lo que mejora el mercado.

Para arreglar el sesgo de goles hay que tocar una constante del motor
(VIDA_MEDIA_DIAS, prior, rho, o la escala de mu), y AGENTS.md exige que
cualquier cambio salga de una medición walk-forward fuera de muestra que
mejore la métrica relevante CON su incertidumbre, no de tunear hacia
atrás. Este script es esa medición.

Cómo se mide:

Walk-forward temporal estricto sobre TODO el historial de la liga
(`historico.py`, cuota de cierre de Pinnacle). Para cada partido se
ajustan las fuerzas con SOLO lo anterior, y se compara lo predicho
contra lo que realmente pasó. Se parte el historial en dos:

  - train: partidos con fecha < 2022  -> se ELIGE el mejor parámetro
  - test:  partidos con fecha >= 2022 -> se CONFIRMA fuera de muestra

Elegir con train y confirmar con test es lo que separa un hallazgo
real de un ajuste hacia atrás.

Qué parámetros se barren (cada uno toca lambda):
  - escala_goles: factor multiplicativo sobre mu_local/mu_visita. Apunta
    DIRECTO al sesgo (modelo subestima goles -> escala > 1 debería
    corregirlo, SI el sesgo está en mu).
  - vida: VIDA_MEDIA_DIAS, la ventana de ponderación por antigüedad.
  - rho: la corrección de Dixon-Coles de los marcadores bajos. Un rho
    más negativo reduce 0-0/1-1 y sube over 2.5.
  - prior: PRIOR_FUERZA, la regularización de las fuerzas.

Qué mide cada corrida (por partición train/test):
  - Brier de over 1.5 / 2.5 / 3.5 / ambos marcan (los mercados de goles)
  - log-loss de la distribución completa de goles (la celda del marcador)
  - Brier 1X2 (efecto colateral)
  - over 2.5: la frecuencia real vs la predicha (el sesgo en una línea)

NO toca nada: es de solo lectura. No implementa ningún cambio; solo
encontrar (o no) una combinación que la medición sostenga.

    python barrido_lambda.py arg            # barrido completo sobre arg
    python barrido_lambda.py bra            # idem bra, como contraste
    python barrido_lambda.py arg --fast     # submuestrea la evaluación
                                            # (para explorar barato); lo
                                            # ganador se confirma luego
                                            # con la corrida completa
"""

import argparse
import datetime
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import historico as H
import backtest as B
import medir_clv
import actualizar as A

# Cuánta historia hace falta antes de empezar a evaluar, y ventana de
# ajuste. Igual que medir_historico.py: la ventana de 1825 días es la
# que corresponde a TEMPORADAS_HISTORIA=5 (la app), no una que dé lindo.
MIN_PREVIOS = 40
VENTANA = 1825
CORTE_TRAIN = datetime.date(2022, 1, 1)


def fuerzas_equipos_var(resultados, hoy, vida, prior, anclas=None, vida_mu=None):
    """Copia de actualizar.fuerzas_equipos() pero con VIDA_MEDIA_DIAS y
    prior parametrizables (el original lee constantes globales). El
    cálculo es idéntico; solo se toman dos constantes como argumento.

    Opcionalmente `vida_mu` separa la ventana de ponderación del NIVEL
    de goles (mu_local/mu_visita) de la de las fuerzas por equipo. Por
    defecto (None) usa la misma `vida` para ambos, como producción."""
    if not resultados:
        return {}, 1.0, 1.0, {}
    vmu = vida if vida_mu is None else vida_mu
    pesos_mu = [0.5 ** ((hoy - p["fecha"]).days / vmu) for p in resultados]
    w_mu = sum(pesos_mu)
    mu_local = sum(p["gh"] * w for p, w in zip(resultados, pesos_mu)) / w_mu
    mu_visita = sum(p["ga"] * w for p, w in zip(resultados, pesos_mu)) / w_mu
    pesos = [0.5 ** ((hoy - p["fecha"]).days / vida) for p in resultados]
    w_home = sum(pesos)
    equipos = set()
    for p in resultados:
        equipos.add(p["home"]); equipos.add(p["away"])
    pj = {t: 0 for t in equipos}
    for p in resultados:
        pj[p["home"]] += 1; pj[p["away"]] += 1
    ataque = {t: 1.0 for t in equipos}; defensa = {t: 1.0 for t in equipos}
    anc = anclas or {}
    pf = prior
    for _ in range(40):
        num_a = {t: pf * anc.get(t, (1.0, 1.0))[0] for t in equipos}
        den_a = {t: pf for t in equipos}
        for p, w in zip(resultados, pesos):
            num_a[p["home"]] += w * p["gh"]
            den_a[p["home"]] += w * mu_local * defensa[p["away"]]
            num_a[p["away"]] += w * p["ga"]
            den_a[p["away"]] += w * mu_visita * defensa[p["home"]]
        na = {t: (num_a[t] / den_a[t] if den_a[t] > 0 else 1.0) for t in equipos}
        num_d = {t: pf * anc.get(t, (1.0, 1.0))[0] for t in equipos}
        den_d = {t: pf for t in equipos}
        for p, w in zip(resultados, pesos):
            num_d[p["home"]] += w * p["ga"]
            den_d[p["home"]] += w * mu_visita * na[p["away"]]
            num_d[p["away"]] += w * p["gh"]
            den_d[p["away"]] += w * mu_local * na[p["home"]]
        nd = {t: (num_d[t] / den_d[t] if den_d[t] > 0 else 1.0) for t in equipos}
        ma = sum(na.values()) / len(na); md = sum(nd.values()) / len(nd)
        ataque = {t: v / ma for t, v in na.items()}
        defensa = {t: v / md for t, v in nd.items()}
    fuerzas = {t: (ataque[t], defensa[t]) for t in equipos}
    return fuerzas, mu_local, mu_visita, pj


def ventana_previa(partidos, i, dias=VENTANA):
    """Partidos estrictamente anteriores por FECHA (dos partidos del
    mismo día no se ven entre sí) dentro de `dias` hacia atrás."""
    if not partidos or i <= 0:
        return []
    hoy = partidos[i]["fecha"]
    return [p for p in partidos[:i]
            if p["fecha"] < hoy and (hoy - p["fecha"]).days <= dias]


# ── métricas ─────────────────────────────────────────────────────────

def brier_bin(pred, real):
    return sum((p - y) ** 2 for p, y in zip(pred, real)) / len(pred)


def log_loss_bin(pred, real, eps=1e-15):
    s = 0.0
    for p, y in zip(pred, real):
        p = min(max(p, eps), 1 - eps)
        s += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return s / len(pred)


def mercados_goles(mat, real):
    """Mercados binarios de goles derivados de la matriz y del marcador
    real. `mat` es la matriz Dixon-Coles (0..9), `real` es (gh, ga)."""
    d = {"Más de 1.5": 1 if real[0] + real[1] > 1.5 else 0,
         "Más de 2.5": 1 if real[0] + real[1] > 2.5 else 0,
         "Más de 3.5": 1 if real[0] + real[1] > 3.5 else 0,
         "Ambos marcan": 1 if real[0] > 0 and real[1] > 0 else 0}
    p = {
        "Más de 1.5": B.suma_si(mat, lambda a, b: a + b > 1.5),
        "Más de 2.5": B.suma_si(mat, lambda a, b: a + b > 2.5),
        "Más de 3.5": B.suma_si(mat, lambda a, b: a + b > 3.5),
        "Ambos marcan": B.suma_si(mat, lambda a, b: a > 0 and b > 0),
    }
    return p, d


def log_loss_distribucion(mat, real, mx=9):
    """Log-loss de la celda exacta del marcador (distribución completa)."""
    gh, ga = real
    gh = min(gh, mx); ga = min(ga, mx)
    p = mat[gh][ga]
    p = min(max(p, 1e-15), 1 - 1e-15)
    return -math.log(p)


# ── evaluación walk-forward ──────────────────────────────────────────

def evaluar_parametros(partidos, vida, prior, rho, escala_goles,
                       step=None, vida_mu=None):
    """Walk-forward temporal con parámetros dados, agrupado por fecha y
    con un barrido de ventana eficiente (O(n), no O(n^2)). Devuelve una
    lista de dicts por partido evaluado."""
    filas = []
    by_fecha = {}
    for p in partidos:
        by_fecha.setdefault(p["fecha"], []).append(p)
    fechas = sorted(by_fecha)
    ventana = []          # partidos actuales dentro de VENTANA días hacia atrás
    j = 0
    for contador, f in enumerate(fechas):
        # agregar partidos con fecha < f (todos los anteriores a hoy)
        while j < len(partidos) and partidos[j]["fecha"] < f:
            ventana.append(partidos[j])
            j += 1
        # podar los que exceden la ventana de 1825 días
        while ventana and (f - ventana[0]["fecha"]).days > VENTANA:
            ventana.pop(0)
        prev = ventana
        if len(prev) < MIN_PREVIOS:
            continue
        if step and (contador % step != 0):
            continue
        fuerzas, mu_local, mu_visita, pj = fuerzas_equipos_var(prev, f, vida, prior, vida_mu=vida_mu)
        for p in by_fecha[f]:
            n_loc, n_vis = pj.get(p["home"], 0), pj.get(p["away"], 0)
            if n_loc < A.MIN_PARTIDOS_FUERZA or n_vis < A.MIN_PARTIDOS_FUERZA:
                continue
            a_loc, d_loc = fuerzas.get(p["home"], (1.0, 1.0))
            a_vis, d_vis = fuerzas.get(p["away"], (1.0, 1.0))
            lh = max(0.35, min(3.20, mu_local * escala_goles * a_loc * d_vis))
            la = max(0.30, min(3.00, mu_visita * escala_goles * a_vis * d_loc))
            mat = B.matriz(lh, la, rho)
            pg, dg = mercados_goles(mat, (p["gh"], p["ga"]))
            p1x2 = [B.suma_si(mat, lambda a, b: a > b),
                    B.suma_si(mat, lambda a, b: a == b),
                    B.suma_si(mat, lambda a, b: a < b)]
            real1x2 = (0 if p["gh"] > p["ga"] else
                       1 if p["gh"] == p["ga"] else 2)
            filas.append({
                "fecha": f,
                "pg": pg, "dg": dg,
                "p1x2": p1x2, "real1x2": real1x2,
                "ll_dist": log_loss_distribucion(mat, (p["gh"], p["ga"])),
                "real": (p["gh"], p["ga"]),
            })
    return filas


def resumir(filas, nombre):
    """Agrega las métricas sobre una lista de filas ya filtrada."""
    if not filas:
        return None
    m = {}
    for k in ("Más de 1.5", "Más de 2.5", "Más de 3.5", "Ambos marcan"):
        ps = [f["pg"][k] for f in filas]
        rs = [f["dg"][k] for f in filas]
        m[k] = {
            "brier": round(brier_bin(ps, rs), 5),
            "logloss": round(log_loss_bin(ps, rs), 5),
            "frec_real": round(sum(rs) / len(rs), 4),
            "frec_modelo": round(sum(ps) / len(ps), 4),
        }
    # 1X2
    p1 = [f["p1x2"] for f in filas]
    ll1 = sum(-math.log(max(min(p[f["real1x2"]], 1 - 1e-15), 1e-15)) for p, f in zip(p1, filas)) / len(filas)
    br1 = sum((p[i] - (1 if f["real1x2"] == i else 0)) ** 2
              for p, f in zip(p1, filas) for i in range(3)) / len(filas)
    m["1X2"] = {"brier": round(br1, 5), "logloss": round(ll1, 5),
                "frec_real": round(sum(1 for f in filas if f["real1x2"] == 0) / len(filas), 4)}
    # distribución
    m["distribucion"] = {"logloss": round(sum(f["ll_dist"] for f in filas) / len(filas), 5)}
    m["n"] = len(filas)
    return m


def grilla_por_liga(liga):
    """Grillas por liga, centradas en los valores de producción."""
    prod = {
        "arg.1": {"vida": 300, "prior": 12, "rho": -0.05},
        "bra.1": {"vida": 300, "prior": 8, "rho": 0.0},
    }
    p = prod[liga]
    return {
        "escala_goles": [0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20],
        "vida": [150, 300, 450],
        "rho": [p["rho"] - 0.10, p["rho"] - 0.05, p["rho"], p["rho"] + 0.05],
        "prior": [max(3, p["prior"] - 4), p["prior"], p["prior"] + 4],
    }


def barrido_1d(partidos, liga, params_prod, fast=False):
    """Barre cada parámetro por separado (los demás en producción)."""
    step = 15 if fast else None
    result = {"liga": liga, "produccion": params_prod, "dimensiones": {}}
    gr = grilla_por_liga(liga)
    for nombre, valores in gr.items():
        filas_dim = []
        for v in valores:
            par = dict(params_prod)
            par[nombre] = v
            filas = evaluar_parametros(
                partidos, par["vida"], par["prior"], par["rho"],
                par["escala_goles"], step=step)
            train = [f for f in filas if f["fecha"] < CORTE_TRAIN]
            test = [f for f in filas if f["fecha"] >= CORTE_TRAIN]
            filas_dim.append({
                "parametro": nombre, "valor": v,
                "train": resumir(train, "train"),
                "test": resumir(test, "test"),
            })
        result["dimensiones"][nombre] = filas_dim
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("liga", nargs="?", default="arg")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--salida", default="data/barrido_lambda.json")
    args = ap.parse_args()

    meta = {"arg": "arg.1", "bra": "bra.1"}.get(args.liga)
    if not meta:
        raise SystemExit(f"liga desconocida: {args.liga}. Hay ['arg','bra']")
    prod_ref = {
        "arg.1": {"vida": 300, "prior": 12, "rho": -0.05, "escala_goles": 1.0},
        "bra.1": {"vida": 300, "prior": 8, "rho": 0.0, "escala_goles": 1.0},
    }[meta]

    print(f"\n=== Barrido lambda · {meta} · {'rápido (submuestra)' if args.fast else 'completo'} ===")
    print("Producción:", prod_ref)
    ps = H.partidos(meta.split('.')[0])  # 'arg' / 'bra'
    print(f"{len(ps)} partidos en el CSV, walk-forward temporal...")

    res = barrido_1d(ps, meta, prod_ref, args.fast)
    out = Path(args.salida)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✓ guardado en {out}")

    # informe
    for dim, filas in res["dimensiones"].items():
        print("\n" + "=" * 70)
        print(f"PARÁMETRO: {dim}   (los demás en producción)")
        print("=" * 70)
        hdr = (f"{'valor':>10} | {'n':>4} | {'train over2.5':>14} | "
               f"{'test over2.5':>13} | {'test 1X2 br':>12} | {'test dist LL':>12}")
        print(hdr)
        print("-" * len(hdr))
        for f in filas:
            tr = f["train"]; te = f["test"]
            if not tr or not te:
                continue
            o25 = lambda d: f"{d['Más de 2.5']['brier']:.4f}({d['Más de 2.5']['frec_real']:.2f}/{d['Más de 2.5']['frec_modelo']:.2f})"
            print(f"{f['valor']:>10} | {te['n']:>4} | {o25(tr):>14} | "
                  f"{o25(te):>13} | {te['1X2']['brier']:>12.4f} | {te['distribucion']['logloss']:>12.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
