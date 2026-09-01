# Arquitectura de información de VALOR — propuesta

Escrito después de recorrer `PRODUCT.md`, `expediente_estadisticas.py`, `index.html` y los `data/*.json`.

---

## 1. Diagnóstico: las pestañas están cortadas por origen del dato, no por intención

Hoy hay siete: Análisis · Pronósticos · Estadísticas · Historial · Posiciones · Plantel (+ Registro).

Cada una corresponde a **de dónde sale el dato** (la skill humana / el motor de goles / el caché de disciplina / ESPN tablas / ESPN plantel). Ninguna corresponde a **qué está tratando de hacer el usuario**. De ahí salen los cuatro problemas concretos:

**a) Hay dos lugares donde VALOR recomienda.**
`Pronósticos` recomienda mercados de resultado y goles. `Estadísticas` recomienda candidatos de córners, tarjetas y remates. Son la misma intención partida por familia de mercado. Eso es exactamente la sensación de "en Pronósticos también podrían aparecer cosas de Quién mirar": no es una duda de contenido, es un error de corte. **Mientras existan dos, siempre habrá solapamiento.**

**b) La afirmación y su evidencia viven en pestañas distintas.**
El Análisis dice "el visitante llega con la defensa rota", y el número que lo sostiene está tres pestañas más allá, en Estadísticas. El usuario tiene que hacer de puente. Peor: el análisis puede decir algo que el dato contradice y nadie lo nota, cuando el principio del producto es justamente que *la contradicción se muestra*.

**c) Historial, Posiciones y Plantel tienen el mismo peso de navegación que las recomendaciones.**
Son material de consulta ocasional ocupando slots de primer nivel. Eso aplana la jerarquía: todo parece igual de importante, entonces nada lo es.

**d) De los jugadores solo se ve a los candidatos.**
`planteles.json` trae 18 jugadores por equipo con serie reciente de remates, al arco, faltas, amarillas, goles y asistencias. La interfaz muestra un puñado destacado. El resto del dato existe y está invisible. Coincido en que esto hay que resolverlo — y no como "más candidatos", sino como una capa distinta.

---

## 2. Sobre tu lista de seis categorías

Tu propuesta era: pronósticos generales / pronósticos estadísticos de equipo / pronósticos estadísticos de jugador / candidatos / análisis general / análisis estadístico.

**No la tomaría.** Corta por *sujeto* (partido / equipo / jugador) y repite el eje pronóstico-vs-análisis tres veces. El resultado es que ante cada pieza de contenido el usuario tiene que preguntarse dos cosas antes de saber dónde buscarla ("¿es de equipo o de jugador?" y "¿es pronóstico o análisis?"), y varias piezas caen legítimamente en dos casillas. Además "pronóstico" y "análisis" son casi sinónimos en castellano: la etiqueta no ayuda a decidir.

El corte que sí resuelve el solapamiento es por **intención**, y da tres, no seis.

---

## 3. Propuesta: tres capas

### I — QUÉ DICE VALOR
*El veredicto. Único lugar del producto donde aparece una recomendación.*

Todas las familias de mercado juntas y ordenadas por valor: resultado, goles, córners, tarjetas, remates de equipo, mercados de jugador. Cada ítem es una línea colapsada (mercado + veredicto + cuota mínima) que se despliega a la tesis completa y un enlace directo a la evidencia en la capa III.

Esto absorbe `Pronósticos` **y** `Quién mirar` **y** los candidatos de Estadísticas. Al haber un solo lugar donde se recomienda, el solapamiento desaparece por construcción, no por disciplina.

Dos consecuencias de diseño que se desprenden de `PRODUCT.md`:
- La capa tiene que estar diseñada para **mostrar cero**. Con ROI −3.27% ± 6.19 y la regla de no prometer valor donde no hay ventaja medida, "hoy no hay nada" es un estado legítimo y frecuente, no un error. Es la pantalla que hay que diseñar primero, no la última.
- Los mercados que repiten la misma tesis se agrupan visualmente en vez de contarse como tres recomendaciones.

### II — POR QUÉ
*La lectura del partido, con la evidencia incrustada.*

La narrativa de la skill, pero cada afirmación acompañada en el mismo bloque por el dato que la sostiene: la comparativa de la métrica citada, la posición en la tabla, el H2H relevante, las bajas. No enlaces a otra pestaña — el número al lado de la frase.

Esto absorbe `Análisis` + `Contexto`, y consume `Historial` y `Posiciones` como evidencia inline en lugar de dejarlos como destinos. Cuando el motor y la skill discrepan, la discrepancia se muestra acá, que es el único lugar donde tiene sentido leerla.

### III — LOS DATOS
*Exploración libre. Sin veredictos, sin dorado, nunca.*

Tres exploradores, cada uno con desplegables por familia de métrica (acá es donde entra la idea del 4B):

- **Equipos** — las nueve métricas (`remates, al_arco, córners, faltas, tarjetas, posesión, tackles, atajadas, offsides`), siempre en el par **produce / concede**, con split local-visita. El cruce es la unidad, no el promedio suelto.
- **Jugadores** — los 18 de cada plantel, **todos**, ordenables por cualquier métrica, con la serie completa visible y el estado `arranca` (titular / suplente / "1 de 3") en el renglón. Esta es la respuesta a tu punto: el usuario arma sus propios candidatos.
- **Referencia** — tablas de posiciones por zona, anual, promedios; historial completo; planteles.

---

## 4. Dos cosas que el dato ya tiene y la interfaz no muestra

Salieron de leer el pipeline, no de la conversación. Las dos son, para mí, más importantes que cualquier reorganización de pestañas.

**`concede`.** Cada equipo tiene medido lo que produce **y lo que le conceden sus rivales**, en las nueve métricas. El comentario del propio código lo dice: *"la pregunta del mercado de estadísticas es casi siempre sobre el CRUCE"*. Mostrar solo lo que produce un equipo es literalmente la mitad del dato. Esto cambia la unidad visual de la capa III: la fila no es "Racing: 12.4 remates", es "Racing produce 12.4 · el rival concede 14.1".

**`fiabilidad_medida`.** `calibracion_jugadores.json` guarda, por métrica, cuánto se le puede creer, medido contra el ruido. Remates se desvía 2.09 veces lo que explica el azar; goles está bien. Hoy la interfaz muestra un promedio de remates y uno de goles con exactamente la misma autoridad tipográfica. Propongo un marcador de fiabilidad persistente en cada métrica de la capa III — no un disclaimer al pie, un atributo del número. Encaja con el principio de honestidad del producto y no existe en ningún competidor.

---

## 5. Lo que hay que decidir antes de dibujar

1. ¿Tres capas o preferís conservar más granularidad arriba?
2. Nombres: "Qué dice VALOR / Por qué / Los datos" es explícito pero largo. Alternativa más seca: "Veredicto / Lectura / Datos".
3. ¿La capa III se navega por equipo (Local | Visitante) o por métrica (todos los remates juntos)? Cambia bastante la pantalla.
