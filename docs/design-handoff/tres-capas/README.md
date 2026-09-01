> **Estado (2026-09-01): implementado.** Este bundle es la entrega de
> Claude Design que originó las tres capas de `index.html`. Se conserva
> como referencia y **no se edita**. Dos cosas se resolvieron distinto
> de lo que dice acá, y el motivo está en TRASPASO §18: el filtro de
> localía arranca en "Este cruce" (cada equipo en su rol de hoy) en vez
> de un promedio general, y la pestaña Herramientas —que el handoff no
> menciona— vive adentro de Veredicto. Los nombres de campo del JSON
> mandan sobre los del handoff: la titularidad sale de
> `serie.tit`/`serie.pj`, no de un campo `arranca`.

# Handoff: VALOR — arquitectura de tres capas

## Overview

Rediseño integral de la navegación y la jerarquía de información de VALOR (pronosticador de fútbol con motor de value betting, uso personal).

El problema que resuelve: hoy cada partido se abre en siete pestañas (Análisis · Pronósticos · Estadísticas · Historial · Posiciones · Plantel · Registro) cortadas por **origen del dato**, no por intención del usuario. De ahí salen cuatro defectos:

1. **Dos pestañas recomiendan.** Pronósticos recomienda resultado y goles; Estadísticas recomienda córners, tarjetas y candidatos de jugador. Mientras existan dos lugares que recomiendan, el contenido se superpone siempre — es un error de corte, no de criterio.
2. **La afirmación y su evidencia viven separadas.** El análisis dice "la defensa está rota" y el número que lo sostiene está tres pestañas más allá.
3. **Historial, Posiciones y Plantel** tienen el mismo peso de navegación que las recomendaciones, aplanando la jerarquía.
4. **De los jugadores solo se ven los candidatos.** `planteles.json` trae 18 por equipo con serie de remates, al arco, faltas, amarillas, goles y asistencias; la interfaz muestra un puñado.

La solución son **tres capas por intención**, más dos destinos de producto en la barra inferior:

| Capa | Rol | Absorbe |
|---|---|---|
| **VEREDICTO** | El único lugar del producto donde aparece una recomendación | Pronósticos + Quién mirar + candidatos de Estadísticas |
| **LECTURA** | La narrativa con la evidencia incrustada al lado de cada frase | Análisis + Contexto; consume Historial y Posiciones como evidencia inline |
| **DATOS** | Exploración libre, sin veredictos y sin dorado | Estadísticas (crudas) + Plantel + Historial y Posiciones completos |

Barra inferior: **Fecha · Registro · Método**. Registro y Método no pertenecen a ningún partido — son del producto — y quedar fuera del flujo de "buscar algo para apostar" es deliberado: es lo que impide que la app se lea como una máquina de picks.

## About the Design Files

Los archivos de este bundle son **referencias de diseño hechas en HTML**: prototipos que muestran aspecto y comportamiento pretendidos, **no código de producción para copiar**. El markup usa estilos inline y una estructura de "canvas de opciones" que existe solo para presentar variantes en revisión — nada de eso va al producto.

La tarea es **recrear estas pantallas en el entorno existente de VALOR**.

### Entorno real de destino (importante)

VALOR **no** es una app con framework. Es:

- Un único **`index.html`** escrito a mano, con CSS y JavaScript vanilla embebidos, servido estático.
- Un pipeline **Python** (`actualizar.py` y compañía) que produce `data/*.json`, que el HTML lee y renderiza.

Consecuencias para quien implemente:

- **No introducir React/Vue/build step.** Seguir el patrón del `index.html` actual: CSS en el `<style>` del documento con clases, JS vanilla, render por template strings o DOM API según ya se haga ahí.
- **El diseño de este bundle usa estilos inline; el `index.html` real usa clases CSS.** Traducir: cada patrón repetido de este handoff (talón, renglón de partido, barra produce/concede, fila de tabla, bloque de advertencia) debe volverse una clase reutilizable, no estilos inline duplicados.
- **La matemática está duplicada a propósito** entre Python y el JS de `index.html`, y hay tests (`doble_via.py`, `test_medir_lineas.py`) que verifican que no se separen. **Este rediseño no toca ni una línea del motor.** Es reorganización de presentación: si un cambio de UI obliga a tocar `probMayor()`, `TESTS` o los umbrales, pará y consultá.
- Los nombres de campo del JSON (`produce`, `concede`, `arranca`, `fiabilidad_medida`, etc.) son la fuente; el diseño se adapta a ellos, no al revés.

## Fidelity

**Alta fidelidad (hifi).** Colores, tipografías, tamaños, pesos, espaciados y estados finales. Recrear pixel-perfect con las clases del `index.html`.

Dos excepciones donde el diseño es intencionalmente indicativo:

- Los **acordeones** están dibujados con uno abierto y el resto cerrado. El comportamiento (uno a la vez o varios) queda a criterio; el cerrado y el abierto están especificados.
- Las **listas truncadas** ("Ver los 36 · 28 más ›", "cuatro equipos más") muestran el patrón, no el contenido completo.

## Screens / Views

Diez pantallas, todas en `VALOR - Rediseño.dc.html`, turno 5 (`#5a` … `#5j`). Todas las de app son **390 px de ancho** (móvil); `5a` es un diagrama de 1040 px de contenido, solo documentación.

---

