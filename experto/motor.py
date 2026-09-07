#!/usr/bin/env python3
"""El motor de lenguaje, intercambiable.

Pronóstic no depende de un proveedor. Acá vive lo único que sí: la
llamada al modelo y el bucle de herramientas. Todo lo demás —`datos.py`,
`voz.md`, `informe.py`, `vigilante.py`— es igual con cualquiera.

Elige solo, en este orden:

1. **Gemini** si está `GEMINI_API_KEY`. Es el que puede andar **gratis**:
   el nivel gratuito quedó solo con modelos Flash, y ahí entran de 10 a
   15 pedidos por minuto y ~1.500 por día. Para 20-25 partidos sobra.
   `gemini-3.8-flash` (2026-09-02) es el mejor Flash que hay y soporta
   herramientas; si tu cuenta no lo tiene gratis, `_elegir()` baja solo
   al siguiente de la lista.
2. **Claude** si está `ANTHROPIC_API_KEY`. Es mejor para esta tarea,
   pero la API se paga.

    pip install google-genai
    setx GEMINI_API_KEY ...        (aistudio.google.com/apikey)
    python experto/motor.py         # dice qué motor y qué modelos hay

El modelo se puede fijar con `PRONOSTIC_MODELO`. Si no está, se usa el
primero de `PREFERIDOS` que la cuenta tenga disponible — preguntándole a
la API, no adivinando: los nombres cambian seguido y un modelo
inventado falla recién en producción.
"""

import json
import os
import sys
import time

# Los nombres cambian rápido —Google sacó tres Flash en seis semanas—, así
# que esto es una preferencia, no una verdad: se prueban en orden contra
# lo que la cuenta tenga de verdad, y si no está ninguno se agarra el
# Flash más nuevo que aparezca.
PREFERIDOS_GEMINI = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.8-flash",
                     "gemini-3.7-flash", "gemini-3.1-flash-lite", "gemini-3-flash"]
MODELO_CLAUDE = "claude-opus-5"
MAX_VUELTAS = 12          # tope de idas y vueltas de herramientas por turno
# Cuántos bloques de conversación se guardan. Importa más de lo que
# parece: un resultado de `jugadores_partido` son 30 KB, y una charla de
# un sábado entero sin recortar se come el límite de tokens por minuto
# del nivel gratuito.
MEMORIA = 40


def _recortar(historia, es_usuario_limpio):
    """Deja los últimos bloques, sin dejar una llamada a herramienta huérfana.

    Cortar en cualquier lado rompe la conversación: si el corte cae entre
    el pedido de una herramienta y su resultado, el modelo recibe una
    respuesta sin pregunta y la API la rechaza. Por eso se avanza hasta
    el primer mensaje de usuario que sea texto de verdad.
    """
    if len(historia) <= MEMORIA:
        return historia
    corte = len(historia) - MEMORIA
    while corte < len(historia) and not es_usuario_limpio(historia[corte]):
        corte += 1
    return historia[corte:] if corte < len(historia) else historia


def cual():
    """Qué motor hay disponible. Gemini primero porque es el gratis."""
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return None


def crear(sistema, herramientas, ejecutar):
    """Devuelve un asesor con memoria de conversación.

    `herramientas` son diccionarios `{name, description, input_schema}` —
    el mismo formato para los dos motores; cada backend lo traduce.
    `ejecutar` es `{nombre: función(args) -> dict}`.
    """
    motor = cual()
    if motor == "gemini":
        return _Gemini(sistema, herramientas, ejecutar)
    if motor == "claude":
        return _Claude(sistema, herramientas, ejecutar)
    raise SystemExit(
        "No hay motor. Poné GEMINI_API_KEY (gratis, aistudio.google.com/apikey)\n"
        "o ANTHROPIC_API_KEY (se paga). Ver experto/ARRANCAR.md.")


# --------------------------------------------------------------- Gemini

