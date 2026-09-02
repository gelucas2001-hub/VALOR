#!/usr/bin/env python3
"""La historia larga de cada equipo, cruzada a los ids de ESPN.

Por qué existe:

El caché del cron tiene 5 u 8 partidos por equipo. `historico.py` tiene
**296**, con estadísticas por partido, para Inglaterra y Francia.
`equipos.py` resolvió el cruce de nombres. Falta ponerlo donde el
modelo lo pueda leer, y eso es este archivo.

Escribe `data/historia_equipos.json`. Se corre **a mano**: la fuente
cambia una vez por semana y el cron corre dos veces por día — meter 22
descargas de football-data en el camino caliente sería pagar todos los
días por un dato que casi nunca cambia.

Qué guarda, y por qué no guarda los valores sueltos:

Guarda `n`, `suma` y `suma2` por equipo y por métrica. De esos tres
salen la media y la varianza exactas, que es todo lo que
`parametros_metricas()` y `media_encogida()` necesitan. La alternativa
—80.000 números sueltos— pesa cien veces más y no dice nada que estos
tres no digan.

Cómo se usa el número, medido y no elegido:

Medido el 2026-08-25 walk-forward sobre las temporadas 2021 a 2025 de
eng.1 y fra.1, prediciendo los córners de cada equipo partido a partido
con solo lo anterior:

    techo teorico (saber la media exacta de cada equipo)   eng 7.88%
    hoy: solo la temporada en curso, k=200                     16% del techo
    historia como ancla + temporada en curso encima            71% del techo

La mejora sobre lo de hoy es 0.4084 +- 0.0902 de error cuadratico en
eng (4.5 errores estandar) y 0.1857 +- 0.0538 en fra (3.5). Ese techo
importa: los córners son casi todos varianza de partido a partido, así
que "solo 5.6% mejor que el promedio de la liga" es en realidad capturar
siete décimas de todo lo que se puede capturar.

**La ventana de historia no importa.** Once temporadas contra tres:
0.0061 +- 0.0178 de diferencia, o sea ruido, y lo mismo en las seis
ventanas probadas y en las dos ligas. No es que once sea mejor: es que
la grilla entera es plana. Se usan todas las que hay porque cubre más
equipos (un ascendido tiene 114 partidos en once temporadas y 38 en
tres), no porque prediga mejor.

    python historia_equipos.py            # escribe el JSON
    python historia_equipos.py --ver      # muestra qué haría, sin escribir
"""

import datetime
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import equipos as EQ

RAIZ = Path(__file__).resolve().parent
DESTINO = RAIZ / "data" / "historia_equipos.json"

# De las ligas de `historico.LIGAS`, cuáles tienen equipo en ESPN. Las
# que no traen estadísticas por partido quedan registradas en
# `sin_estadisticas` en vez de generar una entrada vacía.
LIGAS = {"arg": "arg.1", "bra": "bra.1", "eng": "eng.1", "fra": "fra.1",
         "spa": "esp.1"}


def media(d):
    """La media desde el resumen. None si no hay partidos."""
    if not d or not d.get("n"):
        return None
    return d["suma"] / d["n"]


def varianza(d):
    """La varianza poblacional desde el resumen. None si no hay partidos.

    E[x²] − E[x]². Se recorta en cero porque con floats la resta puede
    dar un negativo minúsculo cuando todos los valores son iguales, y
    una varianza negativa rompe la raíz aguas abajo.
    """
    if not d or not d.get("n"):
        return None
    m = d["suma"] / d["n"]
    return max(0.0, d["suma2"] / d["n"] - m * m)


def resumir(muestras):
    """{met: {tid: [valores]}} a {met: {tid: {n, suma, suma2}}}."""
    out = {}
    for met, por_eq in (muestras or {}).items():
        for tid, vals in (por_eq or {}).items():
            vs = [float(v) for v in vals or []]
            if not vs:
                continue
            out.setdefault(met, {})[str(tid)] = {
                "n": len(vs),
                "suma": round(sum(vs), 3),
                "suma2": round(sum(v * v for v in vs), 3),
            }
    return out


def prior(d, media_liga, k):
    """El ancla de un equipo: su historia encogida hacia la liga.

    Es `media_encogida()` de `actualizar.py`, pero desde el resumen en
    vez de la lista. Sin historia devuelve la media de la liga, que es
    exactamente lo que la app usa hoy — o sea que el peor caso de este
    archivo es no cambiar nada.
    """
    n = (d or {}).get("n") or 0
    suma = (d or {}).get("suma") or 0.0
    return (suma + k * media_liga) / (n + k)


