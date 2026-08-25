#!/usr/bin/env python3
"""Cruzar los nombres de equipo de football-data con los de ESPN.

Por qué existe:

`historico.py` baja 4180 partidos de Inglaterra y 3857 de Francia **con
estadísticas por partido** (remates, córners, faltas, tarjetas). Son
~246 partidos por equipo. El caché de ESPN que alimenta al modelo tiene
5 u 8. Esa diferencia es exactamente lo que separa "publicamos el
promedio de la liga" de "tenemos opinión propia por equipo" — el
hallazgo de TRASPASO.md §6vicies bis, que después se cobró en plata en
§6vicies quater.

Lo único que ataba las dos fuentes era el nombre del equipo, y no
coinciden: el CSV dice "Man City" y ESPN dice "Manchester City".

Qué hace, y qué NO hace:

Cruza **solo por igualdad exacta** después de normalizar (minúsculas,
sin acentos, sin puntuación), contra los tres nombres que ESPN publica
de cada equipo: `displayName`, `shortDisplayName` y `name`. Nada de
parecido, prefijos, ni distancia de edición.

Esa restricción no es pereza, es el punto. Medido el 2026-08-25, la
Ligue 1 tiene a **Paris Saint-Germain y Paris FC jugando la misma
temporada**. Cualquier cruce por prefijo o por parecido le pega la
historia de uno al otro, y el resultado no se ve como un error: se ve
como datos. Un nombre sin cruzar se nota; un nombre mal cruzado, no.

Por la misma razón **no se cruza por abreviatura**, aunque ESPN la
traiga: Brentford (eng) y Brest (fra) son los dos "BRE".

Cuánto resuelve ESPN solo, y cuánto hubo que escribir:

De los 15 equipos de eng.1 y fra.1 cuyo nombre de CSV no coincide con
el `displayName`, **12 se resuelven con el `shortDisplayName` que ESPN
ya publica** — "Wolves", "Man City", "Leeds", "Brighton", "Monaco",
"Rennes", "Auxerre" y compañía. Uno más ("Nott'm Forest") sale solo con
sacar el apóstrofo. Quedan **tres** que necesitan tabla escrita a mano,
y están en `ALIAS` con el motivo al lado.

Que la tabla sea de tres entradas y no de veinte es el resultado de
mirar la fuente antes de escribir: el impulso era transcribir a mano
los 15.

    python equipos.py              # cruce real de eng.1 y fra.1
"""

import json
import sys
import unicodedata
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

# Los nombres que ESPN publica de cada equipo y que SÍ se indexan.
# `abbreviation` queda afuera a propósito: es de tres letras y choca
# entre ligas (BRE es Brentford y también Brest).
CAMPOS = ("display", "short", "name")

# Los apóstrofos se borran en vez de separar palabras — ver `normalizar()`.
# Está el recto y el tipográfico porque las dos fuentes usan uno cada una.
APOSTROFOS = "'’ʼ`"

# Los únicos casos que ESPN no resuelve por su cuenta. Cada entrada es
# un nombre normalizado del CSV apuntando al `displayName` de ESPN —
# nunca a un id, para que la tabla no caduque cuando ESPN renumere.
#
# Verificados el 2026-08-25 contra /standings de eng.1 y fra.1.
ALIAS = {
    # ESPN lo acorta a "Spurs", que el CSV no usa nunca.
    "tottenham": "Tottenham Hotspur",
    # ESPN lo acorta a "PSG". Ojo: en la misma liga está Paris FC, que
    # es otro club — por eso esto es una entrada explícita y no un
    # cruce por prefijo.
    "paris sg": "Paris Saint-Germain",
    # ESPN le deja el "AC" hasta en el nombre corto; el CSV nunca.
    "le havre": "Le Havre AC",
}


def normalizar(nombre):
    """Un nombre a su forma comparable: minúsculas, sin acentos ni signos.

    Iguala "Nott'm Forest" con "Nottm Forest" y "Saint-Étienne" con
    "Saint Etienne", que es todo lo que hace falta. Lo que
    deliberadamente NO hace es acortar: si recortara a la primera
    palabra, "Paris SG" y "Paris FC" pasarían a ser el mismo equipo.

    El apóstrofo se borra en vez de separar, y el resto de los signos
    separan. No es un detalle: "Nott'm" es una contracción de
    "Nottingham", así que convertir el apóstrofo en espacio parte una
    palabra sola en dos ("nott m forest") y deja de cruzar con el
    "Nottm Forest" de ESPN. El guion y el ampersand sí unen palabras
    distintas y por eso sí separan.
    """
    if not nombre:
        return ""
    txt = unicodedata.normalize("NFD", str(nombre))
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    txt = "".join(c for c in txt if c not in APOSTROFOS)
    txt = "".join(c if c.isalnum() else " " for c in txt.lower())
    return " ".join(txt.split())


