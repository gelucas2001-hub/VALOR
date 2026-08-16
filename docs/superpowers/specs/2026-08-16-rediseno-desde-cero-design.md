# VALOR — rediseño desde cero

Fecha: 2026-08-16
Estado: aprobado por Lucas, pendiente de implementación
Revisión 3 — escalera de riesgo, regla de alineación, y umbral de cuota en vez de cuota de referencia

## Por qué

Lucas pidió arrancar el producto "desde 0" no porque el motor matemático estuviera mal, sino porque la interfaz y lo que la app ofrecía habían dejado de ir en la línea que buscaba: se volvió más complicada de usar, no menos, con demasiadas piezas (radar del día, veredictos con semáforo, "calidad del análisis" visible, combinada recomendada como bloque aparte) compitiendo por atención en vez de una sola narrativa por partido.

## Identidad: dos preguntas distintas

La confusión de fondo que arrastramos toda la primera vuelta fue tratar como una sola pregunta a dos que son distintas:

- **"¿Qué va a pasar en este partido?"** → el **pronóstico**. Es la promesa principal, la que cualquiera entiende, y la que define a VALOR. Se mide por **tasa de acierto**.
- **"¿A qué conviene apostar?"** → el **valor**. A veces coincide con el pronóstico, muchas veces no. Se mide por **rentabilidad**.

**VALOR es un pronosticador**, con un motor de value betting abajo sosteniéndolo. No al revés. La razón es de producto, no de matemática: presentarse como herramienta de value betting le exige al usuario común entender EV, banca y varianza antes de obtener algo útil. Presentarse como pronosticador no le exige nada — lee y decide.

**Pero nunca se contradicen en pantalla.** Un intento anterior mostraba "creemos que gana River, pero jugá a Racing a 5.75" — y eso, con razón, se leyó como mandar al usuario a una ruleta rusa. El problema real es de fondo: recomendar ese 27% se apoya en un modelo que medimos equivocándose 9-15pp. La regla que lo resuelve está más abajo (**escalera de riesgo** y **regla de alineación**): una sola lectura del partido, ofrecida a distintos niveles de riesgo, y nada que contradiga esa lectura.

**Principio de ejecución:** el rigor va en *qué* recomendamos, nunca en lo que le exigimos entender al usuario. Una cuota de 1.05 sin valor real no llega a la pantalla — no porque le expliquemos por qué, sino porque simplemente no se muestra. La fracción de Kelly se traduce a **énfasis editorial** ("esta la vemos clara" vs "nos gusta, con menos convicción"), no a aritmética en pantalla. Los números exactos viven en Herramientas, para quien los busque.

**Postura:** seguridad en el veredicto, honestidad en el historial. La app se la juega en cada pronóstico sin llenarse de advertencias, y por separado muestra sin drama cuántas veces acertó.

**Audiencia:** hoy es para Lucas. Pensado para que abrirlo a más gente no requiera rehacer nada, pero sin construir multi-usuario todavía.

**Alcance:** Liga Profesional Argentina, Copa Argentina, CONMEBOL Libertadores y Sudamericana. Volumen real: ~5 partidos por fecha en Liga, hasta 8-10 en día fuerte de copas.

## Hallazgos medidos (2026-08-16, sobre los 33 partidos con cuota de referencia)

Estos números motivan varias decisiones de abajo y no deben perderse:

- **Margen de la casa (DraftKings): 7.7% mediano** sobre la línea 1X2. Cualquier comparación contra cuota cruda tiene que descontarlo primero.
- **El modelo difiere de la línea limpia en 9-15 puntos porcentuales promedio.** Una casa seria suele estar a 2-3 puntos de la verdad. Un desacuerdo de 15pp es, casi siempre, el modelo estando peor informado — no una ventaja encontrada.
- **Un umbral ingenuo de "≠ mercado" dispara en 30 de 33 partidos (91%).** Una señal que aparece casi siempre no informa nada.
- **Sesgo sistemático hacia el local por competición:** Libertadores **+12.3pp**, Copa Argentina +5.5pp, Sudamericana +0.4pp, Liga Profesional −2.3pp.
- **Causa raíz:** la fuerza de ataque/defensa se ajusta *solo con partidos de la misma competición*. Hoy hay **6 partidos por equipo en copas y 4 en Liga** (temporada recién empezada). Con esa muestra la regularización empuja todo al promedio, el modelo cree que Cerro Porteño y Palmeiras son parecidos, y la localía termina decidiendo. Caso extremo medido: modelo 52.0% vs mercado 22.6%.

