#!/usr/bin/env python3
"""Tests de medir_metamodelo.py — predecir cuándo nos equivocamos.

El script dio que NO, y por eso los tests importan más, no menos: lo que
hay que proteger es que la vara que lo mató sea confiable. Un resultado
negativo obtenido con un instrumento roto no cierra nada.

Se protegen tres cosas, y son las tres que podrían haberlo dado vuelta:

  - que `previos()` NO mire el partido de hoy ni los futuros. Con `<=`
    en vez de `<`, dos partidos del mismo día se ven entre sí y el
    calendario filtra futuro al pasado.
  - que el objetivo sea el error RELATIVO al mercado y no el absoluto.
    Son cosas distintas y el script encontró que una es predecible y la
    otra no.
  - que exista el placebo, que es la única vara de qué significa "nada".

    python test_medir_metamodelo.py
"""

import datetime as dt
import sys

sys.stdout.reconfigure(encoding="utf-8")

import medir_metamodelo as M

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def cerca(a, b, tol=1e-9):
    return abs(a - b) < tol


def d(s):
    return dt.date.fromisoformat(s)


print("\nprevios() — la fuga de futuro, que es el error caro\n")

CAL = {"A": [d("2024-01-01"), d("2024-01-10"), d("2024-01-20"), d("2024-02-15")]}

prueba("solo mira hacia atrás",
       M.previos(CAL, "A", d("2024-01-15")) == [d("2024-01-01"), d("2024-01-10")])
prueba("el partido de HOY no se ve a sí mismo",
       M.previos(CAL, "A", d("2024-01-10")) == [d("2024-01-01")])
prueba("dos partidos del mismo día no se ven entre sí",
       len(M.previos(CAL, "A", d("2024-01-20"))) == 2)
# Del 15 al 1 hay EXACTAMENTE 14 días, así que con `<= 14` el 1 entra.
# El borde se fija a propósito: es la clase de detalle que cambia una
# variable de congestión sin que nadie lo note.
prueba("la ventana de días incluye el borde exacto",
       M.previos(CAL, "A", d("2024-01-15"), 14) == [d("2024-01-01"), d("2024-01-10")])
prueba("y un día menos ya lo deja afuera",
       M.previos(CAL, "A", d("2024-01-15"), 13) == [d("2024-01-10")])
prueba("un equipo sin historia devuelve vacío, no rompe",
       M.previos(CAL, "Z", d("2024-01-15")) == [])


print("\ncalendario() — cada equipo aporta sus dos lados\n")

PS = [{"fecha": d("2024-01-10"), "home": "A", "away": "B"},
      {"fecha": d("2024-01-01"), "home": "B", "away": "A"}]
cal = M.calendario(PS)
prueba("un partido suma fecha a los dos equipos",
       len(cal["A"]) == 2 and len(cal["B"]) == 2)
prueba("y quedan ordenadas, que es de lo que depende `previos`",
       cal["A"] == sorted(cal["A"]))


print("\nerror_relativo() — el objetivo, que es contra el MERCADO\n")

# Nosotros clavamos el resultado, el mercado le erra: el relativo tiene
# que ser NEGATIVO (somos mejores acá).
mejor = {"modelo": [1.0, 0.0, 0.0], "mercado": [0.4, 0.3, 0.3], "real": [1, 0, 0]}
prueba("si acertamos y el mercado no, da negativo", M.error_relativo(mejor) < 0)

peor = {"modelo": [0.4, 0.3, 0.3], "mercado": [1.0, 0.0, 0.0], "real": [1, 0, 0]}
prueba("y al revés, positivo", M.error_relativo(peor) > 0)

igual = {"modelo": [0.5, 0.3, 0.2], "mercado": [0.5, 0.3, 0.2], "real": [1, 0, 0]}
prueba("si decimos lo mismo, el relativo es cero exacto",
       cerca(M.error_relativo(igual), 0.0))

# Y el punto que justifica usar el relativo: un partido raro castiga a
# los dos y no dice nada de nosotros.
raro = {"modelo": [0.8, 0.1, 0.1], "mercado": [0.8, 0.1, 0.1], "real": [0, 0, 1]}
prueba("un resultado sorpresivo NO cuenta como error nuestro",
       cerca(M.error_relativo(raro), 0.0))


print("\nla vara: el placebo y el corte de mercado\n")

prueba("hay una variable placebo declarada", "placebo" in M.VARIABLES)
prueba("y no mira el precio", M.VARIABLES["placebo"]["mercado"] is False)
prueba("la discrepancia SÍ está marcada como de mercado",
       M.VARIABLES["discrepancia"]["mercado"] is True)
propias = [v for v, c in M.VARIABLES.items() if not c["mercado"]]
prueba("hay al menos cinco variables propias que medir", len(propias) >= 5)
prueba("todas las variables tienen su descripción escrita",
       all(c.get("txt", "").strip() for c in M.VARIABLES.values()))


print("\ncorrel() — no puede inventar señal donde no hay\n")

prueba("una relación perfecta da 1", cerca(M.correl([1, 2, 3, 4] * 10, [2, 4, 6, 8] * 10), 1.0))
prueba("y la inversa, -1", cerca(M.correl([1, 2, 3, 4] * 10, [-2, -4, -6, -8] * 10), -1.0))
prueba("una constante no correlaciona con nada",
       M.correl([5] * 50, list(range(50))) is None)
prueba("con muy poca muestra devuelve None en vez de un número",
       M.correl([1, 2, 3], [1, 2, 3]) is None)

print(f"\n{ok} ok, {fallan} fallando\n")
sys.exit(1 if fallan else 0)
