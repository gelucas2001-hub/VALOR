# PRONÓSTIC — la carta del asesor

*Diseño acordado el 2026-09-05. Reemplaza la dirección de producto de
`PRODUCT.md` sin tocar el motor ni el pipeline.*

---

## 0. Por qué existe este documento

VALOR construyó un motor serio y un producto que no orienta. El
diagnóstico, con evidencia del propio repo, está en §1. La decisión de
producto está en §2. **Lo que hace que este documento sirva es §4: la
lista explícita de los 22 campos que el asesor tiene que cumplir.**
Contra esa lista se puede decir "esto no lo hace" — que es justamente lo
que no se podía decir antes.

Regla de uso: **si algo de este documento se contradice con
`PRODUCT.md`, gana este.** Si se contradice con una medición del
`TRASPASO`, gana la medición.

---

## 1. El diagnóstico, con los números

### 1.1 Por qué la app no orienta

De los 32 análisis cargados entre el 1 y el 4 de septiembre de 2026,
**29 tienen `inclinacion: null`**. Los otros 3 son `E`. Cero `L`, cero
`V`. Como `inclinacion` es la llave obligatoria de `marcaDeValor()`, la
app no marcó nada en ninguno de los 32.

No es un bug. Es el principio K de
`.claude/skills/valor-analisis-inclinacion/SKILL.md`, línea 133:

> "Si el modelo ya lo sabe, no es motivo para inclinar — es `null`. (…)
> El modelo ve goles, resultados, forma, local/visitante, y la fuerza de
> cada equipo. Si tu razón cae ahí, no alcanza."

O sea: **la capa de análisis tiene prohibido concluir a partir de forma,
tabla, localía o fuerza de los equipos** — que es el 90% de lo que hace
legible un partido de fútbol.

El caso que lo muestra entero, veredicto textual de Estudiantes de Río
Cuarto–Sarmiento del 4/9:

> "Sarmiento llega mucho mejor y con un ataque que funciona contra un
> local que no convierte en su cancha, **pero todo eso está en la tabla
> y en la forma, que es lo que ya se ve sin analizar nada** (…) la
> lectura no agrega una dirección propia."

El análisis describe un partido desparejo, se da cuenta, y se niega a
concluirlo porque la conclusión es obvia.

**La causa raíz:** un solo campo hace dos trabajos incompatibles. Es el
**instrumento de medición** (evidencia ortogonal a λ, para poder medir
si la capa cualitativa aporta) y es la **opinión del producto**. La
regla que lo hace bueno como instrumento es la que lo hace mudo como
producto. §40 del `TRASPASO` llega al mismo lugar desde el otro lado y
deja la pregunta abierta.

### 1.2 Por qué "buscar valor" no puede ser la promesa

| Medición | Resultado |
|---|---|
| ROI walk-forward, 5 ligas (§37) | arg −6.96% · bra −4.99% · eng +2.21% · fra −3.04% · spa −6.95% — ninguno significativo |
| `barrido_valor.py` | 39 ventanas de umbral, **ninguna positiva fuera de muestra** |
| `medir_apertura.py` | CLV contra Bet365 = cero. Contra Pinnacle en eng: **−1.62% ±0.82** |
| `medir_metamodelo.py` | **Nuestro desacuerdo con el mercado no tiene contenido informativo a ninguna magnitud** |
| `medir_bandas.py` | Bandas 4-10: −7.38% ±2.82 en test |
| `medir_props.py` | **+1.15 pp de CLV ±0.38 (3 e.e.)** — la única señal medida del proyecto |
| `medir_margen_props.py` | Bet365 cobra **+9.0 pp** de sobreprecio en esa misma escalera |

Verificado además el 2026-09-05 sobre los dos partidos del 4/9: en las
**ocho líneas de gol** de Bet365, el mercado está por encima de nuestro
número **en todas**. Sistemáticamente.

**Conclusión:** un producto cuya promesa sea "te encuentro apuestas con
ventaja" está obligado a decir "hoy no hay nada" casi todos los días, y
eso es exactamente la experiencia que hay que arreglar.

---

## 2. La decisión de producto

**Pronóstic es un asesor de fútbol y apuestas con el que se conversa.**

Tres decisiones tomadas explícitamente por Lucas el 2026-09-05:

