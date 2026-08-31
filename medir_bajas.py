#!/usr/bin/env python3
"""¿Faltar goleadores predice marcar menos? La hipótesis del análisis.

Por qué existe:

Conectar la skill de análisis a λ (que hoy solo emite un veto de 1 bit)
descansa en una hipótesis que nunca se probó: que las bajas mueven los
goles de forma detectable. Antes de construir esa maquinaria conviene
saber si la hipótesis se sostiene.

Y **sí se puede medir hacia atrás**, contra lo que se venía diciendo. El
research web de la skill no es backtesteable —sobre un partido viejo la
web ya sabe el resultado— pero la parte que importa no necesita
research: `cache_disciplina.json` guarda QUIÉN JUGÓ cada partido
(`_jugadores`), y `planteles.json` tiene el plantel completo con
`peso_goles`. La diferencia entre los dos es quién faltó, sin tocar la
web.

Medido el 2026-08-30 sobre 205 observaciones (equipo-partido):

    peso ausente      n   goles   vs su media
     poco (<15%)    120    1.45      +0.06
   medio (15-30%)    39    0.97      -0.03
    alto (30-50%)    30    1.00      -0.19
  muy alto (>50%)    16    1.25      -0.00

    r = -0.0603 +- 0.1401  (0.9 errores estándar)

**No hay señal.** La dirección es la esperada pero no se despega del
ruido, y el tramo de más ausencias rompe el patrón — lo que apunta a
azar y no a un efecto chico.

Cuatro explicaciones, y la última es la que más pesa para el producto:

1. 205 observaciones es poco.
2. `peso_goles` es acumulado de temporada: un mal proxy de qué tan
   importante es un jugador HOY.
3. Los equipos compensan — entra el suplente, cambia el esquema.
4. **El mercado ya lo sabe.** Si la baja está en el precio antes de que
   nosotros la veamos, no hay ventaja aunque el efecto sea real. Es la
   misma razón por la que el CLV da cero.

El cron sigue acumulando alineaciones con cada fecha. Volver a correrlo
cuando haya el doble de muestra: si con 400 observaciones sigue en 0.9
errores estándar, la hipótesis está muerta y conviene decirlo.

    python medir_bajas.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATOS = Path(__file__).resolve().parent / "data"


def _leer(nombre):
    return json.load(open(DATOS / nombre, encoding="utf-8"))


pl = _leer("planteles.json")["equipos"]
cache = _leer("cache_disciplina.json")
res = _leer("resultados.json")

# peso_goles total del plantel, y por jugador
peso = {eq: {j["id"]: j.get("peso_goles") or 0.0 for j in js} for eq, js in pl.items()}

obs = []
for mid, v in cache.items():
    if not isinstance(v, dict) or not v.get("_jugadores"):
        continue
    marcador = res.get(mid) or res.get("espn" + mid)
    if not marcador:
        continue
    try:
        gh, ga = map(int, str(marcador).split("-"))
    except Exception:
        continue
    jugaron = set(v["_jugadores"])
    equipos = [k for k in v if not k.startswith("_")]
    if len(equipos) != 2:
        continue
    for idx, eq in enumerate(equipos):
        if eq not in peso:
            continue
        total = sum(peso[eq].values())
        if total <= 0:
            continue
        ausente = sum(w for jid, w in peso[eq].items() if jid not in jugaron)
        obs.append({"eq": eq, "frac_ausente": ausente / total,
                    "goles": gh if idx == 0 else ga})

print(f"\n  {len(obs)} observaciones (equipo-partido) con alineación y resultado\n")
if len(obs) < 40:
    print("  muestra insuficiente"); sys.exit()

# Promedio de goles del equipo, para comparar contra su propio nivel
por_eq = defaultdict(list)
for o in obs:
    por_eq[o["eq"]].append(o["goles"])
media_eq = {e: sum(g)/len(g) for e, g in por_eq.items()}

print(f"  {'peso ausente':>16} {'n':>5} {'goles':>7} {'vs su media':>12}")
print("  " + "-"*46)
for lo, hi, et in [(0,.15,"poco (<15%)"),(.15,.30,"medio (15-30%)"),(.30,.50,"alto (30-50%)"),(.50,1.01,"muy alto (>50%)")]:
    sel = [o for o in obs if lo <= o["frac_ausente"] < hi]
    if len(sel) < 15: continue
    g = sum(o["goles"] for o in sel)/len(sel)
    d = sum(o["goles"] - media_eq[o["eq"]] for o in sel)/len(sel)
    print(f"  {et:>16} {len(sel):5d} {g:7.2f} {d:+12.2f}")

# Correlación entre peso ausente y desvío contra la media propia
xs = [o["frac_ausente"] for o in obs]
ys = [o["goles"] - media_eq[o["eq"]] for o in obs]
n = len(xs); mx = sum(xs)/n; my = sum(ys)/n
sxy = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
sxx = sum((x-mx)**2 for x in xs); syy = sum((y-my)**2 for y in ys)
r = sxy/((sxx*syy)**.5) if sxx and syy else 0
se_r = ((1-r*r)/(n-2))**.5
print(f"\n  correlación peso ausente vs goles bajo su media: r = {r:+.4f} ± {2*se_r:.4f}")
print(f"  ({abs(r/se_r):.1f} errores estándar de cero)")
print("\n  Negativo = faltar goleadores predice marcar menos. Es lo que")
print("  haría falta para que conectar las bajas a λ tenga sentido.\n")
