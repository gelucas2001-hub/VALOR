#!/usr/bin/env python3
"""¿El RIVAL y el EQUIPO mueven los remates de un jugador?

De dónde sale la pregunta, y es de Lucas: *"no sé cuáles son las
variables que pueden intensificar las probabilidades de que x jugador
remate. Puede ser el equipo — al Fluminense le suelen rematar mucho los
mediocampistas — o los laterales contra estos rivales suelen pegar de
afuera."*

Es la pregunta correcta, porque hoy el número de jugador **no mira nada
de eso**. `esperado_jugador()` toma la serie reciente del jugador y la
encoge hacia el promedio de su puesto. Punto. No mira contra quién
juega, ni cuánto remata su equipo, ni si el partido pinta trabado.

Y encima es la métrica peor calibrada que tenemos: `medir_jugadores.py`
mide que remates se desvía **2.09 veces** lo que explica el azar. Si
algo la va a arreglar, es información que hoy se está tirando.

Lo raro es que la información ya está en casa: a nivel EQUIPO la app sí
ajusta por el rival (`esperados()` usa lo que el rival concede). Ese
ajuste nunca bajó al jugador.

Los tres pronósticos que se comparan, todos walk-forward:

  hoy     la serie del jugador encogida hacia su puesto. Lo que la app
          publica hoy.
  rival   lo mismo, escalado por cuánto concede el rival respecto del
          promedio de la liga. Si el rival deja rematar 20% más que la
          media, el jugador sube 20%.
  cuota   la PARTE del jugador en los remates de su equipo, aplicada a
          lo que se espera que remate el equipo en este partido. Es la
          lectura de Lucas: "a este equipo le rematan los del medio".

La vara y el ruido: se comparan por error cuadrático sobre las mismas
apariciones, con bootstrap pareado. Dos predicciones sobre el mismo
jugador-partido no son independientes de las del resto de su equipo, así
que además se deja un PARTIDO afuera por vez — la lección que costó el
falso hallazgo del CLV.

    python medir_ajuste_jugador.py
    python medir_ajuste_jugador.py --metrica al_arco
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent

PLANTELES = RAIZ / "data" / "planteles.json"

# Antes de predecirle a un jugador hace falta haberlo visto. Mismo
# mínimo que usa `medir_jugadores.py`, por la misma razón: una serie de
# un partido no distingue al regular del explosivo.
MINIMO = 2

# Cuántos partidos previos del equipo hacen falta para creerle a "cuánto
# concede". Con menos, el factor es ruido multiplicando ruido.
MIN_EQUIPO = 3

REMUESTREOS = 2000
SEMILLA = 20260831


def equipo_de(planteles):
    """{id de jugador: id de equipo}, del caché de planteles."""
    out = {}
    for tid, js in (planteles or {}).items():
        for j in js or []:
            if j.get("id"):
                out[str(j["id"])] = str(tid)
    return out


def factor_rival(concede, media_liga, tope=1.6):
    """Cuánto más (o menos) deja rematar este rival que el promedio.

    El tope no es cosmético: con tres o cuatro partidos, un rival que
    tuvo dos goleadas en contra da un factor de 2.5 que no describe al
    rival, describe la muestra. Recortar es preferir un sesgo chico y
    conocido a una varianza grande y silenciosa.
    """
    if not media_liga or concede is None or media_liga <= 0:
        return 1.0
    f = concede / media_liga
    return max(1 / tope, min(tope, f))


def _ec(reales, preds):
    return sum((r - p) ** 2 for r, p in zip(reales, preds)) / len(reales)


def bootstrap(reales, a, b, remuestreos=REMUESTREOS, semilla=SEMILLA):
    """Error estándar de la diferencia de error cuadrático, pareada."""
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


def evaluar(historia, equipo_por_jugador, metrica="remates", pos_de=None):
    """Una fila por jugador-partido con los tres pronósticos.

    Estricto: todo lo que entra a un pronóstico salió de partidos
    anteriores. La media de la liga también se acumula sobre la marcha.
    """
    import actualizar as A
    import medir_jugadores as J

    i_met = J._IDX[metrica]
    i_eq = list(A.METRICAS_PARTIDO).index(metrica)

    serie_jug = defaultdict(list)      # pid -> [valores]
    hizo = defaultdict(list)           # tid -> [lo que hizo]
    concedio = defaultdict(list)       # tid -> [lo que le hicieron]
    suma_liga = n_liga = 0
    # Inyectable para poder probarlo sin arrastrar `planteles.json`: la
    # medición no puede depender de un archivo de producción para tener
    # tests, y el test lo pidió antes de que se me ocurriera.
    pos_de = J._posiciones() if pos_de is None else pos_de
    filas = []

    for fecha, eid, jugadores, equipos in historia:
        media_liga = (suma_liga / n_liga) if n_liga else None

        # Parámetros por puesto con lo anterior, igual que el pipeline.
        por_pos = {}
        for pid, vals in serie_jug.items():
            p = pos_de.get(pid)
            if p and len(vals) >= MINIMO:
                por_pos.setdefault(p, {})[pid] = vals[-A.SERIE_N:]
        par_pos = {p: A.parametros_metricas({metrica: m}).get(metrica)
                   for p, m in por_pos.items()}

        ids = [t for t in equipos]
        for pid, fila in jugadores.items():
            tid = equipo_por_jugador.get(str(pid))
            if not tid or tid not in ids or len(ids) != 2:
                continue
            rid = ids[0] if ids[1] == tid else ids[1]
            vals = serie_jug.get(pid) or []
            par = par_pos.get(pos_de.get(pid))
            if len(vals) < MINIMO or not par or media_liga is None:
                continue
            if len(concedio.get(rid) or []) < MIN_EQUIPO:
                continue
            if len(hizo.get(tid) or []) < MIN_EQUIPO:
                continue

            hoy = J.esperado(vals[-A.SERIE_N:], par)
            if hoy is None:
                continue

            c_rival = sum(concedio[rid]) / len(concedio[rid])
            f = factor_rival(c_rival, media_liga)

            # La parte del jugador en lo de su equipo, y lo que se espera
            # que haga el equipo contra ESTE rival.
            propio = sum(hizo[tid]) / len(hizo[tid])
            parte = (sum(vals[-A.SERIE_N:]) / len(vals[-A.SERIE_N:]) / propio
                     if propio > 0 else None)
            esperado_eq = propio * f

            filas.append({
                "fecha": fecha, "ev": str(eid), "pid": str(pid),
                "real": float(fila[i_met]),
                "hoy": hoy,
                "rival": hoy * f,
                "cuota": (parte * esperado_eq) if parte is not None else hoy,
            })

        # Recién ahora entra este partido a la historia.
        for pid, fila in jugadores.items():
            serie_jug[pid].append(float(fila[i_met]))
        for tid, row in equipos.items():
            v = row.get(metrica)
            if v is None:
                continue
            hizo[tid].append(float(v))
            for otro, orow in equipos.items():
                if otro != tid and orow.get(metrica) is not None:
                    concedio[tid].append(float(orow[metrica]))
            suma_liga += float(v)
            n_liga += 1

    return filas


def comparar(filas, remuestreos=REMUESTREOS):
    """Error cuadrático de cada pronóstico y su diferencia contra `hoy`."""
    if not filas:
        return None
    reales = [f["real"] for f in filas]
    out = {"n": len(filas), "e_hoy": _ec(reales, [f["hoy"] for f in filas])}
    for k in ("rival", "cuota"):
        preds = [f[k] for f in filas]
        out["e_" + k] = _ec(reales, preds)
        out["gana_" + k] = out["e_hoy"] - out["e_" + k]
        out["ee_" + k] = bootstrap(reales, [f["hoy"] for f in filas],
                                   preds, remuestreos)
    return out


def dejar_uno_afuera(filas, cual="rival", remuestreos=300):
    """La ganancia recalculada sacando un partido por vez.

    Las apariciones de un mismo partido comparten rival, ritmo y árbitro:
    no son observaciones independientes y el error estándar no lo sabe.
    """
    evs = sorted({f["ev"] for f in filas})
    out = []
    for e in evs:
        sub = [f for f in filas if f["ev"] != e]
        r = comparar(sub, remuestreos)
        if r:
            out.append({"sin": e, "n": r["n"], "gana": r["gana_" + cual]})
    return out


def main(argv):
    import medir_jugadores as J
    import medir_lineas as L

    metrica = "remates"
    if "--metrica" in argv:
        metrica = argv[argv.index("--metrica") + 1]

    disc = json.loads(J.DISCIPLINA.read_text(encoding="utf-8")) \
        if J.DISCIPLINA.exists() else {}
    fechas = L._fechas_conocidas(sin_red="--sin-red" in argv)
    historia = []
    for eid, v in disc.items():
        jg = (v or {}).get("_jugadores")
        f = fechas.get(str(eid))
        if not jg or not f:
            continue
        equipos = {k: val for k, val in v.items() if not k.startswith("_")}
        if len(equipos) == 2:
            historia.append((f, str(eid), jg, equipos))
    historia.sort()

    plant = json.loads(PLANTELES.read_text(encoding="utf-8")) \
        if PLANTELES.exists() else {}
    eq_de = equipo_de(plant.get("equipos") or {})

    print(f"\n  ¿EL RIVAL Y EL EQUIPO MUEVEN AL JUGADOR? — {metrica}\n")
    print(f"  {len(historia)} partidos resueltos · {len(eq_de)} jugadores "
          f"con equipo conocido")

    filas = evaluar(historia, eq_de, metrica)
    r = comparar(filas)
    if not r:
        print("\n  Sin apariciones evaluables.\n")
        return 1

    print(f"  {r['n']} apariciones evaluadas\n")
    print(f"    {'pronóstico':10} {'error²':>9} {'le gana a hoy':>15} {'e.e.':>8}")
    print("    " + "-" * 46)
    print(f"    {'hoy':10} {r['e_hoy']:9.4f}")
    for k, nombre in (("rival", "por rival"), ("cuota", "por cuota")):
        sig = r["gana_" + k] / r["ee_" + k] if r["ee_" + k] else 0
        marca = "  ←" if sig >= 2 else ("  ✗" if sig <= -2 else "")
        print(f"    {nombre:10} {r['e_' + k]:9.4f} {r['gana_' + k]:+15.4f} "
              f"{r['ee_' + k]:8.4f}{marca}")

    for k in ("rival", "cuota"):
        fuera = dejar_uno_afuera(filas, k)
        if len(fuera) > 2:
            peor = min(fuera, key=lambda f: f["gana"])
            mejor = max(fuera, key=lambda f: f["gana"])
            print(f"\n    {k}: dejando un partido afuera, la ganancia va de "
                  f"{peor['gana']:+.4f} a {mejor['gana']:+.4f}")

    print("\n  'le gana a hoy' positivo = el ajuste mejora. La marca ← pide")
    print("  dos errores estándar, y el dejar-uno-afuera está porque las")
    print("  apariciones de un mismo partido no son independientes: si el")
    print("  rango cruza el cero, la ganancia era de un partido.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
