---
name: VALOR
description: Pronosticador de fútbol argentino y sudamericano con motor de value betting abajo. Línea gráfica de prensa deportiva argentina vieja — tapas de El Gráfico, cupones de Prode, programas de cancha.
colors:
  fondo: "#1B1611"
  hueco: "#171310"
  panel: "#221C15"
  panel-activo: "#28211A"
  tinta: "#EEE3CE"
  tinta-2: "#D8CDB4"
  tinta-3: "#B8AD95"
  gris: "#AAA190"
  gris-2: "#9C9588"
  gris-3: "#918A7E"
  neutro: "#867F75"
  gris-prosa: "#978F7F"
  neutro-panel: "#8B857B"
  neutro-papel: "#5B564F"
  linea: "#241D16"
  linea-2: "#2A2318"
  linea-3: "#3A3122"
  linea-punteada: "#3A322580"
  neutro-medio: "#4A4030"
  mostaza: "#D6963A"
  mostaza-fondo: "#2E2210"
  mostaza-borde: "#4A3C1E"
  terracota: "#C27152"
  terracota-fondo: "#2B1912"
  terracota-borde: "#4A2E20"
  salvia: "#76846A"
  salvia-2: "#3A4A32"
typography:
  display:
    fontFamily: "'Anton', Impact, sans-serif"
    uso: "Nombres de equipo, títulos de liga, wordmark, encabezados de franja"
  mono:
    fontFamily: "'JetBrains Mono', ui-monospace, monospace"
    uso: "Todo número que se compare o se confíe, etiquetas de UI, pestañas"
  cuerpo:
    fontFamily: "'Archivo', system-ui, sans-serif"
    uso: "Prosa, análisis, nombres de mercado, texto de interfaz"
---

> ## ⚠️ Este documento describe el producto ANTERIOR
>
> Desde el **2026-09-05** la dirección es **Pronóstic**: un asesor
> conversacional que vive en `experto/`, rama `pronostic`. Lo de acá
> abajo —la PWA de `index.html`, el lenguaje de EV y Kelly, la promesa de
> "encontrar valor"— **quedó de lado**, y la última en concreto porque
> las mediciones del repo no la sostienen.
>
> **Empezá por `GEMINI.md`.** El diseño nuevo está en
> `docs/superpowers/specs/2026-09-05-pronostic-diseno.md`.
>
> Este archivo se conserva porque su historia y sus mediciones valen. No
> se toma como especificación de lo que se construye hoy.

> **Lo que SÍ sigue vigente de acá:** la paleta y la regla de un color un
> solo trabajo, si algún día Pronóstic tiene interfaz. Hoy vive en
> Telegram y no la usa.


# Sistema de diseño VALOR

**Archivo en vivo:** `index.html`.
Desde el 2026-08-18 es esta línea. La anterior (negro frío, cian, verde
semáforo) está descartada: si la ves en una captura vieja o en el historial
de git, no es referencia de diseño.

## Dirección

Prensa deportiva argentina vieja. Explícitamente **no**: crema + serif +
terracota ("vintage americano" genérico), negro + verde ácido, ni
negro + celeste + insignias + "PRO AI" (cliché de SaaS de IA).

## Un color, un solo trabajo — siempre

| Color | Hex | Trabajo, único |
|---|---|---|
| Fondo | `#1B1611` | Casi negro tibio, noche de cancha. No negro frío de terminal |
| Tinta | `#EEE3CE` | Texto, datos neutros, y **estado seleccionado** de cualquier control |
| Mostaza | `#D6963A` | **Valor**: acá hay algo mejor que el precio. Y nada más |
| Terracota | `#C06848` | **Alerta**: cuidado, esto no rinde. Y nada más |
| Salvia | `#6B7A5E` | **Voz secundaria**: filete bajo la cabecera, antetítulos, acciones al margen. Nunca dice estado |

### Resultado ≠ valor — resuelto (2026-08-18)

**El resultado de una apuesta no se pinta. Se dice con intensidad
tipográfica.** Ganada en tinta plena, perdida casi apagada — el mismo
recurso que ya usa Historial. Mostaza y terracota **no** entran acá.

Por qué: "valor" es una afirmación de *antes* del partido (el precio
está a favor); "ganada" es un hecho de *después* (esta apuesta pagó).
Una apuesta con valor real puede perder — es el punto entero de jugar
en probabilidad — y una sin valor puede ganar de pura suerte. Pintarlas
del mismo color las hace parecer la misma afirmación, y le enseña al
usuario que mostaza significa "salió bien". Ese es justo el sentido que
arruina la única señal que importa.

