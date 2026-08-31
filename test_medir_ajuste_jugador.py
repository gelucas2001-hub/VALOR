#!/usr/bin/env python3
"""Tests de medir_ajuste_jugador.py — ¿el rival mueve al jugador?

Qué protegen:

- **La fuga de futuro, por partida doble.** Acá no alcanza con no mirar
  el partido del jugador: tampoco se puede mirar lo que su equipo o su
  rival hicieron ESE día. Son tres acumuladores y los tres se actualizan
  después de evaluar, nunca antes.
- **El factor tiene tope.** Con tres partidos, un rival que se comió dos
  goleadas da un factor de 2.5 que no describe al rival, describe la
  muestra. Recortar es preferir un sesgo chico y conocido a una varianza
  grande y silenciosa.
- **El dejar-uno-afuera.** Las apariciones de un mismo partido comparten
  rival, ritmo y árbitro: no son independientes, y el error estándar no
  lo sabe. Es la lección que costó el falso hallazgo del CLV.

    python test_medir_ajuste_jugador.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import medir_ajuste_jugador as M

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


print("\nequipo_de() — de qué equipo es cada jugador\n")

PL = {"10": [{"id": "1", "nombre": "A"}, {"id": "2", "nombre": "B"}],
      "20": [{"id": "3", "nombre": "C"}]}
eq = M.equipo_de(PL)
prueba("mapea jugador a equipo", eq == {"1": "10", "2": "10", "3": "20"})
prueba("un jugador sin id no entra",
       M.equipo_de({"10": [{"nombre": "X"}]}) == {})
prueba("sin planteles devuelve un mapa vacío, no None", M.equipo_de(None) == {})


print("\nfactor_rival() — cuánto más deja rematar este rival\n")

prueba("un rival del promedio no mueve nada", cerca(M.factor_rival(12.0, 12.0), 1.0))
prueba("uno que concede el doble sube el número", M.factor_rival(24.0, 12.0) > 1)
prueba("uno que concede la mitad lo baja", M.factor_rival(6.0, 12.0) < 1)
prueba("pero el factor está topeado para arriba",
       cerca(M.factor_rival(120.0, 12.0), 1.6))
prueba("y también para abajo",
       cerca(M.factor_rival(0.1, 12.0), 1 / 1.6))
prueba("el tope se puede mover a propósito",
       cerca(M.factor_rival(120.0, 12.0, tope=3.0), 3.0))
prueba("sin media de liga no inventa un factor",
       cerca(M.factor_rival(12.0, None), 1.0))
prueba("con media cero tampoco divide por cero",
       cerca(M.factor_rival(12.0, 0), 1.0))
prueba("sin dato del rival queda neutro",
       cerca(M.factor_rival(None, 12.0), 1.0))


print("\ncomparar() — el error de cada pronóstico\n")

def f(real, hoy, rival, cuota, ev="A"):
    return {"real": real, "hoy": hoy, "rival": rival, "cuota": cuota,
            "ev": ev, "fecha": "2026-01-01", "pid": "1"}

# `rival` clava el real, `hoy` le erra por 1, `cuota` por 2.
FILAS = [f(3.0, 2.0, 3.0, 1.0) for _ in range(20)]
r = M.comparar(FILAS, remuestreos=200)
prueba("mide el error de hoy", cerca(r["e_hoy"], 1.0))
prueba("y el del ajuste por rival", cerca(r["e_rival"], 0.0))
prueba("la ganancia es la diferencia, con signo positivo si mejora",
       cerca(r["gana_rival"], 1.0))
prueba("un ajuste peor da ganancia negativa", r["gana_cuota"] < 0)
prueba("sin filas no devuelve un veredicto", M.comparar([]) is None)

# Todos idénticos: no hay diferencia que medir y el ruido es cero.
IGUALES = [f(3.0, 2.0, 2.0, 2.0) for _ in range(20)]
ri = M.comparar(IGUALES, remuestreos=200)
prueba("dos pronósticos idénticos no se sacan ventaja",
       cerca(ri["gana_rival"], 0.0))
prueba("y su diferencia no tiene ruido", cerca(ri["ee_rival"], 0.0))


print("\ndejar_uno_afuera() — la ganancia sin cada partido\n")

# Nueve apariciones neutras en un partido y cinco buenísimas en otro:
# el promedio da lindo y lo sostiene uno solo.
MEZCLA = ([f(3.0, 2.0, 2.0, 2.0, ev="A") for _ in range(9)]
          + [f(3.0, 2.0, 3.0, 2.0, ev="B") for _ in range(5)])
fuera = M.dejar_uno_afuera(MEZCLA, "rival", remuestreos=100)
prueba("recalcula sacando cada partido", len(fuera) == 2)
sinB = [x for x in fuera if x["sin"] == "B"][0]
prueba("sin el partido que la sostiene, la ganancia desaparece",
       cerca(sinB["gana"], 0.0))
prueba("sin cualquier otro, la ganancia sigue ahí",
       [x for x in fuera if x["sin"] == "A"][0]["gana"] > 0.5)


print("\nevaluar() — sin mirar el partido que predice\n")

def historia(n, extremo=False):
    """Historia mínima que el pipeline acepte de verdad.

    Dos cosas la hacen no-degenerada, y las dos se descubrieron porque
    este test fallaba:

    - los jugadores tienen que DIFERIR entre sí. `parametros_metricas()`
      saca el encogimiento partiendo la variación entre jugadores en
      ruido y señal; con todos iguales no hay nada que partir;
    - tiene que haber al menos `MIN_EQUIPOS` (8) jugadores del mismo
      puesto con dos apariciones. Con menos devuelve {} — que es lo
      correcto en producción y deja el fixture sin parámetros.
    """
    ids = [str(i) for i in range(1, 21)]
    h = []
    for i in range(n):
        jug = {pid: [float((int(pid) * 7 + i * 3) % 5), 1, 0, 0, 0, 0, 1]
               for pid in ids}
        h.append((f"2026-01-{i+1:02d}", str(100 + i), jug,
                  {"10": {"remates": 10.0 + (i % 3)},
                   "20": {"remates": 9.0 + (i % 2)}}))
    if extremo:
        h.append(("2026-02-01", "999",
                  {pid: [99.0, 1, 0, 0, 0, 0, 1] for pid in ids},
                  {"10": {"remates": 99.0}, "20": {"remates": 99.0}}))
    return h


IDS = [str(i) for i in range(1, 21)]
EQ = {pid: ("10" if int(pid) <= 10 else "20") for pid in IDS}
POS = {pid: ("F" if int(pid) % 2 else "M") for pid in IDS}

hist = historia(10)
filas = M.evaluar(hist, EQ, "remates", pos_de=POS)
prueba("evalúa apariciones una vez que hay historia", len(filas) > 0)
prueba("nunca evalúa el primer partido, que no tiene nada previo",
       all(f["ev"] != "100" for f in filas))
prueba("ni ninguno anterior al mínimo de partidos del equipo",
       all(f["ev"] not in ("100", "101", "102") for f in filas))

# La prueba de fuga: un último partido enorme no puede cambiar ninguna
# predicción anterior.
f2 = M.evaluar(historia(10, extremo=True), EQ, "remates", pos_de=POS)
prueba("agregar un partido al final no cambia lo ya predicho",
       [(x["ev"], x["pid"], round(x["hoy"], 9)) for x in f2[:len(filas)]]
       == [(x["ev"], x["pid"], round(x["hoy"], 9)) for x in filas])
prueba("el ajuste por rival nunca es cero ni negativo",
       all(f["rival"] > 0 for f in filas))
prueba("con un jugador sin equipo conocido, esa aparición no entra",
       M.evaluar(hist, {}, "remates", pos_de=POS) == [])


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
