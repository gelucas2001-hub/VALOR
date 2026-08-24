#!/usr/bin/env python3
"""Cuanto pesa el arbitro en las tarjetas (y en las faltas y los corners).

Por que existe:

Se midio sobre 177 partidos que las tarjetas NO dependen de como va el
partido. Correlacion con los goles totales: -0.05. Con la diferencia de
gol: +0.01. Partido cerrado 4.44 tarjetas, goleada 4.53. La idea
intuitiva de "partido cerrado, mas tarjetas" es falsa.

Entonces la varianza viene de otro lado, y el sospechoso de siempre es
el arbitro. ESPN lo devuelve en gameInfo.officials, dentro del mismo
/summary que ya se pedia: guardarlo no cuesta un pedido extra.

Lo dificil no es encontrar una diferencia entre arbitros — siempre la
hay, aunque repartas los partidos tirando una moneda. Lo dificil es
saber si esa diferencia es mas grande que la que da el azar. Por eso el
veredicto sale de una prueba de permutacion: se mezclan los totales
entre arbitros miles de veces y se cuenta cuantas de esas mezclas dan
una separacion igual o mayor que la real. Si el azar la iguala seguido,
no hay efecto que mostrar.

El 2026-08-23, con 54 partidos y ~2 por arbitro, el azar igualaba lo
observado el 33% de las veces en tarjetas y el 19% en faltas: nada que
se pueda usar. El dato se sigue guardando y esto se vuelve a correr
cuando haya mas fechas.

    python medir_arbitros.py
"""

import json
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CACHE = Path("data/cache_disciplina.json")

# Cuantos arbitros con 2+ partidos hacen falta para que la comparacion
# tenga algun sentido. Con menos, la dispersion entre promedios es un
# numero sacado de tres puntos.
MIN_ARBITROS = 5

# Debajo de esto se considera que el azar no lo explica solo. Es el
# umbral de siempre; se deja explicito para que no parezca elegido
# despues de ver el resultado.
UMBRAL = 0.05

METRICAS = ("tarjetas", "faltas", "corners")


def _media(v):
    return sum(v) / len(v)


def _var(v):
    if len(v) < 2:
        return 0.0
    m = _media(v)
    return sum((x - m) ** 2 for x in v) / (len(v) - 1)


def pares_arbitro(cache, metrica):
    """[(arbitro, total del partido)] para los partidos que tienen las
    dos cosas: quien dirigio y la metrica de los dos equipos."""
    out = []
    for eid, partido in (cache or {}).items():
        if str(eid).startswith("_") or not isinstance(partido, dict):
            continue
        arb = partido.get("_arbitro")
        if not arb:
            continue
        # Las claves con guion bajo son del partido, no equipos.
        # `_jugadores` ES un diccionario, asi que filtrar por tipo no
        # alcanza: contaria como un tercer equipo.
        filas = [f for k, f in partido.items()
                 if not str(k).startswith("_") and isinstance(f, dict)]
        if len(filas) != 2:
            continue
        vals = [f.get(metrica) for f in filas]
        if any(not isinstance(v, (int, float)) for v in vals):
            continue
        out.append((arb, float(sum(vals))))
    return out


def dispersion_entre(pares):
    """Cuanto se separan entre si los promedios de cada arbitro.

    Es el numero que la prueba de permutacion pone a competir contra el
    azar. Solo cuentan los que dirigieron al menos dos partidos: con uno
    solo el "promedio" es el partido, y eso infla la separacion sin que
    haya nada detras.
    """
    por = {}
    for arb, v in pares:
        por.setdefault(arb, []).append(v)
    medias = [_media(v) for v in por.values() if len(v) >= 2]
    if len(medias) < MIN_ARBITROS:
        return None
    return _var(medias)


def pvalor(pares, vueltas=5000, semilla=0):
    """Cada cuanto el azar solo da una separacion igual o mayor.

    Se mezclan los totales entre arbitros manteniendo cuantos partidos
    dirigio cada uno. Si el azar iguala lo observado seguido, la
    diferencia entre arbitros no es informacion.
    """
    obs = dispersion_entre(pares)
    if obs is None:
        return None
    arbs = [a for a, _ in pares]
    vals = [v for _, v in pares]
    rnd = random.Random(semilla)
    peores = total = 0
    for _ in range(vueltas):
        rnd.shuffle(vals)
        d = dispersion_entre(list(zip(arbs, vals)))
        if d is None:
            continue
        total += 1
        if d >= obs:
            peores += 1
    return None if not total else peores / total


def main():
    if not CACHE.exists():
        print("No hay data/cache_disciplina.json todavia.")
        return 1
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    partidos = [k for k in cache if not str(k).startswith("_")]
    con_arb = [k for k in partidos if cache[k].get("_arbitro")]
    print(f"\ncache: {len(partidos)} partidos, {len(con_arb)} con arbitro informado")
    print("(el resto se rellena solo cuando esos equipos vuelvan a jugar)\n")

    for met in METRICAS:
        pares = pares_arbitro(cache, met)
        por = {}
        for a, v in pares:
            por.setdefault(a, []).append(v)
        repetidos = {a: v for a, v in por.items() if len(v) >= 2}
        obs = dispersion_entre(pares)
        if obs is None:
            print(f"{met:9} sin muestra: {len(por)} arbitros, "
                  f"{len(repetidos)} con 2+ partidos (hacen falta {MIN_ARBITROS})")
            continue
        p = pvalor(pares)
        media = _media([v for _, v in pares])
        veredicto = ("PESA — el azar no lo explica solo" if p < UMBRAL
                     else "indistinguible del azar")
        print(f"{met:9} {len(pares)} partidos · {len(repetidos)} arbitros con 2+ · "
              f"media {media:.2f}")
        print(f"          separacion observada {obs:.2f} · el azar la iguala el "
              f"{p * 100:.1f}% de las veces")
        print(f"          -> {veredicto}")
        if p < UMBRAL:
            ext = sorted(repetidos.items(), key=lambda x: _media(x[1]))
            print(f"          menos: {ext[0][0]} {_media(ext[0][1]):.1f} "
                  f"(n={len(ext[0][1])}) · mas: {ext[-1][0]} "
                  f"{_media(ext[-1][1]):.1f} (n={len(ext[-1][1])})")
        print("")

    print("Mientras el veredicto sea 'indistinguible', la app no muestra")
    print("nada del arbitro: mostrarlo seria vender ruido como lectura.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
