# Handoff: VALOR — rediseño de app y registro automático

> **Corrección post-entrega (2026-08-18):** la sección "Wordmark" más
> abajo describe el troquelado como "la decisión final" del wordmark
> principal. **Eso quedó superado en una entrega posterior**: la marca
> final es una V (ver `DESIGN.md` en la raíz del repo, sección "Marca",
> con el SVG real). El troquelado no desapareció — pasó a ser el
> recurso para los títulos de sección (Registro, Método), no el
> wordmark de portada. El resto de este documento (motor, resolución
> automática, tokens, pantallas) sigue vigente y verificado.
>
> **Corrección 2 (2026-08-18):** la sección "Files" más abajo lista el
> contenido del zip original de Claude Design, no lo que efectivamente
> vive en esta carpeta. De los cinco archivos, acá quedaron tres:
> `VALOR.dc.html`, este `README.md`, y `Wordmark - tres direcciones.dc.html`
> (se sumó después, porque `DESIGN.md` la cita como fuente). **Los otros
> dos se dejaron afuera a propósito, no por error:**
> `support.js` porque el propio README de abajo pide no llevarlo al
> repo, y `Portada - direcciones.dc.html` (260 KB) porque es puro
> registro histórico de direcciones descartadas — el mismo README dice
> "no las implementes". `data/partidos.json` del bundle tampoco hace
> falta: el repo ya tiene su propio `data/partidos.json`, más
> actualizado.

## Overview

VALOR es una app de pronósticos de fútbol que ya existe en el repo
`gelucas2001-hub/VALOR` (branch `main`): un motor Python (`actualizar.py`,
Dixon-Coles) que escribe `data/partidos.json`, y una interfaz `app.html`.

Este paquete contiene el **rediseño completo de la interfaz** y **una
funcionalidad nueva que el repo todavía no tiene**: la resolución automática
del registro de apuestas. El motor no se tocó: la app consume exactamente el
mismo contrato de datos.

Lo que hay que implementar en el repo, en orden de valor:

1. **Resolución automática del registro** (§ Registro automático). Es lógica
   nueva, con reglas y casos borde ya probados contra datos reales. Es la
   parte que cambia qué *significa* la app: hoy `app.html` guarda pronósticos
   que nadie comprueba.
2. **El rediseño visual** de las cuatro vistas (§ Pantallas).

## About the Design Files

Los archivos de este bundle son **referencias de diseño escritas en HTML** —
prototipos que muestran el aspecto y el comportamiento buscados, no código de
producción para copiar y pegar.

`VALOR.dc.html` usa un runtime propio de prototipado (`support.js`: plantilla
con huecos `{{ }}` + una clase de lógica). **No lleves ese runtime al repo.**
La tarea es recrear estos diseños en el entorno del repo — `app.html` es un
único archivo con JS vainilla que renderiza por concatenación de strings, y
ese patrón alcanza perfectamente.

Lo que **sí** se transplanta tal cual, porque es JS común y ya está probado:

- Las funciones del motor copiadas del repo (`pois`, `tau`, `matrix`,
  `sumIf`, `ev`, `kelly`, `devig`, `mercados`) — están idénticas, sirven de
  referencia cruzada.
- `TESTS`, `norm`, `hoyISO`, `buscarResultado`, `resolver` — **estas son
  nuevas y son el corazón del handoff.** Copialas literalmente.

## Fidelity

**Alta fidelidad (hifi).** Colores, tipografías, espaciados y estados son
finales y fueron elegidos por el usuario a lo largo de ocho rondas de
exploración. Recreá la UI con precisión. Los archivos de exploración
(`Portada - direcciones.dc.html`, `Wordmark - tres direcciones.dc.html`)
quedan como registro de las direcciones descartadas: no las implementes.

---

## Registro automático (funcionalidad nueva)

### El problema

Cuando VALOR analiza un partido, el partido todavía no se jugó: el marcador
final no existe en `data/partidos.json`. Por eso el registro del repo pide que
el usuario marque a mano si acertó — y un registro que depende de la
disciplina del usuario no se llena nunca. Sin eso, la app mide opiniones, no
aciertos.

### La solución

