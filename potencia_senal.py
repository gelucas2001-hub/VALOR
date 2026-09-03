#!/usr/bin/env python3
"""¿Cuánta muestra hace falta para validar `desarrollo.senal`?

Nada de esto mide nada nuevo. Es aritmética sobre números que ya están
medidos: las tasas de acierto y las tasas base de `calibrar_senal.py`
(20.897 partidos europeos, train/test temporal) y las coberturas de esa
misma corrida. No toca reglas, umbrales, datasets ni el producto.

Existe porque la pregunta "¿cuántas señales necesitamos?" nunca se hizo,
y la respuesta cambia si vale la pena esperar la muestra o no. Un
instrumento que necesita cinco años para contestar no es un instrumento
lento: es uno que no contesta.

    python potencia_senal.py
"""

import math
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# ── Lo medido, y de dónde sale ───────────────────────────────────────
#
# `hit` es el acierto en TEST de `calibrar_senal.py` con el umbral
# congelado; `base` es la tasa base de esa métrica (la frecuencia del
# lado más común, que es contra lo que hay que ganar, no contra 50%);
# `cobertura` es la fracción de partidos donde la regla llega a emitir.
#
# Los tres números son del mismo experimento y de la misma mitad de test.
MEDIDO = {
    "faltas":          {"base": 0.541, "hit": 0.712, "cobertura": 0.148},
    "volumen_remates": {"base": 0.512, "hit": 0.636, "cobertura": 0.103},
    "corners_total":   {"base": 0.520, "hit": 0.657, "cobertura": 0.019},
    # `tarjetas` no entra: no se afirma nunca, así que no hay potencia
    # que calcular. Su ausencia acá no es un olvido.
}

ALFA = 0.05          # dos colas, convencional
POTENCIAS = (0.80, 0.90)


