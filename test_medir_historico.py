#!/usr/bin/env python3
"""Tests de medir_historico.py

Lo que más importa acá no es que los números den lindo: es que NO se
filtre futuro al pasado. Toda la medición es walk-forward — ajustar con
lo anterior, predecir lo siguiente — y una fuga se ve como un modelo
buenísimo, no como un error. Por eso la mitad de estos tests son sobre
el corte temporal.

    python test_medir_historico.py
"""

import datetime
import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_historico as M

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def p(dia, home="A", away="B", gh=1, ga=0):
    return {"fecha": datetime.date(2024, 1, 1) + datetime.timedelta(days=dia),
            "home": home, "away": away, "gh": gh, "ga": ga,
            "cuotas": [2.0, 3.3, 4.0], "fuente": "pinnacle"}


PARTIDOS = [p(d) for d in range(0, 400, 10)]      # 40 partidos, cada 10 días


print("")
print("ventana_previa() — nada del futuro, nunca")
print("")

i = 30
prev = M.ventana_previa(PARTIDOS, i, dias=365)
prueba("devuelve algo", len(prev) > 0)
prueba("NADA con fecha igual o posterior a la del partido",
       all(x["fecha"] < PARTIDOS[i]["fecha"] for x in prev))
prueba("nada fuera de la ventana de días",
       all((PARTIDOS[i]["fecha"] - x["fecha"]).days <= 365 for x in prev))
prueba("y no se salta ninguno de los que sí entran",
       len(prev) == sum(1 for x in PARTIDOS[:i]
                        if (PARTIDOS[i]["fecha"] - x["fecha"]).days <= 365))

# El caso que rompe una medición sin avisar: dos partidos el MISMO día.
# El segundo no puede usar al primero — cuando se predice una fecha, esa
# fecha entera todavía no se jugó.
mismo_dia = [p(0), p(0, home="C", away="D"), p(5)]
prueba("un partido del mismo día no entra a la ventana",
       M.ventana_previa(mismo_dia, 1, 365) == [])

prueba("el primer partido no tiene historia", M.ventana_previa(PARTIDOS, 0, 365) == [])
prueba("una ventana corta recorta de verdad",
       len(M.ventana_previa(PARTIDOS, i, 30)) < len(prev))
prueba("una lista vacía no rompe", M.ventana_previa([], 0, 365) == [])


print("")
print("tasa_base() — el baseline honesto, sin mirar el resultado que predice")
print("")

# Comparar contra "siempre 33%" es una vara falsa: el local gana bastante
# más que un tercio. La vara justa es la frecuencia histórica, y tiene
# que salir SOLO de los partidos previos.
locales = [p(d, gh=2, ga=0) for d in range(0, 100, 10)]     # gana el local siempre
tb = M.tasa_base(locales)
prueba("suma 1", abs(sum(tb) - 1) < 1e-9)
prueba("si siempre ganó el local, lo refleja", tb[0] > 0.8)

mixto = [p(0, gh=1, ga=0), p(1, gh=0, ga=0), p(2, gh=0, ga=1), p(3, gh=1, ga=0)]
tb2 = M.tasa_base(mixto)
prueba("reparte según lo que pasó", abs(tb2[0] - 0.5) < 1e-9)
prueba("cuenta los empates", abs(tb2[1] - 0.25) < 1e-9)
prueba("y las visitas", abs(tb2[2] - 0.25) < 1e-9)
prueba("sin historia cae al tercio",
       all(abs(x - 1/3) < 1e-9 for x in M.tasa_base([])))


print("")
print("puntajes")
print("")

prueba("acertar con certeza da Brier 0", M.brier([1, 0, 0], [1, 0, 0]) == 0)
prueba("errar con certeza da Brier 2", M.brier([0, 0, 1], [1, 0, 0]) == 2)
prueba("el tercio parejo da 2/3",
       abs(M.brier([1/3, 1/3, 1/3], [1, 0, 0]) - 2/3) < 1e-9)
prueba("una probabilidad mejor puntúa más bajo",
       M.brier([0.6, 0.2, 0.2], [1, 0, 0]) < M.brier([0.4, 0.3, 0.3], [1, 0, 0]))


print("")
print("evaluar() — la corrida completa")
print("")

# Con historia suficiente tiene que producir filas; con menos del mínimo,
# ninguna. El burn-in existe para no evaluar con dos partidos de muestra.
filas = M.evaluar(PARTIDOS, min_previos=5, ventana=365)
prueba("produce filas", len(filas) > 0)
prueba("nunca evalúa antes del mínimo", len(filas) <= len(PARTIDOS) - 5)
f = filas[0]
prueba("cada fila trae la del modelo", len(f["modelo"]) == 3)
prueba("la del mercado", len(f["mercado"]) == 3)
prueba("la tasa base", len(f["base"]) == 3)
prueba("y lo que pasó", sum(f["real"]) == 1)
prueba("las tres probabilidades del modelo suman 1",
       abs(sum(f["modelo"]) - 1) < 1e-6)
prueba("las del mercado también", abs(sum(f["mercado"]) - 1) < 1e-6)

prueba("con un mínimo imposible no evalúa nada",
       M.evaluar(PARTIDOS, min_previos=999, ventana=365) == [])
prueba("sin partidos no rompe", M.evaluar([], min_previos=5, ventana=365) == [])

# Un partido sin cuota se puede usar para ajustar pero no para comparar
# contra el mercado: no debe aparecer como fila evaluada.
sin_c = [dict(x, cuotas=None, fuente=None) for x in PARTIDOS]
prueba("los partidos sin cuota no se evalúan",
       M.evaluar(sin_c, min_previos=5, ventana=365) == [])


print("")
print("VENTANA — la medición no puede darle menos historia que la app")
print("")

# Este test existe por un error real, encontrado el 2026-08-25.
#
# VENTANA estaba en 365 días, y el comentario que lo justificaba decía
# textual que "con VIDA_MEDIA_DIAS = 45, un partido de hace un año pesa
# 0.0036". Cierto entonces; con la vida media en 300 ese partido pesa
# 0.43. El comentario sobrevivió a su propio dato, igual que el de `rho`.
#
# Pero lo grave no era el peso: era que la app NO corta ahí. Publica con
# TEMPORADAS_HISTORIA = 5 temporadas (actualizar.py, get_historia()), así
# que la medición venía evaluando un modelo con un año de historia
# mientras el modelo real tenía cinco. Todo lo medido salía peor de lo
# que el modelo publicado es — y no "un poco": en arg el atraso contra
# el cierre bajó de 0.01594 a 0.01085 con solo darle la historia que le
# corresponde.
#
# La regla que este test fija no es "365 está mal". Es que la medición
# no puede ser más pobre que la producción: si alguien sube
# TEMPORADAS_HISTORIA, esto tiene que fallar hasta que VENTANA lo siga.
import actualizar as A

prueba("VENTANA cubre las temporadas que la app le da al modelo",
       M.VENTANA >= A.TEMPORADAS_HISTORIA * 365)
prueba("y no es tan larga que mida algo que la app nunca ve",
       M.VENTANA <= (A.TEMPORADAS_HISTORIA + 1) * 365)


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
