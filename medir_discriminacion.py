#!/usr/bin/env python3
"""¿La app tiene opinión propia sobre cada equipo, o publica el promedio?

Por qué existe, y es el hallazgo del 2026-08-25:

`medir_lineas.py` ya medía **calibración** — cuando decimos 60%, ¿pasa
el 60%? — y daba "córners bien". Pero calibración y utilidad no son lo
mismo, y acá se vio la diferencia de la peor manera.

Un pronóstico que le publica a TODOS los equipos el promedio de la liga
**está perfectamente calibrado**: el promedio de la liga es, por
definición, lo que pasa en promedio. Y no sirve para apostar nada,
porque la casa también sabe el promedio de la liga. No hay nada que
agregar, y donde no hay nada que agregar no hay valor.

Eso era exactamente lo que estaba pasando. Los 68 equipos del caché
recibían el mismo número:

    córners    de 4.70 a 4.96     (un cuarto de córner entre todos)
    remates    de 13.75 a 13.99
    al arco    de 4.19 a 4.30

No es un bug: `parametros_metricas()` devuelve `k = K_TOPE` cuando no
puede distinguir un equipo de otro, y encoger al tope es su forma
honesta de decirlo. El problema era que **nadie lo estaba mirando**, y
la calibración no lo delataba — al contrario, lo premiaba.

Qué mide este script:

- **Separación entre equipos**: cuánto se distinguen de verdad, ya
  descontado el ruido de promediar pocos partidos. Es el `entre` de
  `parametros_metricas()`, expuesto para poder leerlo.
- **Piso de detección**: la diferencia mínima que la muestra de hoy
  permite ver. Baja con los partidos acumulados, y por eso convierte
  "no hay señal" en "todavía no la vemos", que no es lo mismo.
- **Spread**: cuánto se abren los números que la app efectivamente
  publicaría. Es el síntoma en pantalla.
- **Discriminación**: la recta de lo real contra lo predicho. Pendiente
  1 es seguir a la realidad; pendiente 0 es no saber nada.

Lo que se encontró midiendo (2026-08-25, 189 partidos, ~4 por equipo):
se distinguen **posesión, tackles, faltas, offsides y tarjetas** — o
sea el estilo, que el equipo repite todas las semanas. No se distinguen
**remates, al arco, atajadas** ni todavía **córners** — o sea el
resultado, que depende del rival y del marcador.

    python medir_discriminacion.py
"""

import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import actualizar as A

RAIZ = Path(__file__).resolve().parent

K_TOPE = A.K_TOPE

# Por debajo de esto no se estima nada: la separación entre equipos se
# calcula a partir de la dispersión de sus promedios, y con cinco
# equipos esa dispersión es puro azar.
MIN_EQUIPOS = A.MIN_EQUIPOS

# Orden de lectura: primero lo que se apuesta por línea, después el
# resto. Posesión y pases no tienen mercado, pero sirven de control —
# si el método no las ve separarse, el método está roto.
ORDEN = ("corners", "remates", "al_arco", "faltas", "tarjetas",
         "offsides", "atajadas", "tackles", "posesion")


def piso_deteccion(dentro, nbar):
    """La diferencia mínima entre equipos que esta muestra deja ver.

    Promediar `nbar` partidos de un equipo deja un error de
    `dentro/nbar` en ese promedio. Cuando los equipos se separan menos
    que eso, la separación queda tapada por el ruido de la propia
    muestra — no porque no exista.

    Es el número que distingue "no hay señal" de "todavía no la vemos",
    y son cosas muy distintas para decidir qué hacer.
    """
    if not nbar or nbar <= 0:
        return None
    return dentro / nbar


def separacion(por_equipo):
    """Cuánto se distinguen los equipos, descontando el ruido.

    `por_equipo` es {id: [valores de cada partido]}. Devuelve `dentro`
    (cuánto varía un mismo equipo de fecha a fecha), `entre` (lo que
    sobra después de descontar el ruido de la muestra), el `k` que
    saldría de ahí y el piso de detección.

    La resta es lo importante y es lo que casi nadie hace: los
    promedios de cuatro partidos se separan solos por azar, así que
    mirar la dispersión de los promedios sin descontar nada hace que
    CUALQUIER métrica parezca discriminar.
    """
    con = {t: v for t, v in (por_equipo or {}).items() if len(v) >= 2}
    if len(con) < MIN_EQUIPOS:
        return None
    dentro = A._media([A._var(v) for v in con.values()])
    medias = [A._media(v) for v in con.values()]
    nbar = A._media([len(v) for v in con.values()])
    piso = piso_deteccion(dentro, nbar)
    entre = A._var(medias) - piso
    k = K_TOPE if entre <= 0 else min(dentro / entre, K_TOPE)
    return {"equipos": len(con), "nbar": nbar, "dentro": dentro,
            "entre": entre, "piso": piso, "k": k,
            "sd_real": math.sqrt(entre) if entre > 0 else 0.0,
            "veredicto": ("no se ve" if entre <= 0
                          else "apenas" if k > 40 else "se distingue")}