### 5a — Mapa de arquitectura (documento, no pantalla)

Diagrama de 1040 px que enfrenta las siete pestañas de hoy contra las tres capas y marca qué se fusiona. **No se implementa.** Sirve como referencia de la decisión.

---

### 5b — VEREDICTO (con oportunidad)

**Propósito:** el usuario ve, en un solo lugar, todo lo apostable de este partido, ordenado por valor.

**Layout, de arriba a abajo:**

1. **Cabecera de partido** — `background:#171310`, `padding:13px 16px 12px`, flex con `gap:10px`. Flecha `←` (JetBrains Mono 16px, `#AAA190`), y bloque de dos líneas: nombre del cruce (Anton 14px/1.1, `#EEE3CE`) y `Liga · Nº 06` (JetBrains Mono 11px, `#918A7E`, `letter-spacing:.06em`).
2. **Conmutador de capas** — tres pestañas iguales (`flex:1`), `padding:9px 0`, `gap:4px`, `text-align:center`, JetBrains Mono 11px, `letter-spacing:.08em`, mayúsculas. Activa: fondo `#EEE3CE`, texto `#171310`. Inactivas: fondo `#221C15`, texto `#AAA190`. El contenedor cierra con `border-bottom:3px solid #76846A`.
3. **Sello de sección** — franja `#D8CDB4`, `padding:6px 11px 7px`, `box-shadow:4px 4px 0 #13100B`. Título "VEREDICTO" (Anton 15px, `#171310`, mayúsculas, `letter-spacing:.03em`) y contador a la derecha (JetBrains Mono 700 11px, `#5B564F`, `letter-spacing:.1em`): **"01 DE 06 MERCADOS"**.
4. **Tarjeta de oportunidad** — la única pieza con dorado en todo el partido. `background:#2E2210`, `border-left:2px solid #D6963A`, `padding:13px 13px 14px`, sombra `4px 4px 0 #13100B`.
   - Etiqueta "OPORTUNIDAD DETECTADA" (JetBrains Mono 11px, `#D6963A`, `letter-spacing:.1em`) + familia de mercado a la derecha ("CÓRNERS", `#867F75`).
   - Titular del mercado: Anton 20px/1.15, `#EEE3CE`.
   - Tesis: Archivo 12.5px/1.6, `#D8CDB4`, con los números en `#EEE3CE` peso 600.
   - Tres celdas `gap:1px`, cada una `background:#171310`, `padding:9px 10px`: **CUOTA MÍNIMA** (valor en `#D6963A`), **STAKE** (`#D8CDB4`), **MUESTRA** (`#9C9588`). Rótulos JetBrains Mono 10.5px `#918A7E`; valores JetBrains Mono 600 16px.
   - Pie con `border-top:1px solid #4A3C1E`: "De dónde sale" → enlace **"DATOS · CÓRNERS ›"** en `#D6963A`.
5. **Separador de sección** — rótulo "LO DEMÁS QUE MIRAMOS" (JetBrains Mono 11px, `#8B857B`, `letter-spacing:.12em`) + línea punteada `repeating-linear-gradient(90deg,#3A3122 0 3px,transparent 3px 7px)`.
6. **Escalera de mercados restantes** — filas `background:#221C15`, `padding:11px 12px`, `gap:1px` entre filas. Cada fila: nombre (Anton 15px/1.1, `#D8CDB4`), subtítulo con el motivo (JetBrains Mono 11px/1.5, `#918A7E`), estado a la derecha (JetBrains Mono 10.5px, `#8B857B`, mayúsculas) y `+` de despliegue (`#4A4030`).
   - Estados posibles: **SIN VENTAJA** · **SIN PRECIO** · **SIN DATO** · **NO OPINAMOS**.
   - Variante de riesgo: `background:#2B1912`, `border-left:2px solid #C27152`, título en `#EEE3CE` y motivo en `#C27152`, sin etiqueta de estado.
   - Variante de señal baja: `opacity:.62`, textos a `#9C9588` / `#867F75`.
7. **Pie de talón** — línea punteada + dos rótulos enfrentados (JetBrains Mono 11px, `#8B857B`, `letter-spacing:.12em`): "CERRADO 31/08/26" · "VEREDICTO 01 DE 03".
8. **Ingreso a la capa siguiente** — bloque `#221C15` con sombra: "SIGUE" / "POR QUÉ LO DECIMOS" (Anton 16px) y `›`.
9. **Barra inferior** — ver *Componentes compartidos*.

**Regla dura:** el dorado (`#D6963A`, `#2E2210`, `#4A3C1E`) aparece **solo** en esta capa. Ningún dato crudo lo usa nunca.

---

### 5h — VEREDICTO sin oportunidades

**Propósito:** el estado más frecuente. Un partido puede no tener nada apostable y la pantalla tiene que verse completa, no vacía ni rota.

Idéntica a 5b salvo:

- Contador del sello: **"00 DE 06 MERCADOS"**.
- En lugar de la tarjeta dorada, un bloque centrado `#221C15`, `padding:16px 14px 17px`, `text-align:center`: "NO HAY NADA ACÁ" (Anton 22px/1.15, mayúsculas) + "Seis mercados mirados, ninguno con precio a favor." (Archivo 12.5px/1.6, `#B8AD95`).
- Los seis mercados van todos en la escalera, cada uno con su estado y su motivo.
- Ingreso al final: "IGUAL SE PUEDE LEER / EL PARTIDO" → Lectura.

