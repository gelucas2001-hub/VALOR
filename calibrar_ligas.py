"""Calibra cuánto vale cada liga sudamericana, usando los cruces de copa.

El problema que resuelve: la fuerza doméstica de un equipo es relativa al
promedio de SU liga. Un 1.30 de ataque en Brasil y un 1.30 en Paraguay no
son lo mismo, pero el modelo los trata igual — por eso ancla mal (medido:
el ancla sola solo bajó 1.3pp el sesgo de Libertadores, y empeoró
Sudamericana).

Los partidos de copa son el puente entre ligas: si los brasileños le
meten más a los paraguayos que al revés, Brasil vale más. Con eso se
estima un factor de calidad por liga, sin necesitar la fuerza individual
de cada equipo.

Modelo: para un cruce entre un local de la liga A y un visitante de la B,
    goles esperados del local    = mu_local  * q_A / q_B
    goles esperados del visitante = mu_visita * q_B / q_A
y se ajustan los q por mínimos multiplicativos, regularizados hacia 1.

Se corre a mano y escribe data/factores_liga.json:

    python calibrar_ligas.py
"""
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import actualizar as A

COPAS = ("conmebol.libertadores", "conmebol.sudamericana")
TEMPORADAS = 3          # temporadas hacia atrás (incluye la actual)
ITERACIONES = 60
PRIOR_LIGA = 8          # "partidos fantasma" a nivel 1.0 por liga, para que
                         # una liga con 3 cruces no se vaya a un extremo
MIN_CRUCES = 40         # cruces mínimos para creerle al factor de una liga.
                         # Sin este piso, bra.2 salía 1.352 con 20 cruces — más
                         # alto que bra.1 (1.235), o sea el modelo "aprendía"
                         # que la segunda división brasileña es mejor que la
                         # primera. Con menos muestra que esto, la liga queda
                         # en 1.0 (neutro) en vez de meter ruido con cara de
                         # dato.
SALIDA = Path("data/factores_liga.json")


def juntar_partidos(hoy):
    """Cruces de copa de las últimas temporadas, con la liga de cada equipo."""
    cache_ligas = {}
    if A.CACHE_LIGAS.exists():
        try:
            cache_ligas = json.loads(A.CACHE_LIGAS.read_text(encoding="utf-8"))
        except Exception:
            cache_ligas = {}

    crudos = []
    for slug in COPAS:
        for season in range(hoy.year, hoy.year - TEMPORADAS, -1):
            try:
                r = A.resultados_temporada(slug, season, hoy)
            except Exception as e:
                print(f"  ! {slug} {season}: {e}")
                continue
            print(f"  · {slug} {season}: {len(r)} partidos")
            for p in r:
                crudos.append((slug, p))

    # liga de cada equipo (una consulta por equipo, cacheada en disco)
    ids = {p["home"] for _, p in crudos} | {p["away"] for _, p in crudos}
    print(f"\n  resolviendo la liga de {len(ids)} equipos...")
    for tid in ids:
        A.liga_domestica(tid, COPAS[0], cache_ligas)
    A.CACHE_LIGAS.write_text(json.dumps(cache_ligas, ensure_ascii=False, indent=1),
                             encoding="utf-8")

    partidos = []
    sin_liga = 0
    for _slug, p in crudos:
        la = cache_ligas.get(str(p["home"]))
        lb = cache_ligas.get(str(p["away"]))
        if not la or not lb:
            sin_liga += 1
            continue
        if la == lb:
            continue          # cruce entre dos equipos del mismo país: no informa
        partidos.append({"liga_local": la, "liga_visita": lb,
                         "gh": p["gh"], "ga": p["ga"]})
    print(f"  cruces entre ligas distintas: {len(partidos)} "
          f"({sin_liga} descartados por liga desconocida)")
    return partidos


def calibrar(partidos):
    """Factor de calidad por liga. 1.0 = promedio; >1 mejor."""
    if not partidos:
        return {}, 1.0, 1.0

    mu_local = sum(p["gh"] for p in partidos) / len(partidos)
    mu_visita = sum(p["ga"] for p in partidos) / len(partidos)

    ligas = {p["liga_local"] for p in partidos} | {p["liga_visita"] for p in partidos}
    q = {l: 1.0 for l in ligas}

    for _ in range(ITERACIONES):
        num = {l: PRIOR_LIGA for l in ligas}
        den = {l: PRIOR_LIGA for l in ligas}
        for p in partidos:
            a, b = p["liga_local"], p["liga_visita"]
            pred_h = mu_local * q[a] / q[b]
            pred_a = mu_visita * q[b] / q[a]
            # goles hechos vs esperados, para cada lado
            num[a] += p["gh"]; den[a] += pred_h
            num[b] += p["ga"]; den[b] += pred_a
            # y goles recibidos: recibir menos de lo esperado también sube
            num[a] += pred_a; den[a] += p["ga"]
            num[b] += pred_h; den[b] += p["gh"]
        nuevo = {l: q[l] * (num[l] / den[l]) ** 0.25 for l in ligas}   # amortiguado
        media = sum(nuevo.values()) / len(nuevo)
        q = {l: v / media for l, v in nuevo.items()}

    return q, mu_local, mu_visita


def main():
    hoy = datetime.date.today()
    print("Juntando cruces de copa...")
    partidos = juntar_partidos(hoy)
    q, mu_l, mu_v = calibrar(partidos)

    cuenta = {}
    for p in partidos:
        cuenta[p["liga_local"]] = cuenta.get(p["liga_local"], 0) + 1
        cuenta[p["liga_visita"]] = cuenta.get(p["liga_visita"], 0) + 1

    # Piso de muestra: una liga con pocos cruces no tiene factor creíble.
    finales, descartadas = {}, []
    for l, v in q.items():
        if cuenta.get(l, 0) < MIN_CRUCES:
            finales[l] = 1.0
            descartadas.append((l, v, cuenta.get(l, 0)))
        else:
            finales[l] = v

    print(f"\nmu local {mu_l:.3f} · mu visita {mu_v:.3f}\n")
    print(f"{'liga':10} {'factor':>8} {'cruces':>8}")
    for l in sorted(finales, key=lambda x: -finales[x]):
        marca = "  (poca muestra → neutro)" if finales[l] == 1.0 and l in dict((d[0], 1) for d in descartadas) else ""
        print(f"{l:10} {finales[l]:8.3f} {cuenta.get(l,0):8}{marca}")
    for l, v, n in descartadas:
        print(f"\n  ! {l} habría dado {v:.3f} con solo {n} cruces — se deja en 1.0")

    SALIDA.write_text(json.dumps({
        "generado": hoy.isoformat(),
        "n_cruces": len(partidos),
        "min_cruces": MIN_CRUCES,
        "factores": {l: round(v, 4) for l, v in finales.items()},
        "cruces_por_liga": cuenta,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()
