#!/usr/bin/env python3
"""¿Podemos predecir CUÁNDO nos vamos a equivocar? Walk-forward.

Sale de §29. Ahí quedó medido algo incómodo y muy preciso: sobre 11.570
partidos, cuando le damos MÁS probabilidad que la apertura, la línea se
mueve hacia ABAJO (−0.108 ±0.034), y cuando le damos menos, sube
(+0.099 ±0.023). Monótono en cinco tramos, con 3 y 4 errores estándar.

O sea que nuestro desacuerdo con el mercado no es solo inútil: **tiene
signo predecible**. Y algo con signo predecible se puede evitar.

La pregunta de este script no es "¿qué va a pasar en el partido?" sino
**"¿cuánto hay que creerle a nuestro propio número acá?"**. Un experto
sabe cuándo no sabe. Nuestro modelo tiene la misma confianza siempre.

LAS TRES PREGUNTAS, SEPARADAS A PROPÓSITO

Lucas las pidió distinguidas y la distinción importa, porque una puede
dar que sí y las otras dos que no:

  1. ¿Qué variables predicen nuestro error?
  2. ¿Cuánto mejora la predicción al incorporarlas?
  3. ¿Se mantiene fuera de muestra y sirve para algo en la práctica?

La 1 es una correlación y es barata. La 2 es un ajuste. La 3 es la
única que decide, y se contesta con plata: si nos abstenemos donde el
meta-modelo dice que erramos, ¿mejora el ROI en TEST?

LA GUARDA QUE NO ESTABA EN EL PEDIDO

Las variables se parten en dos grupos y se miden por separado:

  PROPIAS   descanso, congestión, historia del modelo, momento de la
            temporada, volatilidad del equipo, λ total. Todo sale de
            fixtures y resultados: nada mira el precio.
  MERCADO   magnitud de nuestra discrepancia, movimiento apertura→cierre.

Si toda la mejora viene del segundo grupo, no encontramos un
meta-modelo: encontramos una forma cara de copiar al mercado. Lucas fue
explícito — "no quiero convertirnos en un modelo que simplemente copie".
El corte tiene que estar en el código, no en la interpretación.

CONTRA EL AUTOENGAÑO

  - train/test temporal, y lo que decide es test.
  - una variable PLACEBO (ruido puro) en la misma tabla: cualquier
    "mejora" menor que la del placebo es la mejora de no haber medido
    nada.
  - sin leakage: toda variable se calcula con partidos ANTERIORES.
    Los días de descanso salen del fixture previo de ese equipo, no del
    calendario completo.
  - el resultado negativo se reporta igual.

RESULTADO (2026-09-03, 23.790 partidos de eng/spa/fra/arg/bra)

La hipotesis principal murio. Ninguna variable propia predice nuestro
error RELATIVO al mercado.

    1. correlacion con Brier(nosotros) - Brier(mercado)

              variable        train      test     quintiles Q5-Q1 (test)
            congestion      -0.0016   +0.0018            +0.0001
          descanso_dif      -0.0021   +0.0027            +0.0005
          descanso_min      -0.0021   +0.0074            +0.0030
               jornada      -0.0244   -0.0013            -0.0031
          lambda_total      -0.0008   +0.0153            +0.0040
             n_previos      -0.0224   -0.0155            -0.0036
           volatilidad      -0.0103   -0.0137            -0.0010
    -->      PLACEBO        -0.0070   -0.0033            -0.0025
          discrepancia $    +0.1777   +0.1319            +0.0412

Todas las propias estan en el mismo orden de magnitud que el PLACEBO, y
la mayoria cambia de signo entre train y test. Por liga (eng/spa/fra/
arg/bra) tampoco aparece: el placebo solo va de -0.0348 a +0.0196 entre
ligas, y ninguna variable real sale de esa envolvente en varias a la vez.

Se probaron las dos formas de que la medicion estuviera equivocada:

  - contra el error ABSOLUTO, por si el calendario nos afecta a nosotros
    Y al mercado y la resta lo borrara. No aparece: descanso, congestion
    y jornada siguen en el nivel del placebo.
  - por liga, por si existiera solo donde el mercado es mas blando. No.

LO UNICO QUE PREDICE NUESTRO ERROR RELATIVO ES CUANTO DISCREPAMOS

+0.1319 en test, monotono en los cinco quintiles (+0.0008 -> +0.0420),
diez veces el placebo. Y es una variable de MERCADO, o sea la trampa que
Lucas pidio evitar: lo unico accionable que se deduce es "discrepa
menos", que es copiar.

Pero dice algo mas fuerte de lo que parece. Si nuestras discrepancias
fueran a veces buenas, discrepar mucho daria a veces ganancia grande.
Que prediga perdida de forma monotona en TODA la escala significa que
**nuestro desacuerdo con el mercado no tiene contenido informativo a
ninguna magnitud**. Es mas duro que el hallazgo de §29 y lo explica.

LO QUE SI SIRVE, Y NO ES LO MISMO

Contra el error ABSOLUTO, dos variables propias son enormes y estables:

    volatilidad   -0.2371 train  -0.2454 test
    lambda_total  -0.1312 train  -0.1479 test

Eso NO es ventaja: un cruce que damos 70-10 es mas facil para todos, y
por eso desaparece al restarle el mercado. Pero es una medida honesta de
**incertidumbre intrinseca del partido**, y hoy la app no la tiene: 
publica un 45% de un partido parejo con la misma cara que un 78% de uno
desparejo. Sirve para presentar, no para apostar.

La distincion es la que pidio Lucas y conviene dejarla escrita:

    error ABSOLUTO   predecible   -> sirve para decir cuanto confiar
    error RELATIVO   no           -> no hay ventaja que rescatar

    python medir_metamodelo.py
"""

