# VALOR — reglas del repo

Leé esto antes de tocar nada. Existe porque tres herramientas de IA
editaron `index.html` en paralelo sin saber una de la otra, y el
resultado fue trabajo perdido y funcionalidad borrada.

## Antes de empezar

**Leé `TRASPASO.md` entero, primero que nada.** Es el informe de
traspaso del proyecto: qué salió mal antes, qué está resuelto, y en qué
orden seguir. Señala todo lo demás — `DESIGN.md`, el spec, y
`docs/design-handoff/` (una entrega de diseño ya verificada, con una
funcionalidad nueva lista para implementar). Si `TRASPASO.md` y este
archivo se contradicen en algo, gana `TRASPASO.md`: es el más nuevo.

## Qué es cada cosa

| Archivo | Qué hace | Quién lo toca |
|---|---|---|
| `actualizar.py` | Baja datos de ESPN y calcula λ. Corre solo, 2 veces por día, vía GitHub Actions | Con cuidado — es el motor |
| `index.html` | La app. Es la interfaz nueva: reemplazó a la vieja el 2026-08-18 | Una herramienta por vez — ver abajo |
| `test_registro.js`, `test_alineacion.js` | Suites que leen el `index.html` publicado, no una copia | Correr después de tocar la app |
| `doble_via.py` | Compara el motor de Python contra el de JavaScript | Correr después de tocar el motor |
| `data/resultados.json` | Marcadores finales que escribe el cron. Hace exacto el cruce del Registro | Nadie |
| `TRASPASO.md` | Informe de traspaso — léelo primero | A mano, mantenerlo al día |
| `docs/design-handoff/` | Entrega de diseño de Claude Design, verificada | No editar; es referencia |
| `backtest.py` | Calibración contra resultados | A mano |
| `medir_sesgo.py` | Cuánto nos apartamos de la línea del mercado | A mano, antes y después de tocar el modelo |
| `medir_vs_mercado.py` | Brier contra la cuota de cierre real | A mano |
| `medir_calibracion.py` | Cuando la app dice 70%, ¿pasa el 70%? Mide la calibración de lo que la app ya publicó, partido por partido — a diferencia de `backtest.py`, que reconstruye lo que el modelo habría dicho. Faltaba en esta tabla hasta el 2026-08-24 | A mano, cada tanto |
| `historico.py` | Baja y normaliza el historial largo de football-data.co.uk: 6310 partidos de arg, 5544 de bra, **4180 de eng y 3857 de fra** (agregadas el 2026-08-25), con cuota de cierre de Pinnacle. Es la base de las mediciones serias. Lee los **dos** formatos de la fuente — un archivo único para las ligas nuevas, uno por temporada para las clásicas de Europa. Solo el segundo trae estadísticas por partido, y esa es la razón por la que en Inglaterra se distinguen los equipos y en Argentina no | A mano |
| `equipos.py` | Cruza los nombres de equipo del CSV de football-data con los de ESPN, que es lo unico que ataba las dos fuentes. **Solo por igualdad exacta despues de normalizar** — nada de parecido ni prefijos: en Ligue 1 juegan Paris Saint-Germain y Paris FC a la vez, y el CSV tiene a los dos (395 partidos contra 34). Un cruce difuso les funde la historia y eso no se ve como un error, se ve como datos. De los 15 nombres que no coincidian, 12 los resuelve el `shortDisplayName` que ESPN ya publica y uno el apostrofo: la tabla a mano es de **tres** entradas. Cruza 19 de 20 en Inglaterra y 17 de 18 en Francia; los dos que faltan son ascendidos sin historia en primera | A mano, cuando cambia una liga |
| `medir_historico.py` | El modelo contra el mercado sobre TODO el historial, walk-forward. La vara es la tasa base, no 'siempre un tercio' | A mano, cada tanto |
| `medir_devig.py` | Qué método de quitar el margen de la casa acierta. Medido el 2026-08-25 sobre 11.854 partidos con cuota de cierre real: gana Shin, y gana más cuanto más alto el margen — que es la condición de la app. Antes la app usaba el proporcional y las mediciones usaban Shin | A mano, cada tanto |
| `medir_encogimiento.py` | Si conviene calmar al modelo mezclándolo con la tasa base, y cuánto. Medido el 2026-08-25 fuera de muestra: en arg sí (k=0.20, cuatro errores estándar); en bra no, y con la ventana correcta empeora. **Medido y NO se aplica**: mejora el Brier de verdad, pero cambia el 43% de las marcas sin que el set nuevo rinda mejor (−2.35% ±18.78, puro ruido). Ver TRASPASO.md. Mejorar el Brier no es ganar plata | A mano, cada tanto |
| `medir_corners.py` | El mercado de córners contra **plata**, no contra calibración. Baja la línea de cierre real de DraftKings vía el endpoint `propBets` de ESPN, le quita el margen y mide ROI walk-forward. Medido el 2026-08-25 sobre 81 líneas: **la casa pone la línea justo en el punto de la moneda** — el mercado le gana a tirar una moneda por 0,0008 de Brier y cobra 8,4% de margen. El ROI daba +11,2% ±13,9% sobre 41 apuestas: ruido, harían falta ~300. El de **por equipo** sí se sabe: atraso +0,0205 ±0,0093 (2,2 errores estándar detrás) y ROI negativo en los seis umbrales — le apostamos el promedio de la liga a una casa que distingue equipos | A mano, cada tanto |
| `medir_clv.py` | Si la línea se mueve hacia nosotros. Es lo único que dice si hay ventaja sin esperar cientos de apuestas. Necesita que el cron junte fotos primero | A mano, cada tanto |
| `medir_discriminacion.py` | ¿Tenemos opinión propia por equipo, o publicamos el promedio de la liga? Calibrar no alcanza: un pronóstico que le da a todos el promedio calibra perfecto y no sirve para apostar. Medido el 2026-08-25: con 4 partidos por equipo solo posesión y tackles superan el techo de falsa señal — y ninguna de las dos tiene mercado | A mano, cada tanto |
| `medir_lineas.py` | Si el mercado de estadísticas (córners, tarjetas, remates) dice la verdad. Mide calibración, no plata: no hay cuotas históricas de córners. Medido el 2026-08-24: córners bien, faltas con sesgo de 9 puntos | A mano, cada tanto |
| `medir_jugadores.py` | Si las líneas de JUGADOR (remates, al arco) dicen la verdad. Compara el desvío contra el ruido, no contra cero: con 618 casos un modelo perfecto ya desvía 3.5 puntos. Medido el 2026-08-24: remates mal (2.09x el ruido), al arco regular, goles y asistencias bien | A mano, cada tanto |
| `medir_arbitros.py` | Si el árbitro mueve las tarjetas. Prueba de permutación: puede decir que no, y hoy dice que no | A mano, cada tanto |
| `medir_analisis.py` | Si la `inclinacion` del análisis acierta, y si la regla de alineación suma o resta. Correr después de cada fecha | A mano |
| `calibrar_ligas.py` | Cuánto vale cada liga sudamericana | A mano, cada tanto |
| `data/*.json` | Lo escribe el cron. **No editar a mano** | Nadie |
| `data/planteles.json` | Jugadores con números (PJ, goles, peso goleador). Lo escribe el cron | Nadie |
| `data/estadisticas.json` | Promedios por partido de cada equipo (remates, córners, posesión, tackles). Sale del mismo `/summary` que ya se pedía: cero pedidos extra | Nadie |
| `data/cuotas.json` | Historia de la cuota de mercado, foto por corrida. Se acumula: ESPN la borra cuando el partido termina | Nadie |
| `data/calibracion_jugadores.json` | Cuánto le erra cada línea de jugador. Lo escribe `medir_jugadores.py`, y la app lo lee para decir en pantalla de qué fiarse | A mano, vía ese script |
| `data/analisis.json` | Análisis cualitativo, carga manual. El cron **nunca** lo toca | A mano |