**Esta pantalla es requisito, no cortesía.** El ROI medido es −3.27% ± 6.19: el intervalo cruza el cero, y prometer valor donde no hay ventaja medida va contra el principio del producto. Implementar el vacío antes que el caso con oportunidad.

---

### 5c — LECTURA

**Propósito:** entender el partido. Cada afirmación viene con el número que la sostiene **en el mismo bloque**, no a un clic.

**Layout:**

1. Cabecera + conmutador (Lectura activa).
2. **Tesis del partido** — bloque `#221C15`, `padding:14px 13px 15px`: titular Anton 19px/1.18 (`#EEE3CE`, `text-wrap:pretty`) + una línea de encuadre en Archivo 12.5px/1.6 (`#B8AD95`).
3. **Bloques numerados de argumento** — `gap:11px` entre bloques, cada uno `#221C15`, `padding:14px 13px 13px`:
   - Rótulo "01 · DOMINIO" (JetBrains Mono 11px, `#918A7E`, `letter-spacing:.1em`, mayúsculas).
   - Párrafo Archivo 13px/1.62 (`#D8CDB4`), números embebidos en `#EEE3CE` peso 600.
   - **Evidencia**, en caja `#171310`, `padding:10px 11px 11px`, con la forma que corresponda:
     - *Comparativa de métrica*: fila de valores (dos `<b>` de `flex:0 0 40px`, JetBrains Mono 600 13px, el mayor en `#EEE3CE` y el menor en `#9C9588`) con el nombre de la métrica centrado (JetBrains Mono 10.5px, `#918A7E`, `letter-spacing:.1em`, mayúsculas), y debajo dos barras `height:6px`, `gap:3px`, con `flex` proporcional al valor — la mayor en `#EEE3CE` pleno, la menor en `rgba(238,227,206,.24)`.
     - *Renglón de tabla*: dos filas `padding:9px 11px` con puesto (JetBrains Mono 600 12px), nombre (Archivo 12px), puntos y zona. Solo los dos equipos del partido.
     - *H2H*: cuatro celdas `flex:1`, `gap:1px`, `background:#171310`, `padding:9px 6px`, centradas: resultado (JetBrains Mono 600 13px, `#D8CDB4`) + fecha (10px, `#8B857B`).
   - Pie de evidencia opcional con `border-top:1px solid #2A2318`: nota de fiabilidad o enlace a la capa correspondiente (`VEREDICTO ›` en `#D6963A`).
4. **Bloques de advertencia** — `background:#2B1912`, `border-left:2px solid #C27152`, `padding:12px 13px`. Rótulo JetBrains Mono 700 11px `#C27152` mayúsculas + párrafo Archivo 12.5px/1.6 `#D8CDB4`. Dos casos obligatorios cuando aplican:
   - **"EL MOTOR NO DICE LO MISMO"** — cuando el modelo y la lectura discrepan. La contradicción se muestra, no se esconde, y baja la confianza de todo lo que dependa del resultado.
   - **"OJO CON LA MUESTRA"** — cuando el split se apoya en pocos partidos, o cuando no hay partes médicos.
5. Pie de talón ("ESCRITO 31/08/26" · "LECTURA 02 DE 03") + barra inferior.

---

### 5d — DATOS · Equipos

**Propósito:** explorar el cruce sin que nadie recomiende nada.

**Layout:**

1. Cabecera + conmutador (Datos activa) + **sub-conmutador** de tres exploradores: Equipos · Jugadores · Referencia. Pestaña activa: texto `#EEE3CE` con `border-bottom:2px solid #EEE3CE` y `padding-bottom:5px`; inactivas `#8B857B`. El contenedor lleva el `border-bottom:3px solid #76846A`.
2. Sello "EQUIPOS" + contador "09 MÉTRICAS · 5 PJ".
3. **Filtro de localía** — tres segmentos `flex:1`, `gap:1px`, `padding:8px 0`, JetBrains Mono 10.5px mayúsculas: Todo / Local / Visita. Activo `#D8CDB4` sobre texto `#171310`; inactivos `#221C15` sobre `#AAA190`.
4. **Acordeón de nueve métricas** — `gap:1px`, cada ítem `background:#221C15`.
   - **Cabecera de métrica:** `padding:12px 12px 11px`, flex `gap:9px`. Nombre (Anton 15px, `#EEE3CE`, mayúsculas), **marcador de señal** (JetBrains Mono 10px, `letter-spacing:.08em`) y `+` / `−`.
   - **Marcador de señal** — atributo permanente del número, no disclaimer al pie:
     - `SEÑAL ALTA` → `#EEE3CE` (posesión, tackles)
     - `SEÑAL MEDIA` → `#B8AD95` (córners, faltas, tarjetas)
     - `SEÑAL BAJA · 2.09×` → `#867F75`, y toda la fila a `opacity:.7` con el nombre en `#9C9588` (remates, remates al arco)
     - `SIN MEDIR` → `#867F75`, misma atenuación (atajadas, offsides)
   - **Cuerpo abierto:** `padding:0 12px 13px`. Dos pares de barras — **PRODUCE** y **CONCEDE** — con la misma mecánica que la comparativa de 5c. Pie con `border-top` y los dos nombres de equipo enfrentados (JetBrains Mono 10.5px, `#8B857B`).
