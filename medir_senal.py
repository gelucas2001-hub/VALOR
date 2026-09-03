#!/usr/bin/env python3
"""¿La lectura futbolística aporta algo que los números no saben?

Tres capas, y son tres preguntas distintas que Lucas pidió separadas:

  1. LECTURA        ¿la skill puede hacer una afirmación concreta?
  2. VERIFICACIÓN   ¿podemos comprobar objetivamente si ocurrió?
  3. VALOR INCREMENTAL  ¿aporta algo que el modelo no sabía ya?

La tercera es la que importa. Una afirmación puede acertar y ser inútil:
si el modelo ya lo sabía, la lectura no agregó nada. Eso fue exactamente
lo que pasó con el esquema viejo (§33).

POR QUÉ CAMBIÓ EL ESQUEMA

El `senal` original tenía `ritmo_goleador`, `estructura` y
`ambos_marcan`. Los tres describen cuántos goles va a haber, que es
literalmente lo que λ calcula. Medido sobre los 9 análisis que lo
traían: acertaron 4 de 4 en las afirmaciones que se comprometieron, y
los dos partidos que llamaron "de pocos goles" eran exactamente los dos
de λ más bajo del conjunto. La lectura acertaba repitiendo al modelo.

El esquema nuevo sale de medir, sobre 12.095 partidos, qué correlación
tiene λ con cada cosa que la lectura podría afirmar:

    diferencia de remates   +0.459   λ ya lo sabe
    diferencia de córners   +0.345   λ ya lo sabe
    TOTAL de córners        +0.077   ortogonal
    TOTAL de tarjetas       -0.110   ortogonal
    TOTAL de remates        +0.177   parcial

λ encoda la ASIMETRÍA del partido, no su VOLUMEN. Por eso las señales
nuevas son sobre totales y sobre jugadores, no sobre quién domina.

OJO CON LO QUE LA ORTOGONALIDAD **NO** PRUEBA

Que una dimensión sea independiente de λ es condición NECESARIA para que
pueda aportar información nueva. No es prueba de que la aporte: una
señal puede ser perfectamente ortogonal y ser ruido perfecto. La
ortogonalidad dice que el modelo no lo sabe, no que la lectura sí.

`generador` es el caso más claro. Es ortogonal por construcción —λ no
tiene eje de jugador— y eso no le da ninguna ventaja: puede terminar
acertando al nivel de tirar una moneda entre los tres delanteros. La
capa 3 existe para eso, y ninguna dimensión entra al motor sin pasarla.

LO QUE EL INFORME TIENE QUE PODER CONTESTAR, con muestra

  · qué dimensiones usa la IA y cuáles evita (y `null` es válido)
  · cuántas afirmaciones resultaron verificables
  · tasa de acierto POR DIMENSIÓN, con su n al lado
  · si ese acierto supera al pronóstico numérico de la misma métrica

Si una dimensión no tiene sentido, es redundante o está mal definida,
se cambia. El diseño no se defiende por haberlo implementado.

QUÉ ESPERAR HOY

Nada. Cero análisis tienen el esquema nuevo, porque se estrenó el
2026-09-03. Ese es el punto: el reloj de este instrumento solo arranca
cuando se lo enciende, y los otros caminos abiertos usan datos
históricos que ya existen y pueden esperar.

Con 100 o 200 análisis esto contesta: **qué tipos de lectura aporta
VALOR que los modelos numéricos no capturan.** Eso vale más que saber
si la IA acierta.

    python medir_senal.py
"""

import json
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent

# Cada señal: cómo se resuelve y contra qué baseline se mide su aporte.
# El baseline NO es λ: es lo que el modelo numérico ya predice para esa
# misma métrica. Para córners eso es `estadisticas.json`, que tiene el
# promedio por equipo. Comparar contra λ sería fácil y tramposo — λ no
# predice córners y cualquier cosa le ganaría.
SENALES = {
    "corners_total":   {"met": "corners",  "valores": ("muchos", "pocos")},
    "faltas":          {"met": "faltas",   "valores": ("muchas", "pocas")},
    "tarjetas":        {"met": "tarjetas", "valores": ("muchas", "pocas")},
    "volumen_remates": {"met": "remates",  "valores": ("alto", "bajo")},
}

# El umbral de cada dimensión sale de `calibrar_senal.py` y vive en
# `expediente.py`, que es quien lo aplica. Acá se importa para poder
# AUDITAR: una afirmación que no cumplía su propio umbral es un error
# del instrumento, no un fallo de pronóstico, y hay que poder separarlos
# antes de medir acierto. Sin esto la regla es disciplina; con esto es
# estructura — el mismo argumento que sostiene a `test_ejes.js`.
try:
    from expediente import UMBRAL_SENAL, CAMPO_SENAL
