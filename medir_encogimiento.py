#!/usr/bin/env python3
"""¿Conviene tirar el modelo hacia la tasa base? Y si sí, cuánto.

Por qué existe:

`TRASPASO.md` §5 midió el 2026-08-24 que encoger las probabilidades del
modelo hacia la frecuencia histórica mejora fuera de muestra, y dejó
`k = 0.30` para arg y `0.20` para bra. Nunca se aplicó, y ahora tampoco
se puede aplicar tal cual: esos valores se midieron con
`VIDA_MEDIA_DIAS` en **180**, y la constante hoy está en **300**.

Y no es un detalle de número. El hallazgo más interesante de aquella
medición fue justamente que **cuanto más larga la ventana, menos
encogimiento hace falta** — 0.40 con vida 45, 0.30 con vida 180 en arg;
0.30 y 0.20 en bra. La ventana corta fabricaba ruido que después había
que apagar a mano. Si esa tendencia sigue, en 300 el `k` bueno puede
ser bastante más chico, o directamente cero. Copiar el 0.30 sería
apagar un ruido que ya no está.

Qué es encoger:

    p_final = (1 - k) · p_modelo  +  k · tasa_base

`k = 0` deja el modelo como está. `k = 1` lo borra y publica la
frecuencia histórica. En el medio, un modelo menos confiado.

Cómo se mide, y por qué así:

- **Fuera de muestra, con partición temporal.** El `k` se elige con los
  partidos anteriores al corte y se mide con los posteriores. Elegir y
  medir con los mismos partidos siempre "mejora": ahí no se está
  midiendo un modelo, se está midiendo un ajuste de curva.
- **Contra el ruido, no contra cero.** Los dos Brier salen de los MISMOS
  partidos, así que están pareados: lo que importa es la desviación de
  la diferencia partido por partido. Sin eso, cualquier `k` parece
  mejorar algo.
- **Con el atraso contra el cierre, no con la captura.** La captura
  —qué fracción de la ventaja del mercado alcanzamos— infla cuando el
  mercado le gana poco a la tasa base, y ese denominador cambia de liga
  en liga. El atraso es la distancia cruda contra el precio al que hay
  que apostar de verdad.

Lo que dio, el 2026-08-25:

    liga   ventana   atraso sin k    k     atraso con k   significativa
    arg      1825         +0.01085  0.20        +0.00850   sí (4 e.e.)
    bra      1825         +0.01477  0.15        +0.01507   no, y empeora

**arg: encoger sirve, y el k bajó a 0.20.** Aguanta moviendo el corte de
2019 a 2023 — sale entre 0.20 y 0.30 en las cinco particiones, siempre
significativo. El 0.30 de TRASPASO no era falso: era el valor correcto
para una ventana de historia que resultó estar mal puesta.

**bra: no.** La diferencia no se despega del ruido con ninguna ventana, y
con la ventana correcta directamente cambia de signo. Encoger Brasil
sería mover una constante para que un número dé mejor, que es lo que la
regla del repo prohíbe.

Y el hallazgo de TRASPASO §5 —cuanta más historia, menos encogimiento
hace falta— se confirma y se extiende: 0.40 (vida 45) → 0.30 (vida 180)
→ **0.20** (vida 300 con la ventana de medición arreglada). El
encogimiento estaba apagando ruido que el modelo fabricaba por falta de
historia, no un exceso de confianza propio.

    python medir_encogimiento.py            # arg
    python medir_encogimiento.py bra
    python medir_encogimiento.py arg 2020   # otro año de corte
"""

import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import actualizar as A
import historico as H
import medir_historico as MH

RAIZ = Path(__file__).resolve().parent

# De 0 a 0.9. El tope es holgado a propósito: si el óptimo se apoya ahí,
# la grilla se quedó corta y hay que decirlo en vez de reportar el borde
# como hallazgo (CLAUDE.md — pasó dos veces el 2026-08-24).
GRILLA = [round(i * 0.05, 2) for i in range(19)]