5. **Enlace a Método** — fila `#221C15` con sombra, `padding:11px 12px`: "Qué es la señal medida" + "MÉTODO ›".
6. Pie ("ESPN · 5 PJ" · "DATOS 03 DE 03") + barra inferior.

**Las dos reglas de esta capa:**

- **La unidad es el cruce, no el promedio.** Cada métrica se muestra siempre en el par produce / concede: `concede` está medido en las nueve y hoy no se muestra, así que se está viendo la mitad del dato. La pregunta del mercado de estadísticas es casi siempre sobre el cruce.
- **Tinta plena = número más alto, no número mejor.** La barra rellena indica magnitud, no ventaja. No hay semáforo.

---

### 5e — DATOS · Jugadores

**Propósito:** que el usuario arme sus propios candidatos. Todos los jugadores, no solo los que VALOR destaca.

**Layout:**

1. Cabecera + conmutador + sub-conmutador (Jugadores activo).
2. Sello "JUGADORES" + contador "36 EN PLANTEL".
3. **Selector de métrica de orden** — fila con scroll horizontal (`overflow-x:auto`, `scrollbar-width:none`), segmentos `padding:8px 11px`, `gap:1px`, JetBrains Mono 10.5px mayúsculas: Remates · Al arco · Faltas · Amarillas · Goles · Asist. Activo `#D8CDB4`/`#171310`.
4. **Filtro de equipo** — tres segmentos: Los dos / Local / Visitante. Activo `#B8AD95`/`#171310`.
5. **Cabecera de columnas** — `border-bottom:1px solid #2A2318`, `padding-bottom:7px`: JUGADOR (flex) · SERIE (`flex:0 0 64px`, centrado) · MED (`flex:0 0 34px`, derecha, `#EEE3CE`). JetBrains Mono 10px, `letter-spacing:.09em`.
6. **Filas de jugador** — `padding:11px 0`, `border-bottom:1px solid #221C15`:
   - Nombre (Anton 14px/1.05, `#EEE3CE` los dos primeros, `#D8CDB4` el resto).
   - Meta (JetBrains Mono 10px, `#918A7E`): `EQUIPO · PUESTO · TITULAR 3/3`.
   - **Sparkline de serie** — `flex:0 0 64px`, `height:24px`, tres barras `gap:3px` alineadas abajo, `background:rgba(238,227,206,.22)` con `border-top:2px solid` del color de intensidad. Altura en % del máximo de la serie.
   - Media (JetBrains Mono 600 14px, derecha).
   - **Estado de titularidad**, del campo `arranca`: suplente → fila a `opacity:.66`, nombre `#9C9588`, sparkline atenuada (`rgba(238,227,206,.1)` / `#867F75`) y meta en **`#C27152`** con el texto `SUPLENTE 0/3`. El que entra desde el banco juega veinte minutos: su serie no se compara con la de un titular, así que se muestra bajado de intensidad y dicho en el renglón — pero **no se esconde de la lista**.
7. **Ver los 36 · 28 MÁS ›** — fila `#221C15` con sombra.
8. Pie ("ESPN · ÚLTIMOS 3" · "DATOS 03 DE 03") + barra inferior.

---

### 5f — DATOS · Referencia

**Propósito:** contener lo que hoy son tres pestañas de primer nivel y se consulta poco.

**Layout:** cabecera + conmutadores (Referencia activa), sello "REFERENCIA · TABLAS · HISTORIAL · PLANTELES", y tres acordeones `gap:10px`, cada uno `#221C15` con sombra `4px 4px 0 #13100B`:

1. **Posiciones** (abierto) — conmutador de cuatro tablas (Zona A / Zona B / Anual / Prom.), activo `#D8CDB4`, inactivos `#171310`. Cabecera de columnas: `#` · EQUIPO · PJ · DG · PTS. Filas `padding:9px 0`, `border-bottom:1px solid #221C15`, texto `#9C9588`. **Los dos equipos del partido se destacan**: `background:#2A2318`, `margin:0 -8px`, `padding:9px 8px`, textos a `#EEE3CE` peso 600. El resto colapsa en filas de puntos suspensivos a `opacity:.5` ("cuatro equipos más").
2. **Historial** (abierto) — dos sub-bloques con rótulo JetBrains Mono 10px `letter-spacing:.09em`:
   - *CARA A CARA*: filas fecha (`flex:0 0 44px`) · cruce (Archivo 12px) · resultado (JetBrains Mono 600 12px).
   - *ÚLTIMOS CINCO*: por equipo, cinco cuadrados de 16×16 `gap:3px` — ganó `#EEE3CE`, empató `rgba(238,227,206,.3)`, perdió `rgba(238,227,206,.12)`. **Sin verde/rojo.** Leyenda al pie con `border-top`.
3. **Planteles** (cerrado) — "36 FICHAS".

**Advertencia obligatoria al pie** (`#2B1912` / `border-left:2px solid #C27152`): **"EL PLANTEL NO DICE QUIÉN FALTA"** — la fuente devuelve a todos como activos; lesionados y suspendidos no vienen en el dato. Va acá, donde el usuario mira el plantel, no al final de un análisis.

---

### 5g — Portada (Fecha)

**Propósito:** ver el día completo y entrar a un partido.

**Layout:**

