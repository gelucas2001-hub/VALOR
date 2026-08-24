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
| `historico.py` | Baja y normaliza el historial largo de football-data.co.uk (6310 partidos de arg, 5544 de bra, con cuota de cierre de Pinnacle). Es la base de las mediciones serias | A mano |
| `medir_historico.py` | El modelo contra el mercado sobre TODO el historial, walk-forward. La vara es la tasa base, no 'siempre un tercio' | A mano, cada tanto |
| `medir_clv.py` | Si la línea se mueve hacia nosotros. Es lo único que dice si hay ventaja sin esperar cientos de apuestas. Necesita que el cron junte fotos primero | A mano, cada tanto |
| `medir_arbitros.py` | Si el árbitro mueve las tarjetas. Prueba de permutación: puede decir que no, y hoy dice que no | A mano, cada tanto |
| `medir_analisis.py` | Si la `inclinacion` del análisis acierta, y si la regla de alineación suma o resta. Correr después de cada fecha | A mano |
| `calibrar_ligas.py` | Cuánto vale cada liga sudamericana | A mano, cada tanto |
| `data/*.json` | Lo escribe el cron. **No editar a mano** | Nadie |
| `data/planteles.json` | Jugadores con números (PJ, goles, peso goleador). Lo escribe el cron | Nadie |
| `data/estadisticas.json` | Promedios por partido de cada equipo (remates, córners, posesión, tackles). Sale del mismo `/summary` que ya se pedía: cero pedidos extra | Nadie |
| `data/cuotas.json` | Historia de la cuota de mercado, foto por corrida. Se acumula: ESPN la borra cuando el partido termina | Nadie |
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