def z(p):
    """Cuantil de la normal estándar. Aproximación de Acklam, |err|<1e-9."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def n_necesario(p0, p1, potencia=0.80, alfa=ALFA):
    """Señales resueltas para distinguir p1 de p0, una proporción.

    Prueba de una muestra contra una proporción CONOCIDA. Tratar `p0`
    como conocida es defendible acá: sale de miles de partidos, así que
    su error es despreciable frente al de la muestra que vamos a juntar.
    Si se estimara con la misma muestra, el `n` sería mayor.
    """
    if p1 == p0:
        return None
    za, zb = z(1 - alfa / 2), z(potencia)
    num = za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p1 * (1 - p1))
    return math.ceil((num / (p1 - p0)) ** 2)


def tabla_potencia():
    print("\n" + "=" * 78)
    print("  CAPA 2 — ¿cuántas señales para saber si superan su tasa base?")
    print("=" * 78)
    print(f"\n  prueba de una proporción, dos colas, α = {ALFA}")
    print("  la vara es la TASA BASE de cada métrica, no el 50%\n")
    print(f"  {'dimensión':>16} {'base':>7} {'esperado':>9} {'delta':>7} "
          f"{'n 80%':>7} {'n 90%':>7}")
    print("  " + "-" * 60)
    for dim, m in MEDIDO.items():
        n80 = n_necesario(m["base"], m["hit"], 0.80)
        n90 = n_necesario(m["base"], m["hit"], 0.90)
        print(f"  {dim:>16} {m['base']:>6.1%} {m['hit']:>8.1%} "
              f"{m['hit']-m['base']:>+6.1%} {n80:>7} {n90:>7}")

    print("\n" + "-" * 78)
    print("  Y si en Sudamérica la señal resulta más chica que en Europa")
    print("-" * 78)
    print("\n  El `n` crece con el CUADRADO inverso del delta: media señal")
    print("  cuesta cuatro veces la muestra. Escenarios sobre el mismo")
    print("  delta medido, sin suponer nada nuevo.\n")
    print(f"  {'dimensión':>16} {'delta':>8} {'n 80%':>8} | {'×0.75':>7} "
          f"{'n 80%':>8} | {'×0.50':>7} {'n 80%':>8}")
    print("  " + "-" * 74)
    for dim, m in MEDIDO.items():
        fila = f"  {dim:>16}"
        for f in (1.0, 0.75, 0.50):
            d = (m["hit"] - m["base"]) * f
            n = n_necesario(m["base"], m["base"] + d, 0.80)
            etq = f"{d:+.1%}"
            fila += f" {etq:>8} {n:>8}" + (" |" if f != 0.50 else "")
        print(fila)
    print()


def tabla_partidos():
    print("\n" + "=" * 78)
    print("  ¿CUÁNTOS PARTIDOS SON ESAS SEÑALES?")
    print("=" * 78)
    print("\n  La cobertura medida en Europa dice en qué fracción de los")
    print("  partidos la regla llega a emitir. Es POR DIMENSIÓN: cada una")
    print("  acumula su propia muestra, no se suman entre sí.\n")
    print(f"  {'dimensión':>16} {'cobertura':>10} {'1 señal cada':>14}")
    print("  " + "-" * 44)
    for dim, m in MEDIDO.items():
        print(f"  {dim:>16} {m['cobertura']:>9.1%} "
              f"{1/m['cobertura']:>11.0f} partidos")

    print("\n  Partidos necesarios, con la cobertura medida:\n")
    metas = (20, 40, 60, 100)
    print(f"  {'dimensión':>16} " + " ".join(f"{m:>8}" for m in metas)
          + f" {'n 80%':>9} {'n 90%':>9}")
    print("  " + "-" * 74)
    for dim, m in MEDIDO.items():
        n80 = n_necesario(m["base"], m["hit"], 0.80)
        n90 = n_necesario(m["base"], m["hit"], 0.90)
        cel = " ".join(f"{math.ceil(k/m['cobertura']):>8}" for k in metas)
        print(f"  {dim:>16} {cel} {math.ceil(n80/m['cobertura']):>9} "
              f"{math.ceil(n90/m['cobertura']):>9}")

    print("\n  Y si la cobertura real fuera otra — escenarios, no supuestos.")
    print("  Partidos para llegar al `n` de 80% de potencia de cada una:\n")
    print(f"  {'dimensión':>16} {'n 80%':>7} " +
          " ".join(f"{'1 de '+str(k):>10}" for k in (3, 4, 6, 10)))
    print("  " + "-" * 68)
    for dim, m in MEDIDO.items():
        n80 = n_necesario(m["base"], m["hit"], 0.80)
        cel = " ".join(f"{n80*k:>10}" for k in (3, 4, 6, 10))
        print(f"  {dim:>16} {n80:>7} {cel}")

    # arg.1 (15) + bra.1 (11) por fecha. Es lo que hay en la grilla de
    # hoy; se muestra como escala, no como promesa.
    print("\n  A 26 partidos por fecha (arg.1 + bra.1 de la grilla actual),")
    print("  y una fecha por semana:\n")
    print(f"  {'dimensión':>16} {'partidos':>10} {'fechas':>8} {'≈ tiempo':>14}")
    print("  " + "-" * 52)
    for dim, m in MEDIDO.items():
        n80 = n_necesario(m["base"], m["hit"], 0.80)
        ps = math.ceil(n80 / m["cobertura"])
        fechas = ps / 26
        años = fechas / 52
        t = (f"{fechas:.0f} semanas" if años < 1
             else f"{años:.1f} años")
        print(f"  {dim:>16} {ps:>10} {fechas:>8.0f} {t:>14}")
    print()


def capa_tres():
    print("\n" + "=" * 78)
    print("  CAPA 3 — el aporte incremental, que es otra pregunta")
    print("=" * 78)
    print("""
  La potencia de la capa 2 NO sirve para la capa 3, y no por una razón
  estadística. Es anterior.

  LO QUE LA CAPA 3 PREGUNTA
  ¿La señal aporta algo sobre el pronóstico numérico de esa misma
  métrica? El baseline está definido en `medir_senal.py`: el promedio
  por equipo de `estadisticas.json`, no λ.

  EL PROBLEMA, Y ES ESTRUCTURAL
  Desde §34, las cuatro dimensiones de volumen NO las decide la lectura.
  El expediente calcula `senal_base` a partir de `estadisticas.json`, le
  aplica el umbral y entrega el `fallo`; la skill lo copia y tiene
  prohibido discutirlo. O sea:

      señal  =  f(estadisticas.json)
      base   =  g(estadisticas.json)

  Las dos salen del MISMO insumo, y la primera es la segunda pasada por
  un umbral. El aporte incremental de una función determinista de su
  propio baseline es CERO por construcción. No hace falta muestra para
  saberlo, y ninguna cantidad de datos lo va a cambiar.

  Esto no es un defecto de §34: es el precio que se pagó a propósito
  para que la señal fuera reproducible. Sacar la aritmética de la cabeza
  del modelo arregló la inconsistencia del smoke test y, en el mismo
  movimiento, dejó a la lectura sin lugar donde aportar en esas cuatro.

  QUÉ QUEDA, ENTONCES
  La capa 2 sigue siendo una pregunta legítima, pero cambia de dueño:
  mide si el UMBRAL calibrado en Europa transfiere a Sudamérica. Es la
  validación de `calibrar_senal.py`, no de la lectura futbolística.

  `generador` está en la misma situación: `liderazgo_remates()` calcula
  la ventaja y el umbral es fijo. La discreción que le queda a la
  lectura es nula.

  DÓNDE SÍ PUEDE APORTAR LA LECTURA, HOY
  En `inclinacion` y en la prosa — que es lo que mide `medir_analisis.py`
  y no este instrumento. Ahí la lectura sí decide.

  QUÉ HARÍA FALTA PARA UNA CAPA 3 DE VERDAD
  Que la señal tuviera un insumo que el estimador no tiene. Dos formas,
  y las dos son decisiones de diseño que hoy NO están tomadas:

    · dejar que la lectura se aparte del `fallo` cuando tiene research
      que el número no ve (una cancha embarrada, un clásico con
      antecedente, un árbitro designado) — lo que §34 prohíbe hoy;
    · o medir la señal contra un baseline más fuerte que el propio
      estimador que la genera, que es otra pregunta.

  Sin una de las dos, la capa 3 no tiene qué medir. Con cualquiera de
  las dos, el tamaño de muestra depende de un efecto que todavía no
  existe y no se puede estimar honestamente. Lo que sí se puede decir:
  detectar un aporte incremental es SIEMPRE más caro que detectar
  acierto — se mide sobre pares discordantes, y esos son una fracción
  del total.