def _muestras_de(partidos, idx):
    """{met: {tid: [vals]}} y los nombres que no cruzaron, en orden."""
    muestras, sin_cruzar, n_partidos = {}, [], 0
    for p in partidos or []:
        est = p.get("est")
        n_partidos += 1
        if not est:
            continue
        for lado, clave in (("h", "home"), ("a", "away")):
            nombre = p.get(clave)
            tid = EQ.cruzar(nombre, idx)
            if not tid:
                if nombre and nombre not in sin_cruzar:
                    sin_cruzar.append(nombre)
                continue
            for met, v in est.items():
                if not isinstance(v, dict) or lado not in v:
                    continue
                muestras.setdefault(met, {}).setdefault(tid, []).append(
                    float(v[lado]))
    return muestras, sin_cruzar, n_partidos


def construir(partidos_por_liga, indices, ligas=None):
    """El documento entero, desde partidos ya bajados y ya indexados.

    Recibe los datos en vez de bajarlos para poder probarse sin red.
    `partidos_por_liga` es {liga: [partidos de historico]}, `indices` es
    {liga: índice de equipos.indice()}.
    """
    import actualizar

    ligas = ligas or LIGAS
    doc = {
        "actualizado": datetime.date.today().isoformat(),
        "fuente": "football-data.co.uk vía historico.py, cruzado con "
                  "equipos.py contra los ids de ESPN",
        "ligas": {},
        "sin_estadisticas": [],
    }
    for liga, partidos in (partidos_por_liga or {}).items():
        slug = ligas.get(liga, liga)
        idx = (indices or {}).get(liga) or {}
        muestras, sin_cruzar, n_partidos = _muestras_de(partidos, idx)
        if not muestras:
            # Sin una sola estadística no se escribe la liga: una entrada
            # con cero equipos se parece demasiado a una con datos.
            doc["sin_estadisticas"].append(slug)
            continue
        doc["ligas"][slug] = {
            "partidos": n_partidos,
            "parametros": actualizar.parametros_metricas(muestras),
            "equipos": _por_equipo(resumir(muestras)),
            "sin_cruzar": sin_cruzar,
        }
    return doc


def _por_equipo(resumen):
    """Da vuelta {met: {tid: stats}} a {tid: {met: stats}}.

    El consumidor pregunta por equipo, no por métrica: `actualizar.py`
    ya está parado en un equipo cuando necesita esto.
    """
    out = {}
    for met, por_eq in (resumen or {}).items():
        for tid, d in por_eq.items():
            out.setdefault(tid, {})[met] = d
    return out


def bajar_todo(ligas=None):
    """Baja historia y equipos de cada liga. Necesita red."""
    import historico

    ligas = ligas or LIGAS
    partidos, indices = {}, {}
    for liga, slug in ligas.items():
        print(f"  · {liga}: historia…", end="", flush=True)
        partidos[liga] = historico.partidos(liga)
        print(f" {len(partidos[liga])} partidos · ESPN…", end="", flush=True)
        eq = EQ.equipos_espn(slug)
        indices[liga] = EQ.indice(eq)
        amb = EQ.ambiguos(eq)
        print(f" {len(eq)} equipos" + (f" · ! ambiguos: {amb}" if amb else ""))
    return partidos, indices


def main():
    ver = "--ver" in sys.argv
    print()
    partidos, indices = bajar_todo()
    doc = construir(partidos, indices)

    print()
    for slug, d in doc["ligas"].items():
        eq = d["equipos"]
        pjs = [v.get("corners", {}).get("n", 0) for v in eq.values()]
        print(f"  {slug}: {len(eq)} equipos, {d['partidos']} partidos, "
              f"{(sum(pjs) // len(pjs)) if pjs else 0} pj por equipo")
        ks = {m: p["k"] for m, p in d["parametros"].items()}
        print(f"     k por metrica: {ks}")
        if d["sin_cruzar"]:
            print(f"     sin cruzar ({len(d['sin_cruzar'])}): "
                  f"{', '.join(d['sin_cruzar'][:8])}"
                  + (" …" if len(d["sin_cruzar"]) > 8 else ""))
    if doc["sin_estadisticas"]:
        print(f"  sin estadisticas en la fuente: "
              f"{', '.join(doc['sin_estadisticas'])}")

    if ver:
        print("\n  (--ver: no se escribio nada)\n")
        return 0
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"\n  → {DESTINO} ({DESTINO.stat().st_size // 1024} KB)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
