#!/usr/bin/env python3
"""¿Y si medimos al precio al que SÍ apostamos? Apertura, y CLV.

Dos cosas que este proyecto daba por cerradas y no lo estaban.

**1. Todo el ROI se midió contra la cuota de CIERRE.**

El cierre es el precio más difícil que existe: para entonces la línea
ya incorporó el dinero informado, las alineaciones y las lesiones de
último momento. Pero **la app no apuesta al cierre** — apuesta cuando
el usuario mira, horas o días antes. Medir contra un precio al que
nunca se apuesta y concluir "no hay ventaja" es un sesgo de método, no
un hallazgo sobre el modelo.

**2. El CLV se puede medir hacia atrás.**

`TRASPASO.md` §6sexdecies dice que no: "ESPN borra el bloque de cuotas
cuando el partido termina... el CLV no se puede medir hacia atrás. Hay
que ir guardando". Es cierto para ESPN y **falso para football-data**,
que publica apertura y cierre de cada partido. La afirmación se escribió
mirando una fuente y se generalizó a todas — el mismo error que
§6vicies ter documenta con `propBets`.

Por qué importa más que el ROI: el CLV contesta con cientos de apuestas
lo que al ROI le lleva miles. Si la línea se mueve sistemáticamente
hacia donde apostamos, hay información real en el modelo aunque la
muestra de resultados todavía no lo muestre. Y si no se mueve, no la
hay aunque una racha diga que sí.

Cómo se mide el CLV acá:

    CLV = (cuota_tomada × prob_cierre_devigada) − 1

Positivo significa que al precio de cierre, esa apuesta tenía valor
esperado positivo — o sea que entramos antes de que el mercado
corrigiera hacia nuestro lado. Se devigan las dos puntas con Shin.

    python medir_apertura.py eng
    python medir_apertura.py todas
"""

import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent
CORTE = date(2022, 1, 1)


def _clv(cuota_tomada, cuota_cierre):
    """Cuánto mejor fue el precio que conseguimos, contra el de cierre.

        CLV = cuota_tomada / cuota_cierre − 1

    Positivo = entramos a mejor precio del que terminó habiendo, o sea
    la línea se movió HACIA nuestro lado después de que apostamos. Es
    la señal de que sabíamos algo que el mercado todavía no.

    **Ojo con la versión que parece más natural y está mal:**
    `cuota_tomada × prob_cierre_devigada − 1`. Esa compara una cuota
    CON margen contra una probabilidad SIN margen, así que da negativo
    —aproximadamente el margen de la casa— aunque la línea no se haya
    movido un centímetro. Medido así, todo tiene CLV de −4% y parece un
    hallazgo devastador cuando es solo la comisión. Precio contra
    precio: las dos puntas tienen que traer el margen o ninguna.
    """
    if not cuota_cierre:
        return None
    return cuota_tomada / cuota_cierre - 1.0


def apuestas_apertura(filas, partidos_idx, casa="pinnacle",
                      valor_min=None, valor_max=None, max_odds=None):
    """Las mismas apuestas de la regla, pero tomadas al precio de apertura.

    `filas` son las de `medir_historico.evaluar()` (traen el modelo
    walk-forward); `partidos_idx` mapea (fecha, home, away) al partido
    con sus cuotas de apertura y cierre.
    """
    import medir_clv
    import medir_roi as R

    vmin = R.VALOR_MIN if valor_min is None else valor_min
    vmax = R.VALOR_MAX if valor_max is None else valor_max
    modds = R.MAX_ODDS if max_odds is None else max_odds

    out = []
    for f in filas or []:
        p = partidos_idx.get((f["fecha"], f["home"], f["away"]))
        if not p:
            continue
        ap = (p.get("apertura") or {}).get(casa)
        ci = (p.get("por_casa") or {}).get(casa)
        if not ap or not ci:
            continue
        # La ventaja se calcula contra el precio de APERTURA devigado:
        # es el que había cuando se hubiera apostado. Usar el cierre acá
        # sería mirar el futuro.
        pq_ap = medir_clv.devig_shin(ap)
        pq_ci = medir_clv.devig_shin(ci)
        if pq_ap is None or pq_ci is None:
            continue
        for i in range(3):
            ventaja = f["modelo"][i] - pq_ap[i]
            if not (vmin <= ventaja <= vmax) or ap[i] > modds:
                continue
            out.append({"cuota": ap[i], "gano": f["real"][i] == 1,
                        "ventaja": ventaja, "liga": f.get("liga"),
                        "fecha": f["fecha"], "i": i,
                        "clv": _clv(ap[i], ci[i]),
                        "cierre": ci[i]})
    return out


