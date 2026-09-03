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

    # ── Capa 2 y 3 ───────────────────────────────────────────────────
    print(f"\n{'─'*74}\n  CAPA 2 y 3 — ¿se verifica, y aporta sobre el modelo?"
          f"\n{'─'*74}\n")
    print("  Sin resultados cargados para estos partidos todavía no se")
    print("  puede resolver. Volvé a correrlo cuando el cron los cierre.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