1. **Arma boleta siempre, con la etiqueta puesta.** No espera a tener
   ventaja demostrada. Dice qué jugaría, a qué precio, cuánto, y qué la
   rompe — y dice con todas las letras cuándo no le está ganando al
   mercado. *La honestidad va en la etiqueta, no en el silencio.*
2. **Las dos superficies.** Da la jugada **y** audita las ideas de
   Lucas. No son dos productos: son dos puertas al mismo cerebro.
3. **Cobertura completa.** Mercados populares **y** de estadística:
   1X2, doble oportunidad, DNB, más/menos, ambos marcan, córners
   (total y por equipo), tarjetas, faltas, remates y jugadores. No se
   achica a un nicho.

### La separación que arregla el problema de §1.1

| Campo | Qué es | Se muestra |
|---|---|---|
| `inclinacion` | **Sin cambios.** Ortogonal a λ, `null` por defecto, alimenta `medir_analisis.py` y `marcaDeValor()`. Es el experimento | **Nunca** como "la opinión" |
| `lectura` (nueva) | Lo que el asesor realmente piensa. Usa todo: forma, tabla, localía, fuerza, contexto, bajas, λ. **Siempre tiene dirección y confianza. Nunca `null`** | Es lo que el usuario lee |

Coincidir con el modelo no es pecado: **es confirmación, y confirmar es
información.** El instrumento conserva su pureza; el producto recupera
la voz. No invalida ninguna medición del repo.

### La superficie

**Un bot de Telegram.** Lucas escribe desde el teléfono. No hay app que
abrir. El pipeline (`actualizar.py`, `mercado_extra.py`, `foto_props.py`)
**no se toca**: sigue siendo la materia prima.

---

## 3. La licencia — qué puede afirmar

**Regla dura: toda afirmación tiene que trazar a una fila "SÍ".** Sale de
las mediciones del repo, no de opiniones.

| Capacidad | ¿La tiene? | Evidencia |
|---|---|---|
| Goles esperados calibrados | **SÍ** | Calibrado agrupado por nuestra p (§29) |
| Precio justo del mercado | **SÍ** | Shin sobre 11.854 partidos (`medir_devig.py`) |
| Cuánto cobra la casa por mercado | **SÍ** | Márgenes medidos; props +9.0 pp |
| Ancla por equipo en córners / remates / al arco | **SÍ** | +4.8% / +9.9% / +7.3% (`medir_dominio.py`) |
| Ancla en **faltas** | **NO** | −0.199 ±0.072 — empeora |
| Lectura cualitativa de contexto | **SÍ** | Las dos skills; no invalidado |
| Distinguir equipos en estadísticas con 4 partidos | **PARCIAL** | Solo posesión y tackles pasan el ruido |
| Elegir props mejor que la deriva | **SÍ** | +1.15 pp ±0.38 — con 9 pp de margen en contra |
| **Ganarle al precio de cierre** | **NO** | 5 ligas en ruido; 39 ventanas sin una positiva |
| **Saber cuándo se equivoca vs. el mercado** | **NO** | Ninguna variable supera al placebo (§30) |
| Córners **por equipo** contra plata | **NO** | Atraso +0.0205 ±0.0093; ROI negativo en los 6 umbrales |
| Efecto del árbitro | **No concluyente** | 54 partidos |
| Bajas → goles | **NO** | r = −0.06 ± 0.14 |
| Ajustar el número de un jugador por rival | **NO** | −0.1317 ±0.0476 — empeora |

### La banda de confianza

Dos ejes **separados**, porque fusionarlos es lo que produce puré:

- **Qué tan legible es el partido.** Sale de cuán desparejo es y cuántos
  goles se esperan. *Corrección del 2026-09-05: la variable llamada
  `volatilidad` en `medir_metamodelo.py:201` calcula
  `abs(p_local − p_visitante)` — o sea desbalance, no varianza; el
  diccionario de la línea 149 la documenta mal. La correlación −0.245 es
  real pero es en buena parte una propiedad de la escala, no un
  hallazgo.*
- **Cuánta información tenemos.** ¿Hay alineación? ¿Cuántos partidos de
  muestra? ¿Está cargado el análisis? ¿La cuota es real o modelada? ¿De
  cuándo es?