class _Gemini:

    def __init__(self, sistema, herramientas, ejecutar):
        from google import genai
        from google.genai import types
        self.types = types
        self.cliente = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY"))
        self.modelo = os.environ.get("PRONOSTIC_MODELO") or self._elegir()
        self.sistema = sistema
        self.ejecutar = ejecutar
        self.historia = []
        self.tool = types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name=h["name"], description=h["description"],
                parameters_json_schema=h["input_schema"])
            for h in herramientas])
        if "buscar" in [h["name"] for h in herramientas]:
            self.ejecutar["buscar"] = self._buscar_web

    def _buscar_web(self, args):
        consulta = (args or {}).get("consulta", "")
        if not consulta:
            return {"error": "falta consulta"}
        try:
            cfg = self.types.GenerateContentConfig(
                tools=[self.types.Tool(google_search=self.types.GoogleSearch())]
            )
            r = self.cliente.models.generate_content(
                model=self.modelo, contents="Novedades y actualidad sobre: " + consulta,
                config=cfg
            )
            return {"resultado": (r.text or "").strip() or "Sin resultados recientes."}
        except Exception as e:
            return {"error": "Error en búsqueda web: %s" % e}

    def modelos(self):
        try:
            return [m.name.replace("models/", "")
                    for m in self.cliente.models.list()]
        except Exception as e:
            return ["(no pude listar: %s)" % e]

    def _elegir(self):
        hay = set(self.modelos())
        for m in PREFERIDOS_GEMINI:
            if m in hay:
                return m
        flash = sorted(x for x in hay if "flash" in x and "thinking" not in x)
        if flash:
            return flash[-1]
        raise SystemExit("No encontré ningún modelo Flash en tu cuenta. "
                         "Corré `python experto/motor.py` para ver cuáles hay.")

    def _config(self):
        return self.types.GenerateContentConfig(
            system_instruction=self.sistema, tools=[self.tool],
            automatic_function_calling=self.types
            .AutomaticFunctionCallingConfig(disable=True))

    def _pedir(self, contenidos):
        reintentos = 3
        for intento in range(reintentos):
            try:
                return self.cliente.models.generate_content(
                    model=self.modelo, contents=contenidos, config=self._config())
            except Exception as e:
                msg = str(e).lower()
                es_cuota_modelo = "429" in msg and ("perday" in msg or "freetier" in msg or "limit: 20" in msg)
                if not es_cuota_modelo:
                    es_transitorio = any(x in msg for x in ("429", "quota", "resource_exhausted", "503", "unavailable", "high demand"))
                    if es_transitorio and intento < reintentos - 1:
                        time.sleep(2 * (intento + 1))
                        continue
                # Fallback transparente a modelos de respaldo
                for alt in ("gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"):
                    if alt != self.modelo:
                        try:
                            res = self.cliente.models.generate_content(
                                model=alt, contents=contenidos, config=self._config())
                            print("  (cambiando a modelo de respaldo: %s)" % alt)
                            self.modelo = alt
                            return res
                        except Exception:
                            continue
                raise

    def preguntar(self, texto):
        t = self.types
        historia_previa = list(self.historia)
        self.historia.append(
            t.Content(role="user", parts=[t.Part.from_text(text=texto)]))

        try:
            for _ in range(MAX_VUELTAS):
                r = self._pedir(self.historia)
                cand = r.candidates[0].content if r.candidates else None
                if cand:
                    self.historia.append(cand)

                llamadas = r.function_calls or []
                if not llamadas:
                    self.historia = _recortar(self.historia, self._limpio)
                    return (r.text or "").strip() or "No me salió nada, probá de nuevo."

                partes = []
                for c in llamadas:
                    print("  [tool]", c.name, dict(c.args or {}))
                    fn = self.ejecutar.get(c.name)
                    salida = (fn(dict(c.args or {})) if fn
                              else {"error": "no tengo esa herramienta"})
                    partes.append(t.Part.from_function_response(
                        name=c.name, response={"resultado": salida}))
                self.historia.append(t.Content(role="user", parts=partes))

            return ("Me quedé dando vueltas pidiendo datos y no llegué a una "
                    "respuesta. Probá preguntándome algo más puntual.")
        except Exception:
            self.historia = historia_previa
            raise

    @staticmethod
    def _limpio(c):
        """Un turno de usuario que NO es respuesta de herramienta."""
        if getattr(c, "role", None) != "user":
            return False
        return not any(getattr(p, "function_response", None)
                       for p in (getattr(c, "parts", None) or []))

    def una_vez(self, prompt):
        """Un pedido suelto, sin memoria — para el parte y el vigilante."""
        viejo, self.historia = self.historia, []
        try:
            return self.preguntar(prompt)
        finally:
            self.historia = viejo