# Con la muestra partida así, 2022 deja unos cuatro años de prueba y
# diez de ajuste. Es el mismo corte que usó TRASPASO.md §5, así que los
# números son comparables contra los de vida 180.
CORTE = 2022

LIGA_A_COMP = {"arg": "arg.1", "bra": "bra.1"}


def encoger(p, base, k):
    """La mezcla. Con k=0 devuelve el modelo; con k=1, la tasa base."""
    return [(1.0 - k) * p[i] + k * base[i] for i in range(3)]


def brier_de(fila, k):
    """Brier de UN partido con el modelo encogido en k."""
    p = encoger(fila["modelo"], fila["base"], k)
    return sum((p[i] - fila["real"][i]) ** 2 for i in range(3))


def brier_medio(filas, k):
    return sum(brier_de(f, k) for f in filas) / len(filas) if filas else None


def brier_mercado(filas):
    if not filas:
        return None
    return sum(sum((f["mercado"][i] - f["real"][i]) ** 2 for i in range(3))
               for f in filas) / len(filas)


def atraso(filas, k):
    """Cuánto le erramos de más que el mercado. Positivo = vamos atrás.

    Es la métrica honesta: no tiene denominador que la infle. La captura
    divide por la ventaja del mercado sobre la tasa base, y cuando esa
    ventaja es chica —liga poco eficiente— el mismo modelo mediocre
    "captura" un porcentaje enorme.
    """
    if not filas:
        return None
    return brier_medio(filas, k) - brier_mercado(filas)


def partir(filas, anio=CORTE):
    """(ajuste, prueba) partido por año, sin solapamiento.

    El corte es por FECHA, no por posición: un partido del período de
    prueba que se cuele en el ajuste no se ve como error, se ve como un
    `k` buenísimo. Es la misma trampa que `ventana_previa()` cuida un
    nivel más abajo, y por eso está testeada aparte.
    """
    aj = [f for f in filas if f["fecha"].year < anio]
    pr = [f for f in filas if f["fecha"].year >= anio]
    return aj, pr


def mejor_k(filas, grilla=None):
    """El k que minimiza el Brier sobre estos partidos.

    `borde` avisa que el óptimo se apoyó contra el TECHO de la grilla —
    o sea que no se encontró un mínimo, se encontró dónde se dejó de
    mirar. El piso es distinto: `k = 0` significa "no encoger", que es
    una respuesta con contenido, no una pared.
    """
    if not filas:
        return None
    grilla = grilla or GRILLA
    puntos = [(brier_medio(filas, k), k) for k in grilla]
    br, k = min(puntos)
    return {"k": k, "brier": br, "borde": k == max(grilla),
            "curva": [(kk, bb) for bb, kk in sorted(puntos, key=lambda x: x[1])]}


def diferencia_pareada(filas, k1, k2):
    """Brier(k2) − Brier(k1) partido por partido, con su ruido.

    Pareada porque los dos números salen de los mismos partidos: la
    varianza que importa es la de la diferencia, no la de cada serie por
    separado, y es mucho más chica. Tratarlas como independientes es
    tirar a la basura justo la parte que hace la comparación sensible.

    Negativo = k2 mejora. `significativa` pide que la diferencia le
    saque dos errores estándar al cero.
    """
    if not filas:
        return None
    ds = [brier_de(f, k2) - brier_de(f, k1) for f in filas]
    n = len(ds)
    m = sum(ds) / n
    if n < 2:
        ee = 0.0
    else:
        var = sum((d - m) ** 2 for d in ds) / (n - 1)
        ee = math.sqrt(var / n)
    return {"dif": m, "ee": ee, "n": n,
            "significativa": ee > 0 and abs(m) > 2 * ee}


def _tabla_curva(r, etiqueta):
    print("\n  " + etiqueta)
    print("  {:>6} {:>10}".format("k", "Brier"))
    for k, b in r["curva"]:
        marca = "   <- el mejor" if k == r["k"] else ""
        print("  {:6.2f} {:10.5f}{}".format(k, b, marca))