except ImportError:                                          # noqa: BLE001
    UMBRAL_SENAL = CAMPO_SENAL = None


def generadores(senal):
    """La lista de generadores, tolerando el objeto único de la v1.

    `generador` nació como un objeto y pasó a lista el 2026-09-03: con
    un solo lugar, dos jugadores que superaban el umbral obligaban a
    elegir uno a dedo, que es el volado que el umbral existe para
    evitar. Los análisis viejos siguen leyéndose.
    """
    g = senal.get("generador")
    if not g:
        return []
    return list(g) if isinstance(g, list) else [g]


def leer(nombre, defecto=None):
    p = RAIZ / "data" / nombre
    if not p.exists():
        return defecto
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return defecto


def esquema_de(senal):
    """'nuevo', 'viejo' o None. Sirve para no mezclar dos instrumentos."""
    if not isinstance(senal, dict):
        return None
    if set(senal) & {"corners_total", "faltas", "tarjetas",
                     "volumen_remates", "generador"}:
        return "nuevo"
    if set(senal) & {"ritmo_goleador", "estructura", "ambos_marcan"}:
        return "viejo"
    return None


# La tasa base de cada dimensión, medida en Europa por
# `calibrar_senal.py`. Viaja acá SOLO como referencia impresa: la vara
# con la que se juzga la muestra sudamericana es la que se observa en
# ella misma, y las dos se muestran juntas justamente porque pueden no
# coincidir. Ver TRASPASO §37 y §39.
BASE_EUROPA = {"faltas": 0.541, "volumen_remates": 0.512,
               "corners_total": 0.520, "tarjetas": 0.569}

# `_jugadores` de cache_disciplina.json es
# [remates, al_arco, faltas, amarillas, goles, asist, titular] — el orden
# lo fija `jugadores_partido()` en actualizar.py. `generador` afirma
# sobre remates, que es la posición 0.
IDX_REMATES = 0


def resolver_volumen(ev, campo, real):
    """¿La afirmación ocurrió? Contra la vara SELLADA, no una recalculada.

    Esto es lo que C3 (§36) vino a habilitar. `estadisticas.json` se
    sobrescribe, así que la vara con la que se afirmó ya no existe en
    ningún lado salvo en `desarrollo.evidencia`. Recalcularla hoy usaría
    un promedio que incluye el partido que estamos verificando.
    """
    base = (ev.get("senal_base") or {}).get(campo) or {}
    vara, fallo = base.get("vara"), base.get("fallo")
    if vara is None or fallo is None or real is None:
        return None
    arriba = fallo in ("muchos", "muchas", "alto")
    return (real > vara) == arriba


def equipo_de(pid, planteles, ids):
    for tid in ids:
        if any(str(j.get("id")) == str(pid) for j in planteles.get(tid) or []):
            return tid
    return None


def resolver_generador(g, partido, planteles, ids_por_lado):
    """¿El jugador nombrado lideró los remates de su equipo ESE partido?

    Devuelve (acertó, motivo). El motivo importa tanto como el acierto:
    un `None` por "no lo encontramos en el plantel" no es un fallo del
    pronóstico y no puede contar como tal.
    """
    jug = (partido or {}).get("_jugadores") or {}
    if not jug:
        return None, "el partido no tiene estadística por jugador"
    tid = ids_por_lado.get(g.get("equipo"))
    if not tid:
        return None, "no se pudo identificar el equipo"
    plantel = planteles.get(tid) or []
    ids = {str(j.get("id")): j.get("nombre") for j in plantel}
    objetivo = next((i for i, n in ids.items()
                     if n == g.get("jugador")), None)
    if not objetivo:
        return None, f"{g.get('jugador')} no está en el plantel cacheado"
    propios = {i: v for i, v in jug.items() if i in ids}
    if objetivo not in propios:
        return False, "el jugador nombrado no jugó el partido"
    tope = max(v[IDX_REMATES] for v in propios.values())
    return propios[objetivo][IDX_REMATES] >= tope, ""


def ee_prop(p, n):
    return 0.0 if n <= 0 else (p * (1 - p) / n) ** 0.5