El marcador aparece igual, un refresco después, por una puerta lateral: cada
partido de `data/partidos.json` trae los últimos cinco de cada equipo en
`formH` / `formA`, y cada entrada tiene rival, localía y marcador:

```json
{"r":"L","rival":"Independiente Rivadavia","local":false,"marcador":"1-2"}
```

`marcador` está **en la perspectiva del dueño del historial**: acá el dueño
hizo 1 y el rival 2. `local` dice si el dueño jugó de local.

Entonces: el resultado de lo que el usuario anotó aparece en el historial de
cualquiera de los dos equipos, la próxima vez que alguno vuelva a jugar. Se
cruza por ahí.

### Algoritmo

```js
const norm = s => (s||"").toLowerCase().normalize("NFD")
  .replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]/g,"");

function hoyISO(){
  const d = new Date(), z = n => String(n).padStart(2,"0");
  return d.getFullYear()+"-"+z(d.getMonth()+1)+"-"+z(d.getDate());
}

function buscarResultado(H, A, matches, desde){
  let mejor = null;
  const mirar = (dueno, forma) => {
    (forma||[]).forEach((f,k)=>{
      if(!f || !f.marcador) return;
      const [a,b] = String(f.marcador).split("-").map(Number);
      if(!isFinite(a) || !isFinite(b)) return;
      let i, j, fuente;
      if(norm(dueno)===norm(H) && norm(f.rival)===norm(A) && f.local===true){ i=a; j=b; fuente=H; }
      else if(norm(dueno)===norm(A) && norm(f.rival)===norm(H) && f.local===false){ i=b; j=a; fuente=A; }
      else return;
      if(!mejor || k < mejor.k) mejor = {i, j, k, fuente};   // k=0 es el más reciente
    });
  };
  (matches||[]).forEach(m=>{
    if(desde && m.date && m.date <= desde) return;           // candado 1
    mirar(m.home, m.formH); mirar(m.away, m.formA);
  });
  return mejor;
}

function resolver(b, matches, hoy){
  if(b.manual) return {estado:b.estado, auto:false, res:null, esperando:false};
  const H = b.home || (b.partido||"").split(" vs ")[0];
  const A = b.away || (b.partido||"").split(" vs ")[1];
  const enGrilla = (matches||[]).some(m=> m.id===b.matchId && m.date >= hoy);
  if(enGrilla) return {estado:"pendiente", auto:true, res:null, esperando:false};  // candado 2
  const res = buscarResultado(H, A, matches, b.fecha);
  const test = TESTS[(b.key||"").split("__")[1]];
  if(res && test) return {estado: test(res.i,res.j) ? "ganada" : "perdida", auto:true, res, esperando:false};
  return {estado:"pendiente", auto:true, res:null, esperando: !!(b.fecha && b.fecha < hoy)};
}
```

`TESTS` es el mapa de criterios de cobro, a nivel de módulo:

```js
const TESTS = {
  "1x2_l":(i,j)=>i>j, "1x2_e":(i,j)=>i===j, "1x2_v":(i,j)=>i<j,
  "dc_lx":(i,j)=>i>=j, "dc_x2":(i,j)=>i<=j, "dc_12":(i,j)=>i!==j,
  "btts_si":(i,j)=>i>0&&j>0, "btts_no":(i,j)=>i===0||j===0,
};
[1.5,2.5,3.5].forEach(n=>{ TESTS["ov"+n]=(i,j)=>i+j>n; TESTS["un"+n]=(i,j)=>i+j<n; });
```

**Regla de diseño importante:** `mercados()` consume el mismo `TESTS` para
calcular la probabilidad previa (`sumIf(M, TESTS[id])`). El criterio que
promete el cobro y el que lo verifica tienen que ser **el mismo objeto**. Si
se duplican, tarde o temprano divergen y la app miente en una de las dos
puntas.

### Los dos candados (no los saques)

Sin ellos el cruce da falsos positivos:

1. **Solo historiales posteriores** (`m.date > b.fecha`). Un historial cargado
   antes de nuestro partido no puede contenerlo — pero sí puede contener el
   cruce *anterior* entre los mismos dos equipos.
2. **Si el partido sigue en la grilla con fecha ≥ hoy, no se jugó.** Devuelve
   pendiente sin mirar marcadores.