def resumen_clv(aps):
    """CLV medio con su incertidumbre, y cuántas veces la línea nos dio la razón."""
    n = len(aps or [])
    if not n:
        return None
    clvs = [a["clv"] for a in aps]
    m = sum(clvs) / n
    var = sum((c - m) ** 2 for c in clvs) / n
    se = (var ** 0.5) / (n ** 0.5)
    favor = sum(1 for a in aps if a["clv"] > 0)
    return {"n": n, "clv": m, "se": se, "a_favor": favor / n,
            "significativo": abs(m) > 2 * se and n >= 100}


def main(argv):
    import historico as H
    import medir_historico as MH
    import medir_roi as R

    pedido = (argv[1] if len(argv) > 1 else "eng").lower()
    ligas = sorted(H.LIGAS) if pedido == "todas" else [pedido]

    print("\n" + "=" * 78)
    print("  EL PRECIO AL QUE SÍ APOSTAMOS — apertura contra cierre, y CLV")
    print("=" * 78)
    print("\n  Todo el ROI del proyecto se midió contra el CIERRE, que es el")
    print("  precio más difícil que existe. La app apuesta antes.\n")

    for liga in ligas:
        ps = H.partidos(liga)
        idx = {(p["fecha"], p["home"], p["away"]): p for p in ps}
        con_ap = sum(1 for p in ps if p.get("apertura"))
        if not con_ap:
            print(f"  {liga}: la fuente no publica cuota de apertura\n")
            continue
        print(f"  {liga}: {con_ap} de {len(ps)} partidos con apertura. "
              f"Ajustando walk-forward...", flush=True)
        filas = MH.evaluar(ps, progreso=None)
        te = [f for f in filas if f["fecha"] >= CORTE]

        for casa in ("pinnacle", "bet365"):
            aps_ap = apuestas_apertura(te, idx, casa=casa)
            if not aps_ap:
                continue
            r_ap = R.roi(aps_ap)
            # Las mismas apuestas, pero cobradas al cierre: aísla el
            # efecto del PRECIO de entrada, con la misma selección.
            r_ci = R.roi([{**a, "cuota": a["cierre"]} for a in aps_ap])
            c = resumen_clv(aps_ap)
            print(f"\n    {casa}  ({r_ap['n']} apuestas en test)")
            print(f"      ROI a la APERTURA : {r_ap['roi']*100:+6.2f}% "
                  f"±{r_ap['se']*200:5.2f}   caída {r_ap['drawdown']:5.1f}u")
            print(f"      ROI al CIERRE     : {r_ci['roi']*100:+6.2f}% "
                  f"±{r_ci['se']*200:5.2f}   caída {r_ci['drawdown']:5.1f}u")
            print(f"      diferencia        : {(r_ap['roi']-r_ci['roi'])*100:+6.2f} "
                  f"puntos de ROI por entrar antes")
            if c:
                marca = "" if c["significativo"] else "  (ruido)"
                print(f"      CLV               : {c['clv']*100:+6.2f}% "
                      f"±{c['se']*200:5.2f}   la línea vino hacia nosotros el "
                      f"{c['a_favor']*100:.1f}% de las veces{marca}")
        print()

    print("  " + "=" * 74)
    print("  El CLV es lo que contesta rápido: si la línea se mueve hacia")
    print("  donde apostamos, hay información real en el modelo aunque la")
    print("  muestra de resultados todavía no lo muestre. Si no se mueve,")
    print("  no la hay aunque una racha diga que sí.")
    print("  " + "=" * 74 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