def capa_dos(nuevos):
    """¿Las afirmaciones ocurrieron? Nada más que eso.

    No compara contra el modelo —eso sería la capa 3, y §39 midió que
    con este diseño no se puede— ni recalibra nada. Resuelve cada señal
    contra la fotografía que quedó sellada y contra lo que el cron
    guardó del partido.
    """
    print(f"\n{'─'*74}\n  CAPA 2 — ¿ocurrió lo que la señal afirmó?\n{'─'*74}")

    res = leer("resultados.json", {}) or {}
    disc = leer("cache_disciplina.json", {}) or {}
    planteles = (leer("planteles.json", {}) or {}).get("equipos") or {}

    sin_sello, sin_jugar, sin_datos = [], [], []
    por_dim = {c: {"ok": 0, "n": 0} for c in SENALES}
    por_dim["generador"] = {"ok": 0, "n": 0}
    por_liga = {}
    base_obs = {c: {"arriba": 0, "n": 0} for c in SENALES}
    notas = []

    for pid, sen in nuevos:
        ev = ((leer("analisis.json", {}) or {}).get(pid, {})
              .get("desarrollo") or {}).get("evidencia")
        if not ev:
            sin_sello.append(pid)
            continue
        if pid not in res:
            sin_jugar.append(pid)
            continue
        crudo = disc.get(pid.replace("espn", ""))
        if not crudo:
            sin_datos.append(pid)
            continue
        tids = [t for t in crudo if not t.startswith("_")]
        if len(tids) != 2:
            sin_datos.append(pid)
            continue
        # El orden de las claves es local, visitante — verificado 66/66
        # contra historial_pronosticos.json (§38).
        ids_por_lado = {"local": tids[0], "visitante": tids[1]}
        liga = None
        for t in tids:
            for j in planteles.get(t) or []:
                liga = liga or j.get("liga")

        for campo, meta in SENALES.items():
            m = meta["met"]
            real = sum((crudo[t] or {}).get(m) or 0 for t in tids) \
                if all((crudo[t] or {}).get(m) is not None for t in tids) else None
            base = (ev.get("senal_base") or {}).get(campo) or {}
            if real is not None and base.get("vara") is not None:
                base_obs[campo]["n"] += 1
                base_obs[campo]["arriba"] += 1 if real > base["vara"] else 0
            if not sen.get(campo):
                continue
            ok = resolver_volumen(ev, campo, real)
            if ok is None:
                notas.append(f"{pid} {campo}: sin dato del partido")
                continue
            por_dim[campo]["n"] += 1
            por_dim[campo]["ok"] += 1 if ok else 0
            d = por_liga.setdefault(liga or "?", {"ok": 0, "n": 0})
            d["n"] += 1
            d["ok"] += 1 if ok else 0

        for g in generadores(sen):
            ok, motivo = resolver_generador(g, crudo, planteles, ids_por_lado)
            if ok is None:
                notas.append(f"{pid} generador: {motivo}")
                continue
            por_dim["generador"]["n"] += 1
            por_dim["generador"]["ok"] += 1 if ok else 0
            d = por_liga.setdefault(liga or "?", {"ok": 0, "n": 0})
            d["n"] += 1
            d["ok"] += 1 if ok else 0

    emitidas = sum(1 for _k, s in nuevos
                   for c in SENALES if s.get(c)) + \
        sum(len(generadores(s)) for _k, s in nuevos)
    resueltas = sum(d["n"] for d in por_dim.values())
    print(f"\n  {emitidas} señales emitidas · {resueltas} resueltas")
    if sin_sello:
        print(f"  {len(sin_sello)} análisis SIN evidencia sellada — no se "
              f"pueden resolver (ver `expediente.py --sellar`)")
    if sin_jugar:
        print(f"  {len(sin_jugar)} partidos todavía sin jugar")
    if sin_datos:
        print(f"  {len(sin_datos)} jugados pero sin estadística cacheada")

    if not resueltas:
        print("\n  Todavía no hay nada que resolver. El instrumento está")
        print("  completo: cuando el cron cierre los partidos, esto los lee.\n")
        return

    print(f"\n  {'dimensión':>16} {'n':>4} {'ok':>4} {'fallos':>7} "
          f"{'acierto':>8} {'base obs':>9} {'base eur':>9} {'delta':>7} {'±ee':>7}")
    print("  " + "-" * 82)
    for dim, d in por_dim.items():
        if not d["n"]:
            continue
        p = d["ok"] / d["n"]
        bo = base_obs.get(dim)
        # La tasa base se muestra en el mismo sentido que el acierto: la
        # frecuencia del lado más común entre los partidos con evidencia.
        if bo and bo["n"]:
            arr = bo["arriba"] / bo["n"]
            b = max(arr, 1 - arr)
            btxt = f"{b:>8.1%}"
        else:
            b, btxt = None, "       —"
        be = BASE_EUROPA.get(dim)
        betxt = f"{be:>8.1%}" if be else "       —"
        dtxt = f"{p-b:>+6.1%}" if b is not None else "      —"
        print(f"  {dim:>16} {d['n']:>4} {d['ok']:>4} {d['n']-d['ok']:>7} "
              f"{p:>7.1%} {btxt} {betxt} {dtxt} {ee_prop(p, d['n'])*2:>6.1%}")

    if len(por_liga) > 1:
        print(f"\n  por liga")
        for lg, d in sorted(por_liga.items()):
            p = d["ok"] / d["n"]
            print(f"    {lg:>10} {d['n']:>4} señales  {p:>6.1%} "
                  f"±{ee_prop(p, d['n'])*200:.1f}")

    print("\n  El ± son dos errores estándar. Con menos de ~60 señales por")
    print("  dimensión esto NO concluye — ver la potencia en TRASPASO §39.")
    for n in notas[:8]:
        print(f"    - {n}")
    print()