""")


def veredicto():
    print("=" * 78)
    print("  ¿VALE LA PENA ESPERAR ESTA MUESTRA?")
    print("=" * 78)
    print()
    for dim, m in MEDIDO.items():
        n80 = n_necesario(m["base"], m["hit"], 0.80)
        ps = math.ceil(n80 / m["cobertura"])
        años = ps / 26 / 52
        if años <= 1:
            marca, txt = "🟢", "razonable en meses"
        elif años <= 3:
            marca, txt = "🟡", "posible pero lento"
        else:
            marca, txt = "🔴", "poco realista con la frecuencia actual"
        print(f"  {marca} {dim:>16}  {n80:>3} señales · {ps:>5} partidos · "
              f"{años:>4.1f} años   {txt}")
    print()
    print("  CAPA 3   🔴  no es cuestión de muestra: la señal es una")
    print("               función determinista de su propio baseline.")
    print()


def main():
    print("\n" + "#" * 78)
    print("#  POTENCIA Y TAMAÑO DE MUESTRA PARA `desarrollo.senal`")
    print("#  Aritmética sobre lo ya medido. No se recalibra nada.")
    print("#" * 78)
    tabla_potencia()
    tabla_partidos()
    capa_tres()
    veredicto()
    return 0


if __name__ == "__main__":
    sys.exit(main())