def falsa_senal(n_equipos, nbar, repeticiones=200, semilla=17):
    """El techo de `entre/piso` que producen equipos IDÉNTICOS, por azar.

    Es la regla del repo aplicada acá: comparar el error contra el
    ruido, no contra cero (ver `medir_jugadores.ruido_esperado`). Y hace
    muchísima falta, porque el estimador de `separacion()` es
    escandalosamente ruidoso con poca muestra.

    Medido el 2026-08-25 sobre 40 ligas sintéticas de 60 equipos
    idénticos, contando cuántas veces reportó "se distingue":

        partidos por equipo :   4     10     20     40
        falsa señal         : 14/40  3/40   0/40   0/40

    Con cuatro partidos por equipo —que es lo que tenemos hoy— el
    estimador inventa una diferencia entre equipos **el 35% de las
    veces**. Ese número no es un defecto del código: es lo que la
    muestra da de sí. Pero significa que un `entre` positivo con esta
    cantidad de partidos NO alcanza para afirmar nada, y que hace falta
    esta referencia al lado.

    Devuelve el percentil 95 de `|entre| / piso` bajo la hipótesis de
    que todos los equipos son iguales. Una métrica real que no lo supere
    está adentro del ruido, por más que su `k` haya bajado del tope.
    """
    import random
    if not n_equipos or not nbar or nbar < 2:
        return None
    r = random.Random(semilla)
    n = max(2, int(round(nbar)))
    razones = []
    for _ in range(repeticiones):
        # La escala no importa: `entre/piso` es adimensional, así que
        # alcanza con simular equipos idénticos con dispersión 1.
        por_eq = {str(t): [r.gauss(0.0, 1.0) for _ in range(n)]
                  for t in range(n_equipos)}
        e = separacion(por_eq)
        if e and e["piso"]:
            razones.append(abs(e["entre"]) / e["piso"])
    if not razones:
        return None
    razones.sort()
    return razones[int(len(razones) * 0.95)]


def spread(por_equipo, media, k):
    """Cuánto se abren los números que la app publicaría, con este k.

    Es el síntoma visible: si esto da 0.26 en córners, quiere decir que
    entre el equipo que más tira y el que menos hay un cuarto de córner
    de diferencia en lo que mostramos. Nadie apuesta contra eso.
    """
    vals = [A.media_encogida(v, media, k)
            for v in (por_equipo or {}).values() if v]
    return (max(vals) - min(vals)) if len(vals) > 1 else 0.0


def discriminacion(pares):
    """La recta de lo real contra lo predicho: real ≈ a + b · pred.

    `pares` es [(predicho, real)]. La **pendiente** es lo que importa:

    - b ≈ 1: cuando decimos que un equipo hace dos faltas más, hace dos
      faltas más. Seguimos a la realidad.
    - b ≈ 0: lo que decimos no tiene relación con lo que pasa.
    - b > 1: vamos en la dirección correcta pero nos quedamos cortos —
      achatamos las diferencias, o sea encogemos de más.

    Ojo con leer el r²: acá va a ser bajísimo siempre, y eso NO es una
    mala noticia. Un partido suelto tiene muchísimo azar; nadie puede
    explicar la mayor parte. La pendiente sí es interpretable, porque
    pregunta otra cosa: si le acertamos a la DIRECCIÓN y al TAMAÑO.
    """
    pares = [(p, r) for p, r in (pares or []) if p is not None and r is not None]
    n = len(pares)
    if n < 2:
        return None
    mx = sum(p for p, _ in pares) / n
    my = sum(r for _, r in pares) / n
    sxx = sum((p - mx) ** 2 for p, _ in pares)
    if sxx <= 0:
        # Todas las predicciones iguales: no hay pendiente que estimar,
        # y eso ya es la respuesta — no discrimina nada.
        return {"n": n, "pendiente": 0.0, "ee": 0.0, "r2": 0.0,
                "sd_pred": 0.0, "sd_real": math.sqrt(
                    sum((r - my) ** 2 for _, r in pares) / n)}
    sxy = sum((p - mx) * (r - my) for p, r in pares)
    syy = sum((r - my) ** 2 for _, r in pares)
    b = sxy / sxx
    a = my - b * mx
    res = sum((r - a - b * p) ** 2 for p, r in pares)
    ee = math.sqrt(res / (n - 2) / sxx) if n > 2 else 0.0
    return {"n": n, "pendiente": b, "ee": ee,
            "r2": (1 - res / syy) if syy > 0 else 0.0,
            "sd_pred": math.sqrt(sxx / n), "sd_real": math.sqrt(syy / n)}


