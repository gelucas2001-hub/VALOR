#!/usr/bin/env python3
"""Tests de historia_reciente() — varias temporadas para ajustar fuerzas.

Por qué existe:

`resultados_temporada()` pide `{season}0101` a hoy, así que el ajuste de
fuerzas nunca veía más que el año calendario en curso — y en enero, casi
nada. Medido sobre el historial completo (barrido de temporadas × vida
media, 2026-08-24): con una sola temporada el modelo en arg.1 captura
**-26.8%** de la ventaja del mercado sobre la tasa base, o sea que
predice PEOR que apostar siempre al local. Con tres temporadas y vida
media 300 captura **+6.9%**. Las dos ligas medidas eligen ese mismo par
por separado, con datos anteriores a 2022.

Lo que estos tests protegen:

- que se pidan de verdad varias temporadas, no una;
- que un partido no se cuente dos veces (se acumula sobre el mismo slug);
- que quede ordenado por fecha, porque todo el ajuste es walk-forward y
  un orden roto filtra futuro al pasado sin avisar;
- que las temporadas pasadas salgan del cache — no cambian nunca, y sin
  cache serían N pedidos extra por competición **en cada corrida** del
  cron, dos veces por día;
- que la temporada en curso NO se cachee, porque sí cambia;
- que si una temporada falla no se pierdan las demás.

    python test_historia.py
"""

import datetime
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
import actualizar

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


HOY = datetime.date(2026, 8, 24)


def partido(season, n):
    return {"fecha": datetime.date(season, 6, 1), "home": "1", "away": "2",
            "gh": 1.0, "ga": 0.0, "id": f"{season}{n}"}


class Espia:
    """Reemplaza a resultados_temporada() y anota qué temporadas se pidieron."""

    def __init__(self, rompe=()):
        self.pedidas = []
        self.rompe = set(rompe)

    def __call__(self, slug, season, hoy):
        self.pedidas.append(season)
        if season in self.rompe:
            raise RuntimeError("ESPN se cayó")
        return [partido(season, 1), partido(season, 2)]


def con_cache_limpio(fn):
    """Cada prueba arranca sin cache: si no, la anterior le deja resultados."""
    tmp = Path(tempfile.mkdtemp())
    orig_dir, orig_rt = actualizar.CACHE_TEMPORADAS, actualizar.resultados_temporada
    actualizar.CACHE_TEMPORADAS = tmp
    try:
        return fn()
    finally:
        actualizar.CACHE_TEMPORADAS = orig_dir
        actualizar.resultados_temporada = orig_rt
        shutil.rmtree(tmp, ignore_errors=True)


print("\nhistoria_reciente() — varias temporadas, no una\n")


def caso_basico():
    espia = Espia()
    actualizar.resultados_temporada = espia
    r = actualizar.historia_reciente("arg.1", 2026, HOY, temporadas=3)
    return espia, r


espia, r = con_cache_limpio(caso_basico)
prueba("pide tres temporadas", sorted(espia.pedidas) == [2024, 2025, 2026])
prueba("y devuelve los partidos de las tres", len(r) == 6)


def caso_una_sola():
    actualizar.resultados_temporada = Espia()
    return actualizar.historia_reciente("arg.1", 2026, HOY, temporadas=1)


prueba("una sola temporada sigue siendo posible",
       len(con_cache_limpio(caso_una_sola)) == 2)


print("\nsin repetidos y en orden — el ajuste es walk-forward\n")


def caso_repetidos():
    # La misma temporada devuelta dos veces: si se concatena sin mirar el
    # id, ese partido pesa doble en el ajuste de fuerzas.
    actualizar.resultados_temporada = lambda slug, season, hoy: [partido(2025, 1)]
    return actualizar.historia_reciente("arg.1", 2026, HOY, temporadas=3)


r2 = con_cache_limpio(caso_repetidos)
prueba("un partido repetido se cuenta una sola vez", len(r2) == 1)

def caso_orden():
    actualizar.resultados_temporada = Espia()
    return actualizar.historia_reciente("arg.1", 2026, HOY, temporadas=3)

r3 = con_cache_limpio(caso_orden)
prueba("queda ordenado del más viejo al más nuevo",
       [p["fecha"] for p in r3] == sorted(p["fecha"] for p in r3))


print("\nel cache: las temporadas pasadas no se vuelven a pedir\n")


def caso_cache():
    espia = Espia()
    actualizar.resultados_temporada = espia
    actualizar.historia_reciente("arg.1", 2026, HOY, temporadas=3)
    primera = list(espia.pedidas)
    espia.pedidas.clear()
    actualizar.historia_reciente("arg.1", 2026, HOY, temporadas=3)
    return primera, espia.pedidas


primera, segunda = con_cache_limpio(caso_cache)
prueba("la primera corrida pide las tres", sorted(primera) == [2024, 2025, 2026])
prueba("la segunda solo pide la temporada en curso", segunda == [2026])
prueba("la en curso SÍ se vuelve a pedir: todavía cambia", 2026 in segunda)


def caso_no_cachea_actual():
    actualizar.resultados_temporada = Espia()
    actualizar.historia_reciente("arg.1", 2026, HOY, temporadas=3)
    return sorted(p.name for p in actualizar.CACHE_TEMPORADAS.glob("*.json"))


archivos = con_cache_limpio(caso_no_cachea_actual)
prueba("guarda un archivo por temporada pasada", len(archivos) == 2)
prueba("y ninguno de la temporada en curso",
       not any("2026" in a for a in archivos))


print("\nque se caiga una temporada no puede costar las otras\n")


def caso_rota():
    actualizar.resultados_temporada = Espia(rompe={2024})
    return actualizar.historia_reciente("arg.1", 2026, HOY, temporadas=3)


r4 = con_cache_limpio(caso_rota)
prueba("si una temporada falla, las demás igual llegan", len(r4) == 4)
prueba("y ninguna es de la que falló",
       all(not p["id"].startswith("2024") for p in r4))


def caso_cache_corrupto():
    tmp = actualizar.CACHE_TEMPORADAS
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "arg.1-2025.json").write_text("{ no es json", encoding="utf-8")
    actualizar.resultados_temporada = Espia()
    return actualizar.historia_reciente("arg.1", 2026, HOY, temporadas=2)


prueba("un cache corrupto se ignora y se vuelve a pedir",
       len(con_cache_limpio(caso_cache_corrupto)) == 4)


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
