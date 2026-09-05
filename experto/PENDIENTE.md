# Pronóstic — lo que falta construir

*Escrito el 2026-09-05 por Claude Code. Diseño completo en
`docs/superpowers/specs/2026-09-05-pronostic-diseno.md`, la lista de los
22 campos está en su §4.*

**Regla de `CLAUDE.md`: una herramienta por área.** `experto/` queda
libre desde que Claude Code termina esta sesión. Quien lo agarre, lo
agarra entero — no dos a la vez.

## Estado

| Archivo | Estado |
|---|---|
| `voz.md` | ✅ Listo. **Se ajusta usándolo, no leyéndolo** |
| `datos.py` | ✅ Listo, 12 herramientas, todas probadas incluidos los de error |
| `motor.py` | ✅ Listo. Elige Gemini (gratis) o Claude según la clave del entorno. **Es el único archivo que sabe de un proveedor** |
| `bot.py` | ✅ Listo. Falta correrlo contra una API de verdad |
| `informe.py` | ✅ Listo. Arma el expediente del día (~31 mil tokens, 20 centavos) y lo manda |
| `vigilante.py` | ✅ Listo. Detecta movimiento de precio, cambio de once y cambio de número; probado que no repite y que no avisa de lo que pasó antes de la apuesta |
| `memoria.json` + `anotar` | ✅ Listo. `anotar`, `poner_banca`, `resolver`, `recordar_chat`, escritura atómica |
| `probar.py` | ✅ Listo. Chequeo de instalación sin gastar API — corrélo antes de diagnosticar nada |
| `cierre.py` | ✅ Listo. Liquida 1X2, goles y jugador (cache local), mide CLV y balance Lucas vs Pronóstic con error estándar |
| El goleador | ⬜ Una línea, abajo |

## Para arrancar

```
pip install google-genai
set GEMINI_API_KEY=...           (gratis - aistudio.google.com/apikey)
set TELEGRAM_BOT_TOKEN=...       (@BotFather → /newbot)
python experto/bot.py
```

`python experto/bot.py --consola` prueba la voz sin Telegram, y
`python experto/motor.py` dice qué motor y qué modelos hay.

**Y sin ninguna clave también se puede**: ver `experto/SIN_CLAVE.md` —
Antigravity, OpenCode o Hermes leen `voz.md`, corren `datos.py` y hacen
de asesor. Es la forma más rápida de probar si la voz sirve.

---

## 1 · `memoria.json` — ✅ HECHO, así quedó

`memoria.json` se crea solo la primera vez que se escribe algo. Las
funciones son `anotar`, `poner_banca`, `resolver`, `recordar_chat` y
`chat_guardado`, todas en `datos.py` y expuestas como herramientas.
Escribe con temporal y `os.replace`.

```json
{
  "banca": 100000,
  "preferencias": {"casa": "Bet365", "ligas": ["arg.1", "eng.1"]},
  "apuestas": [
    {"fecha": "2026-09-06", "id_partido": "espn401841546",
     "mercado": "Matías Fernández más de 2.5 remates", "cuota": 2.10,
     "monto": 3000, "resultado": null, "quien": "pronostic"}
  ]
}
```

- `resultado`: `null` mientras está abierta, después `"ganada"` / `"perdida"` / `"nula"`.
- `quien`: `"pronostic"` si la propuso el asesor, `"lucas"` si fue idea de él.
  **Esa distinción es la que después permite medir a cada uno por separado**,
  y es la razón de ser de la capa 5. No la saques.

**Herramienta nueva en `datos.py` y en `bot.HERRAMIENTAS`:**
`anotar(id_partido, mercado, cuota, monto, quien)` — agrega la apuesta y
guarda el archivo. Y `poner_banca(monto)`.

Escribir con archivo temporal y `os.replace`: si se corta a la mitad, no
se pierde el registro.

---

## 2 · `informe.py` — ✅ HECHO

Un mensaje de Telegram, no una página. Corre por cron los días con
partidos, a las 09:00 ARG.

1. `datos.partidos_del_dia()`.
2. Para cada uno: `datos_partido`, y `jugadores_partido` solo en los que
   la pista dice que se pueden leer — ahorra tokens y no cambia nada.
3. Una sola llamada a Claude con `voz.md` y todo eso, pidiendo el parte:
   **primero qué jugaría, después los partidos ordenados por cuánto
   sabemos, y al final los que no se pueden leer con una línea cada uno.**