1. **Cabecera de marca** — `#171310`, `padding:20px 16px 15px`, columna centrada `gap:9px`, `border-bottom:3px solid #76846A`. Logo SVG 52×52 (ver *Assets*), luego el wordmark "VALOR" (Anton 15px, `letter-spacing:.3em`, `#D8CDB4`) flanqueado por dos filetes `height:1px` `#3A3225` dentro de un contenedor de `max-width:250px`, y la línea de resumen: **"Dom 30 ago · 17 partidos · 2 oportunidades"** (JetBrains Mono 11px, `letter-spacing:.14em`, `#AAA190`).
2. **Selector de días** — seis celdas `flex:1 0 54px`, `padding:7px 0`, centradas. Activa `#EEE3CE` sobre `#171310`; inactivas `#221C15` con `opacity:.62` y `transform:scale(.93)`. Número JetBrains Mono 600 13px, día Archivo 11px mayúsculas.
3. **Franja de veredictos del día** — `#171310`, `padding:11px 12px 12px`, con sombra. Rótulo "VEREDICTO DEL DÍA" (JetBrains Mono 700 11px, `#76846A`, `letter-spacing:.14em`) + contador. Filas `padding:7px 0`, `border-top:1px solid #241D16`: barra vertical de 3px (dorada `#D6963A` para oportunidad, `#C27152` para riesgo), hora (JetBrains Mono 600 12px, `flex:0 0 40px`), cruce (Archivo 13px, con `text-overflow:ellipsis`), motivo en el color del estado, y liga abreviada a la derecha.
4. **Acordeones por liga** — rótulo "COMPETICIONES" + contador. Fila cerrada: `padding:13px 0`, `border-top:1px solid #2A2318`, `+` de 21px, nombre (Anton 16px/1.05 mayúsculas), sub-línea con **rango horario y recuento de oportunidades** (`15:00 → 21:30 · 1 oportunidad`, la cifra en `#D6963A`; o `6 mirados, ninguna`; o `1 riesgo no compensado` en `#C27152`), y cantidad de partidos a la derecha. Fila abierta: franja `#D8CDB4` con sombra, `−`, nombre en Anton 15px `#171310`, sub-línea en `#5B564F` con la cifra en `#8A6520`.
5. **Renglones de partido** (liga abierta) — `#221C15`, `padding:10px 11px`, sombra, `gap:8px` entre renglones. Hora · dos líneas equipo con escudo de 15px · sparkline de tres barras (`flex:0 0 44px`, 26px de alto) · **estado de veredicto** a la derecha en dos líneas (JetBrains Mono 700 11px/1.25, `letter-spacing:.04em`, `#8B857B`): `SIN / VENTAJA`, `SIN / PRECIO`.
6. **Talón abierto** (el partido con oportunidad) — `#2E2210` con sombra, dos columnas separadas por filete punteado vertical (`repeating-linear-gradient(180deg,#4A3C1E 0 3px,transparent 3px 8px)`):
   - Izquierda `flex:0 0 52px`: "Nº 14" (`#D6963A`), hora (JetBrains Mono 600 15px), "DE 17".
   - Derecha: dos filas de equipo con escudo de 17px y nombre Anton 15.5px/1.18; rótulo "VEREDICTO" (`#D6963A`); titular Anton 17px/1.18; una línea de tesis; tres celdas MÍNIMA / STAKE / MERCADOS (`1/6`); filete punteado; e **ingreso único**: "ENTRÁS POR / VEREDICTO" + `›` dorado.
   - El talón **no es un menú de destinos**: es el veredicto abreviado, y entra por la capa 01. Lectura y Datos quedan a un toque desde adentro.
7. **Pie** — "Datos actualizados 2026-08-30 12:06 · cómo se calcula", el enlace subrayado (`text-decoration-color:#4A4030`, `text-underline-offset:3px`) → Método.
8. Barra inferior con **Fecha** activa.

**Regla de copy:** la portada **no interpreta**. Las etiquetas viejas ("llega mejor", "partido parejo") son lectura y la lectura vive adentro. Cada renglón dice únicamente si hay algo apostable: `SIN VENTAJA`, `SIN PRECIO`, o talón dorado abierto. Y la franja de arriba cuenta **oportunidades**, no partidos destacados: si un día no hay ninguna, dice cero.

---

### 5i — Registro

**Propósito:** el rendimiento real de lo apostado. Fuera del partido, en la barra inferior.

**Layout:**

1. **Cabecera de sección** — `#171310`, `padding:18px 16px 14px`, `border-bottom:3px solid #76846A`: título (Anton 22px mayúsculas, `letter-spacing:.03em`) + "41 APUESTAS CERRADAS · DESDE 04/26" (JetBrains Mono 11px, `#918A7E`).
2. **Bloque de rendimiento** — `#221C15`, `padding:14px 13px 15px`:
   - ROI en JetBrains Mono 600 34px, **`#C27152`** si es negativo, con el desvío al lado (12px, `#918A7E`): `−3.27%  ± 6.19`.
   - **Gráfico de intervalo** — caja `#171310`, `padding:12px 11px 13px`. Riel `height:8px`, `background:rgba(238,227,206,.1)`. Encima: banda del intervalo `left:0;width:100%` en `rgba(194,113,82,.45)`; marca del punto ROI, 2px, `#C27152`, al **50%**; **tick del cero**, 1px, `#EEE3CE`, al **76%**. Eje debajo, `position:relative`, con `−9.5%` a la izquierda, `+3.0%` a la derecha y `0` absoluto al 76% con `transform:translateX(-50%)`.
   - **Cuidado al implementar:** los extremos del eje son los extremos del intervalo (−3.27 ± 6.19), así que la banda ocupa el riel completo, el punto cae al centro y el cero va donde corresponde por la escala: `(0 − (−9.5)) / 12.5 = 76%`. Si el eje se recalcula con otros datos, las tres marcas se derivan de la misma escala. En la pantalla de honestidad del producto, una barra que contradice sus propios números es el peor error posible.
   - Nota al pie: "El intervalo cruza el cero: con esta muestra no se puede afirmar que el método gane ni que pierda."
