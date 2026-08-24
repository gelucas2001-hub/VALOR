#!/usr/bin/env python3
"""¿Cuando la app dice que un jugador remata más de 1.5, pasa?

`medir_lineas.py` mide los totales del PARTIDO. Esto mide las líneas de
JUGADOR, que `index.html` viene mostrando desde el 2026-08-23 sin que
nadie las hubiera comprobado.

Existe por una pregunta de Lucas del 2026-08-24: "si yo juego al mercado
de remates y remates al arco de jugadores, ¿la app me sirve?". La
respuesta honesta era que no se sabía, y este script es lo que hacía
falta para saberlo.

La medición es walk-forward: para cada partido, la serie del jugador y
los parámetros de su puesto salen SOLO de partidos anteriores. Nunca se
usa el partido que se está prediciendo.

Lo que lo distingue de los otros medir_*: **compara contra el ruido, no
contra cero**. Con las 618 observaciones que hay hoy, un modelo
perfectamente calibrado ya desvía 3.5 puntos por puro azar. Un desvío
de 4 no es un problema; uno de 7 sí. Sin ese control, cualquier métrica
parece rota.

    python medir_jugadores.py

Escribe `data/calibracion_jugadores.json`, que la app lee para decir en
pantalla de qué métrica fiarse.
"""

import collections
import datetime
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import actualizar as A
import medir_lineas as L

DISCIPLINA = Path("data/cache_disciplina.json")
PLANTELES = Path("data/planteles.json")
DESTINO = Path("data/calibracion_jugadores.json")

# Las que tienen mercado de jugador en las casas. Se miden todas aunque
# la pregunta original fuera por remates: una métrica que nadie mira hoy
# se mira mañana, y el costo de medirla ya está pagado.
METRICAS = A.METRICAS_JUGADOR

# El orden del array que guarda el caché, sin el flag de titular.
CAMPOS = A.CAMPOS_JUGADOR_PARTIDO[:-1]
_IDX = {m: i for i, m in enumerate(CAMPOS)}

# Igual que el pipeline: una serie de un solo partido no distingue al
# regular del explosivo, que es para lo único que la serie existe.
MINIMO = 2

# Cuántas veces se simula un modelo perfecto para estimar el ruido. Con
# 2000 el número deja de moverse en el primer decimal.
REPS_RUIDO = 2000


# ── las piezas, cada una medible por separado ──────────────────────

def serie_previa(historia, fecha, tope=None):
    """Los partidos de un jugador ANTERIORES a `fecha`, del más viejo al
    más nuevo, recortados a los últimos `tope`.

    `historia` es [(fecha, event_id, fila)]. Solo entran los partidos
    que el jugador jugó: un cero de alguien que estuvo en el banco no es
    un cero medido, es una ausencia, y promediarlo hunde su número.
    """
    tope = A.SERIE_N if tope is None else tope
    previos = [f for f in sorted(historia) if f[0] < fecha]
    return [f[2] for f in previos][-tope:] if tope else [f[2] for f in previos]


def valores(serie, met):
    """La columna de una métrica dentro de la serie."""
    i = _IDX.get(met)
    if i is None:
        return []
    return [float(f[i]) for f in serie or [] if len(f) > i]


def esperado(vals, par):
    """Lo que se espera de este jugador, encogido hacia su puesto.

    Es la misma cuenta que corre el pipeline (`esperado_jugador`), traída
    acá para poder barrerla sin tocar el motor.
    """
    if not par:
        return None
    return A.media_encogida(vals or [], par["media"], par["k"])


def linea_de(mu):
    """La línea que la app ofrece para ese esperado.

    Es el mismo `Math.max(0.5, Math.round(mu) - 0.5)` de `lineaJugador`
    en `index.html`. Se copia y no se reinventa: si las dos se separan,
    la medición deja de decir algo sobre lo que el usuario ve.

    Ojo con lo que esto implica y que la medición dejó a la vista: como
    la línea sale del esperado, y el esperado de casi todos los
    jugadores es menor que 1.5, la app termina ofreciendo la línea 0.5
    en la enorme mayoría de los casos. O sea que contesta "¿remata al
    menos una vez?" y no "¿remata más de 2.5?", que suele ser la que la
    casa pone en la pizarra.
    """
    if mu is None:
        return None
    return max(0.5, round(mu) - 0.5)


