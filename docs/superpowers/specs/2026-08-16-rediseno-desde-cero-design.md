# VALOR — rediseño desde cero

Fecha: 2026-08-16
Estado: aprobado por Lucas, pendiente de implementación

## Por qué

Lucas pidió arrancar el producto "desde 0" no porque el motor matemático estuviera mal (Dixon-Coles, EV, Kelly, calibración, combinadas exactas — todo eso queda intacto y no se toca en este rediseño) sino porque la interfaz y lo que la app ofrecía habían dejado de ir en la línea que él buscaba: se volvió más complicada de usar, no menos, con demasiadas piezas (radar del día, veredictos con semáforo de color, "calidad del análisis" como concepto visible, combinada recomendada como bloque aparte, contexto compacto) compitiendo por atención en vez de una sola narrativa clara por partido.

## Misión

VALOR es un pronosticador de fútbol: le da a la persona toda la información (estadísticas, cuotas, plantel, historial) más el análisis y la recomendación de un experto, en lenguaje llano — sin jerga de apostador profesional en el camino principal. Sirve tanto a alguien que solo quiere saber "a qué le conviene apostar hoy" como, más adentro, a quien quiere ver el detalle técnico completo.

**Audiencia:** hoy es para Lucas. El lenguaje y la estructura están pensados para que, si en el futuro se abre a más gente (conocida o no), no haga falta rehacer nada — pero no se construye ninguna funcionalidad multi-usuario todavía (sería prematuro).

## Identidad visual

**Dirección:** prensa deportiva argentina vieja (tapas de El Gráfico, cupones de Prode, programas de cancha) — no "vintage americano genérico" (cliché de crema+serif+terracota) ni "instrumento/terminal" (la dirección anterior) ni "SaaS de IA" (celeste + insignias, cliché descartado explícitamente tras ver una referencia real).

**Paleta — un color, un solo trabajo, siempre:**
- Fondo casi negro tibio (`#1B1611`) — noche de cancha, no negro frío de terminal.
- Tinta crema (`#EEE3CE`) — texto, datos neutros, y el estado "seleccionado" de cualquier control (día activo, filtro activo). Nunca significa valor.
- **Mostaza (`#D6963A`) — significa "acá hay valor", y solo eso.** Aparece en: la señal "≠ mercado a favor", la cuota destacada, el pick #1 de Pronósticos, "Jugale $X" en Herramientas, "Ganada" en Registro, la curva del gráfico acumulado.
- **Terracota (`#C06848`) — significa "alerta/cuidado", y solo eso.** Aparece en: la señal "≠ mercado en contra", "Perdida" en Registro. Reemplaza al óxido/rust del sistema visual anterior (mismo rol semántico).
- Verde salvia (`#6B7A5E`) — decorativo únicamente, filete de tres colores bajo el logo. Sin trabajo funcional; si no encuentra uno, se puede sacar sin pérdida.
- **Regla dura:** nunca introducir un tercer color funcional, ni badges de semáforo (verde/amarillo/rojo), ni reutilizar mostaza/terracota para algo que no sea valor/alerta (ej. la selección de un día NO es mostaza, es tinta crema).

**Tipografía:**
- **Anton** — nombres de equipo, títulos de liga, wordmark, cabeceras. Imita el título de tapa de revista deportiva vieja.
- **JetBrains Mono** — todo número que se compara o se confía (cuotas, EV, probabilidad, stake).
- **Archivo** — cuerpo de texto, UI, análisis en prosa.

**Chrome y densidad — lecciones de dos referencias reales que Lucas trajo:**
- Pestañas silenciosas: línea inferior + color de texto, nunca botón con caja/relleno (referencia: apps de resultados en vivo).
- Filas planas en listas largas (historial, plantel, posiciones): sin tarjeta-dentro-de-tarjeta, el peso lo lleva la tipografía y el escudo, no el borde.
- El bloque de "Análisis" es tipografía sola, sin caja — como una nota de revista, no una tarjeta de dashboard.
- Grano/textura reservado exclusivamente al header/masthead — nunca sobre filas de datos, por legibilidad.

