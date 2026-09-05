#!/usr/bin/env python3
"""Pronóstic — el bot de Telegram.

Escucha Telegram, le pasa la pregunta al motor de IA con las
herramientas de `datos.py`, y devuelve la respuesta. La voz vive en
`voz.md`; qué modelo contesta lo decide `motor.py`.

    pip install google-genai
    set GEMINI_API_KEY=...            (gratis - aistudio.google.com/apikey)
    set TELEGRAM_BOT_TOKEN=...
    python experto/bot.py

Dos decisiones que conviene tener presentes:

* **`datos.py` es biblioteca estándar; este archivo no.** La regla de
  `CLAUDE.md` es sobre `actualizar.py`, que corre en GitHub Actions sin
  `pip install`. El bot corre en la máquina de Lucas.
* **El modelo vive en `motor.py`, no acá.** Este archivo no sabe con qué
  IA está hablando: declara las herramientas y las ejecuta. Cambiar de
  Gemini a Claude no toca una línea de acá.

Telegram se llama con `urllib` — no hace falta una dependencia para
cuatro pedidos HTTP.
"""

import json
import os
import sys
import time
import traceback
import urllib.parse
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import datos as D
import motor as M


# ------------------------------------------------------------ Telegram

TG = "https://api.telegram.org/bot%s/%s"


def _tg(metodo, **params):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN. Pedíselo a @BotFather.")
    url = TG % (token, metodo)
    cuerpo = urllib.parse.urlencode(
        {k: v for k, v in params.items() if v is not None}).encode()
    req = urllib.request.Request(url, data=cuerpo)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def responder(chat_id, texto):
    """Telegram corta en 4096 caracteres; se parte por párrafo."""
    for trozo in _partir(texto, 3900):
        _tg("sendMessage", chat_id=chat_id, text=trozo)


def _partir(texto, tope):
    if len(texto) <= tope:
        return [texto]
    partes, actual = [], ""
    for parrafo in texto.split("\n\n"):
        if len(actual) + len(parrafo) + 2 > tope and actual:
            partes.append(actual)
            actual = parrafo
        else:
            actual = (actual + "\n\n" + parrafo) if actual else parrafo
    if actual:
        partes.append(actual)
    return partes


# --------------------------------------------------------- herramientas

HERRAMIENTAS = [
    {
        "name": "partidos_del_dia",
        "description": ("Qué partidos se juegan. Sin fecha, trae de hoy en "
                        "adelante. Trae una pista de si el partido se puede "
                        "leer o no, para poder ordenar la fecha por eso."),
        "input_schema": {
            "type": "object",
            "properties": {"fecha": {"type": "string",
                                     "description": "AAAA-MM-DD. Opcional."}},
        },
    },
    {
        "name": "datos_partido",
        "description": ("Todo lo numérico de un partido: goles que esperamos, "
                        "nuestro número de cada cien para cada mercado, los "
                        "precios de Bet365 con lo que cobra la casa, y de "
                        "cuándo son los datos. Es la herramienta principal."),
        "input_schema": {
            "type": "object",
            "properties": {"id_partido": {"type": "string"}},
            "required": ["id_partido"],
        },
    },
    {
        "name": "jugadores_partido",
        "description": ("Las escaleras de remates de Bet365 de cada jugador, "
                        "cruzadas con su serie real de los últimos partidos, "
                        "más el once con el que arrancó cada equipo el partido "
                        "ANTERIOR."),
        "input_schema": {
            "type": "object",
            "properties": {"id_partido": {"type": "string"}},
            "required": ["id_partido"],
        },
    },
    {
        "name": "movimiento",
        "description": ("Cómo se movió el precio desde la primera foto que "
                        "tenemos. Sirve para decir si la línea se fue para un "
                        "lado o quedó clavada."),
        "input_schema": {
            "type": "object",
            "properties": {
                "id_partido": {"type": "string"},
                "jugador": {"type": "string",
                            "description": "Opcional, nombre exacto."},
            },
            "required": ["id_partido"],
        },
    },
    {
        "name": "historial",
        "description": "Forma de cada equipo, cruces anteriores y tabla.",
        "input_schema": {
            "type": "object",
            "properties": {"id_partido": {"type": "string"}},
            "required": ["id_partido"],
        },
    },
    {
        "name": "revisar_boleta",
        "description": ("La probabilidad real de una combinada, la pata que la "
                        "hunde y la comisión total. `mercado` es una clave de "
                        "`nuestro_numero_de_cada_cien` — por ejemplo "
                        "'Menos de 2.5', '1X2 local', 'Ambos marcan'."),
        "input_schema": {
            "type": "object",
            "properties": {
                "patas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_partido": {"type": "string"},
                            "mercado": {"type": "string"},
                            "cuota": {"type": "number"},
                        },
                        "required": ["id_partido", "mercado"],
                    },
                },
            },
            "required": ["patas"],
        },
    },
    {
        "name": "stake",
        "description": ("Cuánto poner, en pesos de cada cien de la banca. Si "
                        "devuelve cero es que a ese precio no da para apostar."),
        "input_schema": {
            "type": "object",
            "properties": {
                "de_cada_cien": {"type": "number",
                                 "description": "Nuestro número, 0 a 100."},
                "cuota": {"type": "number"},
                "banca": {"type": "number", "description": "Opcional."},
            },
            "required": ["de_cada_cien", "cuota"],
        },
    },
    {
        "name": "banca",
        "description": "Cuánta plata tiene Lucas, cuánto está expuesto y la racha.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "registro",
        "description": "Qué apostó Lucas antes y cómo le fue.",
        "input_schema": {
            "type": "object",
            "properties": {"limite": {"type": "integer"}},
        },
    },
    {
        "name": "anotar",
        "description": ("Deja anotada una apuesta que Lucas jugó. Usala cuando "
                        "te diga que la puso, no cuando se la proponés. `quien` "
                        "es 'pronostic' si la idea fue tuya y 'lucas' si fue de "
                        "él — sirve para después medir a cada uno por separado, "
                        "así que ponelo bien."),
        "input_schema": {
            "type": "object",
            "properties": {
                "id_partido": {"type": "string"},
                "mercado": {"type": "string",
                            "description": "Como se lo diría a una persona."},
                "cuota": {"type": "number"},
                "monto": {"type": "number"},
                "quien": {"type": "string", "enum": ["lucas", "pronostic"]},
                "nota": {"type": "string"},
            },
            "required": ["id_partido", "mercado", "cuota", "monto", "quien"],
        },
    },
    {
        "name": "poner_banca",
        "description": ("Guarda cuánta plata tiene Lucas para apostar. Sin esto "
                        "no le podés decir cuánto poner en pesos."),
        "input_schema": {
            "type": "object",
            "properties": {"monto": {"type": "number"}},
            "required": ["monto"],
        },
    },
    {
        "name": "resolver",
        "description": ("Cierra las apuestas que ya tienen marcador. Las de "
                        "jugador quedan abiertas: no se deducen del marcador."),
        "input_schema": {
            "type": "object",
            "properties": {"id_partido": {"type": "string"}},
        },
    },
]

