#!/usr/bin/env python3
"""¿Cuando la app dice 70%, pasa el 70% de las veces?

Es una pregunta distinta de "¿acierta?". Un modelo puede acertar bastante
y estar mal calibrado, y ahí todo EV que calcule la app es una ilusión:
el umbral de cuota sale de la probabilidad, así que si la probabilidad
está inflada, el umbral queda bajo y se recomienda una apuesta que en
realidad no paga lo suficiente.

Se diferencia de `backtest.py` en dos cosas:

  - backtest.py RECONSTRUYE lo que el modelo habría dicho, mercado por
    mercado. Este script usa las predicciones que la app efectivamente
    mostró (`data/historial_pronosticos.json`), que es lo que el usuario
    vio en pantalla.
  - backtest.py mira cada mercado por separado. Este los agrega TODOS
    por banda de probabilidad, que es donde se ve si hay un sesgo de
    forma — probabilidades demasiado extremas, por ejemplo — en vez de
    un problema de un mercado puntual.

Encontrado con esto (2026-08-23): las probabilidades altas salen menos de
lo prometido y las bajas salen más. El modelo estira sus probabilidades
hacia los extremos.

    python medir_calibracion.py
"""

import json
import sys
from pathlib import Path

for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

RAIZ = Path(__file__).resolve().parent
HISTORIAL = RAIZ / "data" / "historial_pronosticos.json"

PASO = 0.1   # ancho de cada banda de probabilidad

# Debajo de esto una banda no dice nada: con 5 casos, un desvío de 20
# puntos es lo que pasa por azar. El error más caro que puede inducir
# este script es que alguien toque una constante del modelo por ruido —
# y el repo lo prohíbe explícitamente.
MUESTRA_BANDA = 20


def banda_de(p):
    """A qué franja de 10 puntos pertenece una probabilidad.

    El epsilon no es cosmético: 0.3/0.1 da 2.9999999999999996 en punto
    flotante, así que sin él un 30% caería en la banda 20-30 y el
    diagnóstico saldría corrido. Lo encontró un test.
    """
    i = int(p / PASO + 1e-9)
    if i >= int(1 / PASO):        # p == 1.0 entra en la última, no en una nueva
        i = int(1 / PASO) - 1
    return (round(i * PASO, 10), round((i + 1) * PASO, 10))


def calibrar(pares):
    """[(probabilidad, pasó?)] -> {banda: {n, pred, real, desvio}}.

    `desvio` = real - predicho. Negativo significa que se prometió de
    más (sobreconfianza); positivo, que se quedó corto.
    """
    if not pares:
        return {}
    acum = {}
    for p, paso in pares:
        b = banda_de(p)
        d = acum.setdefault(b, {"n": 0, "suma_p": 0.0, "exitos": 0})
        d["n"] += 1
        d["suma_p"] += p
        d["exitos"] += 1 if paso else 0
    out = {}
    for b, d in acum.items():
        pred = d["suma_p"] / d["n"]
        real = d["exitos"] / d["n"]
        out[b] = {"n": d["n"], "pred": pred, "real": real, "desvio": real - pred}
    return out


def brier(pares):
    """Error cuadrático medio. 0 es perfecto, 0.25 es decir siempre 50%."""
    if not pares:
        return None
    return sum((p - (1.0 if paso else 0.0)) ** 2 for p, paso in pares) / len(pares)


def fiabilidad(pred, real, n):
    """¿El desvío de esta banda es señal o puede ser azar?

    Se compara contra dos errores estándar de una proporción binomial.
    No es un test formal —los mercados de un mismo partido están
    correlacionados y eso lo haría optimista— pero alcanza para separar
    "esto pasa siempre" de "esto pasó tres veces".
    """
    if n < MUESTRA_BANDA:
        return False
    var = pred * (1 - pred) / n
    if var <= 0:
        return False
    return abs(real - pred) > 2 * (var ** 0.5)


def cargar_pares():
    """Todas las predicciones que la app mostró, con lo que pasó.

    Un partido aporta un par por mercado. Ojo: los mercados de un mismo
    partido NO son independientes (si salió 0-0, 'menos de 1.5' y 'no
    marcan los dos' aciertan juntos), así que la muestra efectiva es
    menor que la cantidad de pares.
    """
    from backtest import matriz, suma_si

    with open(HISTORIAL, encoding="utf-8") as f:
        hist = json.load(f)

    # Los mismos mercados que muestra la app, con su test.
    def defs():
        d = {
            "1X2 local":     (lambda i, j: i > j),
            "1X2 empate":    (lambda i, j: i == j),
            "1X2 visitante": (lambda i, j: i < j),
            "Local o empate": (lambda i, j: i >= j),
            "Visita o empate": (lambda i, j: i <= j),
            "Ambos marcan":  (lambda i, j: i > 0 and j > 0),
        }
        for n in (1.5, 2.5, 3.5):
            d[f"Más de {n}"] = (lambda i, j, n=n: i + j > n)
            d[f"Menos de {n}"] = (lambda i, j, n=n: i + j < n)
        return d

    MER = defs()
    pares, por_mercado, partidos = [], {}, 0
    for h in hist.values():
        res = h.get("resultado")
        if not res or len(res) < 2 or res[0] is None:
            continue
        gh, ga = res[0], res[1]
        M = matriz(h["lh"], h["la"], h.get("rho", 0))
        partidos += 1
        for nombre, test in MER.items():
            p = suma_si(M, test)
            paso = test(gh, ga)
            pares.append((p, paso))
            por_mercado.setdefault(nombre, []).append((p, paso))
    return pares, por_mercado, partidos


