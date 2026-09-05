# Cómo trabajar con Antigravity, de acá en adelante

**Hay dos tipos de sesión y no se mezclan nunca.** Un agente que edita
código y hace de asesor al mismo tiempo se confunde de rol: te contesta
sobre fútbol y de paso te toca un archivo, o al revés.

| | Para qué | Qué hacés ahí |
|---|---|---|
| **Sesión de USO** | Hablar de fútbol | Le preguntás por los partidos, le pedís informes, le pasás tus combinadas |
| **Sesión de OBRA** | Tocar código | Le pedís que construya o arregle algo de `experto/` |

## Lo primero, siempre, en cualquiera de las dos

```
git pull
```

El cron escribe los datos en `main` y vos trabajás en `pronostic`, así
que cuando quieras datos frescos: `git pull origin main`.

## Sesión de USO — el prompt

> Leé `GEMINI.md` y después `experto/SIN_CLAVE.md`. Vas a hacer de
> Pronóstic: leé `experto/voz.md` completo, son tus instrucciones. Los
> datos salen de correr `python experto/datos.py fecha` y
> `python experto/datos.py <id_partido>`, nunca de tu memoria. Arrancá
> diciéndome qué partidos hay para mañana.

Después le hablás normal.

## Sesión de OBRA — el prompt

> Leé `GEMINI.md` entero antes de nada. Estamos en la rama `pronostic`:
> no te vayas a `main` y no toques nada de lo que `GEMINI.md` marca como
> "quedó de lado". Corré `python experto/probar.py` antes de empezar.
> Lo que hay que hacer es: [lo que sea].

Y al final de esa sesión, pedile siempre:

> Commiteá lo que cambiaste y decime en una línea qué tocaste.

## Cuando algo de la voz no te guste

**Anotalo y arreglalo en una sesión de OBRA, no en la de uso.**

Si en medio de una charla le decís *"no me gusta cómo dijiste eso"*, se
va a corregir en ese momento y **el cambio se pierde al cerrar** —
`voz.md` no cambió. Lo que hacés es guardarte el ejemplo y después:

> En `experto/voz.md`, [el cambio]. Ejemplo de lo que hizo mal: "[pegás
> lo que te dijo]". No toques ningún otro archivo.

`voz.md` es texto. Corregirlo no es programar.

## Las tres cosas que no hay que hacer

- **Dos sesiones de obra a la vez** sobre `experto/`. Es lo que hizo
  perder trabajo tres veces en este proyecto.
- **Seguir usando una sesión vieja** después de que otra tocó los mismos
  archivos: trabaja sobre una foto vieja y pisa lo nuevo. Sesión nueva y
  `git pull`.
- **Pedirle cosas del producto anterior.** Si te propone tocar
  `index.html` o las skills de análisis, cortalo: eso quedó de lado y
  `GEMINI.md` lo dice.

---

# Cómo poner a andar Pronóstic

Todo lo que se podía dejar hecho está hecho. **Quedan dos cosas que solo
podés hacer vos**, porque son cuentas tuyas: sacar dos claves.

---

## Paso 1 — Las dos claves (10 minutos, una sola vez)

### La de Gemini — **gratis, sin tarjeta**

> ⚠️ **Tener Gemini Pro no alcanza, y no es lo mismo.** Google AI Pro y
> Ultra son suscripciones de **interfaz de chat** —gemini.google.com,
> Gmail, Docs, Antigravity— y **no incluyen acceso a la API**. La API se
> factura aparte.
>
> **Tener Pro tampoco te quita el nivel gratuito**: son cosas
> independientes. La clave de abajo la podés sacar igual, gratis, tengas
> la suscripción que tengas.
>
> (Si vivieras en Europa o el Reino Unido, Google obliga a activar
> facturación aunque uses modelos gratis. En Argentina no.)

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
git pull origin main
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

**Antes de usarlo, siempre esto:**

```
git pull origin main
```

**Ojo con el `origin main`, no alcanza `git pull` a secas.** El robot de
GitHub escribe los datos en la rama `main`, y vos estás trabajando en
`pronostic`: un `git pull` pelado te trae la rama tuya, que no cambió, y
te quedás con los precios de antes creyendo que actualizaste.

Si te olvidás, no te miente: las herramientas le avisan al asesor que los
datos son viejos y él te lo dice. Pero vas a estar mirando precios de
ayer.

---

## Si algo falla

**Primero corré esto**, que te dice si el problema es el código o es algo
que no configuraste todavía:

```
python experto/probar.py
```

No gasta ni un pedido de API. Si todo sale `OK` o `ojo`, el código está
bien y lo que falta es una clave.

| Qué ves | Qué pasa |
|---|---|
| `ModuleNotFoundError: google` | `pip install google-genai` |
| `No hay motor de IA` | No abriste una ventana nueva después del `setx` |
| `Falta TELEGRAM_BOT_TOKEN` | Lo mismo: ventana nueva |
| Error de autenticación | La clave está mal copiada. Sacá otra en aistudio.google.com/apikey |
| `429` o "quota" | Te pasaste de 10 pedidos por minuto. Esperá un minuto |
| No encuentra modelo | `python experto/motor.py` te lista los que tenés; fijá uno con `setx PRONOSTIC_MODELO "..."` |
| El bot no contesta en Telegram | ¿Está corriendo `python experto/bot.py`? Se corta si cerrás la ventana |
| Dice que los datos son viejos | `git pull origin main` — con `origin main`, no `git pull` a secas |
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