Elegido por Lucas sobre la alternativa de ampliar mostaza a
"valor o ganada", que era lo que traía el handoff de Claude Design.

| Elemento | Antes (handoff) | Ahora |
|---|---|---|
| Sello ganada | mostaza sobre `mostaza-fondo` | tinta plena sobre `hueco` |
| Sello perdida | terracota sobre `terracota-fondo` | `gris-3` sobre `hueco`, apagado |
| Devolución `+$` / `−$` | mostaza / terracota | `tinta-2` / `gris-2` |
| Neto y ROI del balance | mostaza / terracota | `tinta` / `gris-2` |
| Botones de corrección | mostaza / terracota | tinta / apagado |

**Las dos excepciones que sí siguen en mostaza**, porque no son el
resultado de una apuesta puntual: la **marca de valor** y la **curva
acumulada** del Registro.

### Mostaza vive en una sola capa (2026-09-01)

"Solo valor" no alcanza — importa también **dónde**. Desde que el
partido pasa a tres capas (Veredicto · Lectura · Datos, ver TRASPASO
§18), el dorado vive **solo en Veredicto**. Ningún dato crudo de
Lectura o Datos lo usa nunca, aunque describa algo favorable: un
número que el usuario está leyendo para entender el partido no es una
recomendación, y pintarlo de mostaza lo haría parecer una.

Es una regla más estricta que "mostaza = valor" a secas, y hasta esta
revisión vivía solo en TRASPASO/CLAUDE.md — quien mirara nada más que
este documento no tenía cómo saberlo.

### Salvia tiene tres trabajos, no cero (corregido 2026-08-18)

Este archivo decía «decorativo, solo el filete bajo el masthead, sin
trabajo funcional». El handoff aprobado dice «barra bajo cabecera,
**antetítulos, acciones secundarias**», y el prototipo lo hace así.
Manda el handoff: salvia es la **voz secundaria** de la interfaz.

Donde aparece, y en ningún otro lado:

- El filete de 3px bajo la cabecera, y el de 4px del troquelado.
- Antetítulos y contadores al margen (`6 CARGAS`, la línea de
  procedencia del Registro).
- Acciones al margen: `Corregir a mano`, `Volver al automático`.
  Fileteadas con `salvia-2` (`#3A4A32`), que es el mismo olivo apagado
  — un subrayado en salvia plena competiría con el texto.

**Lo que salvia nunca hace: decir estado.** No marca valor, no marca
alerta, no marca ganada ni perdida. Por eso puede tener tres trabajos
sin romper la regla de «un color, un solo trabajo»: esa regla rige los
colores que comunican estado, y salvia no es uno.

### Reglas duras

- **Nunca un tercer color funcional.**
- **Nunca semáforo** verde/amarillo/rojo.
- **Nunca mostaza para selección de UI.** El día activo del slider es
  tinta sobre fondo claro, no mostaza. Confundir "seleccionado" con "hay
  valor" es el error que más caro paga el usuario.
- La escala de grises tibios (`gris`, `gris-2`, `gris-3`, `neutro`) es
  jerarquía de texto, no significado.

### Tinta también tiene grados, según cuánto decide el control (2026-09-01)

"Tinta = seleccionado" no es un solo tono — son tres, y es a propósito:
más lleno cuanto más decide el control.

| Token | Cuándo | Ejemplos |
|---|---|---|
| `tinta` | Decide qué pantalla entera se muestra | Día del slider, Veredicto·Lectura·Datos, lado del plantel, filtro de Registro |
| `tinta-2` | Filtra o reordena dentro de una pantalla ya elegida | Local/visita en Equipos, orden en Jugadores, sub-tabla en Referencia, liga desplegada en la portada |
| `tinta-3` (`.suave`) | Filtro anidado dentro de un panel que ya está abierto | Club dentro de Datos · Jugadores |

Ninguno de los tres usa mostaza ni terracota — esa es la regla de
arriba ("Nunca mostaza para selección de UI"), esto es solo cuánto de
tinta.

### Los grises se aclararon (2026-08-24)

Medido contra el fondo `#1B1611`, la escala vieja no se leía:

| token | antes | contraste | ahora | contraste |
|---|---|---|---|---|
| `gris` | `#8C7F68` | 4.58 | `#AAA190` | **7.02** |
| `gris-2` | `#6E6350` | 3.05 | `#9C9588` | **6.04** |
| `gris-3` | `#5C513F` | 2.31 | `#918A7E` | **5.25** |
| `neutro` | `#4A4030` | **1.77** | `#867F75` | **4.54** |
| `salvia` | `#6B7A5E` | 3.91 | `#76846A` | **4.51** |
| `terracota` | `#C06848` | 4.54 | `#C06A4A` | **4.62** |

