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
import json
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

# El umbral ya elegido vive en `expediente.py`, que es quien lo aplica.
# Acá se importa solo para el censo (`--censo`), que cuenta cuántos
# partidos de la grilla actual lo superan.
try:
    from expediente import UMBRAL_SENAL
except ImportError:                                          # noqa: BLE001
    UMBRAL_SENAL = None


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


def transferencia():
    """¿La regla calibrada en Europa se comporta razonable en arg/bra?

    El umbral salió de 20.897 partidos de seis ligas europeas. Nada
    garantiza que valga en Sudamérica, y tratarlo como si valiera sería
    exactamente el tipo de supuesto que este repo ya pagó caro otras
    veces. Acá se aplica la regla EXACTAMENTE como está congelada — sin
    tocar un umbral para que arg/bra encajen mejor.

    El corpus es `cache_disciplina.json`: los resúmenes por partido que
    el cron ya venía guardando de ESPN, con remates, córners, faltas y
    tarjetas de cada equipo. Son 321 partidos, 121 de arg.1 y 55 de
    bra.1 — demasiado poco para ELEGIR un umbral y quizás suficiente
    para ver si el que hay se rompe.

    Dos supuestos, los dos verificados y los dos declarados:

    · el orden de las claves de cada partido es local, visitante —
      comprobado contra `historial_pronosticos.json`, 66 de 66;
    · el id de ESPN ordena por fecha dentro de una liga — 5 inversiones
      en 34 partidos con fecha conocida, y todas entre partidos de la
      misma jornada, donde el orden no cambia nada.
    """
    disc = cargar_json(RAIZ / "data" / "cache_disciplina.json") or {}
    grilla = cargar_json(RAIZ / "data" / "partidos.json") or {}
    grilla = grilla.get("partidos") if isinstance(grilla, dict) else grilla

    liga_de = {}
    for p in grilla or []:
        liga_de[str(p.get("homeId"))] = p.get("liga")
        liga_de[str(p.get("awayId"))] = p.get("liga")

    porliga = defaultdict(list)
    for mid, v in sorted(disc.items()):
        if mid.startswith("_"):
            continue
        tids = [t for t in v if not t.startswith("_")]
        if len(tids) != 2:
            continue
        lg = {liga_de.get(t) for t in tids} - {None}
        if len(lg) != 1:
            continue
        porliga[next(iter(lg))].append((int(mid), tids[0], tids[1],
                                        v[tids[0]], v[tids[1]]))

    print()
    print("=" * 78)
    print("  ¿LA REGLA EUROPEA SE TRANSFIERE A ARGENTINA Y BRASIL?")
    print("=" * 78)
    print()
    print("  Regla CONGELADA, tal como quedó calibrada sobre 20.897 partidos")
    print("  europeos. No se tocó ningún umbral para este corpus.")

    todo = {}
    for lg in ("arg.1", "bra.1"):
        ps = sorted(porliga.get(lg, []))
        # La vara de liga se calcula dejando AFUERA el partido que se está
        # evaluando, no con una media corrida. Dos motivos: en producción
        # la vara sale de `estadisticas.json`, que es la media de la
        # temporada y no un acumulado walk-forward; y exigir 20 partidos
        # de calentamiento sobre un corpus de 121 se comía justo los
        # partidos donde los equipos llegan a n=6. Los promedios POR
        # EQUIPO siguen siendo estrictamente causales — esos son los que
        # tienen que serlo.
        tot = {m: [0.0, 0] for m in METRICAS}
        for _mid, _l, _v, sl, sv in ps:
            for met in METRICAS:
                gl, gv = sl.get(met), sv.get(met)
                if gl is not None and gv is not None:
                    tot[met][0] += gl + gv
                    tot[met][1] += 1

        filas = []
        acc = {m: Acumulador() for m in METRICAS}
        for _mid, loc, vis, sl, sv in ps:
            for met in METRICAS:
                gl, gv = sl.get(met), sv.get(met)
                if gl is None or gv is None:
                    continue
                a = acc[met]
                est = a.estimadores(loc, vis)
                suma, cuenta = tot[met]
                bar = (suma - (gl + gv)) / (cuenta - 1) if cuenta > 1 else None
                if est and bar:
                    e1, e2, e3, n = est
                    m = (e1 + e2 + e3) / 3
                    filas.append({
                        "met": met, "gap": m / bar - 1,
                        "spread": (max(e1, e2, e3) - min(e1, e2, e3)) / bar,
                        "n": n, "arriba": (gl + gv) > bar,
                    })
                a.sumar(loc, vis, gl, gv)
        todo[lg] = filas
        informe_transferencia(lg, len(ps), filas)

    juntos = todo.get("arg.1", []) + todo.get("bra.1", [])
    informe_transferencia("arg.1 + bra.1", None, juntos)
    print()
    return 0