Cuatro bandas nombradas, nunca decimales: `lectura firme` ·
`lectura razonable` · `lectura frágil` · `no puedo leer este partido`.

**"No puedo leer este partido" ≠ "el partido está parejo".** Un 50-50
legible es una lectura firme.

---

## 4. LOS 22 CAMPOS

**Esta es la lista contra la que se audita.** Un campo sin cumplir es un
hueco del producto, no una opinión.

### Antes del partido — saber

| # | Campo | Estado | De dónde sale |
|---|---|---|---|
| 1 | Qué se juega hoy y qué merece atención | ✅ | `partidos.json` |
| 2 | Cómo llega cada equipo: forma, tabla, qué se juega | ✅ | `partidos.json`, `expediente.py` |
| 3 | Bajas, suspendidos y alineación probable — **y declararlo cuando no se sabe** | ⚠️ parcial | `planteles.json` → clave `once` (es el once ANTERIOR). El resto pide búsqueda web |
| 4 | Técnico, sistema, cambios recientes | ⚠️ | `once.esquema` + búsqueda web |
| 5 | Contexto fuera de los números: copa entre semana, viaje, altura, clima, clásico | ⚠️ | `analisis.json` + búsqueda web |
| 6 | Historial entre ellos | ✅ | `h2h` |
| 7 | Árbitro | ✅ con reserva | Se nombra; **no se le atribuye efecto** (medido) |

### El mercado

| # | Campo | Estado | De dónde sale |
|---|---|---|---|
| 8 | Precio de todos los mercados, populares y de estadística | ✅ | `mercadoExtra` (Bet365) + `mercado` (DraftKings) |
| 9 | **Movimiento de la línea**: abrió en X, está en Y | ❌ **falta** | `cuotas.json` (123 partidos con hora) y `props_jugadores.json` (12.221 líneas). **Los datos existen, nadie los mira** |
| 10 | Cuánto cobra la casa en cada mercado | ✅ | Cálculo sobre las cuotas |
| 11 | Dónde conviene jugarlo | ⚠️ | Solo dos casas hoy |

### La decisión

| # | Campo | Estado |
|---|---|---|
| 12 | Posición clara sobre el partido, con el porqué | ✅ |
| 13 | **Qué jugar, a qué precio mínimo, CUÁNTO, y qué la rompe** | ❌ **falta el cuánto.** Kelly está en `index.html:1569`, sin usar acá |
| 14 | Qué **no** jugar, y por qué | ✅ |
| 15 | **Trabajar con las ideas de Lucas**, no solo emitir las propias | ❌ **falta.** Es su queja original: leía y terminaba apostando a lo suyo |
| 16 | **La fecha como cartera**: correlación, exposición, la pata que hunde | ❌ **falta.** Seis unders en seis partidos es una apuesta, no seis |

### Después

| # | Campo | Estado |
|---|---|---|
| 17 | Cómo salió, y si fue mala apuesta o mala suerte | ❌ falta. `resultados.json` ya se resuelve solo |
| 18 | **Dónde acierta Lucas** — medirlo a él, no solo al modelo | ❌ falta. 30+ scripts miden el modelo; cero lo miden a él |

### Cómo se comporta

| # | Campo | Estado |
|---|---|---|
| 19 | **Escribe sin que le pregunten** cuando algo cambia | ❌ falta. `foto_props.py` ya corre cada hora de 07:00 a 21:00 — el disparador existe |
| 20 | **Se acuerda de Lucas**: qué apostó, cuánto tiene, qué le gusta, qué venían hablando | ❌ falta |
| 21 | Habla en criollo, toma posición, no se esconde en adverbios | ✅ por `voz.md` |
| 22 | Dice que no, y dice cuándo no sabe | ✅ por `voz.md` |

**Diez de veintidós no estaban en el primer diseño.** La lista existe
para que la próxima falta se vea antes de construir, no después.

---

## 5. Prohibiciones

1. Nunca decir "hay valor" fuera de props, y ahí con la salvedad de los
   9 pp de margen.
2. Nunca una **cifra de remates** como pronóstico — la métrica se desvía
   2.09 veces el ruido (`medir_jugadores.py`).
3. Nunca atribuirle un efecto al **árbitro**.
4. Nunca recomendar **córners por equipo** aunque el número dé — medido
   peor que la casa.
