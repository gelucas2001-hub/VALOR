#!/usr/bin/env python3
"""El mercado de córners contra PLATA, no contra calibración.

Por qué existe:

`medir_lineas.py` mide si el número de córners está bien calibrado —
cuando decimos 60%, ¿pasa el 60%? El 2026-08-24 dijo que córners estaba
bien, y eso alcanzó para creer que ahí había algo. No alcanzaba: es
exactamente el error que ya costó tres semanas con el modelo de goles,
donde se midió calibración hasta que alguien midió ROI y daba −6.18%.

Acá se mide contra la línea de cierre real de DraftKings, con el margen
quitado, walk-forward, y la pregunta es si queda plata.

Cómo se consigue el precio:

Las cuotas de córners viven en el endpoint `propBets` de la API interna
de ESPN — el mismo proveedor y sin clave (ver TRASPASO.md §6vicies ter).
El JSON guarda los DOS lados bajo la clave `over`, así que cuál es el
"más de" no viene rotulado. Se resolvió sin mirar resultados: el orden
de los items es estable y el primero es el más de. Verificado sobre 88
partidos por monotonía — la probabilidad del primero baja de 0.559 a
0.464 según sube la línea, que es lo único que puede hacer un "más de".

Qué dio (2026-08-25, 81 líneas de arg.1 y bra.1):

    Brier moneda (siempre 50%)   0.2500
    Brier del MERCADO            0.2492    +0.0008 sobre la moneda
    Brier del MODELO             0.2518    −0.0018 sobre la moneda

    atraso contra el cierre  +0.0026 ± 0.0097   (indistinguible)
    margen de la casa: 8.4% mediano

**La casa pone la línea justo en el punto de la moneda.** El mercado de
córners casi no tiene información —le gana a tirar una moneda por ocho
diezmilésimas— y cobra 8.4% por entrar. Decir "estamos a la par del
mercado" acá suena bien y no significa nada.

El ROI daba +11.2% con umbral de 6%, sobre 41 apuestas, con un error
estándar de ±13.9%. Es ruido: para distinguir ese 11% de cero a dos
errores estándar harían falta ~300 apuestas. Si alguien lee este script
y reporta ese 11.2% como hallazgo, está vendiendo una moneda que salió
cara cuarenta veces — usá `apuestas_necesarias()` antes de hablar.

El sesgo del modelo NO es el problema: predice 9.55 córners y pasan
9.43, +0.12 sobre un promedio de 9.4. El conteo funciona; lo que no hay
es señal que explotar donde la casa pone la línea.

    python medir_corners.py
"""

import math
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Umbral de ventaja a partir del cual se apostaría. No está elegido por
# barrido: es el mismo VALOR_MIN que usa la app para el 1X2, y usar otro
# acá sería medir un producto distinto del que se publica.
UMBRAL = 0.06


def probabilidades(cuotas):
    """(p_mas, p_menos) sin el margen de la casa, desde el par de cuotas.

    El par llega en el orden en que ESPN lo publica, y el primero es el
    "más de" — ver el encabezado. En un mercado de DOS opciones, Shin
    (1993) no corrige nada y devuelve el proporcional; eso es correcto y
    no un atajo, está en CLAUDE.md.
    """
    if not cuotas or len(cuotas) != 2:
        return None
    try:
        a, b = float(cuotas[0]), float(cuotas[1])
    except (TypeError, ValueError):
        return None
    if not (a > 1 and b > 1):
        return None
    s = 1.0 / a + 1.0 / b
    return (1.0 / a) / s, (1.0 / b) / s


def margen(cuotas):
    """Cuánto se queda la casa, en tanto por uno. 0.084 es 8.4%."""
    if not cuotas or len(cuotas) != 2:
        return None
    try:
        a, b = float(cuotas[0]), float(cuotas[1])
    except (TypeError, ValueError):
        return None
    if not (a > 1 and b > 1):
        return None
    return 1.0 / a + 1.0 / b - 1.0


def lado(p_modelo, cuotas, umbral=UMBRAL):
    """A qué lado apostar, o None si a ninguno.

    Devuelve ("mas"|"menos", cuota, ventaja). Se compara contra la
    probabilidad SIN margen: comparar contra la cruda haría ver ventaja
    donde solo hay comisión.
    """
    q = probabilidades(cuotas)
    if q is None or p_modelo is None:
        return None
    v_mas = p_modelo - q[0]
    v_menos = (1.0 - p_modelo) - q[1]
    if v_mas >= umbral and v_mas >= v_menos:
        return ("mas", float(cuotas[0]), v_mas)
    if v_menos >= umbral:
        return ("menos", float(cuotas[1]), v_menos)
    return None


def retorno(cuota, gano):
    """Lo que deja una apuesta de 1. Ganar paga `cuota - 1`, perder −1."""
    return (float(cuota) - 1.0) if gano else -1.0


def resultado(apuestas):
    """ROI de una lista de (cuota, gano), con su error estándar.

    El error estándar es lo que separa un hallazgo de una racha, y en
    este mercado es lo único que evita reportar un +11% que es ruido.
    """
    aps = list(apuestas or [])
    if not aps:
        return None
    ret = [retorno(c, g) for c, g in aps]
    n = len(ret)
    roi = statistics.fmean(ret)
    sd = statistics.pstdev(ret) if n > 1 else 0.0
    ee = sd / math.sqrt(n) if n else 0.0
    return {"n": n, "roi": roi, "ee": ee, "sd": sd,
            "aciertos": sum(1 for _, g in aps if g) / n,
            "significativo": ee > 0 and abs(roi) > 2 * ee}


def apuestas_necesarias(roi, sd=0.95, sigmas=2):
    """Cuántas apuestas harían falta para distinguir ese ROI de cero.

    Existe para que nadie reporte un ROI sin poder decir, en la misma
    frase, si la muestra alcanzaba. Con el ROI medido (+11.2%) y la
    dispersión típica de una apuesta plana, da ~300.
    """
    if not roi:
        return None
    return int(math.ceil((sigmas * sd / abs(roi)) ** 2))


def brier(p, paso):
    return (p - (1 if paso else 0)) ** 2


def contra_el_cierre(filas):
    """Brier del modelo, del mercado y de la moneda, sobre las mismas filas.

    `filas` son dicts con `p` (modelo), `q` (mercado sin margen) y
    `paso` (si el total superó la línea).

    La moneda está a propósito: en un mercado de over/under la casa pone
    la línea cerca del 50%, así que el mercado mismo apenas le gana. Sin
    esa referencia, "estamos a la par del mercado" se lee como un logro
    cuando puede ser un empate en cero.
    """
    fs = list(filas or [])
    if not fs:
        return None
    bm = statistics.fmean(brier(f["p"], f["paso"]) for f in fs)
    bq = statistics.fmean(brier(f["q"], f["paso"]) for f in fs)
    bc = statistics.fmean(brier(0.5, f["paso"]) for f in fs)
    ds = [brier(f["p"], f["paso"]) - brier(f["q"], f["paso"]) for f in fs]
    n = len(ds)
    ee = math.sqrt(statistics.pvariance(ds) / n) if n > 1 else 0.0
    return {"n": n, "modelo": bm, "mercado": bq, "moneda": bc,
            "atraso": bm - bq, "ee": ee,
            "mercado_sobre_moneda": bc - bq,
            "modelo_sobre_moneda": bc - bm}


def main():
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
