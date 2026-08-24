#!/usr/bin/env python3
"""Historial largo de partidos con cuota de cierre real.

Por qué existe:

`medir_vs_mercado.py` ya bajaba `football-data.co.uk/new/ARG.csv` y
después filtraba a la temporada en curso: evaluaba **289 partidos** de
los **6310** que el archivo trae, de 2012 a 2026. El resto estaba ahí,
bajado y descartado.

Y el CSV es autosuficiente. Trae `Home`, `Away`, `HG`, `AG` y `Date`,
que es exactamente lo que `fuerzas_equipos()` necesita — o sea que se
pueden ajustar las fuerzas contra la propia historia del archivo, sin
cruzar nombres con ESPN. Ese cruce era lo que ataba la medición a una
sola temporada.

Además trae varias fuentes de cuota de cierre. Se prefiere Pinnacle
(`PSC*`), que es la vara que la industria usa para CLV: margen medio
3.18% contra 7.07% del promedio del mercado, medido sobre los 6310.

Ligas verificadas el 2026-08-24. Ojo con los códigos: `CHI.csv` es
China y `COL.csv`/`BOL.csv` son Polonia — se chequeó la columna
`Country`, no el nombre del archivo.

    python historico.py            # resumen de lo que hay
"""

import csv
import datetime
import io
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ / "data" / "cache_historico"

BASE = "https://www.football-data.co.uk/new/{}.csv"

# Solo las que se verificaron contra la columna Country del propio CSV.
LIGAS = {
    "arg": {"archivo": "ARG", "pais": "Argentina"},
    "bra": {"archivo": "BRA", "pais": "Brazil"},
}

# Fuentes de cuota de cierre, en orden de preferencia.
FUENTES = (("pinnacle", "PSC"), ("promedio", "AvgC"))


def _num(v):
    try:
        n = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    return n if n > 1.0 else None      # una cuota <= 1.00 es un dato roto


def cuotas_cierre(f):
    """([local, empate, visita], fuente) del cierre, o (None, None).

    Pinnacle primero porque es la referencia de la industria para CLV y
    la que menos margen tiene. Si una fuente viene incompleta o rota se
    prueba la siguiente: se descarta la fuente, nunca el partido.
    """
    for nombre, pref in FUENTES:
        c = [_num(f.get(pref + x)) for x in ("H", "D", "A")]
        if all(x is not None for x in c):
            return c, nombre
    return None, None


def desenlace(p):
    """Qué pasó, en el mismo orden que las cuotas: [local, empate, visita]."""
    gh, ga = p["gh"], p["ga"]
    return [int(gh > ga), int(gh == ga), int(gh < ga)]


def normalizar(filas):
    """Filas crudas del CSV al formato que ya entiende `fuerzas_equipos()`.

    Devuelve `{fecha, home, away, gh, ga, cuotas, fuente, liga,
    temporada}` ordenado del más viejo al más nuevo.

    El orden cronológico no es cosmético: todo lo que se mide con esto
    es walk-forward (ajustar con lo anterior, predecir lo siguiente). Si
    el orden viene mal se filtra futuro al pasado y la medición miente a
    nuestro favor sin avisar.

    Un partido sin cuota se conserva: no sirve para comparar contra el
    mercado, pero sí alimenta el ajuste de fuerzas, y tirarlo sería
    perder historia que ya está bajada.
    """
    out = []
    for f in filas or []:
        try:
            fecha = datetime.datetime.strptime(
                (f.get("Date") or "").strip(), "%d/%m/%Y").date()
            gh, ga = int(f["HG"]), int(f["AG"])
        except (ValueError, KeyError, TypeError):
            continue
        home = (f.get("Home") or "").strip()
        away = (f.get("Away") or "").strip()
        if not home or not away:
            continue
        c, fuente = cuotas_cierre(f)
        out.append({"fecha": fecha, "home": home, "away": away,
                    "gh": gh, "ga": ga, "cuotas": c, "fuente": fuente,
                    "liga": (f.get("League") or "").strip(),
                    "temporada": (f.get("Season") or "").strip()})
    out.sort(key=lambda p: p["fecha"])
    return out


def con_cuota(partidos):
    """Los que se pueden comparar contra el mercado."""
    return [p for p in partidos or [] if p.get("cuotas")]


def bajar(liga, refrescar=False):
    """Filas crudas del CSV, cacheadas en disco.

    Se cachea para no golpear el servidor en cada medición y para que
    los scripts corran sin red. El archivo es de dominio público y no
    cambia hacia atrás: solo se le agregan fechas nuevas.
    """
    if liga not in LIGAS:
        raise ValueError(f"liga desconocida: {liga}. Hay {sorted(LIGAS)}")
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / f"{LIGAS[liga]['archivo']}.csv"
    if refrescar or not destino.exists():
        url = BASE.format(LIGAS[liga]["archivo"])
        txt = urllib.request.urlopen(url, timeout=60).read().decode("utf-8-sig",
                                                                    "ignore")
        destino.write_text(txt, encoding="utf-8")
    txt = destino.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(io.StringIO(txt)))


def partidos(liga, refrescar=False):
    """Todo el historial de una liga, listo para medir."""
    return normalizar(bajar(liga, refrescar))


def main():
    print()
    for liga in sorted(LIGAS):
        try:
            ps = partidos(liga)
        except Exception as e:                       # noqa: BLE001
            print(f"{liga}: no se pudo bajar ({type(e).__name__})")
            continue
        cc = con_cuota(ps)
        pin = sum(1 for p in cc if p["fuente"] == "pinnacle")
        eq = {t for p in ps for t in (p["home"], p["away"])}
        print(f"{liga}: {len(ps)} partidos · {len(cc)} con cuota "
              f"({pin} de Pinnacle) · {len(eq)} equipos")
        if ps:
            print(f"     de {ps[0]['fecha']} a {ps[-1]['fecha']}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
