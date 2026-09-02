# VALOR — reglas del repo

Leé esto antes de tocar nada. Existe porque tres herramientas de IA
editaron `index.html` en paralelo sin saber una de la otra, y el
resultado fue trabajo perdido y funcionalidad borrada.

## Antes de empezar

**Antes de tocar el motor, los datos o el análisis, leé las secciones
relevantes de `TRASPASO.md`.** Es el informe de traspaso del proyecto:
qué salió mal antes, qué está resuelto, y en qué orden seguir. Señala
todo lo demás — `DESIGN.md`, el spec, y `docs/design-handoff/` (una
entrega de diseño ya verificada, con una funcionalidad nueva lista para
implementar). Para trabajo de interfaz/presentación nueva, este archivo
basta. Si `TRASPASO.md` y este archivo se contradicen en algo, gana
`TRASPASO.md`: es el más nuevo. No es necesario releerlo entero en cada
tarea: leé las secciones que aplican a lo que vas a tocar.

## Qué es cada cosa

| Archivo | Qué hace | Quién lo toca |
|---|---|---|
| `actualizar.py` | Baja datos de ESPN y calcula λ. Corre solo, 2 veces por día, vía GitHub Actions | Con cuidado — es el motor |
| `index.html` | La app. **Desde el 2026-09-01 son tres capas por partido —Veredicto · Lectura · Datos— en vez de siete pestañas**, más Fecha/Registro/Método abajo. Ver TRASPASO §18 | Una herramienta por vez — ver abajo |
| `test_registro.js`, `test_alineacion.js` | Suites que leen el `index.html` publicado, no una copia | Correr después de tocar la app |
| `test_alineacion.js` (ver arriba) | Desde el rediseño mira las tres capas: `capaVeredicto`, `capaLectura`, `datosEquipos`, `datosJugadores`, `datosReferencia`, `renglonPartido`. Si movés una pantalla, el contrato se muda con ella — un test que mira una función muerta da verde sin proteger nada | Correr después de tocar la app |
| `test_ejes.js` | El contrato de lectura por ejes (TRASPASO §17). Lee la región marcada `/* ==== INICIO EJES ==== */` del `index.html` publicado, igual que `test_registro.js`. Ata las dos reglas duras: un eje sin `medido_por` no puede declarar más que `sin_medir`, y solo `con_plata` puede llevar apuesta — o sea, solo eso puede pintarse de mostaza. Sin estos tests las reglas son disciplina; con ellos son estructura | Correr después de tocar los ejes |
| `doble_via.py` | Compara el motor de Python contra el de JavaScript | Correr después de tocar el motor |
| `data/resultados.json` | Marcadores finales que escribe el cron. Hace exacto el cruce del Registro | Nadie |
| `TRASPASO.md` | Informe de traspaso — léelo primero | A mano, mantenerlo al día |
| `docs/design-handoff/` | Entrega de diseño de Claude Design, verificada | No editar; es referencia |
| `backtest.py` | Calibración contra resultados | A mano |
| `barrido_lambda.py` | Barrido out-of-sample walk-forward de los parámetros que tocan λ (`escala_goles`, `VIDA_MEDIA_DIAS`, `rho`, `prior`), con train/test temporal, midiendo goles (over 1.5/2.5/3.5, ambos marcan, distribución completa) y el 1X2 como control. **Medido el 2026-08-29: producción está en el óptimo; ninguna variante mejora robustamente OOS — NO tocar λ salvo fuente nueva. Ver TRASPASO.md.** `python barrido_lambda.py arg [--fast]` | A mano, si alguien propone retocar λ |
| `medir_sesgo.py` | Cuánto nos apartamos de la línea del mercado | A mano, antes y después de tocar el modelo |
| `medir_vs_mercado.py` | Brier contra la cuota de cierre real | A mano |
| `medir_calibracion.py` | Cuando la app dice 70%, ¿pasa el 70%? Mide la calibración de lo que la app ya publicó, partido por partido — a diferencia de `backtest.py`, que reconstruye lo que el modelo habría dicho. Faltaba en esta tabla hasta el 2026-08-24 | A mano, cada tanto |
| `historico.py` | Baja y normaliza el historial largo de football-data.co.uk: 6310 partidos de arg, 5544 de bra, **4180 de eng y 3857 de fra** (agregadas el 2026-08-25), con cuota de cierre de Pinnacle. Es la base de las mediciones serias. Lee los **dos** formatos de la fuente — un archivo único para las ligas nuevas, uno por temporada para las clásicas de Europa. Solo el segundo trae estadísticas por partido, y esa es la razón por la que en Inglaterra se distinguen los equipos y en Argentina no | A mano |
| `equipos.py` | Cruza los nombres de equipo del CSV de football-data con los de ESPN, que es lo unico que ataba las dos fuentes. **Solo por igualdad exacta despues de normalizar** — nada de parecido ni prefijos: en Ligue 1 juegan Paris Saint-Germain y Paris FC a la vez, y el CSV tiene a los dos (395 partidos contra 34). Un cruce difuso les funde la historia y eso no se ve como un error, se ve como datos. De los 15 nombres que no coincidian, 12 los resuelve el `shortDisplayName` que ESPN ya publica y uno el apostrofo: la tabla a mano es de **tres** entradas. Cruza 19 de 20 en Inglaterra y 17 de 18 en Francia; los dos que faltan son ascendidos sin historia en primera | A mano, cuando cambia una liga |
| `expediente_estadisticas.py` | El expediente objetivo del **mercado de estadisticas**, para la segunda skill. Mismo molde que `expediente.py` y misma razon: lista blanca, y lo que no esta no viaja — sin λ, sin rho, sin cuotas, y **sin los corners/faltas/tarjetas que esperamos nosotros**, que son salida del modelo aunque no lo parezcan. Lo que si manda es lo que cada equipo produce **y lo que concede**, el split local/visita, la serie por jugador (no el promedio) y cuanto se le cree a cada metrica. `python expediente_estadisticas.py <id>` | A mano, antes de correr la skill |
| `mercado_extra.py` | La cuota que ESPN NO publica, de Bet365 vía odds-api.io: 17 a 19 lineas de gol, ambos marcan, doble oportunidad cotizada, corners del partido **y por equipo con los dos lados**, y la escalera de remates de ~50 jugadores por partido. ESPN daba UNA casa y tres cosas (1X2, goles 2.5, handicap); todo el resto de 'Otros mercados' salia del modelo sin nada real contra que compararse. Cruza los partidos por **fixture** (liga + fecha + los dos equipos), nunca por nombre: ellos escriben 'CA River Plate (ARG)' y tienen ademas 'Racing Club De Lens'. 46 de 46 cruzan unico. **Sin `ODDS_API_KEY` no hace nada y la app queda igual** | A mano / lo llama el cron |
| `historia_equipos.py` | Escribe `data/historia_equipos.json`: la historia larga de cada equipo (296 partidos contra los 5 del cache), cruzada a ids de ESPN con `equipos.py`. Guarda `n`, `suma` y `suma2` por equipo y metrica — de ahi salen media y varianza exactas, y pesa 18 KB en vez de 80.000 numeros sueltos. **Se corre A MANO**: el cron NO lo baja, serian 22 pedidos a football-data dos veces por dia para un archivo que cambia una vez por semana. Volver a correrlo cuando cambian los ascensos y descensos | A mano, cada tanto |
| `medir_historico.py` | El modelo contra el mercado sobre TODO el historial, walk-forward. La vara es la tasa base, no 'siempre un tercio' | A mano, cada tanto |
| `medir_devig.py` | Qué método de quitar el margen de la casa acierta. Medido el 2026-08-25 sobre 11.854 partidos con cuota de cierre real: gana Shin, y gana más cuanto más alto el margen — que es la condición de la app. Antes la app usaba el proporcional y las mediciones usaban Shin | A mano, cada tanto |
| `medir_encogimiento.py` | Si conviene calmar al modelo mezclándolo con la tasa base, y cuánto. Medido el 2026-08-25 fuera de muestra: en arg sí (k=0.20, cuatro errores estándar); en bra no, y con la ventana correcta empeora. **Medido y NO se aplica**: mejora el Brier de verdad, pero cambia el 43% de las marcas sin que el set nuevo rinda mejor (−2.35% ±18.78, puro ruido). Ver TRASPASO.md. Mejorar el Brier no es ganar plata | A mano, cada tanto |
| `medir_condicional.py` | Si el modelo sabe de goles **condicionado al resultado**, cuando ya está medido que en general no. Es la pregunta 1 del "escenario coherente" (gana X + ambos marcan + más de 2.5 como una sola lectura). Medido el 2026-08-31 sobre 28.881 partidos de seis ligas: **no**. El aporte condicionado va de −2.0% a +3.4% con e.e. de 0.6 a 1.1, y solo es positivo en fra y jpn, donde el modelo ya sabía algo de goles sin condicionar. El delta contra el modelo sin condicionar es enorme (+44.8%) y no significa nada: condicionar corrige el NIVEL de goles del subconjunto, que la tasa base ya conocía. Ver TRASPASO.md §16 | A mano, cada tanto |
| `medir_dominio.py` | El eje Dominio: si el ancla por equipo de `historia_equipos.json` sirve en las CINCO métricas o solo en córners, que era la única medida. Le deja a cada pronóstico elegir su propio `k` en train — con una vara de `k` prestado el ancla gana por construcción. Medido el 2026-08-31 en eng y fra: contra la media de la liga, remates +9.9% y al arco +7.3% rinden **más que córners** (+4.8%), que era lo único que se miraba. Contra el caché corto el ancla gana claro en fra y no es concluyente en eng (1.6 e.e., contra los 4.5 que reportaba el número viejo con vara peor). **En faltas EMPEORA** (−0.199 ±0.072): once temporadas son un ancla vieja para una métrica que deriva con el reglamento. Ver TRASPASO §17 addendum. `python medir_dominio.py eng` | A mano, cada tanto |
| `medir_props.py` | El eje Jugadores contra **PLATA**, al precio real de Bet365 — la primera vez que se mide dinero acá, cuando `medir_jugadores.py` solo medía calibración. Usa la escalera de precios entera y las varias fotos por partido que `props_jugadores.json` venía acumulando. Cruza nombres **solo por igualdad exacta**: los que no cruzan son en su mayoría otros jugadores (Clever Ferreira contra Pablo Ferreira), y un cruce difuso los funde. Trae su propia vara: la **deriva** de los escalones que NO se apuestan, sin la cual un CLV positivo puede ser la casa achicando el margen sobre la hora. Trae ademas dos controles que el error estandar no da: **dejar un partido afuera por vez** (las apuestas de un mismo partido no son independientes) y **cuantas lineas quedaron clavadas** (ahi el CLV es cero por construccion). Medido el 2026-08-31 sobre 10 partidos: el CLV daba +4.28% ±2.14 sobre la deriva y parecia la primera señal positiva del proyecto; **los controles la desarmaron** — un solo partido la sostenia (+0.17% sin el) y 11 de 19 lineas no se habian movido. **No hay señal, queda el instrumento.** Ver TRASPASO §17 addendum 3 | A mano, cada tanto — y de nuevo cuando haya más muestra |
| `medir_ajuste_jugador.py` | Si el RIVAL o el EQUIPO mueven los remates de un jugador. Sale de una pregunta de Lucas, y apunta a la metrica peor calibrada que tenemos (remates, 2.09 veces el ruido). Hoy el numero de jugador no mira contra quien juega: `esperado_jugador()` encoge la serie hacia el promedio del puesto y nada mas, aunque a nivel EQUIPO la app si ajusta por lo que concede el rival. Medido el 2026-08-31 walk-forward: **los dos ajustes empeoran** — por rival −0.1317 ±0.0476, por cuota del equipo −0.4765 ±0.1495, y el dejar-uno-afuera no cruza el cero. Multiplicar un numero ruidoso por otro ruidoso suma varianza sin sumar señal. **No prueba que el rival no importe: prueba que ESTA estimacion del rival hace daño.** Ver TRASPASO §17 addendum 6 | A mano, si alguien propone ajustar el numero de jugador |
| `foto_props.py` | Saca una foto de las lineas de jugador **pegada al inicio** del partido, que es lo que le faltaba al CLV para tener resolucion: el 2026-08-31 el 58% de las apuestas tenian el precio clavado entre nuestras fotos porque el cron corre 09:00 y 15:00 y los partidos arrancan hasta las 21:00. Pide **solo los partidos que arrancan en las proximas 2 horas** — entre cero y cinco pedidos, contra los ~55 que cuesta una corrida entera de `actualizar.py`. Descarta el que YA empezo: ahi la cuota es en vivo y es otro mercado. Lo corre `.github/workflows/foto_props.yml` cada hora de 07:00 a 21:00 ARG. No toca `partidos.json` ni recalcula nada | Lo llama el cron; a mano con `--ver` para ver que haria |
| `medir_ejes.py` | En qué EJE del partido sabemos más: Brier por mercado, walk-forward, contra la tasa base **de ese mismo mercado** (un mercado donde el 80% de las veces pasa lo mismo tiene Brier bajo sin que el modelo aporte nada). Es la base sobre la que se decidió qué recomienda la escalera. Medido: en goles el aporte va de −0.9% a +0.4% — nada. Por eso la escalera solo recomienda Resultado. `python medir_ejes.py arg` | A mano, cada tanto |
| `medir_roi.py` | La regla de valor de la app contra **PLATA**, liga por liga: ROI, drawdown y Sharpe walk-forward. Reemplaza al script ad-hoc de Node que midió el único ROI que existía (arg, −3.27% ±6.19) y que no había quedado en el repo. Medido: la regla resta en arg (−9.17%) y en bra (−9.13%), y por eso **la app no marca valor en esas dos ligas**; jpn da +2.78% ±7.67 | A mano, cada tanto |
| `medir_apertura.py` | Mide al precio al que se apuesta de verdad —la **apertura**— y no solo al cierre, que es el precio más difícil que existe y al que la app nunca apuesta. De paso destraba el CLV **hacia atrás**: TRASPASO §6sexdecies decía que no se podía, y era cierto para ESPN y falso para football-data, que publica apertura y cierre. Con 362 apuestas el CLV ya es concluyente mientras el ROI sigue en ±14 — es el instrumento correcto para evaluar un cambio del modelo sin esperar mil apuestas. Toma `casa` como parámetro y mide Pinnacle **y** Bet365: antes de proponer medir 'a la casa blanda', fijate que ya lo hace. **Medido el 2026-09-02: contra Bet365 el CLV es cero, y contra Pinnacle en eng da −1.62% ±0.82 — dos errores estándar NEGATIVO, el único número del conjunto que sale del ruido.** Ese mismo set tiene un ROI de +2.79% ±14.82: es la racha que la regla del CLV manda ignorar, no una señal. Ver TRASPASO §20 | A mano, cada tanto |
| `barrido_valor.py` | Si existe **alguna** ventana de ventaja que dé plata, con train/test temporal. `VALOR_MIN`/`VALOR_MAX` se habían elegido mirando cuántas marcas producían, no cuánta plata daban. Medido el 2026-08-30: **39 ventanas, ninguna positiva fuera de muestra**. Es un resultado definitivo en el sentido útil — no hay que seguir buscándole la vuelta a los umbrales | A mano, si alguien propone mover los umbrales de valor |
| `medir_compresion.py` | Si el modelo aplasta los extremos hacia el promedio. Salió de una objeción de Lucas sobre Unión–Sarmiento (esperaba 2.70 goles, terminó 4-1). Encontró que el modelo estiraba el rango de goles **2.7 veces** más que la realidad — el hallazgo más importante del 2026-08-30. Ya corregido en las cuatro ligas. Ver TRASPASO §14 | A mano, cada tanto |
| `barrido_escala_lambda.py` | Corrige esa exageración de λ y mide si sirve, con train/test temporal. De acá sale `corregir_escala()` de `actualizar.py` | A mano, si se vuelve a tocar λ |
| `barrido_diferencia.py` | El segundo eje del mismo defecto: si el modelo exagera la **diferencia** entre los dos equipos, no el total. La corrección de escala mantiene la proporción entre local y visitante, así que este eje se mide aparte. Medido: el defecto aparece **solo en arg**, y solo ahí se aplicó — 27 partidos por equipo a una vuelta contra 38 de Brasil | A mano, cada tanto |
| `barrido_remates.py` | Si conviene estimar las fuerzas con **remates** además de goles. Medido: mejora +0.8 errores estándar, no alcanza. Camino cerrado | A mano, cada tanto |
| `medir_bajas.py` | Si faltar goleadores predice marcar menos — la hipótesis sobre la que descansaría conectar la skill de análisis a λ (hoy solo emite un veto de 1 bit). Medido: r = −0.06 ± 0.14, sin señal. **No conectar la skill a λ sin dato nuevo** | A mano, cada tanto |
| `medir_consenso.py` | La estrategia SIN modelo: el consenso del mercado contra una casa sola (arXiv 1710.02824). Medido: Bet365 no se desvía del consenso, y con el alpha del paper da cero apuestas. Camino cerrado | A mano, cada tanto |
| `probar_odds_api.py` | Si conviene cambiar DraftKings —la única casa que expone ESPN— por Pinnacle. Prueba de The Odds API. Necesita `ODDS_API_KEY`. **Ojo con la ilusión de que acá hay plata**: el ROI de `medir_roi.py` YA está medido a cierre de Pinnacle, así que el −9% no es margen tirado. Bajar el margen no devuelve puntos que no se estaban perdiendo; lo que sí hace es que el −9% publicado sea optimista respecto de lo que paga la app. Ver TRASPASO §20 | A mano |
| `medir_corners.py` | El mercado de córners contra **plata**, no contra calibración. Baja la línea de cierre real de DraftKings vía el endpoint `propBets` de ESPN, le quita el margen y mide ROI walk-forward. Medido el 2026-08-25 sobre 81 líneas: **la casa pone la línea justo en el punto de la moneda** — el mercado le gana a tirar una moneda por 0,0008 de Brier y cobra 8,4% de margen. El ROI daba +11,2% ±13,9% sobre 41 apuestas: ruido, harían falta ~300. El de **por equipo** sí se sabe: atraso +0,0205 ±0,0093 (2,2 errores estándar detrás) y ROI negativo en los seis umbrales — le apostamos el promedio de la liga a una casa que distingue equipos | A mano, cada tanto |
| `medir_clv.py` | Si la línea se mueve hacia nosotros. Es lo único que dice si hay ventaja sin esperar cientos de apuestas. Necesita que el cron junte fotos primero | A mano, cada tanto |
| `medir_discriminacion.py` | ¿Tenemos opinión propia por equipo, o publicamos el promedio de la liga? Calibrar no alcanza: un pronóstico que le da a todos el promedio calibra perfecto y no sirve para apostar. Medido el 2026-08-25: con 4 partidos por equipo solo posesión y tackles superan el techo de falsa señal — y ninguna de las dos tiene mercado | A mano, cada tanto |
| `medir_lineas.py` | Si el mercado de estadísticas (córners, tarjetas, remates) dice la verdad. Mide calibración, no plata: no hay cuotas históricas de córners. Medido el 2026-08-24: córners bien, faltas con sesgo de 9 puntos | A mano, cada tanto |
| `medir_jugadores.py` | Si las líneas de JUGADOR (remates, al arco) dicen la verdad. Compara el desvío contra el ruido, no contra cero: con 618 casos un modelo perfecto ya desvía 3.5 puntos. Medido el 2026-08-24: remates mal (2.09x el ruido), al arco regular, goles y asistencias bien | A mano, cada tanto |
| `medir_arbitros.py` | Si el árbitro mueve las tarjetas. Prueba de permutación: puede decir que no, y hoy dice que no | A mano, cada tanto |
| `medir_analisis.py` | Si la `inclinacion` del análisis acierta, y si la regla de alineación suma o resta. Correr después de cada fecha | A mano |
| `calibrar_ligas.py` | Cuánto vale cada liga sudamericana | A mano, cada tanto |
| `data/*.json` | Lo escribe el cron. **No editar a mano** | Nadie |
| `data/planteles.json` | Jugadores con números (PJ, goles, peso goleador, **dorsal**) y la **serie** por jugador. Desde el 2026-09-01 trae además la clave `once`: los **once que arrancaron** en el último partido de cada equipo, con dorsal, puesto fino de ESPN (`CD-L`, `AM-R`) y el esquema que ESPN publica (`4-2-3-1`). Sale del mismo `/summary` que ya se pedía — cero pedidos nuevos. Antes la cancha dibujaba un once inferido con una nota que decía que ESPN no publica el titular: es cierto para un partido por jugarse y falso para uno jugado. **Sin `once`, la cancha se comporta igual que antes.** Lo escribe el cron | Nadie |
| `data/estadisticas.json` | Promedios por partido de cada equipo (remates, córners, posesión, tackles). Sale del mismo `/summary` que ya se pedía: cero pedidos extra | Nadie |
| `data/cuotas.json` | Historia de la cuota de mercado, foto por corrida. Se acumula: ESPN la borra cuando el partido termina | Nadie |
| `data/props_jugadores.json` | Historia de las líneas de jugador de Bet365 (remates, al arco), foto por corrida. Se acumula por el mismo motivo que `cuotas.json`, pero acá es más grave: para ligas domésticas, `v3/events` de odds-api.io solo lista partidos pendientes — una vez jugado el partido, ni el `id` del evento queda disponible para pedirlo hacia atrás. Si no se guarda antes, se pierde para siempre | Nadie |
| `data/historia_equipos.json` | El ancla de cada equipo en corners, remates, al arco, faltas y tarjetas, desde 11 temporadas de football-data. Lo escribe `historia_equipos.py`; `actualizar.py` lo lee si esta. **Si no esta, la app se comporta exactamente como antes de que existiera** — arg.1 y bra.1 no lo tienen porque la fuente no trae estadisticas de esas ligas | A mano, via ese script |
| `data/calibracion_jugadores.json` | Cuánto le erra cada línea de jugador. Lo escribe `medir_jugadores.py`, y la app lo lee para decir en pantalla de qué fiarse | A mano, vía ese script |
| `data/analisis.json` | Análisis cualitativo, carga manual. El cron **nunca** lo toca | A mano |
| `data/analisis_estadisticas.json` | El **segundo mercado** del partido: córners, remates, al arco, faltas, tarjetas y que jugador las produce. Lo escribe la skill `valor-analisis-estadisticas` y llena la `lectura` de los ejes Dominio y Jugadores. Carga manual; el cron **nunca** lo toca | A mano |

