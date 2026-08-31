#!/usr/bin/env python3
"""¿Sabe el modelo de goles CONDICIONADO al resultado, si en general no?

De dónde sale: la idea del "escenario coherente" (TRASPASO §15). La
escalera elige mercado por mercado como si fueran independientes —
"gana Chelsea", "ambos marcan", "más de 2.5"— y tira la correlación que
la matriz de marcadores sí tiene. Antes de construir eso hay que
contestar la pregunta previa: `medir_ejes.py` ya midió que en el eje de
goles el modelo no aporta nada sobre la tasa base (entre −0.9% y +0.4%).
Pero "cuántos goles habrá" y "dado que gana el favorito, cuántos goles
suele haber" son preguntas distintas, y la segunda nunca se midió.

Cómo se mide. Para cada condición de resultado R se toman SOLO los
partidos donde R efectivamente pasó, y ahí se comparan tres pronósticos
del mercado de goles G:

  1. la tasa base condicionada — la frecuencia de G entre esos mismos
     partidos. Es la vara, y es dura a propósito: se calcula sobre el
     mismo subconjunto que se evalúa, así que sabe exactamente lo que
     hay que saber sin mirar el partido;
  2. el modelo SIN condicionar, P(G), que es lo que la app publica hoy;
  3. el modelo condicionado, P(G|R) = P(G∩R)/P(R), leído de la matriz.

La respuesta a la hipótesis es la diferencia (3) − (2): cuánto agrega
condicionar, sobre el mismo subconjunto y contra la misma vara. Se
acompaña de su error estándar por bootstrap pareado, porque al cortar
por resultado la muestra baja a un tercio y un aporte de dos puntos
puede ser ruido (regla del repo: comparar el error contra el ruido, no
contra cero).

Qué NO contesta: no dice si conviene apostar el escenario. Condicionar
al resultado real no se puede hacer antes del partido; lo que se apuesta
es el evento conjunto. Eso es la pregunta 2 de §15, y solo tiene sentido
plantearla si esta da que sí.

    python medir_condicional.py arg
    python medir_condicional.py eng --rapido
"""

import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent

SEMILLA = 20260831
REMUESTREOS = 2000

GOLES = [
    ("Más de 1.5 goles",  lambda i, j: i + j > 1.5),
    ("Más de 2.5 goles",  lambda i, j: i + j > 2.5),
    ("Más de 3.5 goles",  lambda i, j: i + j > 3.5),
    ("Ambos marcan",      lambda i, j: i > 0 and j > 0),
]


def _favorito(m):
    """El lado que el MODELO hace favorito. Es la condición que le
    importa al producto: la escalera recomienda un lado, y la pregunta
    es qué sabe de goles dado que ese lado gana."""
    import backtest
    pl = backtest.suma_si(m, lambda i, j: i > j)
    pv = backtest.suma_si(m, lambda i, j: i < j)
    return (lambda i, j: i > j) if pl >= pv else (lambda i, j: i < j)


CONDICIONES = [
    ("gana el favorito",   _favorito),
    ("gana el local",      lambda m: (lambda i, j: i > j)),
    ("gana el visitante",  lambda m: (lambda i, j: i < j)),
    ("empate",             lambda m: (lambda i, j: i == j)),
    ("no hay empate",      lambda m: (lambda i, j: i != j)),
]


def brier(ps, rs):
    return sum((p - r) ** 2 for p, r in zip(ps, rs)) / len(ps)


def aporte(ps, rs):
    """% del Brier de la tasa base que el pronóstico le saca.

    La tasa base es la del propio subconjunto: si todos los partidos del
    subconjunto dan lo mismo no hay nada que aportar y devuelve None."""
    n = len(rs)
    base = sum(rs) / n
    b_base = sum((base - r) ** 2 for r in rs) / n
    if b_base <= 0:
        return None
    return (b_base - brier(ps, rs)) / b_base * 100


