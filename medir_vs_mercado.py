"""¿Le gana nuestro modelo a la cuota de cierre del mercado?

Compara la probabilidad del modelo contra la cuota de cierre real de
partidos ya jugados de Liga Profesional, usando el CSV público de
football-data.co.uk. La cuota de cierre es el precio más afinado que
existe: ya absorbió lesiones, alineaciones y apuestas informadas.

El spec daba por imposible medir esto, porque ESPN borra las cuotas
cuando el partido termina. Cierto de ESPN, falso del mundo.

Evaluación walk-forward: las λ de cada partido se calculan SOLO con
partidos anteriores a esa fecha. Nunca ve el resultado que predice.

No es parte del cron. Se corre a mano:

    python medir_vs_mercado.py

Deliberadamente NO cubre Libertadores/Sudamericana: el dataset es de
ligas, no de copas. El sesgo de copas se mide con medir_sesgo.py.
"""
import csv
import datetime
import io
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from backtest import matriz, suma_si
import actualizar as A

CSV_URL = "https://www.football-data.co.uk/new/ARG.csv"
TEMPORADA = "2026"
MIN_PREVIOS = 40        # partidos de historia mínimos para pronosticar

# ESPN -> football-data. Explícita a propósito: el cruce automático por
# substring hace matchear "Independiente Rivadavia" con "Independiente",
# y eso ensucia los resultados en silencio.
NOMBRES = {
    "Aldosivi": "Aldosivi",
    "Argentinos Juniors": "Argentinos Jrs",
    "Atlético Tucumán": "Atl. Tucuman",
    "Banfield": "Banfield",
    "Barracas Central": "Barracas Central",
    "Belgrano (Córdoba)": "Belgrano",
    "Boca Juniors": "Boca Juniors",
    "Central Córdoba (Santiago del Estero)": "Central Cordoba",
    "Defensa y Justicia": "Defensa y Justicia",
    "Deportivo Riestra": "Dep. Riestra",
    "Estudiantes de La Plata": "Estudiantes L.P.",
    "Estudiantes de Río Cuarto": "Estudiantes Rio Cuarto",
    "Gimnasia (Mendoza)": "Gimnasia Mendoza",
    "Gimnasia La Plata": "Gimnasia L.P.",
    "Huracán": "Huracan",
    "Independiente": "Independiente",
    "Independiente Rivadavia": "Ind. Rivadavia",
    "Instituto (Córdoba)": "Instituto",
    "Lanús": "Lanus",
    "Newell's Old Boys": "Newells Old Boys",
    "Platense": "Platense",
    "Racing Club": "Racing Club",
    "River Plate": "River Plate",
    "Rosario Central": "Rosario Central",
    "San Lorenzo": "San Lorenzo",
    "Sarmiento (Junín)": "Sarmiento Junin",
    "Talleres (Córdoba)": "Talleres Cordoba",
    "Tigre": "Tigre",
    "Unión (Santa Fe)": "Union de Santa Fe",
    "Vélez Sarsfield": "Velez Sarsfield",
}


def bajar_csv():
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": A.UA})
    txt = urllib.request.urlopen(req, timeout=60).read().decode("utf-8-sig", "replace")
    return list(csv.DictReader(io.StringIO(txt)))


def verificar_nombres(filas):
    """Corta si algún equipo del CSV no está mapeado. Un nombre suelto
    significa partidos descartados en silencio, peor que un error ruidoso."""
    del_csv = {r["Home"] for r in filas} | {r["Away"] for r in filas}
    faltan = del_csv - set(NOMBRES.values())
    if faltan:
        raise SystemExit(f"equipos del CSV sin mapear: {sorted(faltan)}")
    return len(del_csv)


def construir_ids(hoy):
    """{nombre de football-data: team_id de ESPN}, desde la tabla de
    posiciones, que trae displayName e id juntos."""
    tabla = A.tabla_competicion("arg.1", hoy.year)
    ids, sin_mapear = {}, set()
    for info in tabla.values():
        for fila in info.get("filas", []):
            fd = NOMBRES.get(fila["t"])
            if fd:
                ids[fd] = fila["id"]
            elif fila["t"]:
                sin_mapear.add(fila["t"])
    if sin_mapear:
        print(f"  aviso: equipos de ESPN sin mapear -> {sorted(sin_mapear)}")
    return ids


