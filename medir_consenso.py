#!/usr/bin/env python3
"""La estrategia SIN MODELO: el consenso del mercado contra una casa.

De dónde sale:

Revisando `sports-betting` (georgedouzas) apareció `OddsComparisonBettor`,
que el README del repo ni menciona. No predice fútbol. Toma el promedio
de cuotas de varias casas como probabilidad real, le resta `alpha` para
descontar el margen, y apuesta donde una casa concreta paga más de lo
que ese consenso justifica. El método viene del paper *Beating the
bookies with their own numbers* (arXiv 1710.02824).

Por qué vale la pena medirlo acá, y por qué es distinto de todo lo
demás que probamos:

- **No depende de que nuestro modelo funcione.** Es ortogonal al
  Dixon-Coles: si el consenso sabe más que nosotros —y está medido que
  sí, capturamos el 39% de lo que sabe el mercado— entonces usarlo
  directamente como verdad es mejor que usar nuestra estimación.
- **No es lo que TRASPASO.md ya descartó.** Aquello usaba `MaxC`, el
  máximo de treinta y pico de casas, y toda la ventaja vivía en que un
  máximo está inflado por serlo. Esto usa el PROMEDIO, que no tiene ese
  sesgo, y apuesta contra una casa real donde de verdad se puede jugar.

Dos límites que hay que decir antes de mirar el número:

1. **`AvgC` probablemente incluye a Bet365 en su promedio.** El paper
   compara contra el consenso de las OTRAS casas. Con 30+ casas en el
   promedio, la contribución de una sola es ~3%, así que el efecto es
   chico — pero está y empuja a favor de la estrategia, no en contra.
2. **La cuota es de CIERRE en las dos puntas.** Si una casa se desvía
   del consenso al cierre, esa desviación es lo más difícil de
   encontrar: para entonces el mercado ya corrigió casi todo. Medido
   así, un resultado positivo es más creíble, no menos.

    python medir_consenso.py eng
    python medir_consenso.py todas
"""

import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent

CORTE = date(2022, 1, 1)

# `alpha` descuenta el margen del consenso. El default del paper y de
# la librería es 0.05; la grilla lo cubre para los dos lados para que un
# óptimo en el borde se vea.
ALPHAS = [0.00, 0.02, 0.04, 0.05, 0.06, 0.08, 0.10, 0.13]

# Tope de cuota, el mismo que rige en la app: arriba de esto no se
# recomienda ni con el modelo propio.
MAX_ODDS = 4.5

MIN_APUESTAS = 100


def apuestas(partidos, alpha=0.05, verdad="promedio", casa="bet365",
             max_odds=MAX_ODDS):
    """Dónde la casa paga más de lo que el consenso justifica."""
    out = []
    for p in partidos or []:
        pc = p.get("por_casa") or {}
        cons, cu = pc.get(verdad), pc.get(casa)
        if not cons or not cu:
            continue
        gh, ga = p["gh"], p["ga"]
        real = [int(gh > ga), int(gh == ga), int(gh < ga)]
        for i in range(3):
            if not cons[i] or not cu[i] or cu[i] > max_odds:
                continue
            prob = 1.0 / cons[i] - alpha
            if prob <= 0:
                continue
            if prob * cu[i] > 1.0:
                out.append({"cuota": cu[i], "gano": real[i] == 1, "i": i,
                            "liga": p.get("liga"), "fecha": p.get("fecha")})
    return out


def roi(aps):
    """ROI con su error estándar. Una ganada devuelve cuota−1, no cuota."""
    n = len(aps or [])
    if not n:
        return {"n": 0, "roi": None, "se": None, "acierto": None,
                "significativo": False}
    ret = [(a["cuota"] - 1) if a["gano"] else -1.0 for a in aps]
    media = sum(ret) / n
    var = sum((r - media) ** 2 for r in ret) / n
    se = (var ** 0.5) / (n ** 0.5)
    return {"n": n, "roi": media, "se": se,
            "acierto": sum(1 for a in aps if a["gano"]) / n,
            "significativo": abs(media) > 2 * se and n >= MIN_APUESTAS}