def informe_transferencia(etiqueta, n_partidos, filas):
    """Una tabla por liga, con el veredicto de las tres opciones."""
    print()
    cab = f"  {etiqueta}"
    if n_partidos is not None:
        cab += f"   {n_partidos} partidos en el corpus"
    print(cab)
    if not filas:
        print("    sin casos evaluables (hace falta la ventana de 20 "
              "partidos que fija la vara)")
        return
    # El embudo importa más que la tabla: si la regla no llega a emitir,
    # hay que poder ver EN QUÉ CONDICIÓN se quedó, porque "cero señales"
    # por falta de muestra y "cero señales" porque nada pasa el gap son
    # dos diagnósticos distintos.
    print(f"    {'dimensión':>16} {'evalu.':>7} {'n ok':>6} {'+disp':>6} "
          f"{'+gap':>6} {'acierto':>8} {'base':>7} {'delta':>8} {'±ee':>7}")
    print("    " + "-" * 82)
    tot_o = tot_n = 0
    for met in METRICAS:
        um = UMBRAL_SENAL.get(met) if UMBRAL_SENAL else None
        hay = [f for f in filas if f["met"] == met]
        if not hay:
            continue
        if um is None:
            print(f"    {met:>16} {len(hay):>7} {'—':>6} {'—':>6} {'—':>6} "
                  f"{'no se afirma nunca':>32}")
            continue
        c_n = [f for f in hay if f["n"] >= um["n"]]
        c_d = [f for f in c_n if f["spread"] <= um["spread"]]
        us = [f for f in c_d if abs(f["gap"]) >= um["gap"]]
        arr = sum(f["arriba"] for f in hay) / len(hay)
        base = max(arr, 1 - arr)
        if not us:
            print(f"    {met:>16} {len(hay):>7} {len(c_n):>6} {len(c_d):>6} "
                  f"{0:>6} {'—':>8} {base:>6.1%} {'—':>8} {'—':>7}")
            continue
        o = sum(1 for f in us if (f["gap"] > 0) == f["arriba"])
        p = o / len(us)
        e = ee(p, len(us))
        tot_o += o
        tot_n += len(us)
        print(f"    {met:>16} {len(hay):>7} {len(c_n):>6} {len(c_d):>6} "
              f"{len(us):>6} {p:>7.1%} {base:>6.1%} {p - base:>+7.1%} "
              f"{e:>6.1%}")
    if tot_n:
        p = tot_o / tot_n
        e = ee(p, tot_n)
        print(f"    {'TOTAL':>16} {'':>7} {'':>6} {'':>6} {tot_n:>6} "
              f"{p:>7.1%} {'':>6} {'':>8} {e:>6.1%}")
    p = tot_o / tot_n if tot_n else 0.0
    print()
    print(f"    veredicto: {veredicto_transferencia(tot_n, p, ee(p, tot_n))}")


def veredicto_transferencia(n, p, e):
    """Una de las tres, y la tercera es la respuesta honesta casi siempre.

    Con ~20 señales el error estándar ronda los 11 puntos: para separar
    'compatible' de 'incompatible' harían falta unas 150. Este umbral
    existe para que un resultado chico no se lea como conclusión.
    """
    if n == 0:
        return ("MUESTRA INSUFICIENTE PARA CONCLUIR — la regla no llegó a "
                "emitir ni una señal en este corpus. No es que falle: no "
                "se la puede probar acá.")
    if n < 60:
        return (f"MUESTRA INSUFICIENTE PARA CONCLUIR — {n} señales, "
                f"±{e:.1%}. Hacen falta ~150 para separar compatible de "
                f"incompatible.")
    if p - 1.96 * e > 0.50:
        return "COMPATIBLE CON TRANSFERENCIA"
    if p + 1.96 * e < 0.50:
        return "INCOMPATIBLE CON TRANSFERENCIA — acierta por debajo del azar"
    return "MUESTRA INSUFICIENTE PARA CONCLUIR — el intervalo cruza el 50%"


