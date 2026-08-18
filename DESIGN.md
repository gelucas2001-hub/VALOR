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
  gris: "#8C7F68"
  gris-2: "#6E6350"
  gris-3: "#5C513F"
  gris-prosa: "#7E7360"
  linea: "#241D16"
  linea-2: "#2A2318"
  linea-3: "#3A3122"
  linea-punteada: "#3A322580"
  neutro-medio: "#4A4030"
  mostaza: "#D6963A"
  mostaza-fondo: "#2E2210"
  mostaza-borde: "#4A3C1E"
  terracota: "#C06848"
  terracota-fondo: "#2B1912"
  terracota-borde: "#4A2E20"
  salvia: "#6B7A5E"
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

# Sistema de diseño VALOR

**Archivo en vivo:** `app.html`.
`index.html` es la versión anterior (línea gráfica descartada: negro frío,
cian, verde semáforo). Queda publicada hasta que `app.html` la reemplace;
no tomarla como referencia de diseño.

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
| Salvia | `#6B7A5E` | Decorativo. Solo el filete bajo el masthead. Sin trabajo funcional |

### Reglas duras

- **Nunca un tercer color funcional.**
- **Nunca semáforo** verde/amarillo/rojo.
- **Nunca mostaza para selección de UI.** El día activo del slider es
  tinta sobre fondo claro, no mostaza. Confundir "seleccionado" con "hay
  valor" es el error que más caro paga el usuario.
- La escala de grises tibios (`gris`, `gris-2`, `gris-3`) es jerarquía de
  texto, no significado.
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

## Chrome y densidad

- **Pestañas silenciosas:** línea inferior de 2px y cambio de color de
  texto. Nunca botón con caja ni relleno.
- **Filas planas** en listas largas. Nada de tarjeta dentro de tarjeta:
  un filete de 1px arriba de cada fila alcanza.
- **El bloque de análisis es tipografía sola, sin caja** — nota de
  revista, no tarjeta de dashboard.
- Grano y textura solo en el masthead, nunca sobre filas de datos.
- La curva acumulada del Registro es la **única línea curva de la app**.

## Navegación

Tres destinos: **Fecha · Registro · Método**. Combinadas y Ajustes no son
destinos — la combinada recomendada vive dentro de Pronósticos, y la banca
se pregunta inline en Herramientas la primera vez que hace falta.

## Fuente de verdad

`docs/superpowers/specs/2026-08-16-rediseno-desde-cero-design.md` manda
sobre este archivo en todo lo que sea producto, reglas de recomendación o
arquitectura de información. Acá vive solo la capa visual.