**Explícitamente descartado (con el motivo):**
- Verde/amarillo/rojo tipo semáforo, "PRO AI" como branding, insignias compitiendo por tarjeta — cliché de "SaaS de IA genérico", visto en una referencia real y rechazado.
- "% de aciertos" como métrica protagonista en Registro — contradice el principio central del Método (alta probabilidad no significa ganancia; ver ejemplo del 91% a cuota 1.07).
- Monto de apuesta en pesos en la pantalla principal — se sacó por sentirse una orden, no una herramienta.

## Estructura de navegación

Tres destinos: **Fecha · Registro · Método**. ("Combinadas" y "Ajustes" existían como pestañas propias antes y se eliminaron — ver más abajo por qué.)

## Pantalla: Fecha (portada)

- Arriba: nombre/logo de la app.
- Slider de días (fecha con desplazamiento horizontal), sin desplegable de ligas — con la cantidad real de partidos por día (1 a 7 según los datos actuales), todo cabe a la vista sin acordeón.
- Agrupado por liga, título simple, todos los partidos visibles debajo.
- Cada partido: hora + estadio, escudos + nombres, las tres cuotas (local/empate/visita, con la de DraftKings vía ESPN — cubre 33 de 34 partidos hoy), y **una señal, no seis números**: "≠ Mercado" con una frase corta cuando el modelo difiere del precio, silencio (una línea gris) cuando no.
- **Sin EV visible acá** — mostrar EV calculado sobre la cuota de referencia (DraftKings, que no opera en Argentina) sería prometer un valor que el usuario no puede cobrar en su propia casa de apuestas. El EV real vive adentro del partido, en Herramientas, contra la cuota que el usuario carga.
- **Sin monto sugerido** — se sacó explícitamente, se sentía una orden más que una herramienta.

## Pantalla: Detalle de partido — 6 pestañas

Orden: **Análisis → Pronósticos → Historial → Posiciones → Plantel → Herramientas**. Cabecera común a las seis: equipos, competición, hora, estadio, las tres cuotas, y la señal de valor con una frase.

1. **Análisis** (default) — el bloque humano: bajas, DT, contexto, en lenguaje llano. Viene de `data/analisis.json` (específico de este cruce). Si no hay entrada cargada, no se muestra nada — cero peso agregado, mismo criterio de siempre.
2. **Pronósticos** — la única pestaña nueva de esta ronda. Recomendaciones **ordenadas por EV** (no por probabilidad — ya validado con el caso del 91%/1.07 vs 43%/2.85), con probabilidad siempre visible al lado, filtradas por el umbral de valor y el tope de cuota máxima ya existentes (esto es lo que evita recomendar tanto una cuota de 1.01 como un disparate improbable — el usuario lo pidió explícitamente y ya estaba resuelto). El mejor pick se destaca, el resto queda listado sin competir en atención. Si nada supera el umbral, pestaña vacía con una frase honesta — no se inventa una recomendación para llenar la pantalla. **La combinada recomendada de este partido vive acá abajo como una tarjeta más** (reutiliza `recomendarCombinada()`, ya construido y validado con un caso real: 23.1% de probabilidad conjunta exacta vs 17.8% si se multiplicaran las cuotas ingenuamente).
3. **Historial** — forma reciente (últimos 5, con rival/local-visita/marcador — ya estaba construido) + últimos cruces directos. El "color" pedido por Lucas viene de escudos reales e intensidad tipográfica (blanco pleno=ganado, apagado=perdido), nunca de mostaza/terracota — esos ya tienen trabajo asignado.
4. **Posiciones** — tabla de la competición, con los dos equipos del partido resaltados. Separada de Historial a pedido explícito de Lucas.
5. **Plantel** — arriba, resumen corto (2-3 líneas, "simplemente eso") de estilo/actualidad por equipo, tomado de `data/equipos.json` (dato reutilizable entre partidos, no específico de este cruce — dos capas de datos distintas y complementarias, ya diseñadas de antes). Debajo, estadísticas del equipo en el torneo (goles, córners, tarjetas promedio) y plantel agrupado por posición con goles/remates por jugador (reutiliza la búsqueda de jugador on-demand ya construida). Pendiente de una pasada de color/detalle visual — aprobado en estructura, no en pulido final.
6. **Herramientas** — lo técnico, explícitamente "para vos, no para la gente en general". Cuota real de la casa de apuestas del usuario → EV/stake personal contra esa cuota (no la de referencia). **El stake se muestra en pesos, no en porcentaje** (la gente común piensa en "tengo $5.000 para jugar hoy", no en fracciones de Kelly — mostrar solo un % sería cambiar una jerga por otra). La etiqueta "Kelly ⅛" se saca del primer plano; el número de pesos habla solo, y el porqué queda explicado con calma en Método para quien lo busque. Punto de entrada para armar una combinada cruzando varios partidos.