## El research de `analisis.json` — con qué skill, y con cuál no

Desde el 2026-08-19, esta terminal SÍ puede correr la investigación:
`python expediente.py <id>` arma el expediente objetivo, y la skill
versionada en `.claude/skills/valor-analisis-inclinacion/SKILL.md`
hace el research y escribe `inclinacion`/`local`/`visitante`/
`contexto`/`veredicto`. Desde el 2026-08-20 el expediente incluye el
plantel de los dos equipos con partidos jugados y peso goleador: la
skill **pesa** las bajas contra esos números en vez de enumerarlas, y
escribe una lectura por equipo (antes el rival quedaba sin describir).
Esa
skill es la fuente de verdad — se edita ahí, en el repo, no en
Claude.ai (evita el problema de dos copias divergiendo sin que nadie
lo note).

**Ojo con el nombre parecido.** Hay (o puede volver a haber) una skill
instalada localmente como `analisis-futbol-valor-json`, que NO es
esta — tiene un esquema de salida distinto (`hallazgo_principal`,
`texto_corto`, sin `inclinacion`, que es el único campo que lee
`index.html`) y espera como input los números del modelo
(`probabilidades_modelo`, `ev_mercado_principal`), justo lo que
`expediente.py` existe para esconder. Invocarla sin querer produce un
JSON que la app no usa y que además viola la regla de alineación. Pasó
una vez (2026-08-19). Antes de correr el análisis, confirmar que es
`valor-analisis-inclinacion` — si el nombre no coincide exacto, no es
esta.

