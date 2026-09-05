# Cómo poner a andar Pronóstic

Todo lo que se podía dejar hecho está hecho. **Quedan dos cosas que solo
podés hacer vos**, porque son cuentas tuyas: sacar dos claves.

---

## Paso 1 — Las dos claves (10 minutos, una sola vez)

### La de Gemini — **gratis, sin tarjeta**

1. Entrá a **aistudio.google.com/apikey** con tu cuenta de Google.
2. **Create API key** → copiala.

Eso es todo. No pide tarjeta ni facturación.

**Qué modelo va a usar.** El código no lo tiene escrito a mano: le
pregunta a la API qué tenés y elige el mejor de la lista. Hoy la
encabeza **`gemini-3.8-flash`**, que salió el 2 de septiembre de 2026 —
1M de contexto, herramientas, y el Flash más capaz que hay. Si tu cuenta
no lo tiene, baja solo al siguiente.

**Lo que entra en el nivel gratuito:** el free tier quedó **solo con
modelos Flash** (Google sacó los Pro en abril de 2026), con 10 a 15
pedidos por minuto y ~1.500 por día. Una fecha de 25 partidos usa un
puñado, así que te sobra.

**El único dato que no te puedo confirmar de acá:** si `gemini-3.8-flash`
entra en tu free tier o pide facturación. Salió hace tres días y los
límites por modelo se ven en el panel de AI Studio, no en la
documentación. **Corré `python experto/motor.py` y te lo dice tu propia
cuenta** — para eso el código pregunta en vez de adivinar.

Si algún día querés comparar contra Claude, poné `ANTHROPIC_API_KEY` en
vez de la de Gemini y cambia solo, sin tocar una línea.

### La de Telegram

1. En Telegram buscá **@BotFather**.
2. Mandale `/newbot`.
3. Te pide un nombre (poné *Pronóstic*) y un usuario que termine en
   `bot` (por ejemplo `pronostic_lucas_bot`).
4. Te devuelve un token largo con dos puntos en el medio. Copialo.

---

## Paso 2 — Guardarlas en tu PC (una sola vez)

Abrí PowerShell y pegá esto, reemplazando por las tuyas:

```
setx GEMINI_API_KEY "AIza-loquetedio"
setx TELEGRAM_BOT_TOKEN "123456:loquetedio"
```

**Cerrá la ventana y abrí una nueva** — `setx` recién se ve en la
siguiente. Para chequear que quedaron:

```
echo $env:GEMINI_API_KEY
```

Van al entorno de Windows, **nunca al repo**. Es la misma regla que
`ODDS_API_KEY`.

---

## Paso 3 — Probar la voz, sin Telegram

Es lo más rápido para ver si suena a experto o a máquina:

```
git pull
pip install google-genai
python experto/motor.py
```

Eso te dice qué motor encontró y **qué modelos tiene tu cuenta**, sin
gastar nada. Si lista modelos, está todo bien. Después:

```
python experto/bot.py --consola
```

Hablale como le hablarías a una persona:

```
vos> ¿qué partidos tenemos?
vos> ¿cómo ves River?
vos> ¿quién te parece que gana?
vos> ¿y el mercado de jugadores?
vos> proponeme algo
```

**Esto es lo que hay que hacer primero.** Si la voz no sirve, lo demás
no importa. Cuando algo no te guste, anotalo — se arregla en `voz.md`.

---

## Paso 4 — Telegram

```
python experto/bot.py
```

Buscá tu bot en Telegram por el usuario que le pusiste y mandale `/start`.
Ya podés hablarle desde el teléfono.

**La primera vez que le escribís, el bot se guarda tu chat.** Eso es lo
que después le permite escribirte solo.

---

## Paso 5 — El parte de la fecha

```
python experto/informe.py --ver
```

Con `--ver` lo imprime en pantalla sin mandarlo, para que lo leas antes.
Sin `--ver`, te llega a Telegram.

Para una fecha puntual: `python experto/informe.py 2026-09-06`

---

## Paso 6 — El vigilante

Es el que te escribe **sin que le preguntes** cuando cambia algo de una
apuesta que ya tenés puesta.

```
python experto/vigilante.py --ver
```

Solo mira partidos donde tenés plata puesta, y no repite un aviso dos
veces. Cuando ande, se pone a correr cada hora con el Programador de
tareas de Windows.

---

## Lo que hay que hacer cada vez

**`git pull` antes de usarlo.** El robot de GitHub baja los datos dos
veces por día, pero eso queda en GitHub — tu PC no se entera sola.

Si te olvidás, no te miente: las herramientas le avisan al asesor que los
datos son viejos y él te lo dice. Pero vas a estar mirando precios de
ayer.

---

## Si algo falla

| Qué ves | Qué pasa |
|---|---|
| `ModuleNotFoundError: google` | `pip install google-genai` |
| `No hay motor de IA` | No abriste una ventana nueva después del `setx` |
| `Falta TELEGRAM_BOT_TOKEN` | Lo mismo: ventana nueva |
| Error de autenticación | La clave está mal copiada. Sacá otra en aistudio.google.com/apikey |
| `429` o "quota" | Te pasaste de 10 pedidos por minuto. Esperá un minuto |
| No encuentra modelo | `python experto/motor.py` te lista los que tenés; fijá uno con `setx PRONOSTIC_MODELO "..."` |
| El bot no contesta en Telegram | ¿Está corriendo `python experto/bot.py`? Se corta si cerrás la ventana |
| Dice que los datos son viejos | `git pull` |
| "no tengo ese partido cargado" | El partido no está en `partidos.json` — o ya se jugó, o es de una liga que no seguimos |

---

## Qué le pasás a las otras herramientas

**`experto/PENDIENTE.md`** tiene el spec de lo que falta, con el orden.
Lo que queda es: `cierre.py` (el que te mide a vos), el goleador en
`mercado_extra.py`, y mudarlo a un servidor para que ande con la PC
apagada.

**Y una nota para el que siga:** el modelo vive **solo** en `motor.py`.
`datos.py` no tiene IA adentro, `voz.md` es texto, y `bot.py`,
`informe.py` y `vigilante.py` no saben con qué modelo hablan. Si mañana
aparece uno mejor o más barato, se cambia ahí y nada más.

**La regla de `CLAUDE.md` sigue en pie: una herramienta por área.**
Mientras alguien esté en `experto/`, que no entre otra.

Todo esto vive en la rama **`pronostic`**, no en `main`.