def main(argv):
    liga = (argv[1] if len(argv) > 1 else "arg").lower()
    corte = int(argv[2]) if len(argv) > 2 else CORTE
    if liga not in H.LIGAS:
        raise SystemExit("liga desconocida: {}. Hay {}".format(liga, sorted(H.LIGAS)))
    rho = A.COMPETICIONES[LIGA_A_COMP[liga]]["rho"]

    print("\n" + "=" * 68)
    print("  ENCOGER HACIA LA TASA BASE — {}, corte {}".format(liga, corte))
    print("=" * 68)
    print("\n  VIDA_MEDIA_DIAS = {}   rho = {:+.2f}".format(A.VIDA_MEDIA_DIAS, rho))
    print("  (TRASPASO.md §5 midió k=0.30 arg / 0.20 bra con vida 180)")

    ps = H.partidos(liga)
    print("\n  {} partidos · ajustando walk-forward, tarda un rato...".format(len(ps)))
    filas = MH.evaluar(ps, rho=rho, progreso=2000)
    if not filas:
        raise SystemExit("no se evaluó ningún partido")

    aj, pr = partir(filas, corte)
    print("\n  ajuste: {} partidos hasta {}".format(len(aj), corte - 1))
    print("  prueba: {} partidos desde {}".format(len(pr), corte))
    if not aj or not pr:
        raise SystemExit("el corte deja una de las dos partes vacía")

    r_aj = mejor_k(aj)
    _tabla_curva(r_aj, "el barrido SOBRE EL AJUSTE (hasta {})".format(corte - 1))
    if r_aj["borde"]:
        print("\n  ⚠ El óptimo se apoya en el tope de la grilla: no se")
        print("    encontró un mínimo, se encontró dónde dejamos de mirar.")
        print("    Extendé GRILLA antes de creerle a este número.")

    k = r_aj["k"]
    print("\n  " + "-" * 64)
    print("  Elegido con el ajuste: k = {:.2f}".format(k))
    print("  Ahora, qué hace ese k en partidos que nunca vio.")
    print("  " + "-" * 64)

    b0, bk = brier_medio(pr, 0.0), brier_medio(pr, k)
    bm = brier_mercado(pr)
    print("\n  {:28} {:>10} {:>18}".format("quién", "Brier", "atraso vs cierre"))
    print("  {:28} {:10.5f} {:18.5f}".format("el mercado (cierre)", bm, 0.0))
    print("  {:28} {:10.5f} {:+18.5f}".format("el modelo, sin encoger", b0, b0 - bm))
    print("  {:28} {:10.5f} {:+18.5f}".format(
        "el modelo, con k={:.2f}".format(k), bk, bk - bm))

    d = diferencia_pareada(pr, 0.0, k)
    print("\n  La diferencia, partido por partido: {:+.5f}".format(d["dif"]))
    print("  Su ruido (error estándar): {:.5f} sobre {} partidos".format(
        d["ee"], d["n"]))
    if k == 0.0:
        print("\n  El ajuste eligió NO encoger. Con esta vida media el modelo")
        print("  ya no fabrica el exceso de confianza que k venía a apagar.")
    elif d["significativa"] and d["dif"] < 0:
        print("\n  Encoger MEJORA, y la mejora le saca dos errores estándar")
        print("  al ruido. Es un hallazgo, no una casualidad.")
    elif d["significativa"]:
        print("\n  ⚠ Encoger EMPEORA fuera de muestra, y no por azar.")
    else:
        print("\n  La diferencia no se despega del ruido: con esta muestra")
        print("  no se puede decir que encoger sirva ni que estorbe. El")
        print("  hallazgo es que no hay hallazgo.")

    r_pr = mejor_k(pr)
    print("\n  De paso, el k que habría sido mejor EN LA PRUEBA: "
          "{:.2f}".format(r_pr["k"]))
    print("  (no es un resultado — es mirar las respuestas después del")
    print("   examen. Sirve solo para ver si el ajuste apuntó cerca.)")
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