Medido contra los 30 partidos reales de `data/partidos.json` (2026-08-17 en
adelante): **sin candados, 3 de 30 se resolvían con el partido equivocado** —
Cerro Porteño vs Palmeiras aparece tres veces en los historiales de la fase de
grupos de Libertadores. **Con candados, 0 falsos positivos de 30**, y el caso
pasado (Independiente Rivadavia 2-1 Estudiantes de Río Cuarto) cruza bien y
orientado.

### Estados resultantes

| Estado | Cuándo | Qué muestra |
|---|---|---|
| `ganada` / `perdida` | hay marcador cruzado y `TESTS[id]` decide | sello ámbar/terracota, marcador, devolución, «Cruzado con el historial de X» |
| `pendiente` (sin jugar) | el partido sigue en grilla, fecha ≥ hoy | sello apagado «SIN JUGAR», «Se juega el MAR 18. Se resuelve solo.» |
| `pendiente` + `esperando` | ya se jugó pero el marcador no apareció | sello «SIN RESULTADO», invita a cargarlo, muestra los tres botones |
| manual | el usuario corrigió | «Lo marcaste vos. No lo tocamos.» + «Volver al automático» |

### Reglas de producto que sostienen esto

- **El estado guardado no manda.** Se resuelve en cada render contra los datos
  frescos. Lo único que se persiste como verdad es la corrección manual
  (`manual: true`).
- **La corrección a mano siempre está disponible** y queda declarada: el cruce
  por nombre de rival es frágil y el usuario tiene que poder desautorizarlo.
  El conteo de corregidas a mano se muestra arriba, junto a las cruzadas.
- **Nada entra solo al registro.** El cruce resuelve, no anota. Si el usuario
  no jugó la apuesta, no existe — un registro lleno de lo que «hubiéramos»
  jugado no sirve para medirse.
- El resumen de procedencia va arriba de la lista, en mono 9px olivo:
  `2 resueltas con el resultado · 1 esperando resultado · 1 corregida a mano`.

### Limitación conocida, declarada en pantalla

Si ninguno de los dos equipos vuelve a jugar dentro de la ventana de
`data/partidos.json`, el resultado no aparece nunca y la carga queda en
«SIN RESULTADO» esperando la corrección manual. Es aceptable en ligas
regulares, y la copia lo dice sin disimular. **La mejora natural, si el motor
puede darla:** que `actualizar.py` persista los marcadores finales de los
partidos que ya publicó, en un `data/resultados.json` con
`{matchId: "2-1"}`. Eso vuelve el cruce exacto y hace innecesarios los dos
candados. Si tomás ese camino, dejá el cruce por historial como respaldo.

---

## Modelo de datos del registro

Cada carga anotada (`log` en `localStorage`, clave `valor.log`):

```js
{
  key: "espn401841498__ov2.5",     // matchId + "__" + id de mercado
  partido: "Estudiantes de Río Cuarto vs Atlético Tucumán",
  home: "Estudiantes de Río Cuarto",   // necesarios para el cruce
  away: "Atlético Tucumán",
  mercado: "Más de 2.5 goles",
  comp: "Liga Profesional Argentina",
  cuota: 2.10,          // la que cargó el usuario
  p: 0.512,             // probabilidad del modelo al momento de anotar
  ev: 0.075,            // EV congelado al momento de anotar
  stake: 1200,          // Kelly fraccionado, topeado al 4% de la banca
  estado: "pendiente",  // solo manda si manual === true
  manual: false,
  fecha: "2026-08-17",  // fecha del partido
  matchId: "espn401841498"
}
```

`p`, `ev` y `cuota` se **congelan al anotar**: son el precio y la creencia de
ese momento. Recalcularlos después con datos nuevos borraría la evidencia.

Métricas derivadas, todas sobre estados **resueltos**, no guardados:

- `invertido` = Σ stake de las cerradas (ganadas + perdidas)
- `neto` = Σ (ganada ? stake × (cuota − 1) : −stake)
- `ROI` = neto / invertido
- `acierto` = ganadas / cerradas
- curva acumulada: polyline de 300×56, un punto por cerrada, `stroke #D6963A`,
  `stroke-width 2`, `vector-effect: non-scaling-stroke`. Es la única línea
  curva de toda la app.