## Por qué "Combinadas" y "Ajustes" dejan de ser pestañas propias

- **Combinadas** (el picker manual de patas de cualquier partido) se evaluó y se descartó como pantalla propia: le pide al usuario que arme algo, cuando el trabajo de la app es decirle qué hacer. La recomendación automática por partido (`recomendarCombinada()`) ya cubre ese caso mejor, y vive dentro de Pronósticos.
- **Ajustes** perdió su única razón de ser cuando la banca se resolvió de otra forma: en vez de una pantalla de configuración que se visita una vez y nunca más, la banca se pregunta **inline, en Herramientas, la primera vez que hace falta** ("¿Cuánto separaste para apostar?", con explicación corta, editable después con un link "cambiar"). El umbral de valor y la cuota máxima quedan fijos con los valores ya validados durante la sesión de calibración — no configurables, porque ya están probados. "Casa de apuestas" pasa a ser un campo suelto en Registro al momento de cargar una apuesta, no una pantalla aparte.

## Pantalla: Registro

Bitácora personal — acá el lenguaje técnico está bien porque el destinatario es el propio usuario, no alguien nuevo. Resumen (Resultado en pesos, ROI, CLV medio, cantidad de apuestas cargadas — **nunca "% de aciertos" como métrica protagonista**, por la razón ya explicada en Método). Gráfico de curva acumulada (la única línea curva de toda la app, en mostaza — acumulado positivo es, literalmente, valor). Filtro por estado (Todas / Ganadas / Perdidas / Pendientes — idea rescatada de una referencia que Lucas trajo, sin el resto de esa referencia). Lista de apuestas cargadas, filas planas, botones de resultado con la misma disciplina de color (mostaza=ganada, terracota=perdida).

## Pantalla: Método

Texto puro, sin cajas — mismo tratamiento que Análisis. Mantiene las explicaciones ya escritas y validadas (por qué EV y no probabilidad, valor falso, Kelly escalado por calidad del análisis, correlación, control de cordura, CLV, "lo que esto no es").

## Pendiente — pasada de pulido (fuera de alcance de este documento)

Explícitamente diferido, no soy parte de esta ronda de decisiones:
- Escudos reales (hoy son placeholders grises en todos los mockups).
- Reincorporar la textura de grano en el header con más criterio.
- Definir el "elemento firma" — la pieza única y memorable de VALOR, todavía no encontrada.
- Ritmo de espaciado y jerarquía tipográfica en detalle.
- Estados de carga e interacción (qué pasa al tocar, no solo cómo se ve quieto).
- Más color/detalle visual en Historial y Plantel, ya pedido por Lucas y aprobado en principio.

## Qué no cambia

Todo el motor matemático: Dixon-Coles, EV, Kelly con fracción por calidad del análisis, devig, correlación por familia de mercado, probabilidad conjunta exacta para combinadas del mismo partido, calibración vía backtest, el pipeline de datos (`actualizar.py`, ESPN, DraftKings como referencia). Nada de esto se toca — este documento es sobre presentación y arquitectura de información, no sobre el modelo.
