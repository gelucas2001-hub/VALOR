#!/usr/bin/env python3
"""¿El mercado de estadísticas dice la verdad?

Por qué existe:

La app publica "62% de chance de pasar 9.5 córners" desde hace semanas.
Nunca se comprobó que cuando dice 62%, pase el 62%. Había
`medir_analisis.py`, `medir_arbitros.py`, `medir_clv.py`,
`medir_sesgo.py` y `medir_historico.py`; no había éste.

Es el mismo agujero que se destapó el 2026-08-24 en el modelo de goles
— tres semanas midiendo calibración y ninguna midiendo si servía —
repetido en el mercado que se quería acaparar. Un mercado sin medir es
una hipótesis con decimales.

Qué mide:

Calibración, no ROI. No tenemos cuotas históricas de córners ni de
tarjetas en ninguna fuente pública, así que el ROI no se puede simular.
Pero calibración es la pregunta previa: si cuando decimos 60% pasa el
45%, cualquier EV que se calcule arriba de eso es humo.

Cómo:

Walk-forward sobre `data/cache_disciplina.json`, que el cron viene
llenando: para cada partido se estiman los córners/tarjetas/remates con
**solo los partidos anteriores**, se calcula la chance de pasar cada
línea, y se compara contra lo que realmente pasó.

El cálculo de probabilidad es un port de `probMayor()` de `index.html`,
y `test_medir_lineas.py` compara las dos vías caso por caso: si se
separan, la medición deja de decir algo sobre lo que el usuario ve.

    python medir_lineas.py
"""

import datetime
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import actualizar as A

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ / "data" / "cache_disciplina.json"
PARTIDOS = RAIZ / "data" / "partidos.json"

# Las métricas que se apuestan por línea. Posesión y pases quedan afuera
# por lo mismo que en index.html: no hay mercado de "más de 51.5% de
# posesión", y un porcentaje no es un conteo.
METRICAS = ("corners", "tarjetas", "remates", "al_arco", "faltas")

# Cuántos partidos previos hacen falta antes de arriesgar una estimación.
MIN_PREVIOS = 20

# Por debajo de esto una métrica no se reporta: una banda de calibración
# con diez casos no dice nada.
MIN_PREDICCIONES = 40


def prob_mayor(mu, disp, linea):
    """Chance de que el número termine ARRIBA de `linea`.

    Port de `probMayor()` de index.html. Tres campanas, según cuánto se
    despatarra la métrica alrededor de su media:

      disp > 1  más despatarrada que Poisson (remates 2.95, córners
                1.75) — binomial negativa, colas gordas
      disp ~ 1  Poisson tal cual
      disp < 1  MÁS regular que Poisson (tarjetas 0.72) — binomial,
                colas flacas

    Usar Poisson para todo, que es lo que hace casi cualquier planilla,
    subvalúa las colas de remates y sobrevalúa las de tarjetas.
    """
    if mu is None or not math.isfinite(mu) or mu <= 0:
        return None
    if linea is None or not math.isfinite(linea):
        return None
    # Línea 4.5 quiere decir "5 o más": el lado estricto, sin empate.
    k0 = math.floor(linea) + 1
    if k0 <= 0:
        return 1
    d = disp if (disp is not None and math.isfinite(disp) and disp > 0) else 1
    acum = 0.0
    if d > 1.05:
        r, p = mu / (d - 1), 1 / d
        q = 1 - p
        t = p ** r
        for k in range(k0):
            acum += t
            t = t * (k + r) / (k + 1) * q
    elif d < 0.95:
        # Menos dispersa que Poisson: ninguna binomial negativa puede
        # hacer eso, la binomial común sí. Si el ajuste no da una
        # binomial válida (o su techo cae debajo de la línea, donde
        # daría un cero que no es cierto), se cae a Poisson.
        n = round(mu / (1 - d))
        p = mu / n if n > 0 else 1
        if not (n >= k0 and 0 < p < 1):
            return prob_mayor(mu, 1, linea)
        t = (1 - p) ** n
        for k in range(k0):
            acum += t
            t = t * (n - k) / (k + 1) * p / (1 - p)
    else:
        t = math.exp(-mu)
        for k in range(k0):
            acum += t
            t = t * mu / (k + 1)
    return min(1.0, max(0.0, 1 - acum))