El mínimo para texto es 4.5:1. `neutro` estaba en 1.77 y rotulaba
talones y gráficos — era texto que prácticamente no existía.

**El escalonado se conservó a propósito**: 7.02 / 6.04 / 5.25 / 4.54
siguen siendo cuatro pasos distinguibles, así que la jerarquía no se
perdió. Cada tono se aclaró sobre su propio matiz, no se reemplazó.

**Y no contradice el "apagado" de una apuesta perdida.** Ese efecto lo
da la distancia contra `tinta` (14.12), que sigue siendo enorme: 5.25
contra 14.12 se lee callado igual. Lo que no se puede es que "callado"
signifique ilegible.

`gris-prosa` estaba escrito **a mano** (`color:#7E7360`) en tres reglas
de prosa, no como variable — por eso no aparecía al revisar `:root` y
casi se lo da por inexistente. Ahora es `--grisProsa` (`#978F7F`, 5.62) y
está acá. Un color suelto en el CSS es un color que nadie audita.

### El piso tipográfico es 11px (2026-08-24)

Había 151 nodos de texto por debajo de 11px — 7px el más chico — en
antetítulos, rótulos de dato y encabezados de tabla. Son texto
funcional: rotulan números que el usuario compara. Las 71 declaraciones
por debajo del piso subieron a 11px de una.

La densidad de cupón se mantiene con lo que ya la sostenía: versalitas,
`letter-spacing`, monoespaciada y la escala de grises. No con tamaños
que no se leen en un teléfono.
- En Historial el "color" viene de **intensidad tipográfica** — ganado en
  tinta plena, perdido casi apagado — nunca de mostaza ni terracota.

## Marca

**La V es la marca de VALOR — no el troquelado.** Elegida por Lucas en
la ronda de exploración de Claude Design (`Wordmark - tres
direcciones.dc.html`), sobre una entrega anterior donde el troquelado
había ganado. Esa decisión quedó superada por esta; si algún documento
viejo dice lo contrario, manda este.

SVG real, extraído del prototipo final (uso en portada, 45×45):

```html
<svg viewBox="0 0 100 100" style="height:45px;width:45px" aria-label="VALOR">
  <defs><clipPath id="vm-s"><polygon points="34,18 55,64 70,18"/></clipPath></defs>
  <polygon points="17,18 34,18 55,64 70,18 83,18 56,84 46,84" fill="#D8CDB4"/>
  <g clip-path="url(#vm-s)">
    <polygon points="42.5,38 47.1,38 36.65,70 32.05,70" fill="#5A6338"/>
    <polygon points="50.5,30 55.1,30 42.05,70 37.45,70" fill="#4E5730"/>
    <polygon points="57.8,24 62.4,24 47.45,70 42.85,70" fill="#616B3C"/>
    <polygon points="64.9,19 69.5,19 52.85,70 48.25,70" fill="#757F4E"/>
  </g>
  <line x1="27.5" y1="30.3" x2="44.3" y2="68.6" stroke="#171310" stroke-width="2"/>
</svg>
```

Una V tallada en tinta papel (`#D8CDB4`), con cuatro barras ascendentes
en verde oliva recortadas dentro del trazo derecho — la escalera de
riesgo, hecha símbolo. `id` de la máscara/clip único por instancia
cuando hay más de una V en la misma pantalla.

**Los cuatro verdes son un ramo tonal propio de la marca, no del
sistema funcional.** `#5A6338`, `#4E5730`, `#616B3C`, `#757F4E` no son
variantes de `salvia` (`#6B7A5E`) — son hex propios que solo existen
adentro de este SVG. La regla de "un color, un solo trabajo" rige los
colores *funcionales* de la interfaz (mostaza=valor, terracota=alerta);
no aplica acá porque las barras no comunican estado, son el dibujo.

**El troquelado no desapareció — cambió de trabajo.** Sigue siendo el
recurso para títulos de sección (`REGISTRO`, `MÉTODO`): la palabra
calada en una barra entintada, vía `<mask>`. Ya no es el wordmark
principal de la portada — eso es trabajo de la V.

## Recursos de la línea — construidos (2026-08-18)

Los cuatro que cargan la identidad. Están en `index.html`; si hacés una
pantalla nueva, se arma con estos, no con inventos nuevos.

