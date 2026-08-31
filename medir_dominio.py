#!/usr/bin/env python3
"""¿Los anclas por equipo sirven en las CINCO métricas, o solo en córners?

De dónde sale: el eje Dominio de la lectura por ejes (TRASPASO §17).

Lo que YA estaba medido, y conviene no volver a medir: `historia_equipos.py`
probó el 2026-08-25, walk-forward sobre eng y fra, que usar la historia
larga como ancla lleva la predicción de **córners** del 16% al 71% del
techo teórico — 0.4084 ± 0.0902 de error cuadrático en eng (4.5 errores
estándar) y 0.1857 ± 0.0538 en fra (3.5).

Lo que NO estaba medido: las otras cuatro métricas. El archivo guarda
remates, al arco, faltas y tarjetas con la misma estructura, y la app
las muestra igual, pero el único número que respalda el ancla es el de
córners. Que sirva ahí no dice nada de las demás: los `k` de liga van
de 6.8 (remates) a 48.6 (tarjetas), o sea que las métricas se
distinguen entre equipos de formas muy distintas.

Cómo se mide:

Walk-forward estricto por equipo. Para cada partido se predice cuánto
va a hacer cada equipo de esa métrica usando **solo lo anterior**, con
tres pronósticos:

  liga   la media de la liga hasta ese momento. Es la vara.
  corto  las últimas VENTANA apariciones del equipo, encogidas hacia la
         liga. Es lo que la app sabía antes de que existieran los anclas.
  largo  TODA la historia previa del equipo, encogida hacia la liga.
         Es lo que agrega `data/historia_equipos.json`.

El `k` de encogimiento no se elige a ojo ni se hereda: se busca en la
primera mitad temporal y se mide en la segunda, y cada pronóstico se
queda con el suyo — darle al `corto` un `k` peor sería ganarle a un
rival amañado.

La vara es la media de la liga, no cero: predecir "el promedio" ya
acierta bastante en métricas que varían poco entre equipos, y sin esa
referencia cualquier pronóstico parece bueno.

    python medir_dominio.py eng
    python medir_dominio.py fra --rapido
"""

import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent

# Cuántas apariciones recientes mira el pronóstico corto. Es el orden de
# magnitud del caché del cron (`estadisticas.json` dice `sobre: 8`).
VENTANA = 8

# Antes de predecirle a un equipo hace falta haberlo visto alguna vez.
MIN_PREVIOS = 3

# La grilla de encogimiento. Arranca en 0 —no encoger— y llega hasta un
# valor donde el pronóstico es casi la liga entera. Si el mejor `k` cae
# en un extremo, el barrido no encontró nada y hay que extender la
# grilla: es regla dura del repo, quemada dos veces el 2026-08-24.
GRILLA_K = [0, 1, 2, 3, 5, 8, 12, 20, 30, 50, 80, 130, 200, 320, 500]

CORTE = 0.5          # primera mitad elige `k`, segunda mide
REMUESTREOS = 2000
SEMILLA = 20260831

METRICAS = ("corners", "remates", "al_arco", "faltas", "tarjetas")


def apariciones(partidos, metrica):
    """Una fila por equipo y por partido, en orden cronológico.

    Cada fila es (fecha, equipo, valor). El partido aporta dos filas —
    una por equipo— porque la métrica es de equipo, no de partido.
    """
    filas = []
    for p in partidos or []:
        est = (p.get("est") or {}).get(metrica)
        if not est:
            continue
        for lado, clave in (("h", "home"), ("a", "away")):
            if lado in est and p.get(clave):
                filas.append((p["fecha"], p[clave], float(est[lado])))
    filas.sort(key=lambda f: f[0])
    return filas


def encoger(media_equipo, n, media_liga, k):
    """La media del equipo tirada hacia la liga según cuánto se lo vio.

    Con k=0 queda la media cruda del equipo; con k grande queda la liga.
    Es la misma forma que `media_encogida()` de actualizar.py — acá se
    reescribe porque este script no importa el motor, y la fórmula es
    de una línea.
    """
    if n <= 0:
        return media_liga
    return (media_equipo * n + media_liga * k) / (n + k)


def pronosticos(filas, ventana=VENTANA, min_previos=MIN_PREVIOS):
    """Para cada aparición: lo que pasó y los tres pronósticos crudos.

    Devuelve (real, media_liga, media_corta, n_corto, media_larga,
    n_largo) por fila. El encogimiento se aplica después, porque el `k`
    se elige aparte y no conviene recorrer todo de nuevo por cada `k`.
    """
    hist = {}                      # equipo -> [valores previos]
    suma_liga = n_liga = 0
    salida = []
    for _fecha, equipo, real in filas:
        previos = hist.get(equipo)
        if previos and len(previos) >= min_previos and n_liga:
            media_liga = suma_liga / n_liga
            corto = previos[-ventana:]
            salida.append((
                real, media_liga,
                sum(corto) / len(corto), len(corto),
                sum(previos) / len(previos), len(previos),
            ))
        hist.setdefault(equipo, []).append(real)
        suma_liga += real
        n_liga += 1
    return salida


def _ec(reales, preds):
    return sum((r - p) ** 2 for r, p in zip(reales, preds)) / len(reales)


