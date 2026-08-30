#!/usr/bin/env python3
"""¿El modelo aplasta los extremos hacia el promedio?

De dónde sale la pregunta:

Lucas vio Unión–Sarmiento con ~2.70 goles esperados y una escalera de
"pocos goles" y "no marcan ambos". Terminó 4-1. Su objeción: los dos
equipos convierten y reciben, no era un partido para esperar poco gol.

La hipótesis que eso sugiere, y que NUNCA se midió: la regularización
(`PRIOR_FUERZA`, los "partidos fantasma" que empujan hacia 1.0) puede
estar comprimiendo el rango de λ. Si es así:

- los partidos de equipos goleadores quedan SUBESTIMADOS
- los de equipos trabados quedan SOBREESTIMADOS
- y **en agregado calibra bien, porque los errores se cancelan**

Ese último punto es el que importa: explicaría por qué ninguna medición
agregada lo detectó nunca. `medir_historico.py` mira calibración por
banda de probabilidad del 1X2; `barrido_lambda.py` mira over 2.5 en
total. Ninguno parte por λ predicho.

Cómo se mide:

Se agrupan los partidos por el λ total que el modelo predijo (lh + la)
y se compara contra los goles que realmente pasaron en ese grupo. Un
modelo sin compresión da la identidad: donde dice 2.0 pasan ~2.0, donde
dice 3.2 pasan ~3.2. Uno comprimido da una recta más plana que la
identidad — pendiente < 1.

La pendiente de la regresión de real contra predicho es el número que
resume todo. **Ojo con el signo, es fácil leerlo al revés:** la
regresión es `real ~ predicho`, así que

    pendiente ~ 1.0   el modelo usa exactamente el rango de la realidad
    pendiente < 1.0   EXAGERA: su rango es más ancho que el real. Donde
                      dice 3.1 pasan 2.4, donde dice 1.8 pasan 2.1.
    pendiente > 1.0   COMPRIME: su rango es más angosto que el real

Es al revés de lo que sugiere la intuición, porque lo que varía de más
es la variable de la derecha (el predicho), no la de la izquierda.

Y se compara contra el ruido, no contra cero: con muestra finita, una
pendiente de exactamente 1.0 no sale nunca. El error estándar de la
pendiente dice cuánto se puede apartar por azar.

    python medir_compresion.py arg
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent

# Franjas de λ total predicho. Bordes elegidos para que cada una tenga
# muestra: la distribución de λ se concentra entre 2.2 y 3.0.
FRANJAS = [(0.0, 2.0), (2.0, 2.2), (2.2, 2.4), (2.4, 2.6),
           (2.6, 2.8), (2.8, 3.0), (3.0, 3.3), (3.3, 9.9)]

MIN_N = 40


def pendiente(pares):
    """Regresión simple de real contra predicho, con su error estándar.

    Devuelve (pendiente, error_estandar, n). La pendiente es lo que
    contesta la pregunta: 1.0 es un modelo que usa todo su rango.
    """
    n = len(pares)
    if n < 3:
        return None, None, n
    sx = sum(p for p, _ in pares)
    sy = sum(r for _, r in pares)
    mx, my = sx / n, sy / n
    sxx = sum((p - mx) ** 2 for p, _ in pares)
    if sxx <= 0:
        return None, None, n
    sxy = sum((p - mx) * (r - my) for p, r in pares)
    b = sxy / sxx
    # Error estándar de la pendiente: sqrt(varianza residual / Sxx)
    resid = sum((r - (my + b * (p - mx))) ** 2 for p, r in pares)
    se = ((resid / (n - 2)) / sxx) ** 0.5 if n > 2 else None
    return b, se, n


def main(argv):
    import historico as H
    import medir_historico as MH

    liga = (argv[1] if len(argv) > 1 else "arg").lower()
    if liga not in H.LIGAS:
        raise SystemExit(f"liga desconocida: {liga}. Hay {sorted(H.LIGAS)}")

    print("\n" + "=" * 72)
    print(f"  ¿EL MODELO APLASTA LOS EXTREMOS? — {liga}")
    print("=" * 72)
    print("\n  ajustando walk-forward...", flush=True)

    filas = MH.evaluar(H.partidos(liga), progreso=2000)
    print(f"  {len(filas)} partidos evaluados\n")

    # (λ predicho, goles reales) por partido
    pares = []
    for f in filas:
        lam = f["lh"] + f["la"]
        real = f["real_ou"]  # no sirve: es binario. Se recalcula abajo.
        pares.append((lam, f))

    # Los goles reales no vienen en la fila; se recuperan del desenlace
    # del partido original. `evaluar` no los guarda, así que se rehace
    # el cruce por fecha y equipos — barato comparado con el ajuste.
    idx = {}
    for p in H.partidos(liga):
        idx[(p["fecha"], p["home"], p["away"])] = p["gh"] + p["ga"]

    datos = []
    for lam, f in pares:
        g = idx.get((f["fecha"], f["home"], f["away"]))
        if g is not None:
            datos.append((lam, g))

    print(f"  {'franja λ':>14} {'n':>6} {'predicho':>10} {'real':>8} {'desvío':>9}")
    print("  " + "-" * 52)
    for lo, hi in FRANJAS:
        sel = [(l, g) for l, g in datos if lo <= l < hi]
        if len(sel) < MIN_N:
            continue
        pred = sum(l for l, _ in sel) / len(sel)
        real = sum(g for _, g in sel) / len(sel)
        marca = "  ←" if abs(pred - real) > 0.15 else ""
        print(f"  {lo:5.1f}-{hi:<5.1f} {len(sel):8d} {pred:10.2f} "
              f"{real:8.2f} {real-pred:+9.2f}{marca}")

    b, se, n = pendiente(datos)
    print("\n  " + "=" * 68)
    if b is None:
        print("  muestra insuficiente para la regresión")
        return 0
    print(f"  pendiente de real contra predicho: {b:.3f} ± {2*se:.3f}  (n={n})")
    lo, hi = b - 2 * se, b + 2 * se
    if lo <= 1.0 <= hi:
        print("\n  El 1.0 está DENTRO del intervalo: el modelo usa el rango")
        print("  que la realidad tiene. Un caso puntual que se haya visto mal")
        print("  fue varianza, no un defecto sistemático de λ.")
    elif hi < 1.0:
        print(f"\n  EXAGERA: pendiente {b:.3f}, y el 1.0 queda afuera del")
        print("  intervalo. El modelo se separa del promedio MÁS de lo que la")
        print("  realidad se separa: donde dice mucho gol pasan menos, y donde")
        print("  dice poco gol pasan más.")
        print("\n  En agregado se cancela — por eso ninguna medición promedio")
        print("  lo veía. Y produce apuestas perdedoras por construcción: se")
        print("  apuesta over donde el modelo infló y under donde desinfló.")
        print(f"\n  El modelo estira su rango {1/b:.1f} veces más que la realidad.")
    else:
        print(f"\n  COMPRIME: pendiente {b:.3f}, mayor que 1. Su rango es más")
        print("  angosto que el real — le da a todos un número parecido al")
        print("  promedio de la liga, que calibra bien y no sirve para apostar.")
    print("  " + "=" * 68 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