## Constantes del motor (copiadas del repo — no las cambies)

```js
MIN_EV = 0.04        // umbral de ventaja para jugar
MAX_ODDS = 4.5       // arriba de esto el acierto es demasiado raro para medirlo
EV_ABSURDO = 0.25    // ventaja así de grande = el modelo falla, no el precio
VENTAJA_MIN = 0.02, VALOR_MIN = 0.06, VALOR_MAX = 0.12, ALERTA_MIN = 0.10
umbral = p => (1 + MIN_EV) / p     // cuota mínima que conviene
kelly  = (p,o) => max(0, (p*(o-1) - (1-p)) / (o-1))
```

Fracción de Kelly según confianza del modelo: `conf ≥ 72 → 0.25`,
`≥ 60 → 0.125`, `≥ 50 → 0.0625`, resto `0.005`. Stake topeado al **4% de la
banca** siempre.

Franjas de la escalera de riesgo: `0.68–0.93` (lo más probable),
`0.45–0.68` (intermedia), `0.12–0.45` (arriesgada).

---

## Design Tokens

### Colores

| Token | Hex | Uso |
|---|---|---|
| Fondo del documento | `#13100B` | body, fuera de la columna |
| Papel | `#1B1611` | columna principal, con grano |
| Tinta | `#171310` | cabeceras, barras entintadas, fondo de botón inactivo |
| Tinta profunda | `#1D1811` | sello apagado |
| Tarjeta | `#221C15` | fondo de tarjetas y cajas de cifras |
| Borde tarjeta | `#2A2318` | divisores internos, bordes de botón |
| Divisor tenue | `#241D16` | líneas de separación |
| Sombra dura | `#13100B` | `box-shadow: 4px 4px 0` — sin blur, siempre |
| Beige papel | `#D8CDB4` | texto principal, wordmark troquelado, bandas |
| Beige claro | `#EEE3CE` | títulos Anton, cifras destacadas, chip activo |
| Beige medio | `#B8AD95` | cifras secundarias |
| Gris cálido | `#8C7F68` | texto de apoyo |
| Gris apagado | `#6E6350` | rótulos, texto terciario |
| Gris mínimo | `#4A4030` | rótulos de gráfico, estados vacíos |
| Ámbar | `#D6963A` | ventaja, ganada, curva acumulada |
| Terracota | `#C06848` | alerta, perdida, EV absurdo |
| Olivo | `#6B7A5E` | barra bajo cabecera, antetítulos, acciones secundarias |
| Ámbar fondo | `#2E2210` | fondo de fila con ventaja / sello ganada |
| Terracota fondo | `#2B1912` | fondo de sello perdida |
| Bordes de estado | `#4A3C1E` (ámbar), `#4A2E20` (terracota), `#3A3122` (neutro) | |

**Máximo dos fondos por pantalla.** El grano es obligatorio en la columna:
tres `radial-gradient` de 0.5px superpuestos (4px/7px/5px), opacidades
`.05` / `.035` beige y `.06` negro. Sin el grano el diseño se ve digital y
pierde el registro de papel de programa de cancha.

### Tipografía

- **Anton** (Google Fonts) — títulos, sellos, wordmark, capitulares. Siempre
  `text-transform: uppercase` salvo en títulos de párrafo. `letter-spacing`
  entre `-1.5` (wordmark) y `.05em` (sellos chicos).
- **JetBrains Mono** 400/500/600/700 — todas las cifras, rótulos, chips,
  metadatos. `letter-spacing` `.06em`–`.16em` en rótulos en mayúscula.
- **Archivo** 400/500/600/700 — texto corrido y nombres de equipo.

Escala usada: rótulos 7.5–9px, metadatos 9.5–11px, texto corrido 12.5–13.5px
(`line-height` 1.6–1.7), cifras 13–15px, títulos Anton 15–22px, capitular
44px, wordmark 38–40px de alto.

**Sin border-radius en ninguna parte.** Todo esquina viva.

### Movimiento