La app ya predica esto en Método ("si un mercado da más de +25% de EV, lo más probable es que tu λ esté mal"). El diseño tiene que respetar su propio principio.

## Cómo se recomienda (reglas duras)

Estas cuatro reglas resuelven la confusión de "qué vale y qué no", que fue el problema que más vueltas dio.

**1. Escalera de riesgo — franjas medidas, no estimadas.** Cada partido ofrece la misma lectura a tres niveles. Verificado sobre los 33 partidos: los tres tienen opciones en las tres franjas, siempre.

| Franja | Probabilidad | Ejemplo real (Racing–Banfield) |
|---|---|---|
| Lo más probable | 68-93% | Racing gana o empata — 74%, justa 1.36 |
| Intermedia | 45-68% | Menos de 2.5 goles — 63%, justa 1.59 |
| Arriesgada | 12-45% | Gana Racing 1-0 — 26%, justa 3.81 |

(Un intento anterior etiquetó como "lo más seguro" a un 54%. Eso es cara o cruz, no seguridad — los tres escalones deben estar en franjas distintas de verdad.)

**2. Los escalones son pronósticos; el valor se marca aparte.** Las apuestas seguras casi nunca tienen valor: el margen de la casa (7.7% medido) se come la ventaja justo en las cuotas bajas. Si se filtrara cada escalón por valor, solo sobreviviría el arriesgado — que es exactamente el problema rechazado. Entonces: los escalones responden *"¿qué es lo más probable?"*, y **la mostaza aparece solo donde además el precio está a favor**. Nunca se afirma valor donde no lo hay.

**3. Regla de alineación — nada contradice nuestra propia lectura.** Si el modelo señala "valor" en algo que va en contra de lo que creemos que va a pasar, eso no es valor: es error del modelo. No se muestra.

Para que esta regla signifique algo, la lectura debe venir de donde el modelo no llega — el análisis cualitativo. Si la lectura la produjera el propio modelo, filtrar por alineación sería circular (el modelo dándose la razón a sí mismo). De ahí se sigue: **solo se recomienda en partidos con análisis cargado.** Un partido sin analizar muestra datos y pronóstico, y dice claramente "todavía no estudiamos este partido" — no se ve roto, se ve honesto.

**4. Umbral de cuota, no cuota de referencia.** Mostrar "@2.20" de DraftKings es una trampa: el usuario va a Betsson y encuentra 2.05, y no sabe si sigue conviniendo. En su lugar se muestra **"conviene si te pagan más de 1.36"** — funciona en cualquier casa y es una sola regla fácil de aplicar.

**Y una regla de ritmo:** siempre hay pronóstico, no siempre hay recomendación. Habrá días sin nada que recomendar, y está bien — pero la app nunca debe quedarse sin opinión, o el usuario deja de abrirla.

## Correcciones al modelo (prioridad)

1. **Elo propio, cruzando competiciones.** Es el arreglo directo al sesgo medido arriba. Un equipo debe llegar a la Libertadores con la fuerza que se ganó en su liga local. No hace falta fuente externa: ya se baja el calendario completo de cada equipo (`/teams/{id}/schedule`), que incluye todas sus competiciones — el Elo se calcula en casa, gratis y sin claves nuevas.
2. **El mercado como línea base del backtest.** Hoy el backtest se compara contra un baseline ingenuo (tasa base con ventana expansiva). La vara que importa es la línea de la casa. Esto además alimenta el marcador de Registro: "acertamos 58%, el mercado 54%" convierte "estamos por encima del mercado" en un dato, no una postura.
3. **Seguimiento de acierto automático.** Hoy `backtest.py` se corre a mano. Que el cron calcule acierto acumulado (nuestro y del mercado) es lo que hace posible el marcador anterior.
4. **Lesiones cuantificadas (después, con validación).** Convertir una baja en ajuste de ataque/defensa según posición. Idea válida pero endeble — cuánto descontar exactamente es arbitrario. No entra hasta poder validarlo.

