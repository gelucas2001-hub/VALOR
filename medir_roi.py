#!/usr/bin/env python3
"""La regla de valor de la app contra PLATA, liga por liga.

Por qué existe, y por qué recién ahora:

El único ROI que este proyecto midió alguna vez es de **arg**: −3.27%
±6.19 (TRASPASO.md, addendum del encogimiento). Se calculó con un
script ad-hoc en Node que no quedó en el repo, así que ni siquiera se
podía volver a correr.

Y mientras tanto, en TRASPASO.md §6vicies ter estaba enterrado esto,
medido fuera de muestra:

    captura de la ventaja del mercado
    eng.1   80.9%      bra.1   45.4%
    fra.1   80.9%      arg.1    7.7%

Un modelo que captura 80.9% de lo que sabe el mercado es bueno de
verdad. Uno que captura 7.7% es ruido con decimales. **No es el mismo
modelo fallando parejo: es un modelo que anda bien donde el torneo
tiene forma normal y se rompe en Argentina** — 28-30 equipos a una
sola vuelta, 1.00 cruces por par contra 2.00 de Brasil, la mitad de
datos por parámetro (§6octodecies).

Nadie preguntó nunca cuál es el ROI donde el modelo captura diez veces
más. Eso contesta este script.

Cómo mide:

Reutiliza entero el arnés walk-forward de `medir_historico.evaluar()`
— ajuste con solo lo anterior, ni el mismo día; devig de Shin; cuota
de cierre real de Pinnacle cuando está. No reimplementa el motor.

Encima de eso aplica la regla real de la app (TRASPASO.md §5):

    ventaja del modelo sobre el mercado dentro de [VALOR_MIN, VALOR_MAX]
    cuota <= MAX_ODDS

Dos salvedades que hay que decir en voz alta, las dos heredadas del
addendum que midió el −3.27%:

1. **Se apuesta a la cuota de CIERRE**, el precio más difícil que
   existe. Sirve para comparar ligas entre sí con la misma vara — que
   es para lo que existe este script — no para estimar lo que da la
   app, que apuesta antes y a otra casa. Un ROI de cero acá es mejor
   de lo que parece.
2. **No se simula la regla de alineación** (que exige análisis humano
   cargado). Es imposible hacia atrás: la skill hace research web y
   sobre un partido viejo la web ya sabe el resultado. Así que esto
   mide la regla de valor sola, sin el filtro cualitativo.

    python medir_roi.py            # arg
    python medir_roi.py eng
    python medir_roi.py todas      # las cuatro, para comparar
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent

# Las mismas constantes que rigen en index.html. Si allá cambian, acá
# también — medir con una vara distinta de la que marca es exactamente
# el error que costó el arreglo del devig (§6vicies).
VALOR_MIN = 0.06
VALOR_MAX = 0.12
MAX_ODDS = 4.5

# Cuántas apuestas hacen falta antes de creerle a un ROI. No es un
# número mágico: es que abajo de esto el error estándar se come
# cualquier señal, y este repo ya reportó un +11.2% que era ruido
# (§6vicies quater, córners). Se usa junto con el test de dos errores
# estándar, no en lugar de él.
MIN_APUESTAS = 100


def apuestas(filas, valor_min=VALOR_MIN, valor_max=VALOR_MAX,
             max_odds=MAX_ODDS):
    """Qué habría apostado la app, sobre las filas de medir_historico.

    Una fila puede generar hasta tres apuestas (local, empate, visita),
    aunque en la práctica casi nunca más de una: la ventaja es una
    resta contra el mercado y rara vez cae en la ventana dos veces.
    """
    out = []
    for f in filas or []:
        cuotas = f.get("cuotas")
        if not cuotas or len(cuotas) != 3:
            continue
        for i in range(3):
            ventaja = f["modelo"][i] - f["mercado"][i]
            if not (valor_min <= ventaja <= valor_max):
                continue
            if not cuotas[i] or cuotas[i] > max_odds:
                continue
            out.append({"cuota": cuotas[i], "gano": f["real"][i] == 1,
                        "ventaja": ventaja, "liga": f.get("liga"),
                        "fecha": f.get("fecha")})
    return out


def roi(aps):
    """ROI con su incertidumbre. Sin el error estándar, el número miente.

    Una ganada devuelve `cuota - 1` (la ganancia), no `cuota`: contar
    el monto apostado como ganancia infla el ROI en cada acierto.
    """
    n = len(aps or [])
    if not n:
        return {"n": 0, "roi": None, "se": None, "acierto": None,
                "significativo": False}
    retornos = [(a["cuota"] - 1) if a["gano"] else -1.0 for a in aps]
    media = sum(retornos) / n
    var = sum((r - media) ** 2 for r in retornos) / n
    se = (var ** 0.5) / (n ** 0.5)
    ganadas = sum(1 for a in aps if a["gano"])
    return {"n": n, "roi": media, "se": se, "acierto": ganadas / n,
            # Dos errores estándar Y muestra suficiente. Las dos
            # condiciones, no una: con 40 apuestas el intervalo es tan
            # ancho que "no significativo" no informa nada.
            "significativo": abs(media) > 2 * se and n >= MIN_APUESTAS}


def _linea(etiqueta, r):
    if not r["n"]:
        return f"  {etiqueta:10} sin una sola apuesta que califique"
    marca = "" if r["significativo"] else "   (ruido: el intervalo incluye cero)"
    return (f"  {etiqueta:10} {r['n']:5d} apuestas   "
            f"ROI {r['roi']*100:+6.2f}% ±{r['se']*200:5.2f}   "
            f"acierto {r['acierto']*100:4.1f}%{marca}")


def medir_liga(liga, progreso=None):
    """Corre el walk-forward completo de una liga y devuelve su ROI."""
    import historico as H
    import medir_historico as MH

    ps = H.partidos(liga)
    if not ps:
        return None, []
    filas = MH.evaluar(ps, progreso=progreso)
    return roi(apuestas(filas)), filas


def main(argv):
    import historico as H

    pedido = (argv[1] if len(argv) > 1 else "arg").lower()
    ligas = sorted(H.LIGAS) if pedido == "todas" else [pedido]
    for l in ligas:
        if l not in H.LIGAS:
            raise SystemExit(f"liga desconocida: {l}. Hay {sorted(H.LIGAS)}")

    print("\n" + "=" * 74)
    print("  LA REGLA DE VALOR CONTRA PLATA — por liga, walk-forward")
    print("=" * 74)
    print(f"\n  regla: ventaja en [{VALOR_MIN:.0%}, {VALOR_MAX:.0%}] "
          f"· cuota <= {MAX_ODDS}")
    print("  precio: cuota de CIERRE (el más difícil que existe)")
    print("  sin el filtro de análisis humano — no es simulable hacia atrás\n")

    resultados = {}
    for l in ligas:
        print(f"  {l}: ajustando walk-forward (tarda ~8 min)...", flush=True)
        r, filas = medir_liga(l)
        if r is None:
            print(f"  {l}: sin partidos")
            continue
        resultados[l] = r
        print(_linea(l, r), flush=True)

    if len(resultados) > 1:
        print("\n  " + "-" * 70)
        print("  La comparación es el punto: si una liga da distinto de otra,")
        print("  el problema no es 'el modelo' sino dónde se lo aplica.")
        print("  " + "-" * 70)

    print("\n  Recordá las dos salvedades: se apuesta al CIERRE (vara dura,")
    print("  un cero acá es mejor de lo que parece) y sin filtro de análisis.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