5. Nunca inventar una **alineación**, ni presentar la probable como
   confirmada.
6. Nunca citar un **precio sin decir de cuándo es**.
7. **Nunca callarse porque la conclusión es obvia.** Es la prohibición
   que arregla §1.1.
8. Nunca proponer una jugada sin las **cuatro cosas**: qué, a qué
   precio, cuánto, y qué la rompe.

---

## 6. Arquitectura

### La frontera, que es la decisión técnica central

> **Los DATOS salen de las herramientas. El RAZONAMIENTO es propio.**

El modelo nunca escribe una cuota, una probabilidad ni una serie de
memoria: las pide. Y tampoco **rehace la cuenta** — si la herramienta
dice 47, no escribe "casi 50", no promedia y no combina dos números para
sacar un tercero; para eso están `stake` y `revisar_boleta`.

Eso elimina la generación de cifras sin fuente. **No elimina el error de
interpretación**: el asesor puede leer mal un dato correcto, y por eso
siempre dice en qué se apoya.

La regla **no** lo convierte en un lector de JSON: sabe de fútbol y tiene
que usarlo. Pero la línea es específica, y sin ella "juicio propio" se
convierte en inventar contexto:

| Puede decirlo solo | Necesita herramienta o `buscar` |
|---|---|
| "Tres partidos en ocho días desgastan" | "River jugó tres en ocho días" |
| "Un equipo que se para atrás te obliga a rematar de afuera" | "Riestra se para atrás" |
| "Hay técnicos que se meten atrás sobre el final" | "Este DT cambió a 5-3-2 en los últimos tres" |
| "Perder al nueve baja la producción" | "Fulano está lesionado" |

**El conocimiento general orienta el razonamiento. Toda afirmación de
hecho sobre ESTE partido sale de una herramienta o de una búsqueda.**

### Los siete archivos

Todo en `experto/`. **Sin dependencias**: la API de Claude y la de
Telegram se llaman con `urllib`, igual que `mercado_extra.py`.

| Archivo | Qué hace |
|---|---|
| `datos.py` | Las herramientas sobre los JSON que ya existen. Sin LLM, testeable |
| `voz.md` | El prompt del asesor — esta carta hecha instrucciones |
| `bot.py` | Telegram ↔ Claude con uso de herramientas, **más búsqueda web** |
| `informe.py` | El parte de la fecha, empujado solo |
| `vigilante.py` | Corre cada hora: salió el once, se movió el precio, se rompió la jugada → **escribe sin que le pregunten** |
| `memoria.json` | Qué apostó, cuánta banca tiene, qué le gusta, qué venían hablando |
| `cierre.py` | Cómo salió, y dónde acierta Lucas |

### Las herramientas de `datos.py`

```
partidos_del_dia(fecha)          fixture, hora, competición, y qué mirar
datos_partido(id)                λ, probabilidades, Bet365, márgenes, frescura
jugadores_partido(id)            escaleras + serie por jugador + once anterior
movimiento(id, mercado)          abrió en X, está en Y, cuándo se movió
historial(equipo)                forma, h2h, tabla, local/visita
revisar_boleta([...])            probabilidad conjunta, pata frágil, margen total
banca()                          saldo, expuesto esta semana, racha
registro(filtro)                 qué apostó, cómo le fue, dónde acierta
stake(p, cuota)                  Kelly fraccional, tope 4% (index.html:1569)
buscar(consulta)                 búsqueda web: lesiones, técnico, clima, noticias
```

### Correcciones de una línea, fuera de `experto/`

- **El goleador.** `mercado_extra.py:159` baja solo remates, al arco y
  faltas. El comentario del propio archivo dice que en arg.1 hay un
  bloque `"Player To Score or Assist"` sin usar. Agregarlo al dict
  `JUGADOR`.
- **El stake.** Kelly ya existe en `index.html:1569`; se porta a
  `datos.py` sin reescribirlo.

### Qué NO se toca

`actualizar.py`, el motor Dixon-Coles, `data/*.json` escritos por el
cron, y las reglas duras de `CLAUDE.md`. Pronóstic **lee**; no cambia el
contrato de `partidos.json`.

---

## 7. El idioma

**Si una palabra no la usaría un tipo en el bar, no va.** Nada de λ,
"cuota justa", "desviggeado", "probabilidad conjunta", "valor esperado",
"Kelly", "Dixon-Coles".