def _por_nombre(equipos):
    """{nombre normalizado: {ids que lo reclaman}}.

    Un mismo equipo puede aportar el mismo nombre por dos campos (cuando
    `displayName` y `name` coinciden); eso no es ambigüedad, por eso se
    junta en un conjunto de ids y no en una lista.
    """
    d = {}
    for e in equipos or []:
        tid = str((e or {}).get("id") or "").strip()
        if not tid:
            continue
        for campo in CAMPOS:
            n = normalizar(e.get(campo))
            if n:
                d.setdefault(n, set()).add(tid)
    return d


def ambiguos(equipos):
    """{nombre: [ids]} de los nombres que reclama más de un equipo.

    Existe para que la ambigüedad se pueda mirar, no solo evitar. Hoy
    está vacío en eng.1 y fra.1; el día que no lo esté, hay que
    enterarse.
    """
    return {n: sorted(ids) for n, ids in _por_nombre(equipos).items()
            if len(ids) > 1}


def indice(equipos):
    """{nombre normalizado: team_id}, dejando afuera los ambiguos.

    Si dos equipos reclaman el mismo nombre, ese nombre NO entra. La
    alternativa —quedarse con el último que pasó— es la que convierte
    un choque de nombres en una historia mezclada sin un solo aviso.
    """
    return {n: next(iter(ids)) for n, ids in _por_nombre(equipos).items()
            if len(ids) == 1}


def cruzar(nombre, idx):
    """El team_id de ESPN para un nombre del CSV, o None.

    None es una respuesta válida y frecuente: los CSV traen once
    temporadas, así que la mitad de los nombres son equipos que hoy no
    están en la liga. Lo que no es válido es devolver el id del club
    más parecido.

    El alias se consulta ANTES que el índice, y si el alias apunta a un
    equipo que no está, devuelve None en vez de caer al nombre crudo:
    una entrada explícita tiene que ganarle siempre a una coincidencia
    derivada, incluso para no encontrar nada.
    """
    n = normalizar(nombre)
    if not n:
        return None
    idx = idx or {}
    if n in ALIAS:
        return idx.get(normalizar(ALIAS[n]))
    return idx.get(n)


def reporte(nombres, idx):
    """Qué cruzó y qué no, contado.

    `historico.py` perdió 1521 partidos por un `except` que descartaba
    filas en silencio. Acá el que no cruza se devuelve por nombre, para
    que la diferencia entre "no hay datos" y "no supimos leerlos" sea
    visible sin salir a contar aparte.
    """
    mapa, sin, vistos = {}, [], set()
    for nombre in nombres or []:
        if nombre in vistos:
            continue
        vistos.add(nombre)
        tid = cruzar(nombre, idx)
        if tid:
            mapa[nombre] = tid
        else:
            sin.append(nombre)
    return {"cruzan": len(mapa), "sin_cruzar": sin, "mapa": mapa,
            "total": len(vistos)}


def equipos_espn(slug, season=None):
    """Los equipos de una liga, como los publica /standings de ESPN.

    Devuelve dicts con `id`, `display`, `short`, `name` y `abbr` — la
    forma que consumen `indice()` y `ambiguos()`.
    """
    url = f"https://site.api.espn.com/apis/v2/sports/soccer/{slug}/standings"
    if season:
        url += f"?season={season}"
    pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(pedido, timeout=60))
    out = []
    for grupo in (d.get("children") or [d]):
        for e in ((grupo.get("standings") or {}).get("entries") or []):
            t = e.get("team") or {}
            if t.get("id"):
                out.append({"id": str(t["id"]), "display": t.get("displayName"),
                            "short": t.get("shortDisplayName"),
                            "name": t.get("name"),
                            "abbr": t.get("abbreviation")})
    return out


def main():
    import historico

    print(__doc__)
    for liga, slug in (("eng", "eng.1"), ("fra", "fra.1")):
        eq = equipos_espn(slug)
        idx = indice(eq)
        amb = ambiguos(eq)
        nombres = []
        for p in historico.partidos(liga):
            nombres += [p["home"], p["away"]]
        rep = reporte(nombres, idx)
        print(f"\n== {liga} · {len(eq)} equipos en ESPN, "
              f"{rep['total']} nombres distintos en el CSV")
        print(f"   cruzan {rep['cruzan']}, quedan {len(rep['sin_cruzar'])} "
              f"sin cruzar")
        cubiertos = set(rep["mapa"].values())
        faltan = [e["display"] for e in eq if e["id"] not in cubiertos]
        print(f"   equipos de ESPN sin historia: {len(faltan)}"
              + (f" — {', '.join(faltan)}" if faltan else ""))
        if amb:
            print(f"   ! nombres ambiguos: {amb}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
