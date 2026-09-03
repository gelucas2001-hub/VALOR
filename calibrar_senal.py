#!/usr/bin/env python3
"""¿A partir de qué diferencia se puede afirmar "muchos" o "pocos"?

POR QUÉ EXISTE

El esquema de `desarrollo.senal` (TRASPASO §33) le puso a `generador` un
umbral explícito —liderar por 50%— y a las cuatro dimensiones de volumen
no le puso ninguno. En el primer smoke test (§34) eso produjo una
inconsistencia dentro de la misma tanda: córners a +16% de la media de
liga se declararon `null` y faltas a +11% se declararon "muchas". Sin
umbral, el corte lo pone el criterio del momento y no es reproducible.

LO QUE ESTE SCRIPT NO HACE

No mira los cuatro partidos del smoke test, y no puede: corre sobre
football-data (temporadas 2015/16 a 2025/26 de seis ligas europeas) y
los partidos de la tanda son de septiembre de 2026. La condición que
puso Lucas es explícita — el umbral no se elige mirando la muestra que
después se va a evaluar — y la única forma de cumplirla es calibrar
contra historial disjunto.

QUÉ MIDE

La pregunta operativa: con los promedios que la app tiene ANTES del
partido, ¿a partir de qué distancia de la media de liga acertamos el
lado (por encima / por debajo) más seguido que tirando una moneda?

Walk-forward dentro de cada temporada: para cada partido, los promedios
salen solo de los partidos ANTERIORES de esa misma temporada. Nunca se
usa el partido que se está prediciendo, ni los que vienen después.

Los tres estimadores son los mismos que tiene el expediente:

    E1 produce   lo que cada equipo produce, sumado
    E2 sede      lo del local en casa + lo del visitante afuera
    E3 cruzado   cada lado promediado contra lo que concede el rival

Se reportan dos cortes, porque son dos reglas distintas:

  · |gap| contra la media de liga  — cuánta diferencia hace falta
  · dispersión entre los tres estimadores — cuándo se contradicen y
    hay que callarse aunque el gap sea grande

TRAIN / TEST

Train: temporadas 15/16 a 22/23. Test: 23/24 a 25/26. El umbral se elige
en train y se reporta en test. Un umbral que solo funciona en train no
es un umbral, es una descripción del pasado.

    python calibrar_senal.py
    python calibrar_senal.py --liga E0
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ / "data" / "cache_historico"

# Las seis de football-data que traen estadística por partido. Las otras
# (N1, B1, P1, T1, ARG, BRA) vienen sin ella — es la misma asimetría de
# fuente que documenta `historico.py`.
LIGAS = ("E0", "F1", "D1", "I1", "SP1", "SC0")

TEMPORADAS = ("1516", "1617", "1718", "1819", "1920", "2021",
              "2122", "2223", "2324", "2425", "2526")
TRAIN = TEMPORADAS[:8]          # 15/16 .. 22/23
TEST = TEMPORADAS[8:]           # 23/24 .. 25/26

# métrica -> (columna local, columna visitante) sumadas para el total.
METRICAS = {
    "corners":  (("HC",), ("AC",)),
    "faltas":   (("HF",), ("AF",)),
    "tarjetas": (("HY", "HR"), ("AY", "AR")),
    "remates":  (("HS",), ("AS",)),
}

# Cuántos partidos previos necesita un equipo para que su promedio entre
# en la cuenta. Es el eje que el smoke test dejó abierto junto con el
# umbral, así que se barre igual que los demás.
MIN_N = (3, 4, 5, 6, 8)

CORTES_GAP = (0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
CORTES_SPREAD = (0.10, 0.15, 0.20, 0.30, 0.50, 9.9)


def num(fila, col):
    v = (fila.get(col) or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def total(fila, cols_l, cols_v):
    vals = [num(fila, c) for c in cols_l + cols_v]
    return None if any(v is None for v in vals) else sum(vals)


def lado(fila, cols):
    vals = [num(fila, c) for c in cols]
    return None if any(v is None for v in vals) else sum(vals)


def partidos_de(liga, temporada):
    p = CACHE / f"{liga}-{temporada}.csv"
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f)
                if (r.get("HomeTeam") or "").strip()]


class Acumulador:
    """Lo que cada equipo lleva hecho y concedido en la temporada.

    Se actualiza DESPUÉS de usar el partido, nunca antes: esa es toda la
    disciplina walk-forward que hace falta acá.
    """

    def __init__(self):
        self.prod = defaultdict(lambda: [0.0, 0])     # suma, n
        self.conc = defaultdict(lambda: [0.0, 0])
        self.prod_loc = defaultdict(lambda: [0.0, 0])
        self.prod_vis = defaultdict(lambda: [0.0, 0])
        self.liga = [0.0, 0]

    @staticmethod
    def _m(par):
        return None if par[1] == 0 else par[0] / par[1]

    def estimadores(self, loc, vis):
        """(E1, E2, E3, n_min) o None si a alguno le falta muestra."""
        pl, pv = self._m(self.prod[loc]), self._m(self.prod[vis])
        cl, cv = self._m(self.conc[loc]), self._m(self.conc[vis])
        sl, sv = self._m(self.prod_loc[loc]), self._m(self.prod_vis[vis])
        if None in (pl, pv, cl, cv):
            return None
        # Sin muestra de sede, el split cae al promedio general en vez de
        # descartar el partido: es lo que hace el expediente cuando
        # `local`/`visita` no vienen.
        sl = pl if sl is None else sl
        sv = pv if sv is None else sv
        e1 = pl + pv
        e2 = sl + sv
        e3 = (sl + cv) / 2 + (sv + cl) / 2
        n = min(self.prod[loc][1], self.prod[vis][1])
        return e1, e2, e3, n

    def bar(self):
        return self._m(self.liga)

    def sumar(self, loc, vis, gl, gv):
        self.prod[loc][0] += gl; self.prod[loc][1] += 1
        self.prod[vis][0] += gv; self.prod[vis][1] += 1
        self.conc[loc][0] += gv; self.conc[loc][1] += 1
        self.conc[vis][0] += gl; self.conc[vis][1] += 1
        self.prod_loc[loc][0] += gl; self.prod_loc[loc][1] += 1
        self.prod_vis[vis][0] += gv; self.prod_vis[vis][1] += 1
        self.liga[0] += gl + gv; self.liga[1] += 1


def recolectar(ligas, temporadas):
    """Una fila por (partido, métrica) con lo que hace falta para decidir."""
    filas = []
    for liga in ligas:
        for temp in temporadas:
            ps = partidos_de(liga, temp)
            if not ps:
                continue
            acc = {m: Acumulador() for m in METRICAS}
            for fila in ps:
                loc = fila["HomeTeam"].strip()
                vis = fila["AwayTeam"].strip()
                for met, (cl, cv) in METRICAS.items():
                    gl, gv = lado(fila, cl), lado(fila, cv)
                    if gl is None or gv is None:
                        continue
                    a = acc[met]
                    est = a.estimadores(loc, vis)
                    bar = a.bar()
                    # La media de liga también se estima con lo corrido:
                    # con menos de 20 partidos es demasiado inestable
                    # para servir de vara.
                    if est and bar and a.liga[1] >= 20:
                        e1, e2, e3, n = est
                        m = (e1 + e2 + e3) / 3
                        filas.append({
                            "liga": liga, "temp": temp, "met": met,
                            "gap": m / bar - 1,
                            "spread": (max(e1, e2, e3) - min(e1, e2, e3)) / bar,
                            "n": n,
                            "arriba": (gl + gv) > bar,
                        })
                    a.sumar(loc, vis, gl, gv)
    return filas


def acierto(filas, gap_min, spread_max, n_min):
    """Sobre las filas que la regla dejaría afirmar, cuántas acierta."""
    ok = tot = 0
    for f in filas:
        if abs(f["gap"]) < gap_min or f["spread"] > spread_max:
            continue
        if f["n"] < n_min:
            continue
        tot += 1
        if (f["gap"] > 0) == f["arriba"]:
            ok += 1
    return ok, tot


def ee(p, n):
    return 0.0 if n == 0 else (p * (1 - p) / n) ** 0.5


def informe(tr, te, met=None):
    if met:
        tr = [f for f in tr if f["met"] == met]
        te = [f for f in te if f["met"] == met]
    base_tr = sum(f["arriba"] for f in tr) / len(tr) if tr else 0
    print(f"\n  train {len(tr):>6} casos   ·   test {len(te):>6} casos"
          f"   ·   tasa base (por encima de la vara) {base_tr:.1%}")

    print(f"\n  {'gap min':>8} {'spread max':>10} {'n min':>6} "
          f"| {'train %':>8} {'usa':>6} | {'test %':>8} {'usa':>6} {'ee':>6}")
    print("  " + "-" * 74)
    mejor = None
    for nm in MIN_N:
        for sp in CORTES_SPREAD:
            for g in CORTES_GAP:
                o1, t1 = acierto(tr, g, sp, nm)
                if t1 < 400:                     # sin muestra no se elige
                    continue
                p1 = o1 / t1
                o2, t2 = acierto(te, g, sp, nm)
                p2 = o2 / t2 if t2 else 0
                cob = t1 / len(tr) if tr else 0
                # Se elige en TRAIN. El test solo se reporta.
                if cob >= 0.05 and (mejor is None or p1 > mejor[0]):
                    mejor = (p1, g, sp, nm, p2, t2, cob)
    for nm in MIN_N:
        for sp in CORTES_SPREAD:
            for g in CORTES_GAP:
                o1, t1 = acierto(tr, g, sp, nm)
                o2, t2 = acierto(te, g, sp, nm)
                if t1 < 400 or t1 / len(tr) < 0.05:
                    continue
                p1, p2 = o1 / t1, (o2 / t2 if t2 else 0)
                marca = ""
                if mejor and (g, sp, nm) == (mejor[1], mejor[2], mejor[3]):
                    marca = "  <- mejor en train"
                sp_txt = "sin tope" if sp > 9 else f"{sp:.0%}"
                print(f"  {g:>7.0%} {sp_txt:>10} {nm:>6} "
                      f"| {p1:>7.1%} {t1:>6} | {p2:>7.1%} {t2:>6} "
                      f"{ee(p2, t2):>5.1%}{marca}")
    return mejor


def main():
    args = sys.argv[1:]
    ligas = LIGAS
    if "--liga" in args:
        ligas = (args[args.index("--liga") + 1],)

    print("\n" + "=" * 78)
    print("  ¿DESDE QUÉ DIFERENCIA SE PUEDE AFIRMAR EL VOLUMEN DE UN PARTIDO?")
    print("=" * 78)
    print(f"\n  ligas: {', '.join(ligas)}")
    print(f"  train: {TRAIN[0]}..{TRAIN[-1]}   test: {TEST[0]}..{TEST[-1]}")
    print("  Ningún partido del smoke test entra acá: son de septiembre 2026.")

    tr = recolectar(ligas, TRAIN)
    te = recolectar(ligas, TEST)
    if not tr or not te:
        print("\n  Sin datos. ¿Está data/cache_historico poblado?")
        return 1

    elegidos = {}
    for met in METRICAS:
        print(f"\n{'─' * 78}\n  {met.upper()}\n{'─' * 78}")
        m = informe(tr, te, met)
        if m:
            elegidos[met] = m

    print(f"\n{'=' * 78}\n  RESUMEN — el umbral elegido en train, medido en test\n{'=' * 78}\n")
    print(f"  {'métrica':>10} {'gap':>6} {'spread':>8} {'n':>4} "
          f"{'test':>8} {'ee':>6} {'casos':>7}")
    print("  " + "-" * 56)
    for met, (_p1, g, sp, nm, p2, t2, _c) in elegidos.items():
        sp_txt = "sin tope" if sp > 9 else f"{sp:.0%}"
        print(f"  {met:>10} {g:>5.0%} {sp_txt:>8} {nm:>4} "
              f"{p2:>7.1%} {ee(p2, t2):>5.1%} {t2:>7}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
