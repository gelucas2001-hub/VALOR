#!/usr/bin/env python3
"""Tests de foto_props.py — la foto pegada al inicio.

Qué protegen:

- **El corte de arriba.** Si la ventana se pasa de ancha, esto deja de
  ser una foto dirigida y se vuelve el cron entero corriendo cada hora,
  que es justo el costo que se quería evitar.
- **El corte de abajo, que es el que se olvida.** Pedirle la pizarra a
  un partido que YA empezó devuelve precios en vivo. Son otro mercado y
  compararlos contra la apertura no mide CLV: mide otra cosa y se ve
  igual de bien.
- **La zona horaria.** `partidos.json` guarda la hora de Argentina y el
  runner de GitHub corre en UTC. Tres horas de error mandan la foto al
  momento equivocado y el archivo igual queda lleno de datos.

    python test_foto_props.py
"""

import datetime
import sys

sys.stdout.reconfigure(encoding="utf-8")
import foto_props as F

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def p(hora, fecha="2026-08-31", home="A", away="B"):
    return {"date": fecha, "hora": hora, "home": home, "away": away,
            "comp": "Liga", "liga": "arg.1"}


AHORA = datetime.datetime(2026, 8, 31, 14, 0, tzinfo=F.TZ_ARG)


print("\ninicio_de() — la hora del partido, con zona\n")

t = F.inicio_de(p("16:00"))
prueba("arma el arranque desde fecha y hora", t.hour == 16 and t.day == 31)
prueba("y lo hace en hora de Argentina, no en UTC",
       t.utcoffset() == datetime.timedelta(hours=-3))
prueba("una fecha con hora ISO adentro no lo confunde",
       F.inicio_de({"date": "2026-08-31T00:00Z", "hora": "16:00"}).hour == 16)
prueba("sin hora no inventa un arranque", F.inicio_de({"date": "2026-08-31"}) is None)
prueba("sin fecha tampoco", F.inicio_de({"hora": "16:00"}) is None)
prueba("una hora rota devuelve None en vez de reventar",
       F.inicio_de({"date": "2026-08-31", "hora": "ya mismo"}) is None)


print("\npor_arrancar() — solo los que están por empezar\n")

LISTA = [p("08:00", home="Temprano"), p("14:30", home="EnUnRato"),
         p("15:45", home="JustoAlBorde"), p("19:00", home="MasTarde"),
         p("16:00", fecha="2026-09-01", home="Mañana")]
sel = F.por_arrancar(LISTA, AHORA, horas=2)
nombres = [x["home"] for x in sel]

prueba("agarra el que arranca dentro de la ventana", "EnUnRato" in nombres)
prueba("y el que cae justo en el borde", "JustoAlBorde" in nombres)
prueba("deja afuera el que arranca después de la ventana",
       "MasTarde" not in nombres)
prueba("deja afuera el de otro día", "Mañana" not in nombres)
prueba("y sobre todo el que YA EMPEZÓ: ahí la cuota es en vivo",
       "Temprano" not in nombres)
prueba("vienen ordenados por hora de inicio",
       nombres == sorted(nombres, key=lambda n: [x["hora"] for x in sel
                                                 if x["home"] == n][0]))
prueba("una ventana más ancha agarra más partidos",
       len(F.por_arrancar(LISTA, AHORA, horas=6)) > len(sel))
prueba("sin partidos devuelve una lista vacía, no None",
       F.por_arrancar([], AHORA) == [])
prueba("un partido sin hora no entra ni rompe",
       F.por_arrancar([{"date": "2026-08-31"}], AHORA) == [])

# La zona horaria, que es donde esto se rompe callado: si el runner UTC
# comparara sin zona, un partido de las 16:00 ARG parecería que arranca
# dentro de 1 hora cuando en realidad faltan 4.
UTC = datetime.datetime(2026, 8, 31, 17, 0, tzinfo=datetime.timezone.utc)
prueba("comparando desde UTC da el mismo resultado que desde ARG",
       [x["home"] for x in F.por_arrancar(LISTA, UTC, horas=2)] == nombres)


print("\nleer() — un archivo roto no tira la corrida\n")

from pathlib import Path
import tempfile
tmp = Path(tempfile.mkdtemp())
prueba("un archivo que no está devuelve None", F.leer(tmp / "no_existe.json") is None)
malo = tmp / "roto.json"; malo.write_text("{esto no es json", encoding="utf-8")
prueba("un JSON roto devuelve None en vez de reventar", F.leer(malo) is None)
bueno = tmp / "ok.json"; bueno.write_text('{"a": 1}', encoding="utf-8")
prueba("y uno bueno se lee", F.leer(bueno) == {"a": 1})


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