| Recurso | Dónde | Qué es |
|---|---|---|
| **La V** | Portada (`marcaV()`) | 58px, centrada, con «VALOR» entre dos filetes debajo |
| **Troquelado** | Registro y Método (`troquel()`) | La palabra calada en barra beige + 3 perforaciones por lado + filete olivo de 4px |
| **Talón** | Tarjeta de partido | Riel de 52px con `Nº 01` / hora / `DE 03`, perforado vertical punteado, y pie perforado horizontal con `VALOR · PROGRAMA` |
| **Sello** | Tarjeta y análisis (`sello()`) | Veredicto en dos palabras, rotado −2,5°, doble filete interno |

**Sombra dura, siempre:** `box-shadow: 4px 4px 0 #13100B`, sin blur. La
tarjeta tiene margen derecho mayor que el izquierdo (20 contra 16) para
que la sombra tenga dónde caer.

**El grano va en la columna, no en las filas.** Tres `radial-gradient`
de medio píxel desfasados, tamaños `4px / 7px / 5px`:

```css
rgba(238,227,206,.05)   /* tinta, mota clara */
rgba(238,227,206,.035)  /* tinta, mota más tenue */
rgba(0,0,0,.06)         /* negro, mota oscura */
```

Las tarjetas son opacas y se apoyan encima, así que ningún dato se lee
sobre textura.

**El negro del grano es la única excepción a la paleta, y es
deliberada.** No es un color funcional: es sombra de textura al 6%, y
un token de la paleta no la da — `#13100B` sobre `#1B1611` no oscurece
igual que negro translúcido. Sale del handoff verificado, que la
especifica así («opacidades .05 / .035 beige y .06 negro»), y del
prototipo, que trae el mismo literal. Sin el grano la superficie se ve
digital y se pierde el registro de papel de programa de cancha.

**Bandas entintadas al revés** (papel beige, texto `#171310`) para
separar secciones: competición en portada, «ÚLTIMAS CARGADAS» en
Registro.

**La forma de los últimos cinco** usa intensidad, no color: ganado en
tinta plena, empate en neutro, perdido apagado.

## Chrome y densidad

- **Pestañas silenciosas — solo en `.nav` y `.subcapas`:** línea
  inferior de 2px y cambio de color de texto, nunca botón con caja ni
  relleno. Rige la barra de abajo (Fecha · Registro · Método) y la
  sub-navegación de Datos (Equipos · Jugadores · Referencia).
  **`.capas` (Veredicto · Lectura · Datos) no es una pestaña
  silenciosa, y no tiene por qué serlo:** decide qué capa entera del
  partido se muestra, no un matiz de la misma vista — fondo `panel` en
  reposo, `tinta` sobre `hueco` activa. Antes de citar "pestaña
  silenciosa" para descartar algo, fijarse cuál de las tres barras es
  la que está en pantalla.
- **Filas planas** en listas largas. Nada de tarjeta dentro de tarjeta:
  un filete de 1px arriba de cada fila alcanza.
- **El bloque de análisis es tipografía sola, sin caja** — nota de
  revista, no tarjeta de dashboard.
- Grano y textura solo en el masthead, nunca sobre filas de datos.
- La curva acumulada del Registro es la **única línea curva de la app**.

## Navegación

Tres destinos: **Fecha · Registro · Método**. Combinadas y Ajustes no son
destinos — la combinada recomendada vive dentro de Veredicto, y la banca
se pregunta inline en Herramientas la primera vez que hace falta.

Adentro de un partido, tres capas — **Veredicto · Lectura · Datos**
(2026-09-01, ver TRASPASO §18) — reemplazan lo que antes eran siete
pestañas. Veredicto es el único lugar con recomendación; Lectura es la
narrativa con el número que la sostiene al lado; Datos es exploración
libre, sin veredictos. Es la barra `.capas` de "Pestañas silenciosas"
arriba: fondo lleno, no subrayado.

Adentro de Datos, tres sub-destinos — **Equipos · Jugadores ·
Referencia** — sí son pestañas silenciosas como Fecha · Registro ·
Método.

## Pendiente

**`.jgrow.supl .mt` pinta de terracota "SUPLENTE" en Datos · Jugadores**
(§ Un color, un solo trabajo). No es una alerta de apuesta, es un dato
descriptivo — rompe "terracota: alerta, y nada más". Encontrado en la
auditoría del 2026-09-01. Es un cambio de código, no de este documento:
queda anotado para que Lucas elija el color correcto (probablemente de
la escala de grises) sin que el hallazgo se pierda.

## Fuente de verdad

`docs/superpowers/specs/2026-08-16-rediseno-desde-cero-design.md` manda
sobre este archivo en todo lo que sea producto, reglas de recomendación o
arquitectura de información. Acá vive solo la capa visual.