def main():
    import medir_lineas as L

    hist = L.historia()
    if not hist:
        raise SystemExit("no hay caché de disciplina — corré el cron primero")
    cache = {x["eid"]: x["equipos"] for x in hist}
    muestras = A.muestras_por_equipo(cache)
    params = A.parametros_metricas(muestras)

    print("\n" + "=" * 78)
    print("  ¿TENEMOS OPINIÓN PROPIA POR EQUIPO, O PUBLICAMOS EL PROMEDIO?")
    print("=" * 78)
    print("\n  {} partidos · de {} a {}\n".format(
        len(hist), hist[0]["fecha"], hist[-1]["fecha"]))

    print("  {:10}{:>7}{:>7}{:>9}{:>7}{:>9}{:>8}  {}".format(
        "métrica", "equips", "pj/eq", "separan", "k", "spread",
        "vs ruido", "veredicto"))
    print("  " + "-" * 78)
    techos = {}
    for met in ORDEN:
        r = separacion(muestras.get(met))
        if not r:
            continue
        p = params.get(met) or {}
        sp = spread(muestras.get(met), p.get("media", 0.0), r["k"])
        clave = (r["equipos"], round(r["nbar"]))
        if clave not in techos:
            techos[clave] = falsa_senal(r["equipos"], r["nbar"])
        techo = techos[clave]
        razon = abs(r["entre"]) / r["piso"] if r["piso"] else 0.0
        # Lo único que cuenta como señal es superar lo que producen
        # equipos idénticos por azar con ESTA misma muestra.
        limpia = r["entre"] > 0 and techo is not None and razon > techo
        print("  {:10}{:7d}{:7.1f}{:9.3f}{:7.1f}{:9.2f}{:8.2f}  {}".format(
            met, r["equipos"], r["nbar"], r["entre"], r["k"], sp,
            razon, "SEÑAL REAL" if limpia else r["veredicto"]))
    if techos:
        t = sorted(v for v in techos.values() if v is not None)
        if t:
            print("\n  Techo de falsa señal con esta muestra: {:.2f}"
                  .format(t[-1]))
            print("  (equipos IDÉNTICOS llegan hasta ahí solos, por azar)")

    print("\n  " + "-" * 76)
    print("  separan = cuánto se distinguen los equipos DE VERDAD, ya")
    print("            descontado el ruido de promediar pocos partidos.")
    print("            Cero o negativo: con esta muestra, no se ve.")
    print("  piso    = la separación mínima que esta muestra deja ver.")
    print("            Baja con los partidos acumulados.")
    print("  vs ruido= |separan| dividido el piso. Tiene que superar el")
    print("            techo de falsa señal para contar como hallazgo.")
    print("  spread  = cuánto se abre el número que PUBLICAMOS entre el")
    print("            equipo más alto y el más bajo. Es el síntoma en")
    print("            pantalla: si es casi cero, publicamos el promedio.")
    print("  " + "-" * 76)

    print("\n\n  Cuánta muestra haría falta — el piso según partidos por equipo\n")
    print("  {:10}{:>10}{:>9}{:>9}{:>9}{:>9}".format(
        "métrica", "hoy", "pj=10", "pj=20", "pj=38", "pj=76"))
    print("  " + "-" * 58)
    for met in ORDEN:
        r = separacion(muestras.get(met))
        if not r:
            continue
        d = r["dentro"]
        print("  {:10}{:10.2f}{:9.2f}{:9.2f}{:9.2f}{:9.2f}".format(
            met, r["piso"], d / 10, d / 20, d / 38, d / 76))
    print("\n  Una temporada completa (38 fechas) baja el piso varias veces")
    print("  respecto de hoy. Una métrica que hoy dice 'no se ve' puede")
    print("  estar diciendo 'todavía no' — y son cosas distintas.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