def _sd(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    mu = sum(xs) / n
    return (sum((x - mu) ** 2 for x in xs) / (n - 1)) ** 0.5


def bootstrap(cond, unc, rs, remuestreos=REMUESTREOS, semilla=SEMILLA):
    """Error estándar de cada aporte y del delta, remuestreando PARTIDOS.

    Pareado: los dos pronósticos se evalúan sobre el mismo remuestreo, y
    la tasa base se recalcula adentro — así el intervalo del delta
    incluye la incertidumbre de la vara, que también se estima."""
    rnd = random.Random(semilla)
    n = len(rs)
    ac, au, ad = [], [], []
    for _ in range(remuestreos):
        idx = [rnd.randrange(n) for _ in range(n)]
        r = [rs[k] for k in idx]
        if not 0 < sum(r) < n:
            continue
        c = aporte([cond[k] for k in idx], r)
        u = aporte([unc[k] for k in idx], r)
        if c is None or u is None:
            continue
        ac.append(c)
        au.append(u)
        ad.append(c - u)
    return _sd(ac), _sd(au), _sd(ad)


def preparar(liga, progreso=2000):
    """Una entrada por partido: matriz del modelo y marcador real."""
    import actualizar as A
    import backtest
    import historico as H
    import medir_historico as MH

    rho = (A.COMPETICIONES.get(liga + ".1") or {}).get("rho", 0.0)
    filas = MH.evaluar(H.partidos(liga), progreso=progreso)
    idx = {(p["fecha"], p["home"], p["away"]): (p["gh"], p["ga"])
           for p in H.partidos(liga)}
    datos = []
    for f in filas:
        g = idx.get((f["fecha"], f["home"], f["away"]))
        if g:
            datos.append((backtest.matriz(f["lh"], f["la"], rho), g))
    return datos


def medir(datos, remuestreos=REMUESTREOS):
    """Para cada condición y cada mercado de goles, los dos aportes."""
    import backtest
    salida = []
    for nombre_r, arma in CONDICIONES:
        tests = [arma(m) for m, _ in datos]
        sub = [k for k, (_, (i, j)) in enumerate(datos) if tests[k](i, j)]
        fila = {"condicion": nombre_r, "n": len(sub),
                "frac": len(sub) / len(datos) if datos else 0, "mercados": []}
        for nombre_g, test_g in GOLES:
            cond, unc, rs = [], [], []
            for k in sub:
                m, (i, j) = datos[k]
                p_r = backtest.suma_si(m, tests[k])
                p_gr = backtest.suma_si(
                    m, lambda a, b, t=tests[k], g=test_g: t(a, b) and g(a, b))
                if p_r < 1e-9:
                    continue
                cond.append(p_gr / p_r)
                unc.append(backtest.suma_si(m, test_g))
                rs.append(1 if test_g(i, j) else 0)
            if len(rs) < 30 or not 0 < sum(rs) < len(rs):
                continue
            a_c, a_u = aporte(cond, rs), aporte(unc, rs)
            ee_c, ee_u, ee_d = bootstrap(cond, unc, rs, remuestreos)
            fila["mercados"].append({
                "mercado": nombre_g, "n": len(rs), "base": sum(rs) / len(rs),
                "aporte_cond": a_c, "aporte_unc": a_u, "delta": a_c - a_u,
                "ee_cond": ee_c, "ee_unc": ee_u, "ee_delta": ee_d})
        salida.append(fila)
    return salida


def referencia(datos, remuestreos=REMUESTREOS):
    """El aporte SIN condicionar, sobre todos los partidos. Es el número
    que ya publica `medir_ejes.py`, y está acá para que la comparación no
    dependa de correr dos scripts."""
    import backtest
    filas = []
    for nombre_g, test_g in GOLES:
        ps = [backtest.suma_si(m, test_g) for m, _ in datos]
        rs = [1 if test_g(i, j) else 0 for _, (i, j) in datos]
        if not 0 < sum(rs) < len(rs):
            continue
        _, ee, _ = bootstrap(ps, ps, rs, remuestreos)
        filas.append({"mercado": nombre_g, "n": len(rs),
                      "base": sum(rs) / len(rs),
                      "aporte": aporte(ps, rs), "ee": ee})
    return filas


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    liga = (args[0] if args else "arg").lower()
    remuestreos = 300 if "--rapido" in argv else REMUESTREOS

    print(f"\n  GOLES CONDICIONADOS AL RESULTADO — {liga}\n")
    print("  ajustando walk-forward...", flush=True)
    datos = preparar(liga)
    print(f"  {len(datos)} partidos\n")
    if not datos:
        print("  sin datos.\n")
        return 1

    print("  SIN CONDICIONAR (la vara: es lo que la app sabe hoy)\n")
    print(f"    {'mercado':20} {'n':>6} {'base':>7} {'aporte':>9} {'e.e.':>7}")
    for f in referencia(datos, remuestreos):
        print(f"    {f['mercado']:20} {f['n']:6d} {f['base']*100:6.1f}% "
              f"{f['aporte']:+8.1f}% {f['ee']:6.1f}")

    print("\n  CONDICIONADO — solo los partidos donde la condición pasó.")
    print("  La columna que contesta la hipótesis es 'cond': cuánto le")
    print("  saca el modelo condicionado a la tasa base DE ESE MISMO")
    print("  subconjunto. 'sin cond' es el modelo de hoy evaluado ahí, y")
    print("  'delta' la diferencia entre los dos — que puede ser grande")
    print("  solo porque el de hoy no sabe en qué subconjunto está.\n")
    for fila in medir(datos, remuestreos):
        print(f"    {fila['condicion']}  —  n={fila['n']} "
              f"({fila['frac']*100:.0f}% de los partidos)")
        print(f"      {'mercado':20} {'base':>7} {'sin cond':>9} "
              f"{'cond':>9} {'e.e.':>6} {'delta':>8} {'e.e.':>6}")
        for m in fila["mercados"]:
            sig = abs(m["aporte_cond"]) / m["ee_cond"] if m["ee_cond"] else 0
            marca = "  ←" if sig >= 2 and m["aporte_cond"] > 0 else (
                "  ✗" if sig >= 2 and m["aporte_cond"] < 0 else "")
            print(f"      {m['mercado']:20} {m['base']*100:6.1f}% "
                  f"{m['aporte_unc']:+8.1f}% {m['aporte_cond']:+8.1f}% "
                  f"{m['ee_cond']:5.1f} {m['delta']:+7.1f}% "
                  f"{m['ee_delta']:5.1f}{marca}")
        print()

    print("  La marca ← es sobre 'cond', no sobre 'delta', y aparece solo")
    print("  a partir de dos errores estándar: al cortar por resultado la")
    print("  muestra baja a un tercio y un aporte de +2 con e.e. de 3 es")
    print("  ruido. Un 'cond' cerca de cero con 'delta' grande NO es un")
    print("  hallazgo: quiere decir que condicionar corrige el NIVEL de")
    print("  goles del subconjunto —que la tasa base ya conocía— y no")
    print("  agrega nada partido por partido.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