def main(argv):
    import historico as H

    pedido = (argv[1] if len(argv) > 1 else "eng").lower()
    ligas = sorted(H.LIGAS) if pedido == "todas" else [pedido]
    for l in ligas:
        if l not in H.LIGAS:
            raise SystemExit(f"liga desconocida: {l}. Hay {sorted(H.LIGAS)}")

    print("\n" + "=" * 78)
    print("  EL CONSENSO DEL MERCADO CONTRA UNA CASA — sin modelo propio")
    print("=" * 78)
    print("\n  método: p = 1/cuota_consenso − alpha ; se apuesta si p × cuota_casa > 1")
    print("  (arXiv 1710.02824, vía OddsComparisonBettor de sports-betting)")
    print(f"\n  train: < {CORTE}  ·  test: >= {CORTE}  ·  cuota <= {MAX_ODDS}\n")

    todos = []
    for l in ligas:
        ps = [p for p in H.partidos(l)
              if (p.get("por_casa") or {}).get("promedio")
              and (p.get("por_casa") or {}).get("bet365")]
        print(f"  {l}: {len(ps)} partidos con consenso Y Bet365")
        todos.extend(ps)
    if not todos:
        raise SystemExit("\n  ninguna liga tiene las dos fuentes")

    tr = [p for p in todos if p["fecha"] < CORTE]
    te = [p for p in todos if p["fecha"] >= CORTE]
    print(f"\n  train {len(tr)} · test {len(te)}\n")

    print(f"  {'alpha':>6} │ {'n tr':>6} {'ROI train':>11} │ "
          f"{'n te':>6} {'ROI test':>11} {'±2se':>7} {'acierto':>8}")
    print("  " + "-" * 70)

    res = []
    for a in ALPHAS:
        r_tr = roi(apuestas(tr, alpha=a))
        r_te = roi(apuestas(te, alpha=a))
        if not r_tr["n"] or not r_te["n"]:
            continue
        res.append({"alpha": a, "tr": r_tr, "te": r_te})
        marca = ""
        if r_tr["n"] >= MIN_APUESTAS and r_te["n"] >= MIN_APUESTAS:
            if r_tr["roi"] > 0 and r_te["roi"] > 0:
                marca = "  ← positivo en LAS DOS"
            elif r_tr["roi"] > 0 > r_te["roi"]:
                marca = "  (se da vuelta)"
        print(f"  {a:6.2f} │ {r_tr['n']:6d} {r_tr['roi']*100:+10.2f}% │ "
              f"{r_te['n']:6d} {r_te['roi']*100:+10.2f}% {r_te['se']*200:6.2f} "
              f"{r_te['acierto']*100:7.1f}%{marca}")

    print("\n  " + "=" * 74)
    utiles = [x for x in res
              if x["tr"]["n"] >= MIN_APUESTAS and x["te"]["n"] >= MIN_APUESTAS]
    dobles = [x for x in utiles if x["tr"]["roi"] > 0 and x["te"]["roi"] > 0]
    signif = [x for x in dobles if x["te"]["significativo"]]
    if not dobles:
        print("  NINGÚN alpha da positivo en train Y test. La estrategia del")
        print("  paper no funciona con estos datos — y eso también cierra un")
        print("  camino, que es para lo que se mide.")
    elif not signif:
        print(f"  {len(dobles)} alpha(s) positivo(s) en las dos mitades, pero")
        print("  ninguno se despega del ruido en test.")
        for x in dobles:
            print(f"    alpha {x['alpha']:.2f}: test {x['te']['roi']*100:+.2f}% "
                  f"±{x['te']['se']*200:.2f} sobre {x['te']['n']} apuestas")
    else:
        print(f"  {len(signif)} alpha(s) POSITIVO Y SIGNIFICATIVO en test:")
        for x in signif:
            print(f"    alpha {x['alpha']:.2f}: train {x['tr']['roi']*100:+.2f}% · "
                  f"test {x['te']['roi']*100:+.2f}% ±{x['te']['se']*200:.2f} "
                  f"sobre {x['te']['n']} apuestas")
        print("\n  Antes de creerlo: revisar que el alpha no esté en el borde")
        print("  de la grilla, y recordar que AvgC probablemente incluye a")
        print("  Bet365 en su promedio (empuja a favor de la estrategia).")
    print("  " + "=" * 74 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