def evaluar():
    filas = [r for r in bajar_csv()
             if r["Season"] == TEMPORADA and (r.get("AvgCH") or "").strip()]
    n_eq = verificar_nombres(filas)
    print(f"CSV: {len(filas)} partidos con cuota de cierre, {n_eq} equipos, todos mapeados")

    hoy = datetime.date.today()
    ids = construir_ids(hoy)
    print(f"cruzados con ESPN: {len(ids)} equipos")

    resultados = A.resultados_temporada("arg.1", hoy.year, hoy)
    print(f"historial de ESPN: {len(resultados)} partidos jugados\n")

    rho = A.COMPETICIONES["arg.1"]["rho"]
    cache_fuerzas = {}          # fecha -> ajuste con los partidos previos
    br_mod = br_mkt = br_nul = 0.0
    ll_mod = ll_mkt = 0.0
    n = saltados = 0

    for r in sorted(filas, key=lambda x: x["Date"]):
        try:
            fecha = datetime.datetime.strptime(r["Date"], "%d/%m/%Y").date()
            gh, ga = int(r["HG"]), int(r["AG"])
            cuotas = [float(r["AvgCH"]), float(r["AvgCD"]), float(r["AvgCA"])]
        except (ValueError, KeyError):
            saltados += 1
            continue
        if r["Home"] not in ids or r["Away"] not in ids:
            saltados += 1
            continue

        previos = [p for p in resultados if p["fecha"] < fecha]
        if len(previos) < MIN_PREVIOS:
            saltados += 1
            continue
        if fecha not in cache_fuerzas:
            cache_fuerzas[fecha] = A.fuerzas_equipos(previos, fecha)
        fuerzas, mu_l, mu_v, _pj = cache_fuerzas[fecha]

        a_l, d_l = fuerzas.get(ids[r["Home"]], (1.0, 1.0))
        a_v, d_v = fuerzas.get(ids[r["Away"]], (1.0, 1.0))
        lh = max(0.35, min(3.20, mu_l * a_l * d_v))
        la = max(0.30, min(3.00, mu_v * a_v * d_l))

        M = matriz(lh, la, rho)
        pm = [suma_si(M, lambda i, j: i > j),
              suma_si(M, lambda i, j: i == j),
              suma_si(M, lambda i, j: i < j)]
        crudas = [1 / c for c in cuotas]
        tot = sum(crudas)
        pq = [x / tot for x in crudas]

        real = [int(gh > ga), int(gh == ga), int(gh < ga)]
        idx = real.index(1)
        br_mod += sum((pm[i] - real[i]) ** 2 for i in range(3))
        br_mkt += sum((pq[i] - real[i]) ** 2 for i in range(3))
        # línea base del que no sabe nada: 1/3 a cada resultado. Sirve para
        # saber si la distancia contra el mercado es mucha o poca.
        br_nul += sum((1/3 - real[i]) ** 2 for i in range(3))
        ll_mod -= __import__("math").log(max(pm[idx], 1e-15))
        ll_mkt -= __import__("math").log(max(pq[idx], 1e-15))
        n += 1

    return n, saltados, br_mod, br_mkt, br_nul, ll_mod, ll_mkt


def main():
    n, saltados, brm, brq, brn, llm, llq = evaluar()
    if not n:
        raise SystemExit("no se evaluó ningún partido — revisar el cruce de nombres")
    print(f"partidos evaluados: {n}  (saltados: {saltados})\n")
    print(f"{'':22} {'Brier':>10}   (más bajo = mejor)")
    print(f"{'sin saber nada (1/3)':22} {brn/n:10.5f}")
    print(f"{'nuestro modelo':22} {brm/n:10.5f}")
    print(f"{'cuota de cierre':22} {brq/n:10.5f}")
    print(f"\n{'log loss modelo':22} {llm/n:10.5f}")
    print(f"{'log loss mercado':22} {llq/n:10.5f}")

    margen_mercado = (brn - brq) / n     # cuánto sabe el mercado
    margen_nuestro = (brn - brm) / n     # cuánto sabemos nosotros
    print()
    if margen_mercado > 0:
        pct = margen_nuestro / margen_mercado * 100
        print(f"  El mercado mejora {margen_mercado:.5f} sobre no saber nada.")
        print(f"  Nosotros mejoramos {margen_nuestro:.5f}, o sea el {pct:.0f}% de eso.")
    dif = (brq - brm) / n
    if dif > 0:
        print(f"\n  Le ganamos al cierre por {dif:.5f}. Eso es raro: revisá que no")
        print("  haya fuga de información en el filtro de fecha antes de festejar.")
    else:
        print(f"\n  El cierre nos gana por {-dif:.5f} de Brier. Es lo esperable —")
        print("  es el mejor predictor público que existe.")


if __name__ == "__main__":
    main()