def cargar_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return None


def censo():
    """Cuánta evidencia hay HOY, liga por liga y dimensión por dimensión.

    La pregunta que contesta, y que Lucas hizo antes de gastar research:
    ¿cuántos partidos de la grilla pueden producir algo distinto de
    `null`? Si la respuesta es "casi ninguno", correr diez análisis no
    junta información sobre la señal — junta `null`.

    No mira ninguna salida de la skill. Solo el expediente, que es quien
    aplica el umbral, y `estadisticas.json`, de donde sale `n`.

    Ojo con la lectura: el umbral está calibrado sobre ligas europeas.
    Que arg.1 y bra.1 tengan material suficiente NO significa que el
    10%/20% funcione igual ahí — eso es una hipótesis de transferencia
    y hay que validarla aparte.
    """
    import expediente as X

    partidos = X.cargar()
    ligas = sorted({p.get("liga") for p in partidos if p.get("liga")})
    dims = ("corners_total", "faltas", "volumen_remates", "tarjetas")
    de_dim = {"corners_total": "corners", "faltas": "faltas",
              "volumen_remates": "remates", "tarjetas": "tarjetas"}

    print()
    print("=" * 78)
    print("  CENSO DE EVIDENCIA — qué puede producir el instrumento hoy")
    print("=" * 78)
    print()
    print("  El umbral se calibró sobre ligas europeas. Su transferencia a")
    print("  arg/bra es una HIPÓTESIS, no una regla demostrada.")

    for liga in ligas:
        ps = [p for p in partidos if p.get("liga") == liga]
        filas = []
        for p in ps:
            try:
                e = X.expediente(p, grilla=partidos)
            except Exception:                                # noqa: BLE001
                continue
            if e.get("senal_base"):
                filas.append((p, e["senal_base"], e))
        print()
        if not filas:
            print(f"  {liga:<24} {len(ps):>3} partidos · sin métricas medidas "
                  f"de los dos equipos")
            continue

        print(f"  {liga}   {len(ps)} partidos en la grilla, "
              f"{len(filas)} con métricas de los dos")
        print(f"    {'dimensión':>16} {'n>=6':>6} {'+disp':>6} {'+gap':>6} "
              f"{'AFIRMA':>8}   {'n mediano':>10}")
        print("    " + "-" * 62)
        for d in dims:
            um = UMBRAL_SENAL.get(de_dim[d]) if UMBRAL_SENAL else None
            hay = [f[1][d] for f in filas if d in f[1]]
            if not hay:
                continue
            ns = sorted(h["n"] for h in hay)
            tip = ns[len(ns) // 2]
            if um is None:
                print(f"    {d:>16} {'-':>6} {'-':>6} {'-':>6} {'nunca':>8}"
                      f"   {tip:>10}")
                continue
            c_n = [h for h in hay if h["n"] >= um["n"]]
            c_d = [h for h in c_n if h["dispersion"] <= um["spread"]]
            c_g = [h for h in c_d if abs(h["gap"]) >= um["gap"]]
            print(f"    {d:>16} {len(c_n):>6} {len(c_d):>6} {len(c_g):>6} "
                  f"{len(c_g):>8}   {tip:>10}")

        # `generador` es otro eje: no pasa por estadisticas.json ni por el
        # umbral de volumen, así que se cuenta aparte.
        g = sum(1 for _p, _sb, e in filas for l in ("H", "A")
                if (e.get("liderazgo" + l) or {}).get("ventaja", 0) >= 0.50)
        print(f"    {'generador':>16} {'':>6} {'':>6} {'':>6} {g:>8}"
              f"   (de {len(filas) * 2} equipos)")

        vivos = 0
        for _p, sb, e in filas:
            vol = any((sb.get(d) or {}).get("fallo") for d in dims)
            gen = any((e.get("liderazgo" + l) or {}).get("ventaja", 0) >= 0.50
                      for l in ("H", "A"))
            vivos += 1 if (vol or gen) else 0
        print(f"    -> {vivos} de {len(filas)} partidos pueden producir al "
              f"menos una afirmación")
    print()
    return 0


def main():
    args = sys.argv[1:]
    if "--censo" in args:
        return censo()
    if "--transferencia" in args:
        return transferencia()
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