## Restricciones duras

- **`actualizar.py`: solo biblioteca estándar.** Corre en GitHub Actions sin `pip install`. Nada de dependencias.
- **Sin claves de API.** Todo sale de endpoints públicos.
- **No cambiar el contrato de `data/partidos.json`.** Agregar campos sí; renombrar o cambiar tipos rompe el frontend.
- **No tocar constantes del modelo para que un número dé mejor.** Si una medición no mejora, el hallazgo es que no mejoró. Hay scripts para medir: usalos.
- **Un barrido que mejora en el borde de la grilla no encontró nada.**
  Pasó dos veces el 2026-08-24. Con `VIDA_MEDIA_DIAS` se frenó a tiempo
  y se extendió la grilla; el valor bueno estaba adentro. Con `rho` la
  primera grilla (-0.05 a 0.15) daba su mejor número en -0.05, o sea
  chocando contra la pared. Elegir el extremo de una grilla es elegir
  dónde uno dejó de mirar.
- **Un parametro de liga se calcula DENTRO de la liga.** El 2026-08-25,
  al entrar Premier y Ligue 1, se vio que `parametros_metricas()` corria
  sobre todo el cache mezclando competiciones. `k` sale de partir la
  variacion entre equipos en ruido y senal, asi que con varias ligas en
  el pozo **la diferencia entre ligas se lee como diferencia entre
  equipos**: `k` baja y parece que aprendimos a distinguir equipos
  cuando distinguimos paises. El pozo daba k=77.6 en corners donde
  Argentina tenia 17.0 y Brasil 200.0 — y en tarjetas daba la conclusion
  opuesta a la verdadera para cada una. Si agregas una competicion,
  fijate que ningun estadistico agregado la mezcle con las demas.

- **La fuente cambia de formato sin avisar, y el parser lo tapa.**
  football-data usa año de cuatro dígitos en casi todos sus archivos y
  de dos en cuatro de ellos (`E0-1617`, `F1-1516`, `F1-1617`,
  `F1-1718`). El `except ValueError` de la fecha los descartaba en
  silencio: **1521 partidos**, una temporada entera de Inglaterra y tres
  de Francia, perdidas sin un solo mensaje. Encontrado el 2026-08-25
  porque los totales no cerraban contra un conteo hecho aparte. Si un
  parser tuyo tiene un `except` que saltea filas, contá cuántas saltea y
  comparalo contra el archivo: un descarte silencioso no se ve como un
  error, se ve como menos datos.

