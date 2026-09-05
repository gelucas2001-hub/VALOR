#!/usr/bin/env python3
"""El parte de la fecha — el mensaje que llega solo a la mañana.

Junta los partidos del día, le pide a Claude el parte con la voz de
`voz.md`, y lo manda por Telegram.

    python experto/informe.py            # manda el parte de hoy
    python experto/informe.py --ver      # lo imprime, no lo manda
    python experto/informe.py 2026-09-06

No reimplementa la voz: lee el mismo `voz.md` que el bot y le agrega
una instrucción de formato. Si la voz se ajusta en un lado, se ajusta
en los dos.
"""

import datetime
import json
import os
import sys

import anthropic

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import datos as D
import bot as B

# Cuántos partidos se miran en profundidad. Los demás entran igual en el
# parte, con una línea — un partido que no aparece se lee como un partido
# que nadie miró.
A_FONDO = 12

FORMATO = """\
Escribí el parte de la fecha para Lucas. Es el mensaje que abre el día,
así que va todo en una sola pieza y en este orden:

1. **Lo que jugaría hoy.** Arriba de todo, antes de cualquier explicación.
   Si no hay nada para jugar, decilo en una línea y explicá por qué — eso
   también es un parte completo.
2. **Los partidos que se pueden leer**, ordenados por cuánto sabés, no
   por horario. De cada uno: la lectura, y si hay algo para comprar o no.
3. **Los que no se pueden leer**, con una línea cada uno diciendo por qué.
   Van igual: uno que no aparece parece uno que nadie miró.

Es Telegram, así que sin tablas y sin markdown pesado. Párrafos cortos.
Nombres de equipo en MAYÚSCULA para separar los bloques. Todo lo que
digas sale de los datos de abajo; si algo te falta, decí que te falta.
"""


def juntar(fecha):
    """El expediente del día. `datos_partido` de todos; los jugadores solo
    de los que se pueden leer, que es donde importan."""
    dia = D.partidos_del_dia(fecha)
    if not dia["partidos"]:
        return None, dia
    a_fondo = [p for p in dia["partidos"] if p["pista"] != "parejo, difícil de leer"]
    a_fondo = (a_fondo or dia["partidos"])[:A_FONDO]
    hondo = {p["id"] for p in a_fondo}

    expediente = []
    for p in dia["partidos"]:
        e = {"resumen": p, "numeros": D.datos_partido(p["id"])}
        if p["id"] in hondo:
            e["historial"] = D.historial(p["id"])
            e["movimiento"] = D.movimiento(p["id"])
            if p["jugadores_cotizados"]:
                j = D.jugadores_partido(p["id"])
                # Solo los que cruzan con serie propia: del resto no se
                # puede decir nada y ocupan lugar.
                if "jugadores" in j:
                    j["jugadores"] = [x for x in j["jugadores"]
                                      if x["cruzo_con_nuestra_serie"]][:12]
                e["jugadores"] = j
        expediente.append(e)
    return expediente, dia


def escribir(expediente, dia):
    cliente = anthropic.Anthropic()
    r = cliente.messages.create(
        model=B.MODELO,
        max_tokens=B.MAX_TOKENS,
        system=[{"type": "text", "text": B.voz(),
                 "cache_control": {"type": "ephemeral"}}],
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": "%s\n\nBANCA Y REGISTRO:\n%s\n\n"
                                              "LOS PARTIDOS:\n%s" % (
            FORMATO,
            json.dumps(D.banca(), ensure_ascii=False),
            json.dumps(expediente, ensure_ascii=False))}],
    )
    return "".join(b.text for b in r.content if b.type == "text").strip()


def main():
    args = [a for a in sys.argv[1:]]
    ver = "--ver" in args
    fecha = next((a for a in args if a.startswith("2")), None)
    fecha = fecha or datetime.date.today().isoformat()

    D.recargar()
    expediente, dia = juntar(fecha)
    if not expediente:
        print("No hay partidos el %s." % fecha)
        return

    print("Armando el parte de %s — %d partidos, datos %s."
          % (fecha, dia["cuantos"], dia["desde_cuando"]["texto"]))
    texto = escribir(expediente, dia)

    if ver:
        print("\n" + texto)
        return
    chat = D.chat_guardado()
    if not chat:
        print("\nNo sé a qué chat mandarlo. Escribile al bot una vez y "
              "queda guardado.\n")
        print(texto)
        return
    B.responder(chat, texto)
    print("Mandado.")


if __name__ == "__main__":
    main()