def barra(pred, real, ancho=22):
    """Dibuja predicho vs real para leer el sesgo de un vistazo."""
    a, b = int(round(pred * ancho)), int(round(real * ancho))
    linea = ["·"] * ancho
    lo, hi = min(a, b), max(a, b)
    for k in range(lo, min(hi, ancho)):
        linea[k] = "─"
    if a < ancho:
        linea[a] = "P"
    if b < ancho:
        linea[b] = "R"
    return "".join(linea)


def main():
    pares, por_mercado, partidos = cargar_pares()
    if not pares:
        print("\n  No hay partidos con resultado todavía.\n")
        return 0

    print(f"\n{'='*70}")
    print("  CALIBRACIÓN — ¿cuando decimos 70%, pasa el 70%?")
    print(f"{'='*70}")
    print(f"\n  {partidos} partidos jugados · {len(pares)} predicciones "
          f"({len(por_mercado)} mercados por partido)")
    print("  Ojo: los mercados de un mismo partido no son independientes,")
    print("  así que la muestra real pesa menos que ese número.")

    cal = calibrar(pares)
    print(f"\n{'─'*70}")
    print("  POR BANDA DE PROBABILIDAD")
    print(f"{'─'*70}\n")
    print(f"  {'banda':<10} {'n':>5}  {'decimos':>8} {'pasa':>8} {'desvío':>8}   P=predicho R=real")
    for b in sorted(cal):
        d = cal[b]
        marca = ""
        if fiabilidad(d["pred"], d["real"], d["n"]):
            marca = " ←" if d["desvio"] < 0 else " ←"
        print(f"  {int(b[0]*100):>3}-{int(b[1]*100):<3}%  {d['n']:>5}  "
              f"{d['pred']*100:>7.1f}% {d['real']*100:>7.1f}% "
              f"{d['desvio']*100:>+7.1f}%   {barra(d['pred'], d['real'])}{marca}")
    print(f"\n  Las bandas con ← se desvían más de lo que explicaría el azar")
    print(f"  (mínimo {MUESTRA_BANDA} casos y más de dos errores estándar).")

    # ── El patrón que importa ────────────────────────────────────────
    altas = [d for b, d in cal.items() if b[0] >= 0.6 and d["n"] >= MUESTRA_BANDA]
    bajas = [d for b, d in cal.items() if b[1] <= 0.4 and d["n"] >= MUESTRA_BANDA]
    print(f"\n{'─'*70}")
    print("  EL PATRÓN")
    print(f"{'─'*70}\n")
    if altas and bajas:
        da = sum(d["desvio"] * d["n"] for d in altas) / sum(d["n"] for d in altas)
        db = sum(d["desvio"] * d["n"] for d in bajas) / sum(d["n"] for d in bajas)
        print(f"  Probabilidades altas (60%+):  {da*100:+.1f}% de desvío")
        print(f"  Probabilidades bajas (<40%):  {db*100:+.1f}% de desvío")
        if da < -0.02 and db > 0.02:
            print("\n  ⚠ SOBRE-DISPERSIÓN: lo que damos por probable pasa menos de lo")
            print("    que decimos, y lo improbable pasa más. El modelo estira sus")
            print("    probabilidades hacia los extremos — se cree más seguro de lo")
            print("    que es, en las dos direcciones.")
            print("\n    Consecuencia directa: el umbral de cuota sale de la")
            print("    probabilidad, así que en las apuestas 'seguras' pedimos menos")
            print("    cuota de la que corresponde y recomendamos precios malos.")
        elif da > 0.02 and db < -0.02:
            print("\n  ⚠ SUB-DISPERSIÓN: las probabilidades son demasiado tibias.")
        else:
            print("\n  Sin un patrón claro de dispersión en las dos puntas.")
    else:
        print("  Todavía no hay suficientes casos en las bandas extremas.")

    # ── Por mercado ──────────────────────────────────────────────────
    print(f"\n{'─'*70}")
    print("  POR MERCADO — dónde duele más")
    print(f"{'─'*70}\n")
    print(f"  {'mercado':<18} {'n':>4}  {'decimos':>8} {'pasa':>8} {'desvío':>8} {'Brier':>7}")
    filas = []
    for nombre, ps in por_mercado.items():
        pred = sum(p for p, _ in ps) / len(ps)
        real = sum(1 for _, x in ps if x) / len(ps)
        filas.append((abs(real - pred), nombre, len(ps), pred, real, brier(ps)))
    for _, nombre, n, pred, real, br in sorted(filas, reverse=True):
        print(f"  {nombre:<18} {n:>4}  {pred*100:>7.1f}% {real*100:>7.1f}% "
              f"{(real-pred)*100:>+7.1f}% {br:>7.4f}")

    b = brier(pares)
    print(f"\n  Brier global: {b:.4f}  (0 es perfecto; 0.25 es decir siempre 50%)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