def prob_mayor_js(casos):
    """Los mismos casos, calculados por el JS real de index.html.

    Existe para que las dos implementaciones no se separen en silencio.
    Se extrae del archivo publicado, no de una copia — el mismo criterio
    que usan `test_registro.js` y `doble_via.py`.
    """
    html = (RAIZ / "index.html").read_text(encoding="utf-8")
    i = html.index("function probMayor(")
    j = html.index("\n}", i) + 2
    script = (html[i:j] + "\nconst casos=" + json.dumps(casos) + ";\n"
              "console.log(JSON.stringify("
              "casos.map(c=>probMayor(c[0],c[1],c[2]))));")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(script)
        ruta = f.name
    try:
        out = subprocess.run(["node", ruta], capture_output=True, text=True,
                             timeout=30)
        if out.returncode != 0:
            raise RuntimeError(out.stderr[:400])
        return json.loads(out.stdout)
    finally:
        Path(ruta).unlink(missing_ok=True)


def previos(historia, fecha):
    """Los partidos utilizables para predecir uno de `fecha`.

    Estrictamente anteriores: dos partidos del mismo día no se ven entre
    sí, porque cuando se predice una fecha esa fecha todavía no se jugó.
    Una fuga de futuro no se ve como un error — se ve como un modelo
    buenísimo.
    """
    return [p for p in (historia or []) if p["fecha"] < fecha]


def lineas_de(mu):
    """Cuatro líneas alrededor de lo esperado, siempre en .5.

    En .5 para que no exista el empate: en una línea entera la casa
    devuelve el dinero, y la probabilidad de acá no describiría esa
    apuesta.
    """
    base = round(mu)
    return [x for x in (base - 1.5, base - 0.5, base + 0.5, base + 1.5) if x > 0]


def calibracion(filas, paso=0.1):
    """Por banda de probabilidad: qué dijimos y qué pasó."""
    bandas = []
    lo = 0.0
    while lo < 1.0:
        hi = lo + paso
        dentro = [f for f in filas if lo <= f["p"] < hi]
        if dentro:
            bandas.append({
                "lo": lo, "hi": hi, "n": len(dentro),
                "dicho": sum(f["p"] for f in dentro) / len(dentro),
                "paso": sum(f["paso"] for f in dentro) / len(dentro),
            })
        lo = hi
    return bandas


def _fechas_conocidas(sin_red=False):
    """event_id -> fecha, de todas las fuentes que ya están en disco.

    El caché de disciplina no guarda la fecha, y `data/partidos.json`
    solo tiene los partidos que **faltan** jugar — o sea justo los que
    no sirven para medir. Las fechas de los ya jugados salen de
    `historia_reciente()`, que para las temporadas pasadas lee del
    caché en disco y solo pide a ESPN la que está en curso.
    """
    fechas = {}
    if PARTIDOS.exists():
        d = json.loads(PARTIDOS.read_text(encoding="utf-8"))
        lista = d.get("partidos") if isinstance(d, dict) else d
        for m in lista or []:
            if isinstance(m, dict) and m.get("id") and m.get("date"):
                fechas[str(m["id"]).replace("espn", "")] = m["date"][:10]
    if sin_red:
        return fechas
    hoy = datetime.date.today()
    for slug in A.COMPETICIONES:
        try:
            for p in A.historia_reciente(slug, hoy.year, hoy):
                if p.get("id"):
                    fechas.setdefault(str(p["id"]), p["fecha"].isoformat())
        except Exception:                                        # noqa: BLE001
            # Una competición que no responde cuesta sus partidos, no la
            # medición entera.
            continue
    return fechas