EJECUTAR = {
    "partidos_del_dia": lambda a: D.partidos_del_dia(a.get("fecha")),
    "datos_partido": lambda a: D.datos_partido(a["id_partido"]),
    "jugadores_partido": lambda a: D.jugadores_partido(a["id_partido"]),
    "movimiento": lambda a: D.movimiento(a["id_partido"], a.get("jugador")),
    "historial": lambda a: D.historial(a["id_partido"]),
    "revisar_boleta": lambda a: D.revisar_boleta(a["patas"]),
    "stake": lambda a: D.stake(a["de_cada_cien"], a["cuota"], a.get("banca")),
    "banca": lambda a: D.banca(),
    "registro": lambda a: D.registro(a.get("limite", 30)),
    "anotar": lambda a: D.anotar(a["id_partido"], a["mercado"], a["cuota"],
                                 a["monto"], a["quien"], a.get("nota")),
    "poner_banca": lambda a: D.poner_banca(a["monto"]),
    "resolver": lambda a: D.resolver(a.get("id_partido")),
}


def _correr(nombre, args):
    try:
        return EJECUTAR[nombre](args)
    except KeyError as e:
        return {"error": "me falta el dato %s" % e}
    except Exception as e:
        return {"error": "la herramienta falló: %s" % e}


# ------------------------------------------------------------ el experto

def voz():
    with open(os.path.join(AQUI, "voz.md"), encoding="utf-8") as f:
        return f.read()


def experto():
    """Un asesor nuevo, con la voz de `voz.md` y las herramientas de arriba.

    Quién contesta —Gemini o Claude— lo decide `motor.py` según la clave
    que haya en el entorno. Acá no se sabe ni hace falta.
    """
    return M.crear(voz(), HERRAMIENTAS, EJECUTAR)


# ------------------------------------------------------------- el bucle

def main():
    if not M.cual():
        raise SystemExit(
            "No hay motor de IA. Poné GEMINI_API_KEY (gratis, "
            "aistudio.google.com/apikey) o ANTHROPIC_API_KEY (se paga).\n"
            "Ver experto/ARRANCAR.md.")
    print("Pronóstic escuchando (motor: %s). Ctrl+C para cortar.\n" % M.cual())

    charlas = {}
    offset = None
    while True:
        try:
            r = _tg("getUpdates", offset=offset, timeout=50)
        except Exception as e:
            print("Telegram no contesta (%s). Reintento en 5s." % e)
            time.sleep(5)
            continue

        for u in r.get("result", []):
            offset = u["update_id"] + 1
            msg = u.get("message") or {}
            texto = (msg.get("text") or "").strip()
            chat = (msg.get("chat") or {}).get("id")
            if not texto or not chat:
                continue

            print("<<", texto)
            # El parte y el vigilante escriben sin que nadie les hable;
            # de acá sacan a dónde.
            D.recordar_chat(chat)

            if texto in ("/start", "/reset"):
                charlas.pop(chat, None)
                responder(chat, "Listo, arrancamos de cero. ¿Qué querés ver?")
                continue

            if chat not in charlas:
                charlas[chat] = experto()
            _tg("sendChatAction", chat_id=chat, action="typing")
            try:
                salida = charlas[chat].preguntar(texto)
            except Exception:
                traceback.print_exc()
                salida = "Se me cayó algo acá. Probá de nuevo en un momento."
            print(">>", salida[:200].replace("\n", " "), "\n")
            responder(chat, salida)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--consola":
        # Para probar la voz sin Telegram: python experto/bot.py --consola
        e = experto()
        while True:
            try:
                q = input("\nvos> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q:
                print("\nPronóstic>", e.preguntar(q))
    else:
        main()
