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


def apuestas_ou(filas, valor_min=VALOR_MIN, valor_max=VALOR_MAX,
                max_odds=MAX_ODDS):
    """Lo mismo, pero sobre el mercado de GOLES (over/under 2.5).

    Existe porque el ROI se midió siempre sobre 1X2, y hay dos razones
    medidas para sospechar que el de goles es el bueno:

    - `barrido_lambda.py` (2026-08-29): over 2.5 está bien calibrado
      —0.357 real contra 0.375 predicho sobre 2559 partidos— mientras
      el 1X2 arrastra favoritos sobreconfiados.
    - El único sesgo grande que encontramos hoy es direccional del 1X2
      (visitante inflado hasta +10pp). El mercado de goles no tiene
      dirección: no hay local ni visitante que inflar.

    El margen se quita con Shin, igual que en el resto del proyecto. En
    un mercado de dos opciones Shin devuelve el proporcional — eso es
    correcto, no un atajo (CLAUDE.md lo deja escrito).
    """
    import medir_clv
    out = []
    for f in filas or []:
        cu, pmod, real = (f.get("cuotas_ou"), f.get("modelo_ou"),
                          f.get("real_ou"))
        if not cu or not pmod or not real:
            continue
        pq = medir_clv.devig_shin(cu)
        if pq is None:
            continue
        for i in (0, 1):          # 0 = over, 1 = under
            ventaja = pmod[i] - pq[i]
            if not (valor_min <= ventaja <= valor_max):
                continue
            if not cu[i] or cu[i] > max_odds:
                continue
            out.append({"cuota": cu[i], "gano": real[i] == 1,
                        "ventaja": ventaja, "lado": "over" if i == 0 else "under",
                        "liga": f.get("liga"), "fecha": f.get("fecha")})
    return out


def _drawdown(retornos):
    """La peor caída desde un pico, en unidades apostadas.

    El ROI medio no dice cómo fue el camino: dos estrategias con el
    mismo +2% no son la misma cosa si una llegó derecho y la otra pasó
    por una caída de 40 unidades en el medio. La segunda se abandona
    antes de llegar, y una estrategia que no se puede sostener no
    rinde lo que dice el promedio.

    Con stake fijo de 1 unidad, la caída se mide en unidades y no hace
    falta suponer un bankroll inicial.
    """
    pico = acum = peor = 0.0
    for r in retornos:
        acum += r
        pico = max(pico, acum)
        peor = max(peor, pico - acum)
    return peor


def roi(aps):
    """ROI con su incertidumbre y su riesgo. Sin eso, el número miente.

    Una ganada devuelve `cuota - 1` (la ganancia), no `cuota`: contar
    el monto apostado como ganancia infla el ROI en cada acierto.

    El **drawdown** se mide en orden CRONOLÓGICO, no en el orden en que
    vinieron las apuestas en la lista: una caída depende de la secuencia,
    y medirla sobre un orden arbitrario da un número que no le pasó a
    nadie.

    El **Sharpe** acá es por apuesta, no anualizado: media dividido
    desvío de los retornos, con tasa libre de riesgo en cero. Vale la
    pena saber que está atado a la significancia — `sharpe = z / √n`,
    donde z es el ROI en errores estándar. No es información nueva sobre
    si hay ventaja; es la misma información en unidades de riesgo, que
    es como se compara una estrategia contra otra.
    """
    n = len(aps or [])
    if not n:
        return {"n": 0, "roi": None, "se": None, "acierto": None,
                "significativo": False, "drawdown": None, "sharpe": None}
    ordenadas = sorted(aps, key=lambda a: (a.get("fecha") or 0, a.get("cuota", 0)))
    retornos = [(a["cuota"] - 1) if a["gano"] else -1.0 for a in ordenadas]
    media = sum(retornos) / n
    var = sum((r - media) ** 2 for r in retornos) / n
    sd = var ** 0.5
    se = sd / (n ** 0.5)
    ganadas = sum(1 for a in aps if a["gano"])
    return {"n": n, "roi": media, "se": se, "acierto": ganadas / n,
            # Dos errores estándar Y muestra suficiente. Las dos
            # condiciones, no una: con 40 apuestas el intervalo es tan
            # ancho que "no significativo" no informa nada.
            "significativo": abs(media) > 2 * se and n >= MIN_APUESTAS,
            "drawdown": _drawdown(retornos),
            # Sin variación no hay riesgo que medir y la división no
            # existe. Devolver None es más honesto que un infinito que
            # después alguien formatea como número.
            "sharpe": (media / sd) if sd > 0 else None}


def _linea(etiqueta, r):
    if not r["n"]:
        return f"  {etiqueta:10} sin una sola apuesta que califique"
    marca = "" if r["significativo"] else "  (ruido)"
    sharpe = f"{r['sharpe']:+.3f}" if r["sharpe"] is not None else "  —  "
    # El drawdown va en unidades apostadas y también como múltiplo de lo
    # que la estrategia ganó o perdió en total: 12 unidades de caída son
    # otra cosa sobre 100 apuestas que sobre 2000.
    dd_rel = r["drawdown"] / r["n"] * 100
    return (f"  {etiqueta:10} {r['n']:5d} ap.  "
            f"ROI {r['roi']*100:+6.2f}% ±{r['se']*200:5.2f}  "
            f"acierto {r['acierto']*100:4.1f}%  "
            f"caída {r['drawdown']:6.1f}u ({dd_rel:4.1f}%)  "
            f"Sharpe {sharpe}{marca}")


def medir_liga(liga, progreso=None):
    """Corre el walk-forward completo de una liga y devuelve su ROI."""
    import historico as H
    import medir_historico as MH

    ps = H.partidos(liga)
    if not ps:
        return None, []
    # `liga` viaja para que el λ salga con los parámetros de PRODUCCIÓN
    # (rho, escala, diferencia) y no crudo. Hasta el 2026-09-03 no
    # viajaba, así que este ROI —el que decide en qué ligas la app marca
    # valor— medía un modelo distinto del que se publica. Ver §36 C2.
    filas = MH.evaluar(ps, progreso=progreso, liga=liga)
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
        print(_linea(l + " 1X2", r), flush=True)
        # El mercado de goles, donde la fuente lo publica. Solo el
        # formato clásico (eng, fra) trae over/under; arg y bra no.
        r_ou = roi(apuestas_ou(filas))
        if r_ou["n"]:
            print(_linea(l + " O/U", r_ou), flush=True)
        else:
            print(f"  {l+' O/U':10} la fuente no publica línea de goles para esta liga")

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