3. **Tres celdas** `gap:1px` — STAKE TOTAL · RESULTADO (negativo en `#C27152`) · ACIERTO.
4. **Por familia de mercado** — tabla con cabecera MERCADO · N · ROI (`flex:0 0 26px` y `flex:0 0 54px`). Filas `padding:10px 0`. ROI negativo `#C27152`, positivo `#D8CDB4`, sin muestra suficiente: **`n/d`** en `#8B857B` (una sola línea; no texto largo, la columna es de 54px).
5. **Últimas cerradas** — filas `#221C15`, `padding:10px 11px`, `gap:1px`: barra vertical de 3px (`#76846A` acertada, `#C27152` perdida), cruce + mercado (Archivo 13px), meta `fecha · cuota · stake` (JetBrains Mono 10.5px), y resultado en unidades (JetBrains Mono 600 12px) del color de la barra.
6. **Ver las 41 · 38 MÁS ›**, pie ("CIERRE 31/08/26" · "SOLO CERRADAS") y barra inferior con **Registro** activo.

---

### 5j — Método

**Propósito:** destino de todos los enlaces de fiabilidad de la app y explicación de los límites.

**Layout:**

1. Cabecera de sección: "MÉTODO" + "CÓMO SE CALCULA Y CUÁNTO SE LE CREE".
2. **Cuatro pasos** — `gap:1px`, cada uno `#221C15`, `padding:12px 12px 13px`, flex `gap:11px`: número (Anton 18px, `#918A7E`, `flex:0 0 20px`), título (Anton 14px mayúsculas) y una frase (Archivo 12px/1.55, `#B8AD95`). Goles esperados → Probabilidad → Cuota mínima → Stake.
3. **Señal por métrica** — rótulo de sección + una línea de encuadre, y caja `#221C15` `padding:13px 13px 14px` con siete filas `gap:10px`:
   - Cada fila: nombre (Archivo 12px) + valor (JetBrains Mono 600 12px) sobre un riel `height:6px` `rgba(238,227,206,.08)`.
   - Relleno proporcional a `valor / 2` (el riel representa 0 a 2.00×), y **tick del techo** de 1px `#76846A` al 50%.
   - Colores por tramo: debajo del techo `#EEE3CE` pleno; entre 1.00 y 1.60 `rgba(238,227,206,.5)` con texto `#D8CDB4`; por encima `rgba(194,113,82,.55)` con texto `#9C9588` y el valor extremo en `#C27152`.
   - Valores del diseño: posesión 0.62 · tackles 0.81 · córners 1.34 · faltas 1.41 · tarjetas 1.52 · remates al arco 1.88 · remates 2.09. **Vienen de `calibracion_jugadores.json` / `fiabilidad_medida`; leerlos del dato, no cablearlos.**
   - Leyenda al pie: tick + "techo 1.00".
4. **Límites** — cuatro bloques `#2B1912` / `border-left:2px solid #C27152`, `gap:1px`: título (Archivo 13px, `#EEE3CE`) + detalle (JetBrains Mono 11px, `#C27152`). Cinco partidos por equipo · No hay partes médicos · Una sola casa de cuotas · 41 apuestas cerradas.
5. **Rendimiento real → REGISTRO ›**, pie ("CALIBRADO 30/08/26" · "9 MÉTRICAS") y barra inferior con **Método** activo.

---

## Componentes compartidos

Extraer estos como clases antes de escribir pantallas — se repiten en las diez.

