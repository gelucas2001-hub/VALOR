#!/usr/bin/env python3
"""El modelo contra el mercado, sobre TODO el historial disponible.

Por qué existe:

`medir_vs_mercado.py` evaluaba 289 partidos — la temporada en curso —
porque dependía de cruzar nombres del CSV con equipos de ESPN, y ESPN
solo devuelve la temporada actual. Pero el CSV es autosuficiente
(`historico.py`), así que se puede ajustar contra su propia historia y
evaluar **6310 partidos de arg.1 y 5544 de bra.1**, de 2012 a hoy.

Eso es lo que destraba medir en serio `rho`, `VIDA_MEDIA_DIAS`,
`PRIOR_FUERZA` y la calibración antes de publicar: todos estaban
parados por falta de muestra.

Cómo se mide:

Walk-forward estricto. Para cada partido se ajustan las fuerzas usando
**solo lo anterior** — y ni siquiera lo del mismo día, porque cuando se
predice una fecha esa fecha todavía no se jugó. Una fuga de futuro no
se ve como un error: se ve como un modelo buenísimo. Por eso el corte
está testeado aparte.

Contra qué se compara:

- **el mercado**, con el cierre de Pinnacle cuando está (margen 3.18%
  contra 7.07% del promedio) y devig de Shin;
- **la tasa base**, o sea la frecuencia histórica de local/empate/visita
  hasta ese momento. Comparar contra "siempre 33%" es una vara falsa:
  el local gana bastante más que un tercio, y un modelo que solo
  aprendiera eso ya parecería listo.

    python medir_historico.py            # arg
    python medir_historico.py bra
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import actualizar as A
import backtest
import historico as H
import medir_clv

RAIZ = Path(__file__).resolve().parent

# Cuánta historia hace falta antes de empezar a evaluar.
MIN_PREVIOS = 40

# Ventana de historia para ajustar. Tiene que ser la MISMA que usa la
# app, no la que sea cómoda: `actualizar.get_historia()` le pasa a
# `fuerzas_equipos()` las últimas TEMPORADAS_HISTORIA (=5) temporadas.
# Cinco años calendario son 1825 días, y de ahí sale este número — no de
# un barrido. Que la medición coincida con producción no es un óptimo
# que se elige, es una condición para que lo medido sea el modelo que se
# publica. Hay un test que lo ata a TEMPORADAS_HISTORIA.
#
# Hasta el 2026-08-25 esto valía 365, con un comentario que lo defendía
# así: "con VIDA_MEDIA_DIAS = 45, un partido de hace un año pesa 0.0036
# y uno de hace dos, 0.0000". Era cierto con vida 45. Con vida 300 ese
# partido pesa 0.43 y el de hace dos años 0.185: el corte estaba tirando
# a la basura peso real. El comentario sobrevivió a su propio dato,
# igual que el de `rho` un día antes.
#
# Cuánto costaba el error, medido el 2026-08-25 sobre 2583 partidos de
# arg fuera de muestra — atraso del modelo contra el cierre de Pinnacle:
#
#     ventana    365    730    900   1100   1460   1825
#     arg      .0159  .0122  .0115  .0112  .0110  .0109
#     bra      .0229  .0165  .0162  .0155  .0151  .0148
#
# O sea que un tercio del "atraso contra el mercado" que veníamos
# reportando no era del modelo: era de la medición, que lo evaluaba con
# un año de historia mientras el publicado tenía cinco. La curva además
# está bien aplanada al final, así que 1825 no es un borde de grilla:
# los partidos de hace cinco años pesan 0.015 y ya no mueven nada.
#
# Cuesta: la pasada completa pasa de ~1.5 min a ~8 min por liga.
VENTANA = 1825


def ventana_previa(partidos, i, dias=VENTANA):
    """Los partidos que se pueden usar para predecir `partidos[i]`.

    Estrictamente anteriores en FECHA, no en posición: dos partidos del
    mismo día no se ven entre sí, porque cuando se predice una fecha esa
    fecha entera todavía no se jugó. Usar el primero para predecir el
    segundo sería fuga de futuro, y una fuga se ve como un modelo
    buenísimo en vez de como un error.
    """
    if not partidos or i <= 0:
        return []
    hoy = partidos[i]["fecha"]
    return [p for p in partidos[:i]
            if p["fecha"] < hoy and (hoy - p["fecha"]).days <= dias]


def tasa_base(previos):
    """Frecuencia histórica de [local, empate, visita].

    Es la vara honesta: comparar contra "siempre un tercio" regala
    dificultad, porque el local gana bastante más que eso y aprender
    solo la localía ya alcanzaría para parecer listo.
    """
    if not previos:
        return [1 / 3, 1 / 3, 1 / 3]
    n = len(previos)
    c = [0, 0, 0]
    for p in previos:
        c[H.desenlace(p).index(1)] += 1
    return [x / n for x in c]


def brier(p, real):
    """Suma de cuadrados. 0 es perfecto; el tercio parejo da 2/3."""
    return sum((p[i] - real[i]) ** 2 for i in range(3))


def _probs_modelo(previos, hoy, home, away, rho):
    """1X2 del modelo ajustado solo con `previos`."""
    fuerzas, mu_l, mu_v, _pj = A.fuerzas_equipos(previos, hoy)
    a_l, d_l = fuerzas.get(home, (1.0, 1.0))
    a_v, d_v = fuerzas.get(away, (1.0, 1.0))
    lh = max(0.35, min(3.20, mu_l * a_l * d_v))
    la = max(0.30, min(3.00, mu_v * a_v * d_l))
    m = backtest.matriz(lh, la, rho)
    return [backtest.suma_si(m, lambda i, j: i > j),
            backtest.suma_si(m, lambda i, j: i == j),
            backtest.suma_si(m, lambda i, j: i < j)], lh, la


def evaluar(partidos, min_previos=MIN_PREVIOS, ventana=VENTANA, rho=0.05,
            progreso=None):
    """Una fila por partido evaluado: modelo, mercado, tasa base y qué pasó.

    Los partidos sin cuota igual alimentan el ajuste — están en la
    historia — pero no se evalúan, porque no hay contra qué compararlos.
    """
    filas = []
    cache = {}
    for i, p in enumerate(partidos or []):
        if i < min_previos or not p.get("cuotas"):
            continue
        prev = ventana_previa(partidos, i, ventana)
        if len(prev) < min_previos:
            continue
        clave = p["fecha"]
        if clave not in cache:
            cache[clave] = prev
        pm, lh, la = _probs_modelo(prev, p["fecha"], p["home"], p["away"], rho)
        pq = medir_clv.devig_shin(p["cuotas"])
        if pq is None:
            continue
        filas.append({"fecha": p["fecha"], "modelo": pm, "mercado": pq,
                      "base": tasa_base(prev), "real": H.desenlace(p),
                      "lh": lh, "la": la, "fuente": p.get("fuente"),
                      # Para poder cortar despues por torneo, por equipo o
                      # por cuanta historia tenia cada uno.
                      "liga": p.get("liga"), "temporada": p.get("temporada"),
                      "home": p["home"], "away": p["away"],
                      "n_previos": len(prev)})
        if progreso and len(filas) % progreso == 0:
            print(f"    {len(filas)} evaluados...", flush=True)
    return filas


def _resumen(filas, etiqueta):
    n = len(filas)
    br = {k: sum(brier(f[k], f["real"]) for f in filas) / n
          for k in ("modelo", "mercado", "base")}
    print(f"\n  {etiqueta}: {n} partidos evaluados\n")
    print(f"  {'quién':22} {'Brier':>9}")
    print(f"  {'la tasa base':22} {br['base']:9.5f}")
    print(f"  {'nuestro modelo':22} {br['modelo']:9.5f}")
    print(f"  {'el mercado (cierre)':22} {br['mercado']:9.5f}")

    gap_mkt = br["base"] - br["mercado"]
    gap_mod = br["base"] - br["modelo"]
    print(f"\n  El mercado mejora {gap_mkt:.5f} sobre la tasa base.")
    if gap_mkt > 0:
        print(f"  Nosotros mejoramos {gap_mod:.5f}, o sea el "
              f"{gap_mod / gap_mkt * 100:.0f}% de eso.")
    if gap_mod <= 0:
        print("  ⚠ El modelo NO le gana a la frecuencia histórica.")
    return br


def _bandas(filas):
    """Calibración: cuando decimos 70%, ¿pasa el 70%?"""
    print(f"\n  {'banda':10} {'n':>6} {'decimos':>9} {'pasa':>8} {'desvío':>8}")
    for lo in range(0, 100, 10):
        hi = lo + 10
        ps, rs = [], []
        for f in filas:
            for i in range(3):
                if lo <= f["modelo"][i] * 100 < hi:
                    ps.append(f["modelo"][i])
                    rs.append(f["real"][i])
        if len(ps) < 20:
            continue
        dec, real = sum(ps) / len(ps), sum(rs) / len(rs)
        marca = "  ←" if abs(dec - real) > 0.05 else ""
        print(f"  {lo:3d}-{hi:3d}% {len(ps):6d} {dec*100:8.1f}% "
              f"{real*100:7.1f}% {(dec-real)*100:+7.1f}{marca}")


def main(argv):
    liga = (argv[1] if len(argv) > 1 else "arg").lower()
    if liga not in H.LIGAS:
        raise SystemExit(f"liga desconocida: {liga}. Hay {sorted(H.LIGAS)}")
    print("\n" + "=" * 68)
    print(f"  EL MODELO CONTRA EL MERCADO — historial completo de {liga}")
    print("=" * 68)
    ps = H.partidos(liga)
    cc = H.con_cuota(ps)
    pin = sum(1 for p in cc if p["fuente"] == "pinnacle")
    print(f"\n  {len(ps)} partidos en el CSV · {len(cc)} con cuota de cierre")
    print(f"  ({pin} de Pinnacle, el resto promedio del mercado)")
    print(f"  de {ps[0]['fecha']} a {ps[-1]['fecha']}")
    print("\n  ajustando walk-forward (esto tarda un rato)...")

    filas = evaluar(ps, progreso=1000)
    if not filas:
        raise SystemExit("no se evaluó ningún partido")
    _resumen(filas, liga)
    _bandas(filas)
    print("\n  " + "-" * 64)
    print("  La vara es la tasa base, no 'siempre un tercio': el local gana")
    print("  bastante más que eso, y un modelo que solo aprendiera la")
    print("  localía ya parecería listo contra la vara falsa.")
    print("  " + "-" * 64 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