## Las DOS skills del partido, y cuál escribe qué

Desde el 2026-08-31 un partido tiene **dos mercados** y una skill para
cada uno. No se pisan, y mezclarlas hace que el usuario lea dos veces
lo mismo:

| skill | expediente | escribe | alimenta |
|---|---|---|---|
| `valor-analisis-inclinacion` | `expediente.py` | `data/analisis.json` | la inclinación y el eje Contexto |
| `valor-analisis-estadisticas` | `expediente_estadisticas.py` | `data/analisis_estadisticas.json` | la lectura de los ejes Dominio y Jugadores |

La segunda tiene tres reglas duras que salen de mediciones, no de
opiniones: **no escribe una cifra de remates** como pronóstico (la
métrica está medida y se desvía 2.09 veces el ruido), **no le atribuye
nada al árbitro** (efecto medido por permutación: cero), y **no habla
de quién gana** — ese es el otro mercado.

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
- **Una clave de API se lee del entorno, nunca del repo.** Hasta el
  2026-08-26 la regla era "sin claves", y se eliminó a propósito: la
  cuota de córners, de jugador y de las líneas de gol que ESPN no
  publica sale de odds-api.io, que pide clave. Lo que queda en pie es
  cómo se maneja: `os.environ`, secret de GitHub Actions, y **sin la
  clave todo tiene que seguir andando igual que antes** — la fuente
  nueva agrega mercados, no reemplaza los que ya funcionan.