| Componente | Especificación |
|---|---|
| **Fondo de papel** | `background-color:#1B1611` + tres `radial-gradient` de puntos (`rgba(238,227,206,.05)` a 4px, `rgba(238,227,206,.035)` a 7px, `rgba(0,0,0,.06)` a 5px) con `background-position` desfasado (`0 0`, `2px 3px`, `3px 1px`). Es la textura de toda la app. |
| **Sombra dura** | `box-shadow:4px 4px 0 #13100B`. Nunca sombras blandas. |
| **Sello de sección** | Franja `#D8CDB4`, `padding:6px 11px 7px`, sombra dura. Título Anton 15px `#171310` mayúsculas + contador JetBrains Mono 700 11px `#5B564F`. |
| **Cabecera de partido** | `#171310`, `padding:13px 16px 12px`, flecha + cruce + liga/Nº. |
| **Conmutador de capas** | Tres segmentos iguales, activo `#EEE3CE`/`#171310`, inactivos `#221C15`/`#AAA190`, contenedor con `border-bottom:3px solid #76846A`. |
| **Sub-conmutador** | Subrayado de 2px en la activa, sin fondo. |
| **Segmentado de filtro** | `gap:1px`, `padding:8px 0`, activo `#D8CDB4` o `#B8AD95` sobre `#171310`. |
| **Fila de acordeón** | `#221C15`, `padding:12px 12px 11px`, nombre + marcador + `+`/`−` en JetBrains Mono 16px `#918A7E`. |
| **Barra comparativa** | Par de valores `flex:0 0 40px` + nombre centrado, barras `height:6px` `gap:3px` con `flex` proporcional; mayor `#EEE3CE`, menor `rgba(238,227,206,.24)`. |
| **Sparkline** | Tres barras `gap:2–3px` alineadas abajo, `background:rgba(238,227,206,.22)` + `border-top:2px solid`. Alto 24–26px. |
| **Bloque de advertencia** | `#2B1912`, `border-left:2px solid #C27152`, rótulo JetBrains Mono 700 11px `#C27152` mayúsculas + párrafo Archivo 12.5px/1.6 `#D8CDB4`. |
| **Filete punteado** | `repeating-linear-gradient(90deg,#3A3122 0 3px,transparent 3px 7px)`, `height:1px`. Vertical: `180deg` con `#4A3C1E`. |
| **Pie de talón** | Filete punteado + dos rótulos enfrentados, JetBrains Mono 11px `#8B857B` `letter-spacing:.12em`. |
| **Fila de enlace** | `#221C15` con sombra, `padding:11px 12px`: etiqueta Archivo 12px `#B8AD95` + destino JetBrains Mono 11px `#918A7E` (o `#D6963A` si apunta a Veredicto). |
| **Barra inferior** | `#171310`, `border-top:1px solid #2A2318`, tres celdas `flex:1` `padding:15px 0 14px` centradas, JetBrains Mono 11px `letter-spacing:.1em` mayúsculas. Activa `#EEE3CE` con un `::before` absoluto arriba (`left:22%;right:22%;height:2px;background:#EEE3CE`); inactivas `#9C9588`. **Fecha · Registro · Método**, en ese orden, en todas las pantallas. |

## Interactions & Behavior

**Navegación**

- Portada → talón: tocar un renglón lo expande al talón completo, y la liga colapsa los demás. Tocar el ingreso del talón entra al partido **en la capa VEREDICTO**.
- Dentro del partido: el conmutador de tres capas persiste en las tres pantallas; `←` vuelve a la portada.
- Datos tiene un segundo nivel (Equipos / Jugadores / Referencia) que persiste al cambiar de explorador.
- Barra inferior: siempre visible, cambia de sección completa. Fecha conserva el día y la liga abiertos al volver.

**Enlaces cruzados entre capas** (parte del diseño, no adorno):

| Desde | Hacia |
|---|---|
| Veredicto · "De dónde sale" | Datos, al acordeón de esa métrica ya abierto |
| Veredicto · "Sigue / Por qué lo decimos" | Lectura |
| Veredicto vacío · "Igual se puede leer" | Lectura |
| Lectura · pie de evidencia | Veredicto, a ese mercado |
| Datos · "Qué es la señal medida" | Método, a Señal por métrica |
| Datos · marcador de señal | Método |
| Portada · "cómo se calcula" | Método |
| Método · "Rendimiento real" | Registro |

**Acordeones** — un `+`/`−` que alterna. Los cerrados no montan su cuerpo. En el diseño de las nueve métricas está abierta una sola; si se permite abrir varias, mantener el `gap:1px` para que la lista siga leyéndose como una sola pieza.

**Estados de datos que hay que soportar** — no son casos de borde, son frecuentes:

- Veredicto con cero oportunidades (5h). **Implementar primero.**
- Mercado sin línea publicada → `SIN PRECIO`.
- Mercado sin dato de entrada (árbitro sin historial) → `SIN DATO`.
- Métrica con señal por encima del techo → `NO OPINAMOS` y fila atenuada.
- Muestra insuficiente para ROI por mercado → `n/d`.
- Jugador suplente → fila atenuada con `SUPLENTE 0/3` en `#C27152`.
- Motor y lectura discrepan → bloque de advertencia en Lectura.

**Animación** — en la portada, los renglones de una liga que se abre entran con `sube .32s cubic-bezier(.22,1,.36,1) backwards` y `animation-delay` escalonado de 38ms. Nada más se anima; sin transiciones de página.

**Responsive** — el diseño es de 390px. Escalar a lo ancho manteniendo los `flex` y los anchos fijos de columna (`flex:0 0 40px`, `0 0 54px`, `0 0 64px`); nada de reflows a multi-columna. El objetivo es móvil y no hay layout de escritorio definido.

## State Management

Vanilla, sin librería. Lo que hay que sostener:

- `diaActivo` — día seleccionado en el selector.
- `ligaAbierta` — cuál acordeón de liga está expandido (o ninguno).
- `partidoAbierto` — qué renglón está en talón dentro de la liga.
- `partidoActual` + `capaActiva` (`veredicto` | `lectura` | `datos`) — pantalla de partido.
- `exploradorActivo` (`equipos` | `jugadores` | `referencia`) y, dentro:
  - `localiaFiltro` (`todo` | `local` | `visita`) para Equipos
  - `metricaOrden` y `equipoFiltro` para Jugadores
  - `tablaActiva` (`zonaA` | `zonaB` | `anual` | `promedios`) para Referencia