## Identidad visual

**Dirección:** prensa deportiva argentina vieja (tapas de El Gráfico, cupones de Prode, programas de cancha). Explícitamente **no**: crema+serif+terracota ("vintage americano" genérico), negro+verde ácido, ni negro+celeste+insignias+"PRO AI" (cliché de SaaS de IA, descartado tras ver una referencia real).

**Paleta — un color, un solo trabajo, siempre:**

| Color | Hex | Trabajo — único |
|---|---|---|
| Fondo | `#1B1611` | Casi negro tibio, noche de cancha (no negro frío de terminal) |
| Tinta | `#EEE3CE` | Texto, datos neutros, y **estado seleccionado** de cualquier control |
| Mostaza | `#D6963A` | **Valor**: acá hay algo mejor que el precio. Y nada más |
| Terracota | `#C06848` | **Alerta**: cuidado, esto no rinde. Y nada más |
| Salvia | `#6B7A5E` | Decorativo (filete bajo el logo). Sin trabajo funcional |

**Reglas duras:** nunca un tercer color funcional. Nunca semáforo verde/amarillo/rojo. Nunca mostaza para selección de UI (el día activo es tinta, no mostaza) — confundir "seleccionado" con "hay valor" es el error que más caro paga el usuario.

**Tipografía:** **Anton** para nombres de equipo, títulos de liga y wordmark (título de tapa de revista deportiva). **JetBrains Mono** para todo número que se compare o se confíe. **Archivo** para cuerpo, UI y prosa de análisis.

**Chrome y densidad:** pestañas silenciosas (línea inferior + color de texto, nunca botón con caja). Filas planas en listas largas, sin tarjeta-dentro-de-tarjeta. El bloque de análisis es tipografía sola, sin caja — nota de revista, no tarjeta de dashboard. Grano/textura solo en el masthead, nunca sobre filas de datos.

## Navegación

Tres destinos: **Fecha · Registro · Método**.

"Combinadas" se eliminó como destino: el picker manual le pide al usuario que arme algo, cuando el trabajo de la app es decirle qué hacer. La recomendación automática por partido (`recomendarCombinada()`, ya construida y validada: 23.1% de probabilidad conjunta exacta vs 17.8% multiplicando cuotas ingenuamente) vive dentro de Pronósticos.

"Ajustes" se eliminó como destino: la banca se pregunta inline en Herramientas la primera vez que hace falta, editable después. El umbral de valor y la cuota máxima quedan fijos con los valores ya validados. La casa de apuestas es un campo al registrar, no una pantalla.

## Pantalla: Fecha (portada)

- Logo, slider de días, agrupado por liga con todos los partidos a la vista (sin acordeón: con 5-10 partidos por día, todo entra).
- Por partido: hora + estadio, escudos + nombres, las tres cuotas de referencia, y **nuestro pronóstico**.
- **El pronóstico no es una señal rara, es un dato que siempre existe** — por eso reemplaza al "≠ Mercado", que disparaba en el 91% de los casos y no informaba nada. Se expresa como probabilidad o inclinación, no necesariamente nombrando un ganador.
- **La marca de valor sí es rara y va en banda:** por debajo de ~3pp de diferencia contra la línea limpia no hay nada que decir; por encima de ~12-15pp tampoco, porque ahí el sospechoso es el modelo, no el precio. El valor está en el medio.
- **Silencio cuando el modelo sabe poco.** Con 4-6 partidos por equipo, una competición debe mostrar menos, no más. La marca de valor se gatilla también por muestra disponible.
- Sin EV y sin monto sugerido en portada.

## Pantalla: Detalle de partido — 6 pestañas

Cabecera común: equipos, competición, hora, estadio, las tres cuotas, y el pronóstico.