def ruido_esperado(ps, reps=REPS_RUIDO, semilla=7):
    """El desvío que mostraría un modelo PERFECTO con esta muestra.

    Es la vara. Si la app dice 60% y pasa el 60%, con 600 casos el
    desvío medido igual no da cero: da unos tres puntos y medio, porque
    600 monedas no salen exactamente mitad y mitad. Comparar el desvío
    observado contra cero es fabricar un problema; hay que compararlo
    contra esto.
    """
    if not ps:
        return None
    rnd = random.Random(semilla)
    salidas = []
    for _ in range(reps):
        filas = [{"p": p, "paso": 1 if rnd.random() < p else 0} for p in ps]
        r = L.resumen_metrica(filas)
        if r:
            salidas.append(r["desvio"])
    if not salidas:
        return None
    salidas.sort()
    return round(salidas[len(salidas) // 2], 1)


def veredicto(desvio, ruido):
    """De qué fiarse, en palabras, comparando contra el ruido.

    Los cortes son múltiplos del ruido y no números absolutos, porque el
    mismo desvío significa cosas distintas con 100 casos que con 5000.
    """
    if desvio is None or not ruido:
        return None
    razon = desvio / ruido
    if razon <= 1.3:
        return {"nivel": "bien", "razon": round(razon, 2),
                "texto": "Le viene acertando: cuando dice un porcentaje, "
                         "pasa más o menos eso."}
    if razon <= 1.8:
        return {"nivel": "regular", "razon": round(razon, 2),
                "texto": "Se le va la mano en algunos tramos. Sirve para "
                         "comparar jugadores, no para creerle el número exacto."}
    return {"nivel": "mal", "razon": round(razon, 2),
            "texto": "No le creas el porcentaje: se desvía bastante más "
                     "de lo que explica el azar."}


def resumen(filas, largos):
    """Lo que se publica de una métrica."""
    if not filas:
        return None
    base = L.resumen_metrica(filas)
    if not base:
        return None
    ruido = ruido_esperado([f["p"] for f in filas])
    v = veredicto(base["desvio"], ruido)
    tipico = collections.Counter(largos or []).most_common(1)
    return {
        "n": base["n"],
        "desvio": base["desvio"],
        "sesgo": base["sesgo"],
        "ruido": ruido,
        "nivel": (v or {}).get("nivel"),
        "razon": (v or {}).get("razon"),
        "texto": (v or {}).get("texto"),
        "serie": tipico[0][0] if tipico else None,
    }


# ── el recorrido, que es lo caro ───────────────────────────────────

def _posiciones():
    if not PLANTELES.exists():
        return {}
    d = json.loads(PLANTELES.read_text(encoding="utf-8"))
    return {str(j["id"]): j["pos"]
            for eq in (d.get("equipos") or {}).values()
            for j in eq or []
            if j.get("id") and j.get("pos")}


def historia(sin_red=False):
    """[(fecha, event_id, {jugador: fila})], del más viejo al más nuevo."""
    if not DISCIPLINA.exists():
        return []
    d = json.loads(DISCIPLINA.read_text(encoding="utf-8"))
    fechas = L._fechas_conocidas(sin_red=sin_red)
    out = []
    for eid, v in d.items():
        jg = (v or {}).get("_jugadores")
        f = fechas.get(str(eid))
        if jg and f:
            out.append((f, str(eid), jg))
    out.sort()
    return out


def evaluar(hist, pos_de=None):
    """{metrica: ([filas de calibracion], [largos de serie])}."""
    pos_de = _posiciones() if pos_de is None else pos_de
    acumulado = collections.defaultdict(list)
    filas = {m: [] for m in METRICAS}
    largos = {m: [] for m in METRICAS}

    for fecha, eid, jugadores in hist:
        # Parámetros por puesto con lo que se sabía ANTES de este partido.
        por_pos = {}
        for pid, serie in acumulado.items():
            p = pos_de.get(pid)
            if not p or len(serie) < MINIMO:
                continue
            for m in METRICAS:
                (por_pos.setdefault(p, {}).setdefault(m, {})
                 [pid]) = valores(serie[-A.SERIE_N:], m)
        par_pos = {}
        for p, muestras in por_pos.items():
            pr = A.parametros_metricas(muestras)
            if pr:
                par_pos[p] = pr

        for pid, fila in jugadores.items():
            serie = acumulado.get(pid) or []
            if len(serie) < MINIMO:
                continue
            par = par_pos.get(pos_de.get(pid))
            if not par:
                continue
            ventana = serie[-A.SERIE_N:]
            for m in METRICAS:
                pm = par.get(m)
                if not pm or not pm.get("disp"):
                    continue
                vals = valores(ventana, m)
                mu = esperado(vals, pm)
                ln = linea_de(mu)
                q = L.prob_mayor(mu, pm["disp"], ln)
                if q is None:
                    continue
                real = float(fila[_IDX[m]])
                filas[m].append({"p": q, "paso": int(real > ln)})
                largos[m].append(len(vals))

        for pid, fila in jugadores.items():
            acumulado[pid].append(fila)

    return {m: (filas[m], largos[m]) for m in METRICAS}


def escribir(por_metrica, destino=DESTINO):
    salida = {}
    for met, (fs, lg) in (por_metrica or {}).items():
        r = resumen(fs, lg)
        if r:
            salida[met] = r
    if not salida:
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(
        {"actualizado": datetime.date.today().isoformat(),
         "metricas": salida}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    return destino


def main():
    hist = historia()
    print(f"\npartidos con estadística por jugador: {len(hist)}")
    if len(hist) < 20:
        print("  muestra insuficiente para medir nada.\n")
        return
    print(f"  del {hist[0][0]} al {hist[-1][0]}\n")

    por_metrica = evaluar(hist)
    print(f"{'métrica':11} {'n':>5} {'dice':>7} {'pasa':>7} {'desvío':>8} "
          f"{'ruido':>7} {'razón':>7}  veredicto")
    for m in METRICAS:
        fs, lg = por_metrica[m]
        r = resumen(fs, lg)
        if not r:
            print(f"{m:11} {len(fs):5}   (sin muestra)")
            continue
        dice = sum(x["p"] for x in fs) / len(fs) * 100
        pasa = sum(x["paso"] for x in fs) / len(fs) * 100
        print(f"{m:11} {r['n']:5} {dice:6.1f}% {pasa:6.1f}% {r['desvio']:8.1f} "
              f"{r['ruido']:7.1f} {r['razon']:7.2f}  {r['nivel']}")

    print("\n  El ruido es el desvío que mostraría un modelo PERFECTO con")
    print("  esta misma cantidad de casos. La razón es desvío/ruido: es el")
    print("  número que decide, no el desvío suelto.\n")

    # La línea que se ofrece no es un detalle: si siempre es 0.5, la app
    # contesta una pregunta distinta de la que hace la casa.
    for m in ("remates", "al_arco"):
        fs, _ = por_metrica[m]
        if not fs:
            continue
    destino = escribir(por_metrica)
    if destino:
        print(f"  escrito: {destino}\n")


if __name__ == "__main__":
    main()