- **No cambiar el contrato de `data/partidos.json`.** Agregar campos sí; renombrar o cambiar tipos rompe el frontend.
- **Tocar una constante del modelo solo entra si una medición lo sostiene.** Un ajuste se aprueba por una medición walk-forward fuera de muestra que mejore la métrica relevante (ROI/Brier/calibración) con su incertidumbre — no por tunear hacia atrás ni para que un número dé mejor. Si una medición no mejora, el hallazgo es que no mejoró; pero eso no prohíbe probar: hay scripts para medir, usalos, y documentá el resultado (ver `medir_encogimiento.py`).
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

## Las tres capas del partido (2026-09-01)

Un partido se abre en **Veredicto** (el único lugar del producto donde
aparece una recomendación), **Lectura** (la narrativa con el número que
la sostiene en el mismo bloque) y **Datos** (exploración libre, sin
veredictos). Abajo, en la barra: Fecha · Registro · Método.

Dos reglas duras que salieron de ahí y no se negocian:

- **El dorado (`--mostaza`) vive solo en Veredicto.** Ningún dato crudo
  lo usa nunca. Si el mismo color dijera "acá el precio está a favor" y
  "este número es importante", dejaría de decir la primera — que es la
  única que cuesta plata.
- **Un mercado que no se recomienda se muestra igual, con el motivo**
  (SIN VENTAJA · SIN PRECIO · SIN DATO · NO OPINAMOS). Un mercado que no
  aparece se lee como un mercado que nadie miró.

El detalle de qué absorbió cada capa, qué se borró y a dónde fue cada
cosa está en TRASPASO §18.

## El rediseño anterior, ya cerrado

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
aparte. Dos herramientas sobre el mismo archivo terminan pisándose. La
regla de exclusión es sobre el MISMO archivo: está bien que trabajen en
áreas separadas o en ramas distintas de forma coordinada, siempre que
nunca dos editen el mismo archivo a la vez.

## Verificar antes de dar algo por hecho

Este proyecto tiene historial de afirmaciones que resultaron falsas al
chequearlas contra la API real (que `/teams/{id}/schedule` traía todas
las competiciones — no; que no había cuotas históricas — sí las hay en
football-data.co.uk). Si vas a afirmar algo sobre los datos, medilo.
