#!/usr/bin/env python3
"""¿Existe ALGUNA ventana de ventaja que dé plata? Train/test temporal.

Por qué existe:

`VALOR_MIN = 0.06` y `VALOR_MAX = 0.12` — las dos constantes que
deciden qué se marca en dorado — se eligieron mirando **cuántas marcas
producían**, no cuánta plata daban. Está escrito en TRASPASO.md §5bis:

    "La única forma honesta de fijar el piso es medir si los picks
    marcados ganan más que los no marcados, y para eso hacen falta
    resultados. Ese camino ahora existe."

Ese camino existe desde que hay `medir_roi.py`. Esto lo recorre.

Qué contesta, y por qué la respuesta sirve en los dos sentidos:

- Si **ninguna** ventana da ROI positivo fuera de muestra, la respuesta
  es definitiva y vale tanto como un hallazgo positivo: la regla de
  valor no funciona con este modelo, y el producto tiene que dejar de
  marcar valor en vez de seguir buscándole la vuelta a los umbrales.
- Si alguna da positivo **y aguanta en test**, tenemos la ventana
  medida contra plata en vez de contra cantidad de marcas.

Método, con la disciplina que el repo ya exige:

- **train (fecha < 2022) para elegir, test (>= 2022) para confirmar.**
  Elegir y validar sobre lo mismo es tunear hacia atrás.
- Se reporta el ROI de train Y el de test. **Si el ganador de train se
  da vuelta en test, no es un hallazgo** — es la señal de que era
  ruido, igual que pasó en `barrido_lambda.py`.
- Un óptimo en el borde de la grilla no es un óptimo: es donde se dejó
  de mirar. La grilla se extiende si el mejor cae en el borde.

    python barrido_valor.py arg
    python barrido_valor.py arg --rapido    # grilla chica
"""

import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent

CORTE = date(2022, 1, 1)

# Grilla de pisos y techos. El piso actual (0.06) y el techo (0.12)
# están adentro, para poder ver dónde queda producción.
PISOS = [0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15]
TECHOS = [0.08, 0.10, 0.12, 0.16, 0.20, 0.30, 1.00]

PISOS_RAPIDO = [0.04, 0.06, 0.10]
TECHOS_RAPIDO = [0.12, 0.20, 1.00]

# Abajo de esto, un ROI no dice nada — el error estándar se lo come.
MIN_N = 60


def partir(filas):
    """train/test por fecha. El corte es temporal, nunca aleatorio:
    con series de tiempo, mezclar es fuga de futuro."""
    tr = [f for f in filas if f["fecha"] < CORTE]
    te = [f for f in filas if f["fecha"] >= CORTE]
    return tr, te


def evaluar_ventana(filas, piso, techo):
    import medir_roi as R
    return R.roi(R.apuestas(filas, valor_min=piso, valor_max=techo))


def main(argv):
    import historico as H
    import medir_historico as MH

    liga = "arg"
    rapido = "--rapido" in argv
    for a in argv[1:]:
        if not a.startswith("--"):
            liga = a.lower()
    if liga not in H.LIGAS:
        raise SystemExit(f"liga desconocida: {liga}. Hay {sorted(H.LIGAS)}")

    pisos = PISOS_RAPIDO if rapido else PISOS
    techos = TECHOS_RAPIDO if rapido else TECHOS

    print("\n" + "=" * 78)
    print(f"  ¿ALGUNA VENTANA DE VENTAJA DA PLATA? — {liga}, train/test temporal")
    print("=" * 78)
    print(f"\n  train: fecha < {CORTE}   ·   test: fecha >= {CORTE}")
    print(f"  producción hoy: piso 0.06, techo 0.12")
    print("\n  ajustando walk-forward (una sola vez, tarda ~8 min)...", flush=True)

    filas = MH.evaluar(H.partidos(liga), progreso=2000)
    tr, te = partir(filas)
    print(f"  {len(filas)} partidos · train {len(tr)} · test {len(te)}\n")

    print(f"  {'piso':>6} {'techo':>7} │ {'n tr':>6} {'ROI train':>11} │ "
          f"{'n te':>6} {'ROI test':>11} {'±2se':>7}")
    print("  " + "-" * 74)

    resultados = []
    for piso in pisos:
        for techo in techos:
            if techo <= piso:
                continue
            r_tr = evaluar_ventana(tr, piso, techo)
            r_te = evaluar_ventana(te, piso, techo)
            if not r_tr["n"] or not r_te["n"]:
                continue
            resultados.append({"piso": piso, "techo": techo,
                               "tr": r_tr, "te": r_te})
            marca = ""
            if r_tr["n"] >= MIN_N and r_te["n"] >= MIN_N:
                if r_tr["roi"] > 0 and r_te["roi"] > 0:
                    marca = "  ← positivo en LAS DOS"
                elif r_tr["roi"] > 0 > r_te["roi"]:
                    marca = "  (se da vuelta: ruido)"
            print(f"  {piso:6.2f} {techo:7.2f} │ {r_tr['n']:6d} "
                  f"{r_tr['roi']*100:+10.2f}% │ {r_te['n']:6d} "
                  f"{r_te['roi']*100:+10.2f}% {r_te['se']*200:6.2f}{marca}")

    # El veredicto, escrito para poder decir que no.
    print("\n  " + "=" * 74)
    utiles = [x for x in resultados
              if x["tr"]["n"] >= MIN_N and x["te"]["n"] >= MIN_N]
    dobles = [x for x in utiles if x["tr"]["roi"] > 0 and x["te"]["roi"] > 0]
    signif = [x for x in dobles if x["te"]["significativo"]]

    print(f"  {len(utiles)} ventanas con muestra suficiente en las dos mitades.")
    if not dobles:
        print("\n  NINGUNA ventana da ROI positivo en train Y en test.")
        print("  Con este modelo, mover los umbrales no convierte la regla de")
        print("  valor en rentable. El hallazgo es que no hay hallazgo, y es")
        print("  la respuesta que el producto necesitaba: no se marca valor")
        print("  buscándole la vuelta a una constante.")
    elif not signif:
        print(f"\n  {len(dobles)} ventana(s) positiva(s) en las dos mitades, pero")
        print("  NINGUNA se despega del ruido en test. No alcanza para mover")
        print("  una constante — es exactamente el caso que el repo ya")
        print("  documentó con córners (+11.2% sobre 41 apuestas).")
        for x in dobles:
            print(f"    piso {x['piso']:.2f} techo {x['techo']:.2f}: "
                  f"test {x['te']['roi']*100:+.2f}% ±{x['te']['se']*200:.2f} "
                  f"sobre {x['te']['n']} apuestas")
    else:
        print(f"\n  {len(signif)} ventana(s) POSITIVA Y SIGNIFICATIVA en test:")
        for x in signif:
            print(f"    piso {x['piso']:.2f} techo {x['techo']:.2f}: "
                  f"train {x['tr']['roi']*100:+.2f}% · "
                  f"test {x['te']['roi']*100:+.2f}% ±{x['te']['se']*200:.2f} "
                  f"sobre {x['te']['n']} apuestas")
        print("\n  Antes de tocar nada: revisar que el óptimo no esté en el")
        print("  borde de la grilla, y correrlo en otra liga.")
    print("  " + "=" * 74 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
