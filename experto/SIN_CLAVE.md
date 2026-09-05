# Pronóstic sin ninguna clave

Con Antigravity, OpenCode o Hermes ya podés usar el asesor **hoy, sin
sacar ninguna clave y sin gastar un peso**. No tenés el teléfono ni los
avisos automáticos, pero tenés el asesor.

La idea es simple: esas herramientas ya son un modelo con acceso a tu
carpeta. Lo único que les falta es **quién ser** (`voz.md`) y **los datos**
(`datos.py`). Las dos cosas están acá.

---

## Cómo se usa

Abrí Antigravity, OpenCode o Hermes **en la carpeta VALOR** y pegale esto:

> Leé `experto/voz.md` completo: son tus instrucciones, sos vos.
>
> Los datos salen de correr comandos, nunca de tu memoria:
> - `python experto/datos.py fecha` — qué se juega
> - `python experto/datos.py <id_partido>` — el expediente completo de un
>   partido: nuestros números, los precios de Bet365, la comisión, la
>   forma, los cruces anteriores, las escaleras de remates con la serie
>   de cada jugador, el movimiento de la línea y el once anterior
> - `python experto/datos.py banca` — mi banca y lo que tengo abierto
>
> Corré lo que necesites y contestame como dice `voz.md`. Arrancá
> diciéndome qué partidos hay.

A partir de ahí le hablás normal: *"¿cómo ves River?"*, *"¿quién gana?"*,
*"¿el mercado de jugadores?"*, *"proponeme algo"*.

**Las reglas de `voz.md` valen igual**: no inventa cifras, toma posición,
te dice qué jugar con precio y monto, y te avisa cuando no hay nada.

---

## Qué perdés y qué no

| | Con clave de Gemini | Sin ninguna clave |
|---|---|---|
| Conversar con el asesor | ✅ | ✅ |
| Los mismos datos y las mismas reglas | ✅ | ✅ |
| Desde el teléfono | ✅ | ❌ desde la compu |
| El parte que llega solo a la mañana | ✅ | ❌ se lo pedís |
| **Que te escriba cuando salió el once o se movió el precio** | ✅ | ❌ |
| Que anote tus apuestas | ✅ | ⚠️ pedíselo explícito |

**Lo único que se pierde de verdad es que te escriba sin que preguntes**
—el vigilante—, porque para eso hace falta un programa corriendo solo.
Todo lo demás lo tenés.

---

## Anotar una apuesta en este modo

El agente puede llamar a las mismas funciones:

```
python -c "import sys;sys.path.insert(0,'experto');import datos as D;print(D.poner_banca(100000))"
python -c "import sys;sys.path.insert(0,'experto');import datos as D;print(D.anotar('espn401841546','Fernández más de 2.5 remates',2.10,3000,'pronostic'))"
```

Se guarda en `experto/memoria.json`, que es el mismo que usa el bot. **Lo
que anotes acá lo ve el bot cuando lo enchufes, y al revés.**

---

## Cuál conviene

**Empezá por acá**, y hay un motivo mejor que "es gratis".

Lucas tiene **Gemini Pro**, y esa suscripción **no da acceso a la API**
—es de interfaz de chat, no de programas—, pero **sí funciona dentro de
Antigravity**. Google puso `gemini-3.8-flash` en Antigravity desde el
día que salió.

O sea: **en este modo estás usando el modelo bueno, ya pago, sin sacar
ninguna clave.** El bot con la clave gratuita va a correr con un Flash
del nivel gratuito, que es menos.

Así que para la única pregunta que importa hoy —**si la voz suena a
experto**— este modo no es el plan B: es el mejor banco de pruebas que
hay. Si acá convence, sacás la clave gratis y ganás el teléfono, el
parte de la mañana y el vigilante. Si no convence, arreglás `voz.md` sin
haber sacado nada.

---

## Y para lo otro que sí sirven

Antigravity, OpenCode y Hermes son **quienes siguen construyendo esto**.
`experto/PENDIENTE.md` está escrito para ellos: dice qué falta, en qué
orden y qué no tocar. Eso es su trabajo principal — el modo de arriba es
un rendimiento extra mientras tanto.

**Una herramienta por área** (`CLAUDE.md`): que no entren dos a la vez a
`experto/`.
