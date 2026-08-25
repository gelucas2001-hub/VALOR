"""Mide cuánto se aparta el modelo de la línea del mercado, por competición.

No es parte del cron. Se corre a mano antes y después de tocar el modelo
para comprobar que un cambio mejora de verdad y no de palabra:

    python medir_sesgo.py

Un sesgo positivo en "local" significa que el modelo le da más
probabilidad al local que el mercado. La línea se compara SIN margen
(devig proporcional): la cuota cruda implica probabilidades que suman
~1.077, y compararse contra eso haría ver ventaja donde solo hay comisión.

OJO CON COMPARAR ENTRE CORRIDAS: el cron reescribe data/partidos.json dos
veces por día, así que dos mediciones separadas en el tiempo miden
PARTIDOS DISTINTOS y no se pueden comparar entre sí. Medido en la
práctica: el mismo día, con el mismo código, Libertadores dio +12.3pp por
la mañana y +8.7pp después de una actualización del cron. Con 8 partidos
por competición el ruido es enorme.

Para comparar antes/después de un cambio en el modelo hay que usar el
MISMO archivo en las dos mediciones:

    python medir_sesgo.py                      # datos de hoy
    python medir_sesgo.py ruta/a/snapshot.json # un archivo congelado
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from backtest import matriz, suma_si
import medir_clv

PARTIDOS = Path("data/partidos.json")


def probs_modelo(m):
    """(p_local, p_empate, p_visita) según Dixon-Coles para ese partido."""
    M = matriz(m["lh"], m["la"], m["rho"])
    return (suma_si(M, lambda i, j: i > j),
            suma_si(M, lambda i, j: i == j),
            suma_si(M, lambda i, j: i < j))


def probs_mercado(mk):
    """Igual, según la cuota de referencia, con el margen ya descontado.

    Por Shin y no repartiendo el margen parejo: las casas le cargan más
    a la cuota alta, así que dividir por el total infla la probabilidad
    implícita del batacazo y desinfla la del favorito. Como este script
    mide justamente cuánto nos apartamos del mercado, un sesgo acá se
    confunde con sesgo nuestro. Medido en `medir_devig.py`.
    """
    p = medir_clv.devig_shin([mk["local"], mk["empate"], mk["visitante"]])
    return tuple(p) if p else None


def sesgo_por_competicion(partidos):
    por_comp = {}
    for m in partidos:
        mk = m.get("mercado")
        if not mk or not mk.get("local"):
            continue
        pm = probs_modelo(m)
        pq = probs_mercado(mk)
        if not pq:
            continue
        d = por_comp.setdefault(m["comp"], {"n": 0, "local": 0.0, "empate": 0.0,
                                            "visita": 0.0, "magnitud": 0.0})
        d["n"] += 1
        for k, i in (("local", 0), ("empate", 1), ("visita", 2)):
            d[k] += pm[i] - pq[i]
        d["magnitud"] += max(abs(pm[i] - pq[i]) for i in range(3))
    for d in por_comp.values():
        for k in ("local", "empate", "visita", "magnitud"):
            d[k] /= d["n"]
    return por_comp


def main():
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else PARTIDOS
    partidos = json.loads(ruta.read_text(encoding="utf-8"))
    if isinstance(partidos, dict):
        partidos = partidos.get("partidos", [])
    res = sesgo_por_competicion(partidos)
    print(f"fuente: {ruta}\n")
    print(f"{'competición':34} {'n':>3} {'local':>8} {'empate':>8} {'visita':>8} {'|dif|':>8}")
    for comp in sorted(res):
        d = res[comp]
        print(f"{comp:34} {d['n']:3} {d['local']*100:+7.1f}pp {d['empate']*100:+7.1f}pp "
              f"{d['visita']*100:+7.1f}pp {d['magnitud']*100:7.1f}pp")


if __name__ == "__main__":
    main()
