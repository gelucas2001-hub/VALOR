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
| `datos.py` | ✅ Listo, 9 herramientas, 14 casos probados incluidos los de error |
| `bot.py` | ✅ Listo. Falta correrlo contra la API de verdad |
| `informe.py` | ⬜ Abajo |
| `vigilante.py` | ⬜ Abajo — **es el que lo hace humano** |
| `memoria.json` + `anotar` | ⬜ Abajo |
| `cierre.py` | ⬜ Abajo |
| El goleador | ⬜ Una línea, abajo |

## Para arrancar

```
pip install anthropic
set ANTHROPIC_API_KEY=...        (console.anthropic.com)
set TELEGRAM_BOT_TOKEN=...       (@BotFather → /newbot)
python experto/bot.py
```

`python experto/bot.py --consola` prueba la voz sin Telegram.

---

## 1 · `memoria.json` y el verbo `anotar` — hacer esto primero

Todo lo demás lo necesita. Hoy `datos.banca()` y `datos.registro()` leen
`experto/memoria.json`, que **todavía no existe**; devuelven vacío y
avisan, que es el comportamiento correcto mientras tanto.

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

## 2 · `informe.py` — el parte de la fecha

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

## 3 · `vigilante.py` — el que escribe sin que le pregunten

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
- **No agregar dependencias a `datos.py`** — lo puede importar el cron.
  `bot.py` sí usa el SDK de Anthropic; corre en la máquina de Lucas.
- **No sacar los avisos de `datos.py`** (córners por equipo, el 30% que
  no arranca, la frescura del precio). Son mediciones del repo, no
  adornos: sin ellos el asesor recomienda cosas que están medidas como
  malas.