4. `bot.responder(chat_id, texto)`.

Con 20-25 partidos son centavos. **No reimplementes la voz acá**: se lee
el mismo `voz.md`, con una instrucción extra de formato al final.

---

## 3 · `vigilante.py` — ✅ HECHO

**Es el campo 19 y el que separa esto de un informe.** Corre cada hora
entre las 07:00 y las 22:00.

Guarda su propio estado en `experto/visto.json` para no repetir el mismo
aviso dos veces.

Tres disparadores, y cada uno se manda **solo si toca una apuesta abierta
de `memoria.json` o un partido del parte de hoy**:

| Disparador | Cómo se detecta | Qué manda |
|---|---|---|
| **Salió el once** | ESPN publica el titular ~1h antes. Comparar contra `planteles.json → once` | *"Salió el once. Fernández va al banco — se cae la de ayer, no la juegues."* |
| **Se movió el precio** | `datos.movimiento()`. Umbral: 8% de cambio en la implícita | *"Fernández se fue de 2.10 a 1.85. A ese precio ya no me gusta."* |
| **Se rompió la lectura** | Un λ que cambió fuerte, o un partido que pasó a estar sin precio | *"Cambió el número de este partido, la lectura de ayer ya no aplica."* |

Redacta con `voz.md`, en una o dos frases. **Un aviso que no cambia una
decisión no se manda** — si el bot escribe de más, Lucas lo silencia y se
pierde el canal entero.

---

## 4 · `cierre.py` — cómo salió, y quién acierta

Corre a la mañana siguiente.

1. Cruza `memoria.json → apuestas` abiertas contra `data/resultados.json`.
2. Resuelve las de resultado y goles solas. **Las de jugador NO se pueden
   resolver del marcador** — hay que pedir los remates del `/summary` de
   ESPN, que ya baja `actualizar.py`.
3. Manda un mensaje corto con qué salió, y **una vez por semana** el
   corte que importa: cómo viene lo que propuso el asesor contra lo que
   propuso Lucas, separado por `quien`.

**Cuidado con el lenguaje.** Con menos de ~50 apuestas cerradas no se
dice "acertás más en X": se dice "vamos por acá, todavía es poca
muestra". Es la misma regla de §35 del `TRASPASO` — sin muestra se
escribe *no concluyente*, nunca *no funciona*.

---

## 5 · El goleador — una línea

`mercado_extra.py:159` baja solo tres mercados de jugador. El comentario
de arriba dice que en arg.1 queda un bloque sin usar. Agregar:

```python
JUGADOR = {
    "remates": ("Player Shots", "Player Shots O/U"),
    "al_arco": ("Player Shots on Target", "Player Shots on Target O/U"),
    "faltas": ("Player Fouls Committed", "Player Fouls"),
    "gol_o_asistencia": ("Player To Score or Assist",),   # ← nuevo
}
```

Correr `test_mercado_extra.py` después. Que un mercado no venga en una
liga es estado normal: `extraer()` no escribe la clave y listo.

---

## 6 · Cuando esté andando

Mudar `bot.py` y `vigilante.py` a un servidor gratuito para que
contesten con la PC apagada. Media hora. **No lo hagas antes de que la
voz esté afinada** — mientras se ajusta `voz.md`, tenerlo local es más
rápido.

---

## Lo que NO hay que hacer

- **No reescribir el motor.** `datos.py` importa la matriz de
  `backtest.py` y el devig de `medir_clv.py` a propósito.
- **No meter números en `voz.md`.** Los números vienen de las
  herramientas. Un precio escrito en el prompt queda viejo el mismo día.
- **No tocar `actualizar.py`** ni el contrato de `data/partidos.json`.
- **No agregar dependencias a `datos.py`** — lo puede importar el cron, y
  es lo que hace posible el modo sin clave. Los SDK viven en `motor.py`.
- **No atar ningún archivo nuevo a un proveedor.** Si hace falta hablarle
  a un modelo, se hace por `motor.py`. Lucas no paga API: la ruta por
  defecto es el nivel gratuito de Gemini.
- **No sacar los avisos de `datos.py`** (córners por equipo, el 30% que
  no arranca, la frescura del precio). Son mediciones del repo, no
  adornos: sin ellos el asesor recomienda cosas que están medidas como
  malas.
