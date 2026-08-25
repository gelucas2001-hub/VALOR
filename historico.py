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

# Las ligas clasicas de Europa viven en otra carpeta y en un archivo por
# temporada, con otros nombres de columna. Ver `normalizar()` y `bajar()`.
BASE_TEMPORADA = "https://www.football-data.co.uk/mmz4281/{temporada}/{codigo}.csv"

# Cuantas temporadas bajar de una liga clasica. Cinco es lo que la app
# le da al modelo (`actualizar.TEMPORADAS_HISTORIA`), pero aca se baja
# mas porque el archivo es de dominio publico, no cambia hacia atras y
# cuesta un pedido por temporada: la medicion walk-forward necesita
# historia ANTES del primer partido que evalua.
TEMPORADAS = 11

# Solo las que se verificaron contra la columna Country del propio CSV.
#
# `formato` dice de donde sale el archivo:
#   "unico"      — un CSV con toda la historia, en /new/. Columnas
#                  Home/Away/HG/AG. Sin estadisticas de partido.
#   "temporadas" — un CSV por temporada, en /mmz4281/. Columnas
#                  HomeTeam/AwayTeam/FTHG/FTAG, y CON estadisticas
#                  (remates, al arco, corners, faltas, tarjetas).
#
# Esa diferencia no es un detalle de parseo. Medido el 2026-08-25:
# ARG.csv y BRA.csv no traen ni una columna de estadisticas en 11.855
# partidos; E0 y F1 las traen todas. Es la razon por la que en Argentina
# el modelo publica el promedio de la liga para corners (4.70 a 4.96
# entre 68 equipos) y en Inglaterra no tendria por que.
LIGAS = {
    "arg": {"archivo": "ARG", "pais": "Argentina", "formato": "unico"},
    "bra": {"archivo": "BRA", "pais": "Brazil", "formato": "unico"},
    # Agregadas el 2026-08-25. Se eligieron midiendo tres cosas a la vez
    # (ver TRASPASO.md): atraso del modelo contra el cierre, profundidad
    # del mercado de props en ESPN/DraftKings, y si con la historia que
    # hay en disco se distinguen los equipos.
    #
    #            atraso (de 26)   jugadores/partido   k corners
    #   eng.1    0.0137  (6o)          41              14.2
    #   fra.1    0.0147  (9o)          27              23.0
    #   arg.1    0.0147  (11o)          0             tope (200)
    "eng": {"archivo": "E0", "pais": "England", "formato": "temporadas"},
    "fra": {"archivo": "F1", "pais": "France", "formato": "temporadas"},
}


# Nombres de columna de cada formato: (equipo local, visitante, goles L, goles V).
_COLUMNAS = (("Home", "Away", "HG", "AG"),            # /new/
             ("HomeTeam", "AwayTeam", "FTHG", "FTAG"))  # /mmz4281/

# Estadisticas del partido, cuando el CSV las trae. La clave es como las
# nombra el resto del repo (`cache_disciplina.json`, `medir_lineas.py`);
# el valor, como las nombra football-data.
_EST = {"remates": ("HS", "AS"), "al_arco": ("HST", "AST"),
        "corners": ("HC", "AC"), "faltas": ("HF", "AF"),
        "tarjetas": ("HY", "AY")}


def temporadas_de(cuantas, hasta=None):
    """Las ultimas `cuantas` temporadas, como las nombra football-data.

    La temporada 2025/26 es "2526". Se corta en la que ya empezo: pedir
    una del futuro devuelve un 404 y ensucia la salida sin aportar nada.
    """
    if hasta is None:
        hoy = datetime.date.today()
        # La temporada europea arranca en agosto: antes de julio, la
        # ultima empezada es la del ano anterior.
        hasta = hoy.year if hoy.month >= 7 else hoy.year - 1
    out = []
    for i in range(cuantas):
        a = hasta - 1 - i
        out.append(f"{a % 100:02d}{(a + 1) % 100:02d}")
    return sorted(out)


def estadisticas_fila(f):
    """Las estadisticas del partido, o None si el CSV no las trae.

    Devuelve None y no un dict vacio a proposito: "no hay dato" y "hay
    dato y vale cero" son cosas distintas, y confundirlas es lo que hace
    que un promedio se hunda sin que nadie lo note.
    """
    out = {}
    for met, (ch, ca) in _EST.items():
        try:
            out[met] = {"h": float(f[ch]), "a": float(f[ca])}
        except (TypeError, ValueError, KeyError):
            continue
    return out or None

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


def _fecha(txt):
    """La fecha del CSV, o None si no se entiende.

    Dos formatos, y football-data alterna entre ellos POR TEMPORADA sin
    documentarlo: E0-1617, F1-1516, F1-1617 y F1-1718 traen el ano en
    dos digitos y el resto en cuatro. Soportar solo uno costaba 380
    partidos de Inglaterra y 1141 de Francia, descartados sin un aviso.
    """
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(txt, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


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
        fecha = _fecha((f.get("Date") or "").strip())
        if fecha is None:
            continue
        # Los dos formatos de football-data nombran distinto lo mismo. Se
        # prueba uno y despues el otro en vez de mirar un campo "formato",
        # porque `normalizar()` recibe filas sueltas y no sabe de que
        # archivo salieron.
        home = away = None
        for ch, ca, cgh, cga in _COLUMNAS:
            try:
                gh, ga = int(f[cgh]), int(f[cga])
            except (ValueError, KeyError, TypeError):
                continue
            home = (f.get(ch) or "").strip()
            away = (f.get(ca) or "").strip()
            if home and away:
                break
            home = away = None
        if not home or not away:
            continue
        c, fuente = cuotas_cierre(f)
        p = {"fecha": fecha, "home": home, "away": away,
             "gh": gh, "ga": ga, "cuotas": c, "fuente": fuente,
             "liga": (f.get("League") or f.get("Div") or "").strip(),
             "temporada": (f.get("Season") or "").strip()}
        est = estadisticas_fila(f)
        if est:
            p["est"] = est
        out.append(p)
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
    meta = LIGAS[liga]
    codigo = meta["archivo"]

    def leer(destino, url):
        if refrescar or not destino.exists():
            txt = urllib.request.urlopen(url, timeout=60).read().decode(
                "utf-8-sig", "ignore")
            destino.write_text(txt, encoding="utf-8")
        return list(csv.DictReader(
            io.StringIO(destino.read_text(encoding="utf-8-sig"))))

    if meta.get("formato") != "temporadas":
        return leer(CACHE / f"{codigo}.csv", BASE.format(codigo))

    # Una liga clasica son N archivos, uno por temporada. Se juntan en
    # orden y `normalizar()` los ordena por fecha igual, asi que un
    # archivo faltante no descoloca al resto: se pierde esa temporada,
    # no la liga. Que una temporada vieja no exista es normal (el
    # ascenso/descenso cambia la division), y frenar todo por eso seria
    # cambiar una liga entera por un 404.
    filas = []
    for t in temporadas_de(TEMPORADAS):
        destino = CACHE / f"{codigo}-{t}.csv"
        try:
            filas += leer(destino, BASE_TEMPORADA.format(temporada=t,
                                                         codigo=codigo))
        except Exception as e:                       # noqa: BLE001
            print(f"  ! {liga} {t}: {type(e).__name__}", file=sys.stderr)
    return filas


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
