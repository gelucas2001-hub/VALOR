#!/usr/bin/env python3
"""¿Hay ventaja en las cuotas de 4 a 10? Por banda de precio, walk-forward.

Sale de una pregunta de Lucas, y es la mejor que se hizo en el proyecto:

    "Si determinadas situaciones se dan en el fútbol, entonces pueden
    existir condiciones o contextos que aumenten considerablemente su
    probabilidad en partidos específicos. No hablo de cuotas de 30 o 60.
    Hablo de cuotas de 5, 8 o 10."

El indicio que la motiva es real y estaba medido sin leerse en esa
dirección. `medir_calibracion.py` sobre lo que la app publicó:

    banda 10-20 %   decimos 16.4 %   pasa 24.6 %   (+8.2)
    banda 30-40 %   decimos 34.5 %   pasa 43.1 %   (+8.5)
    banda 80-90 %   decimos 83.7 %   pasa 75.9 %   (−7.8)

O sea que el modelo subestima lo improbable — y la banda 10-20 % ES la
cuota 5 a 10. Con remuestreo por partido, el desvío de las bajas daba
IC 95 % [+4.7, +13.8]: no cruza el cero.

Hay una explicación estructural y no es un bug: Poisson tiene las colas
más finas que el fútbol real. Las goleadas y las sorpresas pasan más de
lo que un Poisson dice, porque el fútbol tiene expulsiones, partidos que
se rompen y momentum, y el modelo los trata como independientes.

LO QUE ESTE SCRIPT TIENE QUE PODER CONTESTAR QUE NO

El sesgo favorito-perdedor es el efecto más conocido del mercado de
apuestas: las cuotas largas están históricamente sobrevaloradas, o sea
que pagan MENOS de lo que corresponde. Si eso sigue siendo cierto, el
modelo puede subestimar lo improbable Y el mercado seguir teniendo razón
— porque el mercado subestima menos. Las dos cosas a la vez.

Por eso acá no se pregunta "¿estamos bien calibrados?" sino las tres
juntas, sobre los mismos partidos:

    nuestra p   ·   la p del mercado (devig Shin)   ·   lo que pasó

Y la pregunta de plata, que es distinta de las tres: apostar esa banda,
¿da? Con la cuota de cierre, que es el precio más difícil que existe.

CONTRA EL AUTOENGAÑO

Lucas puso la condición justa: "en un momento le dábamos mucho papel a
las lesiones o a los viajes, que nos distorsionaban los partidos. No
quiero que cometamos ese error." Tres guardas, entonces:

  - train/test TEMPORAL. Lo que se encuentre en train hay que verlo
    también en test, o no existe.
  - el error estándar al lado de todo, y comparado contra la tasa base
    de esa misma banda — no contra cero.
  - se reporta la banda ENTERA aunque no dé, y el resultado negativo se
    escribe igual. La hipótesis se investiga, no se confirma.

RESULTADO (2026-09-03, 23.870 partidos de eng/arg/bra/spa/fra)

La hipotesis dio que NO, y en la direccion contraria a la que se supuso.

    TEST     cuota      n  decimos  mercado     pasó  nos-merc  real-merc
             4.0-6   5377    23.2%    20.3%    20.0%     +2.9      -0.2
            6.0-10   2006    17.0%    12.8%    12.0%     +4.2      -0.8
               10+    572    10.5%     6.7%     6.5%     +3.8      -0.3

`real - mercado` es negativo en las tres: el mercado paga apenas de
MENOS en las cuotas largas, no de mas. Y contra plata, en test, apostar
solo donde le ganamos al mercado da -7.38% ±2.82 — mas de dos errores
estandar NEGATIVO. Cuando discrepamos ahi, discrepamos para el lado
equivocado.

El indicio que motivo todo esto (medir_calibracion, +8.2 puntos en la
banda 10-20%) no sobrevive: eran 85 partidos sobre 12 mercados
correlacionados del mismo partido. Estos son 23.870, solo 1X2.

EL BOLSILLO QUE MURIO, y por que estaba la guarda

El local perdedor a 4-10 era el unico subconjunto cerca de cero
(ROI -1.91%). Mirado en serio: train +5.52% ±6.95, test -7.85% ±7.14.
Cambio de signo, los dos dentro del ruido, sin consistencia entre ligas.
Sin el corte train/test se reportaba como hallazgo.

QUE SE APRENDIO DEL MODELO, que es lo que quedo

Agrupado por NUESTRA propia p, el modelo esta bien calibrado: decimos
22% y pasa 24%, decimos 75% y pasa 71%. La recalibracion isotonica
mejora el Brier de test en 0.00006, o sea nada. Y una potencia global
`p^k` tiene su optimo en k=0.90 —aplanar— no en afilar.

O sea que las dos cosas son ciertas a la vez:

    agrupado por nuestra p        calibrado
    agrupado por la cuota         +3 a +5 en las largas

Eso solo puede pasar si nuestro error esta CORRELACIONADO con el precio:
cuando el mercado pone a alguien a 6.00 y nosotros le damos 17%, el
mercado sabe algo que nosotros no. No estamos descalibrados, estamos
menos informados — y eso no se arregla reformando nuestros numeros.

LO ACCIONABLE

La regla de valor pierde en TODAS las bandas, y la perdida crece
monotona con la cuota, en train y en test:

    1.0-2.0   -4.77%      3.0-3.5   -1.76%
    2.0-2.5   -2.30%      3.5-4.0   -9.40%
    2.5-3.0   -7.83%      4.0-4.5  -16.59% ±6.34

`MAX_ODDS = 4.5` admite el tramo donde la regla pierde tres veces mas.
Recortarlo no la vuelve positiva —`barrido_valor.py` ya probo 39
ventanas y ninguna lo es— pero deja de firmar las peores.

OJO CON EL RHO DEL ARNES

`medir_historico.evaluar()` mide con `rho=0.05` fijo y NINGUNA liga usa
ese valor (arg -0.05, bra 0.00, eng -0.02, fra -0.05, esp 0.00). Sobre
la regla de valor eso son 1,5 puntos de ROI y un 12% mas de marcas:

    rho 0.05 (arnes)     6050 marcas   -6.29% ±1.74
    rho de produccion    5386 marcas   -4.78% ±1.88

Ninguna conclusion se da vuelta —la diferencia es menor que el error
estandar— pero afecta a medir_roi.py y medir_apertura.py, que son los
que deciden que liga entra a la app.

    python medir_bandas.py                # todas las ligas
    python medir_bandas.py eng spa        # solo algunas
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
CACHE = RAIZ / "data" / "bandas_filas.json"

# Los cortes son de CUOTA, no de probabilidad, porque la pregunta se hizo
# en cuotas: "5, 8 o 10". La banda 4-10 es la que Lucas señaló.
BANDAS = [(1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 4.0),
          (4.0, 6.0), (6.0, 10.0), (10.0, 999.0)]

# Debajo de esto una banda no dice nada. Con 30 casos, un desvío de 10
# puntos es lo que sale por azar la mitad de las veces.
MIN_BANDA = 100


def banda_de(cuota):
    for lo, hi in BANDAS:
        if lo <= cuota < hi:
            return (lo, hi)
    return None


def selecciones(filas):
    """Una fila por SELECCIÓN (local, empate, visitante), no por partido.

    Un partido aporta tres. No son independientes entre sí —si gana el
    local, el empate y la visita fallan juntos— y eso importa para el
    error estándar: se avisa donde se reporta.
    """
    out = []
    for f in filas:
        cuotas = f.get("cuotas") or []
        if len(cuotas) != 3:
            continue
        for k in range(3):
            c = cuotas[k]
            if not c or c <= 1:
                continue
            out.append({
                "cuota": c,
                "nuestra": f["modelo"][k],
                "mercado": f["mercado"][k],
                "paso": bool(f["real"][k]),
                "fecha": f["fecha"],
                "liga": f.get("liga"),
                "lado": ("local", "empate", "visita")[k],
                "n_previos": f.get("n_previos", 0),
            })
    return out


def resumen(sel):
    """n, nuestra p media, la del mercado, y con qué frecuencia pasó."""
    n = len(sel)
    if not n:
        return None
    nues = sum(s["nuestra"] for s in sel) / n
    merc = sum(s["mercado"] for s in sel) / n
    real = sum(1 for s in sel if s["paso"]) / n
    # Error estándar de la frecuencia observada. Ojo: asume selecciones
    # independientes y las tres de un partido no lo son, así que el
    # intervalo real es más ancho que este.
    ee = (real * (1 - real) / n) ** 0.5
    brier_n = sum((s["nuestra"] - (1 if s["paso"] else 0)) ** 2 for s in sel) / n
    brier_m = sum((s["mercado"] - (1 if s["paso"] else 0)) ** 2 for s in sel) / n
    return {"n": n, "nuestra": nues, "mercado": merc, "real": real, "ee": ee,
            "brier_n": brier_n, "brier_m": brier_m}


def roi(sel):
    """Apostar TODAS las selecciones de este grupo, a la cuota de cierre."""
    n = len(sel)
    if not n:
        return None
    g = [(s["cuota"] - 1) if s["paso"] else -1.0 for s in sel]
    media = sum(g) / n
    var = sum((x - media) ** 2 for x in g) / n if n > 1 else 0.0
    return {"n": n, "roi": media * 100, "ee": (var / n) ** 0.5 * 100}


def cargar(ligas, refrescar=False):
    """Las filas walk-forward, cacheadas: la pasada cuesta ~8 min por liga."""
    import historico as H
    import medir_historico as MH

    previo = {}
    if CACHE.exists() and not refrescar:
        try:
            previo = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            previo = {}

    todas = []
    for liga in ligas:
        if liga in previo:
            print(f"  {liga}: {len(previo[liga])} filas (cache)")
            todas += previo[liga]
            continue
        print(f"  {liga}: ajustando walk-forward (tarda ~8 min)...", flush=True)
        ps = H.partidos(liga)
        filas = MH.evaluar(ps, rho=0.05)
        for f in filas:
            f["liga"] = liga
            f["fecha"] = str(f["fecha"])
        previo[liga] = filas
        todas += filas
        print(f"  {liga}: {len(filas)} partidos evaluados")
        CACHE.write_text(json.dumps(previo, ensure_ascii=False,
                                    separators=(",", ":")), encoding="utf-8")
    return todas


def tabla(sel, titulo):
    print(f"\n{'─' * 78}")
    print(f"  {titulo}")
    print(f"{'─' * 78}\n")
    print(f"  {'cuota':>11} {'n':>6} {'decimos':>8} {'mercado':>8} {'pasó':>8} "
          f"{'nos-merc':>9} {'real-merc':>10}")
    for lo, hi in BANDAS:
        g = [s for s in sel if lo <= s["cuota"] < hi]
        r = resumen(g)
        if not r or r["n"] < MIN_BANDA:
            continue
        et = f"{lo:.1f}-{hi:.0f}" if hi < 999 else f"{lo:.0f}+"
        print(f"  {et:>11} {r['n']:>6} {r['nuestra']*100:>7.1f}% "
              f"{r['mercado']*100:>7.1f}% {r['real']*100:>7.1f}% "
              f"{(r['nuestra']-r['mercado'])*100:>+8.1f} "
              f"{(r['real']-r['mercado'])*100:>+9.1f}")


def main(argv):
    import historico as H

    ligas = [a for a in argv[1:] if not a.startswith("--")] or sorted(H.LIGAS)
    for l in ligas:
        if l not in H.LIGAS:
            raise SystemExit(f"liga desconocida: {l}. Hay {sorted(H.LIGAS)}")

    print("\n" + "=" * 78)
    print("  ¿HAY VENTAJA EN LAS CUOTAS DE 4 A 10?  —  por banda de precio")
    print("=" * 78 + "\n")

    filas = cargar(ligas, refrescar="--refrescar" in argv)
    if not filas:
        print("\n  Sin filas.\n")
        return 1
    sel = selecciones(filas)
    fechas = sorted({s["fecha"] for s in sel})
    corte = fechas[int(len(fechas) * 0.6)]
    print(f"\n  {len(filas)} partidos · {len(sel)} selecciones · "
          f"{fechas[0]} a {fechas[-1]}")
    print(f"  train hasta {corte}, test desde ahí")
    print("  Ojo: las tres selecciones de un partido no son independientes,")
    print("  así que los intervalos de abajo son más angostos que la verdad.")

    tabla(sel, "TODO EL HISTORIAL")
    print("\n  'decimos' es nuestro modelo; 'mercado' es la cuota sin margen")
    print("  (Shin); 'pasó' es lo que ocurrió. La última columna es la que")
    print("  dice si el MERCADO se equivoca: positiva = paga de más.")

    tr = [s for s in sel if s["fecha"] < corte]
    te = [s for s in sel if s["fecha"] >= corte]
    tabla(tr, "TRAIN")
    tabla(te, "TEST  —  si el patrón no está acá, no existe")

    # ── La banda que preguntó Lucas, contra plata ────────────────────
    print(f"\n{'═' * 78}")
    print("  LA BANDA 4-10 CONTRA PLATA")
    print(f"{'═' * 78}\n")
    for et, grupo in (("todo", sel), ("train", tr), ("test", te)):
        g = [s for s in grupo if 4.0 <= s["cuota"] < 10.0]
        r, m = resumen(g), roi(g)
        if not r or r["n"] < MIN_BANDA:
            continue
        print(f"  {et:>6}  apostar TODAS: {m['n']:>6} apuestas · "
              f"ROI {m['roi']:>+7.2f}% ±{m['ee']:.2f}")
        # Y solo donde NOSOTROS decimos más que el mercado: si el modelo
        # aporta algo, tiene que aparecer en este corte y no en el de
        # arriba, que no usa el modelo para nada.
        conv = [s for s in g if s["nuestra"] > s["mercado"]]
        if len(conv) >= MIN_BANDA:
            mc = roi(conv)
            rc = resumen(conv)
            print(f"          solo donde le ganamos al mercado: {mc['n']:>5} · "
                  f"ROI {mc['roi']:>+7.2f}% ±{mc['ee']:.2f} · "
                  f"decimos {rc['nuestra']*100:.1f}% y pasó {rc['real']*100:.1f}%")
        print()

    # ── Dónde vive esa banda ─────────────────────────────────────────
    #
    # "En qué mercados o situaciones aparece" es la mitad de la pregunta.
    # Una banda de cuota mezcla tres cosas distintas: el empate (que casi
    # siempre cae en 3-5), la visita de un chico a un grande, y el local
    # flojo. No tienen por qué comportarse igual, y el empate en
    # particular tiene su propio sesgo documentado.
    g410 = [s for s in sel if 4.0 <= s["cuota"] < 10.0]
    print(f"\n{'─' * 78}")
    print("  DE QUÉ ESTÁ HECHA LA BANDA 4-10")
    print(f"{'─' * 78}\n")
    print(f"  {'':>10} {'n':>7} {'decimos':>8} {'mercado':>8} {'pasó':>8} "
          f"{'real-merc':>10} {'ROI':>9}")
    for lado in ("local", "empate", "visita"):
        gg = [s for s in g410 if s["lado"] == lado]
        r, m = resumen(gg), roi(gg)
        if not r or r["n"] < MIN_BANDA:
            continue
        print(f"  {lado:>10} {r['n']:>7} {r['nuestra']*100:>7.1f}% "
              f"{r['mercado']*100:>7.1f}% {r['real']*100:>7.1f}% "
              f"{(r['real']-r['mercado'])*100:>+9.1f} {m['roi']:>+8.2f}%")

    print(f"\n  {'liga':>10} {'n':>7} {'decimos':>8} {'mercado':>8} {'pasó':>8} "
          f"{'real-merc':>10} {'ROI':>9}")
    for lg in sorted({s["liga"] for s in g410 if s["liga"]}):
        gg = [s for s in g410 if s["liga"] == lg]
        r, m = resumen(gg), roi(gg)
        if not r or r["n"] < MIN_BANDA:
            continue
        print(f"  {lg:>10} {r['n']:>7} {r['nuestra']*100:>7.1f}% "
              f"{r['mercado']*100:>7.1f}% {r['real']*100:>7.1f}% "
              f"{(r['real']-r['mercado'])*100:>+9.1f} {m['roi']:>+8.2f}%")

    # ── Brier en la banda: ¿quién sabe más ahí? ──────────────────────
    g = [s for s in sel if 4.0 <= s["cuota"] < 10.0]
    r = resumen(g)
    if r:
        print(f"{'─' * 78}")
        print("  ¿QUIÉN SABE MÁS EN ESA BANDA?")
        print(f"{'─' * 78}\n")
        print(f"  Brier del modelo  {r['brier_n']:.5f}")
        print(f"  Brier del mercado {r['brier_m']:.5f}")
        d = r["brier_n"] - r["brier_m"]
        print(f"  diferencia        {d:+.5f}  "
              f"({'el mercado' if d > 0 else 'nosotros'} sabe más)")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
