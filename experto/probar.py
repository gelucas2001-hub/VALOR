#!/usr/bin/env python3
"""Chequeo rápido: ¿está todo bien enchufado?

    python experto/probar.py

No gasta un solo pedido de API. Sirve para saber si el problema es la
instalación o es otra cosa, antes de empezar a culpar al código.
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

BIEN, MAL, OJO = "  OK  ", " FALLA", "  ojo "
fallas = []


def probar(nombre, fn, critico=True):
    try:
        detalle = fn()
        print("%s %-38s %s" % (BIEN, nombre, detalle or ""))
    except Exception as e:
        print("%s %-38s %s" % (MAL if critico else OJO, nombre, e))
        if critico:
            fallas.append(nombre)


def main():
    print("\nPronóstic — chequeo de instalación\n" + "-" * 62)

    def _datos():
        import datos as D
        d = D.partidos_del_dia()
        if not d["partidos"]:
            raise RuntimeError("no hay partidos futuros cargados; probá `git pull`")
        return "%d partidos, datos %s" % (d["cuantos"], d["desde_cuando"]["texto"])
    probar("los datos del cron se leen", _datos)

    def _motor_import():
        import backtest, medir_clv          # noqa: F401
        return "matriz de backtest.py y devig de medir_clv.py"
    probar("el motor matemático se importa", _motor_import)

    def _herramientas():
        import bot as B
        d, i = {h["name"] for h in B.HERRAMIENTAS}, set(B.EJECUTAR)
        if d != i:
            raise RuntimeError("descalce: %s" % (d ^ i))
        for h in B.HERRAMIENTAS:
            B._correr(h["name"], {})       # ninguna debe explotar sin argumentos
        return "%d declaradas, %d implementadas, ninguna explota" % (len(d), len(i))
    probar("las herramientas responden", _herramientas)

    def _cuentas():
        import datos as D
        p = D.partidos_del_dia()["partidos"][0]["id"]
        d = D.datos_partido(p)
        n = d["nuestro_numero_de_cada_cien"]
        s = n["1X2 local"] + n["1X2 empate"] + n["1X2 visitante"]
        if not 98 <= s <= 102:
            raise RuntimeError("las tres del 1X2 suman %d, deberían dar 100" % s)
        return "1X2 suma %d de cada cien" % s
    probar("las probabilidades cierran", _cuentas)

    def _sdk():
        import google.genai                # noqa: F401
        return "google-genai instalado"
    probar("el SDK de Gemini", _sdk, critico=False)

    def _motor():
        import motor as M
        q = M.cual()
        if not q:
            raise RuntimeError("sin clave todavía — poné GEMINI_API_KEY "
                               "(gratis, aistudio.google.com/apikey)")
        a = M.crear("probando", [], {})
        return "%s, modelo %s" % (q, a.modelo)
    probar("hay motor de IA y elige modelo", _motor, critico=False)

    def _telegram():
        if not os.environ.get("TELEGRAM_BOT_TOKEN"):
            raise RuntimeError("sin token todavía — @BotFather, /newbot")
        import bot as B
        r = B._tg("getMe")
        return "@%s" % r["result"]["username"]
    probar("Telegram responde", _telegram, critico=False)

    def _memoria():
        import datos as D
        b = D.banca()
        return ("banca $%s, %d abiertas" % (b["banca"], b["apuestas_abiertas"])
                if b["banca"] else "todavía sin banca cargada (normal al empezar)")
    probar("la memoria de apuestas", _memoria, critico=False)

    print("-" * 62)
    if fallas:
        print("\nHay algo roto de verdad: %s" % ", ".join(fallas))
        print("Eso NO es falta de clave — es el código o los datos.\n")
        return 1
    print("\nLo esencial anda. Lo que salga como 'ojo' arriba es algo que")
    print("todavía no configuraste, no algo roto — ver experto/ARRANCAR.md.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
