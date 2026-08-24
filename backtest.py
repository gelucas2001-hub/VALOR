#!/usr/bin/env python3
"""
VALOR — backtest de calibración
¿Cuando el modelo dice 60%, pasa el 60% de las veces?

Reconstruye, para cada partido ya jugado de la temporada, lo que VALOR
habría predicho usando SOLO los partidos anteriores a esa fecha (sin
mirar el futuro), y compara esas probabilidades contra lo que realmente
pasó.

Este script no mide ROI: mide calibración, que es la pregunta de
fondo — sin eso, cualquier EV que calcule la app es una hipótesis.

OJO, acá decía que el ROI era IMPOSIBLE de medir porque ESPN borra las
cuotas cuando el partido termina. Eso era cierto y dejó de serlo el
2026-08-24, cuando `historico.py` trajo 6310 partidos de arg.1 con
cuota de cierre real de Pinnacle. La frase quedó y nadie volvió a hacer
la pregunta: se pasaron tres semanas midiendo calibración y ninguna
midiendo plata. Cuando por fin se midió, el modelo daba -6.18% de ROI.

Si volvés a leer acá que algo "no se puede medir", chequeá la fecha de
la afirmación antes de creerle.

Correr a mano:  python backtest.py
No forma parte del pipeline diario (es lento y no cambia día a día).
"""

import json, sys, math, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import actualizar as A

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SALIDA = Path("data/backtest.json")
# Un partido necesita historia previa para que el modelo tenga algo que
# decir. Se saltean los primeros de la temporada.
MIN_PREVIOS_POR_EQUIPO = A.MIN_PARTIDOS_FUERZA


# ── modelo (puerto del que corre en index.html) ──────────────────
# OJO: esta matemática está duplicada — vive en JS dentro de index.html
# y acá en Python. Si se toca una hay que tocar la otra. Al final del
# backtest se imprime un caso de control para poder compararlo a mano
# contra la app y detectar que no se hayan desincronizado.

def pois(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)


def tau(i, j, lh, la, rho):
    if i == 0 and j == 0: return 1 - lh*la*rho
    if i == 0 and j == 1: return 1 + lh*rho
    if i == 1 and j == 0: return 1 + la*rho
    if i == 1 and j == 1: return 1 - rho
    return 1.0


def matriz(lh, la, rho, mx=9):
    m = [[pois(i, lh) * pois(j, la) * tau(i, j, lh, la, rho)
          for j in range(mx+1)] for i in range(mx+1)]
    tot = sum(sum(f) for f in m)
    return [[v/tot for v in f] for f in m]


def suma_si(m, cond):
    return sum(m[i][j] for i in range(len(m)) for j in range(len(m)) if cond(i, j))


def mercados(m):
    """Las probabilidades que la app deriva de la matriz. Solo los
    mercados con desenlace inequívoco desde el marcador final."""
    return {
        "1X2 local":      suma_si(m, lambda i, j: i > j),
        "1X2 empate":     suma_si(m, lambda i, j: i == j),
        "1X2 visitante":  suma_si(m, lambda i, j: i < j),
        "Más de 0.5":     suma_si(m, lambda i, j: i+j > 0.5),
        "Más de 1.5":     suma_si(m, lambda i, j: i+j > 1.5),
        "Más de 2.5":     suma_si(m, lambda i, j: i+j > 2.5),
        "Más de 3.5":     suma_si(m, lambda i, j: i+j > 3.5),
        "Ambos marcan":   suma_si(m, lambda i, j: i > 0 and j > 0),
    }


def desenlaces(gh, ga):
    """Qué pasó de verdad, en el mismo formato que mercados()."""
    return {
        "1X2 local":      1 if gh > ga else 0,
        "1X2 empate":     1 if gh == ga else 0,
        "1X2 visitante":  1 if gh < ga else 0,
        "Más de 0.5":     1 if gh+ga > 0.5 else 0,
        "Más de 1.5":     1 if gh+ga > 1.5 else 0,
        "Más de 2.5":     1 if gh+ga > 2.5 else 0,
        "Más de 3.5":     1 if gh+ga > 3.5 else 0,
        "Ambos marcan":   1 if gh > 0 and ga > 0 else 0,
    }


# ── métricas ─────────────────────────────────────────────────────

def brier(pred, real):
    return sum((p-y)**2 for p, y in zip(pred, real)) / len(pred)


def log_loss(pred, real, eps=1e-15):
    s = 0.0
    for p, y in zip(pred, real):
        p = min(max(p, eps), 1-eps)
        s += -(y*math.log(p) + (1-y)*math.log(1-p))
    return s / len(pred)


def calibracion(pred, real, bins=5):
    """Agrupa por franja de probabilidad y compara predicho vs real.
    Es la tabla que dice si un '70%' del modelo realmente pasa 70% de
    las veces."""
    out = []
    for b in range(bins):
        lo, hi = b/bins, (b+1)/bins
        idx = [k for k, p in enumerate(pred) if (p >= lo and p < hi) or (b == bins-1 and p == 1.0)]
        if not idx:
            continue
        out.append({
            "franja": f"{int(lo*100)}-{int(hi*100)}%",
            "n": len(idx),
            "predicho": round(sum(pred[k] for k in idx)/len(idx), 4),
            "real": round(sum(real[k] for k in idx)/len(idx), 4),
        })
    return out


def resultados_con_marcador(slug, season, hoy):
    """Como A.resultados_temporada pero conservando el marcador para
    poder evaluar los desenlaces."""
    return A.resultados_temporada(slug, season, hoy)


