#!/usr/bin/env python3
"""Una foto de las líneas de jugador PEGADA AL INICIO del partido.

Por qué existe:

`medir_props.py` puede medir CLV en las líneas de jugador — es el único
instrumento que dice si hay ventaja sin esperar mil apuestas. Pero el
2026-08-31, al correrlo por primera vez, apareció esto: **11 de 19
apuestas tenían el precio clavado** entre la primera foto y la última.
El CLV de esas es cero por construcción, y el instrumento no está
midiendo nada.

La causa no es el mercado: es nuestra cadencia. El cron corre a las
09:00 y 15:00 de Argentina, y los partidos arrancan entre las 08:00 y
las 21:00. Para uno de las 19:00, la última foto es de cuatro horas
antes — justo antes de que la línea se mueva de verdad, que es cuando
entra el dinero informado y se confirman las alineaciones.

Qué hace, y por qué no es "correr el cron más seguido":

Correr `actualizar.py` cada hora cuesta ~55 pedidos a odds-api por
corrida (uno por liga más uno por partido). Esto pide **solo los
partidos que arrancan en las próximas VENTANA_HORAS**, que son un
puñado: entre cero y cinco pedidos por corrida. La foto cara se saca
solo donde sirve.

Lo que NO hace: no toca `partidos.json`, no recalcula λ, no cambia nada
de lo que la app muestra. Solo agrega fotos a
`data/props_jugadores.json`, que es un archivo que solo crece y que
nadie más escribe. Sin `ODDS_API_KEY` no hace nada y sale sin ruido,
igual que el resto de la fuente.

    python foto_props.py            # las próximas 2 horas
    python foto_props.py --horas 3
    python foto_props.py --ver      # qué haría, sin pedir ni escribir
"""

import datetime
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent

PARTIDOS = RAIZ / "data" / "partidos.json"
PROPS = RAIZ / "data" / "props_jugadores.json"

# Cuánto antes del inicio se saca la foto. Dos horas es el compromiso:
# lo bastante cerca para agarrar el movimiento de las alineaciones (que
# se confirman ~1 hora antes) y lo bastante lejos para que la casa
# todavía tenga la pizarra abierta.
VENTANA_HORAS = 2

# El desfasaje de `hora` en partidos.json, que viene en hora de
# Argentina (UTC-3) mientras el runner de GitHub corre en UTC.
TZ_ARG = datetime.timezone(datetime.timedelta(hours=-3))


def leer(ruta):
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def inicio_de(p):
    """El arranque del partido, con zona. None si el dato no alcanza."""
    fecha, hora = p.get("date"), p.get("hora")
    if not fecha or not hora:
        return None
    try:
        d = datetime.date.fromisoformat(str(fecha)[:10])
        hh, mm = str(hora).split(":")[:2]
        return datetime.datetime(d.year, d.month, d.day, int(hh), int(mm),
                                 tzinfo=TZ_ARG)
    except (ValueError, TypeError):
        return None


def por_arrancar(partidos, ahora, horas=VENTANA_HORAS):
    """Los que arrancan dentro de la ventana y todavía no empezaron.

    El corte de abajo es tan importante como el de arriba: pedirle la
    pizarra a un partido que ya se juega devuelve precios en vivo, que
    son otro mercado y no se pueden comparar contra la apertura.
    """
    fin = ahora + datetime.timedelta(hours=horas)
    out = []
    for p in partidos or []:
        t = inicio_de(p)
        if t and ahora <= t <= fin:
            out.append((t, p))
    return [p for _t, p in sorted(out, key=lambda x: x[0])]


def main(argv):
    import actualizar as A

    horas = VENTANA_HORAS
    if "--horas" in argv:
        horas = float(argv[argv.index("--horas") + 1])
    ver = "--ver" in argv

    ahora = datetime.datetime.now(TZ_ARG)
    d = leer(PARTIDOS) or []
    partidos = d.get("partidos") if isinstance(d, dict) else d
    proximos = por_arrancar(partidos, ahora, horas)

    print(f"\n  FOTO PEGADA AL INICIO — {ahora:%Y-%m-%d %H:%M} ARG")
    print(f"  {len(proximos)} partido(s) arrancan en las próximas {horas:g} h\n")
    for p in proximos:
        print(f"    {p.get('hora')}  {p.get('home')} vs {p.get('away')}"
              f"  ({p.get('comp')})")
    if not proximos:
        print("    (nada que fotografiar)\n")
        return 0
    if ver:
        print("\n  --ver: no se pidió nada ni se escribió nada.\n")
        return 0

    key = A.ME.clave() if hasattr(A, "ME") else None
    if not key:
        print("\n  FALTA ODDS_API_KEY. Sin ella esto no hace nada, y la app"
              " queda igual.\n")
        return 0

    cache, pedidos = {}, 0
    for p in proximos:
        slug = p.get("liga")
        if not slug:
            # Sin slug no se sabe a qué liga pedirle los eventos. Pasa
            # con los archivos escritos antes del 2026-08-31.
            continue
        evs = A.eventos_extra(slug, key, cache)
        mx = A.mercado_extra_de(p, evs, key)
        pedidos += 1
        if mx:
            p["mercadoExtra"] = mx

    previas = leer(PROPS) or {}
    antes = sum(len(v) for v in previas.values())
    salida = A.snapshot_props(previas, proximos, ahora.strftime("%Y-%m-%dT%H:%M"))
    despues = sum(len(v) for v in salida.values())

    PROPS.parent.mkdir(parents=True, exist_ok=True)
    PROPS.write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    print(f"\n  {pedidos} pedido(s) a odds-api · {despues - antes} foto(s) nuevas")
    print(f"  {len(salida)} series en data/props_jugadores.json\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