def historia(sin_red=False):
    """Los partidos del caché, con sus números y su fecha, en orden.

    Un partido sin fecha conocida se descarta: sin fecha no se puede
    decir qué es "anterior", y sin eso la medición no sería
    walk-forward. Es preferible medir sobre menos partidos que sobre un
    orden inventado.
    """
    if not CACHE.exists():
        return []
    crudo = json.loads(CACHE.read_text(encoding="utf-8"))
    fechas = _fechas_conocidas(sin_red)
    out = []
    for eid, p in (crudo or {}).items():
        if str(eid).startswith("_") or not isinstance(p, dict):
            continue
        equipos = {k: v for k, v in p.items()
                   if not str(k).startswith("_") and isinstance(v, dict)}
        if len(equipos) != 2:
            continue
        f = fechas.get(str(eid))
        if not f:
            continue
        try:
            fecha = datetime.date.fromisoformat(f)
        except ValueError:
            continue
        out.append({"eid": str(eid), "fecha": fecha, "equipos": equipos})
    out.sort(key=lambda x: x["fecha"])
    return out


def evaluar(hist):
    """Una fila por (partido, equipo, métrica, línea): qué dijimos y qué pasó."""
    por_metrica = {m: [] for m in METRICAS}
    for p in hist or []:
        prev = previos(hist, p["fecha"])
        if len(prev) < MIN_PREVIOS:
            continue
        cache_prev = {x["eid"]: x["equipos"] for x in prev}
        params = A.parametros_metricas(A.muestras_por_equipo(cache_prev))
        for tid, datos in p["equipos"].items():
            propios = [x["equipos"][tid] for x in prev if tid in x["equipos"]]
            if not propios:
                continue
            esp = A.esperados(propios, params)
            for met in METRICAS:
                mu, real, par = esp.get(met), datos.get(met), params.get(met)
                if mu is None or real is None or not par:
                    continue
                for ln in lineas_de(mu):
                    q = prob_mayor(mu, par.get("disp"), ln)
                    if q is not None:
                        por_metrica[met].append({"p": q, "paso": int(real > ln)})
    return por_metrica


def main():
    hist = historia()
    print("\n" + "=" * 68)
    print("  EL MERCADO DE ESTADÍSTICAS — ¿cuando decimos 60%, pasa el 60%?")
    print("=" * 68)
    if len(hist) < MIN_PREVIOS + 5:
        print(f"\n  Solo hay {len(hist)} partidos con estadísticas y fecha.")
        print(f"  Hacen falta más de {MIN_PREVIOS + 5} para medir algo.")
        print("  El cron los junta solo: volvé a correr esto en unas fechas.\n")
        return 0
    print(f"\n  {len(hist)} partidos con estadísticas")
    print(f"  de {hist[0]['fecha']} a {hist[-1]['fecha']}")

    por_metrica = evaluar(hist)
    hubo = False
    for met in METRICAS:
        filas = por_metrica[met]
        if len(filas) < MIN_PREDICCIONES:
            continue
        hubo = True
        bandas = calibracion(filas)
        n = len(filas)
        desvio = sum(abs(b["dicho"] - b["paso"]) * b["n"] for b in bandas) / n
        print(f"\n  {met} — {n} predicciones")
        print(f"  {'banda':10} {'n':>6} {'decimos':>9} {'pasa':>8} {'desvío':>8}")
        for b in bandas:
            marca = ("  ←" if abs(b["dicho"] - b["paso"]) > 0.1 and b["n"] >= 20
                     else "")
            print(f"  {b['lo']*100:3.0f}-{b['hi']*100:3.0f}% {b['n']:6d} "
                  f"{b['dicho']*100:8.1f}% {b['paso']*100:7.1f}% "
                  f"{(b['dicho']-b['paso'])*100:+7.1f}{marca}")
        print(f"  desvío medio ponderado: {desvio*100:.1f} puntos")

    if not hubo:
        print("\n  Todavía no hay predicciones suficientes por métrica.\n")
        return 0
    print("\n  " + "-" * 64)
    print("  Esto mide calibración, no plata: no hay cuotas históricas de")
    print("  córners ni tarjetas con qué simular apuestas. Pero si cuando")
    print("  decimos 60% pasa el 45%, cualquier EV calculado arriba es humo.")
    print("  " + "-" * 64 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
