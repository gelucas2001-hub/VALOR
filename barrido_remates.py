#!/usr/bin/env python3
"""¿Estimar fuerzas con REMATES en vez de solo goles? Train/test.

Pendiente del proyecto desde el 2026-08-24 (`TRASPASO.md`, "Pendientes
reales del modelo", punto 4): *"Usar remates además de goles para
estimar fuerza. Es una pregunta empírica, ahora respondible porque
existe la vara del punto anterior."* Nunca se probó.

Por qué debería funcionar, en una línea: **un partido tiene 2 o 3 goles
y 25 remates.** Los goles son pocos eventos y por eso ruidosos; los
remates son muchos y por eso estables. Estimar la fuerza de un equipo
con 5 partidos de goles es estimar con ~13 eventos; con remates son
~125. Es la razón por la que los modelos profesionales usan xG, que no
tenemos — remates al arco es el proxy disponible.

Y a diferencia del análisis cualitativo, **esto SÍ se puede medir hacia
atrás**: football-data trae remates y remates al arco por partido en el
formato clásico (eng 4180, fra 3857).

Cómo se prueba:

Se estiman fuerzas por dos vías sobre los MISMOS partidos previos:

- la actual, con goles;
- una con remates al arco, reescalada para que su λ medio coincida con
  el de goles (un equipo remata 12 veces al arco, no marca 12 goles).

Y se mezcla: `λ = w·λ_goles + (1−w)·λ_remates`. w=1.0 es producción.

Se mide Brier del 1X2 y de over/under 2.5, con train (<2022) para
elegir y test (>=2022) para confirmar. Si el ganador de train se da
vuelta en test, no es un hallazgo.

    python barrido_remates.py eng
"""

import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent
CORTE = date(2022, 1, 1)

# w = cuánto pesa el λ de goles. 1.00 es producción (solo goles).
PESOS = [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]

MIN_PREVIOS = 40


def resultados_desde(previos, metrica):
    """Los partidos previos, con la métrica elegida en lugar de los goles.

    `fuerzas_equipos()` no sabe de qué está hecho lo que cuenta: pide
    partidos con un marcador y estima ataque y defensa. Pasarle remates
    al arco en vez de goles estima exactamente lo mismo sobre una señal
    con diez veces más eventos.
    """
    if metrica == "goles":
        return previos
    out = []
    for p in previos:
        est = p.get("est") or {}
        m = est.get(metrica)
        if not m or m.get("h") is None or m.get("a") is None:
            continue
        out.append({**p, "gh": m["h"], "ga": m["a"]})
    return out