| En vez de | Se dice |
|---|---|
| "λ total 2.35" | "espero unos 2 goles y medio" |
| "p = 47.3%, justa 2.11" | "lo gana 47 de cada 100 veces" |
| "el mercado desviggeado da 54.9%" | "la casa lo tiene en 55 de cada 100" |
| "EV negativo" | "a ese precio estás pagando de más" |
| "stake Kelly 2.1%" | "poné dos de cada cien pesos de tu banca" |

### La regla de tono, que es el corazón

> **Prohibido el condicional que esconde la posición.**

La regla es sobre esconderse, no sobre palabras: *"podría", "en
principio", "aunque también", "no se puede descartar", "habría que ver"*
son el síntoma casi siempre, y cuando aparece una hay que ver qué se
está evitando decir. **Sí van los condicionales que nombran una
condición concreta** — *"si no arranca Fernández, esto no va"* — porque
esos no esconden nada; y describir un partido abierto cuando el partido
es abierto tampoco es evasiva.

La duda estructural va en la banda de confianza y en **qué cambiaría mi
lectura**. **La prosa afirma.**

Es lo que permite ser firme y honesto en la misma frase — y lo contrario
exacto del veredicto real de §1.1, donde la duda se comió la conclusión.

### Predicción ≠ apuesta

La distinción fundacional del proyecto (§1 del `TRASPASO`), y ahora una
regla con nombre en `voz.md`. *"Gana River"* sale de la lectura; *"a 1.40
no lo juego"* sale del precio. **Las dos conviven y siempre se dicen
juntas.** La predicción manda sobre *qué* se compra; el precio manda
sobre *si* se compra — nunca al revés, que es el error de "creemos que
gana River pero jugá a Racing a 5.75".

### Boleta siempre ≠ apuesta siempre

**Siempre hay posición sobre el partido. No siempre hay apuesta.**
*"Mi lectura es River; a 1.55 no lo compro; si baja a 1.70, sí"* es una
respuesta terminada. Lo que no existe nunca es quedarse sin decir qué se
piensa.

### La memoria describe a Lucas, no al fútbol

*"A Lucas le gustan los unders"* es un hecho sobre Lucas. **No es
evidencia de que el under sea buena apuesta.** `memoria.json` se usa para
aconsejarlo mejor a él —y para frenarlo cuando viene perdiendo—, jamás
como argumento futbolístico. El campo `quien` existe para poder medir por
separado lo que propone el asesor y lo que propone él.

---

## 8. Cómo se cierra lo que falta

**No con otra auditoría.** Este documento encontró 10 huecos en dos
pasadas, lo que prueba que auditar desde la silla no converge. Lo que
cierra es **una fecha real**: Lucas usa el bot en la fecha 8 de la Liga
Profesional, y cada vez que queda con ganas de algo que el asesor no
hizo, **eso es un campo 23**.

Orden de construcción, por costo de equivocarse:

1. `voz.md` y esta carta — no se delegan
2. `datos.py` con tests — el esqueleto seguro
3. `bot.py` mínimo, corriendo en la PC de Lucas — para poder probarlo
4. `vigilante.py`, `memoria.json`, `cierre.py` — con spec, delegables
5. Mudarlo a un servidor

**Una herramienta por área** (`CLAUDE.md`): mientras Claude Code está en
`experto/`, nadie más entra ahí.

### Lo que necesita Lucas

- `ANTHROPIC_API_KEY` — console.anthropic.com
- `TELEGRAM_BOT_TOKEN` — `@BotFather`, `/newbot`

Las dos por variable de entorno, nunca en el repo, igual que
`ODDS_API_KEY`.

---

## 9. Lo que este diseño NO promete

No crea ventaja sobre el mercado. En 1X2 y goles el ROI esperado sigue
siendo el margen de la casa en contra. Lo que cambia es que Lucas deja
de perder por desorientación y por pagar de más, y que el producto lo
acompaña de verdad.

El único hilo con señal medida son los props (+1.15 pp de CLV) contra un
margen de 9 pp. **No está resuelto.** La primera medición que falta:
ese 9% es el promedio de la escalera de titulares, **no el de las líneas
que efectivamente elegiríamos**. Nadie preguntó eso todavía.