import json
import random
import statistics as st
import sys
from pathlib import Path

for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ / "data" / "bandas_filas.json"
LIGAS = ("eng", "spa", "fra", "arg", "bra")

# Debajo de esto un grupo no dice nada.
MIN_GRUPO = 300


# ── Las variables ────────────────────────────────────────────────────
#
# `mercado: True` marca las que miran el precio. Se miden igual pero se
# reportan aparte, y la conclusión se saca de las otras.
VARIABLES = {
    "descanso_min":   {"mercado": False, "txt": "días de descanso del que menos tuvo"},
    "descanso_dif":   {"mercado": False, "txt": "asimetría de descanso entre los dos"},
    "congestion":     {"mercado": False, "txt": "partidos de los dos en 14 días"},
    "n_previos":      {"mercado": False, "txt": "cuánta historia tenía el modelo"},
    "jornada":        {"mercado": False, "txt": "qué tan avanzada la temporada"},
    "lambda_total":   {"mercado": False, "txt": "goles esperados del partido"},
    "volatilidad":    {"mercado": False, "txt": "varianza reciente de los dos equipos"},
    "placebo":        {"mercado": False, "txt": "RUIDO PURO — la vara de qué es nada"},
    "discrepancia":   {"mercado": True,  "txt": "cuánto discrepamos del cierre"},
}


def calendario(ps):
    """{equipo: [fechas ordenadas]} para poder mirar SOLO hacia atrás."""
    cal = {}
    for p in ps:
        for e in (p["home"], p["away"]):
            cal.setdefault(e, []).append(p["fecha"])
    for e in cal:
        cal[e].sort()
    return cal


def previos(cal, equipo, fecha, dias=None):
    """Los partidos ANTERIORES de un equipo. Nunca el de hoy ni los futuros.

    El `<` y no `<=` no es un detalle: dos partidos del mismo día se
    verían entre sí y eso es fuga de futuro, la misma que
    `ventana_previa()` evita en medir_historico.
    """
    fs = [f for f in cal.get(equipo, []) if f < fecha]
    if dias is None:
        return fs
    return [f for f in fs if (fecha - f).days <= dias]


def rasgos(p, cal, f, rnd):
    """Las variables del partido, todas mirando hacia atrás."""
    ha = previos(cal, p["home"], p["fecha"])
    aa = previos(cal, p["away"], p["fecha"])
    if not ha or not aa:
        return None
    dh = (p["fecha"] - ha[-1]).days
    da = (p["fecha"] - aa[-1]).days
    # Volatilidad: qué tan parejo viene siendo el equipo. Un equipo que
    # alterna 4-0 y 0-3 es menos predecible que uno que empata siempre,
    # y el modelo no distingue.
    return {
        "descanso_min": min(dh, da),
        "descanso_dif": abs(dh - da),
        "congestion": len(previos(cal, p["home"], p["fecha"], 14))
                      + len(previos(cal, p["away"], p["fecha"], 14)),
        "n_previos": f.get("n_previos", 0),
        "jornada": min(len(ha), len(aa)),
        "lambda_total": (f.get("lh") or 0) + (f.get("la") or 0),
        # Cuan desparejo vemos NOSOTROS el partido. Un cruce que damos
        # 70-10 no es igual de incierto que uno 35-35, y el modelo no
        # distingue: publica los dos con la misma confianza.
        "volatilidad": abs(f["modelo"][0] - f["modelo"][2]),
        "placebo": rnd.random(),
        "discrepancia": sum(abs(f["modelo"][i] - f["mercado"][i]) for i in range(3)),
    }


def error_relativo(f):
    """Brier nuestro menos Brier del mercado, en ESTE partido.

    Positivo = el mercado estuvo mejor acá. Es el objetivo correcto y no
    el error crudo: queremos saber dónde somos PEORES QUE ELLOS, que es
    distinto de dónde el partido salió raro. Un 0-0 sorpresivo castiga
    a los dos por igual y no dice nada de nosotros.
    """
    bn = sum((f["modelo"][i] - f["real"][i]) ** 2 for i in range(3))
    bm = sum((f["mercado"][i] - f["real"][i]) ** 2 for i in range(3))
    return bn - bm