def correr(slug, nombre, rho, season, hoy):
    print(f"· {nombre} — trayendo temporada")
    todos = resultados_con_marcador(slug, season, hoy)
    if not todos:
        print("  sin datos")
        return None
    todos.sort(key=lambda p: p["fecha"])
    print(f"  {len(todos)} partidos jugados")

    # agrupar por fecha: los partidos del mismo día comparten el mismo
    # "pasado", así se recalculan las fuerzas una vez por fecha y no una
    # vez por partido
    fechas = sorted({p["fecha"] for p in todos})
    pred = {k: [] for k in mercados(matriz(1, 1, rho))}
    real = {k: [] for k in pred}
    # La línea base también tiene que jugar limpio: predice la frecuencia
    # observada SOLO en los partidos anteriores, no la de toda la
    # temporada. Con la frecuencia global estaría mirando el futuro y le
    # ganaría al modelo con ventaja tramposa.
    base_pred = {k: [] for k in pred}
    evaluados, salteados = 0, 0
    control = None

    for f in fechas:
        previos = [p for p in todos if p["fecha"] < f]
        if len(previos) < 10:
            salteados += sum(1 for p in todos if p["fecha"] == f)
            continue
        fuerzas, mu_l, mu_v, pj = A.fuerzas_equipos(previos, f)

        for p in [x for x in todos if x["fecha"] == f]:
            n_loc, n_vis = pj.get(p["home"], 0), pj.get(p["away"], 0)
            if n_loc < MIN_PREVIOS_POR_EQUIPO or n_vis < MIN_PREVIOS_POR_EQUIPO:
                salteados += 1
                continue
            a_loc, d_loc = fuerzas.get(p["home"], (1.0, 1.0))
            a_vis, d_vis = fuerzas.get(p["away"], (1.0, 1.0))
            lh = round(max(0.35, min(3.20, mu_l * a_loc * d_vis)), 3)
            la = round(max(0.30, min(3.00, mu_v * a_vis * d_loc)), 3)

            probs = mercados(matriz(lh, la, rho))
            reales = desenlaces(p["gh"], p["ga"])
            # frecuencia base con los partidos previos nomás (0.5 si aún
            # no hay historia, que es no saber nada)
            previos_des = [desenlaces(q["gh"], q["ga"]) for q in previos]
            for k in probs:
                pred[k].append(probs[k])
                real[k].append(reales[k])
                base_pred[k].append(sum(d[k] for d in previos_des)/len(previos_des)
                                    if previos_des else 0.5)
            evaluados += 1
            if control is None:
                control = {"fecha": str(f), "lh": lh, "la": la, "rho": rho,
                           "prob_local": round(probs["1X2 local"], 4),
                           "prob_over25": round(probs["Más de 2.5"], 4)}

    if evaluados == 0:
        print("  sin partidos evaluables")
        return None
    print(f"  evaluados {evaluados} · salteados {salteados} (poca historia previa)")

    # línea de base honesta: en cada partido, la frecuencia observada
    # hasta ese momento. Si el modelo no le gana a esto, no está
    # aportando nada por encima de "mirá cuántas veces pasó antes".
    res = {"competicion": nombre, "n": evaluados, "control": control, "mercados": {}}
    for k in pred:
        res["mercados"][k] = {
            "n": len(pred[k]),
            "brier_modelo": round(brier(pred[k], real[k]), 5),
            "brier_base":   round(brier(base_pred[k], real[k]), 5),
            "logloss_modelo": round(log_loss(pred[k], real[k]), 5),
            "logloss_base":   round(log_loss(base_pred[k], real[k]), 5),
            "frecuencia_real": round(sum(real[k])/len(real[k]), 4),
            "prob_media_modelo": round(sum(pred[k])/len(pred[k]), 4),
            "calibracion": calibracion(pred[k], real[k]),
        }
    return res


def main():
    hoy = datetime.date.today()
    season = hoy.year
    salida = {"generado": datetime.datetime.now().isoformat(timespec="minutes"),
              "nota": ("Solo calibración de probabilidades. No hay ROI ni CLV: "
                       "ESPN no conserva las cuotas de partidos ya jugados."),
              "competiciones": []}

    for slug in A.CON_FUERZAS:
        meta = A.COMPETICIONES[slug]
        r = correr(slug, meta["nombre"], meta["rho"], season, hoy)
        if r:
            salida["competiciones"].append(r)

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── informe ──
    for c in salida["competiciones"]:
        print()
        print("=" * 66)
        print(f"{c['competicion']} — {c['n']} partidos evaluados")
        print("=" * 66)
        print(f"{'mercado':<16}{'Brier':>9}{'base':>9}{'  ':>2}{'gana?':<7}{'modelo':>8}{'real':>8}")
        for k, v in c["mercados"].items():
            mejor = "sí" if v["brier_modelo"] < v["brier_base"] else "NO"
            print(f"{k:<16}{v['brier_modelo']:>9.4f}{v['brier_base']:>9.4f}  {mejor:<7}"
                  f"{v['prob_media_modelo']:>8.3f}{v['frecuencia_real']:>8.3f}")
        print()
        print("calibración de 'Más de 2.5' (predicho vs real por franja):")
        for f in c["mercados"]["Más de 2.5"]["calibracion"]:
            print(f"  {f['franja']:<10} n={f['n']:<5} predicho {f['predicho']:.3f}   real {f['real']:.3f}")

    print()
    print(f"✓ guardado en {SALIDA}")
    print("  'gana?' = el modelo tiene mejor Brier que predecir siempre la media histórica.")
    print("  Si dice NO, en ese mercado el modelo no está aportando sobre la frecuencia base.")


if __name__ == "__main__":
    main()