1. **Análisis** (default) — el bloque humano en lenguaje llano: bajas, DT, contexto. Viene de `data/analisis.json` (específico del cruce). Sin entrada cargada, no se muestra nada.
2. **Pronósticos** — nuestra lectura del partido arriba, y debajo la escalera de riesgo con las cuatro reglas de la sección "Cómo se recomienda". Cada opción lleva su probabilidad, su umbral de cuota, y una línea que explica en castellano cuándo se cobra ("se te paga salvo que gane Banfield"). La combinada recomendada del partido vive acá como una opción más. Sin análisis cargado, esta pestaña dice que todavía no estudiamos el partido.
3. **Historial** — forma reciente (rival, local/visita, marcador) y cruces directos. El "color" viene de escudos reales e intensidad tipográfica (blanco pleno = ganado, apagado = perdido), nunca de mostaza/terracota.
4. **Posiciones** — tabla de la competición, con los dos equipos resaltados. Separada de Historial a pedido explícito.
5. **Plantel** — resumen corto (2-3 líneas) de estilo y actualidad por equipo, desde `data/equipos.json`. Debajo, **estadísticas del equipo** (que sí tenemos sin costo) y el plantel agrupado por posición. **Las estadísticas por jugador se traen solo al tocar un jugador** — el roster de ESPN da nombre y posición, pero cada estadística individual es un pedido aparte; mostrarlas en la lista serían ~50 pedidos por pestaña.
6. **Herramientas** — explícitamente "para vos, no para la gente". Cuota real de tu casa → EV y stake **en pesos** contra esa cuota. La etiqueta "Kelly" no aparece; el monto habla solo y el porqué está en Método. Banca preguntada inline la primera vez ("¿Cuánto separaste para apostar?"), editable después.

## Pantalla: Registro

Bitácora personal — acá el lenguaje técnico es correcto, el destinatario es el propio usuario.

- **Marcador principal: tasa de acierto, nuestra y la del mercado, lado a lado.** Es la métrica honesta de la promesa "pronosticamos", y comparada contra la línea es la prueba objetiva de estar por encima del mercado.
- **Rentabilidad y CLV debajo**, como consecuencia económica para quien la mire. (Corrección explícita respecto de la revisión 1: ahí se había descartado la tasa de acierto como métrica principal; con VALOR definido como pronosticador, es la métrica correcta. Lo único prohibido es presentarla como equivalente a rentabilidad.)
- Gráfico de curva acumulada (única línea curva de la app, en mostaza).
- Filtro por estado (Todas / Ganadas / Perdidas / Pendientes).
- Filas planas, resultado con la disciplina de color de siempre.
- **Los resultados se resuelven solos.** Ya bajamos los marcadores de ESPN para calcular la forma; pedirle al usuario que marque "Ganada/Perdida" a mano es fricción innecesaria y es lo que hace que la gente abandone el registro a la semana. Se resuelve automático todo lo que dependa del marcador (1X2, goles, ambos marcan, hándicap); queda manual solo lo que no podemos verificar.

## Pantalla: Método

Texto puro, sin cajas. Mantiene las explicaciones ya validadas (por qué valor y no probabilidad sola, valor falso, correlación, control de cordura, CLV, "lo que esto no es") y suma dos:

- **Que trabajamos con una cuota de referencia** (DraftKings vía ESPN, que no opera en Argentina), qué significa eso y por qué el EV real solo aparece contra la cuota que vos cargás. Transparencia en vez de esconder el dato.
- **Cómo nos medimos**: acierto propio contra acierto del mercado, sobre los mismos partidos.

## Pendiente — pasada de pulido

Fuera de alcance de este documento: escudos reales (hoy placeholders), reincorporar el grano del masthead con criterio, definir el **elemento firma** (la pieza memorable de VALOR, todavía sin encontrar), ritmo de espaciado y jerarquía fina, estados de carga e interacción, y más color/detalle en Historial y Plantel (pedido y aprobado en principio).

## Qué no cambia

Dixon-Coles, Poisson, EV, Kelly con fracción por calidad, devig, correlación por familia, probabilidad conjunta exacta para combinadas, rho calibrado por competición, y el pipeline (`actualizar.py`, ESPN, DraftKings como referencia). Este documento es sobre presentación, arquitectura de información y las correcciones de calibración listadas arriba — no sobre reemplazar el motor.