```css
@keyframes sube    { from{opacity:0;transform:translateY(7px)} to{opacity:1;transform:none} }
@keyframes desliza { from{opacity:0;transform:translateX(10px)} to{opacity:1;transform:none} }
@keyframes selló   { from{opacity:0;transform:scale(1.14) rotate(-2.5deg)} to{opacity:1;transform:scale(1) rotate(-2.5deg)} }
@keyframes late    { 0%,100%{opacity:.28} 50%{opacity:.6} }
```

Cambio de vista: `desliza .22s cubic-bezier(.22,1,.36,1)`. El sello entra con
`selló` y queda con rotación `-2.5deg` permanente. Respetá
`prefers-reduced-motion: reduce` anulando todo.

---

## Pantallas

Columna única, `max-width: 520px`, centrada, `padding-bottom: 64px` por la
barra de navegación fija. Es una app de teléfono; todo objetivo táctil ≥ 44px.

### 1. Fecha (portada)

**Propósito:** elegir el partido del día.

- **Cabecera** `#171310`, `padding: 18px 16px 14px`, con barra olivo de 3px al
  pie. Wordmark troquelado a la izquierda (§ Wordmark), a la derecha fecha en
  mono 10px `.1em` mayúscula + bajada en `#6B7A5E`.
- **Tira de días:** botones de igual ancho, número en Anton 17px y día en mono
  8px. Activo: fondo `#D8CDB4`, texto `#171310`.
- **Tira de competiciones:** chips con escudo 14px + nombre mono 10px, scroll
  horizontal sin barra. Activo en beige.
- **Banda de competición:** fondo `#D8CDB4`, texto `#171310` en Anton 15px
  mayúscula, con la cuenta de partidos en mono a la derecha.
- **Tarjeta de partido:** `#221C15` con `box-shadow: 4px 4px 0 #13100B`.
  Riel izquierdo con `N° 01`, hora en mono 15px y `01 04`. Cuerpo: escudo
  18px + nombre por equipo, tira de forma de los últimos cinco a la derecha,
  fila de tres cuotas (rótulo mono 7.5px + cuota mono 20px + probabilidad),
  lectura en una frase, y **sello** rotado `-2.5deg` con el veredicto en dos
  palabras. Pie perforado: fila de puntos de 2px + `VALOR · PROGRAMA` y el
  contador.
- **Navegación fija** al pie: `FECHA / REGISTRO / MÉTODO`, mono 10px `.1em`,
  activo en beige con raya de 2px arriba.

### 2. Detalle de partido

Seis pestañas: `Análisis / Historial / Posiciones / Plantel / Herramientas`
más el resumen. Marco con talón numerado y perforado; antetítulos olivo en
mono 9px `.16em`; sello del veredicto arriba a la derecha.

Estados vacíos honestos, no disimulados: `data/analisis.json` no trae análisis
cualitativo y el contrato no tiene jugadores. Las pantallas lo declaran en
lugar de rellenar. **Mantené esa decisión.**

### 3. Registro

- Cabecera con wordmark «REGISTRO» troquelado, kicker con la cuenta de cargas.
- **Fila de cuatro cifras** en `#221C15`: Resultado / Acierto / ROI /
  Cerradas, mono 15px 600, divididas por `1px #2A2318`. `opacity: .5` cuando
  el registro está vacío.
- **Línea de procedencia** (nueva) en mono 9px olivo, con la raya que se
  extiende: de dónde viene cada estado.
- **Curva acumulada** en SVG 300×56 sobre `#171310`, con `ACUMULADO` y el
  neto en los extremos.
- **Chips de filtro** con conteo: Todas / Ganadas / Perdidas / Pendientes.
- **Banda «ÚLTIMAS CARGADAS»** beige + lista de tarjetas. Cada tarjeta:
  partido y stake, mercado, meta (`liga · @cuota · EV`), **sello de estado +
  marcador + devolución**, línea de procedencia, y el enlace
  `Corregir a mano` / `Volver al automático`. Los tres botones
  Ganada/Perdida/Pendiente aparecen solo cuando hay algo que corregir.
- **Vacío:** título Anton 22px, párrafo con capitular, y la promesa de que se
  resuelve solo. Cierra con `SIN MOVIMIENTOS` entre dos rayas.

### 4. Método

