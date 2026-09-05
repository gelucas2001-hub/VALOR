#!/usr/bin/env python3
"""El que escribe sin que le pregunten.

Corre cada hora. Mira si pasó algo que cambie una decisión ya tomada y,
si pasó, le escribe a Lucas. Es lo que separa un asesor de un informe.

    python experto/vigilante.py          # revisa y avisa
    python experto/vigilante.py --ver    # dice qué avisaría, sin mandar

Dos reglas que hacen que esto sirva en vez de molestar:

* **Solo mira lo que toca una apuesta abierta.** Un aviso sobre un
  partido que a Lucas no le importa gasta el canal.
* **Un aviso que no cambia una decisión no se manda.** Si el bot escribe
  de más, lo silencia y se pierde todo — incluido el aviso que sí
  importaba.

Lo ya avisado queda en `experto/visto.json` para no repetirlo.
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import datos as D
import bot as B

VISTO = os.path.join(AQUI, "visto.json")

# Cuánto se tiene que mover la probabilidad implícita para que valga la
# pena avisar. Debajo de esto es respiración del mercado.
UMBRAL_MOVIMIENTO = 0.08

INSTRUCCION = """\
Sos vos mismo, pero acá no te preguntó nadie: encontraste algo que
cambia una apuesta que Lucas ya tiene puesta, y le vas a escribir sin
que te lo pida.

Escribí UN mensaje de Telegram, de una o dos frases, diciendo qué pasó y
qué hacer. Directo, sin saludo y sin preámbulo. Si son varias cosas,
todas en el mismo mensaje.

Y lo más importante: **si mirando esto pensás que no cambia ninguna
decisión de Lucas, contestá exactamente NADA y nada más.** Un aviso que
no sirve gasta el canal, y el día que mandes uno que importa lo va a
tener silenciado.
"""


def _visto():
    if not os.path.exists(VISTO):
        return {}
    try:
        with open(VISTO, encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return {}


def _marcar(claves):
    v = _visto()
    v.update({k: True for k in claves})
    tmp = VISTO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(v, f)
    os.replace(tmp, VISTO)


def revisar():
    """Qué pasó desde la última vuelta, solo en lo que Lucas tiene jugado."""
    mem = D._memoria()
    abiertas = [a for a in mem.get("apuestas", []) if not a.get("resultado")]
    if not abiertas:
        return [], []

    ya = _visto()
    novedades, claves = [], []

    for a in abiertas:
        pid = a["id_partido"]
        # La primera vuelta de una apuesta solo toma la foto base. Lo que
        # se movió ANTES de que Lucas apostara no es noticia — él ya
        # apostó al precio que vio.
        base = "base|%s" % pid
        primera = base not in ya
        claves.append(base)

        # 1. Se movió el precio del partido.
        mov = D.movimiento(pid)
        qg = (mov or {}).get("quien_gana") or {}
        for lado in ("local", "empate", "visitante"):
            d = qg.get(lado)
            if not isinstance(d, dict) or not d.get("abrio") or not d.get("ahora"):
                continue
            antes, ahora = 1.0 / d["abrio"], 1.0 / d["ahora"]
            if abs(ahora - antes) / antes < UMBRAL_MOVIMIENTO:
                continue
            k = "mov|%s|%s|%s" % (pid, lado, d["ahora"])
            claves.append(k)
            if k in ya or primera:
                continue
            novedades.append({"que": "se movió el precio", "apuesta": a,
                              "lado": lado, "abrio": d["abrio"],
                              "ahora": d["ahora"]})

        # 2. Salió el once, o cambió el que teníamos.
        j = D.jugadores_partido(pid)
        once = (j or {}).get("once_anterior")
        if once:
            firma = json.dumps(once, sort_keys=True, ensure_ascii=False)[:400]
            k = "once|%s|%d" % (pid, hash(firma) % 10**8)
            if not primera and k not in ya:
                novedades.append({"que": "cambió el once que teníamos",
                                  "apuesta": a, "once": once})
            claves.append(k)

        # 3. Cambió el número del partido: la lectura vieja ya no aplica.
        d = D.datos_partido(pid)
        if "error" not in d:
            k = "num|%s|%s" % (pid, d["goles_que_esperamos"]["total"])
            if not primera and k not in ya:
                novedades.append({"que": "cambiaron los goles que esperamos",
                                  "apuesta": a,
                                  "ahora": d["goles_que_esperamos"]})
            claves.append(k)

    return novedades, claves


def redactar(novedades):
    asesor = B.experto()
    return asesor.una_vez("%s\n\nLO QUE ENCONTRÉ:\n%s" % (
        INSTRUCCION, json.dumps(novedades, ensure_ascii=False)))


def main():
    ver = "--ver" in sys.argv
    D.recargar()
    novedades, claves = revisar()

    if not novedades:
        print("Nada que avisar.")
        if claves and not ver:
            _marcar(claves)      # primera vuelta: se toma la foto base
        return

    print("%d novedad(es):" % len(novedades))
    for n in novedades:
        print("  -", n["que"], "|", n["apuesta"]["partido"])

    texto = redactar(novedades)
    if texto.strip().upper().rstrip(".") == "NADA":
        print("El asesor decidió que no cambia ninguna decisión. No mando nada.")
        if not ver:
            _marcar(claves)
        return

    if ver:
        print("\nMandaría:\n" + texto)
        return

    chat = D.chat_guardado()
    if not chat:
        print("No sé a qué chat escribirle todavía.\n" + texto)
        return
    B.responder(chat, texto)
    _marcar(claves)
    print("Avisado.")


if __name__ == "__main__":
    main()