def main(argv):
    import actualizar as A
    import backtest
    import historico as H
    import medir_clv
    import medir_historico as MH

    liga = (argv[1] if len(argv) > 1 else "eng").lower()
    metrica = argv[2] if len(argv) > 2 else "al_arco"

    print("\n" + "=" * 76)
    print(f"  ¿FUERZAS CON REMATES EN VEZ DE GOLES? — {liga}, métrica: {metrica}")
    print("=" * 76)
    print(f"\n  w = cuánto pesa el λ de goles. w=1.00 es producción.")
    print(f"  train < {CORTE} elige · test >= {CORTE} confirma\n")

    ps = H.partidos(liga)
    con_est = [p for p in ps if p.get("est", {}).get(metrica)]
    print(f"  {len(con_est)} de {len(ps)} partidos con {metrica}\n")
    if len(con_est) < 500:
        raise SystemExit("  muestra insuficiente")

    rho = (A.COMPETICIONES.get(liga + ".1") or {}).get("rho", 0.0)

    # Una sola pasada: por cada partido se guardan los DOS λ.
    print("  ajustando walk-forward por las dos vías (tarda)...", flush=True)
    filas = []
    for i, p in enumerate(ps):
        if i < MIN_PREVIOS or not p.get("cuotas"):
            continue
        prev = MH.ventana_previa(ps, i)
        if len(prev) < MIN_PREVIOS:
            continue
        pq = medir_clv.devig_shin(p["cuotas"])
        if pq is None:
            continue
        lam = {}
        for via in ("goles", metrica):
            base = resultados_desde(prev, via)
            if len(base) < MIN_PREVIOS:
                lam = None
                break
            f, mu_l, mu_v, pj = A.fuerzas_equipos(base, p["fecha"])
            a_l, d_l = f.get(p["home"], (1.0, 1.0))
            a_v, d_v = f.get(p["away"], (1.0, 1.0))
            lam[via] = (mu_l * a_l * d_v, mu_v * a_v * d_l)
        if not lam:
            continue
        # El λ de remates se reescala al nivel de goles: lo que aporta
        # es la RELACIÓN entre equipos, no la magnitud.
        gl, gv = lam["goles"]
        rl, rv = lam[metrica]
        tot_r = rl + rv
        if tot_r <= 0:
            continue
        esc = (gl + gv) / tot_r
        filas.append({"fecha": p["fecha"], "gl": gl, "gv": gv,
                      "rl": rl * esc, "rv": rv * esc,
                      "real": H.desenlace(p), "real_ou": H.desenlace_ou(p)})
        if len(filas) % 1000 == 0:
            print(f"    {len(filas)} evaluados...", flush=True)

    tr = [f for f in filas if f["fecha"] < CORTE]
    te = [f for f in filas if f["fecha"] >= CORTE]
    print(f"  {len(filas)} partidos · train {len(tr)} · test {len(te)}\n")

    def briers(fs, w):
        b3 = bou = 0.0
        for f in fs:
            lh = w * f["gl"] + (1 - w) * f["rl"]
            la = w * f["gv"] + (1 - w) * f["rv"]
            m = backtest.matriz(max(0.35, min(3.2, lh)), max(0.3, min(3.0, la)), rho)
            p3 = [backtest.suma_si(m, lambda i, j: i > j),
                  backtest.suma_si(m, lambda i, j: i == j),
                  backtest.suma_si(m, lambda i, j: i < j)]
            b3 += sum((p3[k] - f["real"][k]) ** 2 for k in range(3))
            pou = [backtest.suma_si(m, lambda i, j: i + j > 2.5),
                   backtest.suma_si(m, lambda i, j: i + j < 2.5)]
            bou += sum((pou[k] - f["real_ou"][k]) ** 2 for k in range(2))
        return b3 / len(fs), bou / len(fs)

    print(f"  {'w':>5} │ {'Brier 1X2 tr':>12} {'Brier 1X2 te':>12} │ "
          f"{'Brier O/U tr':>12} {'Brier O/U te':>12}")
    print("  " + "-" * 62)
    res = []
    for w in PESOS:
        b3tr, boutr = briers(tr, w)
        b3te, boute = briers(te, w)
        res.append({"w": w, "b3tr": b3tr, "b3te": b3te, "boutr": boutr, "boute": boute})
        marca = "  ← producción" if w == 1.0 else ""
        print(f"  {w:5.2f} │ {b3tr:12.5f} {b3te:12.5f} │ {boutr:12.5f} {boute:12.5f}{marca}")

    prod = next(x for x in res if x["w"] == 1.0)
    mejor_tr = min(res, key=lambda x: x["b3tr"])
    mejor_te = min(res, key=lambda x: x["b3te"])
    print("\n  " + "=" * 72)
    print(f"  1X2 — mejor w en train: {mejor_tr['w']:.2f} · en test: {mejor_te['w']:.2f}"
          f" · producción: 1.00")
    if mejor_tr["w"] == 1.0:
        print("\n  Los goles solos ganan en train. Agregar remates NO mejora:")
        print("  el hallazgo es que no hay hallazgo, y cierra el pendiente.")
    elif mejor_tr["w"] != mejor_te["w"]:
        print("\n  El ganador de train no es el de test: no es estable.")
        print(f"  Con w={mejor_tr['w']:.2f} el Brier de test da {mejor_tr['b3te']:.5f} "
              f"contra {prod['b3te']:.5f} de producción "
              f"({'mejora' if mejor_tr['b3te'] < prod['b3te'] else 'empeora'}).")
    else:
        print(f"\n  w={mejor_tr['w']:.2f} gana en las dos mitades. Brier de test "
              f"{mejor_tr['b3te']:.5f} contra {prod['b3te']:.5f}.")
        print("  Antes de tocar nada: revisar que no esté en el borde de la")
        print("  grilla y correrlo en la otra liga.")
    print("  " + "=" * 72 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