Explica el modelo sin letra chica: capitular, Poisson bivariado ajustado por
antigüedad, la regla graduada del Brier con los valores medidos
(0,667 / 0,645 / 0,623) y el margen medido de las casas (7,7%).

## Wordmark

Troquelado: la palabra **calada** en una barra entintada, no dibujada. SVG con
`<mask>`: rect blanco del tamaño de la barra, texto en Anton negro encima
(así perfora), más tres círculos negros de `r=1.7` en cada borde vertical
(las perforaciones del talón). El rect visible se pinta `#D8CDB4` con la
máscara aplicada, y abajo lleva una barra olivo de 4px.

```html
<svg viewBox="0 0 150 50" style="height:40px">
  <defs><mask id="tq">
    <rect x="0" y="0" width="150" height="46" fill="#fff"/>
    <text x="75" y="36" text-anchor="middle" font-family="Anton" font-size="34"
          letter-spacing="-1.5" fill="#000">VALOR</text>
    <circle cx="6" cy="12" r="1.7" fill="#000"/><!-- ×3 por lado -->
  </mask></defs>
  <rect width="150" height="46" fill="#D8CDB4" mask="url(#tq)"/>
  <rect y="46" width="150" height="4" fill="#6B7A5E"/>
</svg>
```

El mismo patrón, con otro `viewBox` y otra palabra, titula REGISTRO y MÉTODO.
Cada máscara necesita un `id` único por instancia.

**Se descartaron explícitamente** letras dibujadas a mano y variantes
tipográficas custom (dos rondas). El troquelado es la decisión final.

## Estado

En `localStorage`, prefijo `valor.`:

- `banca` (número o null) — se pide una vez, en Herramientas
- `cuotas` (`{key: número}`) — las cuotas cargadas por el usuario
- `log` (array) — el registro (§ Modelo de datos)

Estado efímero en memoria: `vista`, `dia`, `matchId`, `tab`, `filtro`,
`corrigiendo`, `cuotasTxt`, `bancaTxt`.

**Detalle no obvio, ya resuelto:** el input de cuota guarda **lo que el
usuario tipea** (`cuotasTxt`), separado del número parseado (`cuotas`). Si
solo se guardara el número, escribir «1.30» moriría en el primer «1» — que no
supera el umbral y borra la clave. Reproducí esa separación.

## Assets

- Escudos de equipos y logos de liga: URLs de ESPN que ya vienen en
  `data/partidos.json` (`homeLogo`, `awayLogo`, `compLogo`). Los escudos de
  rivales en Historial se resuelven por nombre contra los equipos presentes en
  el archivo. Todo `<img>` de escudo lleva un `onError` que lo esconde.
- Tipografías: Google Fonts (Anton, Archivo, JetBrains Mono).
- No hay assets binarios en este bundle.

## Files

| Archivo | Qué es |
|---|---|
| `VALOR.dc.html` | La app completa: portada, detalle con 6 pestañas, Registro, Método. Referencia principal. |
| `support.js` | Runtime del prototipo. **No lo lleves al repo.** Solo permite abrir el HTML. |
| `data/partidos.json` | Datos reales del motor (30 partidos, 2026-08-17 en adelante). Sirve para probar el cruce de resultados. |
| `Portada - direcciones.dc.html` | Las rondas de exploración de portada, incluidas las descartadas. Registro histórico. |
| `Wordmark - tres direcciones.dc.html` | Las tres direcciones de wordmark; ganó el troquelado. Registro histórico. |

Abrí `VALOR.dc.html` en el navegador para verlo funcionando con datos reales.

## Cómo probar la resolución automática

En la consola, sobre datos reales: un partido pasado entre dos equipos que
vuelven a jugar tiene que cruzar orientado, y **ningún** partido de la grilla
actual debe cruzar.

```js
buscarResultado("Independiente Rivadavia","Estudiantes de Río Cuarto", matches, "2026-08-10")
// → {i:2, j:1, k:0, fuente:"Estudiantes de Río Cuarto"}

matches.filter(m => buscarResultado(m.home, m.away, matches, m.date)).length
// → 0   (sin el candado de fecha: 3)
```

Ese segundo chequeo es el test de regresión que importa. Si alguna vez da
distinto de 0, el cruce está resolviendo partidos que no se jugaron.