- **Cruzar nombres solo por igualdad exacta, nunca por parecido.** El
  2026-08-25, al unir el CSV de football-data con ESPN, el atajo obvio
  era casar por prefijo o por distancia de edición. En Ligue 1 juegan
  **Paris Saint-Germain y Paris FC la misma temporada**, y el CSV trae a
  los dos: 395 partidos contra 34. Cualquier cruce difuso les pega la
  historia de uno al otro, y el resultado no se ve como un error — se ve
  como datos. Un nombre sin cruzar se nota; uno mal cruzado, no. Por lo
  mismo, `equipos.py` no cruza por abreviatura aunque ESPN la traiga:
  Brentford y Brest son los dos "BRE". Y si dos equipos reclaman el
  mismo nombre, ese nombre queda **afuera** del índice en vez de irse
  con el último que pasó.

- **Mirá la fuente antes de transcribir a mano.** De los 15 equipos de
  eng/fra cuyo nombre no coincidía, el impulso era escribir las 15
  entradas. ESPN ya publica `shortDisplayName` y eso resuelve 12; sacar
  el apóstrofo resuelve otra. La tabla escrita a mano quedó en **tres**
  entradas, y cada entrada a mano es una que hay que mantener el día que
  la fuente cambie.

- **Comparar el error contra el ruido, no contra cero.** Con 618
  predicciones, un modelo PERFECTAMENTE calibrado ya desvía 3.5 puntos
  solo por azar — 600 monedas no salen exactamente mitad y mitad. El
  2026-08-24, midiendo las líneas de jugador, se estuvo a punto de
  reportar `al_arco` como mala con 4.6 de desvío: simulando un modelo
  perfecto se vio que ese valor sale el 6% de las veces por casualidad.
  `medir_jugadores.py` tiene la función (`ruido_esperado`); usála antes
  de llamar rota a una métrica.

- **Una sola forma de sacarle el margen a una cuota, y es Shin.**
  Hasta el 2026-08-25 `index.html` repartía el margen parejo entre las
  tres opciones mientras `medir_clv.py` y `medir_historico.py` usaban
  Shin (1993): se medía el modelo con una vara y se marcaba valor con
  otra. Está medido sobre 11.854 partidos (`medir_devig.py`) que el
  proporcional le erra casi el doble cuando el margen es alto, que es
  justo el caso de la app (DraftKings, 7.7%). Si agregás un mercado
  nuevo, sacale el margen con `devigShin` — no con una normalización a
  mano. En mercados de dos opciones Shin no corrige nada y devuelve el
  proporcional: eso es correcto, no un atajo.

- **Antes de calibrar algo, medir si ya sirve.** Se pasaron tres semanas
  midiendo calibración del modelo de goles y ninguna midiendo si daba
  plata. Cuando por fin se midió, daba -6.18% de ROI. Ver `TRASPASO.md`.

## El rediseño, ya cerrado

La interfaz nueva **es** `index.html` desde el 2026-08-18. Se construyó
aparte, como `app.html`, y recién cuando estuvo terminada y verificada
reemplazó a la vieja. Lo que queda vigente de aquellas reglas:

- El motor matemático (Dixon-Coles, Kelly, combinadas) se **copia**, no se
  reescribe: está validado y reescribirlo arriesga errores numéricos
  silenciosos. `doble_via.py` existe para probar que no se movió.
- Referencia del motor verificado: tag `motor-verificado` (versión con ancla
  doméstica: tag `motor-v2-ancla`).
- Trabajo previo descartado: rama `ui-antigravity` (no borrar, es respaldo).
- La región `/* ==== INICIO RESOLUCION ==== */` de `index.html` la lee
  `test_registro.js` tal cual. Si la movés o le cambiás el nombre, la suite
  deja de encontrarla — es a propósito.

## Para evitar el problema que originó este archivo

Una herramienta por área. Si vas a usar otra IA en paralelo, que sea
para algo distinto (backend vs. interfaz vs. contenido) o en una rama
aparte. Dos herramientas sobre el mismo archivo terminan pisándose.

## Verificar antes de dar algo por hecho

Este proyecto tiene historial de afirmaciones que resultaron falsas al
chequearlas contra la API real (que `/teams/{id}/schedule` traía todas
las competiciones — no; que no había cuotas históricas — sí las hay en
football-data.co.uk). Si vas a afirmar algo sobre los datos, medilo.
