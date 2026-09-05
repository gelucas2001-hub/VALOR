#!/usr/bin/env python3
"""Pronóstic — el bot de Telegram.

Escucha Telegram, le pasa la pregunta a Claude con las herramientas de
`datos.py`, y devuelve la respuesta. La voz vive en `voz.md`.

    pip install anthropic
    set ANTHROPIC_API_KEY=...
    set TELEGRAM_BOT_TOKEN=...
    python experto/bot.py

Dos decisiones que conviene tener presentes:

* **`datos.py` es biblioteca estándar; este archivo no.** La regla de
  `CLAUDE.md` es sobre `actualizar.py`, que corre en GitHub Actions sin
  `pip install`. El bot corre en la máquina de Lucas, así que usa el SDK
  oficial de Anthropic, que es lo correcto para hablar con la API.
* **El bucle de herramientas está escrito a mano** en vez de usar el
  `tool_runner` del SDK. Es más código, pero es explícito: se ve dónde se
  ejecuta cada herramienta, no depende de una beta, y quien lo mantenga
  después no tiene que conocer el helper.

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

import anthropic

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import datos as D

MODELO = "claude-opus-5"
MAX_TOKENS = 16000
# Cuántos turnos de ida y vuelta se guardan por conversación. El sistema
# y las herramientas quedan cacheados; esto es lo que crece.
MEMORIA_TURNOS = 40


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
]

# Búsqueda web del lado del servidor: lesiones, técnico, clima, noticias.
# No se ejecuta acá — la corre la API.
HERRAMIENTAS_SERVIDOR = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 6},
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


class Experto:
    """Una conversación. El bucle de herramientas está a la vista."""

    def __init__(self):
        self.cliente = anthropic.Anthropic()
        # El sistema y las herramientas son estables, así que se cachean:
        # se renderizan antes que los mensajes y no cambian entre turnos.
        self.sistema = [{"type": "text", "text": voz(),
                         "cache_control": {"type": "ephemeral"}}]
        self.historia = []

    def preguntar(self, texto):
        D.recargar()          # el cron pudo haber reescrito los datos
        self.historia.append({"role": "user", "content": texto})

        while True:
            r = self.cliente.messages.create(
                model=MODELO,
                max_tokens=MAX_TOKENS,
                system=self.sistema,
                thinking={"type": "adaptive"},
                tools=HERRAMIENTAS + HERRAMIENTAS_SERVIDOR,
                messages=self.historia,
            )
            # Se guardan los bloques enteros, no solo el texto: los de
            # pensamiento y los de herramienta tienen que volver tal cual.
            self.historia.append({"role": "assistant", "content": r.content})

            if r.stop_reason == "refusal":
                return "No puedo contestar eso."

            if r.stop_reason == "pause_turn":
                continue      # el servidor pausó; se retoma con la misma historia

            if r.stop_reason != "tool_use":
                self._recortar()
                return "".join(b.text for b in r.content if b.type == "text").strip()

            # Todos los tool_result van en UN solo mensaje de usuario. Si se
            # parten en varios, el modelo deja de pedir herramientas en paralelo.
            resultados = []
            for b in r.content:
                if b.type == "tool_use":
                    salida = _correr(b.name, b.input or {})
                    resultados.append({
                        "type": "tool_result", "tool_use_id": b.id,
                        "content": json.dumps(salida, ensure_ascii=False),
                        "is_error": "error" in salida,
                    })
            self.historia.append({"role": "user", "content": resultados})

    def _recortar(self):
        """Deja los últimos turnos. Nunca corta dejando un tool_use huérfano."""
        if len(self.historia) <= MEMORIA_TURNOS:
            return
        corte = len(self.historia) - MEMORIA_TURNOS
        while corte < len(self.historia):
            m = self.historia[corte]
            suelto = isinstance(m.get("content"), list) and any(
                getattr(b, "type", None) == "tool_result"
                or (isinstance(b, dict) and b.get("type") == "tool_result")
                for b in m["content"])
            if m["role"] == "user" and not suelto:
                break
            corte += 1
        self.historia = self.historia[corte:]


# ------------------------------------------------------------- el bucle

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Falta ANTHROPIC_API_KEY (console.anthropic.com).")
    print("Pronóstic escuchando. Ctrl+C para cortar.\n")

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
            if texto in ("/start", "/reset"):
                charlas.pop(chat, None)
                responder(chat, "Listo, arrancamos de cero. ¿Qué querés ver?")
                continue

            if chat not in charlas:
                charlas[chat] = Experto()
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
        e = Experto()
        while True:
            try:
                q = input("\nvos> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q:
                print("\nPronóstic>", e.preguntar(q))
    else:
        main()