def capa_tres():
    print(f"{'─'*74}\n  CAPA 3 — el aporte incremental\n{'─'*74}\n")
    print("  No se implementa, y no es por falta de muestra (§39).")
    print()
    print("  Desde §34 las cuatro dimensiones de volumen no las decide la")
    print("  lectura: el expediente calcula `senal_base` desde")
    print("  estadisticas.json, aplica el umbral y entrega el fallo, y la")
    print("  skill lo copia. Señal y baseline salen del MISMO insumo, así")
    print("  que el aporte incremental es cero por construcción. Ninguna")
    print("  cantidad de datos lo cambia.")
    print()
    print("  Lo que la capa 2 sí contesta, y es una pregunta real: si el")
    print("  umbral calibrado en Europa transfiere a Sudamérica.")
    print()


def main():
    an = leer("analisis.json", {}) or {}
    an.pop("_schema", None)
    est = (leer("estadisticas.json", {}) or {}).get("equipos") or {}

    con = {}
    for k, v in an.items():
        s = (v.get("desarrollo") or {}).get("senal")
        e = esquema_de(s)
        if e:
            con.setdefault(e, []).append((k, s))

    print("\n" + "=" * 74)
    print("  ¿LA LECTURA APORTA ALGO QUE LOS NÚMEROS NO SABEN?")
    print("=" * 74)
    print(f"\n  {len(an)} análisis cargados")
    for e in ("nuevo", "viejo"):
        print(f"    esquema {e:>5}: {len(con.get(e, []))}")

    nuevos = con.get("nuevo", [])
    if not nuevos:
        print("\n  Todavía no hay análisis con el esquema nuevo.")
        print("  Se estrenó el 2026-09-03; el contador arranca con la")
        print("  próxima carga de `valor-analisis-inclinacion`.\n")
        print("  CAPA 1 — lectura: el esquema existe y acepta null.")
        print("  CAPA 2 — verificación: lista, contra estadisticas.json.")
        print("  CAPA 3 — valor incremental: pide muestra.\n")
        return 0

    # ── Capa 1: ¿cuántas afirmaciones concretas hay? ─────────────────
    print(f"\n{'─'*74}\n  CAPA 1 — ¿hace afirmaciones concretas?\n{'─'*74}\n")
    tot = {c: 0 for c in SENALES}
    gen = 0
    for _k, s in nuevos:
        for c in tot:
            if s.get(c) not in (None, "", {}):
                tot[c] += 1
        gen += len(generadores(s))
    for c, n in tot.items():
        nota = ""
        if UMBRAL_SENAL and UMBRAL_SENAL.get(SENALES[c]["met"]) is None:
            nota = "(no se afirma nunca — no supera su tasa base)"
        elif n < len(nuevos):
            nota = "(null es respuesta válida)"
        print(f"  {c:>18}  {n:>3}/{len(nuevos)}   {nota}")
    print(f"  {'generador':>18}  {gen:>3}      "
          f"(hasta uno por equipo, o sea hasta {len(nuevos) * 2})")

    afirmadas = sum(tot.values()) + gen
    print(f"\n  {afirmadas} afirmaciones sobre "
          f"{len(nuevos) * (len(SENALES) + 2)} casilleros posibles.")

    capa_dos(nuevos)
    capa_tres()
    return 0


if __name__ == "__main__":
    sys.exit(main())