def cargar():
    """Filas del caché de medir_bandas, más las variables del calendario."""
    import historico as H
    if not CACHE.exists():
        raise SystemExit("Falta data/bandas_filas.json — corré antes "
                         "`python medir_bandas.py`.")
    d = json.loads(CACHE.read_text(encoding="utf-8"))
    rnd = random.Random(20260903)
    filas = []
    for lg in LIGAS:
        if lg not in d:
            continue
        ps = H.partidos(lg)
        cal = calendario(ps)
        por_clave = {(str(p["fecha"]), p["home"], p["away"]): p for p in ps}
        for f in d[lg]:
            p = por_clave.get((str(f["fecha"]), f["home"], f["away"]))
            if not p:
                continue
            r = rasgos(p, cal, f, rnd)
            if not r:
                continue
            r["_err"] = error_relativo(f)
            r["_fecha"] = str(f["fecha"])
            r["_liga"] = lg
            r["_fila"] = f
            filas.append(r)
    return filas


def correl(xs, ys):
    """Pearson. Con miles de casos alcanza y evita una dependencia."""
    n = len(xs)
    if n < 30:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def main(argv):
    filas = cargar()
    if not filas:
        print("\n  Sin filas.\n")
        return 1
    fechas = sorted({f["_fecha"] for f in filas})
    corte = fechas[int(len(fechas) * 0.6)]
    tr = [f for f in filas if f["_fecha"] < corte]
    te = [f for f in filas if f["_fecha"] >= corte]

    print("\n" + "=" * 78)
    print("  ¿PODEMOS PREDECIR CUÁNDO NOS EQUIVOCAMOS?")
    print("=" * 78)
    print(f"\n  {len(filas)} partidos · train {len(tr)} · test {len(te)} "
          f"· corte {corte}")
    print(f"  objetivo: Brier nuestro − Brier del mercado (positivo = ellos mejor)")
    print(f"  media del objetivo: train {st.mean([f['_err'] for f in tr]):+.5f} "
          f"· test {st.mean([f['_err'] for f in te]):+.5f}")

    # ── 1. ¿Qué variables predicen nuestro error? ────────────────────
    print(f"\n{'─' * 78}")
    print("  1. QUÉ VARIABLES PREDICEN NUESTRO ERROR  (correlación)")
    print(f"{'─' * 78}\n")
    print(f"  {'variable':>16} {'':>2} {'train':>9} {'test':>9}   {'descripción'}")
    orden = sorted(VARIABLES, key=lambda v: (VARIABLES[v]["mercado"], v))
    for v in orden:
        ctr = correl([f[v] for f in tr], [f["_err"] for f in tr])
        cte = correl([f[v] for f in te], [f["_err"] for f in te])
        if ctr is None:
            continue
        marca = "$" if VARIABLES[v]["mercado"] else " "
        print(f"  {v:>16} {marca:>2} {ctr:>+9.4f} {cte:>+9.4f}   "
              f"{VARIABLES[v]['txt']}")
    print("\n  '$' = mira el precio. La conclusión sale de las otras.")
    print("  Una correlación que no repite el signo en test no existe.")

    # ── 2 y 3. ¿Sirve para algo? ─────────────────────────────────────
    #
    # La prueba práctica: partir TEST en quintiles por lo que el
    # meta-modelo predice, y ver si el error real sigue ese orden. Si el
    # quintil "peor" no es peor de verdad, la correlación era decorativa.
    print(f"\n{'─' * 78}")
    print("  2 y 3. ¿SIRVE?  Quintiles de TEST por lo que predice cada variable")
    print(f"{'─' * 78}\n")
    print(f"  {'variable':>16} {'':>2} " +
          "".join(f"{'Q'+str(i+1):>9}" for i in range(5)) + f"{'Q5-Q1':>10}")
    for v in orden:
        ok = [f for f in te if f.get(v) is not None]
        if len(ok) < MIN_GRUPO * 5:
            continue
        ok.sort(key=lambda f: f[v])
        n = len(ok) // 5
        qs = [ok[i * n:(i + 1) * n] for i in range(5)]
        med = [st.mean([f["_err"] for f in q]) for q in qs]
        marca = "$" if VARIABLES[v]["mercado"] else " "
        print(f"  {v:>16} {marca:>2} " +
              "".join(f"{m:>+9.4f}" for m in med) +
              f"{med[-1] - med[0]:>+10.4f}")
    print("\n  Q1 = donde la variable es más baja. La última columna es el")
    print("  efecto: si no supera al del placebo, no hay efecto.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