- `metricasAbiertas` — set de acordeones desplegados.
- `seccionInferior` (`fecha` | `registro` | `metodo`).
- `listasExpandidas` — qué listas truncadas se abrieron ("Ver los 36", "Ver las 41").

**Datos** — todo sale de los `data/*.json` que ya produce el pipeline; el HTML solo lee. Campos que el rediseño empieza a usar y hoy no se muestran:

- **`concede`** — en las nueve métricas. Es la mitad del dato que falta; sin esto la capa Datos no tiene sentido.
- **`fiabilidad_medida`** (de `calibracion_jugadores.json`) — alimenta los marcadores de señal en Datos y el gráfico de Método.
- **`arranca`** — titular / suplente / "1 de 3", en la fila de cada jugador.
- **Los 18 jugadores por equipo** de `planteles.json`, no solo los destacados.

## Design Tokens

**Colores**

| Uso | Hex |
|---|---|
| Papel (fondo) | `#1B1611` |
| Papel, capa oscura (cabeceras, celdas internas) | `#171310` |
| Sombra dura | `#13100B` |
| Superficie de tarjeta | `#221C15` |
| Superficie de tarjeta, alterna | `#2A2318` · `#1F1710` |
| Tinta principal | `#EEE3CE` |
| Tinta secundaria | `#D8CDB4` |
| Tinta terciaria | `#B8AD95` |
| Tinta apagada | `#9C9588` · `#918A7E` · `#8B857B` · `#867F75` |
| Tinta sobre claro | `#171310` · `#5B564F` |
| Filete / borde | `#2A2318` · `#3A3122` · `#241D16` · `#3A3225` |
| Filete dorado | `#4A3C1E` · `#4A4030` |
| **Dorado (solo Veredicto)** | `#D6963A`, fondo `#2E2210`, tinta sobre claro `#8A6520` |
| **Alerta / riesgo** | `#C27152`, fondo `#2B1912`, filete `#4A2E20` |
| **Verde de filete estructural** | `#76846A` |
| Verde del logo | `#4E5730` · `#5A6338` · `#616B3C` · `#757F4E` |

**Tipografía**

- **Anton** — títulos, nombres de equipo, cifras destacadas. Solo peso 400. Mayúsculas con `letter-spacing:.02em`–`.03em` en títulos de sección.
- **Archivo** — texto corrido y etiquetas. 400 y 600.
- **JetBrains Mono** — números, rótulos, estados, metadatos. 400, 600 y 700.

Escala usada: 34 · 26 · 22 · 21 · 20 · 19 · 18 · 17 · 16 · 15.5 · 15 · 14 · 13.5 · 13 · 12.5 · 12 · 11.5 · 11 · 10.5 · 10 px. Interlineado: `1` en cifras y rótulos, `1.05`–`1.2` en títulos, `1.5`–`1.65` en texto corrido. `letter-spacing` en JetBrains Mono: `.04em` a `.14em` según jerarquía. `text-wrap:pretty` en todo párrafo.

**Espaciado** — 1 · 3 · 4 · 5 · 6 · 7 · 8 · 9 · 10 · 11 · 12 · 13 · 14 · 16 · 18 · 20 · 22 · 24 · 26 px. Los márgenes laterales de contenido son **asimétricos a propósito**: `margin:X 20px 0 16px` — 16 a la izquierda, 20 a la derecha, para dejar respirar la sombra dura de 4px.

**Radios** — ninguno. Todo a 90°.

**Sombras** — solo `4px 4px 0 #13100B`.

## Assets

- **Logo VALOR** — SVG inline, 100×100 `viewBox`, sin dependencias: una "V" en `#D8CDB4` con cuatro franjas verdes recortadas por `clipPath` y una línea de `#171310` de 2px cruzando. Está repetido en 5g y en 2a; **cada instancia necesita un `id` de `clipPath` único** (`vm-2a`, `vm-5g`) o el recorte se comparte y rompe. Al implementar, dejar una sola definición.
- **Escudos de equipo** — `https://a.espncdn.com/i/teamlogos/soccer/500/<id>.png`, 15px en renglones y 17px en talones, `object-fit:contain`. Ya es la fuente del pipeline.
- **Fuentes** — Anton, Archivo y JetBrains Mono. Verificar cómo las carga el `index.html` actual y usar el mismo mecanismo.
- Sin iconos, sin emoji, sin ilustración. Las flechas y los `+`/`−` son caracteres en JetBrains Mono (`←`, `›`, `→`, `+`, `−`).

## Files

- **`VALOR - Rediseño.dc.html`** — el archivo de diseño. Abre en el navegador. Es un canvas de opciones: **el turno 5 (`#5a` a `#5j`) es lo aprobado**; los turnos 4, 3, 2 y 1 son exploraciones anteriores y no se implementan. Cada opción lleva su id visible arriba.
- **`NOTAS-ARQUITECTURA.md`** — el razonamiento detrás del corte en tres capas y el diagnóstico de las siete pestañas. Contexto de por qué, no de cómo.

Orden de implementación sugerido: componentes compartidos → 5h (Veredicto vacío) → 5b (Veredicto con oportunidad) → 5g (Portada) → 5c (Lectura) → 5d/5e/5f (Datos) → 5j (Método) → 5i (Registro).
