#!/usr/bin/env python3
"""Prueba de The Odds API: ¿conviene cambiar DraftKings por Pinnacle?

Por qué existe:

La app marca valor comparando el modelo contra la cuota de DraftKings,
que es la única casa que expone ESPN — verificado el 2026-08-25: el
endpoint core de odds devuelve `count: 1`. DraftKings tiene 7.7% de
margen y ni siquiera opera en Argentina.

Buchdahl, en "Using the Wisdom of the Crowd" (gratis en
football-data.co.uk), concluye que **Pinnacle es el único libro cuyas
cuotas reflejan probabilidad real**; las de los demás reflejan
marketing. Ya usamos su cuota de cierre para toda la medición
histórica, pero para marcar valor en vivo usamos la casa blanda.

Esto NO toca el pipeline ni escribe nada en data/. Pide una fecha,
compara las dos fuentes, y dice si la diferencia justifica el cambio.

    # clave gratis en https://the-odds-api.com  (500 créditos/mes)
    export ODDS_API_KEY=...          # o `set` en Windows
    python probar_odds_api.py

Costo: 1 crédito por competición. Esta prueba gasta 2.
"""

import json
import os
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import medir_clv as C

BASE = ("https://api.the-odds-api.com/v4/sports/{sport}/odds"
        "?apiKey={key}&regions=eu&markets=h2h&oddsFormat=decimal")

# Verificado el 2026-08-25 contra su listado público de deportes.
DEPORTES = {
    "soccer_argentina_primera_division": "Liga Profesional Argentina",
    "soccer_brazil_campeonato": "Brasileirão Série A",
}

PARTIDOS = Path("data/partidos.json")


def pedir(sport, key):
    """(eventos, créditos_restantes, créditos_usados)."""
    req = urllib.request.Request(BASE.format(sport=sport, key=key),
                                 headers={"User-Agent": "VALOR/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return (json.loads(r.read()),
                r.headers.get("x-requests-remaining"),
                r.headers.get("x-requests-used"))


def margen(cuotas):
    return sum(1.0 / c for c in cuotas) - 1.0


def tri_de(ev, casa):
    """[local, empate, visitante] de una casa puntual, o None."""
    for bk in ev.get("bookmakers") or []:
        if bk.get("key") != casa:
            continue
        for mk in bk.get("markets") or []:
            if mk.get("key") != "h2h":
                continue
            pr = {o.get("name"): o.get("price") for o in mk.get("outcomes") or []}
            tri = [pr.get(ev.get("home_team")), pr.get("Draw"),
                   pr.get(ev.get("away_team"))]
            if all(isinstance(x, (int, float)) and x > 1 for x in tri):
                return tri
    return None


def clave(nombre):
    """Normaliza para cruzar nombres entre ESPN y The Odds API.

    Los dos escriben distinto ("Athletico-PR" vs "Athletico Paranaense",
    acentos, paréntesis). Esto empareja lo que se puede; lo que no cruza
    se reporta en vez de descartarse en silencio.
    """
    s = unicodedata.normalize("NFKD", (nombre or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    for ch in "().-":
        s = s.replace(ch, " ")
    return " ".join(s.split())


def nuestros():
    if not PARTIDOS.exists():
        return {}
    d = json.loads(PARTIDOS.read_text(encoding="utf-8"))
    out = {}
    for m in d.get("partidos") or []:
        mk = m.get("mercado") or {}
        if mk.get("local"):
            out[(clave(m.get("home")), clave(m.get("away")))] = m
    return out


def main():
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        print(__doc__)
        print("  FALTA LA CLAVE. Es gratis: https://the-odds-api.com\n")
        return 1

    mios = nuestros()
    print(f"\n  partidos con cuota de DraftKings que ya tenemos: {len(mios)}")

    eventos, casas, quedan = [], {}, None
    for sport, nombre in DEPORTES.items():
        try:
            evs, quedan, usados = pedir(sport, key)
        except urllib.error.HTTPError as e:
            cuerpo = e.read()[:200].decode("utf-8", "ignore")
            print(f"\n  {nombre}: HTTP {e.code} — {cuerpo}")
            continue
        except Exception as e:
            print(f"\n  {nombre}: {type(e).__name__}: {e}")
            continue
        eventos += evs
        print(f"  {nombre}: {len(evs)} partidos   "
              f"(usados {usados}, quedan {quedan})")
        for ev in evs:
            for bk in ev.get("bookmakers") or []:
                casas[bk.get("key")] = casas.get(bk.get("key"), 0) + 1

    if not eventos:
        print("\n  No vino ningún partido — puede no haber fecha próxima.\n")
        return 0

    print(f"\n  casas en la región 'eu' ({len(casas)} distintas):")
    for k, n in sorted(casas.items(), key=lambda kv: -kv[1])[:20]:
        print(f"    {k:26} en {n} partidos"
              f"{'   <- la que nos importa' if k == 'pinnacle' else ''}")

    if "pinnacle" not in casas:
        print("\n  Pinnacle NO vino. Sin eso el cambio no tiene sentido.\n")
        return 0

    print(f"\n  {'partido':40}{'marg DK':>9}{'marg Pin':>10}{'dif prob':>10}")
    print("  " + "-" * 69)
    difs, m_dk, m_pin, sin_cruce = [], [], [], 0
    for ev in eventos:
        pin = tri_de(ev, "pinnacle")
        if not pin:
            continue
        mio = mios.get((clave(ev.get("home_team")), clave(ev.get("away_team"))))
        if not mio:
            sin_cruce += 1
            continue
        mk = mio["mercado"]
        dk = [mk["local"], mk["empate"], mk["visitante"]]
        p_dk, p_pin = C.devig_shin(dk), C.devig_shin(pin)
        if not p_dk or not p_pin:
            continue
        d = max(abs(a - b) for a, b in zip(p_dk, p_pin))
        difs.append(d)
        m_dk.append(margen(dk))
        m_pin.append(margen(pin))
        nombre = f"{mio.get('home','?')[:18]} v {mio.get('away','?')[:18]}"
        print(f"  {nombre[:40]:40}{margen(dk)*100:8.2f}%{margen(pin)*100:9.2f}%"
              f"{d*100:9.2f}pp")

    if not difs:
        print("\n  Ningún partido cruzó entre las dos fuentes.")
        print(f"  ({sin_cruce} de The Odds API no encontraron par en partidos.json)\n")
        return 0

    n = len(difs)
    print("  " + "-" * 69)
    print(f"  {n} partidos cruzados" + (f" · {sin_cruce} sin par" if sin_cruce else ""))
    print(f"\n  margen medio DraftKings : {sum(m_dk)/n*100:.2f}%")
    print(f"  margen medio Pinnacle   : {sum(m_pin)/n*100:.2f}%")
    print(f"  la referencia mejora en  {(sum(m_dk)-sum(m_pin))/n*100:.2f} puntos de margen")
    print(f"\n  cuánto se mueve la probabilidad de mercado al cambiar de casa:")
    print(f"    media {sum(difs)/n*100:.2f} pp · máxima {max(difs)*100:.2f} pp")
    print(f"\n  El umbral de la marca dorada es 6.00 pp. Si esto se le acerca,")
    print(f"  cambiar de referencia mueve qué partidos quedan marcados.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