def _errores(datos, k_corto, k_largo):
    """Error cuadrático de los tres pronósticos sobre las mismas filas."""
    liga, corto, largo, reales = [], [], [], []
    for real, m_liga, m_corto, n_corto, m_largo, n_largo in datos:
        reales.append(real)
        liga.append(m_liga)
        corto.append(encoger(m_corto, n_corto, m_liga, k_corto))
        largo.append(encoger(m_largo, n_largo, m_liga, k_largo))
    return reales, liga, corto, largo


def elegir_k(datos, cual):
    """El `k` que menos error da en train, para `corto` o para `largo`.

    Cada pronóstico elige el suyo: comparar el largo con su mejor `k`
    contra el corto con un `k` prestado sería medir contra un rival
    amañado.
    """
    mejor, mejor_k = None, None
    for k in GRILLA_K:
        preds, reales = [], []
        for real, m_liga, m_corto, n_corto, m_largo, n_largo in datos:
            reales.append(real)
            if cual == "corto":
                preds.append(encoger(m_corto, n_corto, m_liga, k))
            else:
                preds.append(encoger(m_largo, n_largo, m_liga, k))
        e = _ec(reales, preds)
        if mejor is None or e < mejor:
            mejor, mejor_k = e, k
    return mejor_k, mejor_k in (GRILLA_K[0], GRILLA_K[-1])


def bootstrap(reales, a, b, remuestreos=REMUESTREOS, semilla=SEMILLA):
    """Error estándar de la diferencia de error cuadrático, pareada.

    Pareada porque los dos pronósticos se evalúan sobre las MISMAS
    apariciones: la desviación que importa es la de la diferencia fila
    por fila, no la de cada error por separado.
    """
    dif = [(r - x) ** 2 - (r - y) ** 2 for r, x, y in zip(reales, a, b)]
    n = len(dif)
    if n < 2:
        return 0.0
    rnd = random.Random(semilla)
    medias = []
    for _ in range(remuestreos):
        s = 0.0
        for _ in range(n):
            s += dif[rnd.randrange(n)]
        medias.append(s / n)
    mu = sum(medias) / len(medias)
    return (sum((x - mu) ** 2 for x in medias) / (len(medias) - 1)) ** 0.5


def medir(partidos, metrica, remuestreos=REMUESTREOS):
    """Todo junto para una métrica: elegir en train, medir en test."""
    datos = pronosticos(apariciones(partidos, metrica))
    if len(datos) < 200:
        return None
    corte = int(len(datos) * CORTE)
    train, test = datos[:corte], datos[corte:]
    k_corto, borde_c = elegir_k(train, "corto")
    k_largo, borde_l = elegir_k(train, "largo")
    reales, liga, corto, largo = _errores(test, k_corto, k_largo)
    e_liga, e_corto, e_largo = _ec(reales, liga), _ec(reales, corto), _ec(reales, largo)
    return {
        "metrica": metrica, "n": len(test), "k_corto": k_corto, "k_largo": k_largo,
        "borde": borde_c or borde_l,
        "e_liga": e_liga, "e_corto": e_corto, "e_largo": e_largo,
        "mej_corto": (e_liga - e_corto) / e_liga * 100 if e_liga else 0,
        "mej_largo": (e_liga - e_largo) / e_liga * 100 if e_liga else 0,
        "ganancia": e_corto - e_largo,
        "ee": bootstrap(reales, corto, largo, remuestreos),
    }


def main(argv):
    import historico as H

    args = [a for a in argv[1:] if not a.startswith("-")]
    liga = (args[0] if args else "eng").lower()
    remuestreos = 300 if "--rapido" in argv else REMUESTREOS

    partidos = H.partidos(liga)
    con_est = sum(1 for p in partidos if p.get("est"))
    print(f"\n  EL EJE DOMINIO — {liga}")
    print(f"  {len(partidos)} partidos, {con_est} con estadísticas por partido\n")
    if not con_est:
        print("  Esta liga no trae estadísticas por partido en la fuente.")
        print("  Es el caso de arg y bra: no hay nada que medir acá.\n")
        return 1

    print(f"  {'métrica':10} {'n test':>7} {'liga':>8} {'corto':>8} {'largo':>8} "
          f"{'mejora':>8} {'gana':>9} {'e.e.':>7}")
    print("  " + "-" * 74)
    for met in METRICAS:
        r = medir(partidos, met, remuestreos)
        if not r:
            print(f"  {met:10}    sin muestra suficiente")
            continue
        sig = r["ganancia"] / r["ee"] if r["ee"] else 0
        marca = "  ←" if sig >= 2 else ("  ✗" if sig <= -2 else "")
        print(f"  {r['metrica']:10} {r['n']:7d} {r['e_liga']:8.3f} {r['e_corto']:8.3f} "
              f"{r['e_largo']:8.3f} {r['mej_largo']:+7.1f}% {r['ganancia']:+9.4f} "
              f"{r['ee']:7.4f}{marca}")
        if r["borde"]:
            print(f"             ⚠ el k elegido cayó en el borde de la grilla "
                  f"(corto={r['k_corto']}, largo={r['k_largo']}): extender GRILLA_K")

    print("\n  'liga', 'corto' y 'largo' son error cuadrático en test — menos es")
    print("  mejor. 'mejora' es cuánto le saca el largo a la media de la liga.")
    print("  'gana' es lo que el ancla larga le saca al caché corto, y solo se")
    print("  marca ← a partir de dos errores estándar de esa diferencia.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