# --------------------------------------------------------------- Claude

class _Claude:

    def __init__(self, sistema, herramientas, ejecutar):
        import anthropic
        self.cliente = anthropic.Anthropic()
        self.modelo = os.environ.get("PRONOSTIC_MODELO") or MODELO_CLAUDE
        self.sistema = [{"type": "text", "text": sistema,
                         "cache_control": {"type": "ephemeral"}}]
        self.herramientas = herramientas + [
            {"type": "web_search_20260209", "name": "web_search", "max_uses": 6}]
        self.ejecutar = ejecutar
        self.historia = []

    def modelos(self):
        try:
            return [m.id for m in self.cliente.models.list()]
        except Exception as e:
            return ["(no pude listar: %s)" % e]

    def preguntar(self, texto):
        self.historia.append({"role": "user", "content": texto})
        for _ in range(MAX_VUELTAS):
            r = self.cliente.messages.create(
                model=self.modelo, max_tokens=16000, system=self.sistema,
                thinking={"type": "adaptive"}, tools=self.herramientas,
                messages=self.historia)
            self.historia.append({"role": "assistant", "content": r.content})

            if r.stop_reason == "refusal":
                return "No puedo contestar eso."
            if r.stop_reason == "pause_turn":
                continue
            if r.stop_reason != "tool_use":
                self.historia = _recortar(self.historia, self._limpio)
                return "".join(b.text for b in r.content
                               if b.type == "text").strip()

            # Todos los resultados en UN mensaje: si se parten, el modelo
            # deja de pedir herramientas en paralelo.
            res = []
            for b in r.content:
                if b.type != "tool_use":
                    continue
                fn = self.ejecutar.get(b.name)
                salida = (fn(b.input or {}) if fn
                          else {"error": "no tengo esa herramienta"})
                res.append({"type": "tool_result", "tool_use_id": b.id,
                            "content": json.dumps(salida, ensure_ascii=False),
                            "is_error": isinstance(salida, dict)
                            and "error" in salida})
            self.historia.append({"role": "user", "content": res})

        return ("Me quedé dando vueltas pidiendo datos y no llegué a una "
                "respuesta. Probá preguntándome algo más puntual.")

    @staticmethod
    def _limpio(m):
        if m.get("role") != "user":
            return False
        c = m.get("content")
        if isinstance(c, str):
            return True
        return not any((b.get("type") if isinstance(b, dict)
                        else getattr(b, "type", None)) == "tool_result"
                       for b in (c or []))

    def una_vez(self, prompt):
        viejo, self.historia = self.historia, []
        try:
            return self.preguntar(prompt)
        finally:
            self.historia = viejo


if __name__ == "__main__":
    m = cual()
    if not m:
        print("Sin motor.\n"
              "  GRATIS:  setx GEMINI_API_KEY ...   (aistudio.google.com/apikey)\n"
              "  SE PAGA: setx ANTHROPIC_API_KEY ...")
        sys.exit(1)
    print("Motor: %s" % m)
    a = crear("probando", [], {})
    print("Modelo elegido: %s\n" % a.modelo)
    print("Disponibles en tu cuenta:")
    for x in a.modelos():
        print("  ", x)
