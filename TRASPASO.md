# VALOR — informe de traspaso

**Para:** la IA que arranque el proyecto de cero en una carpeta nueva.
**Escrito:** 2026-08-17. **Repo de origen:** `gelucas2001-hub/VALOR`.

> **Actualización 2026-08-18 — leer antes que el resto del documento.**
> Después de escrito esto, se hizo el brainstorm visual que la sección
> 11 (Fase 1, pasos 5-8) pedía como pendiente — **ya no está pendiente.**
> Se hizo en Claude Design, con opciones comparadas y elegidas por
> Lucas, y produjo dos cosas que este documento todavía no menciona:
>
> 1. **El elemento firma está resuelto** (una V con barras ascendientes,
>    no el cupón). Ver la sección corregida más abajo y `DESIGN.md`.
> 2. **Un handoff completo con una funcionalidad nueva, verificada y
>    lista para implementar: la resolución automática del registro.**
>    Vive en `docs/design-handoff/` — está en el repo, no hace falta ir
>    a buscarlo a ningún lado externo. Ver la sección 6bis, nueva.
>
> La Fase 1 de la sección 11 (brainstorm) está **completa**. Empezá
> directo por la Fase 2 (docs/design-handoff/ + reglas) — ver el orden
> corregido al final de la sección 11.

> **Actualización 2026-08-19 — leer antes que el resto del documento.**
> La Fase 4 (sección 11, contenido) **ya no es un hueco**: hay una skill
> versionada en el repo, `.claude/skills/valor-analisis-inclinacion/`,
> que hace el research y escribe `inclinacion`/`contexto`/`veredicto`
> siguiendo la regla de alineación. **Se edita ahí, no en Claude.ai.**
> `data/analisis.json` tiene 12 partidos cargados (era 0). Ver la
> sección 10 corregida y la 6quinsexies para el resto: qué se agregó
> (`forma_general`, "Otros mercados", `divergen()`).
>
> **Actualización 2026-08-20 — el plantel ya no es un hueco.** El cron
> escribe `data/planteles.json` (42 equipos, 1152 jugadores con partidos
> jugados, goles y peso goleador), la pestaña Plantel lo muestra con la
> cancha del handoff, y `expediente.py` se lo pasa a la skill. Con eso,
> la skill pasó a **v2.0**: una lectura por equipo (campos `local` y
> `visitante`, nuevos en `analisis.json`) y bajas pesadas contra el
> plantel en vez de enumeradas. Ver la sección 6septies.

> **Actualización 2026-08-24 — la más importante, leer antes que todo
> lo demás.** Se midió por primera vez si el producto sirve, y la
> respuesta cambió la prioridad del proyecto.
>
> **1. Nunca se había medido la plata.** Durante tres semanas se midió
> calibración, sesgo, árbitros y análisis. Nunca ROI. El motivo estaba
> escrito en `backtest.py`: *"ESPN borra las cuotas cuando el partido
> termina, así que no hay precios históricos con los que simular
> apuestas"*. Era cierto cuando se escribió y dejó de serlo cuando
> apareció `historico.py` (6310 partidos de arg.1 con cuota de cierre
> real de Pinnacle). Nadie volvió a hacer la pregunta. **Si leés que
> algo "no se puede medir", chequeá la fecha de esa afirmación.**
>
> **2. El modelo estaba en terreno negativo en Argentina.** Aplicando
> la regla real de la app (EV ≥ 4%, cuota ≤ 4.5), sobre 977 apuestas
> desde 2022: **−6.18% de ROI**. Y en tasa de acierto, 40.8% contra el
> 43.2% de apostar siempre al local. El modelo restaba.
>
> **3. La causa: el ajuste arrancaba de cero cada enero.**
> `resultados_temporada()` pide del 1/1 a hoy, así que
> `fuerzas_equipos()` nunca veía más de un año calendario. Se agregó
> `historia_reciente()` (5 temporadas, cacheadas en disco) y se subió
> `VIDA_MEDIA_DIAS` de 45 a 300. **Los dos cambios solo sirven juntos**
> — hay una tabla en el comentario de la constante que lo demuestra, y
> el par lo eligieron arg y bra por separado con datos anteriores a
> 2022. Resultado: el ROI pasó de **−6.18% a −0.94%**.
>
> **4. Lo que eso significa, sin adornos.** −0.94% con z = −0.2 es
> *indistinguible de cero*. El modelo dejó de perder; no empezó a
> ganar. Hasta que `medir_clv.py` junte datos, no hay ninguna evidencia
> de ventaja sobre el precio.
>
> **5. Una pista que se persiguió y resultó falsa.** Usar la
> probabilidad de cierre de Pinnacle y apostar a la mejor cuota del
> mercado daba +16.6% en bra.1 con z = +3.9. Contra una casa concreta
> (Bet365) la misma regla dispara **11 veces en catorce años**: toda la
> ventaja vivía en que `MaxC` es el *máximo* de treinta y pico de casas,
> y un máximo está inflado por serlo. **No es una estrategia.** Queda
> escrito para que nadie vuelva a entusiasmarse con ese número.
>
> **6. El mercado de estadísticas ya se mide** (`medir_lineas.py`, y
> tiene pestaña propia desde hoy — vivía enterrado en Plantel). Sobre
> 179 partidos: córners calibra bien (3.5 puntos de desvío), **faltas
> tiene sesgo sistemático de ~9 puntos siempre para el mismo lado** y
> remates de ~7 para el otro. De cinco métricas que la app deja
> apostar, una está bien.
>
> **7. Accesibilidad de la interfaz, corregida.** Había 151 nodos de
> texto por debajo de 11px (el más chico, 7px), nueve casos de
> contraste por debajo del mínimo (el peor, 1.77:1) y todos los botones
> por debajo de 44px táctiles. Ver `DESIGN.md` para la rampa de grises
> nueva y por qué no contradice el "apagado" de una apuesta perdida.
>
> **Lo que queda sin medir y es el candidato serio:** el torneo
> argentino se juega por grupos, a una sola vuelta, con 28-30 equipos y
> tabla de promedios. `fuerzas_equipos()` asume que todos juegan contra
> todos, así que las fuerzas de equipos de zonas distintas no están en
> la misma escala. Nunca se probó.

> **Actualización 2026-08-30 — redirección de producto, leer antes que
> el resto del documento.** `data/presentacion-claude.md` (visión de
> producto) y `data/PROBLEMAS.md` (estado medido, con números) se
> escribieron para contrastar la app de hoy contra hacia dónde debería
> ir. Redefinen la prioridad de todo lo que sigue en este documento —
> ver la sección 13, nueva, al final.
>
> **En una frase:** la escalera de recomendaciones hoy ordena por
> probabilidad de mercado, no por valor — muestra siempre 3 tarjetas
> (a veces triple under, la misma idea tres veces) y no está atada a la
> lectura 1X2 propia (caso Lyon: local 59.8%, el pick más confiado de
> la fecha, y la escalera puso tres unders sin una sola apuesta a que
> gana el local). Nada de esto es del motor: es lógica de selección y
> presentación en `index.html`, y es lo primero a corregir. El motor no
> tiene ventaja demostrada (ROI walk-forward −3.27%±6.19, el intervalo
> incluye cero) — eso sigue abierto y ningún rediseño de presentación
> lo resuelve.

Este documento existe porque Lucas decidió rehacer el proyecto desde
cero, pero **el motor matemático y el pipeline de datos están validados
y medidos, y tirarlos sería destruir la única parte que costó semanas
de medición.** Lo que se rehace es la **interfaz**. Lo demás se
**hereda**.

Leé este archivo entero antes de escribir una línea de código.

---

## 0. Lo primero: qué salió mal, para no repetirlo

Esto no es autocrítica decorativa. Es la parte más útil del documento.

**El error central: se escribió la interfaz copiando maquetas aprobadas
en vez de diseñarla.** Las maquetas eran comps de 320px hechas para
*decidir una dirección*, no para ser el diseño final. Copiarlas 1:1 dio
una app correcta y genérica. Cuando el usuario dijo "le falta trabajo",
la respuesta fue parchar (agregar un elemento firma, después ajustar
espaciados) en vez de rehacer el proceso. Parchar dos veces sobre una
base copiada no arregla una base copiada.

**Errores concretos que costaron tiempo y no deben repetirse:**

1. **Afirmar sin medir.** Se afirmó que `/teams/{id}/schedule` traía
   todas las competiciones de un equipo. Es falso. Se afirmó que no se
   podía medir contra el mercado retroactivamente. Es falso
   (football-data.co.uk publica cuotas de cierre gratis). **Regla: si
   vas a afirmar algo sobre los datos, medilo primero.**

2. **Elegir constantes a ojo.** El spec pedía marcar "valor" a partir de
   3 puntos porcentuales de diferencia contra el mercado — pero el mismo
   documento medía que el modelo se aparta 9-15pp en promedio. O sea: el
   umbral estaba *dentro del propio error*. **Regla: toda constante de
   producto se barre sobre datos reales antes de fijarla.**

3. **Comparar mediciones entre corridas distintas.** El cron reescribe
   `data/partidos.json` dos veces por día. Medir "antes" a la mañana y
   "después" a la tarde compara partidos distintos. El mismo código dio
   +12.3pp y +8.7pp el mismo día. **Regla: para comparar antes/después,
   congelá un snapshot y usá el mismo archivo en las dos mediciones.**

4. **Mostrar capturas que el usuario no ve.** Se sacaron capturas, se
   miraron, y se le describieron al usuario sin mandárselas. El usuario
   no tenía forma de evaluar nada. **Regla: si evaluás algo visual,
   mandale el archivo.**

5. **Skills instaladas y no usadas.** Había skills de brainstorming y
   diseño instaladas que nunca se invocaron; se fue directo a escribir
   código. **Regla: si hay una skill que cubre la tarea, usala antes de
   empezar, no después de que el resultado no guste.**

6. **Tres IAs editando el mismo archivo en paralelo.** Claude Code,
   Antigravity y otra terminal tocaron `index.html` sin saber una de la
   otra. Se perdió trabajo y se borró funcionalidad. **Regla: una
   herramienta por área, o ramas separadas.**

---

## 1. Qué es VALOR

Una PWA de pronósticos de fútbol argentino y sudamericano, con un motor
de value betting abajo sosteniéndola.

**La distinción de producto más importante, y la que más vueltas
costó:** son dos preguntas distintas.

- *"¿Qué va a pasar en este partido?"* → el **pronóstico**. Es la
  promesa principal. Se mide por **tasa de acierto**.
- *"¿A qué conviene apostar?"* → el **valor**. A veces coincide con el
  pronóstico, muchas veces no. Se mide por **rentabilidad**.

**VALOR es un pronosticador, con un motor de value betting abajo. No al
revés.** La razón es de producto: presentarse como herramienta de value
betting obliga al usuario común a entender EV, banca y varianza antes de
obtener algo útil. Presentarse como pronosticador no le exige nada.

**Pero nunca se contradicen en pantalla.** Un intento anterior mostraba
"creemos que gana River, pero jugá a Racing a 5.75". Lucas lo rechazó
así: *"Es como decir, es probable que gane River pero paga poco, así que
preferimos que juegues una ruleta rusa a Racing."* Tenía razón, y el
problema de fondo es peor: ese 27% se apoyaba en un modelo que medimos
equivocándose 9-15pp.

**Alcance:** Liga Profesional Argentina, Copa Argentina, CONMEBOL
Libertadores, CONMEBOL Sudamericana. Volumen real: ~5 partidos por fecha
en Liga, hasta 8-10 en día fuerte de copas.

**Audiencia:** hoy es para Lucas. Pensado para que abrirlo a más gente
no requiera rehacer nada, pero sin construir multi-usuario todavía.

---

## 2. Lo que se hereda tal cual — NO REESCRIBIR

Estos archivos están validados y medidos. **Copialos, no los
reescribas.** Reescribir el motor arriesga errores numéricos
silenciosos: un signo cambiado en Dixon-Coles no tira una excepción,
solo da probabilidades sutilmente mal para siempre.

| Archivo | Qué hace |
|---|---|
| `actualizar.py` | Baja datos de ESPN y calcula λ. Corre solo, 2×/día, en GitHub Actions. **Es el motor.** |
| `backtest.py` | Calibración contra resultados reales |
| `medir_sesgo.py` | Cuánto nos apartamos de la línea del mercado, por competición |
| `medir_vs_mercado.py` | Brier contra la cuota de cierre real |
| `calibrar_ligas.py` | Cuánto vale cada liga sudamericana |
| `.github/workflows/actualizar.yml` | El cron |
| `data/*.json` | Los datos. Los escribe el cron. **No editar a mano.** |
| `icons/`, `manifest.json` | PWA |

**Referencia del motor verificado:** tag `motor-verificado`
(commit `539588f`, 2026-08-16).

**Rama de respaldo, no borrar:** `ui-antigravity` — trabajo previo
descartado que se conserva por si algo hace falta.

---

## 3. El pipeline de datos

### Cómo corre

GitHub Actions, `.github/workflows/actualizar.yml`:

- **Cron:** `0 12 * * *` y `0 18 * * *` UTC → 09:00 y 15:00 hora
  Argentina (UTC-3). Más `workflow_dispatch` para dispararlo a mano.
- **Runner:** `ubuntu-latest`, Python **3.12**.
- Corre `python actualizar.py`, hace `git add data/`, commitea como
  `valor-bot` y pushea.
- Necesita `permissions: contents: write`.

### Restricciones duras — no negociables

- **`actualizar.py` usa SOLO biblioteca estándar.** Corre en GitHub
  Actions sin `pip install`. Nada de `requests`, `numpy`, `pandas`.
- **Sin claves de API.** Todo sale de endpoints públicos.
- **No cambiar el contrato de `data/partidos.json`.** Agregar campos sí;
  renombrar o cambiar tipos rompe el frontend.

### De dónde salen los datos

**ESPN, API pública no documentada.** Dos hosts, con fallback: algunas
redes bloquean el primero (Akamai) y el segundo sirve las mismas
respuestas.

```
https://site.api.espn.com
https://site.web.api.espn.com      (fallback)
```

Dos prefijos de ruta:

```
apis/site/v2/sports/soccer    → scoreboard, teams/{id}/schedule, summary, teams/{id}
apis/v2/sports/soccer         → standings
```

Endpoints concretos en uso:

| Endpoint | Para qué |
|---|---|
| `{SITE}/{slug}/scoreboard?dates={desde}-{hasta}` | Partidos y **cuotas de DraftKings** |
| `{SITE}/{slug}/teams/{id}/schedule` | Partidos jugados: condición, goles, rival |
| `{SITE}/{slug}/teams/{id}` | Campo `defaultLeague` → la liga local del equipo |
| `{SITE}/{slug}/summary?event={id}` | Córners, faltas, tarjetas. **Un pedido por partido — es caro, por eso está cacheado** |
| `{CORE}/{slug}/standings?season={año}` | Tabla de posiciones |

Manda un `User-Agent` de navegador; sin eso responde mal.

**Slugs de competición:**

```python
"arg.1"                    Liga Profesional Argentina   rho 0.05  conf 75
"conmebol.libertadores"    CONMEBOL Libertadores        rho 0.00  conf 65
"conmebol.sudamericana"    CONMEBOL Sudamericana        rho 0.00  conf 65
"arg.copa"                 Copa Argentina               rho 0.00  conf 60
```

**Segunda fuente, para medir contra el mercado:**
`https://www.football-data.co.uk/new/ARG.csv` — CSV gratis, sin clave,
6.295 partidos de Liga Profesional desde 2012 con **cuota de cierre**.
No cubre copas.

### Trampa conocida al cruzar fuentes

Los nombres de equipo difieren entre ESPN y football-data, y **el cruce
difuso es peligroso**: hace matchear "Independiente Rivadavia" con
"Independiente" y ensucia resultados en silencio. `medir_vs_mercado.py`
tiene una tabla explícita de 30 equipos y **corta con error si falta
alguno**. Mantenerlo así.

---

## 4. El modelo matemático

### Núcleo

**Dixon-Coles sobre Poisson.** Se estiman λ (goles esperados) de local y
visitante, se arma la matriz de marcadores 0-9 × 0-9, y de ahí sale la
probabilidad de cualquier mercado sumando celdas.

La corrección `tau` de Dixon-Coles ajusta los cuatro marcadores bajos
(0-0, 0-1, 1-0, 1-1) que Poisson puro estima mal. El parámetro `rho`
está calibrado por competición (ver tabla de slugs arriba).

**Advertencia registrada:** `rho = 0.00` en las tres copas es un valor
**por defecto no validado**, no un resultado medido. Queda pendiente
calibrarlo — ahora hay 889 partidos de muestra y una vara para medirlo.

### Ajuste de fuerzas

`fuerzas_equipos()` estima ataque y defensa por equipo, iterativamente,
con dos mecanismos:

- **Decaimiento temporal:** `VIDA_MEDIA_DIAS = 45`. Un partido de hace 45
  días pesa la mitad que uno de hoy.
- **Regularización por prior:** `PRIOR_FUERZA = 3` "partidos fantasma"
  que empujan hacia un valor de referencia.
- `MIN_PARTIDOS_FUERZA = 3` — con menos que eso, el equipo no se estima.

### El problema grande que se resolvió: el ancla doméstica

**Síntoma medido:** el modelo tenía sesgo sistemático hacia el local en
copas — Libertadores **+12.3pp**, Copa Argentina +5.5pp, Sudamericana
+0.4pp, Liga Profesional −2.3pp. Caso extremo: modelo 52.0% vs mercado
22.6%.

**Causa raíz:** las fuerzas se ajustaban *solo con partidos de la misma
competición*. Con 6 partidos por equipo en copas, la regularización
empujaba todo al promedio: el modelo creía que Cerro Porteño y Palmeiras
eran parecidos, y la localía terminaba decidiendo.

**Solución en dos partes:**

1. **Ancla doméstica.** Un equipo llega a la Libertadores con la fuerza
   que se ganó en su liga local, donde tiene ~23 partidos en vez de ~6.
   Esa fuerza reemplaza al 1.0 hacia el que empujaba la regularización.
   La liga local se descubre con `defaultLeague` de `/teams/{id}`
   (verificado: Palmeiras→`bra.1`, Cerro Porteño→`par.1`, Liga de
   Quito→`ecu.1`). `MIN_PARTIDOS_ANCLA = 8`.

   Se implementa como **ancla del prior, no como Elo**: Elo resume la
   fuerza en un solo número, y el modelo de goles necesita ataque y
   defensa por separado.

2. **Factores de calidad de liga.** El ancla sola **empeoró**
   Sudamericana (magnitud 20.8 → 24.7pp), porque un 1.30 de ataque en
   Brasil y un 1.30 en Paraguay no son lo mismo. `calibrar_ligas.py`
   estima un multiplicador por liga usando 805 cruces de copa de 3
   temporadas. `MIN_CRUCES = 40` como piso: sin ese piso, `bra.2` daba
   1.352 con 20 cruces — más alto que `bra.1` (1.235), o sea el modelo
   "aprendía" que la segunda división brasileña es mejor que la primera.

**Resultado medido:** sesgo de Libertadores **+8.7pp → +3.5pp**.

### La vara: cuánto sabemos realmente

`medir_vs_mercado.py`, evaluación **walk-forward** (las λ de cada partido
se calculan solo con partidos anteriores a esa fecha — nunca ve el
resultado que predice), contra la cuota de cierre real:

```
Brier (más bajo = mejor)
  no saber nada (1/3)   0.667
  nuestro modelo        0.645
  cuota de cierre       0.623
```

**Traducción: el mercado mejora 0.044 sobre no saber nada; nosotros
mejoramos 0.022, o sea el 48% de eso. Le seguimos perdiendo al cierre.**

Esto no es un fracaso, es el número real y honesto. La app lo dice en la
pantalla de Método en vez de esconderlo.

### Otras piezas del motor

- **Devig proporcional.** La cuota cruda implica probabilidades que suman
  ~1.077 (**margen de la casa: 7.7% mediano**, medido sobre DraftKings).
  Compararse contra cuota cruda haría ver ventaja donde solo hay
  comisión. Siempre descontar el margen primero.
- **EV y Kelly.** Fracción de Kelly escalada por confianza de la
  competición. Tope de stake al 4% de banca.
- **Probabilidad conjunta exacta para combinadas.** Dos patas del mismo
  partido están correlacionadas; multiplicar las probabilidades por
  separado da un número falso. Se suma sobre la matriz. **Medido: la
  corrección supera 2pp en solo 4 de 16 combinadas, con máximo 6.2pp** —
  o sea que importa, pero menos de lo que se suponía.
- **Registro de pronósticos.** `registrar_pronosticos()` guarda λ, rho y
  mercado devigado por partido, y resuelve los terminados. Alimenta el
  marcador de acierto propio vs. acierto del mercado.

### Evaluado y descartado (no volver a intentarlo sin fuente nueva)

- **Lesiones de ESPN:** el endpoint responde **vacío** para equipos
  argentinos. No hay fuente gratuita. El contexto de bajas es carga
  manual.
- **xG de ESPN:** `/summary` trae `expectedGoals` **solo por jugador
  destacado**, no por equipo. Sumar dos o tres líderes no da el xG del
  equipo. Lo que sí viene completo por equipo: remates, remates al arco,
  posesión.
- **API-Football:** es paga. Descartada por la restricción de costo cero.
- **Ventaja de localía individual por equipo:** ruido con la muestra
  disponible.

### Pendientes reales del modelo

1. **Calibrar `rho` para copas** (hoy 0.00 sin validar).
2. **Validar `VIDA_MEDIA_DIAS` y `PRIOR_FUERZA`** con train/test split —
   **HECHO el 2026-08-29** con `barrido_lambda.py` (walk-forward
   temporal, train <2022 / test ≥2022, sobre el historial largo con
   cuota Pinnacle): producción está en el óptimo, ninguna variante
   mejora robustamente OOS ni en goles ni en 1X2. **No tocar λ salvo
   fuente nueva.** Ver el Addendum con esa fecha.
3. **Descontar partidos afectados por expulsión** — idea del propio
   Lucas, tras notar que Palmeiras empató 1-1 con un jugador menos desde
   el minuto 70.
4. **Usar remates además de goles** para estimar fuerza. Es una pregunta
   empírica, ahora respondible porque existe la vara del punto anterior.
5. **Calibrar la probabilidad antes de publicarla.** Hoy se publica la
   cruda. Lo correcto sería `cruda → calibración → publicada`. **No se
   implementó por muestra insuficiente:** las franjas de
   `data/backtest.json` tienen entre 1 y 27 partidos. Corregir con un bin
   de 1 partido agrega ruido y disfraza de precisión algo que no la
   tiene. **Condición para activarlo: al menos 30 partidos por franja.**
   El barrido del 2026-08-29 aporta evidencia en contra de "el modelo
   erra grueso": sobre 2559 partidos de arg en test el over 2.5 está
   bien calibrado (0.357 real vs 0.375 predicho). El único sesgo visible
   es el 1X2 de favoritos sobreconfiados, y `medir_encogimiento.py` ya
   mostró que encoger hacia la tasa base NO rinde OOS en arg.

---

## 5. Las reglas de recomendación (medidas, no opinadas)

Esta sección es el corazón del producto y **cada número acá se barrió
sobre los 30 partidos reales antes de fijarse**. Se reprodujo por dos
caminos independientes — un script Python sobre `backtest.py` y el motor
en JavaScript del frontend — con resultado idéntico (20 marcas sobre 90
picks, 2 alertas sobre 25 partidos con cuota).

### Regla 1 — Escalera de riesgo

Cada partido ofrece **la misma lectura a tres niveles de riesgo**. No son
tres opiniones distintas: son tres formas de jugar la misma lectura.

| Franja | Probabilidad |
|---|---|
| Lo más probable | 68-93% |
| Intermedia | 45-68% |
| Arriesgada | 12-45% |

**Verificado: las tres franjas tienen candidato en 30 de 30 partidos.**

(Un intento anterior etiquetó como "lo más seguro" a un 54%. Eso es cara
o cruz, no seguridad.)

### Regla 2 — Los escalones son pronósticos; el valor se marca aparte

Las apuestas seguras casi nunca tienen valor: el margen de 7.7% se come
la ventaja justo en las cuotas bajas. Si se filtrara cada escalón por
valor, solo sobreviviría el arriesgado — que es exactamente el problema
que Lucas rechazó. Entonces: los escalones responden *"¿qué es lo más
probable?"*, y **la marca de valor aparece solo donde además el precio
está a favor**.

### Regla 3 — Alineación: nada contradice nuestra propia lectura

Si el modelo señala "valor" en algo que va en contra de lo que creemos
que va a pasar, eso no es valor: es error del modelo. No se muestra.

**Para que esto no sea circular, la lectura debe venir de donde el
modelo no llega — el análisis cualitativo.** Si la lectura la produjera
el propio modelo, filtrar por alineación sería el modelo dándose la
razón a sí mismo. De ahí se sigue: **solo se marca valor en partidos con
análisis cargado.**

**Corrección 2026-08-30 — esto YA ESTÁ hecho, y la nota de hoy temprano
que decía "pendiente de implementar" estaba mal.** Se escribió sin
chequear el código primero — la regla que este mismo documento repite
("medir antes de afirmar"). `divergen()` (`index.html`, desde el
2026-08-19, §6quinsexies) ya compara `inclinacionDe()` contra
`lectura().lean` y, cuando difieren, la pestaña Pronósticos lo dice
explícito: *"Los números crudos del modelo dan más chance [X] arriba,
pero nuestro análisis vio algo que los números solos no ven, y se
inclina [Y]. Son dos lecturas distintas a propósito..."* — con tests
(`test_alineacion.js`, "divergen() detecta cuando el análisis humano no
coincide con el modelo"). Y hay una capa más fina y más nueva,
`senalDividida()`, que separa la contradicción de "desarrollo" (ritmo
goleador, ambos marcan) mercado por mercado, no solo por dirección
1X2 — con su propia batería de tests. La regla de fondo sigue siendo
la misma (seguir sin marcar valor contra la lectura propia): lo que
esta corrección aclara es que el *decir por qué* ya estaba resuelto,
no pendiente. Ver la sección 13 para el estado actualizado del orden
de trabajo.

### Regla 4 — Umbral de cuota, no cuota de referencia

Mostrar "@2.20 de DraftKings" es una trampa: DraftKings no opera en
Argentina, el usuario va a Betsson, encuentra 2.05 y no sabe si sigue
conviniendo. Se muestra **"conviene si te pagan más de X"**.

**X no es la cuota justa: es la justa más el margen de seguridad.** A la
justa exacta la ventaja es **cero**.

```
umbral = (1 / probabilidad) × (1 + 0.04)
```

### Regla 5 — Selección dentro de cada franja

La franja sola no alcanza. Si dentro de "lo más probable" se elige el
porcentaje más alto, el sistema recomienda siempre lo mismo y algo
inservible: verificado, los más probables eran "local no pierde por 2+"
(91.4%) y "más de 0.5 goles" (89.4%) — mercados que pagan 1.09.

1. **Lista corta de mercados que la gente juega y entiende:** 1X2, doble
   oportunidad (las tres), más/menos de 1.5-2.5-3.5 goles, ambos marcan
   sí/no. **Quedan fuera** marcador exacto, hándicaps y las líneas de 0.5
   goles (pagan 1.05-1.12: ruido disfrazado de apuesta).
2. **Dentro de la franja, el de mayor ventaja sobre el mercado**, pidiendo
   al menos 2pp — **pero solo dentro de la banda creíble (≤12pp)**. Sin
   ese techo la regla elegía cosas como Botafogo–Cienciano con **+53pp**
   de diferencia, que no es una oportunidad encontrada sino el modelo
   equivocado: elegir por ahí es elegir justo el pick con más chance de
   estar mal.
3. **Si ninguno califica, el más cercano al centro de la franja**,
   mostrado sin marca de valor.

**Verificado: la regla reparte entre 13 mercados distintos sobre 90
picks.** No repite siempre lo mismo.

### Constantes de valor — barridas, no elegidas

```
VALOR_MIN = 0.06     piso de la banda de mostaza
VALOR_MAX = 0.12     techo
ALERTA_MIN = 0.10    el mercado nos saca esto en nuestra propia lectura
MIN_EV = 0.04
EV_ABSURDO = 0.25    arriba de esto no se recomienda monto
MAX_ODDS = 4.5
```

**Por qué el piso es 6pp y no 3pp:** el spec pedía 3pp, pero el modelo se
aparta 9-15pp de la línea limpia en promedio. Un piso de 3pp está
*dentro del propio error*. Barrido real:

```
piso    picks marcados   % de picks   partidos con marca
 3pp          29             32%          19 de 30
 4pp          25             28%          18 de 30
 5pp          23             26%          17 de 30
 6pp          20             22%          16 de 30   ← elegido
 7pp          18             20%          15 de 30
 8pp          15             17%          12 de 30
```

**Una sola marca de valor por partido**, la de mayor ventaja. Sin esa
regla quedaban dos escalones dorados en el mismo partido, y una señal
que aparece en todos lados no informa nada.

**Control de cordura:** Método dice que arriba de +25% de EV lo más
probable es que nuestro λ esté mal. Herramientas debe respetarlo y **no
recomendar monto** en ese caso, o la app se desmiente a sí misma en dos
pantallas.

### 5bis. El barrido rehecho — y el problema que encontró

Medido el 2026-08-18 con `node barrer_valor.js`, sobre el snapshot
congelado de 34 partidos. Las funciones salen de `index.html`, no de una
copia.

**La forma del barrido se reproduce.** Al 3pp da 32% de los picks
marcados, idéntico a lo que decía la tabla original medida sobre 30
partidos:

```
piso    marcados   % de picks   partidos con marca
 3pp        33         32%        21 de 34
 4pp        32         31%        21 de 34
 5pp        32         31%        21 de 34
 6pp        27         26%        19 de 34   ← el que rige
 7pp        22         22%        17 de 34
 8pp        16         16%        13 de 34
10pp         8          8%         8 de 34
```

**Dos números del TRASPASO se confirman y uno no.** La alerta se
enciende en el **7%** de los partidos con cuota (decía 8%). El margen
de las casas da mediana **7,68%** (decía 7,7%). Pero el apartamiento
del modelo respecto de la línea limpia da **media 8,5%, mediana 7,3%,
percentil 90 15,3%** — el documento decía "9-15pp en promedio", y la
media queda apenas por debajo de ese rango.

**El problema, y es el mismo que motivó subir el piso de 3pp a 6pp:**
la mediana del apartamiento es **7,3pp** y el piso es **6pp**. O sea
que el piso actual también está por debajo del apartamiento típico.
El argumento que descartó el 3pp le aplica igual al 6pp.

**No se tocó la constante.** Elegir 8pp porque "queda arriba de la
mediana" sería exactamente el error que el repo prohíbe: mover un
número para que la medición se vea bien. Y además la pregunta está mal
planteada — apartarse del mercado no es lo mismo que equivocarse. La
única forma honesta de fijar el piso es medir **si los picks marcados
ganan más que los no marcados**, y para eso hacen falta resultados.

**Ese camino ahora existe:** la resolución automática del registro
(sección 6ter) acumula resultados sola. Cuando haya volumen, el piso
se decide con datos de cobro, no con distancia al mercado. Hasta
entonces el 6pp se queda, declarado como provisorio.

### Regla de ritmo

**Siempre hay pronóstico, no siempre hay recomendación.** Habrá días sin
nada que recomendar, y está bien — pero la app nunca debe quedarse sin
opinión, o el usuario deja de abrirla.

**Corolario importante:** un partido sin análisis cargado **muestra la
escalera como pronóstico, sin ninguna marca de valor** — no una pantalla
vacía. Con `analisis.json` vacío, la alternativa dejaría la app entera
sin contenido.

---

## 6. La línea gráfica

**Dirección:** prensa deportiva argentina vieja — tapas de El Gráfico,
cupones de Prode, programas de cancha.

**Explícitamente rechazado por Lucas, no volver a proponerlo:**
- crema + serif + terracota ("vintage americano" genérico)
- negro + verde ácido
- negro + celeste + insignias + "PRO AI" (cliché de SaaS de IA)

### Paleta — un color, un solo trabajo, siempre

| Color | Hex | Trabajo, único |
|---|---|---|
| Fondo | `#1B1611` | Casi negro tibio, noche de cancha. **No** negro frío de terminal |
| Hueco | `#171310` | Más hondo: masthead, cajas hundidas |
| Panel | `#221C15` | Tarjeta |
| Tinta | `#EEE3CE` | Texto, datos neutros, y **estado seleccionado** |
| Mostaza | `#D6963A` | **Valor**: acá hay algo mejor que el precio. Y nada más |
| Terracota | `#C06848` | **Alerta**: cuidado, esto no rinde. Y nada más |
| Salvia | `#6B7A5E` | Decorativo. Solo el filete bajo el masthead |

Escala de grises tibios para jerarquía de texto: `#D8CDB4`, `#B8AD95`,
`#8C7F68`, `#6E6350`, `#5C513F`. Líneas: `#241D16`, `#2A2318`.

**Reglas duras:**
- Nunca un tercer color funcional.
- Nunca semáforo verde/amarillo/rojo.
- **Nunca mostaza para selección de UI.** El día activo es tinta, no
  mostaza. Confundir "seleccionado" con "hay valor" es el error que más
  caro paga el usuario.
- En Historial el "color" viene de **intensidad tipográfica** — ganado en
  tinta plena, perdido casi apagado — nunca de mostaza ni terracota.

### Tipografía

- **Anton** — nombres de equipo, títulos de liga, wordmark. Tapa de
  revista deportiva.
- **JetBrains Mono** — todo número que se compare o se confíe.
- **Archivo** — cuerpo, UI, prosa de análisis.

### Chrome y densidad

- **Pestañas silenciosas:** línea inferior + color de texto. Nunca botón
  con caja.
- **Filas planas** en listas largas. Nada de tarjeta dentro de tarjeta.
- **El bloque de análisis es tipografía sola, sin caja** — nota de
  revista, no tarjeta de dashboard.
- Grano/textura solo en el masthead, nunca sobre filas de datos.
- La curva acumulada del Registro es la única línea curva de la app.

### El elemento firma — estado: RESUELTO (2026-08-18)

El spec lo definía como "la pieza memorable de VALOR, todavía sin
encontrar". Se intentó una idea acá mismo, en este repo — **el cupón de
Prode** — y no convenció en dos ejecuciones distintas (ver el hallazgo
2 de la sección 0, más abajo, que sigue siendo válido como lección de
proceso aunque la firma ya esté resuelta).

**Se resolvió en Claude Design, con un brainstorm real: cuatro
candidatos aislados, comparados antes de integrar ninguno.** Ganó una
**V** con cuatro barras ascendientes en verde oliva recortadas dentro
del trazo derecho — la escalera de riesgo, hecha símbolo. El cupón no
volvió a proponerse.

**El SVG real y la explicación completa están en `DESIGN.md`, sección
"Marca".** No la reinventes ni la vuelvas a buscar: está verificada
(extraída del prototipo final, no retipeada) y aprobada por Lucas.

Un detalle de proceso que vale la pena repetir en el futuro: la entrega
del handoff **cambió de marca entre una versión y la siguiente**
(troquelado → V) y el README del bundle no se actualizó — seguía
llamando "decisión final" a la versión vieja. Se corrigió a mano. **Si
volvés a pedir un handoff externo, confirmá que la documentación
coincide con el prototipo antes de darla por buena.**

---

## 6bis. El handoff de Claude Design — verificado, listo para implementar

`docs/design-handoff/VALOR.dc.html` + `docs/design-handoff/README.md`
son la entrega final de una ronda de diseño hecha en Claude Design,
conectado a este mismo repo por GitHub. **No es un mockup a medias: se
verificó línea por línea, no se aceptó de palabra.** Lo que sigue es lo
que se comprobó corriendo código, no leyendo promesas:

- **El motor matemático no fue tocado.** Se extrajeron las funciones
  (`matrix`, `sumIf`, `ev`, `kelly`, `tau`, `pois`) del prototipo y las
  del `index.html` del repo, se corrieron ambas sobre los 30 partidos
  reales: **diferencia máxima 0** en las 90 probabilidades resultantes.
  Motor idéntico, bit a bit.
- **La resolución automática del registro es una funcionalidad nueva,
  con lógica probada.** Hoy el registro depende de que el usuario marque
  a mano si acertó — y eso nunca se llena. La solución: cruzar cada
  apuesta anotada contra `formH`/`formA` de partidos futuros del mismo
  equipo (el marcador aparece ahí, un refresco después de jugarse).
  Verificado con Node contra los datos reales: **sin los dos candados
  del algoritmo, 3 de 30 partidos cruzan con el resultado equivocado
  (fase de grupos, mismos rivales repetidos). Con los candados, 0 de
  30.** Está documentado con el algoritmo completo, los dos candados
  explicados, y por qué hacen falta.
- **Los tokens de diseño (color, tipografía, espaciado, movimiento)
  están medidos, no elegidos a ojo** — ocho rondas de exploración con
  Lucas eligiendo en cada una.
- **Encontraron un hueco real en los datos que nadie había visto:** la
  tabla del Grupo A de Libertadores trae 4 equipos y le falta uno de los
  que juega ese partido (Cruzeiro). Verificado contra `data/partidos.json`
  real. Diseñaron Posiciones y Plantel para declarar el hueco en vez de
  esconderlo.

**Orden de implementación recomendado, por valor:**

1. ~~**Resolución automática del registro primero.**~~ **HECHO
   (2026-08-18).** Está en `index.html`, en la región marcada
   `/* ==== INICIO RESOLUCION ==== */`, con `test_registro.js` (17
   casos, `node test_registro.js`) corriendo contra el snapshot
   congelado `tests/partidos-snapshot.json`. Ver la sección 6ter.
2. ~~**El rediseño visual completo** de las cuatro pantallas.~~
   **HECHO (2026-08-18).** Las cuatro están construidas contra el
   prototipo. Ver la sección 6quater.

**Una limitación del archivo, no del diseño:** `VALOR.dc.html` usa un
motor de plantillas propio de Claude Design que no corre completo fuera
de su entorno (un solo error de consola conocido: la curva del Registro
no reemplaza `{{ reg.puntos }}`). Es un documento para **leer**, no para
ejecutar y copiar. La lógica de JS común (motor, `TESTS`, `resolver`,
`buscarResultado`) sí se transplanta literal — el propio README lo
señala.

**Antes de escribir código de la fase visual: confirmá que `README.md`
sigue describiendo lo que hay en `VALOR.dc.html`.** Ya pasó una vez que
no coincidían (ver la nota en la sección anterior sobre la marca).

---

## 6ter. Resolución automática — implementada, y lo que se midió

Implementada el 2026-08-18 siguiendo el algoritmo del handoff **sin
cambiarlo**. Lo que sigue es lo que se comprobó corriendo código.

**Reproduce la medición del handoff.** Sobre los 34 partidos de
`data/partidos.json` del 2026-08-17 (el handoff midió sobre 30): sin el
candado de fecha cruzan mal **3** — Independiente Rivadavia vs
Fluminense, Cerro Porteño vs Palmeiras, Club Olimpia vs Vasco da Gama.
Con los dos candados, **0**. El handoff decía 3 y nombraba Cerro
Porteño vs Palmeiras: coincide.

**La orientación del marcador se verificó sin fixtures a mano.** Un
partido puede aparecer en dos historiales independientes (el del local
y el del visitante, este último con el marcador al revés). De 78
partidos que aparecen en las dos fuentes, 75 se jugaron una sola vez y
**coinciden sin una sola excepción**. Ese test es el que atrapa un
error de signo.

**Hallazgo nuevo, no estaba en el handoff:** los otros 3 son cruces
**repetidos con el mismo local**. Olimpia y Vasco se cruzaron tres
veces dentro de los últimos cinco de Olimpia, dos de ellas en Brasil
(0-0 y 3-0). El desempate por `k` se queda con el más reciente, que es
lo correcto en ese caso, pero **es una grieta real del cruce por
historial**: si anotás el primero de dos partidos con el mismo local y
después se juega el segundo, el cruce puede traer el marcador del
segundo. Pasa solo en fase de grupos y solo con localía repetida.

**La solución de fondo ya estaba señalada por el handoff, y conviene
hacerla:** que `actualizar.py` persista los marcadores finales en
`data/resultados.json` (`{matchId: "2-1"}`). Eso vuelve el cruce exacto
y hace innecesarios los dos candados. **Dejar el cruce por historial
como respaldo**, no borrarlo: cubre los partidos anteriores a que ese
archivo exista.

**Contradicción de documentación, sin resolver:** `DESIGN.md` dice
"mostaza = valor, y nada más" y "terracota = alerta, y nada más"; el
handoff le asigna mostaza a *ganada* y terracota a *perdida* en el
Registro. Se siguió el handoff porque `index.html` ya usaba esos dos
colores para ganada/perdida en los botones del Registro desde antes.
La regla de `DESIGN.md` sobre intensidad tipográfica habla del
**Historial** (la pestaña del partido), que es otra pantalla. Vale
aclararlo en `DESIGN.md` antes de la fase visual.

---

## 6quater. La fase visual — hecha, y contra qué se construyó

**El README del handoff está desactualizado en dos puntos. Se verificó
contra `VALOR.dc.html` antes de escribir código, y manda el prototipo:**

1. El README dice que la portada lleva el **wordmark troquelado**. El
   prototipo (`:29-31`) usa **la V**, y reserva el troquelado para
   `REGISTRO` y `MÉTODO` (máscaras `tq-rg`, `tq-mt`). Coincide con
   `DESIGN.md`. Es el mismo desajuste que ya había pasado con la marca:
   el README no se actualizó cuando el prototipo cambió.
2. El README dice "seis pestañas" y después lista cinco, llamando "el
   resumen" a Pronósticos. El prototipo (`:1536`) tiene las seis con
   Pronósticos por nombre, como esta sección 7.

**Decisión de color tomada por Lucas:** el resultado de una apuesta
(ganada/perdida) **no se pinta** — va por intensidad tipográfica, como
Historial. Mostaza y terracota se quedan exclusivas de valor y alerta.
La única excepción es la curva acumulada, que sigue en mostaza porque
es la trayectoria, no una apuesta puntual. Está documentado en
`DESIGN.md § Resultado ≠ valor`, con la tabla de qué cambió.

**Corrección al hallazgo de datos del handoff — medido.** El handoff
decía haber encontrado un hueco: «la tabla del Grupo A de Libertadores
trae 4 equipos y le falta uno de los que juega ese partido
(Cruzeiro)», y diseñó Posiciones y Plantel para declararlo.
**Verificado sobre los 34 partidos: Cruzeiro está en el Grupo D de la
misma Libertadores.** Ese partido es un cruce entre grupos, no un
agujero de datos.

De 24 partidos donde uno de los dos equipos no figura en la tabla:

```
19   el equipo está en otro grupo/zona de la MISMA competición   → tabla completa, cruce de llave
 5   no figura en ninguna tabla de esa competición               → hueco real
```

En Liga Profesional el patrón es sistemático: Zona A y Zona B son
tablas separadas, así que el rival de la otra zona nunca va a estar.
La nota del handoff, tal cual, habría dicho «la fuente devolvió estas
15 líneas y ninguna es suya» en partidos donde la fuente está
perfecta. **Se partió en dos casos** (`quienFalta()` en `index.html`):
«Juegan cruzado» cuando el rival está en otro grupo, «Falta uno» solo
cuando de verdad no está. Los tres casos verificados en navegador:
Flamengo–Cruzeiro da cruzado, Tolima–Independiente del Valle da falta,
Lanús–Independiente no da nota.

**Regla violada en el código viejo, corregida:** la tabla de Posiciones
resaltaba el puesto de tus equipos en **mostaza**. `DESIGN.md` dice
«Nunca mostaza para selección de UI» y lo llama «el error que más caro
paga el usuario». Ahora va en tinta, como el prototipo.

**Lo que NO se copió del prototipo, y por qué:** las casillas de cuota
de `index.html` tienen una barra de tinta que dibuja la probabilidad con
escala fija al 70%. El prototipo usa casillas planas. Se conservó la
barra: es información real que el prototipo no tiene, y borrarla sería
perder funcionalidad para parecerse más a una maqueta.

**Verificado en navegador, a 375px, con datos reales:** cero errores de
consola; las cuatro pantallas y las seis pestañas sin desborde
horizontal — medido intentando `scrollTo(500,0)` y confirmando que
`scrollX` queda en 0, no solo leyendo `scrollWidth`, que reporta de más
mientras la tira de pestañas todavía está animando.

---

## 6quinquies. El cambio de guardia — hecho (2026-08-18)

La interfaz nueva dejó de llamarse `app.html`: **es `index.html`.** El
archivo viejo (negro frío, cian, verde semáforo) se borró; su contenido
sigue en el historial de git si alguna vez hace falta.

Se hizo con `git rm index.html && git mv app.html index.html`. **Ojo con
la historia:** como `index.html` ya existía, git no lo anota como rename
sino como borrado más modificación. `git log --follow index.html`
devuelve la historia de la interfaz **vieja**, no la de esta. Para la de
la app actual: `git log -- app.html`, hasta el commit del cambio.

**Lo que arrastró el cambio de nombre**, porque cuatro scripts leen el
HTML publicado en vez de una copia — que es exactamente por qué se
enteraron del rename:

| Archivo | Qué lee |
|---|---|
| `test_registro.js` | La región `/* ==== INICIO RESOLUCION ==== */` |
| `test_alineacion.js` | Las funciones de lectura y sello |
| `barrer_valor.js` | Las constantes de valor que rigen hoy |
| `doble_via.py` | El motor, para compararlo contra el de Python |

Más `CLAUDE.md`, `DESIGN.md` y este documento. Los de
`docs/design-handoff/` y `docs/superpowers/specs/` se dejaron como
estaban: son actas de una entrega cerrada y dicen `app.html` porque eso
era cierto cuando se escribieron.

**Verificado después del cambio:** `node test_registro.js` 22 ok,
`node test_alineacion.js` 19 ok, `python doble_via.py` diferencia máxima
6,7e-16. Y `manifest.json`, que se había quedado con `#070B14` — el azul
de la línea descartada — ahora arranca en `#1B1611`: la pantalla de
carga del PWA ya no destella el color viejo.

---

## 6quinsexies. Lo que se agregó el 2026-08-19

**Problema de fondo que motivó todo esto:** la forma reciente de un
equipo se calculaba *por competición*. Un equipo con partidos
infrecuentes en copa (fase de grupos, 1 partido cada 3-4 semanas)
mostraba una "forma" de meses de antigüedad el día del análisis, sin
nada de su actualidad real en el torneo local.

- **`forma_general()`** (`actualizar.py`) — junta la forma de todas las
  competiciones de un equipo y ordena por fecha real, no por
  competición. Para equipos en Libertadores/Sudamericana, reutiliza los
  resultados de liga doméstica que `ancla_de()` **ya pedía** para el
  ancla — sin pedido de red nuevo. Verificado en vivo: Cerro Porteño
  (Paraguay) pasó de mostrar forma vieja/duplicada a forma real y
  fresca de `par.1`. 23/23 tests en `test_forma.py`.
- **"Otros mercados"** (`index.html`, `otrosMercados()`) — la escalera
  de riesgo solo mostraba 3 mercados; si los tres caían en la misma
  familia (ej. los tres de Goles), el usuario no veía 1X2 ni Ambos
  Marcan. La sección nueva muestra **todos** los mercados calculados,
  reusando los mismos valores — nunca agrega una segunda marca dorada.
- **`divergen()`** (`index.html`) — si la lectura del modelo (`lectura().lean`)
  y la inclinación humana (`inclinacionDe()`) señalan direcciones
  distintas, la pestaña Pronósticos ahora lo dice explícito en vez de
  mostrar los dos sin explicar por qué no coinciden.
- **La skill de análisis pasó a vivir en el repo**, versionada:
  `.claude/skills/valor-analisis-inclinacion/SKILL.md`. Se corrigieron
  dos errores reales que Lucas encontró leyendo el contenido generado
  (no un chequeo automático): una racha de Platense mal leída — el DT
  nuevo ya había jugado dos partidos, no "seguía acomodándose" — y una
  búsqueda floja que no identificó a Coudet como DT de River. Se
  agregó **principio I** a la skill: cruzar cualquier afirmación de
  racha/momento contra el propio `formH_general`/`formA_general` del
  expediente antes de escribirla, porque ese dato ya está cargado y
  fechado — no hace falta que lo confirme una búsqueda externa que
  puede estar vieja o incompleta.

---

## 6septies. El plantel y la skill v2.0 (2026-08-20)

Todo esto salió de una sola auditoría de Lucas: leyó el análisis de
River–Independiente Santa Fe y dijo que solo nombraba bajas, que la
mayoría no valían nada (Acuña y Driussi hacía más de un mes que
faltaban; Arambarri había jugado un partido), y que del rival no sabía
nada — "¿cómo juega? ¿viene bien? ¿es fuerte de local?".

Resultaron ser **tres causas distintas**, y esto importa porque
arreglar solo la última no hubiera servido:

1. **Un bug de cableado.** La app mostraba `formH`/`formA` (filtrado
   por competencia, viejo en copa) donde ya existía `formH_general`.
   River aparecía con cinco resultados de la fase de grupos mientras el
   dato fresco —cuatro derrotas 0-1— estaba en el mismo archivo, sin
   usar. Dos líneas en `tabHistorial()` y `tarjeta()`.
2. **Faltaba el dato para pesar.** Sin partidos jugados ni goles por
   jugador, "no está Montiel" y "no está Arambarri" se escriben igual.
   Ahora el cron escribe `data/planteles.json`.
3. **La skill nunca pidió describir el juego.** Recién con (2) resuelto
   tenía sentido tocarla.

**`data/planteles.json`** — 42 equipos, 1152 jugadores, ~300 KB. Sale
de `/{slug}/teams/{id}/roster`, que medido en vivo devuelve 38-40
jugadores con estadísticas completas en **un pedido de ~0.5s** (la app
afirmaba que hacían falta 50 pedidos; era falso, se corrigió). La
trampa de siempre: las estadísticas son **por competición**, igual que
la forma. Se resolvió acumulando los slugs por equipo
(`slugs_de_equipos()`) y fusionando después — acumular planteles por
partido haría que un equipo con dos fechas de la misma liga se sume a
sí mismo. Verificado: Driussi pasó de 3 PJ/1 gol a 5 PJ/3 goles, y el
costo total subió de 592 a 594 requests.

**La pestaña Plantel** dibuja la cancha del handoff de Claude Design,
con el once inferido por partidos jugados. El prototipo tenía un 4-3-3
fijo; al derivarlo de datos reales, 13 de 42 equipos daban esquemas
imposibles (el peor, 7-0-3) porque ESPN clasifica mal a varios
jugadores. Con cupos por línea acotados a rangos reales: 0 de 42, y
siguen apareciendo nueve esquemas distintos. La pantalla dice que es
una inferencia, no un dato.

**La skill v2.0** (`.claude/skills/valor-analisis-inclinacion/`):

- `expediente.py` ahora entrega `plantelH`/`plantelA` (los 25 que más
  jugaron, con `pj`, goles, asistencias y `peso_goles`) y `pjMaxH`/
  `pjMaxA` como escala. El recorte del modelo sigue intacto y hay un
  test que lo verifica (`test_expediente.py`).
- **Principio J:** toda ausencia se cruza contra el plantel antes de
  escribirse. Se descarta la que no mueve el partido, se nombran dos o
  tres como mucho, se dice por qué pesa con el número, y una ausencia
  de más de un mes es el estado del equipo, no una novedad.
- **Campos `local` y `visitante`** en `analisis.json`, uno por equipo,
  que la app muestra bajo el nombre de cada uno. El cambio es
  estructural a propósito: con un campo único nada obligaba a hablar
  del rival y el hueco no se veía. Son aditivos — los análisis viejos
  siguen andando, y hay un test que lo cubre.
- **Sección 4bis:** cómo describir a qué juega un equipo sin inventar,
  usando los marcadores como retrato y `peso_goles` para saber si el
  ataque es un equipo o un jugador.
- Presupuesto de búsqueda de 4 a 6, con al menos dos sobre el equipo
  del que menos se sabe.

Probada en Aldosivi–Unión: encontró tres titulares lesionados del
visitante (Vargas, Malcorra, Mosqueira), los tres con `pj` alto en el
plantel, y describió a los dos equipos por su problema real —ninguno
convierte— en vez de listar nombres.

---

## 6octies. Estadísticas de equipo y de jugador (2026-08-20)

Lucas empezó a mirar apuestas de estadísticas y pidió **ver** los
números — remates, remates al arco, faltas, córners, tarjetas,
atajadas. Explícitamente **no** como mercado: no hay línea, no hay
cuota, no hay Kelly. Es información, no una recomendación.

**El hallazgo:** el pipeline ya pedía `/summary?event=` de cada partido
para calcular los córners del modelo (`disciplina_equipo`), y ese mismo
response trae **25 métricas por equipo**. Se guardaban 3 y se tiraban
22. Sumarlas no costó un pedido más — costó dejar de descartar.

- `estadisticas_equipo()` aplana las métricas de un partido. Lo que
  ESPN no trajo queda en `None`, **nunca en 0**: en pantalla un cero
  medido y un dato ausente se leen igual, y un equipo que remató 0
  veces es una noticia mientras que un partido sin estadísticas
  cargadas no lo es.
- `promedios_equipo()` promedia cada métrica sobre los partidos que sí
  la traen, con divisor propio por métrica — dividir por el total
  contaría los ausentes como cero y hundiría el promedio.
- `data/estadisticas.json`: promedios de hasta 8 partidos por equipo.

**Cuidado con el caché.** `data/cache_disciplina.json` persiste entre
corridas y los registros anteriores a este cambio tienen solo tres
campos. Si se dan por buenos, las métricas nuevas no se pueblan nunca
(el partido ya está cacheado y no se vuelve a pedir). `resumen_completo()`
los detecta y los re-pide **una sola vez**. Si ese re-pedido falla, se
sigue usando el registro viejo: sirve para los λ, y perderlo por un
error de red sería cambiar un dato bueno por ninguno.

**Lo que casi rompe el motor:** `cards` pasó a poder ser `None`, y
`disciplina_equipo()` le sumaba sin chequear. Lo agarró un test antes
de correr. Los λ dependen de esa función.

**En la app:**
- Pestaña Plantel, por jugador: se elige una estadística y la lista se
  ordena por ella. En 375px no entran ocho columnas, y además la
  pregunta real es "quién remata más acá". La columna que importa es el
  **promedio por partido**: en Aldosivi, Acevedo tiene más remates
  totales (16) pero Sosa remata más seguido (2.6 contra 1.2).
- Comparativa entre los dos equipos, enfrentada. Si falta el dato de
  uno **no se muestra nada**: enfrentar un número contra un hueco
  invita a compararlos igual.

**El límite, que hay que decirlo:** no hay cuotas de props de jugador.
ESPN no las da. Con esto se puede pronosticar un número, no decir si
una línea está mal precificada. Mientras esto sea "para ver", no
importa; si algún día se quiere marcar valor acá, lo primero es
conseguir cuotas, no más estadísticas.

---

## 6nonies. El análisis estaba copiando al modelo (2026-08-20)

La primera medición de la `inclinacion` contra resultados reales, con
`medir_analisis.py`. Los números, sobre 6 partidos ya jugados y 13
análisis escritos:

- **El análisis coincidió con el modelo en 5 de 6 (83%).**
- Eligió `"L"` en 9 de 12 direcciones (**75%**), contra ~45% de locales
  que gana el fútbol sudamericano y 50% en esta muestra.
- Eligió `"E"` una sola vez (8%), contra ~28% de empates reales.
- Usó `null` una sola vez en 13 análisis.
- Acertó 2 de 6, contra 3 de 6 del modelo y 3 de 6 de la estrategia sin
  trabajo de apostar siempre al local.

**El diagnóstico no es "acierta poco" — con 6 partidos eso es ruido.**
Es que la distribución está mal, y eso se ve con muestra chica porque es
sesgo de proceso. Leyendo los 13 veredictos, la causa aparece sola: casi
todos argumentaban sobre **forma, tabla o localía**, que es exactamente
lo que el modelo ya procesa (los λ salen de ahí). El análisis no estaba
aportando una segunda lectura: estaba rehaciendo la primera, a mano y
con menos rigor.

Eso rompe la promesa de Método por una vía que la regla de alineación no
protege. Método dice que la lectura viene "de donde el modelo no llega".
Nunca vio un número del modelo —el recorte de `expediente.py` funciona—
pero llegaba al mismo lugar por el mismo camino.

Y como consecuencia, **la regla de alineación está prácticamente
inerte**: solo actúa cuando las dos lecturas difieren, y difieren el 17%
de las veces. En la única divergencia medida, acertó el modelo.

**Lo que se hizo (skill v2.1):**

- **Principio K:** si el motivo de la dirección lo puede ver el modelo
  (forma, tabla, localía), va `null`. Solo se inclina nombrando un
  factor que el modelo no ve: una baja pesada, un DT recién llegado, un
  equipo ya clasificado, calendario o viaje. `null` pasa a ser la
  respuesta por omisión. Prueba dura incluida en la auto-verificación:
  tapar la frase de la baja — si la dirección sigue en pie sin ella,
  salió de la forma y era decorado.
- **Principio L:** estar golpeado no es perder, también es empatar. De
  los análisis que fallaron, **tres terminaron en empate** (0-0, 2-2,
  0-0), todos razonando "a X le faltan más jugadores, gana Y". Un equipo
  con bajas juega peor, y peor sube el empate tanto como la derrota.

**Se espera que baje la cantidad de partidos marcados.** Es el punto: la
marca hoy aparece porque el análisis repite al modelo, que es justo lo
que la app promete que no pasa.

**Límite conocido: esto no se puede backtestear.** La skill hace research
web; corrida sobre un partido viejo, la web ya sabe el resultado. La
muestra solo crece hacia adelante, fecha a fecha. Por eso
`medir_analisis.py` avisa cuando la muestra es chica y empuja a mirar la
distribución antes que el acierto: es el error más caro que puede
inducir un medidor — que alguien "corrija" la skill por una racha.

---

## 6decies. Dos errores reales en la primera corrida de la v2.1 (2026-08-23)

La primera corrida de la skill con los principios K/L, sobre los 5
partidos del domingo, produjo un análisis de River-Vélez con dos
errores. Los encontró Lucas leyendo el resultado, no un test — y los
dos quedaron corregidos en la skill (v2.2) para que no se repitan.

**1. El plantel puede mostrar a un lesionado como si estuviera jugando.**
El expediente traía a Driussi con `pj:5, goles:3`, y con eso se escribió
"está jugando y convirtiendo" para descartar una baja que el research
había encontrado. Al revés: Driussi se lesionó en abril, se resintió en
julio, y no había debutado en el Clausura. Verificado contra la API en
vivo: `arg.1` da 3 apariciones/1 gol, `conmebol.sudamericana` da 2/2 —
los dos totales son de ANTES de la lesión, y `/roster` los suma sin
saber que hay una baja en el medio. `pj`/`goles` son acumulado de toda
la temporada, no forma reciente, y pueden quedar congelados en el
último partido que jugó alguien antes de lastimarse. Documentado como
**principio M**: si el research trae una fecha, esa fecha manda sobre
el plantel — el plantel pesa una baja que ya confirmaste, no la
descarta.

**2. "Jugó entre semana por copa" no es un factor exclusivo por sí solo.**
El análisis usó que River jugó Sudamericana el miércoles como base para
inclinar. Lucas: *"habría que ver si realmente las copas
internacionales representan tanto desgaste como para mover un
resultado, river jugo el miercoles ya por darte un ejemplo."* Tenía
razón: jugar martes/miércoles y domingo después es el ritmo semanal
normal de cualquier equipo de copa, no una desventaja puntual de ESE
partido — tratarlo como hallazgo infla una rutina a algo que distingue
al cruce. Lo que sí es exclusivo: tiempo extra y penales (Barracas-
Platense, donde Platense jugó 120' + penales en Chile — eso sí es más
carga que un partido normal), viajes largos, o ausencias confirmadas
con nombre (Racing-Boca, tres bajas concretas). Documentado como
**principio N**, con la pregunta de control: ¿esto distingue a este
partido de la rutina semanal de cualquier equipo de copa, o es la
rutina misma?

River-Vélez se corrigió a `null` — sin el factor de la baja (que no
era tal) ni el de la fatiga (que no era exclusivo), no quedaba nada que
sostuviera una dirección. Racing-Boca se reescribió para apoyarse en
las tres bajas confirmadas primero, con la fatiga como color
secundario, no como base.

---

## 6undecies. Un ascenso rompía el plantel (2026-08-23)

Lucas preguntó por qué algunos jugadores figuraban con 20-40 partidos y
otros con 5-6. La mayoría es normal —titular contra suplente—, pero un
caso no lo era: un mediocampista de Estudiantes de Río Cuarto con **52
partidos jugados**.

Rastreado: 16 eran reales, de esta temporada en Liga Profesional
(`arg.1`, la competencia del partido). Los otros 36 eran de Primera
Nacional (`arg.2`) — la categoría de la que el club **ascendió**. ESPN
sigue cacheando `arg.2` como el `defaultLeague` del club y no lo
actualiza. `slugs_plantel()` estaba pensada para sumar la liga
doméstica cuando el partido es de **copa** (ahí sí falta muestra), pero
no distinguía ese caso de un partido que **ya es de liga** — y sumaba
las dos categorías del mismo jugador, no copa más liga.

Afectaba a 1 de 42 equipos en la corrida del 2026-08-23. Se va a repetir
con cualquier equipo recién ascendido o descendido mientras ESPN no
actualice esa metadata — que puede ser todo el resto de la temporada.

Arreglado con `LIGAS_DOMESTICAS = {"arg.1"}`: `slugs_plantel()` ahora
solo suma la liga doméstica cuando la competición del partido **no**
es ya una liga doméstica conocida. Test agregado en `test_plantel.py`
con el caso exacto (`slugs_plantel("arg.1", "arg.2") == ["arg.1"]`).

---

## 6duodecies. Estadísticas: rival, local/visita, constancia (2026-08-23)

Lucas empezó a mirar apuestas de estadísticas de verdad (córners,
tarjetas, remates de jugador) y preguntó cómo mejorar la lectura ahí.
Pidió explícitamente tres cosas, con un ejemplo propio: *"no es lo
mismo un jugador que remató 5 veces en 5 partidos pero hizo 4 en 1"*.

**Lo que se agregó, cero pedidos nuevos** (mismo hallazgo que motivó
6octies: `/summary` ya se pedía para los córners del modelo):

- **`concede`**: no solo lo que un equipo hace, sino lo que le hacen. Se
  arma con los mismos partidos cacheados, mirando la fila del RIVAL en
  cada uno — `filas_partido()` cruza el historial (que ya trae
  `local`/`rival_id` por partido) con el caché de resúmenes.
- **`local`/`visita`**: split por sede sobre esos mismos partidos.
- **`desvio`**: desvío estándar por métrica, junto al promedio. Es lo
  que responde el ejemplo de Lucas — "5 remates en 5 partidos, uno por
  partido" y "4 en uno, 1 repartido en los otros cuatro" dan el mismo
  promedio y desvíos completamente distintos. Con menos de 2 partidos
  con dato no se calcula (sería ruido con forma de número).

`promedios_equipo()` sigue devolviendo el mismo total que antes, y
ahora además `local`/`visita`/`concede` como sub-objetos con la misma
forma — aditivo, no rompe lo que ya leía la app.

**En la comparativa de Plantel:** el local usa su propio split *de
local* y el visitante el *de visita* — jugar en casa o afuera no es lo
mismo, y promediarlo junto tapaba esa diferencia. Debajo de cada número
va **lo que su rival le suele conceder** en esa misma métrica: rematar
10 no significa lo mismo contra un equipo que concede 6 que contra uno
que concede 15. Ese cruce es lo que convierte un promedio suelto en una
lectura del partido.

**Corregido el mismo día, tras una auto-auditoría a pedido de Lucas
("¿está bien hecho?"):** la primera versión tenía tres fallas reales.

1. `concede` se calculaba y **no se usaba en ningún lado** — la feature
   que Lucas había pedido primero quedó a medias, con el dato guardado
   y sin mostrar. Ahora es la sub-línea de cada fila.
2. El split se mostraba con **2 partidos de muestra**. Medido sobre los
   datos reales: el caché tiene mediana 3 partidos por equipo (tope de
   `DISCIPLINA_N`, que existe para el modelo), y al partirlo por sede
   quedan 1-2 por lado — el mismo "muestra chica" que el proyecto le
   prohíbe al análisis, y encima **peor** que el total que reemplazaba.
   Ahora `MIN_SPLIT = 4`: abajo de eso se usa el total, que duplica la
   muestra aunque mezcle las sedes. El caché crece solo con cada fecha,
   así que el split se va habilitando sin pedir un request más.
3. El `±` de irregularidad usaba un umbral (>60% del promedio) **elegido
   a ojo**, que es exactamente lo que el repo prohíbe. Se sacó: con 3
   partidos de muestra un desvío no dice nada, y el cruce con `concede`
   ocupa ese lugar con información que sí se sostiene. El desvío se
   sigue calculando y guardando, para cuando haya muestra.

`cruza:false` marca las métricas donde "lo que concede el rival" no
significa nada: posesión (es complementaria — la de los dos suma 100),
precisión de pase y atajadas describen al que las hace, no algo que el
rival permita.

**Lo que queda para después, y es más grande:** el `/summary` que ya
se pide también trae estadísticas **por jugador y por partido**
(`rosters[].roster[].stats`), no solo el acumulado de temporada que
usa `planteles.json`. Eso resolvería dos cosas a la vez: la lectura de
constancia de un jugador partido a partido (el pedido original de
Lucas), y de raíz el problema de 6nonies/principio M (`pj`/`goles` del
plantel quedando congelados en el último partido antes de una lesión).
Es un archivo nuevo (`data/jugadores_partidos.json` o similar) y más
peso en el cron — se dejó afuera de este cambio a propósito, para no
mezclar dos features en un commit y poder mostrar esto funcionando
antes de sumar más.

---

## 7. Arquitectura de información

**Tres destinos: Fecha · Registro · Método.**

"Combinadas" **no** es un destino: el picker manual le pide al usuario
que arme algo, cuando el trabajo de la app es decirle qué hacer. La
combinada recomendada vive dentro de Pronósticos.

"Ajustes" **no** es un destino: la banca se pregunta inline en
Herramientas la primera vez que hace falta.

### Pantalla: Fecha (portada)

- Logo, slider de días, agrupado por liga, todos los partidos a la vista
  (sin acordeón: con 5-10 por día, todo entra).
- Por partido: hora, escudos + nombres, las tres cuotas, y **nuestro
  pronóstico**.
- El pronóstico **siempre existe** — no es una señal rara. Reemplaza al
  viejo "≠ Mercado", que disparaba en el 91% de los casos y no informaba
  nada.
- **La marca de valor sí es rara y va en banda.**
- Sin EV y sin monto sugerido en portada.

### Pantalla: Detalle de partido — 6 pestañas

1. **Análisis** (default) — el bloque humano en lenguaje llano: bajas,
   DT, contexto. Desde `data/analisis.json`.
2. **Pronósticos** — la lectura arriba, y debajo la escalera de riesgo.
   Cada opción con su probabilidad, su umbral de cuota, y una línea en
   castellano de cuándo se cobra ("se te paga salvo que gane Banfield").
   La combinada recomendada vive acá.
3. **Historial** — forma reciente y cruces directos.
4. **Posiciones** — tabla de la competición, con los dos equipos
   resaltados. Separada de Historial a pedido explícito de Lucas.
5. **Plantel** — la cancha con el once inferido, la lista de jugadores
   con sus estadísticas, y la comparativa de equipo (`data/planteles.json`,
   `data/estadisticas.json`). `data/equipos.json` existió con este
   propósito y se borró el 2026-08-20 sin haberse usado nunca — ver la
   sección 10.
6. **Herramientas** — explícitamente "para vos, no para la gente". Cuota
   real de tu casa → EV y stake en pesos. **La etiqueta "Kelly" no
   aparece**; el monto habla solo y el porqué está en Método.

### Pantalla: Registro

- **Marcador principal: tasa de acierto, nuestra y la del mercado, lado
  a lado.**
- Rentabilidad y CLV debajo.
- **Los resultados se resuelven solos.** Ya bajamos los marcadores de
  ESPN; pedirle al usuario que marque "Ganada/Perdida" a mano es
  fricción y es lo que hace que la gente abandone el registro a la
  semana.

### Pantalla: Método

Texto puro, sin cajas. Debe incluir: por qué probabilidad y no "va a
ganar X", por qué un umbral y no una cuota, qué es valor falso, y **cómo
nos medimos** — incluido el Brier real donde el mercado nos gana. La
transparencia es parte del producto.

---

## 8. Principio de ejecución

**El rigor va en *qué* recomendamos, nunca en lo que le exigimos
entender al usuario.**

Una cuota de 1.05 sin valor real no llega a la pantalla — no porque le
expliquemos por qué, sino porque simplemente no se muestra. La fracción
de Kelly se traduce a **énfasis editorial** ("esta la vemos clara" vs
"nos gusta, con menos convicción"), no a aritmética en pantalla.

**Postura:** seguridad en el veredicto, honestidad en el historial. La
app se la juega en cada pronóstico sin llenarse de advertencias, y por
separado muestra sin drama cuántas veces acertó.

Lucas fue explícito sobre el lenguaje: *"la gente normal no sabe lo que
es Kelly"*, y *"las apuestas suelen ser espontáneas a veces"*. El
usuario común no debe encontrarse con jerga.

---

## 9. Datos que faltan y de dónde sacarlos

Ninguno de estos se inventó en la interfaz; se dejaron como huecos
honestos.

| Falta | Dónde está | Qué hacer |
|---|---|---|
| **Estadio** | `competitions[0].venue.fullName` del scoreboard | Agregarlo en `actualizar.py` |
| **Goles en contra** | La tabla de ESPN trae `gf` pero no `gc` | Sin eso no hay diferencia de gol; mostrar G-E-P |
| **Plantel de jugadores** | `/roster`, pero las stats son un pedido por jugador (~50 por pestaña) | Bajarlo en el cron, nunca en vivo |
| **`grupo` en inglés** | ESPN devuelve `"Group B"` para todo | Traducir: "Zona" en liga local, "Grupo" en copas |

**Convención crítica de `marcador`:** en `formH`/`formA`, el primer
número es **siempre el del equipo de la fila**, no el del local.
Verificado sobre 206 partidos: 206 de 206 cierran con esta lectura, solo
109 con la otra.

---

## 10. El hueco más grande del producto — resuelto para analisis.json; equipos.json se borró (2026-08-20)

**Estado 2026-08-19:** `data/analisis.json` ya no está vacío — 12
partidos cargados, generados por la skill versionada (ver 6quinsexies).

**`data/equipos.json` se borró el 2026-08-20**, junto con el código que
lo leía en `index.html` (la variable `EQUIPOS`, su fetch, y los tres
campos `resumen`/`forma`/`localVisita`/`bajas` en la pestaña Plantel).
Nunca se cargó — quedó en `{_schema}` desde que se creó — y todo lo que
prometía terminó cubierto por otra vía, mejor: `resumen`/`forma` los
reemplaza el campo `local`/`visitante` de la skill (por partido, no
genérico); `bajas` las busca la skill y las **pesa** contra el plantel
en vez de listarlas a mano. Lo único que no tiene reemplazo es
`fichajes`, y ni eso justificaba mantener un archivo con esquema y
código de lectura sin ningún dato adentro — el riesgo real era que la
próxima IA lo viera "cargado" (con esquema) y asumiera que hacía algo.
Si algún día hace falta una ficha de equipo con identidad estable, se
diseña de cero: este archivo mezclaba cosas que caducan en días
(lesiones) con cosas que no (estilo), y por eso nadie lo mantuvo nunca.

El riesgo que motivó esta sección **se resolvió, no desapareció solo**:
la generación de `inclinacion`/`contexto`/`veredicto` ya no depende de
que Lucas escriba a mano cada partido. La hace esta misma terminal,
corriendo `.claude/skills/valor-analisis-inclinacion/SKILL.md` vía el
research (`expediente.py` + WebSearch). **Ojo con el nombre parecido:**
existe (o puede volver a existir) una skill instalada localmente como
`analisis-futbol-valor-json`, que NO es esta — esquema de salida
distinto, sin `inclinacion`, y espera como input los números del propio
modelo, lo que rompería la regla de alineación si se usara sin querer.
Antes de correr el research, confirmar el nombre exacto.

**El plantel dejó de ser un hueco el 2026-08-20.** Lo que esta sección
daba por pendiente ya está construido: el cron escribe
`data/planteles.json` (42 equipos, 1152 jugadores con `pj`, goles,
asistencias y `peso_goles`), `/roster` costó 2 requests más sobre 592, y
`expediente.py` se lo entrega a la skill. `injuries`/`status` del mismo
endpoint están
presentes en el esquema pero vacíos/no mantenidos para ligas
sudamericanas (verificado en vivo: Valentín Carboni de Racing, con
rotura de ligamento cruzado real, aparece `Active`/`[]`). Tampoco sirve
para identificar DT actual — el campo `coach` del roster es una lista
histórica vieja (verificado: devolvió a Gorosito/Cappa/Lopez/Almeyda
para River en vez de Coudet, el DT real desde marzo). Esos dos —
lesiones y DT— siguen necesitando research humano/IA, no automatizables
con esta API.

---

## 11. Cómo debería arrancar la IA nueva — en orden

**Fase 0 — Antes de escribir código**
1. Leer este documento entero.
2. Copiar del repo viejo, **sin modificar**: `actualizar.py`,
   `backtest.py`, `medir_sesgo.py`, `medir_vs_mercado.py`,
   `calibrar_ligas.py`, `data/`, `icons/`, `manifest.json`,
   `.github/workflows/actualizar.yml`.
3. Verificar que el pipeline corre: `python actualizar.py` debe
   completar sin dependencias externas.
4. Correr `python medir_vs_mercado.py` y confirmar que reproduce
   Brier ≈ 0.645 vs 0.623. **Si no reproduce, algo se rompió al copiar
   — pará y averiguá antes de seguir.**

**Fase 1 — Diseño: YA HECHA, no la repitas**
5. ~~Invocar la skill de brainstorming~~ — **ya se hizo, en Claude
   Design.** Leé `docs/design-handoff/VALOR.dc.html` y
   `docs/design-handoff/README.md` (sección 6bis explica qué es).
6. ~~Producir variantes comparadas~~ — **ya se produjeron y Lucas ya
   eligió.** No le vuelvas a pedir que elija entre direcciones de
   portada: eso ya pasó.
7. ~~Resolver el elemento firma~~ — **resuelto: la V.** Ver `DESIGN.md`.
8. El sistema de diseño (color, tipografía, espaciado, movimiento) **ya
   está escrito** en `docs/design-handoff/README.md`. Empezá por ahí,
   no lo reinventes.

Si después de leer el handoff **vos** ves algo genuinamente sin
resolver o inconsistente (como pasó con la marca — ver arriba),
mostraselo a Lucas con opciones antes de decidir solo. Pero no vuelvas a
correr el proceso completo de cero: la mayor parte del trabajo de esta
fase está terminado.

**Fase 2 — Reglas antes de pantallas**
9. ~~Portar las reglas y volver a barrerlas~~ **HECHO (2026-08-18):**
   `node barrer_valor.js`. Ver la sección 5bis — reprodujo la forma del
   barrido pero encontró un problema con el piso.
10. ~~Confirmar que el port a JavaScript da el mismo número que
    Python~~ **HECHO (2026-08-18):** `python doble_via.py`. Diferencia
    máxima **6,7e-16** sobre 476 probabilidades. El port no introdujo
    error numérico.

**Fase 3 — Interfaz: HECHA (2026-08-18)**
11. ~~Construirla pantalla por pantalla~~ **HECHO.** Las cuatro
    pantallas y las seis pestañas del detalle. Ver sección 6quater.
12. ~~Verificar en navegador~~ **HECHO:** cero errores de consola, sin
    desborde horizontal a 375px.
12bis. ~~Cambio de guardia `index.html`~~ **HECHO.** Ver 6quinquies.

**Fase 4 — Contenido: HECHA (2026-08-19/20)**
13. ~~Arreglar la skill de análisis~~ **HECHO — pero es otra skill.**
    La vieja `analisis-futbol-valor-json` quedó descartada, no
    arreglada: nació con el modelo como input, lo que viola la regla de
    alineación de raíz. La skill real es
    `.claude/skills/valor-analisis-inclinacion/SKILL.md`, versionada en
    el repo, con `expediente.py` como fuente objetiva y research propio
    (WebSearch). Ver la sección 6quinsexies.
14. ~~Cargar análisis real~~ **HECHO — 12 partidos en `data/analisis.json`.**
    La marca de valor aparece donde `inclinacion` coincide con el
    mercado. `data/equipos.json` se borró (2026-08-20): nunca se cargó
    (ver sección 10).

**Fase 5 — Modelo (opcional, con tiempo)**
15. Calibrar `rho` para copas.
16. ~~Validar `VIDA_MEDIA_DIAS` y `PRIOR_FUERZA` con train/test~~ **HECHO
    (2026-08-29):** `barrido_lambda.py`. Resultado: producción en el
    óptimo, NO tocar λ salvo fuente nueva. Ver el Addendum con esa fecha.

---

## 12. Reglas de trabajo con Lucas

Salieron de esta sesión y de las anteriores. Respetarlas ahorra
fricción.

- **Español, siempre.** Commits en español explicando **el porqué**, no
  el qué.
- **Medir antes de afirmar.** El proyecto tiene historial de
  afirmaciones que resultaron falsas al chequearlas contra la API real.
- **Nunca tocar constantes del modelo para que un número dé mejor.** Si
  una medición no mejora, el hallazgo es que no mejoró.
- **Mandarle los archivos.** Si evaluás algo visual, mandale la imagen
  al chat. No se la describas.
- **Una herramienta por área.** Si va a usar otra IA en paralelo, que
  sea para algo distinto o en una rama aparte.
- **No dar por terminado sin verificar en navegador.**
- Lucas pregunta seguido "¿vamos bien?" y espera una respuesta honesta
  con lo bueno **y** lo que falta, no un informe de logros.

## 6terdecies · Apuestas de estadísticas: la chance de pasar la línea (2026-08-23)

Lucas apuesta cada vez más a estadísticas (córners, tarjetas, remates,
remates al arco) y preguntó qué debería tener en cuenta alguien que
apuesta a eso. La respuesta salió de medir sobre los 177 partidos que
ya estaban en `cache_disciplina.json`, no de suponer. Varias hipótesis
razonables se cayeron.

### Lo que se midió

**El promedio es la unidad equivocada.** El mercado vende líneas, no
promedios. Y la irregularidad cambia de signo según de qué lado de la
media caiga la línea: con media 2.0, el errático tiene MÁS chance de
pasar 3.5 y MENOS de pasar 1.5. Mismo número, apuestas opuestas.

**Cada métrica se dispersa distinto** (varianza / media, por equipo y
por partido):

| métrica | disp equipo | disp total | k |
|---|---|---|---|
| faltas | 1.39 | 1.39 | 6.6 |
| tackles | 1.61 | 1.95 | 5.5 |
| córners | 1.77 | **1.00** | 123 |
| tarjetas | **0.73** | 0.87 | 183 |
| remates | 3.01 | 1.59 | 200 |
| al arco | 1.93 | 1.42 | 200 |

Usar Poisson para todo — lo que hace casi cualquier planilla —
subvalúa las colas de remates y sobrevalúa las de tarjetas. Por eso
`probMayor()` elige la campana según `disp`: binomial negativa arriba
de 1, Poisson cerca de 1, binomial (más regular que Poisson) abajo.

**El total del partido no es la suma de dos equipos independientes.**
En córners un equipo suelto mide 1.77 y el total 1.00. Si fueran
independientes tendrían que coincidir. No lo son: los córners son medio
suma cero. Sumar dos modelos sueltos infla las colas y hace ver valor
donde no hay. Por eso `dispersion_total()` lo mide aparte. Con las
tarjetas pasa al revés (0.73 → 0.87): un partido caliente le saca a los
dos.

**Con esta muestra, los equipos no se distinguen en remates.** `k` sale
de partir la diferencia entre equipos en ruido de muestreo y señal real.
Con 3-4 partidos por equipo, la diferencia observada en remates, al arco
y córners NO es más grande que el ruido: k=200 quiere decir "usá el
promedio de la liga". Lo que sí distingue a un equipo es el estilo —
faltas (k=6.6), posesión (3.9), quites (5.5). La app venía mostrando
"12.5 contra 18.7" como si fuera una diferencia real; era ruido con
decimales. Ahora cada número dice qué parte es del equipo y qué parte
de la liga.

Nada de esto es una constante puesta a mano: `parametros_metricas()`
recalcula media, dispersión y k en cada corrida sobre el caché entero,
así que el encogimiento se afloja solo a medida que se juntan partidos.

**Las tarjetas no dependen del partido.** Correlación con el marcador:
−0.05 con los goles, +0.01 con la diferencia; partido cerrado 4.44
tarjetas, goleada 4.53. La idea intuitiva de "partido cerrado, más
tarjetas" es falsa acá. La varianza viene de otro lado — del árbitro, y
ESPN lo devuelve en `gameInfo.officials[0].fullName`, dentro del mismo
`/summary` que ya se pide. Sin medir todavía: haría falta un re-fetch
de los 177 partidos, una vez.

**Cuidado con la tautología:** remates al arco contra goles da r=0.56.
Un gol *es* un remate al arco. Modelar eso es re-modelar goles con otro
nombre, y hereda la sobredispersión que ya se midió en el modelo.

### Qué se agregó

- `actualizar.py`: `muestras_por_equipo()`, `parametros_metricas()`,
  `media_encogida()`, `esperados()`, `dispersion_total()`. Se escriben
  en `data/estadisticas.json` como `parametros` (nuevo, top-level) y
  `esperado` por equipo. Contrato aditivo: nada se renombró.
- `index.html`: `probMayor()`, `lineasDe()`, `pesoEquipo()`,
  `bloqueLineas()` — la escalera de 4 líneas por equipo y del total,
  con selector de métrica (`data-linmet`, agregado al `closest()`;
  olvidarlo es el bug silencioso que ya pasó dos veces).
- `test_probabilidad.js` (32) y 32 tests nuevos en
  `test_estadisticas.py`. Los dos corren en CI.

### Lo que NO se hizo, a propósito

- **No se ajusta por el rival.** Sería ataque×defensa como en goles,
  pero `concede` tiene el mismo problema de muestra que el resto: hoy
  agregaría ruido, no información.
- **El `esperado` se calcula sobre la muestra total, no sobre el split
  de local/visita.** El ancla de la liga es la general; anclar un split
  de 2 partidos a una media que no le corresponde metería un sesgo peor
  que el que corrige.
- **No aparece como mercado.** Lucas lo pidió explícito: ver las
  estadísticas alcanza, no quiere que compitan con los pronósticos.

## 6quaterdecies · El árbitro: guardado, medido, y no mostrado (2026-08-23)

Paso 2 de los tres que salieron de la pregunta de Lucas sobre apuestas
de estadísticas. El razonamiento venía de una medición: las tarjetas no
dependen de cómo va el partido (r = −0.05 con los goles, +0.01 con la
diferencia). Si la varianza no viene del partido, el sospechoso es el
árbitro — y ESPN lo devuelve en `gameInfo.officials`, dentro del mismo
`/summary` que ya se pedía.

### Lo que se hizo

`arbitro_de()` saca al juez principal **por posición, no por orden**:
`officials` trae también asistentes y cuarto árbitro, y el primero de la
lista no siempre es el que muestra las tarjetas. Se guarda como
`_arbitro` en el registro del partido (guion bajo para que todo lo que
recorre equipos lo saltee) y `resumen_completo()` ahora exige esa clave,
que es lo que dispara el rellenado de una sola vez — el mismo mecanismo
que se usó para las 25 métricas.

Al 2026-08-23: **57 de 179 partidos** con árbitro informado. El resto se
rellena solo cuando esos equipos vuelvan a jugar; no se forzó un
re-fetch masivo porque no hacía falta.

### Lo que dio la medición

`medir_arbitros.py` no compara promedios: hace una **prueba de
permutación**. Siempre hay diferencia entre árbitros, aunque repartas
los partidos tirando una moneda; la pregunta es si esa diferencia es más
grande que la que da el azar. Se mezclan los totales entre árbitros 5000
veces y se cuenta cuántas mezclas igualan o superan la separación real.

Con 54 partidos y ~2 por árbitro:

| métrica | separación observada | el azar la iguala | veredicto |
|---|---|---|---|
| tarjetas | 1.90 | 32.6% | indistinguible |
| faltas | 16.26 | 17.7% | indistinguible |
| córners | 4.42 | 66.9% | indistinguible |

**No se muestra nada del árbitro en la app.** El chequeo ingenuo
(varianza entre promedios contra ruido esperado) daba "hay señal" en
tarjetas y faltas; la permutación lo desarma. Es exactamente el caso que
la regla del repo cubre: si una medición no mejora, el hallazgo es que
no mejoró.

El dato se sigue guardando porque llega gratis, y el script se vuelve a
correr cuando haya más fechas. Cuando el veredicto cambie, ahí se
mostrará.

## 6quindecies · Estadísticas por jugador y por partido (2026-08-23)

Paso 3, y el pedido original de Lucas, textual: *"no es lo mismo un
jugador que remató 5 veces en 5 partidos pero hizo 4 en 1"*. El
acumulado de temporada que traía el roster da lo mismo en los dos casos.

Sale del mismo `/summary` que ya se pedía, en `rosters[]`: cero pedidos
nuevos, igual que las 25 métricas de equipo y que el árbitro.

### Lo que se guarda

`jugadores_partido()` deja por partido, y solo de los que jugaron, una
lista compacta `[remates, al_arco, faltas, amarillas, goles, asist,
titular]`. Va como lista y no como diccionario porque son ~32 jugadores
por partido: repetir siete nombres de clave por fila multiplicaba por
seis el caché. Un cero de alguien que estuvo en el banco no es un cero,
es una ausencia, y promediarlo hundiría su número — por eso solo entran
los que jugaron.

`serie_jugadores()` arma la serie de los últimos 8, en orden, y descarta
a los que aparecen una sola vez: una serie de un partido no distingue al
regular del explosivo, que es para lo único que existe.

### El hallazgo: los jugadores SÍ se distinguen

A nivel equipo, `k` en remates dio 200 — dos equipos no se separan del
ruido. A nivel jugador da **2.5**. Un delantero y un central se
distinguen y por mucho:

| puesto | remates/partido | k |
|---|---|---|
| delantero | 1.41 | 3.6 |
| mediocampista | 1.06 | 3.7 |
| defensor | 0.48 | 20.9 |
| arquero | 0.00 | — |

Por eso al número de un jugador se le puede creer mucho más que al de un
equipo. Pero el ancla no puede ser el promedio de todos los jugadores:
encogería al 9 hacia abajo y al central hacia arriba, borrando la única
diferencia que sí es real. `parametros_jugadores()` agrupa **por
puesto**, que es la división que ESPN da gratis y la que más explica.

En pantalla, cada jugador muestra su serie partido por partido sin
promediar, y la chance de pasar la línea más cercana a lo que se espera
de él. La campana es la de su puesto: con 3 a 8 partidos, un desvío
propio sería ruido con forma de número.

### Un bug que atrapó el test, no el navegador

`_jugadores` **es un diccionario**, a diferencia de `_arbitro`. Todo lo
que recorría el registro filtrando por tipo (`isinstance(f, dict)`) lo
contaba como un tercer equipo y descartaba el partido entero.
`dispersion_total()` y `medir_arbitros.py` tenían los dos ese bug. Ahora
las claves con guion bajo se filtran por nombre, no por tipo.

### Peso: bajó, no subió

`planteles.json` se escribía con `indent=1` — 138 KB de espacios en un
archivo que CLAUDE.md marca como "no editar a mano" y que el teléfono
baja entero en cada carga. Compactado, y con las series de un solo
partido descartadas:

- antes de todo esto: **195 KB**
- con la serie por jugador: **180 KB**

### De paso, la causa raíz del principio M

`expediente.py` pasa ahora la serie a la skill de análisis. Eso resuelve
sin research la mitad del caso Driussi: **quien no viene jugando no
tiene serie**. Verificado con datos reales — Bruno Leyes figura con 15
PJ de temporada y sin serie reciente, que es exactamente la señal que
faltaba. `esp` (la media encogida) queda afuera del expediente a
propósito: es un número del modelo, y el expediente existe para que el
análisis no lo vea.

## 6sexdecies · CLV: el único instrumento que contesta rápido (2026-08-23)

Sale de evaluar dos recomendaciones de ChatGPT que trajo Lucas. La
mayoría de lo que proponía no es viable con nuestros datos (xG con
cobertura del 42%, minutos esperados y toques en área que ESPN no da,
splits defensivos por puesto que necesitan cientos de partidos, varias
casas que requieren API paga). Pero el CLV sí, y es el mejor de la
lista.

### Por qué importa más que el resto

Está medido que el modelo captura el **44%** de lo que sabe el mercado
(289 partidos contra la cuota de cierre real) y que apenas le gana a la
frecuencia base (4 de 8 mercados en Liga, 1 de 8 en Libertadores, sobre
425 partidos). Con esa señal, esperar a que los resultados digan si hay
ventaja tarda cientos de apuestas — y para entonces la plata ya se fue
averiguándolo.

El CLV contesta antes: si el modelo sabe algo que el precio todavía no
tiene, la línea debería moverse **hacia nosotros** antes del inicio. Si
eso pasa sostenidamente hay ventaja aunque la apuesta puntual se
pierda; si no pasa, no la hay aunque se gane.

### El hallazgo que definió el diseño

**ESPN borra el bloque de cuotas cuando el partido termina.** Verificado
sobre 11 partidos ya jugados de arg.1 en cuatro fechas distintas: los
tres que quedaban en grilla tenían `odds`, los pasados **ninguno**.

Consecuencia: el CLV **no se puede medir hacia atrás**. Hay que ir
guardando. Por eso `snapshot_cuotas()` acumula una foto por corrida en
`data/cuotas.json` — y nunca borra, igual que los marcadores, porque
ese archivo va a ser el único lugar donde viva la cuota de cierre.

Cuesta **cero pedidos nuevos**: la cuota ya venía en el scoreboard que
se pide para armar la grilla, y `mercado_de()` ya la extraía. Lo único
que faltaba era guardarla en el tiempo.

### Qué mide `medir_clv.py`

No compara promedios de cuota. Por cada partido con dos fotos:

1. Le saca el margen a las dos (`devig`) — sin eso, cualquier cuota
   parece generosa y la comparación está sesgada a nuestro favor.
2. Toma la probabilidad del modelo en el momento de la primera foto.
3. Pregunta si la línea se movió hacia donde apuntaba el modelo, más
   seguido de lo que da una moneda (test binomial).
4. Informa el CLV medio: cuota tomada × probabilidad de cierre − 1.

Está escrito para **poder decir que no**: hay un test que le pasa ruido
y verifica que no invente señal, y otro que le pasa una señal real y
verifica que la detecte. Con menos de 30 casos se niega a concluir.

### Estado al 2026-08-23

8 partidos, 8 fotos, ninguno con dos todavía. El script lo dice y no
inventa nada. Verificado igual de punta a punta simulando el movimiento
de línea sobre las cuotas reales: 32 comparaciones, devig correcto, y
el veredicto negándose a concluir con 22 casos útiles.

Hacen falta varias corridas del cron sobre partidos que todavía no se
jugaron. Es lo esperable, no un error.

## 6septdecies · El "44%" era contra una vara falsa (2026-08-24)

Sale del issue #8: `medir_vs_mercado.py` evaluaba **289 partidos** — la
temporada en curso — porque cruzaba nombres del CSV con equipos de ESPN,
y ESPN solo devuelve la temporada actual. El CSV que ya bajábamos tiene
**6310**, de 2012 a 2026, y es autosuficiente: trae `Home`, `Away`,
`HG`, `AG` y `Date`, que es exactamente lo que `fuerzas_equipos()`
necesita. El cruce con ESPN era lo único que ataba la medición.

`historico.py` lo normaliza (arg 6310, bra 5544, con cierre de Pinnacle
en el 94%) y `medir_historico.py` mide walk-forward estricto.

### El hallazgo

Sobre **6270 partidos de arg.1**:

```
Brier tasa base       0.65292
Brier modelo          0.65071
Brier mercado         0.62553
Brier siempre 1/3     0.66667
```

Contando de las dos formas, la MISMA medición:

| vara | capturamos |
|---|---|
| "siempre un tercio" | **38.8%** |
| tasa base histórica | **8.1%** |

**El salto de 44% a 8% no es por la muestra: es por dejar de contarnos
la localía como mérito.** El local gana bastante más que un tercio; un
modelo que solo aprendiera eso ya parecería listo contra la vara falsa.
La tasa base — la frecuencia histórica de local/empate/visita hasta ese
momento — es la vara honesta, y contra ella el modelo aporta 8%.

### Argentina no es Brasil

Misma medición sobre 5504 partidos de bra.1:

```
tasa base   0.63383
modelo      0.61994
mercado     0.59671
capturamos  37%
```

Y la calibración de Brasil es buena (casi todas las franjas dentro de
pocos puntos), mientras que la de Argentina se rompe arriba: cuando
decimos 70-80%, pasa el 56.4% — **+17.4 puntos de exceso de
confianza**.

O sea que la debilidad del modelo está concentrada justo en la liga que
más le importa a Lucas. Eso es una pista, no una condena: hay algo del
fútbol argentino (o de cómo lo tratamos) que el modelo no está
capturando, y ahora hay muestra para investigarlo.

### El corte temporal, testeado aparte

Todo esto es walk-forward: se ajusta con lo anterior y se predice lo
siguiente. Una fuga de futuro **no se ve como un error, se ve como un
modelo buenísimo**, así que `ventana_previa()` tiene tests propios —
incluido el caso que rompe sin avisar: dos partidos del mismo día no se
ven entre sí, porque cuando se predice una fecha esa fecha todavía no
se jugó.

Ventana de 365 días: medido, con `VIDA_MEDIA_DIAS = 45` un partido de
hace un año pesa 0.0036 y uno de hace dos, 0.0000. Cortar ahí no cambia
el ajuste y evita recorrer 14 años por partido.

### Qué destraba

Los issues #2 (rho), #3 (VIDA_MEDIA_DIAS / PRIOR_FUERZA), #5 (remates
para fuerza) y #6 (calibrar antes de publicar) estaban todos parados
por falta de muestra. Con 11.854 partidos y el arnés walk-forward ya
armado, se pueden atacar de verdad.

## 6octodecies · Por qué Argentina anda mal: dos constantes sin validar (2026-08-24)

Issue #9. Con el arnés de `medir_historico.py` se puede cortar la
medición por torneo, por era y por profundidad de historia. Lo que
salió, en orden:

### 1. La Copa de la Liga empeora el modelo

| corte | n | capturamos |
|---|---|---|
| arg · Copa De La Liga | 920 | **−17.5%** |
| arg · Liga Profesional | 5350 | 11.1% |

Peor que la tasa base. Mezclarla con la liga ensucia la medición y
probablemente también el ajuste de fuerzas.

### 2. El problema es RECIENTE, no estructural

Solo Liga Profesional / Serie A:

| era | arg | bra |
|---|---|---|
| 2012-2017 | 15.8% | 17.4% |
| 2018-2021 | 26.7% | 51.2% |
| 2022-2026 | **−23.0%** | 40.5% |

Argentina andaba bien y se rompió. Brasil no.

### 3. Y la causa está en la forma del torneo

| | equipos | PJ/equipo | cruces por par |
|---|---|---|---|
| bra, todas las temporadas | 20 | 38 | **2.00** |
| arg 2022-2024 | 28-29 | 27 | **1.00** |

Brasil es un doble round-robin perfecto, 14 años seguidos: la red de
cruces está completa y balanceada. Argentina pasó a 28-30 equipos con
**una sola vuelta**. Eso es ~1.5x más parámetros (ataque y defensa por
equipo) estimados con ~0.7x los partidos por equipo: la mitad de datos
por parámetro.

Y el modelo no sabe que tiene menos datos. Se ve en cuánto se anima a
separarse de la tasa base:

| | modelo | mercado |
|---|---|---|
| arg 2022-2026 | **7.70%** | 7.02% |
| bra 2022-2026 | 8.11% | 8.13% |

En Brasil opinamos tanto como el mercado. **En Argentina opinamos MÁS
que el mercado** — y nos equivocamos. Ruido confundido con señal.

### 4. `VIDA_MEDIA_DIAS = 45` está muy lejos del óptimo

Barrido, 2018+ (in-sample):

| vida media | arg | bra |
|---|---|---|
| 25 | −12.6% | 38.0% |
| **45 (actual)** | **−1.3%** | **46.4%** |
| 90 | 7.7% | 54.4% |
| 180 | 19.2% | 61.7% |

Monótono y en las dos ligas. Confirmado **fuera de muestra** (elegir
con 2012-2021, medir en 2022-2026):

| liga | vida | capt. 2022+ |
|---|---|---|
| arg | 45 | **−29.9%** |
| arg | 180 | +3.4% |
| arg | 270 | **+12.7%** |
| bra | 45 | 40.5% |
| bra | 180 | **+57.7%** |

**No se cambió la constante todavía, y a propósito:** la mejora sigue
subiendo a 270 y el barrido se cortó por tiempo de cómputo, no porque
la curva se aplanara. Poner un número sacado de un barrido inconcluso
es justo lo que la regla del repo prohíbe. Falta encontrar el óptimo.

### 5. Encoger hacia la tasa base también mejora, fuera de muestra

Ajustando `k` solo con 2012-2021 y aplicándolo a 2022-2026:

| liga | vida | capt. sin k | k | capt. con k |
|---|---|---|---|---|
| arg | 45 | −29.9% | 0.40 | 25.0% |
| arg | 180 | 3.4% | 0.30 | **34.6%** |
| bra | 45 | 40.5% | 0.30 | 46.3% |
| bra | 180 | 57.7% | 0.20 | **58.1%** |

Dato que confirma el diagnóstico: **con la vida media más larga hace
falta MENOS encogimiento** (0.40 → 0.30 en arg, 0.30 → 0.20 en bra).
La ventana corta estaba fabricando ruido que después había que
apagar.

Esto es el issue #6 y no se aplicó: agrega un mecanismo nuevo a lo que
se publica e interactúa con `VALOR_MIN`. Es decisión de producto.

### Lo que NO se pudo medir

El efecto sobre las marcas de valor. Se intentó una simulación rápida y
daba que el 36% de todas las opciones quedaban marcadas, lo cual es
implausible: la cuenta no replica la lógica real de `marcaDeValor()` ni
de `escalera()`. Se descartó el número en vez de reportarlo.


## 6novodecies · Segunda auditoría de ChatGPT: tres arreglos, y la lección de que ya la habíamos contestado (2026-08-24)

Lucas trajo una auditoría externa larga del repo entero. Es la **segunda**
— la primera fue el 2026-08-23 y está en §6sexdecies. Lo importante no
es lo que propuso, sino que **propuso de nuevo cosas que §6sexdecies ya
había descartado con medición**, un día después y teniendo el archivo a
la vista.

Si llega una tercera, empezá por acá y por §6sexdecies antes de evaluar
nada.

### Lo que se aplicó (los tres eran reales)

**1. `actualizar.py` se contradecía a sí mismo sobre `rho`.** Un
comentario decía `arg.1 = +0.05 MEDIDO`; treinta líneas más abajo, el
barrido del 2026-08-24 decía que 0.05 es peor que el -0.05 que está en
la config. La config estaba bien: lo podrido era el comentario viejo,
que sobrevivió a su propio dato. Reescrito en un bloque solo, que
además deja dicho explícitamente que si alguien vuelve a leer "+0.05
está MEDIDO" es texto vencido.

**2. `PRODUCT.md` era el único archivo del repo que llamaba xG a λ.**
`TRASPASO.md` y el spec de diseño ya documentaban bien que ESPN solo da
`expectedGoals` por jugador destacado y nunca por equipo. Corregido, con
la aclaración de por qué no es xG.

**3. El historial no decía con qué constantes se hizo cada pronóstico.**
Este era el hallazgo bueno. `rho` ya se guardaba por registro, pero
`VIDA_MEDIA_DIAS` y el `prior` de la liga no — y las dos se tocaron este
mes. Sin eso, agregar `historial_pronosticos.json` para medir
calibración mezcla eras del modelo sin avisar.

Ahora cada registro nuevo lleva un bloque `modelo`. **Y a los viejos no
se les estampa nada**, que es la parte que importa: no sabemos con qué
constantes se hicieron, y ponerles las de hoy los haría parecer
comparables con los nuevos — exactamente lo contrario de para lo que
existe el sello. `test_pronosticos.py` (15 casos) protege eso.

### Lo que se descartó, y por qué — para no volver a evaluarlo

- **"Prioridad 1: value betting real para córners, tarjetas, remates y
  jugador."** No hay cuotas de esos mercados en ningún lado del
  pipeline: `mercado` de `partidos.json` trae 1X2, totales y hándicap y
  nada más. Sin cuota no hay EV. Es un problema de fuente de datos, no
  de código.
- **Y peor: proponía construirlo justo sobre remates de jugador**, que
  el mismo día se midió como la métrica **peor calibrada de la app**
  (2.09 veces el piso de ruido, ver `medir_jugadores.py`). Ponerle
  Kelly a una probabilidad que sabemos rota no da value betting: da
  apuestas malas con cara de confiables. El orden va al revés.
- **"Prioridad 2: Market Scanner con Bet365/Betano/Betsson."** Ya
  descartado en §6sexdecies el día anterior: requiere API paga.
- **"Siete modelos, uno por mercado."** Es agregar parámetros cuando el
  diagnóstico ya es que falta señal. Choca de frente con la regla de
  medir antes de calibrar.
- **"TRAIN/VALIDATION/TEST."** `medir_historico.py` ya hace
  walk-forward, que para series temporales es mejor que un corte fijo.
  La auditoría no lo registró.
- **"VALOR SCORE 84/100."** Un número compuesto que esconde cuál de sus
  seis componentes lo mueve. La app hoy declara fiabilidad métrica por
  métrica, que es lo contrario y es de lo mejor que tiene.

### Lo que la auditoría no vio, y es lo que más importa

Le puso **8/10 general y 7/10 a "value betting" a una app cuyo ROI
medido es −6.18%**. Leyó `backtest.py`, citó números de Brier, y nunca
escribió que esto hoy pierde plata. Tampoco vio que las líneas de
jugador caen casi siempre en 0.5 — o sea que la app contesta "¿remata
al menos una vez?" cuando la casa pregunta "¿remata más de 2.5?".

**La moraleja para la próxima auditoría externa:** una revisión que no
menciona el número que más duele es demasiado amable para servir. Lo
útil de esta fueron tres arreglos chicos de higiene; la dirección del
producto no salió de acá.

## 6vicies · La app marcaba valor con una vara distinta de la que usaban las mediciones (2026-08-25)

Sale de un informe de Gemini que trajo Lucas, con literatura de apuestas.
El informe en sí no aportó nada nuevo — su arquitectura de tres pasos
(xG → Dixon-Coles → EV + Kelly fraccionado) es literalmente la de VALOR,
y su recomendación central de construir sobre xG es la que está cerrada
desde el 2026-08-16 porque ESPN solo da `expectedGoals` por jugador
destacado.

Pero listaba un recurso de acceso abierto que valía la pena perseguir:
"Using the Wisdom of the Crowd to Find Value in a Football Match Betting
Market", de Joseph Buchdahl, alojado gratis y legal en
football-data.co.uk — el mismo sitio del que `historico.py` ya baja
nuestros 11.854 partidos.

### El hallazgo

Buchdahl dedica varias páginas a cómo se le saca el margen a una cuota,
y su punto es que repartirlo parejo entre las tres opciones está mal:
las casas le cargan más margen a las cuotas altas. Fui a ver qué
hacíamos nosotros y aparecieron **dos métodos conviviendo**:

| | Método | Corrige favorito-longshot |
|---|---|---|
| `medir_clv.py`, `medir_historico.py` | Shin (1993) | sí |
| `index.html` — lo que ve el usuario | proporcional | **no** |

O sea: medíamos el modelo con una vara y marcábamos valor con otra. Shin
ya estaba implementado y documentado en el repo desde antes; la app
nunca lo usó.

### La medición (`medir_devig.py`, nuevo)

Las cuotas de cierre son la mejor estimación disponible de la
probabilidad real. Se les saca el margen de las dos maneras y se compara
cuál queda más cerca de lo que efectivamente pasó. No hay ajuste: la `z`
de Shin sale de las cuotas del propio partido, nunca del resultado. El
error se mide **contra el ruido binomial**, no contra cero.

Sobre 11.854 partidos de Argentina y Brasil, 2012–2026:

```
                        margen    error prop   error shin
Pinnacle                 3.13%        7.84         6.28
Promedio del mercado     6.94%       11.21         6.18
```

**El patrón es lo que decide, no el número suelto:** cuando el margen
sube de 3% a 7%, el error del proporcional casi se duplica y el de Shin
no se mueve. Shin es robusto al margen; el proporcional se degrada.

Y la app trabaja con cuotas de DraftKings, margen **7.7%** — la
condición donde el proporcional es peor. Con margen alto Shin gana en
todos los tramos, sin excepción.

(Con Pinnacle, los dos tramos de cuota más alta favorecen al
proporcional: Shin sobrecorrige ahí. Son 1187 y 56 casos, y el total
igual da Shin. Queda anotado porque es la única grieta del resultado.)

### Lo que se cambió

`index.html` ahora usa `devigShin`, traducción literal de `devig_shin`
de `medir_clv.py` — misma bisección, mismas constantes. Seis tests
nuevos en `test_alineacion.js` fijan los valores contra los que Python
devuelve, a 1e-9: si las dos implementaciones se separan, salta.
Verificado además en el navegador, con los mismos dígitos.

### Cuánto mueve la aguja, con honestidad

Sobre la grilla real de hoy (29 partidos): diferencia media de 0.58 pp,
máxima 1.76 pp. Contra el umbral de 6 pp de la marca dorada, eso puede
dar vuelta un caso de borde, y hoy hay tres opciones entre 5.2 y 5.7 pp
que están a menos de un punto de encenderse.

**Pero el efecto práctico hoy es chico, y por una razón que conviene
saber:** la mayoría de las marcas actuales son de over/under, que van
por la vía de dos opciones donde Shin no corrige nada (igual que en
Python). El cambio afecta 1X2 y doble oportunidad. No es un arreglo que
se note en pantalla mañana; es que las dos mitades del sistema por fin
miden con la misma vara.

### Lo que sigue abierto

Buchdahl concluye que **Pinnacle es el único libro cuyas cuotas reflejan
probabilidad real**, y que las de los demás reflejan marketing.
Nosotros detectamos valor contra DraftKings porque es lo que da ESPN.
Para medición histórica estamos bien (usamos Pinnacle). Para las marcas
en vivo, no — y eso no se arregla con código, hace falta otra fuente.

### Addendum · los dos scripts que quedaban con la vara vieja (2026-08-25)

Al arreglar `index.html` aparecieron dos mediciones más con el devig
proporcional: `medir_vs_mercado.py` y `medir_sesgo.py`. Dejarlas así
era peor que no haber empezado — alguien compara el número de
`medir_vs_mercado.py` contra el de `medir_historico.py` sin saber que
están medidos con varas distintas. Las dos pasan ahora por
`medir_clv.devig_shin`.

`medir_sesgo.py` era el más importante de los dos: mide **cuánto nos
apartamos del mercado**, así que un sesgo en el devig se confunde con
sesgo nuestro.

**El veredicto no se movió, y eso también es el hallazgo.** En
`medir_vs_mercado.py` el Brier del mercado mejoró de 0.62452 a 0.62436
y el "capturamos el 33% de lo que sabe el mercado" quedó igual. Es lo
esperable: ese script usa cuotas de Pinnacle, margen 3.13%, donde los
dos métodos casi no se separan. La corrección pesa donde el margen es
alto — o sea en la app, que usa DraftKings al 7.7%.


## 6vicies semel · Medíamos el modelo con un ojo tapado (2026-08-25)

Salió buscando otra cosa. La tarea era la #5 de la lista pendiente —
volver a medir el encogimiento hacia la tasa base, porque los `k` de
§5 se habían medido con `VIDA_MEDIA_DIAS` en 180 y la constante hoy
está en 300. Se midió, y de paso apareció esto, que es más grande.

### El error

`medir_historico.VENTANA` estaba en **365 días**: cuánta historia se le
deja ver al modelo para predecir cada partido del walk-forward. El
comentario que lo defendía decía, textual:

> "Medido: con `VIDA_MEDIA_DIAS = 45`, un partido de hace un año pesa
> 0.0036 y uno de hace dos, 0.0000. Cortar en 365 días no cambia el
> ajuste y evita recorrer 14 años por partido."

Era cierto **cuando se escribió**. Con vida 300 ese partido pesa
**0.43** y el de hace dos años 0.185. Es el tercer comentario de este
repo que sobrevive a su propio dato, y el segundo en dos días — el de
`rho` fue el 2026-08-24, el de `arg.copa` el mismo día.

Pero el peso no era lo grave. Lo grave es que **la app no corta ahí**:
`TEMPORADAS_HISTORIA = 5` y `get_historia()` (actualizar.py:1772) le
pasa cinco temporadas a `fuerzas_equipos()`. O sea que veníamos
evaluando un modelo con un año de historia mientras el publicado tenía
cinco. **Todo lo medido en semanas salió peor de lo que el modelo
publicado es.**

Atraso contra el cierre de Pinnacle, fuera de muestra (2583 partidos de
arg desde 2022, 1745 de bra):

| ventana | 365 | 730 | 900 | 1100 | 1460 | 1825 |
|---|---|---|---|---|---|---|
| arg | .0159 | .0122 | .0115 | .0112 | .0110 | **.0109** |
| bra | .0229 | .0165 | .0162 | .0155 | .0151 | **.0148** |

**Un tercio del "atraso contra el mercado" era de la medición, no del
modelo.** Y la curva está bien aplanada al final, así que 1825 no es un
borde de grilla: a los cinco años un partido pesa 0.015 y ya no mueve
nada.

`VENTANA` pasa a **1825**, y hay un test que lo ata a
`TEMPORADAS_HISTORIA`: si alguien sube las temporadas, falla hasta que
la ventana lo siga. La regla que fija no es "365 está mal" sino que **la
medición no puede ser más pobre que la producción**. Cuesta: la pasada
completa va de ~1.5 min a ~8 min por liga.

### Lo que hay que rehacer

Todo número de atraso o de captura reportado antes del 2026-08-25 está
medido con la ventana corta y **subestima al modelo**. En particular:

- **el barrido de 26 ligas** que concluyó que la distancia al cierre es
  parecida en todas (0.012–0.036) y que por lo tanto Argentina no es el
  problema. La conclusión puede sobrevivir —el error afecta a todas las
  ligas por igual— pero los números no, y si el efecto es desparejo la
  conclusión tampoco;
- §6septdecies y §6octodecies, que eligieron `VIDA_MEDIA_DIAS` y
  discutieron `rho` con esta vara.

### Y la tarea original: el encogimiento

`medir_encogimiento.py` es nuevo, con 23 tests. Mide
`p = (1-k)·modelo + k·tasa_base` fuera de muestra, con partición
temporal, contra el ruido pareado y con atraso en vez de captura.

| liga | ventana | atraso sin k | k | atraso con k | ¿se despega del ruido? |
|---|---|---|---|---|---|
| arg | 1825 | +0.01085 | 0.20 | **+0.00850** | sí, 4 errores estándar |
| bra | 1825 | +0.01477 | 0.15 | +0.01507 | no, y encima empeora |

**arg: sirve, y el `k` bajó a 0.20.** Aguanta moviendo el corte de 2019
a 2023: sale entre 0.20 y 0.30 en las cinco particiones, siempre
significativo.

**bra: no.** No se despega del ruido con ninguna ventana, y con la
correcta cambia de signo. Aplicarlo sería mover una constante para que
un número dé mejor.

El hallazgo de §5 —cuanta más historia, menos encogimiento hace falta—
se confirma y se extiende: **0.40** (vida 45) → **0.30** (vida 180) →
**0.20** (vida 300, ventana arreglada). El encogimiento estaba apagando
ruido que el modelo fabricaba por falta de historia, no un exceso de
confianza propio. Cuando se dijo el 2026-08-25 que "la tendencia no
siguió", estaba medido con la ventana rota; con la buena, sigue.

**Sigue sin aplicarse, y sigue siendo decisión de producto** — cambia
qué partidos quedan marcados e interactúa con `VALOR_MIN`. Lo que falta
antes de decidir es medir el efecto sobre las marcas, que es lo que §5
tampoco pudo.

### Addendum · el encogimiento no se aplica, y ahora con la medición que faltaba (2026-08-25)

§5 dejó pendiente lo único que decidía: **cuántas marcas de valor
cambian**. Aquella vez se intentó y se descartó el número por
implausible ("36% de todas las opciones marcadas") porque la cuenta no
replicaba `marcaDeValor()` ni `escalera()`. Ahora está medido en serio.

**Cómo, para no repetir el error.** No se reimplementó nada: un script
en Node carga el `index.html` publicado igual que `test_alineacion.js` e
inyecta el encogimiento en **una sola línea** de `lectura()` — la que
arma las tres probabilidades del 1X2. `escalera()`, `FRANJAS`,
`contradice()`, `incompatibles()`, `marcaDeValor()`, `alerta()` y
`devigShin()` corren tal cual están publicados.

**Sobre la grilla del día** (29 partidos): cero cambios en 1X2, cero en
la escalera, una alerta terracota más. Pero no hay ninguna marca 1X2
encendida para empezar —exige `inclinacion` cargada a mano y hay 18
análisis— así que la muestra no aguanta ninguna conclusión.

**Sobre 2583 partidos de arg desde 2022**, contando las opciones que
caen en la ventana `[VALOR_MIN, VALOR_MAX]` = [0.06, 0.12]:

| | sin encoger | con k=0.20 |
|---|---|---|
| opciones marcadas | 836 | 883 |
| acierto | 28.3% | 24.6% |
| ROI al cierre de Pinnacle | −3.27% ±6.19 | −3.43% ±6.41 |

**Cambia el 43% de las marcas** (213 se apagan, 260 se encienden, 623
sobreviven). O sea que no es cosmético: es casi la mitad de las
apuestas señaladas.

Y la comparación que decide — lo que entra contra lo que sale:

| grupo | n | acierto | ROI al cierre |
|---|---|---|---|
| se apagan | 213 | 38.0% | +6.77% ±12.80 |
| sobreviven | 623 | 25.0% | −6.70% ±7.06 |
| se encienden | 260 | 23.5% | +4.42% ±13.73 |

**Lo que entra menos lo que sale: −2.35% ±18.78.** No se despega del
ruido ni de lejos. Con esta muestra, cambiar el 43% de las marcas **no
se distingue de barajar y dar de nuevo**.

### Decisión: NO se aplica

Encoger mejora el Brier de forma real y significativa (§6vicies semel),
y aun así **no hay evidencia de que mejore lo que la app recomienda**.
Es exactamente la trampa que este repo ya documentó una vez: se pasaron
tres semanas midiendo calibración y ninguna midiendo si daba plata.
Mejorar el Brier y ganar plata no son la misma cosa, y acá se ve por
qué — el encogimiento mueve las probabilidades una mediana de 0.0086,
que contra una ventana de valor de 0.06 de ancho alcanza para cruzar el
borde en muchos casos, pero cruzar el borde no es acertar.

Queda medido, con su script y sus tests, para que nadie lo vuelva a
proponer sin este número enfrente.

**Salvedad del ROI:** está calculado a la cuota de **cierre** de
Pinnacle, el precio más difícil que existe. Sirve para comparar las dos
versiones entre sí —el mismo precio en los dos casos— no para estimar
lo que da la app, que apuesta antes y a otra casa.


## 6vicies bis · Calibrar no es saber: publicábamos el promedio de la liga (2026-08-25)

Lucas pidió avanzar sobre el mercado de estadísticas — córners,
tarjetas, faltas, remates, y sobre todo líneas de jugador. Su reclamo,
textual: *"no tenemos un analisis para eso, simplemente las
estadisticas volcadas, ni sugerencias ni consejos"*.

Antes de escribir consejos había que ver si los números sabían algo. No
saben.

### El camino, porque el primer diagnóstico fue mío y estaba mal

`calibracion_lineas.json` reportaba faltas con **−9,0 puntos** de sesgo
y remates con **+6,6**. Se dijo en el chat que eran "sesgo casi puro, o
sea corregible restando". **Falso**, y se vio apenas se midió el sesgo
en el número crudo en vez de en la probabilidad:

    faltas    decimos 11,33   hubo 12,11   (segunda mitad: 11,86 vs 12,10)
    remates   decimos 14,06   hubo 13,81
    córners   decimos  4,84   hubo  4,78

El valor esperado no está corrido. Así que el sesgo de probabilidad
venía de otro lado.

### Lo que había en cambio

La recta de lo real contra lo predicho da **pendiente ≈ 0** en córners,
remates, al arco y tarjetas. No hay nada que correlacionar, y el motivo
se ve mirando qué publica la app para los 68 equipos del caché:

    córners    de 4,70 a 4,96      (un cuarto de córner entre todos)
    remates    de 13,75 a 13,99
    al arco    de 4,19 a 4,30

**Le publicamos el promedio de la liga a todos los equipos.**

No es un bug. `parametros_metricas()` devuelve `k = K_TOPE` cuando la
separación entre equipos no supera el ruido de promediar pocos
partidos, y su comentario ya lo decía: *"Mostrar 12.5 contra 18.7 como
si fuera una diferencia real es mentir con decimales."* El código es
honesto. Lo que faltaba era que alguien lo mirara — y la calibración no
lo delataba, **al contrario: lo premiaba.** Publicar el promedio de la
liga calibra perfecto por definición.

De ahí `medir_discriminacion.py` (30 tests), que mide lo que
`medir_lineas.py` no podía ver.

### La medición, con el techo de ruido al lado

189 partidos, ~4 por equipo:

| métrica | separan | k | spread | vs ruido | |
|---|---|---|---|---|---|
| posesión | 32,03 | 3,5 | 16,20 | **1,12** | **señal real** |
| tackles | 6,72 | 4,5 | 8,08 | **0,87** | **señal real** |
| faltas | 1,24 | 13,3 | 2,21 | 0,29 | dentro del ruido |
| offsides | 0,16 | 13,3 | 0,96 | 0,29 | dentro del ruido |
| tarjetas | 0,07 | 21,2 | 0,41 | 0,19 | dentro del ruido |
| córners | 0,03 | 200 | 0,14 | 0,02 | no se ve |
| remates | −1,56 | 200 | 0,23 | 0,18 | no se ve |
| al arco | −0,02 | 200 | 0,11 | 0,01 | no se ve |
| atajadas | −0,26 | 200 | 0,10 | 0,26 | no se ve |

**Techo de falsa señal: 0,47.** Sale de simular ligas de equipos
IDÉNTICOS con esta misma muestra y ver hasta dónde llega el estimador
por puro azar. Es la regla del repo aplicada acá — comparar contra el
ruido, no contra cero.

Y el techo hacía muchísima falta, porque el estimador es malísimo con
poca muestra. Sobre 40 ligas de equipos idénticos:

    partidos por equipo   :   4     10     20     40
    reportó "se distingue": 14/40  3/40   0/40   0/40

**Con 4 partidos por equipo inventa una diferencia el 35% de las
veces.** Por eso `faltas` y `tarjetas`, que el `k` da por buenas, no
cuentan: no superan lo que producen equipos iguales por casualidad.

### Qué significa

**Hoy no hay ninguna métrica con mercado que tenga señal demostrable.**
Las dos que la tienen —posesión y tackles— no se apuestan en ningún
lado.

Y hay un patrón que ordena todo: **se distingue el estilo, no el
resultado.** Cuántas faltas hace un equipo o cuánto presiona es una
decisión suya que repite cada semana. Cuántos remates termina tirando
depende del rival, del marcador y de si va ganando y se echa atrás.

### Qué NO se hizo, a propósito

- **No se tocó el `k` de `actualizar.py`.** El estimador acepta ruido
  como señal el 35% de las veces con esta muestra, y eso es un hallazgo
  real sobre el código de producción. Pero corregirlo hoy sería
  sobreactuar: faltas y tarjetas son estables en la literatura, y
  encogerlas al tope también sería equivocarse. Queda anotado.
- **No se escribieron consejos.** Era el pedido, y es lo que no
  corresponde todavía: aconsejar sobre córners cuando le publicamos el
  mismo número a los 68 equipos sería inventar autoridad.

### Lo que destraba esto es tiempo, no código

El piso de detección baja con los partidos acumulados:

| | hoy (pj≈4) | pj=10 | pj=20 | temporada (pj=38) |
|---|---|---|---|---|
| córners | 1,64 | 0,82 | 0,41 | **0,22** |
| faltas | 3,28 | 1,64 | 0,82 | **0,43** |
| remates | 6,74 | 3,37 | 1,69 | **0,89** |

El cron viene juntando desde mayo. Con una temporada completa el piso
baja 7,6 veces, y las métricas que hoy dicen "no se ve" pueden estar
diciendo "todavía no". Correr `medir_discriminacion.py` cada tanto es
lo que avisa cuándo cambió.

---

## 6vicies ter · El mercado de estadísticas existe, y estaba a un link de distancia (2026-08-25)

### Lo que se afirmó, y era falso

El 2026-08-25, contestando si se podía atacar el mercado de córners y
de jugadores, esta terminal afirmó que no existía fuente gratuita de
cuotas de córners ni de tarjetas en ningún lado.

**Es falso.** Están en el mismo ESPN que el cron ya llama dos veces por
día, sin clave y sin costo.

El error tiene una causa concreta y vale más que el hallazgo. Se miró
el bloque `odds` del *scoreboard* — que efectivamente trae solo 1X2,
hándicap y over/under de goles — y se dio el tema por cerrado. Nunca se
siguió el link `propBets` que el propio objeto de odds de la API
interna publica:

    sports.core.api.espn.com/v2/sports/soccer/leagues/{liga}
        /events/{id}/competitions/{id}/odds/100/propBets

Son **150 a 840 líneas por partido**. La lección ya está escrita en
CLAUDE.md: mirar un endpoint y concluir sobre *la fuente* es
generalizar de una muestra de uno.

### Qué hay, medido sobre partidos ya jugados

El board queda congelado después del partido, así que se puede auditar
hacia atrás. Sobre los 30 partidos de Liga Profesional de los últimos
12 días:

| Mercado | Cobertura en arg.1 |
|---|---|
| Córners (total, por equipo, hándicap, 1er/2do tiempo, primero/último, carrera a N) | **30 de 30** |
| Goleador (primero, en cualquier momento, último, 2+) | **30 de 30** |
| Remates, al arco, faltas, tackles, offsides, tarjetas | **0 de 30** |

**Los córners están en todas las ligas medidas** (28 líneas por
partido; la única excepción es China, con cero). Las estadísticas de
JUGADOR están en muy pocas:

    Inglaterra 41 jug/partido · Italia 38 · Championship 35 · Francia 27
    España 19 · Escocia 10 · EEUU 4 · México 2 · Brasil 1
    Argentina, Japón, Austria, Portugal, Noruega, Bélgica,
    Dinamarca, P. Bajos, Turquía, Suecia: CERO

No es cuestión de esperar a que se acerque el partido: se probaron los
30 partidos argentinos con el board ya cerrado. Cero en los 30.

### Los dos hallazgos que definen cómo se puede analizar

**1. Los córners vienen en par, y por eso se les puede sacar el
margen.** `Total Corners` 8.5 aparece dos veces (1.80 y 1.90): son el
más y el menos, los dos bajo la clave `over` del JSON. Con el par se
aplica `devigShin` como manda CLAUDE.md — en dos opciones Shin devuelve
el proporcional, que es correcto — y la comparación es probabilidad
contra probabilidad, igual que el 1X2.

**2. Las líneas de jugador vienen de un solo lado, y no se les puede
sacar el margen.** No existe el "menos de". Vienen en escalera
acumulada (1+, 2+, 3+), y una escalera acumulada es autoconsistente por
construcción: el margen no se puede despejar de ahí.

La salida se encontró midiendo: **DraftKings arma toda la escalera
desde un solo Poisson**, y el ajuste es casi perfecto.

    Grealish  1+ 1.10 · 2+ 1.47 · 3+ 2.40  ->  Poisson(2.34)  error 0.0013
    Kovacic   1+ 1.34 · 2+ 2.55            ->  Poisson(1.34)  error 0.0008

O sea que se le puede leer **la cantidad esperada que el mercado tiene
en la cabeza**, y comparar cantidad contra cantidad. Eso esquiva el
problema del margen entero.

Dos límites que hay que respetar y mostrar:

- **Solo el 33% de las escaleras de remates tiene dos escalones o más**
  (tackles 49%, faltas 45%; asistencias y offsides casi ninguna). Con un
  escalón no hay dos ecuaciones y no se despeja nada. Para esos, la regla
  conservadora: marcar valor solo si le ganamos al precio **con el margen
  todavía adentro**. Menos marcas, ninguna inventada.
- **Cuando le vemos MENOS que la casa a un jugador, no hay nada que
  apostar**, porque no existe el under. La mitad de nuestras opiniones no
  son accionables, y la pantalla tiene que decirlo en vez de esconderlo.

### Por qué entraron Premier League y Ligue 1

Se midieron **tres** cosas sobre las 26 ligas del barrido anterior, y
hacían falta las tres a la vez:

|  | atraso (de 26) | jugadores/partido | k de córners |
|---|---|---|---|
| **eng.1** | 0.0137 (6º) | 41 | 14.2 |
| **fra.1** | 0.0147 (9º) | 27 | 23.0 |
| ita.1 | 0.0167 (20º) | 38 | — |
| esp.1 | 0.0164 (18º) | 19 | — |
| arg.1 | 0.0147 (11º) | 0 | tope (200) |

Italia y España tienen mercado profundo **y el modelo anda mal ahí**.
Mercado grande donde peor jugamos no es una oportunidad. Japón y México
son 1º y 2º en atraso y no tienen mercado de jugadores.

**La tercera columna es la que decide.** `ARG.csv` y `BRA.csv` no traen
ni una columna de estadísticas por partido; `E0` y `F1` las traen todas
en 11 temporadas. Con 246 partidos por equipo, el `k` de córners baja
de 200 —el tope, que es la forma honesta de decir "no distingo un
equipo de otro"— a 14. Es exactamente el bloqueo descrito en §6vicies
bis, y en Inglaterra no existe desde el día uno.

Corrido sobre eng/fra/sco, las cinco métricas (córners, remates, al
arco, faltas, tarjetas) superan el techo de falsa señal en las tres
ligas. **15 de 15.**

### Constantes, medidas y no copiadas

Barridos walk-forward propios sobre 4180 y 3857 partidos con cuota de
cierre de Pinnacle, eligiendo con datos < 2022 y evaluando en >= 2022:

    eng.1   rho -0.02   prior 5   conf 80   corners 10.33  fouls 21.51  cards 3.91
    fra.1   rho -0.05   prior 8   conf 80   corners  9.47  fouls 24.22  cards 3.98

**Captura de la ventaja del mercado, fuera de muestra: 80.9% y 80.9%**,
contra 45.4% de Brasil y 7.7% de Argentina. Atraso 0.01470 ± 0.00298 y
0.01253 ± 0.00302.

**Ojo con el prior de Inglaterra.** El primer barrido (3, 8, 12, 20,
30) dio 3 — el borde de la grilla, o sea nada. Extendida a 0.5/1/2
apareció el óptimo adentro. Es la **tercera** vez que pasa en este
repo; la regla ya está en CLAUDE.md y hay que leerla antes de festejar
un barrido.

### Un bug caro que apareció de paso

football-data usa año de cuatro dígitos en casi todos sus archivos y de
**dos** en cuatro de ellos. El `except ValueError` de la fecha los
descartaba en silencio: **1521 partidos**, una temporada entera de
Inglaterra y tres de Francia. No rompía nada, no imprimía nada — solo
medía menos de lo que decía medir. Se encontró porque los totales no
cerraban contra un conteo hecho aparte. Arreglado, con test.

### Lo que está hecho y lo que falta

Hecho y verificado:

- `historico.py` lee los dos formatos y arrastra las estadísticas por
  partido. 56 tests.
- `actualizar.py`: las dos ligas en `COMPETICIONES`, `CON_FUERZAS` y
  `LIGAS_DOMESTICAS`; `index.html` sincronizado. 191 tests.
- Endpoints verificados en vivo para las dos: scoreboard, summary,
  roster, standings y cuota. El box score de jugadores llega igual.
- **Los IDs de jugador del mercado y los del plantel son el mismo
  namespace de ESPN: cruzan 30 de 31 (97%) sin tocar un nombre.**

Falta, en este orden:

1. ~~**Backtest de córners contra plata.**~~ **Hecho el 2026-08-25 — ver
   §6vicies quater.** La respuesta es que no: el total del partido está
   puesto en el punto de la moneda (empate en cero, 41 apuestas de las
   ~300 que harían falta) y el por equipo ya se sabe que no (2,2 errores
   estándar detrás del cierre, ROI negativo en los seis umbrales).
2. ~~Tabla de alias de equipos.~~ **Hecha el 2026-08-25 — ver
   §6vicies quinquies.** `equipos.py` cruza 19 de 20 en Inglaterra
   y 17 de 18 en Francia; los dos que faltan son ascendidos sin
   historia en primera. Con la historia enganchada, los equipos
   ingleses SI se distinguen en corners (k=11.6 contra el tope de
   200 del cache). Falta que alguien la consuma: ver el final de
   esa seccion.
3. La mitad de equipo en la app: precio y marca en `bloqueLineas`.
   **Sigue sin corresponder, pero por otro motivo que antes.** El punto 1
   la habia cancelado; el punto 2 bajo `k` de verdad (200 -> 11.6 en
   Inglaterra), que era la condicion para reabrirla. Lo que falta ahora
   es la medicion: **las ligas con linea de mercado juntada (arg, bra) no
   tienen estadisticas en el CSV, y las que tienen estadisticas (eng,
   fra) todavia no tienen lineas juntadas.** Hasta que el cron acumule
   `propBets` de eng/fra y se rehaga el backtest de §6vicies quater con
   el numero bueno, no se marca valor. `bloqueLineas` sigue mostrando el
   numero esperado, que es informativo y honesto.
4. La mitad de jugador, solo donde el mercado existe. **Bloqueada por
   tiempo, no por código**: Premier y Ligue 1 arrancaron temporada, hay 1
   partido por equipo en caché y 0 jugadores con 2 o más presencias, así
   que todavía no hay serie propia contra la cual medir. Es el mercado
   que más interesa y el único donde el modelo ya mostró discriminación
   real (pendiente 1,11 en remates) — pero medirlo hoy sería medir ruido.

### Addendum · Agregar ligas rompió los parámetros de estadísticas (2026-08-25)

Agregar `eng.1` y `fra.1` destapó un bug que ya existía y que las dos
ligas nuevas iban a agravar hasta hacerlo grave.

`parametros_metricas()` se corría **una sola vez sobre todo el caché**,
mezclando las competiciones. Con arg+bra era discutible; con cuatro
ligas pasa a ser incorrecto, y de la peor forma: **se ve como una
mejora**.

`k` sale de partir la variación entre equipos en ruido y señal. Si el
pozo tiene varias ligas adentro, la diferencia **entre ligas** entra
como si fuera diferencia **entre equipos**. Inglaterra hace 21.5 faltas
por partido y Argentina 25.5: esa brecha infla la señal, hace bajar `k`
y la app parece haber aprendido a distinguir equipos cuando lo único
que distingue es un país de otro. Para decidir si Chelsea hace más
córners que Brighton, saber que Brasil hace más que Argentina no aporta
nada.

Medido sobre el caché real (213 partidos), separando por liga:

| métrica | pozo mezclado | arg.1 | bra.1 |
|---|---|---|---|
| córners | 77.6 | **17.0** | **200.0** |
| tarjetas | 14.8 | **200.0** | **5.3** |
| al arco | 55.4 | **200.0** | **10.1** |
| tackles | 4.9 | **45.5** | **4.2** |

*(k alto = "no distingo un equipo de otro"; 200 es el tope.)*

**El número mezclado no describía a ninguna de las dos, y en tarjetas y
al arco daba la conclusión opuesta a la verdadera para cada liga.** La
app le venía publicando a los equipos argentinos números propios de
tarjetas y de remates al arco apoyada en un `k` que era señal de
Brasil. O sea: inventaba diferencias por equipo que sus propios datos
no sostienen.

Sobre dos ligas sintéticas de equipos **idénticos entre sí** pero con
medias distintas, el pozo mezclado da `k = 0.1` — "creele todo al
promedio del equipo" — cuando la respuesta correcta es el tope.

**El arreglo:** `parametros_por_liga(muestras, liga_de_equipo)` calcula
los mismos parámetros dentro de cada liga, usando el mapa
`data/cache_ligas.json` que el cron ya mantiene (cero pedidos nuevos).
Una liga con menos de `MIN_EQUIPOS` queda **afuera** y quien la consuma
cae al parámetro global — peor, pero honesto sobre su incertidumbre.

Es aditivo: `estadisticas.json` sigue trayendo `parametros` y ahora
suma `parametros_liga`; cada equipo trae además su `liga`. El frontend
elige con `paramsDe()`, que cae al global cuando los dos equipos de un
partido no comparten liga (copas).

**La lección, que es la misma de §6vicies bis por tercera vez:** un
número que mejora no es un número que mejoró. `k` bajando de 200 a 77
parecía progreso y era contaminación. Antes de festejar que una métrica
"ahora sí distingue", hay que preguntarse *entre qué* está
distinguiendo.

Y una de método: el test de esto **no** se escribió contra un umbral
absoluto de `k`. Con 12 equipos de 6 partidos el estimador rebota entre
3 y 200 según la semilla — la misma banda de ruido que documenta
`test_medir_discriminacion.py`. Lo que se testea es la **relación**
(separar por liga siempre da menos confianza que mezclar) y la mediana
sobre 20 semillas. Un umbral mágico adentro de la banda de ruido no
mide nada; ya se cometió ese error dos veces en este repo.

---

## 6vicies quater · Córners contra plata: el total no se puede saber, el por equipo ya se sabe que no (2026-08-25)

Primera vez que un mercado de estadísticas se mide contra **ROI** y no
contra calibración. Es la regla que ya costó tres semanas con el modelo
de goles, aplicada a tiempo esta vez.

Walk-forward estricto, línea de cierre real de DraftKings (endpoint
`propBets`), margen quitado, resultado real del caché.

### Total del partido: empate en cero

81 líneas de arg.1 y bra.1.

| | Brier | sobre la moneda |
|---|---|---|
| Moneda (siempre 50%) | 0.2500 | — |
| **Mercado** | 0.2492 | **+0.0008** |
| **Modelo** | 0.2518 | **−0.0018** |

atraso contra el cierre: **+0.0026 ± 0.0097** — indistinguible.

**La casa pone la línea justo en el punto de la moneda.** El mercado
casi no tiene información y cobra **8.4% de margen**. Decir "estamos a
la par del mercado" acá suena a logro y es un empate en cero.

El ROI daba +11.2% con umbral 6%, sobre **41** apuestas, con ±13.9% de
azar. Es ruido: harían falta ~300 apuestas. Ese número está en un test
de `test_medir_corners.py` que exige que NO salga marcado como
significativo.

### Por equipo: acá sí se sabe, y es que no

187 líneas, 120 partidos. Casi el triple de muestra.

| | Brier | sobre la moneda |
|---|---|---|
| Moneda | 0.2500 | — |
| **Mercado** | 0.2432 | **+0.0068** |
| **Modelo** | 0.2638 | **−0.0138** |

atraso contra el cierre: **+0.0205 ± 0.0093** — **2.2 errores estándar
detrás**. Eso ya no es empate: es estar medidamente peor.

Y el ROI es negativo en **los seis** umbrales, con notable estabilidad:

    umbral   2%     4%     6%     8%    10%    15%
    n       160    142    119    106     90     47
    ROI   -9.5%  -9.7% -10.9% -10.2% -10.9% -11.6%

Ninguno es significativo por separado (±7.4% a ±13.8%), pero seis
umbrales apuntando al mismo lado con muestras que van de 47 a 160 no se
lee como azar.

### Por qué el por equipo es PEOR que el total

Es §6vicies bis cobrado en plata. Nuestro número por equipo está
encogido casi todo hacia el promedio de la liga (`k` de córners: 17 en
Argentina, 200 en Brasil), o sea que **le apostamos el promedio de la
liga a una casa que sí distingue equipo por equipo**.

Y se ve en los Brier: en el total del partido el mercado apenas le gana
a la moneda (+0.0008), porque ahí no hay mucho que saber. En el por
equipo el mercado le gana ocho veces más (+0.0068) — hay información
real que capturar, y nosotros no la tenemos.

**Conclusión: no corresponde marca de valor en córners, ni de total ni
de equipo.** El total no se puede saber todavía; el por equipo ya se
sabe, y la respuesta es no.

### Qué haría falta para que cambie

Para el por equipo, lo mismo que §6vicies bis: muestra suficiente para
que `k` baje y el número deje de ser el promedio de la liga. En
Argentina son ~20 partidos por equipo y hoy hay 7. En Inglaterra el
problema no existe (246 por equipo en los CSV), pero esos datos todavía
no alimentan el modelo — hace falta la tabla de alias de equipos.

Para el total, ~300 apuestas marcadas. Hoy hay 41.

---

## 6vicies quinquies · Los equipos ingleses SÍ se distinguen, y lo único que faltaba era el nombre (2026-08-25)

Punto 2 de la lista de pendientes, hecho. Es el que destrabó algo.

### El problema, en una línea

`historico.py` tenía 4180 partidos de Inglaterra y 3857 de Francia **con
estadísticas por partido** — ~296 por equipo. El caché de ESPN que
alimenta al modelo tiene 5 u 8. Lo único que ataba las dos fuentes era
el nombre del equipo, y no coinciden: el CSV dice "Man City", ESPN dice
"Manchester City".

### Lo que NO se hizo, y es la mitad del trabajo

El atajo obvio era cruzar por parecido: prefijo, distancia de edición,
subcadena. No se hizo, y no por prolijidad.

**En Ligue 1 juegan Paris Saint-Germain y Paris FC la misma temporada, y
el CSV trae a los dos: 395 partidos contra 34.** Cualquier cruce difuso
le pega la historia de uno al otro. Y ese error no se ve: no tira
excepción, no baja un contador, no deja un hueco. Se ve como datos. Un
nombre sin cruzar se nota; uno mal cruzado, no.

Entonces `equipos.py` cruza **solo por igualdad exacta** después de
normalizar (minúsculas, sin acentos, sin puntuación), contra los tres
nombres que ESPN publica: `displayName`, `shortDisplayName` y `name`.
Dos decisiones más, cada una con su test:

- **No se cruza por abreviatura**, aunque ESPN la traiga. Brentford
  (eng) y Brest (fra) son los dos "BRE".
- **Si dos equipos reclaman el mismo nombre, ese nombre queda afuera**
  del índice. La alternativa —quedarse con el último que pasó— es
  exactamente la que convierte un choque en una historia mezclada sin un
  solo aviso.

### La tabla a mano es de tres entradas, no de quince

El impulso era transcribir los 15 nombres que no coincidían. Mirando la
fuente primero: **ESPN ya publica `shortDisplayName`, y eso resuelve
12** — "Wolves", "Man City", "Man United", "Leeds", "Brighton",
"Bournemouth", "Newcastle", "West Ham", "Monaco", "Rennes", "Auxerre",
"Nottm Forest". Uno más ("Nott'm Forest") sale solo con borrar el
apóstrofo en vez de convertirlo en espacio — es una contracción de
"Nottingham", y separarlo daba "nott m forest", que no cruza con nada.

Quedaron **tres** entradas escritas a mano, y cada una lleva el motivo
al lado:

    "tottenham" -> "Tottenham Hotspur"      ESPN lo acorta a "Spurs"
    "paris sg"  -> "Paris Saint-Germain"    ESPN lo acorta a "PSG"
    "le havre"  -> "Le Havre AC"            ESPN le deja el "AC"

Cada entrada a mano es una que hay que mantener el día que la fuente
cambie. Doce menos es doce menos.

### El cruce, medido

    eng.1   19 de 20 equipos          fra.1   17 de 18 equipos

Los dos que faltan son **Coventry City** y **Le Mans**: ascendidos que
no pisaron primera en las once temporadas que tenemos. No es un alias
que falta, es historia que no existe.

(Los números viejos del traspaso —17/23 y 14/21— salían de otra
comparación y no eran estos.)

### El hallazgo: los equipos ingleses se distinguen

Con la historia enganchada, `parametros_metricas()` corrido **dentro de
cada liga** (la regla de §6vicies ter):

| métrica | eng, 11 temp. | eng, 3 temp. | fra, 11 temp. | fra, 3 temp. |
|---|---|---|---|---|
| córners | **11.6** | **10.1** | 21.6 | 16.3 |
| remates | **6.8** | **7.3** | 10.5 | **6.8** |
| al arco | **8.4** | 10.3 | 9.7 | **7.3** |
| faltas | 33.3 | 13.7 | 18.1 | 10.7 |
| tarjetas | 48.6 | 32.3 | 80.5 | 33.7 |

*(k bajo = "sí distingo un equipo de otro". El tope es 200.)*

Contra el caché de ESPN, donde córners daba **17.0 en Argentina y el
tope de 200 en Brasil**.

Y lo que cambia no es `k` a secas, es el peso: `n/(n+k)`. Con 5 partidos
y k=200, el número del equipo pesa **2%** — publicamos el promedio de la
liga. Con 296 partidos y k=11.6, pesa **96%**.

### El techo de ruido, porque acá siempre hay que mirarlo

`k` bajando podría ser un artefacto de tener más muestra. Se simularon
**19 equipos idénticos entre sí**, con la misma dispersión por partido y
los mismos 296 partidos, sobre 40 semillas:

    equipos identicos:  k mediano 200.0, minimo 200.0   (40 de 40)
    REAL (eng córners): k = 11.6

El estimador no puede fabricar señal con esta muestra: devuelve el tope
siempre. El 11.6 es real.

Y la diferencia entre equipos es concreta, no estadística: de **3.82 a
7.16 córners por partido** entre el que menos y el que más. Casi el
doble. Eso es exactamente lo que una casa de apuestas cobra por saber.

### Lo que esto NO prueba

**No prueba que ahora se le gane al mercado de córners.** §6vicies
quater midió que apostar córners por equipo perdía ~10%, y diagnosticó
la causa: le apostábamos el promedio de la liga a una casa que
distingue equipos. Esto **remueve la causa conocida**; no demuestra que
no haya otras.

Y hay un problema de calendario que hay que decir en voz alta: **las
ligas donde tenemos línea de mercado (arg, bra) no tienen estadísticas
en el CSV, y las ligas donde tenemos estadísticas (eng, fra) todavía no
tienen líneas juntadas.** ARG.csv y BRA.csv no traen ni una columna de
estadísticas en 11.855 partidos. Así que el backtest de córners con el
número bueno **no se puede correr hoy** — hace falta que el cron junte
`propBets` de eng/fra durante unas semanas.

Es la misma disciplina de siempre: esto es un resultado intermedio
prometedor, no plata.

### Lo que falta para que lo use la app

`equipos.py` cruza; nadie lo consume todavía. El camino corto y sin
tocar el camino caliente del cron:

1. Un script a mano que escriba `data/historia_equipos.json` con las
   muestras por equipo ya cruzadas a id de ESPN — el mismo patrón que
   `data/calibracion_jugadores.json`.
2. `actualizar.py` lo lee si está y lo suma a las muestras del caché
   antes de `parametros_por_liga()`. Aditivo: si el archivo no está, se
   comporta como hoy.

Lo que **no** conviene es que el cron baje los CSV: son 22 pedidos por
corrida a una fuente que cambia una vez por semana, metida en el camino
que corre dos veces por día.

### Addendum · La historia enchufada, y un bug que salió al pasar (2026-08-25)

`equipos.py` cruzaba y nadie lo consumía. Ahora sí.

**`historia_equipos.py`** escribe `data/historia_equipos.json`: por
equipo y por métrica, `n`, `suma` y `suma2`. De esos tres salen la media
y la varianza exactas — que es todo lo que `parametros_metricas()` y
`media_encogida()` necesitan — y el archivo pesa **18 KB** en vez de los
80.000 números sueltos.

Se corre **a mano**, y eso es una decisión, no una pendiente: serían 22
descargas de football-data por corrida, dos veces por día, para un
archivo que cambia una vez por semana.

**`actualizar.py`** lo lee con `leer_historia()`. Si no está, devuelve
`{}` y todo aguas abajo se comporta como antes de que existiera. Tres
funciones nuevas, cada una con tests:

- `params_con_historia()` — pisa **métrica por métrica**, no la tabla
  entera. De football-data salen córners, remates, al arco, faltas y
  tarjetas; posesión, tackles, offsides y pases solo existen en el caché
  de ESPN, y pisar la tabla completa los borraría.
- `prior_equipo()` — el ancla de un equipo: su historia encogida hacia
  la liga con el mismo `k` que después encoge la temporada en curso
  hacia el ancla. Sin historia devuelve `{}`.
- `params_de_partido()` — ver más abajo.

Y `esperados()` / `esperado_partido()` toman el ancla como argumento
opcional. Sin ella, byte por byte lo de antes; hay tests de regresión
que lo fijan.

#### El número que cambia

    Manchester City, córners
      ancla vieja (promedio de la liga)      5.46
      ancla nueva (418 partidos propios)     7.11

    Ipswich Town                             3.82
    PSG                                      6.07

El orden que sale del cruce es el que cualquiera que mire fútbol
esperaría —City arriba, los ascendidos abajo, PSG primero en Francia—
y eso es en sí una verificación: un cruce roto habría dado un ranking
sin sentido.

#### El bug que salió al pasar

`esperado_partido()` se llamaba con `parametros` **global**, no con los
de la liga. O sea: el arreglo de §6vicies ter —el del pozo mezclado—
había llegado a `pr["esperado"]`, que alimenta las líneas de la pestaña
Estadísticas, y **no** a esta otra ruta, que es la que alimenta el total
de córners de la tarjeta del partido.

La misma métrica se calculaba con dos varas distintas según dónde se la
mirara, y **la más visible usaba la mala**. Es exactamente la clase de
contradicción que este repo ya arregló dos veces (§6vicies con el
devig, §6vicies ter con el pozo) y que vuelve a aparecer cada vez que
un arreglo se aplica en un lugar y no en todos.

Arreglado con `params_de_partido()`, que replica la regla de `paramsDe()`
del frontend: si los dos equipos comparten liga y esa liga tiene
parámetros propios, gana la liga; si no —copas, que cruzan países— cae
al global.

**La lección de método:** cuando una corrección se aplica, hay que
buscar todos los llamadores, no el que motivó el hallazgo. `grep` del
nombre de la función habría encontrado este en diez segundos.

#### Lo que NO cambia

- arg.1 y bra.1 no tienen historia y no la van a tener: la fuente no
  trae estadísticas de esas ligas. Ahí el ancla sigue siendo el promedio
  de la liga, igual que hoy. El archivo lo dice en `sin_estadisticas`.
- El frontend no se tocó. Lee `L.esperado` ya calculado, así que el
  ancla le llega sola.
- **Sigue sin haber marca de valor en córners.** Esto mejora el número;
  no demuestra que le gane a una casa. Ver el punto 3 de la lista de
  pendientes.

#### Cuándo hay que volver a correrlo

Cuando cambian los ascensos y descensos. El índice se arma contra el
standings **actual**, así que un equipo que descendió deja de cruzar y
uno que ascendió aparece sin historia hasta la próxima corrida. Hoy
Coventry City y Le Mans están así: ascendieron y no pisaron primera en
las once temporadas que tenemos.

### Addendum · Solo líneas binarias, y DraftKings sigue siendo la referencia (2026-08-26)

Dos correcciones antes de cablear `mercado_extra.py` a la app.

**Bet365 cotiza líneas que no son binarias.** De 16 líneas de gol,
solo 7 son X.5 (gana/pierde limpio). Las de cuarto (2.25, 2.75...)
reparten la apuesta en dos mitades; las enteras (2, 3, 4...) pueden
empatar y devolver ("push"). Todo el motor de la app —`TESTS` en
`index.html`, el Brier de `medir_corners.py`, el registro de
pronósticos— asume binario. Compararlo contra una de esas no tira
error: da un EV mal calculado sin avisar, que es peor que no tener la
línea. `binaria()` las saca antes de que lleguen a nada. Verificado
contra la API real: de las 16 de Unión–Sarmiento quedan 7 (0.5 a 6.5).

**DraftKings sigue siendo la referencia del 1X2.** Medido sobre 43
partidos cruzados por fixture entre las dos casas:

    margen medio DraftKings   7.15%
    margen medio Bet365       7.89%
    diferencia: +0.74pp ± 0.26pp (significativo, no ruido)

    diferencia de probabilidad devigada (Shin) entre las dos casas:
    media 1.55pp, maxima 3.68pp — nunca cerca del umbral de 6pp

DraftKings es más ajustado, y cambiar de referencia no hubiera movido
ninguna marca en estos 43 partidos. Se decidió NO tocar la referencia
del 1X2: sigue siendo DraftKings, como siempre. Bet365 entra solo
donde DraftKings no tiene nada (el resto de las líneas de gol,
córners, jugadores, ambos marcan, doble oportunidad cotizada) — así
ningún mercado queda con dos varas compitiendo, porque no se
superponen en ninguno.

Falta: cablear `mercado_extra.py` a `actualizar.py` y a la interfaz.

### Addendum · `mercado_extra.py` cableado al cron (2026-08-26)

`actualizar.py` ahora llama a `mercado_extra.py` por cada partido, con
dos funciones puras y testeadas en `test_actualizar.py` (8 tests):

- `eventos_extra(slug, key, cache)` — un pedido por liga, cacheado por
  corrida; si la red falla, devuelve `[]` y esa liga simplemente no
  cruza nada.
- `mercado_extra_de(partido, eventos, key)` — cruza por fixture y pide
  los mercados de ese evento; si falta la clave, no hay eventos, el
  fixture no cruza, o el pedido falla, devuelve `None` sin tirar.

El resultado se escribe como campo nuevo y aditivo,
`partido["mercadoExtra"]` (`{}` si no hay nada) — `mercado` (la
referencia de DraftKings) no se toca, así que ningún contrato
existente cambia. Sin `ODDS_API_KEY`, `ME.clave()` devuelve `None` y el
loop entero se salta: cero pedidos nuevos, cero campos nuevos con
contenido, la app queda bit a bit igual que antes de este trabajo.

Falta: mostrarlo en la interfaz.

### Addendum · `mercadoExtra` en la interfaz (2026-08-26)

Dos cambios en `index.html`, verificados en el navegador con un
partido de prueba (datos sintéticos, restaurados después — nunca
tocaron `data/partidos.json` en el repo):

- **Goles y ambos marcan, con precio real.** `TESTS` pasó de tres
  líneas fijas (1.5/2.5/3.5) a las siete que Bet365 cotiza en binario
  (0.5 a 6.5). `mercados()` agrega las que además tengan cruce real
  para ESE partido; sin clave o sin cruce, un partido se ve exactamente
  igual que antes (verificado: 0 líneas de más sin `mercadoExtra`).
  `pMercado()` ahora prueba Bet365 primero (Shin, dos vías) y solo cae
  a DraftKings si Bet365 no tiene esa línea puntual. "Ambos marcan"
  tenía cero respaldo real desde siempre — ahora lo tiene.
- **Córners de Bet365, informativo, sin marca de valor — a propósito.**
  Nueva sección en la pestaña Estadísticas, al lado de "Chance de pasar
  la línea" (que es estimación nuestra). Muestra el precio real del
  partido y por equipo, ya sin margen, con una nota explícita: no se
  marca como valor porque `medir_corners.py` ya midió que el córner por
  equipo le pierde plata al mercado. Enseñar el número sin la
  advertencia hubiera prometido una ventaja que se midió que no existe.

4 tests nuevos en `test_alineacion.js` (73 en total), `test_registro.js`
sin tocar (22, sigue en 0 fallando). La escalera de remates de jugador
(~50 por partido) queda afuera de este paso — es una pantalla aparte,
no una fila más.

### Addendum · Herramientas ya no pide tipear lo que ya tenemos (2026-08-26)

Lucas usa Bet365. Herramientas (la pestaña de staking/Kelly) le pedía
cargar la cuota a mano para TODO, 1X2 incluido, aunque ya bajáramos la
referencia de DraftKings — a propósito, porque esa referencia no es
apostable en Argentina. Bet365 sí es la casa real del usuario, así que
`cuotaReal(m, op)` la deja precargada (1X2, doble oportunidad, goles,
ambos marcan) cuando hay cruce, editable si le pagan distinto en el
momento — y `anotar()` usa esa misma cuota si el campo quedó sin tocar,
así que "Anotar en Registro" funciona sin que el usuario haya escrito
un solo número. Sin cruce, sigue pidiendo la carga manual, igual que
siempre.

Verificado en el navegador: anotó una apuesta a "Gana Independiente del
Valle" con cuota 2.0 sin tipear nada, y quedó guardada así en el
registro. 5 tests nuevos en `test_alineacion.js` (78 en total).

Pendiente, ya con visibilidad: si conviene *escribir* la cuota real en
`CUOTAS` (localStorage) en vez de solo mostrarla — hoy es puramente una
sugerencia de render, nunca se persiste sola. Se decidió así para no
mezclar "lo que el usuario cargó" con "lo que le sugerimos" en el mismo
storage sin que él lo pida.

### Addendum · Por qué no hay backtest de jugador todavía (2026-08-26)

El plan era medir remates/al arco contra plata real, como se hizo con
córners. Se cayó al primer chequeo, y vale la pena dejar escrito por
qué: `v3/events` de odds-api.io para ligas domésticas (probado sobre
arg.1) devuelve **150 eventos, los 150 pendientes** — el primero recién
el 28/8. `status=settled` da cero, y no existe un endpoint de eventos
históricos (`historical/events` da 400). Para Libertadores/Sudamericana
sí funciona — son llaves de pocos partidos, la fuente los deja
visibles después de jugados — pero para las ligas de todos-contra-
todos, el `id` del evento deja de estar disponible en cuanto el
partido se juega. Sin `id` no hay `historical/odds` posible, aunque
el endpoint funcione (se probó y anda, con el partido de Independiente
del Valle).

Conclusión: no hay historial de Bet365 esperando a que lo bajemos para
arg.1/bra.1. Hay que juntarlo desde ahora y medir dentro de unas
semanas. Se agregó `snapshot_props()` en `actualizar.py` (TDD, 5 tests
en `test_actualizar.py`, 13 en total), que guarda una foto de las
líneas de `mercadoExtra.remates`/`.al_arco` en `data/props_jugadores.json`
cada corrida — **cero pedidos nuevos**, el dato ya lo trae
`mercado_extra_de()`. Se acumula igual que `cuotas.json`, y solo agrega
una foto cuando la línea se movió.

Falta, para cuando haya semanas de fotos acumuladas: cruzar cada foto
contra el resultado real del jugador (`cache_disciplina.json._jugadores`,
que ya lo tiene) y medir ROI walk-forward, con el mismo criterio que
`medir_corners.py`. Hasta entonces, cero recomendaciones de jugador en
la interfaz — sería calibrar sin haber medido si sirve, justo lo que
este archivo prohíbe.

### Addendum · "Otros mercados" no mostraba la cuota real ni marcaba lo que ya podía marcar (2026-08-26)

Lucas lo encontró mirando la pantalla: cada fila de "Otros mercados"
seguía mostrando solo "conviene si te pagan más de X" — el umbral
teórico de nuestro propio modelo — sin la cuota real de Bet365 al
lado, aunque `otrosMercados()` ya la tuviera calculada (`ventaja`).

Y había un segundo problema, más de fondo: el dorado solo se encendía
en la ÚNICA fila que `escalera()` había elegido para su franja —
`esVal: o.id===marcadoId`. Con casi todo el mercado sin precio real,
eso nunca se notaba. Con `mercadoExtra` ya anda distinto: en el
partido de hoy (River–Santa Fe), además del pick de la escalera había
ventaja real en "Menos de 4.5 goles" y "Menos de 5.5 goles", y
`otrosMercados()` los devolvía con `ventaja` calculada pero `esVal:
false` — el pie de la pantalla prometía "marcamos en dorado cuando el
precio está a favor" y no lo cumplía.

Arreglado: `otrosMercados()` ahora evalúa cada fila con el mismo
criterio que `escalera()` (ventana `[VENTAJA_MIN, VALOR_MAX]`, regla de
alineación vía `contradice()`, análisis cargado) en vez de solo repetir
el pick de la escalera. El render muestra la cuota de Bet365 cuando
existe. Verificado en el navegador: 2 marcas nuevas en el partido de
hoy, ninguna contradice la inclinación (`E`). 2 tests actualizados y 2
nuevos en `test_alineacion.js` (80 en total).

### Addendum · Piso de cuota: "conviene si te pagan más de 1.05" no es una recomendación (2026-08-26)

El addendum anterior arregló QUE se marcara cada fila por su cuenta.
Este arregla CUÁL fila puede marcarse. Lucas lo encontró mirando el
partido de hoy: "Menos de 4.5 goles" quedó en dorado con Bet365
pagando **1.06**. Los números, exactos:

    modelo: 99.06%   Bet365: 1.062   ventaja: 8.66pp   EV: 5.2%

Matemáticamente pasaba el filtro — la ventana de ventaja [6,12]pp se
midió sobre 1X2, donde una cuota así de baja casi no existe. Estirada
a mercados que sí llegan a cuota 1.05-1.10 (líneas de gol lejos del
promedio), la misma ventana deja pasar apuestas donde hay mucho más
para perder que para ganar. Se verificó además una inconsistencia
aparte: `otrosMercados()` usaba `VENTAJA_MIN` (2pp, el piso para
CANDIDATEAR dentro de una franja) en vez de `VALOR_MIN` (6pp, el piso
real para MARCAR) — dos varas distintas para la misma pregunta.

Medido antes de decidir el número (no elegido a ojo): sobre la grilla
del día, un piso de 1.75 apagaba el 79% de las marcas activas (11 de
14, casi todas en la franja "Lo más probable" — que por diseño es la
que menos paga, así que perderlas no pierde información). Con 1.50,
apaga el 43% (6 de 14) — Lucas lo eligió después de ver los dos
números.

Se agregó `CUOTA_MIN_VAL = 1.50` y `cuotaUsada(op, pq, mk, mx)` —la
cuota cruda que `pMercado()` efectivamente comparó, no una aproximación
distinta— aplicado en `escalera()` (su propio `valor`) y en
`otrosMercados()` (ya usando `VALOR_MIN`, corregido). El piso frena la
marca INDIVIDUAL únicamente: la escalera y las combinadas siguen
eligiendo su pata por franja sin mirarlo, así que una cuota de 1.20
sigue disponible para armar una combinada — la discusión que lo generó
fue justamente esa distinción ("en combinadas 1.20 sirve, en
individual no llama la atención").

De paso se corrigió un bug chico: la rama de `escalera()` que se usa
cuando ninguna opción es "creíble" llamaba a `pMercado()` sin pasarle
`mx` — la ventaja de esa rama nunca veía precio de Bet365.

6 tests nuevos/corregidos en `test_alineacion.js` (82 en total).
Verificado en el navegador: las dos marcas de 1.06 y 1.01 del partido
de hoy desaparecieron y ninguna otra las reemplazó.

### Addendum · Pendiente real: pantalla de mercado de JUGADOR (2026-08-26)

Lucas quiere incursionar en el mercado de estadísticas, sobre todo del
lado **jugador** (remates, al arco, faltas, tarjetas) — le interesa
mucho más que a la app hoy le dedica (nada: hoy solo hay estadística
volcada, sin análisis ni sugerencia). No quiere cargar cuotas a mano,
solo mover con precio real (ya tenemos Bet365 vía `mercado_extra.py`).

**Se diseñó una sesión antes (2026-08-25), y no quedó ni una línea de
código.** El plan de esa sesión: leerle a DraftKings el Poisson que
tiene en la cabeza ajustando su escalera acumulada de remates (verificado
con error de ajuste ~0.001), separando equipo (córners, dos lados,
Shin) de jugador (un solo lado, sin margen despejable). Ese método
usaba ESPN/`propBets` — **sin verificar en el repo si `propBets` tiene
mercado de jugador**, sospecho que no (el único uso comiteado es de
córners de equipo).

Hoy ya existe una vía alternativa que esa sesión no tenía: `mercado_extra.py`
trae remates/al_arco de Bet365 con escalera propia, y `snapshot_props()`
ya está acumulando fotos para el futuro backtest (ver addendum de arriba,
"Por qué no hay backtest de jugador todavía"). Cuando haya crédito para
retomar esto, el camino más corto es construir la pantalla de jugador
sobre esos datos de Bet365 — no reconstruir el método DraftKings/propBets,
salvo que se verifique que aporta algo que Bet365 no tiene.

**Falta, en orden:**
1. Confirmar si `propBets` de ESPN tiene mercado de jugador (barato: un
   pedido de prueba). Si no, se descarta esa vía y se sigue solo con Bet365.
2. Esperar que `data/props_jugadores.json` acumule semanas de fotos.
3. Backtest de ROI walk-forward (mismo criterio que `medir_corners.py`).
4. Recién con eso medido, diseñar la pantalla — con marca de valor si
   gana, informativo si pierde, igual que córners hoy.

No hay atajo legítimo antes del paso 2 — es tiempo, no código.

### Addendum · La escalera repetía "Menos de X goles" en casi todo (2026-08-26)

Lucas lo notó mirando tres partidos seguidos: las tres franjas de la
escalera eran siempre líneas de gol, casi con los mismos números. Medido:
**115 de 135 franjas (85%) eran Goles**, y como consecuencia
`combinada()` — que necesita una pata de Resultado con p≥50% — dejó de
generar en 42 de 45 partidos (93%, contra 14/45 sin `mercadoExtra`).

**Causa, en dos capas:**

1. Hoy se extendieron las líneas de gol de 3 a 7 para darles precio real
   de Bet365 (ver addendum de "Otros mercados"). Eso multiplicó los
   candidatos de Goles en la escalera a 14 contra 8 de Resultado+Ambos.
   **Arreglo:** `LINEAS_ESCALERA` — la escalera vuelve a elegir su franja
   solo entre 1.5/2.5/3.5 (las líneas de siempre); las 7 completas
   siguen en `mercados()` para Otros Mercados y Herramientas.

2. Más de fondo, y preexistente (no es un bug de hoy): cuando ninguna
   opción de una franja es "creíble", se elige la más cercana al centro
   de la banda — y eso favorece a Goles siempre, con o sin Bet365,
   porque los totales de gol se reparten suave por toda la probabilidad
   mientras Resultado se agrupa en pocos valores correlacionados.
   Medido: **98 de 135 franjas (73%) se resolvían así**, no por ventaja
   real. **Arreglo:** `familiasUsadas` — al elegir por cercanía al
   centro, se prefiere una familia que todavía no ganó una franja
   anterior de este mismo partido, si hay opción ahí. Cuando SÍ hay
   ventaja creíble, no se toca: preferir variedad ahí sería elegir a
   propósito el pick peor.

**Con los dos arreglos:** Goles bajó de 115→95 franjas, Resultado subió
de 6→19, Ambos de 14→20. Repetir la misma familia en las tres franjas
bajó de (implícitamente) casi siempre a 19/45 partidos.

**Lo que NO se cerró, y quedó anotado como pregunta abierta, no como
bug:** `combinada()` sigue en 3/45. Con Bet365 real en las tres líneas
de gol, Goles encuentra ventaja *genuina* en la franja "Lo más
probable" más seguido que Resultado — y ahí la diversidad no debe
intervenir (sería preferir el pick sin ventaja al que sí la tiene). No
está medido si el 17/45 de antes era un número sano que se rompió, o
si ya era mayormente "cercanía al centro" disfrazada con menos
competencia porque casi nada tenía precio real todavía. Antes de tocar
esto de nuevo, hay que medirlo — no adivinarlo.

3 tests nuevos en `test_alineacion.js` (86 en total). Verificado en el
navegador: 0 errores sobre los 45 partidos reales de hoy.


### Addendum · ¿Están mal los pronósticos? Barrido OOS de los parámetros de λ (2026-08-29)

Lucas vio que los pronósticos numéricos "estuvieron extremadamente
errados" (caso señalado: Unión venció 4-1 a Sarmiento cuando la app
marcaba escalera de pocos goles / `un1.5`). Pregunta de fondo: ¿el motor
de goles (λ / Dixon-Coles) está mal calibrado, y se puede arreglar?

**Diagnóstico previo (`backtest.py`, temporada en curso de ESPN):**
parecía que el modelo subestimaba los goles — en la franja donde decía
30% de over 2.5, pasaban 37-65%. Y el 1X2 capturaba ~39% de lo que
mejora el mercado sobre la tasa base.

**Qué se hizo — un barrido out-of-sample, walk-forward temporal estricto**:
se escribió `barrido_lambda.py` (nuevo, de SOLO LECTURA, no toca el
motor). Usa el historial largo de `historico.py` (6310 partidos arg,
5544 bra) con la vara más dura — cuota de cierre real de Pinnacle —,
partición **train (fecha < 2022) para elegir / test (≥ 2022) para
confirmar**, y mide over 1.5/2.5/3.5, ambos marcan, la distribución
completa de goles (log-loss de la celda del marcador) y el 1X2 como
control de efectos colaterales. Se barreron, uno por vez y centrados en
producción, los parámetros que tocan λ: `escala_goles` (factor sobre μ,
apunta directo al sesgo sospechado), `VIDA_MEDIA_DIAS`, `rho` y `prior`.

**Resultado — NO hay nada que implementar.** Producción (escala 1.0,
vida 300, rho/prior por liga) está en el óptimo o indistinguible de él
dentro del ruido, en arg y en bra. La escala 0.95 "gana" en test por
0.0004 de Brier (ruido puro: error estándar ~0.003 con n=2559) y **pierde
en train** — la dirección del "ganador" se invierte entre train y test,
que es exactamente la señal de que no es un hallazgo. Todas las demás
variaciones de vida/rho/prior están dentro del ruido y rebalancean solo
marginalmente entre 1X2 y distribución (nunca mejoran ambos).

**La lectura correcta del presunto "sesgo":** sobre 2559 partidos de arg
en test, la frecuencia real de over 2.5 es 0.357 y el modelo predice
0.375 — desvío de ~1.8 pp, bien calibrado. El "subestimar goles" que se
veía en `backtest` era un artefacto de la muestra chica de la temporada
en curso y de franjas específicas (20-40%), no un defecto estructural de
λ que un parámetro arregle. El 4-1 de Unión fue varianza de un solo
partido (el 4-1 vive en la cola de una Poisson con λ≈1.47/0.95), no
evidencia de mala calibración cuando 2559 partidos dicen lo contrario.

**Regla respetada:** AGENTS.md exige que una constante entre solo si una
medición walk-forward fuera de muestra mejora la métrica con su
incertidumbre. Acá la medición NO lo sostiene — tocar cualquier constante
ahora sería tunear, y empeoraría 1X2 o la distribución para ganar un
Brier invisible.

**Qué NO fue, y dónde queda:** no se tocó `actualizar.py` ni `index.html`
(git lo confirma). Quedan `barrido_lambda.py` (script de medición
reutilizable: `python barrido_lambda.py arg [--fast]`) y
`data/barrido_lambda.json` (salida). Si vuelve a aparecer un pedido de
"arreglar los pronósticos", correr este script con la liga en cuestión
antes de pensar en tocar λ: el resultado probable es el mismo, y si
algún día cambia (esperanza: una fuente nueva o un formato de torneo
nuevo), se verá acá antes que en la queja de un partido.

---

## 13. Redirección de producto (2026-08-30) — qué cambia y en qué orden

Dos documentos nuevos en `data/` motivaron esto: `presentacion-claude.md`
(la visión — VALOR como asesor personal, no calculadora de EV) y
`PROBLEMAS.md` (el estado medido de hoy, con números y una fecha real de
15 partidos como ilustración). Se le pidió a Claude que evaluara la
visión contra el estado real, sin complacencia. Esto resume el
veredicto y qué se decidió hacer con él. **Es redirección de producto,
no un cambio de código todavía** — cualquier implementación de lo que
sigue entra por TDD y se verifica en navegador, como cualquier cambio de
lógica de este repo.

### El diagnóstico, sin adornos — y corregido el mismo día contra el código real

**Ojo, esto se escribió mirando `PROBLEMAS.md`, no `index.html`.** Al
implementar el punto 1 (ver abajo) se leyó el código de cerca y dos de
los tres puntos de este diagnóstico resultaron menos ciertos de lo que
parecían. Se deja la corrección acá en vez de borrar el error, siguiendo
la misma disciplina que el resto del documento (comentarios vencidos
que sobreviven a su propio dato ya causaron bugs reales, ver §6vicies
semel).

1. **La redundancia mecánica era real, y ya se arregló (2026-08-30).**
   Con precio real de Bet365, un3.5/un2.5/un1.5 podían dar ventaja real
   los tres a la vez — 24 de 34 partidos reales recomendaban "pocos
   goles" tres veces con otro número. Corregido con `temaDe()` en
   `escalera()`, TDD completo, bajó a 3/34 (escasez real verificada a
   mano, no bug). **Lo que NO era cierto:** que la escalera "ordene por
   probabilidad en vez de por valor" sea en sí un bug — las tres franjas
   por banda de probabilidad son la Regla 1 (sección 5), un diseño
   deliberado y medido ("misma lectura, tres formas de jugarla, no tres
   opiniones"). El problema real era la redundancia de tema, no el
   ordenamiento por franja.
2. **"Permitir 0 recomendaciones" ya estaba cumplido.** `marcaDeValor()`
   ya devuelve `null` la mayoría de las veces (es la regla, no la
   excepción), y cada franja de la escalera ya puede quedar en
   `"Sin ninguna opción clara en esta franja para este partido"` cuando
   de verdad no hay candidato — no fuerza nada. Lo que parecía "siempre
   3 tarjetas" es la escalera (Regla 1, deliberadamente 3 formas de la
   misma lectura) confundida con la marca de valor (que sí es rara, por
   diseño). No hace falta código nuevo acá.
3. **"Exponer la contradicción motor↔skill" ya estaba construido desde
   el 2026-08-19.** Ver la corrección en la Regla 3 (sección 5, arriba):
   `divergen()` y la más nueva `senalDividida()` ya lo hacen, con texto
   en pantalla y tests. La nota que decía "pendiente de implementar" en
   este documento estaba mal — se escribió sin leer el código.
4. **El motor sigue sin ventaja demostrada**, y esto sí sigue abierto.
   ROI walk-forward −3.27%±6.19 contra cierre de Pinnacle: el intervalo
   incluye cero. Ninguna capa de presentación cambia esto. No es motivo
   para parar — es motivo para no vender "valor" en la interfaz donde no
   hay nada medido que lo sostenga, y para seguir corriendo
   `medir_clv.py` hasta tener volumen.

### Orden de trabajo, actualizado

1. ~~Escalera: redundancia de tema~~ **HECHO (2026-08-30).** Ver punto 1
   de arriba.
2. ~~Permitir 0 recomendaciones~~ **Ya estaba cumplido**, verificado
   leyendo el código — no requirió cambios.
3. ~~Exponer contradicción motor↔skill~~ **Ya estaba hecho desde el
   2026-08-19** — no requirió cambios.
4. **Lo que queda realmente abierto:** el lenguaje de la UI en Método y
   Herramientas (nada de mostaza/"valor" donde no hay ventaja medida —
   falta verificar puntualmente, no se revisó hoy) y la capa de
   narrativa "por qué" de `presentacion-claude.md` §2/§6 (ver la sección
   de abajo). El diagnóstico de fondo del punto 4 sigue siendo el que
   manda: sin ventaja demostrada, ninguna de estas capas es la que
   decide si el producto sirve.

**Deliberadamente fuera de este orden:** tocar λ, `rho`,
`VIDA_MEDIA_DIAS`, `PRIOR_FUERZA` o cualquier constante del modelo. Ya
está barrido (sección "Addendum" arriba, 2026-08-29) y ninguna variante
mejora robustamente fuera de muestra. Tocarlo sin medición nueva es
justo la regla que este repo prohíbe.

### Qué falta para que la app se sienta como el asesor descrito

No está en el orden de arriba porque es capa de contenido, no de lógica
de selección — pero está en `presentacion-claude.md` §2 y §6: cada pick
necesita 1-2 frases de "por qué" que tejan dato + contexto (`inclinacion`
de la skill), no solo un número con una etiqueta. Depende de que la
escalera ya elija bien (punto 1 arriba) antes de tener sentido escribirle
texto a lo que elige.

---

## 14. El modelo exageraba su rango de goles (2026-08-30)

**El hallazgo más importante de la sesión, y salió de una objeción de
Lucas sobre un partido puntual.** Vale la pena contar cómo, porque el
método es el hallazgo tanto como el número.

### Cómo apareció

Lucas vio Unión–Sarmiento: ~2.70 de goles esperados, escalera de "pocos
goles" y "no marcan ambos", terminó 4-1. Su objeción: los dos equipos
convierten y reciben, no era un partido para esperar poco gol.

La respuesta fácil —y la que se dio primero— era "un partido es
varianza, con λ=2.70 un 4-1 vive en la cola". Es cierto y no alcanza:
la pregunta que quedaba sin contestar era si el modelo acierta *el
rango*, no si acertó *ese* partido. Lucas insistió, y tenía razón.

### Qué se midió

`medir_compresion.py`, sobre 6270 partidos de arg, walk-forward,
partiendo por **λ predicho** — la vista que ninguna medición anterior
usaba:

```
 franja λ      n   predicho   real   desvío
  0.0-2.0   1583      1.80    2.07    +0.27
  2.4-2.6    931      2.49    2.31    -0.18
  3.0-3.3    129      3.11    2.44    -0.67

 pendiente de real contra predicho: 0.368 ± 0.108
```

**El modelo predecía un rango de 1.80 a 3.11 goles donde la realidad va
de 2.07 a 2.44.** Estiraba su rango ~2.7 veces de más: donde decía
mucho gol pasaban menos, y donde decía poco gol pasaban más.

**No es atenuación estadística**, y esto se verificó antes de creerle
al número: un modelo PERFECTO simulado con la misma muestra y la misma
distribución de λ da pendiente 0.944 ± 0.091; uno que exagera 2.7x da
0.335 ± 0.091. El real (0.368) está en el segundo grupo.

### Por qué nadie lo había visto en tres semanas de mediciones

**En agregado se cancela.** Los partidos inflados y los desinflados se
compensan, así que todas las mediciones promedio daban "sin problema":

- `medir_historico.py` parte por banda de probabilidad del 1X2.
- `barrido_lambda.py` mide over 2.5 en total, y daba **bien calibrado**
  (0.357 real contra 0.375 predicho sobre 2559 partidos).
- `backtest.py` mira franjas de probabilidad, no de λ.

Ninguna partía por λ predicho. **La lección de método: un promedio que
da bien puede estar tapando dos errores que se cancelan. Si el producto
falla en casos concretos mientras el agregado calibra, buscá la
partición donde el error NO se cancele.**

### La corrección, y qué compra

```
λ_corregido = centro_liga + k · (λ_modelo − centro_liga)
```

Barrida con train/test temporal (`barrido_escala_lambda.py`), y
verificada con test **pareado** sobre el Brier de goles en test:

| liga | k | centro | Brier de goles en test | 1X2 |
|---|---|---|---|---|
| arg | 0.50 | 2.266 | +0.00372 ± 0.00351 (**2.1 e.e.**, pareado) | sin daño |
| bra | 0.50 | 2.371 | 0.49676 contra 0.50187 | sin daño |
| eng | 0.60 | 2.785 | +0.00245 ± 0.00342 (1.4 e.e., pareado) | sin daño |
| fra | 0.60 | 2.617 | 0.49176 contra 0.49343 | sin daño |

**Las cuatro ligas, independientes, todas con el óptimo en k < 1 y
dentro de la grilla** — exagerar más (k=1.15) empeora en las cuatro. La
significancia individual solo se verificó con test pareado en arg
(2.1 e.e.) y eng (1.4); lo que sostiene a las otras dos es la
consistencia de la dirección y que el óptimo no cae en un borde.

**Lo que NO compra, y hay que decirlo: no mejora el ROI.** Entra porque
corrige un defecto medido en un número que la app **muestra en
pantalla** ("2.7 goles esperados entre los dos"), no porque haga ganar
plata. Mejorar el Brier y ganar plata no son la misma cosa — ver
`medir_encogimiento.py`, que ya costó esa lección.

### La trampa del centro, que casi se implementa mal

El centro parecía obvio: `mu_local + mu_visita`, el λ de dos equipos
promedio. **Es incorrecto.** Medido sobre arg da 2.025 mientras la
media real de λ es 2.266, porque λ es multiplicativo y `E[a·d]` no
vale 1. Centrar ahí metía un sesgo sistemático de **−0.11 goles en cada
partido** — un error que no tira excepción, no aparece en los tests y
solo desplaza todo hacia abajo.

Por eso el centro es una **constante medida por liga**, y es el mismo
valor con el que se barrió cada `k`: medir con una vara y aplicar con
otra es el error de §6vicies, y acá estuvo a un paso de repetirse.

### Qué NO se tocó

`index.html` no cambia: la corrección vive en `actualizar.py`, así que
el frontend recibe λ ya corregido. `doble_via.py` sigue dando 6.7e-16
de diferencia máxima — el motor de las dos vías sigue siendo el mismo.

Una competición sin `escala` y `centro` medidos **no se corrige**. Las
copas no tienen cuotas históricas en football-data, así que no se
pudieron medir, y extrapolar el k de una liga a una copa sería
inventar.

### Addendum · El segundo eje: la diferencia entre equipos (2026-08-30)

Salió de una pregunta de Lucas —"¿cómo le fue a la app el 30/8?"— y
terminó explicando el problema de Argentina.

**Cómo le fue esa fecha** (16 partidos, sin análisis: motor puro):

```
lean (1X2):     11/16 = 69%     siempre local: 10/16 = 63%
escalera:       24/48 = 50%
  Lo más probable  9/16 = 56%   ← la banda promete 68-93%
  Intermedia       8/16 = 50%
  Arriesgada       7/16 = 44%   ← la banda promete 12-45%
```

El pronóstico anduvo bien (69% contra 63% de la vara) y confirma que el
29/8 fue una fecha anómala, no un defecto. Pero la franja "Lo más
probable" acertó 56% cuando su banda promete al menos 68%, y la
"Arriesgada" acertó de más. Las dos hacia el centro.

**`medir_calibracion.py` sobre los 59 partidos ya publicados lo
confirma:**

```
Probabilidades altas (60%+):  -6.6% de desvío
Probabilidades bajas (<40%):  +9.8% de desvío
1X2 local:  decimos 43.5%, pasa 25.4%   (-18.1%)
```

**Es el mismo defecto que `medir_compresion.py`, en el otro eje.** La
corrección de escala arregla *cuántos goles hay*; esto es *cuánta
diferencia hay entre los dos equipos*, que es lo que mueve el 1X2. Son
independientes: `encoger_diferencia()` conserva el total.

**Y solo pasa en Argentina.** Barrido train/test con test pareado sobre
el Brier del 1X2:

| liga | k de train | test |
|---|---|---|
| **arg** | **0.95** | **+0.00046 ± 0.00039 (+2.4 e.e.) MEJORA** |
| bra | 1.00 | 1.00 es el óptimo en las dos mitades |
| eng | 1.00 | 1.00 es el óptimo en las dos mitades |
| fra | 0.95 | empeora en test |

**Eso cierra el diagnóstico de Argentina**, que el documento arrastraba
como "el candidato serio, nunca se probó": arg juega 27 partidos por
equipo a una sola vuelta con 28-30 equipos; Brasil juega 38 a doble
vuelta. Con menos partidos por equipo, **el ruido de estimación se lee
como diferencia real entre equipos**, y el modelo los separa más de lo
que la realidad los separa.

Es la misma raíz de todo lo que ya estaba medido sin explicación: que
arg capture 7.7% de la ventaja del mercado contra 45.4% de bra y 80.9%
de eng/fra, que el modelo "opine más que el mercado" ahí (7.70% contra
7.02%), y el "1X2 de favoritos sobreconfiados".

Aplicado solo a `arg.1` (`"diferencia": 0.95`). Las demás quedan en
1.00 porque ahí el modelo NO exagera — medido, no supuesto.

---

## 15. Dónde retomar (2026-08-31)

Lo que sigue es el estado al cerrar la sesión del 30-31/08 y la
hipótesis con la que conviene arrancar la próxima. Leer esta sección
entera antes de tocar nada: ahorra repetir mediciones que ya se
hicieron y dieron que no.

### La hipótesis para arrancar, y salió de Lucas

Textual: *"imaginate si en el partido del Chelsea ponía: gana Chelsea,
ambos marcan y hay más de 2.5 goles como variantes. Pero que esto no
salga porque sí, sino por estudio, medición."*

Chelsea–Brighton terminó 4-3: las tres habrían acertado.

**Lo que hace distinta a esa idea:** esas tres cosas NO son
independientes. Si Chelsea gana Y ambos marcan, ya hay 3 goles mínimo.
Y el motor tiene esa correlación exacta en la matriz de marcadores
(0-9 × 0-9) — `combinada()` ya la usa para dos patas. Pero `escalera()`
elige mercado por mercado, como si fueran independientes, y tira justo
la información que hace coherente al conjunto.

**Las dos preguntas medibles, en orden:**

1. **¿El modelo acierta mejor los goles CONDICIONADO al resultado que
   en general?** Está medido que en general no sabe nada de goles
   (`medir_ejes.py`: aporte entre −0.9% y +0.4% sobre la tasa base).
   Pero "cuántos goles habrá" y "dado que gana el favorito, cuántos
   goles suele haber" son preguntas distintas. La segunda nunca se
   midió.

2. **¿Un escenario coherente acierta más que tres mercados sueltos?**
   Construir el escenario desde la matriz (el marcador más probable y
   lo que se desprende de él) y compararlo contra la escalera actual.

Si la (1) da que sí, la (2) tiene fundamento y el producto que Lucas
pide se puede construir medido. Si da que no, la escalera se queda como
está —solo Resultado— y eso también cierra el tema.

Herramientas que ya existen para medirlo: `medir_ejes.py` (aporte por
mercado contra la tasa base), `medir_roi.py` (ROI, drawdown, Sharpe),
`eval_fecha.js` (cómo le fue al motor en una fecha real).

### Lo que se hizo el 30-31/08, para no repetirlo

**Motor — dos correcciones, las dos medidas y aplicadas:**

- **Escala de λ** (§14): el modelo estiraba su rango de goles 2.7 veces
  más que la realidad. Corregido en las cuatro ligas.
- **Diferencia entre equipos** (§14, addendum): exageraba la brecha
  entre local y visitante. Corregido **solo en arg**, que es la única
  liga donde el defecto aparece — y eso cierra el diagnóstico del
  "candidato serio" que este documento arrastraba: 27 partidos por
  equipo a una vuelta contra 38 de Brasil.

**Producto:**

- La app **no marca valor en arg ni bra**: medido que ahí la regla
  resta (−9.17% y −9.13%, significativo), y `barrido_valor.py` probó 39
  ventanas distintas sin encontrar ninguna positiva.
- La escalera **solo recomienda mercados de Resultado**, con piso de
  cuota 1.30. Es el único eje donde el modelo tiene información medida.
- La skill de análisis: `desarrollo` pasa a obligatorio (estaba en 1 de
  20) y el principio O se actualizó con el sesgo re-medido (69% de
  inclinaciones al local contra 45% que corresponde).

**Caminos cerrados con número — no volver a proponerlos sin dato nuevo:**

| camino | resultado |
|---|---|
| Mover los umbrales de valor | 39 ventanas, ninguna positiva OOS |
| Mercado de goles (over/under) | eng −2.85%, fra −8.27% |
| Consenso del mercado (arXiv 1710.02824) | Bet365 no se desvía; con alpha del paper, cero apuestas |
| Remates para estimar fuerzas | mejora +0.8 e.e., no alcanza |
| Bajas de goleadores → menos goles | r = −0.06 ± 0.14, sin señal |
| xG de fuente gratis | cinco fuentes probadas, todas cerradas |

**Lo que se desbloqueó y conviene usar:**

- **El CLV se puede medir hacia atrás.** Este documento decía que no
  (§6sexdecies), y es cierto para ESPN pero falso para football-data,
  que publica apertura y cierre. `medir_apertura.py`. Con 362 apuestas
  el CLV ya es concluyente mientras el ROI sigue en ±14 — es el
  instrumento correcto para evaluar cualquier cambio del modelo sin
  esperar mil apuestas.
- **Japón y México están medidas y son las mejores candidatas.** jpn da
  +2.78% de ROI con la menor caída de las seis ligas (2.0% contra 9.7%
  de arg), y es la única donde el modelo también aporta en goles. No es
  significativo (±7.67), pero es el mejor perfil que hay.

### El estado honesto, en una línea

Contra Bet365 el CLV es cero: el modelo **empata con el mercado antes
de comisión**. No elige mal — la pérdida es el margen que se paga sin
ventaja que lo compense. Para ganar hace falta CLV positivo, y eso solo
sale de información que el mercado todavía no tiene.

## 16. El escenario coherente: la pregunta 1 da que NO (2026-08-31)

§15 dejó dos preguntas en orden, y la segunda solo tenía sentido si la
primera daba que sí. Está medida la primera: **no da**. Herramienta
nueva: `medir_condicional.py` (con `test_medir_condicional.py`, 22
pruebas).

### Qué se midió, exactamente

Para cada condición de resultado R se toman **solo los partidos donde R
efectivamente pasó**, y ahí se comparan tres pronósticos del mercado de
goles G:

1. la **tasa base condicionada** — la frecuencia de G entre esos mismos
   partidos. Es la vara;
2. el modelo **sin condicionar**, P(G), que es lo que la app publica;
3. el modelo **condicionado**, P(G|R) = P(G∩R)/P(R), leído de la misma
   matriz de marcadores que ya usa `combinada()`.

La columna que contesta la hipótesis es la (3) contra la (1). Bootstrap
pareado de 2000 remuestreos para el error estándar, porque al cortar por
resultado la muestra baja a un tercio.

### El resultado, seis ligas, 28.881 partidos walk-forward

Aporte sobre la tasa base, en la condición que le importa al producto
(*dado que gana el favorito del modelo*), contra el aporte que el mismo
modelo ya tenía **sin** condicionar:

| liga | n | +1.5 sin/cond | +2.5 sin/cond | +3.5 sin/cond | ambos sin/cond |
|---|---|---|---|---|---|
| arg | 2781 | −0.6 / **−1.2** | −0.9 / **−1.9** | −0.9 / **−1.9** | −0.4 / **−1.6** |
| bra | 2748 | −0.1 / **+0.2** | −0.4 / **−1.3** | −1.1 / **−2.0** | −1.1 / **−1.8** |
| eng | 2213 | +0.1 / **+0.1** | +0.4 / **−0.2** | +0.3 / **−0.0** | −0.2 / **+0.0** |
| fra | 1950 | +0.1 / **+1.9** | +1.3 / **+1.6** | +2.4 / **+3.4** | −0.7 / **+0.2** |
| jpn | 2109 | +1.3 / **+2.0** | +0.7 / **+1.6** | +0.6 / **+1.6** | +0.6 / **+1.0** |
| mex | 2191 | −0.5 / **+0.3** | +0.0 / **−0.6** | −0.0 / **+1.0** | −1.8 / **−1.3** |

Los errores estándar del condicionado están entre 0.6 y 1.1. O sea: casi
ningún número de esa tabla llega a dos errores estándar de cero, y los
que llegan son de fra y jpn, **las dos ligas donde el modelo ya sabía
algo de goles sin condicionar**. Condicionar no destapa información
donde no la había: la mueve entre medio punto y un punto donde ya la
había. En arg y bra el condicionado es *peor* que la tasa base.

### La trampa que casi lo hace parecer un hallazgo

La primera versión del script imprimía el **delta** (condicionado menos
sin condicionar) sin el error estándar del condicionado. Y el delta es
espectacular: +5.3% en arg dado que gana el favorito, **+44.8%** en la
condición "empate" sobre más de 2.5 goles.

Ese número es real y no significa nada. Quiere decir que si uno ya sabe
que el partido terminó empatado, el modelo sin condicionar —que publica
P(más de 2.5) ≈ 49%— queda ridículo contra el 14.9% que de verdad pasa.
Condicionar corrige el **nivel** de goles del subconjunto, que es
exactamente lo que la tasa base condicionada ya sabe. Por eso el
condicionado aterriza en +0.3%: acomoda el nivel y **no agrega nada
partido por partido**.

Es el mismo error que §6vicies bis: calibrar no es saber. Un pronóstico
que le da a todos los partidos del subconjunto el promedio de ese
subconjunto calibra perfecto y no sirve para apostar.

Y hay algo peor: condicionar al resultado real **no se puede hacer antes
del partido**. La medición mira una información que el apostador no
tiene. Aun así, con esa ayuda regalada, el aporte da cero. Sin la ayuda
solo puede dar menos.

### Qué queda decidido

- **La pregunta 2 de §15 no se abre.** No hay escenario coherente que
  construir: el eje de goles sigue sin información propia, condicionado
  o no. La escalera se queda como está — solo Resultado.
- **Camino cerrado con número.** Sumar a la tabla de §15: *goles
  condicionados al resultado — aporte entre −2.0% y +3.4%, con e.e. de
  0.6 a 1.1, y solo positivo donde ya lo era sin condicionar*.
- **Lo que sí sigue vivo del pedido de Lucas.** La idea de mostrar un
  escenario en vez de tres mercados sueltos es buena como *lectura*: si
  alguna vez se publica, la probabilidad conjunta tiene que salir de la
  matriz (`combinada()`), nunca del producto de tres mercados sueltos —
  eso está bien fundado y es lo que hace coherente al conjunto. Lo que
  esta medición prohíbe es **recomendarlo como valor**: la coherencia
  interna del escenario no es información sobre goles.
- **fra y jpn son las dos ligas con algo en el eje de goles**, y eso
  refuerza lo que §15 ya decía de jpn por otro lado (ROI +2.78%, la
  menor caída de las seis). Si algún día se prueba un mercado de goles,
  se prueba ahí y en ningún otro lado.

    python medir_condicional.py arg
    python test_medir_condicional.py

---

## 17. Lectura por ejes: dos varas en vez de una (2026-08-31)

Redirección de arquitectura, y sale de una objeción de Lucas que es la
más importante que recibió el proyecto. Textual: *"no quiero que VALOR
se limite porque una determinada medición todavía no sea buena. Quiero
que pensemos al revés: esto hoy no funciona lo suficientemente bien,
¿qué necesitamos hacer para que funcione?"*

### El error, y es de método

Durante tres meses se midió TODO con una sola pregunta: **¿le gana al
precio de cierre?** Esa es la vara de una recomendación de apuesta. No
es la vara de un análisis.

Con esa vara se cerraron córners (§6vicies quater), tarjetas, faltas y
remates por jugador (§6quindecies) — mercados donde el número era
honesto y útil de leer, pero no le ganaba al precio. Se los trató como
fracasos cuando eran material de producto.

El resultado es un producto que sabe mucho de un solo eje y no dice
nada de los otros cinco, y un usuario con la sensación —correcta— de
que buscando por su cuenta llegaría a lo mismo. En el 1X2 eso está
medido: capturamos el 80.9% de lo que sabe el mercado en eng/fra, o
sea que publicamos el consenso con otro método.

### La regla nueva

Dos varas, y cada cosa se juzga con la suya:

| vara | pregunta | instrumento | consecuencia |
|---|---|---|---|
| 1 | ¿el número es verdadero? | calibración | **se muestra** |
| 2 | ¿le gana al precio? | CLV, ROI | **se marca** |

**Todo eje se muestra. Solo el que pasa la vara 2 se marca.** Con eso
el análisis completo del partido se puede construir entero sin mentir,
y la mostaza recupera el significado que pierde cuando está en todos
lados (regla de los dos metales, `DESIGN.md`).

### El contrato

Los seis ejes emiten el mismo registro de diez claves. La app no sabe
qué es un córner: sabe renderizar un eje. Agregar el séptimo no toca
una línea de interfaz.

    eje · titulo · estimacion · ancla · medido_por
    confianza · aporte · mercado · lectura · apuesta

`confianza ∈ {sin_medir, calibrada, con_plata}`, y **sale de la tabla
`MEDICIONES`, nunca del que llama**. Las dos reglas duras:

1. Un eje sin `medido_por` no puede declarar más que `sin_medir`.
2. Solo `confianza === "con_plata"` puede llevar `apuesta`.

Eso convierte la honestidad en estructura y no en disciplina: si nadie
escribió el script que mide un eje, la app lo declara sin medir sola.
Para saltear la regla hay que romper un test a propósito.

`aporte` es por liga y **no se hereda**: una liga sin medición da
`null`, no el número de la vecina. Es la misma regla que §6vicies
semel aprendió a los golpes con `parametros_metricas()`.

### Los seis ejes y su estado

| eje | pregunta | mide | estado |
|---|---|---|---|
| Resultado | quién gana | `medir_ejes`, `medir_roi`, `medir_apertura` | calibrada; aporte +13.2% eng, +2.6% arg; CLV cero |
| Volumen | cuántos goles | `medir_ejes`, `medir_condicional` | calibrada, sin aporte; techo 7.2% eng, 5.5% arg |
| Dominio | córners, remates, al arco | `medir_corners`, `medir_lineas` | **a re-medir** |
| Fricción | faltas, tarjetas, árbitro | `medir_lineas`, `medir_arbitros` | parcial; faltas con sesgo de 9 puntos |
| Jugadores | remates, al arco, goles, asistencias | `medir_jugadores` | calibración conocida; **plata sin medir** |
| Contexto | bajas, DT, motivación | `medir_analisis` | corregido el 30/08, sin re-medir |

**El "a re-medir" de Dominio es el hallazgo operativo de esta sesión.**
§6vicies quater cerró los córners el 2026-08-25 con este motivo escrito:
*"le apostamos el promedio de la liga a una casa que sí distingue equipo
por equipo"* — `k` de córners 17 en arg, 200 en bra. Y dejó anotado qué
haría falta: más muestra por equipo para que `k` baje.

Esa muestra llegó. `data/historia_equipos.json` tiene hoy 300-418
partidos por equipo en eng y fra, y los `k` que salen de ahí son 11.6
en córners, 6.8 en remates, 8.4 en al arco. **Nadie volvió a medir.**
La puerta que cerramos con un "no sirve" está destrabada hace una
semana. Es el ejemplo exacto de lo que pide la objeción de Lucas: no
cerrar, preguntar qué falta — y después volver.

### El techo de cada eje, medido el 2026-08-31

Var(resultado) = ruido Poisson irreducible + Var(lo que el modelo
mueve). Para dos Poisson independientes el piso de ruido es el MISMO
en los dos ejes, así que lo único que los distingue es cuánto varía la
parte nuestra:

| liga | eje | Var real | Var(λ) | techo |
|---|---|---|---|---|
| eng | diferencia (1X2) | 3.577 | 0.782 | **21.9%** |
| eng | total (goles) | 2.748 | 0.199 | **7.2%** |
| arg | diferencia (1X2) | 2.260 | 0.212 | **9.4%** |
| arg | total (goles) | 2.337 | 0.128 | **5.5%** |

Explica de una sola vez tres cosas que estaban sueltas: por qué el eje
de goles no aporta (techo de 5-7%, y encima no lo agarramos), por qué
el 1X2 sí (techo 21.9% en eng, capturamos 13.2), y por qué Argentina
anda peor (techo de 9.4% contra 21.9% — no es que el modelo falle más,
es que hay menos para saber).

El script quedó en el scratchpad, no en el repo. Si se va a citar de
nuevo, promoverlo a `medir_techo.py` con su suite.

### Cómo se juntan los ejes

1. **La probabilidad conjunta sale de la matriz, nunca del producto de
   los ejes.** Es lo único que sobrevive del "escenario coherente"
   (§16): la correlación existe y `combinada()` ya la usa; multiplicar
   dos porcentajes de pantalla da un número que no existe.
2. **La lectura global no afirma más que su eje más débil.** Si no, la
   prosa asciende sola una lectura a recomendación, que es justo lo que
   la vara 2 existe para impedir.
3. **Cuando dos ejes se contradicen, se dice.** No se promedia.
   `senalDividida()` ya lo hace entre modelo y skill; se generaliza.

### Hecho en esta sesión (paso 1 de 5)

- **`index.html`**: región marcada `/* ==== INICIO EJES ==== */`, con
  `CONFIANZAS`, `CONTRATO`, `MEDICIONES`, `sellar()` y
  `construirEjes()`. `construirEjes` es **puro**: recibe los números ya
  calculados en vez de volver a correr el motor, así el motor sigue
  teniendo una sola implementación (regla de `CLAUDE.md`).
- **`test_ejes.js`**: 15 pruebas que leen esa región del `index.html`
  publicado, igual que `test_registro.js`. Atan las dos reglas duras.
- **`actualizar.py`**: cada partido ahora trae `"liga": slug` además de
  `comp`. Hasta hoy la app identificaba la liga por expresión regular
  sobre el nombre que se muestra en pantalla (`LIGAS_SIN_VALOR`): si
  ESPN cambia "Brasileirão" por "Brasileirao", la regla medida deja de
  aplicarse **en silencio**. Campo nuevo, contrato intacto.
- **En pantalla no cambia nada**, y es a propósito: primero se prueba
  el contrato contra lo que ya funciona.

Verificado: `test_ejes.js` 15/15, `test_registro.js` 22/22,
`test_alineacion.js` 110/110, `test_probabilidad.js` 43/43,
`test_actualizar.py` 33/33, más `test_pronosticos`, `test_calibracion`
y `test_forma`. La app carga sin errores de consola y
`construirEjes()` corre contra `data/partidos.json` real.

### Lo que sigue

2. **Dominio con los anclas nuevos y la re-medición.** eng y fra, que
   son las que tienen historia por equipo.
3. **Jugadores: medir plata**, que nunca se hizo. Los datos de Bet365
   ya entran y `data/props_jugadores.json` ya acumula.
4. **Fricción**, con el sesgo de faltas declarado en pantalla.
5. **Contexto: una skill por eje.** Recién acá — una skill que estudie
   remates de jugadores solo sirve cuando el eje que la recibe ya
   existe y sabe declarar cuánto se le cree.

### Lo que esto NO hace

No crea ventaja: ordena y declara la que hay, que hoy contra el precio
es cero. No convierte una lectura en recomendación — al revés, hace
imposible confundirlas. No reemplaza ninguna medición: le da a cada una
un lugar fijo donde su resultado se ve. Y no arregla el eje de Volumen:
ese techo es del fútbol, no del modelo.

### Addendum · El eje Dominio, medido — y una corrección (2026-08-31)

**Primero la corrección, porque la escribí mal más arriba en esta misma
sección.** Este documento decía que el ancla por equipo estaba
"a re-medir" y que "nadie volvió a medir". Es falso: el docstring de
`historia_equipos.py` trae la medición, del 2026-08-25, walk-forward
sobre eng y fra. Lo que faltaba era otra cosa, y son dos cosas:

1. esa medición cubría **solo córners**. Las otras cuatro métricas
   —remates, al arco, faltas, tarjetas— se guardan y se muestran igual,
   sin un número que las respalde;
2. la comparación era contra *"solo la temporada en curso, k=200"*, o
   sea contra una vara con un `k` prestado.

`medir_dominio.py` (con `test_medir_dominio.py`, 27 pruebas) mide las
cinco, y le deja a cada pronóstico **elegir su propio `k` en train**.

#### Lo medido, test temporal, error cuadrático

| | eng: mejora / gana ± e.e. | fra: mejora / gana ± e.e. |
|---|---|---|
| remates | +9.9% / +0.117 ± 0.250 | +7.0% / +0.243 ± 0.175 |
| al arco | +7.3% / +0.036 ± 0.055 | **+9.1% / +0.122 ± 0.042** |
| córners | +4.8% / +0.097 ± 0.063 | **+2.9% / +0.142 ± 0.036** |
| faltas | +1.8% / **−0.199 ± 0.072** | +4.1% / **−0.105 ± 0.082** |
| tarjetas | +1.0% / +0.000 ± 0.005 | +0.6% / +0.000 ± 0.005 |

*mejora* = cuánto le saca el ancla larga a la media de la liga.
*gana* = cuánto le saca al caché corto, que es la pregunta real.

#### Tres cosas que salen de ahí

**El ancla vale bastante menos de lo que decía el número viejo.** En
córners de eng, contra una vara con `k` propio, la ganancia es
+0.097 ± 0.063 — **1.6 errores estándar**, no concluyente. El 4.5 e.e.
del 2026-08-25 se midió contra `k=200`, que es el `k` de Brasil, no el
de Inglaterra. No es que aquella medición esté mal: es que su vara era
peor de lo necesario, y por eso la mejora parecía más grande. En fra sí
aguanta (3.9 e.e. en córners, 2.9 en al arco).

**Donde más se sabe no es donde estábamos mirando.** Contra la media de
la liga, remates rinde +9.9% y al arco +7.3%, contra +4.8% de córners.
Los córners eran el mercado que se estaba mirando porque es el que la
casa cotiza más visible, no porque sea donde más sabemos.

**El ancla larga PUEDE EMPEORAR, y con faltas empeora.** −0.199 ± 0.072
en eng (2.8 e.e. en contra) y −0.105 en fra. Tiene sentido y no es un
bug: las faltas se mueven con la época —cambios de reglamento, criterio
arbitral— así que once temporadas de historia son un ancla vieja. La
lección general es la que importa: **más historia no es gratis; en una
métrica que deriva, el pasado lejano es peor que el caché reciente.**
Tarjetas es el caso extremo: ancla y caché dan lo mismo hasta el tercer
decimal, y ninguno de los dos le saca nada a la liga.

#### Qué queda decidido para el eje Dominio

- **Se muestra** (vara 1): remates, al arco y córners, que le sacan
  entre 3% y 10% a la media de la liga en las dos ligas.
- **Se muestra con el sesgo declarado**: faltas y tarjetas, que no
  aportan nada — y en faltas, el ancla larga directamente no se usa.
- **No se marca** ninguna (vara 2). Contra plata sigue sin medirse, y
  **no se puede medir hacia atrás**: football-data no publica cuota de
  córners. Hace falta acumular líneas hacia adelante, que es lo que ya
  hace `mercado_extra.py` con Bet365. Ese es el único camino, y tarda.
- `confianza: "calibrada"`, `medido_por: "medir_dominio.py"` cuando el
  eje se cuelgue del contrato.

### Addendum 2 · El eje Dominio en pantalla (2026-08-31)

Paso 3: el primer eje que baja del contrato a la interfaz, y a
propósito uno que **no se puede marcar**. Aparece en Pronósticos, entre
la escalera y Otros mercados.

Qué muestra: remates, al arco y córners esperados de cada equipo, en
**ese orden** — que es el orden en que sabemos (+9.9%, +7.3%, +4.8%
sobre la media de la liga), no el orden en que la casa los cotiza. Con
la barra de reparto en salvia, que es la voz secundaria de `DESIGN.md`:
no puede ser mostaza ni terracota porque no dice valor ni alerta.

Faltas y tarjetas quedan afuera del eje: medido que no aportan nada
(+1.0% y +0.6%). Siguen en Estadísticas como dato crudo.

El pie dice, con todas las letras, por qué no está marcado: *"contra el
precio de la casa nunca se midió, y no se puede medir hacia atrás
porque no hay cuotas históricas de córners"*. Es la vara 2 declarada en
pantalla en vez de escondida.

**Tres piezas nuevas, y una regla nueva:**

- `MEDICIONES.dominio` con `por_liga: true`. Es la regla nueva: una
  medición que **no se hizo en todas las ligas** degrada la confianza a
  `sin_medir` donde no se midió, en vez de heredar el número de otra.
  Verificado en el navegador contra datos reales: Premier sale
  `calibrada` con su aporte, Argentina sale `sin_medir` — la fuente no
  publica estadísticas por partido de arg ni bra.
- `ligaDe(m, L, V)`: el slug sale de `m.liga` y, si todavía no está
  —los archivos publicados no lo tienen hasta que corra el cron—, del
  caché de estadísticas, que guarda el mismo slug por equipo. Sin
  ninguno de los dos devuelve null y el eje se declara sin medir.
- `dominioDe(L, V)`: toma las tres métricas de `esperado`, el número
  ajustado por rival y localía que la app ya usa en las líneas, no el
  promedio crudo. Y si falta un equipo **no arma medio eje**: media
  lectura invita a comparar contra un hueco.

Verificado: `test_ejes.js` 21/21 (6 pruebas nuevas, todas sobre las
reglas y no sobre los números), `test_registro.js` 22/22,
`test_alineacion.js` 110/110, `test_probabilidad.js` 43/43,
`test_actualizar.py` 33/33, `test_medir_dominio.py` 27/27. Sin errores
de consola; el bloque renderiza con los números correctos y se comprobó
por hit-testing que efectivamente se pinta.

**Lo que NO pude verificar:** la captura de pantalla del navegador de
esta sesión devuelve negro apenas la página está scrolleada — falla del
entorno, no de la página. La verificación visual quedó en el texto
renderizado y en el hit-testing, no en una foto del bloque.

### Addendum 3 · El eje Jugadores contra plata: la primera señal positiva (2026-08-31)

Paso 4. **Es la primera vez que este proyecto mide dinero en las líneas
de jugador**, y la primera vez que ve un CLV que no es cero. Con una
muestra chiquísima, así que lo que sigue es una pista, no un hallazgo.

#### Lo que lo hizo posible, y no era obvio

`data/props_jugadores.json` no guarda la línea sola: guarda **la
escalera de precios entera** de Bet365 (1.5 → 1.02, 2.5 → 1.10, …
10.5 → 21.0) y **varias fotos por partido**. O sea que había precio real
para ROI y movimiento de línea para CLV, acumulándose hace días sin que
nadie lo mirara.

#### El cruce de nombres, y por qué NO se aflojó

Bet365 escribe "Lucas Beltran" y ESPN "Lucas Beltrán". El impulso obvio
es cruzar por parecido para levantar el rendimiento del 55%. Mirando
los que no cruzan se ve por qué no:

    Clever Ferreira   → ESPN tiene Pablo Ferreira, Javier Ferreira
    Wesley Fofana     → ESPN tiene Malick Fofana
    Angel Gomez       → ESPN tiene Lautaro Gómez, Thiago Gómez

**Son personas distintas.** De los 1029 que no cruzan, 407 comparten
apellido con alguien de ESPN y casi todos son otro jugador; los otros
622 directamente no están en el caché de planteles. Un cruce difuso les
fundiría la historia y no se vería como un error: se vería como datos.
Es Brentford y Brest otra vez (CLAUDE.md).

Encima del cruce exacto hay un segundo candado: **el id tiene que haber
jugado ese partido**. Un jugador que no jugó anula la apuesta en la
vida real, así que no es un descarte sino la regla del mercado.

#### Lo medido

10 partidos utilizables, 872 escalones de precio evaluados walk-forward
con el mismo camino que usa el pipeline (`prob_mayor` de
`medir_lineas.py`, parámetros por puesto con lo anterior).

| umbral de ventaja | apuestas | ROI | CLV |
|---|---|---|---|
| 2% | 25 | +51.5% ±82 | +4.29% ±1.81 |
| 4% | 19 | +74.2% ±107 | +4.39% ±2.09 |
| 6% | 15 | +110.6% ±133 | +5.72% ±2.41 |
| 10% | 13 | +143.0% ±152 | +4.79% ±2.37 |

**El ROI no dice nada** — ±107 sobre 19 apuestas es ruido con decimales,
y lo digo antes de que alguien lea el +74% como un resultado.

**El CLV sí dice algo, y pasó el control que importa.** El confundidor
obvio: si la casa achica el margen sobre la hora, TODOS los precios
bajan y cualquier selección muestra CLV positivo sin haber elegido
nada. Por eso se mide la deriva de los escalones que no apostamos:

    854 escalones sin elegir    +0.12% ±0.47   ← no hay deriva de fondo
    los 19 que apostaríamos     +4.39% ±2.09
    elegimos mejor por          +4.28% ±2.14   (2.0 e.e.)

La vara está en cero, así que el CLV no es la casa moviéndose sola.

#### CORRECCIÓN, media hora después: la señal era UN partido

Antes de escribir nada en el producto le pasé dos controles más, y no
los pasa. **Se retira el hallazgo.**

**Control 1 — dejar un partido afuera por vez.** El error estándar
asume apuestas independientes, y las de un mismo partido no lo son:
comparten equipos, hora y quién movió esa pizarra.

    sin 401841209   14 apuestas   CLV +5.96%
    sin 401841535   14 apuestas   CLV +0.17%   ← se desarma
    (los otros ocho quedan entre +4.39% y +5.06%)

Cinco apuestas de un solo evento sostenían todo el +4.28%.

**Control 2 — cuántas líneas se movieron.** 11 de las 19 tienen el
precio **clavado** entre la primera foto y la última: ahí el CLV es
cero por construcción y el instrumento no está midiendo nada. El
promedio se calculaba sobre 8 apuestas que se movieron, no sobre 19.

Y un tercer olor, que no necesita test: las apuestas se concentran en
cuotas de 21.00 con `p = 0.056`. El modelo dice tener ventaja justo
donde su estimación es menos confiable — el patrón clásico de la
ventaja falsa.

Los dos controles quedaron **dentro del script** (`dejar_uno_afuera()`
y `sin_movimiento()`), no como una revisión suelta que se pierde. La
próxima vez que alguien corra esto, los ve sin tener que acordarse.

**Lo metodológico, que sí queda:** con dos fotos por día y ninguna
pegada al inicio, el CLV en props casi no tiene resolución — la casa no
mueve esas pizarras entre nuestras fotos. Para medirlo en serio hace
falta una foto cerca del inicio, y eso es un cambio en el cron, no una
medición nueva.

#### Qué significa y qué NO

**No hay señal.** Lo que parecía la primera positiva del proyecto era
un partido, y los dos controles de arriba lo muestran. Queda el
instrumento, que es lo que de verdad valía: es la primera vez que se
puede medir plata en este mercado, y el mismo script contesta cuando
haya muestra.

Lo que aprendí, y es lo que más vale de todo esto: **dos errores
estándar no alcanzan cuando las observaciones vienen en camadas.**
Diecinueve apuestas de diez partidos no son diecinueve datos
independientes. El dejar-uno-afuera lo ve y el intervalo no.

#### Lo que sigue, y no requiere trabajo nuevo

El cron ya acumula `props_jugadores.json` cada corrida. En dos o tres
semanas hay diez veces esta muestra, y **el mismo script contesta**. Si
el +4.3% aguanta con n de tres dígitos, es lo primero que este proyecto
puede llevar al producto como valor medido. Si se cae, se cae barato.

Mientras tanto, el eje Jugadores va como **lectura**: `confianza:
"calibrada"` con la calibración por métrica que ya está medida (remates
2.09× el ruido, al arco 1.59, goles y asistencias bien), y sin marca.

Herramientas: `medir_props.py`, `test_medir_props.py` (33 pruebas).

### Addendum 4 · La foto pegada al inicio (2026-08-31)

El hallazgo metodológico del addendum 3 —que el CLV en props no tiene
resolución porque la línea no se mueve entre nuestras fotos— resultó
ser un arreglo de una tarde, no un pendiente.

**El diagnóstico, con número:** el cron corre 09:00 y 15:00 de
Argentina; los partidos arrancan entre las 08:00 y las 21:00. Para uno
de las 19:00 la última foto es de cuatro horas antes, justo antes de
que la línea se mueva de verdad — dinero informado y alineaciones
confirmadas, que salen alrededor de una hora antes del inicio.

**Por qué no alcanzaba con correr el cron más seguido:** `actualizar.py`
cuesta ~55 pedidos a odds-api por corrida (uno por liga más uno por
partido pendiente). Cada hora serían ~800 por día contra ~110 de hoy.

**`foto_props.py`** pide **solo los partidos que arrancan en las
próximas 2 horas**: entre cero y cinco pedidos, y la mayoría de las
corridas no pide nada. La foto cara se saca donde sirve.

Detalles que importan y están testeados (`test_foto_props.py`, 19
pruebas):

- **El corte de abajo, que es el que se olvida.** Un partido que YA
  empezó tiene cuota en vivo: es otro mercado, y compararlo contra la
  apertura no mide CLV — mide otra cosa y se ve igual de bien.
- **La zona horaria.** `partidos.json` guarda hora de Argentina y el
  runner de GitHub corre en UTC. Tres horas de error mandan la foto al
  momento equivocado y el archivo igual queda lleno de datos, que es la
  peor forma de fallar. Hay un test que compara desde las dos zonas.
- **No toca nada más.** No escribe `partidos.json`, no recalcula λ, no
  cambia lo que la app muestra. Solo agrega fotos a
  `props_jugadores.json`, que es un archivo que solo crece. Sin
  `ODDS_API_KEY` sale sin ruido, igual que el resto de esa fuente.
- El workflow (`.github/workflows/foto_props.yml`) corre cada hora
  entre las 07:00 y las 21:00 de Argentina, con `concurrency` para que
  dos corridas no se pisen el archivo, y `pull --rebase` antes del push
  porque el cron grande puede haber escrito mientras tanto.

**Qué se espera de esto:** que en dos o tres semanas `medir_props.py`
corra sobre apuestas cuya línea efectivamente se movió, en vez de sobre
un 58% de precios clavados. No mejora el modelo — hace que el
instrumento mida.

### Addendum 5 · El eje Jugadores en pantalla, y un estado nuevo (2026-08-31)

Es el eje que más se parece a lo que Lucas pidió — *"quién puede
marcar, quién puede rematar"* — y el que obligó a arreglar el contrato.

**El hueco que tenía el contrato.** `remates` está medido (618 casos) y
el resultado es que se desvía **2.09 veces lo que explica el azar**.
Declararlo `sin_medir` sería mentir por omisión: sí se midió.
Declararlo `calibrada` sería mentir a secas. Faltaba el estado del
medio, y ahora existe:

    sin_medir  <  mal_calibrada  <  calibrada  <  con_plata

El orden importa: es lo que hace posible la regla nueva de `sellar()`.

**La regla nueva: el que llama puede BAJAR la confianza, nunca
subirla.** La tabla `MEDICIONES` dice qué se midió por eje, pero cuánto
vale depende de qué métrica se muestra — goles calibra bien, remates
mal— y eso solo lo sabe quien arma el eje. Que solo se pueda bajar es
lo que mantiene la regla original en pie: nadie se declara más
confiable de lo que la medición permite. Está testeado en los dos
sentidos.

**El eje vale lo que vale su métrica peor.** Como en pantalla va
remates, el eje entero sale `mal_calibrada` y el chip dice *"una de las
tres no es de fiar"*. Mostrar goles bien calibrado al lado de remates
mal calibrado y declarar el conjunto "calibrado" sería usar lo bueno
para tapar lo malo.

En pantalla, remates va en **gris apagado**, no en terracota: la
terracota dice alerta y esto no es una alerta, es un dato que no hay
que usar para apostar (`DESIGN.md`, un color un solo trabajo).

**Un bug encontrado mirando, que ningún test iba a encontrar.** La
leyenda decía *"23 partidos en la muestra"* usando `j.pj` —la
temporada entera— mientras el número se calcula con `serie.pj`, que
suele ser 3. O sea que decía que el dato era ocho veces más firme de lo
que es, y el que lee no tenía cómo saberlo. Corregido: ahora dice *"el
número sale de sus últimos 3 partidos"*.

**Una falsa alarma que vale documentar**, porque el próximo que mire va
a sospechar lo mismo: Kevin Serna y Hulk aparecen con `gol 0.24` y
`al arco 0.74` idénticos. No es una fusión de jugadores — sus series de
goles son las dos `[1,1,0]`, por casualidad, con tres partidos cada
una. Se verificó antes de tocar nada.

Cobertura: 38 de 49 partidos tienen el eje (arg y bra completos, eng y
fra a medias — ESPN todavía no publica series por jugador de todos los
equipos europeos). Donde no hay, el eje no aparece: media lectura es
peor que ninguna.

### Addendum 6 · Qué mueve los remates de un jugador: medido, y no es el rival (2026-08-31)

La pregunta es de Lucas, textual: *"no sé cuáles son las variables que
pueden intensificar las probabilidades de que x jugador remate. Puede
ser el equipo — al Fluminense le suelen rematar mucho los
mediocampistas — o los laterales contra estos rivales suelen pegar de
afuera."*

Es la pregunta correcta, porque el número de jugador **no mira nada de
eso**. `esperado_jugador()` toma la serie reciente y la encoge hacia el
promedio del puesto. No mira contra quién juega, ni cuánto remata su
equipo, ni si el partido pinta trabado. Y es la métrica peor calibrada
que tenemos (2.09 veces el ruido).

Lo llamativo es que la información ya estaba en casa: a nivel EQUIPO la
app sí ajusta por lo que concede el rival. Ese ajuste nunca bajó al
jugador.

`medir_ajuste_jugador.py` lo baja y lo mide, walk-forward, contra lo
que se publica hoy:

| pronóstico | error² | le gana a hoy | e.e. |
|---|---|---|---|
| hoy | 1.4775 | — | — |
| ajustado por rival | 1.6092 | **−0.1317** | 0.0476 |
| por cuota del equipo | 1.9540 | **−0.4765** | 0.1495 |

**Los dos empeoran**, con 2.8 y 3.2 errores estándar, y el
dejar-uno-afuera no cruza el cero en ninguno (rival: −0.17 a −0.08;
cuota: −0.55 a −0.35). No es un partido: es el ajuste.

**Por qué, y es la misma lección de siempre en este repo.** El factor
del rival sale de 3 o 4 partidos, así que es una estimación ruidosa.
Multiplicar un número ruidoso (la serie del jugador) por otro número
ruidoso (el factor) suma varianza sin sumar señal. Es exactamente lo
que `parametros_metricas()` ya sabía a nivel equipo: con pocos partidos
hay que encoger MÁS, no multiplicar.

**Qué NO prueba.** No prueba que el rival no importe — prueba que
*esta estimación del rival* hace daño. Un factor bien estimado
necesitaría muchos más partidos por equipo, y los anclas largos que
darían eso existen solo para eng y fra, que son justo las ligas donde
ESPN todavía no publica series por jugador de todos los equipos. El
camino queda abierto y con una condición clara.

**Lo de "partido trabado o dinámico": no está medido.** Se puede
derivar (faltas esperadas, λ total) pero nadie probó que prediga
remates de jugador. Es candidato, no hallazgo.

**Y un cambio de producto que sí entró**, porque era estructura y no
decoración: el eje Jugadores ahora agrupa por **línea** — Delantera,
Mediocampo, Defensa — con dos candidatos por línea en vez de una lista
sola. Con una lista sola la delantera se llevaba todos los lugares
siempre: verdadero e inútil, porque el que mira ya sabe que los
delanteros rematan más. Lo que no sabe es cuál de los volantes de ESTE
partido llega mejor, y eso solo se ve comparando adentro de su línea.

Herramientas: `medir_ajuste_jugador.py`, `test_medir_ajuste_jugador.py`
(28 pruebas). El test encontró dos cosas antes que yo: que `evaluar()`
no era inyectable —dependía de `planteles.json` para tener tests— y que
un fixture con jugadores idénticos deja a `parametros_metricas()`
devolviendo `{}`, porque necesita variación entre jugadores y ocho de
ellos como mínimo.

### Addendum 7 · El eje Contexto: cableado, y declarado sin medir (2026-08-31)

Lo preguntó Lucas — *"¿no nos falta la skill?"*— y tenía razón: el plan
tenía cinco pasos y quedamos en el tercero. Contexto es el paso 5, y es
el único eje que **no calcula nadie**: lo escribe la skill
`valor-analisis-inclinacion` a mano en `data/analisis.json`.

**Queda `sin_medir`, y es la decisión importante de este addendum.**
Hay script que lo mide (`medir_analisis.py`) y hay medición hecha: la
skill inclinaba al local el **69% de las veces contra el 45% que
corresponde**. Eso se corrigió el 2026-08-30 y **no se volvió a medir**
— hace falta una fecha nueva de análisis escritos con la skill
corregida. Declararlo "calibrada" con la corrección sin verificar sería
exactamente el error que este contrato existe para impedir.

**Es el único eje que trae la `lectura` llena.** Los otros cuatro la
dejan en `null` porque el texto lo compone la pantalla; acá el texto
**es** el dato — lo escribió una persona. El contrato lo soportaba
desde el principio sin que nadie lo hubiera usado.

**No se agregó un sexto bloque a Pronósticos, a propósito.** Lucas
acababa de decir que esa pestaña está sobrecargada, y el análisis ya
tiene su propia pestaña. El eje entra al **contrato** para que la
arquitectura esté completa y Claude Design decida dónde ponerlo; sumar
píxeles a la pestaña que se está por rediseñar hubiera sido trabajo
para tirar.

Cobertura hoy: 1 de 49 partidos tiene análisis cargado. No es un bug —
`analisis.json` es carga manual y solo se escribe para los partidos que
se miran en serio.

Con esto el contrato tiene **cinco ejes**: resultado, volumen, dominio,
jugadores y contexto. Falta Fricción (faltas, tarjetas, árbitro), que
está medido y da poco: faltas con sesgo de 9 puntos, tarjetas sin
aporte, y el árbitro sin efecto detectable por permutación.

### Addendum 8 · La segunda skill: el mercado de estadísticas (2026-08-31)

Lucas lo había pedido y yo lo había dejado pasar: *"¿no te había dicho
que yo quería una skill aparte para estadísticas? Tenemos la principal
del partido, faltaría la de estadísticas, quiero que tengamos dos
mercados divididos en un partido."*

Tenía razón y ahora están los dos.

| skill | expediente | escribe | alimenta |
|---|---|---|---|
| `valor-analisis-inclinacion` | `expediente.py` | `analisis.json` | inclinación + eje Contexto |
| **`valor-analisis-estadisticas`** | **`expediente_estadisticas.py`** | **`analisis_estadisticas.json`** | **lectura de Dominio y Jugadores** |

**Dónde encaja en la arquitectura, y por qué encajó sin pelear.** Los
ejes Dominio y Jugadores tenían la `lectura` en `null` desde que se
construyeron — el contrato la soportaba y nadie la llenaba. La skill
nueva la llena. No hubo que tocar el contrato ni `sellar()`: un campo
que ya existía encontró quién lo escribiera.

**Las tres reglas duras de la skill nueva salen de mediciones**, no de
criterio:

- **no escribe una cifra de remates** como pronóstico — la métrica está
  medida y se desvía 2.09 veces el ruido. Puede decir "es el que más
  patea"; no puede decir "va a rematar 3 veces";
- **no le atribuye nada al árbitro** — efecto sobre tarjetas medido por
  permutación, y da cero;
- **no habla de quién gana** — ese es el otro mercado, y repetirlo hace
  que el usuario lea dos veces lo mismo.

**El expediente es una lista blanca, igual que el otro**, y tiene una
exclusión que no es obvia: `corners`, `fouls` y `cards` de
`partidos.json` **no viajan**, porque son *los que esperamos nosotros* —
salida del modelo disfrazada de dato. Lo que sí viaja son los promedios
crudos por equipo, que es otra cosa. Hay un test que lo ata.

**Lo que hace útil al expediente nuevo es `concede`.** Sin él la skill
solo puede describir a un equipo; la pregunta del mercado de
estadísticas es casi siempre sobre el cruce. Probado en Athletico–
Fluminense: el promedio de Athletico dice 9.75 remates y esconde que de
local produce 20 y de visitante 6.33 — el split cambia la lectura
entera.

Verificado de punta a punta: expediente → skill → JSON → los dos ejes
mostrando el texto arriba de sus números, en el navegador, con datos
reales.

Herramientas: `expediente_estadisticas.py`,
`test_expediente_estadisticas.py` (32 pruebas, la mitad sobre que no se
filtre la salida del modelo), `.claude/skills/valor-analisis-estadisticas/`.

### Addendum 8bis · Los cuatro huecos de la skill nueva (2026-08-31)

Lucas preguntó si la skill le transmite al apostador todo lo que
necesita. No. Cuatro huecos, y el primero lo probó la propia salida de
la skill.

**1. No exigía mirar si el jugador es titular.** El dato viajaba
(`titular_en`) y nadie lo miraba — incluido el primer análisis, que
recomendó a **Kevin Serna** por su eficiencia al arco sin decir que
había arrancado **1 de 3**. Un pronóstico de remates de alguien que
entra a los sesenta no sirve. Ahora el expediente manda un campo
`arranca` que dice `titular`, `suplente` o `2 de 3` en castellano, hay
un aviso, y la skill tiene el principio D-bis con el caso adentro. El
análisis se reescribió.

**2. Faltaba `atajadas`.** Está en el caché, se cotiza, y quedó afuera
de `METRICAS_EQUIPO` por olvido. Entró, junto con `offsides` — que
describe una línea alta, y una línea alta produce córners.

**3. Nadie sabe quién patea córners, tiros libres y penales.** Es el
dato que más define esos mercados y **no existe en ninguna fuente que
tengamos**. No se puede arreglar con código: quedó como aviso explícito
del expediente y como obligación de research. Es un pendiente real, no
una tarea.

**4. No hay ausencias.** ESPN devuelve a todos los jugadores como
activos — el expediente del resultado ya lo declaraba y este no. Mismo
tratamiento: aviso explícito, y la skill no puede llamar "candidato
firme" a nadie sin chequear la alineación.

La lección que vale más allá de esto: **una skill se audita corriéndola
y leyendo lo que escribió, no releyendo su documento.** El hueco 1
estaba en el SKILL.md como dato disponible y aun así la salida lo
ignoró.


## 18. Tres capas en vez de siete pestañas (2026-09-01)

El rediseño llegó como entrega de Claude Design
(`design_handoff_valor_tres_capas`) y se aplicó entero sobre
`index.html`. **No toca el motor**: `escalera()`, `otrosMercados()`,
`probMayor()`, `construirEjes()` y las constantes se llaman igual que
antes. Es reorganización de presentación, y las cuatro suites siguen en
verde (40 + 22 + 107 + 43).

### El diagnóstico, que no era de contenido sino de corte

Las siete pestañas —Análisis · Pronósticos · Estadísticas · Historial ·
Posiciones · Plantel · Herramientas— estaban cortadas por **origen del
dato**: la skill humana, el motor de goles, el caché de disciplina, las
tablas de ESPN, el roster. Ninguna correspondía a lo que el que mira
está tratando de hacer. De ahí salían cuatro defectos, y ninguno se
arreglaba escribiendo mejor adentro de una pestaña:

1. **Dos lugares recomendaban.** Pronósticos recomendaba resultado y
   goles; Estadísticas recomendaba córners, tarjetas y candidatos de
   jugador. Es la misma intención partida por familia de mercado:
   mientras existan dos, el solapamiento vuelve siempre.
2. **La afirmación y su evidencia vivían separadas.** El análisis decía
   "la defensa está rota" y el número estaba tres pestañas más allá.
3. **Historial, Posiciones y Plantel** pesaban lo mismo que una
   recomendación, y eso aplana la jerarquía: si todo parece igual de
   importante, nada lo es.
4. **De los jugadores solo se veían los destacados**, con los 18 de cada
   plantel bajados y sin mostrar.

### El corte nuevo

| Capa | Qué contesta | Absorbió |
|---|---|---|
| **Veredicto** | ¿hay algo apostable? | Pronósticos + candidatos de Estadísticas + Herramientas |
| **Lectura** | ¿por qué lo decimos? | Análisis + Contexto, con Historial y Posiciones como evidencia inline |
| **Datos** | quiero mirar yo | Estadísticas crudas + Plantel + Historial y Posiciones completos |

Abajo siguen los dos destinos del producto: **Registro** y **Método**.
Que queden fuera del flujo de buscar algo para apostar es deliberado —
es lo que impide que la app se lea como una máquina de picks.

**Un solo lugar recomienda, y el solapamiento desaparece por
construcción y no por disciplina.** Eso es lo que se compró con el
rediseño.

### Lo que la pantalla ahora dice y antes callaba

- **El estado de cada mercado, con su motivo.** SIN VENTAJA · SIN PRECIO
  · SIN DATO · NO OPINAMOS. Un mercado que no aparece se lee como un
  mercado que nadie miró; uno que aparece diciendo "sin precio" es una
  respuesta. El más caro de escribir es el cuarto: dice que la medición
  existe y salió mal.
- **Cero oportunidades como estado terminado.** Con el ROI en
  −3.27% ±6.19 —el intervalo cruza el cero— un día sin nada apostable es
  lo normal, no una falla. La pantalla vacía se implementó **primero**.
- **`concede` en las nueve métricas**, siempre en el par produce /
  concede. Estaba medido y se mostraba en un renglón chico al pie: se
  estaba viendo la mitad del dato.
- **La señal medida como atributo del número**, no como disclaimer al
  pie: sale de `calibracion_lineas.json` y `calibracion_jugadores.json`,
  y donde no hay medición dice SIN MEDIR. El diseño proponía una tabla
  fija (posesión y tackles "señal alta"); eso venía de
  `medir_discriminacion.py` y **no está en ningún JSON que la app lea**,
  así que se derivó del dato que sí está — la regla del repo: leerlo del
  dato, no cablearlo.
- **Los planteles enteros**, ordenables por cualquier métrica, con la
  titularidad en el renglón (`serie.tit`/`serie.pj`; el handoff lo
  llamaba `arranca`, que es el nombre que usa el expediente, no el del
  JSON). El suplente se atenúa y se dice, **no se esconde**.
- **El intervalo del ROI en Registro**, con las tres marcas —banda,
  punto y cero— derivadas de la misma escala, calculada de la dispersión
  de los retornos. Un ROI sin intervalo es una promesa.

### Dos decisiones propias, contra el handoff

- **El filtro de localía arranca en "Este cruce"**: el local con su
  promedio DE LOCAL y el visitante con el suyo DE VISITA. El handoff
  proponía Todo/Local/Visita con "Todo" como promedio general, y eso
  perdía la lectura que la comparativa vieja ya hacía bien — que es
  justo la que el partido de hoy pone en juego.
- **Herramientas no desapareció.** El handoff no la menciona (la entrega
  se hizo sobre las seis pestañas de contenido). Cargar la cuota de tu
  casa y anotar en el Registro son actos de apostar, así que viven
  adentro de Veredicto, detrás de un toque, y no ocupan un destino de
  primer nivel.

### Lo que se borró, y a dónde fue cada cosa

Se eliminaron `tabAnalisis`, `tabPronosticos`, `tabEstadisticas`,
`tabHistorial`, `tabPosiciones`, `tabPlantel`, `comparativa`,
`bloqueLineas`, `bloqueDominio`, `bloqueJugadores`, `sello`,
`fraseCorta`, `nombreSello` y `tarjeta`. Ninguna funcionalidad se
perdió: el precio real de córners de Bet365 y la escalera de líneas por
equipo pasaron al cuerpo desplegable de su fila de mercado, la combinada
es una fila más del Veredicto, el eje Jugadores de la segunda skill es
el bloque 04 de Lectura, y el desarrollo, la inclinación declarada y el
marcador más probable están en Lectura.

**Los tests se mudaron con la pantalla.** Cuando una función de
presentación desaparece, el contrato que la cuidaba no se borra: se
apunta a lo que ahora sí dibuja. Un test que mira una función muerta da
verde sin proteger nada.

### Una trampa que dejó el rediseño, y cómo quedó tapada

El veredicto de un partido se **memoiza por id** (`_veredictos`): la
portada lo necesita para los 17 partidos del día en cada render. Si algo
lo pide antes de que termine de entrar el dato —una pantalla dibujada a
mitad de carga, una prueba desde la consola— queda cacheado un veredicto
calculado sin estadísticas y la app lo repite todo el día. Pasó al
probar. El arranque limpia la caché después de asignar los JSON, y el
`cargar()` de los tests hace lo mismo.


## 19. Lo que la pantalla no decía (2026-09-01)

Lucas revisó las tres capas ya publicadas y señaló seis cosas que no se
entendían. Cinco eran de presentación; una destapó un bug de contenido y
otra un bug de CSS que llevaba semanas puesto. Todo lo de acá es
`index.html` salvo el once real, que toca `actualizar.py`.

### 19.1 Los cuadros de ganado/empatado/perdido no tenían letra

`tiraForma()` **ya escribía G/E/P adentro de cada casilla**. La regla
`.plin .forma.mini i` le ponía `font-size:0`. La portada mostraba cinco
cuadros mudos, sin leyenda al lado, y no había de dónde sacar el código.

Y había un segundo dibujo del mismo dato: Historial usaba `.cinco` con
cuadros propios sin letra más una leyenda al pie. Dos dibujos del mismo
dato obligan a aprender dos códigos. Ahora Historial usa `tiraForma`; la
leyenda queda porque presenta la letra una vez, no porque el cuadro no
diga nada.

La casilla mini pasó de 9 a 11px (una letra de 8px necesita eso) y la
columna de la portada de 53 a 63px.

### 19.2 `crest()` existía y no lo llamaba nadie

Función completa, con placeholder para el 404 de ESPN y todo, sin un
solo llamado. Los escudos de la portada se dibujaban con un `<img>`
inline aparte, y el resto de la app no tenía ninguno.

Ahora lo llaman los diez lugares que nombran un club: portada (renglón y
talón), cabecera del partido, Datos · Jugadores (renglón y filtro),
Lectura (Tabla, Antecedente, Jugadores), pie de las barras de Equipos,
Posiciones, Cara a cara, Últimos cinco y el selector de Planteles.

Dos efectos que valen por sí solos:

- **Las tarjetas del Antecedente decían `1-5` y la fecha.** Para saber
  quién puso el 1 había que acordarse de que el orden es local-visitante
  y de quién jugó de local aquella vez. Ahora llevan los dos escudos en
  el orden del marcador. El cruce es por **igualdad exacta** contra
  `m.home`/`m.away`: un nombre que no es ninguno de los dos va al hueco.
  Un escudo adivinado no se ve como un error, se ve como el partido al
  revés.
- **En Datos · Jugadores hay homónimos.** Mirassol tiene dos Carlos
  Eduardo. El nombre no alcanzaba ni sabiendo la liga.

El escudo le comió 20px al renglón de Lectura · Jugadores y empezó a
cortar nombres. Se recuperó sacando `GOL ESPERADO` de los seis renglones
y diciéndolo una vez arriba de la columna: seis repeticiones de las
mismas tres palabras no informaban seis veces, ocupaban.

### 19.3 El filtro local/visita no cambiaba nada, y no lo decía

`MIN_SPLIT` es 4 y está bien fundado (§ del split). Con el caché en 4
partidos por equipo quedan **2 por sede**, así que `ladoDe()` caía al
total en las tres opciones: tres botones, los mismos diez números,
ningún aviso. El que mira concluye que el equipo juega igual de local
que de visitante, que es justo lo que el dato no dice.

`alcanceFiltro()` cuenta en cuántas métricas cambiaría cada filtro. Con
cero, el botón se apaga y muestra con cuántos partidos cuenta (`2 PJ`),
y abajo va la razón. **"Este cruce" no se apaga nunca**: es el default y
su caída al total es la lectura correcta. El filtro elegido persiste
entre partidos, así que si viene puesto de uno que sí tenía muestra, la
marca vuelve al default en vez de dejar los tres sin marcar.

### 19.4 La serie del jugador — tres bugs en una columna

**La barra no se podía leer.** `.spark` normalizaba contra el máximo DE
ESE JUGADOR: la barra más alta de uno y la de otro no valían lo mismo, y
no había forma de saberlo. Reemplazada por la pieza `.sq` que Lectura ya
usaba —cuatro intensidades con el número adentro—, bajada al renglón
porque en 64px de columna ocho casillas no entran. Una sola función
(`tiraSerie`) la dibuja en las dos pantallas.

**Iba al revés del tiempo.** `planteles.json` guarda la serie del más
nuevo al más viejo (`jugados` viene ordenado por fecha descendente, ver
`actualizar.py`). La app la dibujaba cruda, o sea al revés que la tira
de los últimos cinco, que sí se invierte. Dos tiras al lado con
direcciones opuestas no se leen como órdenes distintos: se leen mal.

**`SIN SERIE` acusaba a la fuente equivocada.** El pie decía "la fuente
no publica el partido a partido de esa liga" mientras en el mismo
Mirassol diecinueve compañeros tenían serie. Que la fuente publique es
propiedad de la **liga**, no del jugador: si algún compañero tiene
serie, el que no la tiene es porque no jugó. Ahora son dos estados
distintos, `SIN SERIE` y `NO VIENE JUGANDO`.

Eso arrastraba lo peor: sin serie, MED cae al promedio de temporada **sin
encoger**, y se ordenaba contra números encogidos. `Tiziano Perrota`
encabezaba la lista de remates de Defensa sin haber jugado ninguna de
las últimas fechas — el primer nombre que leía el que apuesta era el que
no juega. Ahora los que tienen serie van primero. No se esconden: se
ordenan.

### 19.5 El bug de contenido: el análisis leyó la serie al revés

Verificando la dirección de la serie contra ESPN partido por partido:

    Juan Gutiérrez — remates
    09/08: 6    17/08: 2    23/08: 1

`expediente_estadisticas.py` manda la serie cruda **sin decir de qué
lado está el presente**, y la skill la leyó de izquierda a derecha. El
análisis publicado de Defensa y Justicia – Platense dice que Gutiérrez
"subió su volumen" con "uno, dos y seis". Viene bajando. Lo mismo con
Zapiola ("irrupción tardía" sobre una serie 6, 1, 2).

Arreglado en la causa: el expediente manda la serie en orden
cronológico, con un aviso explícito, y `SKILL.md` lo anota. **El texto
ya publicado en `data/analisis_estadisticas.json` sigue invertido** —
es carga manual y hay que volver a correr la skill para esos partidos.

Regla general: una lista de números sin fecha se lee de izquierda a
derecha como se lee el tiempo. Un orden implícito no se ve como un
error, se ve como una tendencia.

### 19.6 Dos cosas se llamaban `.mas`

La máscara de degradado que avisa "hay más a la derecha" en las tiras
que se cortan, y el `+`/`−` de los acordeones. El glifo mide 10px y la
máscara pone su tramo opaco en `calc(100% - 30px)` —o sea en −20px—, así
que **todo el signo caía adentro del degradado y se dibujaba semi
transparente**. Por eso el `+` de "SEÑAL BAJA +" se veía lavado y pegado
al texto en vez de leerse como un control. La máscara pasó a `.corte`.

Dos nombres iguales para dos cosas distintas no fallan: se tapan.

### 19.7 El once real, no el inferido

`cancha()` dibujaba a los que más partidos llevan, acomodados por
puesto, con una nota que decía que **ESPN no publica ni el equipo
titular ni el esquema**. Verificado contra la API el 2026-09-01: para un
partido YA JUGADO sí los publica.

    Racing Club   formation= 4-2-3-1   starters 11
    Boca Juniors  formation= 4-3-3     starters 11

`rosters[]` trae `starter`, `jersey`, `formationPlace` y `formation`, en
el mismo `/summary` que el cron ya pide para la serie: **cero pedidos
nuevos**. `once_partido()` saca los once de cada lado y `ultimo_once()`
elige el partido más reciente que tenga uno —recorre hacia atrás, porque
un partido sin `rosters` cargados no puede dejar al equipo sin once— y
lo guarda con su fecha, su rival y su marcador. Un once sin fecha se lee
como el once de hoy.

Un lado con distinto de once titulares se descarta entero, que es el
mismo criterio que ya usaba `onceProbable()`: un dibujo con ocho
jugadores miente sobre el equipo tanto como uno con cuatro delanteros.

En la app: cinco filas y no cuatro, porque ESPN dice `CD-L`, `AM-R`,
`LF` y no `D`/`M`/`F`, y eso es justo lo que separa el "2" del "3" en un
4-2-3-1. La fila vacía no se dibuja. **El dibujo manda sobre la
etiqueta**: si el esquema que publica ESPN no coincide con el que sale
de las posiciones, se rotula el que se dibuja — una cancha con cinco
volantes abajo de un cartel que dice 2-3 es peor que no poner cartel.
Los dorsales reales reemplazan a la letra del puesto.

`resumen_completo()` ahora exige `_once`, así que los resúmenes ya
cacheados que se vuelvan a mirar se re-piden una vez. Es
auto-limitante: solo se re-piden los que la ventana de partidos
recientes toca.

Sin la clave `once`, la cancha se comporta exactamente como antes.

### 19.8 Los chicos

- `19:30 → 19:30 · 1 mirado, ninguna` — "ninguna" ¿qué? La palabra
  "oportunidad" no aparecía en esa rama de la franja. Y el rango de
  horas de un solo partido ahora muestra una hora sola.
- El club dejó de repetirse en Datos · Jugadores cuando la lista está
  filtrada a un equipo: ahí ya lo dicen el botón de arriba y el escudo
  del renglón.

### Qué quedó verificado

    test_alineacion  117 ok   (11 nuevos)
    test_registro     22 ok
    test_ejes         40 ok
    test_plantel      45 ok   (9 nuevos)
    test_expediente_estadisticas  34 ok  (2 nuevos)

Los tests nuevos fallan contra el código viejo, que es la única forma de
que un test proteja algo: dirección de la serie, orden de la lista,
`SIN SERIE` contra `NO VIENE JUGANDO`, el filtro que se apaga y el que
sigue vivo, el once real y su caída al inferido, y que el cartel del
esquema nunca contradiga al dibujo.

### 19.9 Tres cosas más, del mismo repaso

- **El dorsal ya venía y se tiraba.** `roster()` recibe `jersey` y
  `aplanar_jugador()` no lo guardaba. Mirassol tiene **dos Carlos
  Eduardo** en el mismo plantel: ahí el escudo no distingue nada. Ahora
  `planteles.json` trae `dorsal` y va detrás del nombre, en la línea de
  arriba — no en la de contexto, que ya se estira sola.
- **Qué significa la tinta, dicho en pantalla.** "Tinta plena = número
  más alto, NO número mejor" estaba escrito en el código y en ningún
  lado de la app. En `Produce` el más alto se lee como el mejor y no hay
  problema; en `Concede` es exactamente al revés y el mismo dibujo dice
  las dos cosas. Se aclara con una línea de texto: meter un semáforo
  sería una opinión disfrazada de dato.
- **`injuries` de ESPN está siempre vacío.** El aviso "el plantel no
  dice quién falta" era una afirmación heredada; el 2026-09-01 se midió
  sobre 166 jugadores de cuatro equipos: `injuries: []` y
  `status: active` en los 166. El aviso es correcto y ahora está
  verificado.

### Lo que queda abierto

- **La prosa del eje Jugadores se corrigió a mano donde estaba
  invertida, no se regeneró.** En `espn401841528` dos lecturas decían lo
  contrario del dato (Gutiérrez "subió su volumen" con 6→2→1; Zapiola
  "irrupción tardía" con 6→1→2) y se reescribieron con la serie
  verificada contra ESPN; en `espn401913077` se dieron vuelta los cinco
  arreglos citados para que coincidan con lo que la app dibuja. **Se
  tocó solo lo que la verificación mostró falso** — los juicios de
  magnitud, la titularidad y las advertencias quedaron como los escribió
  la skill. Lo correcto sigue siendo volver a correrla para esos
  partidos.
- En `espn401913077`, "Pedro… en dos de esos llevó tres al arco": la
  serie al arco es 0, 3, 2, 0 — un partido con tres, no dos. No es un
  error de dirección y no se tocó.


## 20. Cambiar de casa no es la palanca, y el +2.79% es la trampa (2026-09-02)

Lucas preguntó si quedaba algo a mano para mejorar la certeza de la app.
La respuesta corta es que no, y esta sección existe para que la
propuesta que se hizo acá no se vuelva a hacer.

### La hipótesis, y por qué era razonable

El razonamiento fue: el ROI de la regla de valor da −9.17% en arg y
−9.13% en bra, y la app marca contra DraftKings, que cobra **7.7% de
margen**. Pinnacle cobra **3.13%**. Si el modelo tuviera habilidad
cercana a cero, la diferencia de margen explicaría buena parte de la
pérdida, y bajar el precio devolvería del orden de cuatro puntos **por
aritmética, no por acertar más** — cinco veces más grande que cualquier
cosa que se haya intentado del lado del modelo (`barrido_remates` daba
+0.8 errores estándar, `medir_encogimiento` daba ruido).

Apoyaba la idea que `mercado_extra.py` pide **una sola casa**
(`CASA = "Bet365"`) cuando odds-api.io devuelve `bookmakers[CASA]` y
acepta varias, y que `probar_odds_api.py` existe justamente para esta
pregunta y no tiene resultado registrado en ningún lado.

### Por qué está mal

**`medir_roi.py` ya mide a la cuota de cierre de Pinnacle.** Está
escrito en su propio encabezado: "Reutiliza entero el arnés
walk-forward de `medir_historico.evaluar()` — devig de Shin; cuota de
cierre real de Pinnacle cuando está".

O sea que el −9.17% **ya está medido al precio bueno**. No hay cuatro
puntos tirados en el margen: no se están perdiendo ahí.

Peor: la brecha corre en la dirección contraria a la que se supuso. La
medición usa Pinnacle y la app apostaría contra DraftKings, así que el
número real de la app es **por debajo** de −9.17%, no por encima. El
−9.17% es optimista, no pesimista.

### Y la medición que se propuso ya existía

Se propuso medir el ROI a la apertura de la casa blanda, "que nadie
midió". Falso: `medir_apertura.py` ya toma `casa` como parámetro y mide
Pinnacle **y** Bet365, y §6 ya tenía anotado que contra Bet365 el CLV da
cero. Antes de proponer una medición, buscar si el script ya la hace con
otro argumento.

### Lo que dio al correrlo (2026-09-02)

```
eng          ROI apertura      CLV
Pinnacle     +2.79% ±14.82     −1.62% ±0.82
Bet365       −4.27% ±13.57     −0.44% ±0.82   (ruido)

fra          ROI apertura      CLV
Pinnacle     −9.91% ±15.64     −0.56% ±1.07   (ruido)
Bet365      −10.09% ±14.87     +0.05% ±1.03   (ruido)
```

**Sí hay diferencia entre casas, y es grande donde aparece:** 7 puntos
de ROI en Inglaterra. Pero en Francia son 0.2 puntos. Un efecto que
aparece en una liga y desaparece en la otra, con ±15 encima, no es un
efecto — es la misma trampa que `barrido_valor.py` documentó con los
umbrales.

### El +2.79% es la trampa, y hay que decirlo con nombre

Es el único número positivo del conjunto. **No perseguirlo.**

Ese mismo set de 362 apuestas tiene un **CLV de −1.62% ±0.82**: dos
errores estándar por debajo de cero, y el único número de toda la tabla
que sale del ruido. La línea se mueve **en contra** el 60% de las veces.

Es exactamente el caso que la regla del proyecto anticipa:

> Si la línea se mueve hacia donde apostamos, hay información real en el
> modelo aunque la muestra de resultados todavía no lo muestre. Si no se
> mueve, no la hay aunque una racha diga que sí.

Acá no es que no se mueve: se mueve para el otro lado. El +2.79% es la
racha que la propia regla manda ignorar, y con ±14.82 ni siquiera hace
falta el CLV para saberlo.

### El agujero que queda abierto de verdad

`arg` y `bra` —las dos ligas donde vive el producto— **no tienen cuota
de apertura en football-data**. El precio real al que se apuesta ahí no
se puede medir hacia atrás con la fuente que hay. Todo lo que sabemos de
esas dos ligas es a cierre de Pinnacle, que no es el precio de la app.

Eso no es un resultado negativo más: es un hueco de medición, y es
distinto. Si algún día aparece una fuente con apertura para
Sudamérica, esta es la primera pregunta que hay que volver a hacerle.

### Lo que sigue cerrado

Sumado a lo de §5 y §6, la lista de caminos medidos y cerrados para
mejorar el rendimiento:

λ · umbrales de valor · encogimiento · remates como fuerza · consenso
sin modelo · goles condicionados · ajuste del jugador por rival ·
bajas → goles · árbitro → tarjetas · córners por equipo · **cambiar de
casa**.

## 21. El Veredicto deja de estar mudo (2026-09-02)

Lucas: *"el 90% de los partidos no pone nada en el veredicto, ¿está
bien?"*. No, y era el reclamo más justo de toda la sesión. Un asesor que
no dice nada nueve de cada diez veces no es un asesor, aunque tenga
razón en callarse.

Hasta hoy, un partido sin marca de valor mostraba `No hay nada acá · N
mercados mirados, ninguno con precio a favor` y ahí se terminaba la
pantalla. `loQueSabemos()` agrega debajo, pegado al mismo panel, hasta
cuatro afirmaciones — cada una con su número:

1. **La métrica en la que más se distinguen estos dos equipos**, y solo
   entre las de señal ALTA. No la más alta: la que más separa, que es la
   única que dice algo del cruce. Con separación menor al 12% no se dice
   nada.
2. **Cuánto le falta al precio más cerca de encenderse.** La escalera lo
   contestaba con la cuota mínima, que obliga a restar de cabeza.
3. **Cuando el mercado nos gana de mano**, dicho con todas las letras:
   es la única señal que tenemos de que el precio sabe algo que nosotros
   no.
4. **Qué mirar a la hora del partido** — el once confirmado, que es lo
   único que llega DESPUÉS de que la casa puso la línea.

### El caso que casi sale mal

En arg y bra la regla de valor está medida perdiendo, así que ahí decir
"le faltan N puntos para que la marquemos" invita a esperar que los
junte — y aunque los juntara, no la marcaríamos. En esas ligas la frase
es la otra: *"tiene 10 puntos de ventaja y aun así no la marcamos:
está medido que seguir la regla resta plata"*. Lo que falla no es el
umbral, es la regla entera en esa liga.

### Las dos reglas duras, con test

- **Nunca lleva mostaza.** El dorado significa "acá el precio está a
  favor" y esto es literalmente el caso contrario. Si el mismo color
  dijera las dos cosas dejaría de decir la primera, que es la única que
  cuesta plata (§18).
- **No aparece cuando SÍ hay oportunidad.** Ahí la tarjeta dorada es la
  respuesta y un segundo bloque compite con ella.

Verificado sobre 11 partidos reales de tres fechas, todos sin
oportunidad: los 11 pasan de silencio a 3 o 4 afirmaciones. 124 tests de
alineación, 0 fallando.

### Lo que esto NO es

No es una recomendación encubierta ni baja la vara de evidencia. Todo lo
que dice ya lo calculaba la app y lo escondía dentro de Datos, a dos
toques — o sea que el que abría un partido sin oportunidad no llegaba
nunca. Es la misma información, puesta donde se mira.

## 22. El primer lead que sobrevive a sus controles (2026-09-02)

`medir_props.py` mide el eje Jugadores contra **plata**, al precio real
de Bet365. Es el mercado más blando al que llega el proyecto: nadie en
Bet365 le dedica a "remates de Almada en Liga Profesional" el esfuerzo
que le dedica al 1X2 de Premier.

El 2026-08-31 se midió sobre 10 partidos, dio CLV +4.28% ±2.14, y **los
controles lo desarmaron**: un solo partido lo sostenía (+0.17% sin él) y
11 de 19 líneas no se habían movido. Quedó anotado como "no hay señal,
queda el instrumento".

### Al volver a correrlo con 25 partidos, el resultado se dio vuelta

```
umbral 4%:  89 apuestas · ROI +9.98% ±21.12 · CLV +3.32% ±0.86

LA VARA — la deriva de los escalones que NO se eligen
  3214 escalones sin elegir · +0.99% ±0.29
  los 89 que apostaríamos   · +3.32% ±0.86
  elegimos mejor por        · +2.33% ±0.91   (2.6 e.e.)

DEJANDO UN PARTIDO AFUERA POR VEZ
  peor caso +2.55%   ·   mejor +3.55%
```

**Los dos controles que en agosto lo mataron ahora lo sostienen.**

La deriva era la trampa principal, y es el control que este proyecto
inventó para no engañarse: si toda la escalera de precios se mueve, un
CLV positivo es la casa achicando su margen sobre la hora, no nosotros
eligiendo bien. Contra esa vara elegimos **2.6 errores estándar mejor**.

Y ningún partido lo carga: sacando cualquiera de los 25 queda entre
+2.55% y +3.55%. El CLV además es estable en los cinco umbrales medidos
(+3.09% a +3.70%), o sea que no es un filo de la grilla.

**Lo que más pesa: la señal creció con la muestra en vez de
desaparecer.** Es lo contrario de lo que hace el ruido.

### Los tres reparos que siguen en pie

1. **62 de las 89 líneas no se movieron** (70%). Ahí el CLV es cero por
   construcción, así que el número lo generan 27 apuestas, no 89.
2. **El "cierre" puede no ser el cierre.** El cron corre 09:00 y 15:00 y
   los partidos arrancan hasta las 21:00. `foto_props.py` se agregó el
   2026-08-31 justo por eso y lleva dos días. La deriva controla parte
   —los 3214 escalones se miden con la misma ventana— pero no todo.
3. **CLV no es plata.** El ROI a umbral 4% es +9.98% **±21.12**: no dice
   nada, y no va a decir nada hasta ~300 apuestas. Confundir las dos
   cosas es exactamente el error que costó tres semanas en §5.

### Qué hacer con esto

**Nada todavía, salvo seguir juntando.** Van 89 de las ~300 que hacen
falta para que el ROI diga algo, y `foto_props.py` ya mejora la
resolución del CLV desde el 31/08 — o sea que la muestra que viene es de
mejor calidad que la que produjo este número.

Lo que NO corresponde: marcar props en dorado en la app. La regla del
proyecto es que solo `con_plata` puede llevar apuesta, y esto todavía es
CLV, no plata. El eje Jugadores sigue en NO OPINAMOS hasta que el ROI
concluya.

Lo que sí conviene: **volver a correr esto cada 10 partidos nuevos** y
anotar la serie. Si el CLV sobre deriva se sostiene arriba de 2 errores
estándar mientras la muestra crece, es el primer camino abierto que tuvo
el proyecto. Si se desinfla, se cierra con evidencia y se documenta como
los otros diez.

## 23. "Lo más firme del partido" (2026-09-02)

Lucas, mirando la escalera de un partido sin marca: *"¿no podemos hacer
que aunque no haya apuesta ganadora diga la más cercana al acierto? Pero
acierto en serio, no cualquier cosa — si me tira que hay menos de 7.5
goles es cualquiera"*.

El pedido es legítimo y él mismo nombró la trampa. Ordenar por
probabilidad a secas pone arriba de todo lo que es verdad por
construcción. Se resolvió con cuatro filtros, y **tres de los cuatro
salieron de errores que se vieron en pantalla, no de pensarlo antes**.

### Los cuatro filtros, en el orden en que hicieron falta

**1 · Solo las líneas de la escalera en Goles.** Ya existía
(`LINEAS_ESCALERA`), por la razón de siempre: "menos de 4.5 al 82%"
tiene probabilidad alta por construcción y no dice nada del partido.

**2 · Solo el eje Resultado.** Primer error visto: con todos los ejes
mezclados salía *"Menos de 3.5 goles: le damos 27 puntos más que la
línea"*. En goles está medido que el aporte va de −0.9% a +0.4%, o sea
que esos 27 puntos no son un hallazgo — son el error del modelo de goles
dibujado como si fuera uno. Misma regla que ya usa `escalera()`.

**3 · Solo el 1X2, no la doble oportunidad.** Segundo error: cinco de
seis partidos decían *"Gana alguno (sin empate)"*. El empate ronda el
27%, así que esa opción da ~73% en **todos** los partidos. Es la misma
trampa del punto 1 desde el otro lado del tablero: una frase que sale
igual siempre no describe nada.

**4 · Y el piso de cuota NO aplica al 1X2.** Tercer error, y el más
instructivo porque Lucas lo había anticipado en el mismo mensaje: *"por
ahí Flamengo paga poco pero es el candidato"*. `CUOTA_MIN_ESCALERA`
(1.30) existe para matar líneas de gol triviales; aplicado al 1X2 hacía
exactamente lo contrario de lo pedido. En **Manchester City vs
Coventry**, City a 1.20 quedaba filtrado y "lo más firme" salía *Gana
Coventry al 30%*, por descarte.

### El número del mercado va SIEMPRE al lado

Decir "Gana Flamengo al 62%" sin nada más se lee como opinión nuestra
cuando puede ser el precio leído en voz alta. Ahora la frase dice las
dos, y el veredicto sobre la diferencia:

- **|dif| < 3pp** → "coincidimos: acá no estamos aportando una lectura
  propia, la estamos confirmando". Coincidir no es un fracaso; es
  información, y es lo que pasa en arg, donde el caché tiene muestra.
- **dif > VALOR_MAX (12pp)** → *no se llama ventaja*. "Arriba de eso el
  sospechoso es el modelo, no el precio" es la razón escrita de
  `VALOR_MAX` y vale igual acá. Un "+39 puntos" no es una ventaja
  enorme: es un número roto, y presentarlo como ventaja manda a apostar
  una cuota larga por un error nuestro.

### Lo que el bloque destapó, que estaba enterrado

**Manchester City vs Coventry, 2026-09-05:** λ 1.35 contra 1.10 —casi
iguales— mientras el mercado paga 1.20 contra 11.00. La causa es `pj 2`
en los dos equipos: con dos partidos en el caché el modelo los empuja a
los dos al promedio de la liga, y un gigante y un ascendido salen
parecidos. El número no está mal calculado: **está calculado sobre
nada**.

Eso vivía adentro de "Otros mercados" sin nada al lado contra qué
chequearlo. Ahora la app lo dice con el motivo, incluida la muestra:
*"tenemos 2 partidos de uno de los dos, y con esa muestra el modelo los
empuja a los dos al promedio de la liga"*.

Queda como pregunta abierta si corresponde publicar probabilidades de
1X2 con `pj < 4`, o declarar el partido sin lectura como ya se hace en
Datos · Equipos con el split por sede.

### 23bis · Con menos de 4 fechas no se publica nada (2026-09-02)

Decisión de Lucas después de ver el caso City–Coventry. La regla nueva:

    partidosJugados(m) < MIN_PARTIDOS (4)  →  no se publica probabilidad

Es el mismo 4 de `MIN_SPLIT` y por la misma razón medida: abajo de eso
el promedio se apoya en una muestra que el propio proyecto le prohíbe al
análisis. Acá el efecto es peor que un promedio flojo — es un 1X2
publicado con cara de lectura.

`partidosJugados()` lee la **tabla** (el conteo oficial de la
competición) y cae a `formH_general`/`formA_general` en las copas, donde
no hay tabla.

**Qué deja de publicarse:** la marca de oportunidad, los porcentajes de
la escalera, "lo más firme del partido", y el estado de la portada, que
pasa a `SIN MUESTRA`.

**Qué se sigue publicando:** los datos observados. "Al arco es donde más
se distinguen: Manchester City produce 7.5 contra 2.0" es un promedio de
lo que pasó, no una salida del modelo. La regla apaga las
probabilidades, no la pantalla.

#### La fuga que hubo que tapar aparte

`alerta()` —"el precio está en contra"— sobrevivía al corte, y se veía
en la portada de un partido donde ya habíamos decidido no opinar. Es una
afirmación sobre NUESTRO número (dice que el mercado le da más), así que
sin muestra no hay alerta: dejarla pasar era publicar la misma
probabilidad por la puerta de atrás, encima con cara de aviso.

#### Nota para quien escriba tests acá

`veredictoDe` memoiza por id de partido. Un fixture armado con
`{...partido, tabla:[...]}` comparte el id, así que hay que construirlo
**antes** de `cargar()` — que es lo que limpia la caché. Si no, el test
lee el veredicto del partido original y da verde sin mirar nada.

## 24. La app miraba las ligas equivocadas (2026-09-02)

Lucas, después de ver "16 partidos · 0 oportunidades": *"¿no te parece
heavy eso? Siento que ponés más parches y no solucionás el problema de
raíz"*. Tenía razón, y el número lo demuestra.

### Por qué el contador decía cero

    45 partidos por jugar
    26 → ligaSinValor   (arg + bra)
    19 → sinMuestra     (eng + fra, temporada de 2 fechas)
    ───────────────────────────────
     0 → llegan a evaluarse

26 + 19 = 45. **Ningún partido podía ser considerado.** No era que no
hubiera oportunidades: era que la app cubría cuatro ligas y en dos está
medido que la regla pierde.

### La liga que estaba medida y no estaba

`historico.py` traía `jpn` y `mex` "SOLO PARA MEDIR" desde el
2026-08-31, y decía textual: *"Estar en COMPETICIONES de actualizar.py
es otra decisión: esto solo las hace medibles"*. Se midieron y la
decisión nunca se tomó.

    jpn  +2.78% ± 7.67   (ruido)   ← no estaba en la app
    eng  +1.01% ± 8.92   (ruido)
    mex  −3.46% ± 7.50   (ruido)   ← medido el 2026-09-02, NO entra
    fra  −5.22% ± 8.71   (ruido)
    bra  −9.13% ± 7.32   negativo de verdad
    arg  −9.17% ± 6.44   negativo de verdad

**Ninguna liga es rentable de forma demostrada.** Japón tiene el mejor
punto estimado de las seis y el cero adentro del intervalo. Entra porque
es la menos mala y porque sin ella la app no tiene dónde hablar, no
porque prometa ganar.

### El error que se cometió en el camino, y conviene que quede escrito

Primero se ranquearon las ligas por **`aporte`** (mejora de Brier sobre
la tasa base) y México salía primera: +5.5% contra +5.2% de Japón. Al
medir su ROI dio **−3.46%**.

Es la lección de §5 otra vez — calibrar no es ganar plata — cometida con
el archivo abierto. **El orden por Brier no es el orden por plata**, y
antes de agregar una liga se mide su ROI, no su aporte.

### Las constantes de `jpn.1`, y de dónde sale cada una

    escala 0.60 · centro 2.695
      `barrido_escala_lambda.py jpn`, 4499 partidos, train 3103 / test
      1396. TODO k<1 le gana a producción en test y 1.00 es el peor de
      la grilla salvo 1.15. Train elige 0.60 y test 0.50: no coinciden,
      así que se toma el de train — criterio conservador, el mismo que
      se usó en eng y fra.

    conf 70 (no 80)
      El ROI es RUIDO, no una ventaja demostrada. 70 cae en el escalón
      de OCTAVO de Kelly, no de cuarto. Mismo movimiento que se le hizo
      a arg.1 cuando su medición no sostuvo el 75.

    corners 9.53 · fouls 22.65 · cards 2.77
      60 partidos de ESPN, medidos el 2026-09-02. No salen de
      football-data: Japón viene en formato "unico", que no publica
      estadísticas por partido.

    rho 0.00
      El neutro. Medirlo pide otro barrido y `barrido_lambda.py` ya dijo
      que producción está en el óptimo en las ligas donde se midió.

Verificado contra la API: 20 equipos, **5 partidos jugados cada uno** —
pasa `MIN_PARTIDOS` — y 10 partidos en el scoreboard de hoy.

### De paso: "Regular Season" en pantalla

ESPN llama `Regular Season` a la tabla única de una liga sin grupos.
`grupoEs()` devolvía ese string tal cual, así que el sello de Posiciones
habría dicho "REGULAR SEASON · 20 EQUIPOS" en inglés. Ahora los nombres
genéricos se descartan; los de verdad (Group A/B de Argentina) siguen
traduciéndose a Zona.

### Lo que esto NO resuelve

Queda en pie el otro cuello, y es el más grande: la regla de alineación
exige `!!dir` —un análisis cargado a mano— y hoy hay **0 de 45**. Japón
puede llegar a evaluarse, pero se va a frenar ahí hasta que se decida
qué hacer con esa regla, que es la única restricción del sistema sin una
medición que la sostenga (4 divergencias, 1 a 1, inconcluso).

## 25. Las cuotas de Bet365 estaban bajadas y la app usaba otras (2026-09-02)

Lucas: *"tampoco veo las cuotas o valores de Bet365 que antes estaban"*.
No faltaban. Estaban en el dato desde hacía semanas y la app no las
miraba. Tres defectos encadenados, y el tercero lo introduje yo veinte
minutos antes de encontrarlo.

### 1 · El precio se escondía en arg y bra

    if(sinValor) motivo = `${lee} · en esta liga la regla de valor resta`;
    else         motivo = `${lee} · pagan ${cuota}`;

En las dos ligas donde vive el producto, el motivo REEMPLAZABA al
precio. Que no recomendemos una apuesta no vuelve secreto lo que paga la
casa: el precio es un hecho. Ahora van los dos.

### 2 · `cuotaUsada()` no usaba Bet365

    1X2                 leía `mk` → DraftKings, 7.7% de margen
    doble oportunidad   devolvía `1/pMercado` → una cuenta NUESTRA,
                        presentada al lector con la palabra "pagan"

`mercado_extra.py` baja `mercadoExtra["1x2"]` y `mercadoExtra.dc` desde
hace semanas — justamente para que hubiera un precio real contra el cual
compararse. Nadie conectó esa fuente a la función que muestra el precio.

Verificado en Flamengo–Mirassol: la app decía **1.07** para "Flamengo
gana o empata" y Bet365 la paga **1.03**; decía 1.19 para "Gana
Flamengo" y Bet365 paga 1.181. Ahora Bet365 primero y DraftKings como
respaldo.

### 3 · La escalera mostraba dónde más discrepamos, no lo que pensamos

`mejor()` ordena por ventaja porque su trabajo es encontrar valor. Pero
cuando no se marca nada, ese resultado se lee como nuestra opinión.
Lucas lo vio: la Lectura decía *"Flamengo es favorito, le damos 66%"* y
el renglón de Resultado decía *"Mirassol gana o empata al 34%"*. Las dos
ciertas —el mercado sobrevalúa a Flamengo, así que la mayor ventaja cae
del otro lado— y juntas se leen como que la app se desdice.

Ahora: **con apuesta manda la ventaja, sin apuesta manda la
probabilidad.** El renglón contesta una pregunta por vez.

**Y el error que eso me hizo cometer, que vale más que el arreglo:**
cambié el texto a la opción más probable y dejé el precio calculado
sobre la otra. Durante veinte minutos el renglón mostró *"Flamengo gana
o empata al 87% · pagan 5.35"* — la etiqueta de una opción con la cuota
de la contraria. **Etiqueta y precio salen siempre del mismo objeto.**

### 4 · La app se justificaba cuatro veces por pantalla

Lucas: *"¿está bien que la app se justifique o se defienda todo el
tiempo? Da a entender que no sabe un carajo"*.

La misma brecha contra el mercado se decía cuatro veces en la misma
pantalla: en "lo más firme", en "lo más cerca de encenderse", en la
alerta, y otra vez en el renglón de Resultado. Cada una con su propio
descargo. Eso no se lee como rigor.

Ahora la dice **una sola**: cuando hay alerta, ella es la dueña de esa
frase y las otras se callan. El renglón conserva el borde de terracota
—el aviso visual— pero recupera su lectura y su precio.

De cinco párrafos con tres repeticiones se pasó a cuatro sin ninguna.

### 24bis · Vuelve la Copa Argentina, con la guarda que le faltaba (2026-09-02)

Salió el 2026-08-25 porque es eliminación directa: sin red de cruces no
hay fuerzas que calibrar, y sus λ salían de `promedio_condicion()` en
vez del motor. Era la única competición publicada sin pasar por
Dixon-Coles.

**Vuelve porque el motivo dejó de aplicar del todo:** `ancla_de()` ancla
a cada equipo de copa a su fuerza en SU liga local — es lo que hace
andar la Libertadores. Un equipo de Liga Profesional llega a la Copa con
sus fechas ya calibradas.

**Y vuelve con guarda, porque el motivo aplica a medias.** La Copa cruza
primera con Federal A y Primera B, divisiones que la app no sigue. Ese
equipo no tiene ancla en ningún lado y su λ vuelve a salir del promedio.

`MIN_PARTIDOS` no lo ve: el equipo **tiene** partidos jugados. Lo que no
tiene es una liga donde hayamos medido su fuerza. Son dos huecos
distintos con el mismo efecto, y solo `actualizar.py` sabe cuál es cuál
—es el único que sabe si `ancla_de()` encontró algo—, así que lo escribe
en el partido:

    "sinAncla": true    → la app no publica probabilidad, y dice por qué:
                          "uno de los dos juega en una división que no
                          seguimos, así que no tenemos medida su fuerza"

Campo **aditivo**: los partidos guardados antes de hoy no lo traen y se
comportan como siempre. Hay test de las dos mitades.

El slug es `arg.copa`, no `copa.argentina` — el segundo devuelve 400.

## 22bis · El CLV de props se medía en una escala que una sola cuota larga podía mover (2026-09-02)

Lucas pidió volver a correr `medir_props.py`. La primera lectura del
resultado parecía mala noticia: la señal de §22 caía de 2.6 a 1.5
errores estándar. No era eso. Lo que se rompió fue la escala con la que
se la mide, y encontrarlo vale más que la corrida.

### Primero, la advertencia de muestra

§22 dijo "volver a correr esto cada 10 partidos nuevos". Van **uno**:
25 → 26 partidos, 89 → 96 apuestas. Nada de lo de acá es muestra nueva,
así que ningún número de esta sección confirma ni desmiente a §22 por
haber juntado datos. Lo único nuevo es el instrumento.

### El defecto

`clv()` medía el movimiento de precio como `precio/cierre - 1`. Es la
forma intuitiva —"la cuota bajó un 10%"— y es **asimétrica**: hacia
arriba no tiene techo, hacia abajo está acotada en −100%. Con cuotas
largas adentro de la muestra eso deja de ser un detalle de presentación.

Entró **una** línea que fue de 13.00 a 3.50. Es la misma línea (el
cruce es por `cierra.get(linea)`, así que no es un error de cruce: es un
precio real que se desplomó). En esa escala vale **+271.43%**. Sola:

    §22 (25 partidos)         ahora (26 partidos)
    CLV        +3.32% ±0.86   +6.11% ±3.10
    deriva     +0.99% ±0.29   +1.40% ±0.31
    diferencia +2.33% ±0.91   +4.71% ±3.11
               (2.6 e.e.)     (1.5 e.e.)

El punto estimado casi se duplicó y el error estándar se cuadruplicó. La
significancia **bajó porque apareció un acierto grande**. Un número que
empeora cuando le va mejor no está midiendo lo que dice medir.

### El arreglo

La misma pregunta —¿la línea se movió hacia nosotros?— en diferencia de
probabilidad implícita: `1/cierre - 1/precio`, en puntos porcentuales.
Dice lo mismo con el mismo signo, es simétrica y está acotada de los dos
lados, así que ninguna cuota larga sola puede dominarla.

    mismo set de 96 apuestas        elegidas        deriva          diferencia
    cociente (viejo)                +6.11% ±3.10    +1.27% ±0.30    +4.84% ±3.11  (1.6 e.e.)
    logaritmo                       +3.88% ±1.78    −0.18% ±0.30    +4.06% ±1.81  (2.2 e.e.)
    probabilidad implícita (nuevo)  +1.13 pp ±0.37  −0.02 pp ±0.07  +1.15 pp ±0.38 (3.0 e.e.)

Dos cosas salen de ahí, y la segunda corrige a §22:

- **La señal aguanta, y mejor de lo que decía §22**: 3.0 errores
  estándar. Dejando un partido afuera por vez, el peor caso deja la
  diferencia en **+0.74 pp** — en escala simétrica ningún partido la
  carga, tampoco el del outlier. En la escala vieja ese mismo control
  daba +2.84% contra +6.11%, o sea que parecía sostenida por un partido
  cuando no lo estaba.
- **La deriva de fondo es cero, no +1%.** En logaritmo da −0.18% y en
  probabilidad implícita −0.02 pp. El positivo del cociente es
  convexidad de `x/y`, no la casa achicando el margen sobre la hora.
  Restar la deriva seguía siendo lo correcto —es la disciplina de
  comparar contra la tasa base— pero por un motivo distinto del que
  estaba escrito, y con una vara que traía adentro su propio sesgo.

### Por métrica, que §22 no desglosaba

    remates   70 apuestas · ROI −22.39% ±13.49 · CLV +1.09 pp ±0.47
    al_arco   26 apuestas · ROI  +87.50% ±67.41 · CLV +1.25 pp ±0.51

El CLV no distingue las dos métricas. El ROI sí, y remates —la métrica
que `medir_jugadores.py` ya tenía marcada como la peor calibrada, 2.09
veces el ruido— está 1.7 errores estándar en rojo. Con ±13.49 y ±67.41
no concluye ninguna de las dos, pero si el día que haya muestra la
diferencia se sostiene, el eje Jugadores no es un eje: son dos, y uno
resta.

### Qué se tocó

`clv()` y `deriva()` devuelven las dos escalas: `pp`/`ee_pp` es la buena
y manda en pantalla, `clv`/`ee` queda para poder comparar contra los
números publicados en §22. `dejar_uno_afuera()` reporta además la
diferencia contra la deriva **del resto** —antes daba el CLV crudo, que
no es el número que decide nada—. `test_medir_props.py` pasa de 40 a 50
pruebas; las 10 nuevas fijan la escala, el signo, la cota de los dos
lados y la propiedad que motivó todo: que una sola cuota larga más que
duplique el promedio en cociente y mueva menos del 20% el de
probabilidad implícita.

### Qué NO cambia

**La app no se tocó y no se toca.** `index.html` no lee este script; el
eje Jugadores sigue en NO OPINAMOS y la regla del proyecto sigue siendo
que solo `con_plata` puede llevar apuesta. Esto es CLV, no plata: el ROI
a umbral 4% es +7.37% ±21.33 y no va a decir nada hasta ~300 apuestas.
Van 96.

Y sigue en pie el reparo peor de §22: **63 de las 96 líneas están
clavadas** (66%), o sea que el número lo generan 33 apuestas. `pp` no
arregla eso — arregla que las 33 se lean en una escala que no se deja
mover por una sola.

## 26. La cuota de cierre de Pinnacle se apagó y el respaldo lo tapó (2026-09-02)

Salió contestando otra pregunta. Lucas preguntó de qué ligas tenemos
más estadísticas, y al contar de dónde sale cada cuota apareció esto:

```
liga   Pinnacle en el total        Pinnacle desde 2026-01-01
arg    5928 de 6310               0%   sobre 329 partidos
bra    5275 de 5544               0%   sobre 225
usa    5800 de 6115               0%   sobre 299
mex    4437 de 4691               0%   sobre 203
jpn    4503 de 4543               0%   sobre  20
fra    3704 de 3857               6%   sobre 162
spa    3987 de 4180               9%   sobre 209
eng    4010 de 4180              12%   sobre 194
```

**football-data dejó de llenar la cuota de cierre de Pinnacle a mitad de
la temporada 2025/26.** La columna sigue existiendo y viene vacía:

```
E0  2425:  380 de 380 filas con PSCH
E0  2526:  210 de 380
SP1 2526:  188 de 380
```

`AvgCH` y `B365CH` siguen completas, 380 de 380 en las cuatro.

### Por qué no lo vimos

`FUENTES` es una cadena de respaldo —Pinnacle, si no el promedio del
mercado, si no Bet365— y **funcionó exactamente como fue diseñada**. Ahí
está la diferencia con los dos casos que TRASPASO ya tenía anotados: el
`except` que se comió 1521 partidos era un bug, y el formato de fecha de
dos dígitos era un parser incompleto. Acá no hay error. Hay un respaldo
haciendo su trabajo, en silencio, mientras el repo entero sigue diciendo
"cuota de cierre real de Pinnacle" en los encabezados de `medir_roi.py`,
`medir_historico.py` y `medir_apertura.py`.

El total lo tapa y por eso duró meses: España tiene 3987 de 4180 con
Pinnacle real, que es el 95%. Mirando ese número no hay nada que ver.
Los partidos NUEVOS son los que cambiaron, y son el 0% al 12%.

### Qué invalida y qué no

**No invalida las mediciones grandes.** El walk-forward de `medir_roi.py`
y `medir_historico.py` está dominado por 2015-2025, donde Pinnacle está
completo. Los ROI de las seis ligas, el barrido de λ, el de umbrales de
valor y las once vías cerradas siguen en pie.

**Sí cambia dos cosas, y la segunda es la que importa.**

La primera: los números de la ventana reciente están contra una vara más
blanda de lo que decimos. El promedio del mercado cobra más margen que
Pinnacle, así que lo reciente se ve **mejor** de lo que se vería contra
el precio duro. Es el signo incómodo — el error nos favorece.

La segunda: **de acá en adelante es el 100% de los partidos nuevos.**
Esto no se estabiliza, empeora. Cada fecha que pasa, la proporción de
"medido contra Pinnacle" baja, y el día que alguien mida algo sobre los
últimos seis meses va a estar midiendo contra el promedio sin saberlo.

### Lo que se hizo

`cobertura_fuente()` en `historico.py` reparte las cuotas por casa, en
el total y en la ventana reciente por separado, y levanta alerta cuando
la reciente cae debajo de `PISO_PINNACLE` (0.50). `main()` la imprime
para cada liga. Hoy las ocho dan alerta.

Ocho tests nuevos en `test_historico.py`: que el total tape y la ventana
muestre, que el caso sano no moleste, que la ventana se pueda pedir a
mano, y que sin partidos con cuota no invente un reporte.

El umbral 0.50 no está medido: es el punto donde la frase "medido contra
Pinnacle" deja de ser cierta para la mayoría del tramo. Si alguien lo
mueve, que sea por un motivo escrito.

### Lo que queda abierto

- **Los encabezados siguen diciendo Pinnacle.** No se tocaron:
  cambiarlos pide decidir qué se quiere que digan, y decir "cierre de
  Pinnacle cuando está, promedio del mercado cuando no" es exacto pero
  invita a ignorarlo. La alerta al menos hace que se vea al correr.
- **`medir_apertura.py` mide Pinnacle y Bet365 por separado** y su
  resultado de eng (CLV −1.62% ±0.82, §20) es sobre datos con Pinnacle
  presente. Habría que confirmar que su ventana no se corrió hacia el
  tramo sin Pinnacle antes de volver a citar ese número.
- **La regla general que sale de acá**, que es lo único que vale más
  que el arreglo: *un respaldo que funciona es más difícil de ver que un
  error que falla.* Si escribís una cadena de fuentes, contá cuál está
  usando cada una — igual que se cuentan las filas que un `except`
  saltea.

## 27. La Copa volvió por un motivo que el código no hacía (2026-09-02)

Salió de una pregunta de Lucas: "¿está todo configurado correctamente?".
Auditando las constantes por liga apareció que no, y el hallazgo es de
la misma familia que los otros cinco del día: algo que *parecía* hecho.

### Lo que decía §24bis y lo que pasaba

§24bis (de esta misma jornada) trajo de vuelta `arg.copa` con este
argumento: *"vuelve porque el motivo dejó de aplicar del todo:
`ancla_de()` ancla a cada equipo de copa a su fuerza en SU liga local"*.
Y agregó una guarda, el campo `sinAncla`, para el equipo de Federal A o
Primera B que no tiene fuerza medida en ninguna parte.

Ninguna de las dos cosas ocurría. `arg.copa` no estaba en
`CON_FUERZAS`, y ese conjunto es lo único que dispara `get_fuerzas()`,
que es donde se calcula el ancla **y** donde se llena `sin_ancla`.

El daño era doble, y el segundo peor que el primero:

1. La λ de la Copa seguía saliendo de `promedio_condicion()` — que es
   exactamente el motivo por el que la competición se había sacado el
   2026-08-25.
2. **`sinAncla` no podía dar `True` nunca** en la única competición para
   la que fue escrita. Se guardaba `False` en los 59 partidos.

### Cómo se vio

Cuatro partidos compartían la misma λ, 1.35/1.10, que es el valor por
defecto cuando no hay fuerza calibrada:

```
liga      partido                        estado        publica prob.
arg.copa  Vélez Sarsfield vs Boca        SIN LECTURA   SÍ
eng.1     Manchester City vs Coventry    SIN MUESTRA   no
eng.1     Hull City vs Aston Villa       SIN MUESTRA   no
fra.1     Nice vs Le Mans                SIN MUESTRA   no
```

A los tres de liga los tapa `sinMuestra` (pj=2). Al de Copa no lo tapaba
nadie: `partidosJugados()` lee la **tabla**, una copa no tiene, y cae a
la forma general — donde Vélez y Boca tienen partidos de sobra. La otra
guarda, la escrita para este caso, estaba muerta.

### El arreglo, y por qué el comentario que lo impedía estaba viejo

`arg.copa` entra a `CON_FUERZAS`. El comentario que la excluía decía
*"eliminación directa desde el arranque — no hay red de cruces
repetidos"*, y era cierto cuando se escribió. Dejó de serlo el día que
apareció `ancla_de()`: Libertadores y Sudamericana también son
eliminación directa y están en el conjunto desde entonces, justamente
porque la fuerza no sale de la copa sino de la liga local de cada
equipo. El comentario sobrevivió a su propio dato, igual que el de `rho`
y el de la ventana de 365 días.

Verificado sin salir a la red, sobre las 4 temporadas ya cacheadas:

```
252 partidos de Copa · 109 equipos · 62 superan MIN_PARTIDOS_FUERZA (3)

Vélez  ataque 1.164  defensa 1.003  pj 13
Boca   ataque 1.239  defensa 1.122  pj 17

λ con la red + ancla:  1.752 / 1.205
λ que publicaba hoy:   1.350 / 1.100   (promedio_condicion)
```

Los equipos que no llegan a 3 partidos siguen cayendo al promedio, pero
ahora quedan marcados con `sinAncla` y la app corta ahí — que es el
comportamiento que §24bis describía.

### Lo que NO se arregló, y está dicho en el código

La Copa no tiene `escala` ni `centro`. `barrido_escala_lambda.py` se
apoya en football-data, que no publica copas, así que la corrección de
rango de goles de §14 no se puede medir ahí. Cae a `ESCALA_DEFECTO`
(1.0): no se corrige. Es la elección conservadora —usar el número de
arg.1 sería extrapolar— pero conviene no leerlo como "la copa no tiene
el defecto". No lo sabemos.

### El test que faltaba

```
set(COMPETICIONES) - CON_FUERZAS  ==  set()
```

Una línea. Habría atrapado esto el mismo día que se agregó la Copa, y
habría atrapado también el caso simétrico (ajustar fuerzas de algo que
no se publica). Si alguna competición tiene que quedar afuera, el test
se cambia a propósito y con el motivo escrito.

### La lección

**Una guarda que no puede encenderse se lee igual que una guarda que no
hizo falta.** `sinAncla` estuvo en `False` en los 59 partidos y eso se
leía como "no hay ningún caso", cuando era "nadie lo calculó".

Es la misma forma que §26: ahí un respaldo que funcionaba tapaba que la
fuente se había apagado; acá un campo en `False` tapaba que nunca se
computaba. En los dos casos no hay error, no hay excepción, y no hay
nada raro en pantalla. Cuando agregues una guarda, escribí también el
test de que puede dispararse.

## 28. Auditoría completa del proyecto (2026-09-03)

Lucas pidió una revisión de todo, no solo del funcionamiento. Se leyeron
los 227 archivos trackeados y se midió lo que se podía medir. Lo que
sigue es lo que se encontró, lo que se arregló y lo que quedó anotado.

**El patrón, que vale más que la lista:** los seis hallazgos de fondo
son todos de la misma forma. Nada falla, nada tira excepción, nada se ve
raro en pantalla. Lo que falla ruidosamente ya está arreglado; lo que
falla en silencio se venía acumulando.

### Lo que se arregló

**1 · `fechaCorta()` estaba declarada dos veces** (`index.html` 3203 y
5073), con formatos distintos —"02/09/26" y "2 de sep"— y las dos como
declaración de función, así que la segunda pisaba a la primera. Los tres
talones que pedían el compacto (CERRADO, ESCRITO, CALIBRADO) mostraban
el largo desde el 2026-09-01. La segunda pasó a `fechaEnPalabras()`.
Mismo choque que §19.6 con `.mas`.

**2 · `senalDividida()` se quedó sin llamador** en `41a6006`, el commit
que borró las siete pestañas. La función, sus exports y sus **tres
tests** sobrevivieron dando verde.

No era decorativa: des-doraba los mercados que el análisis contradice, y
`contradice()` no la reemplaza —esa mira la inclinación, que es sobre
quién gana, y no ve una tensión de goles. Sin ella la app podía marcar
"más de 2.5" en un partido cuyo propio análisis decía "trabado", y
`deMercado("goles", ...)` sí puede llegar a OPORTUNIDAD: el hueco era
real. El llamado vuelve en `otrosMercados()`, que es donde se decide
`esVal`, y se separó `filasMercado()` para romper el ciclo.

**3 · Los dos workflows escriben `data/` y sus crons coinciden** en el
minuto cero de las 12:00 y 18:00 UTC. `foto_props.yml` se defendía con
`concurrency` y `git pull --rebase`; `actualizar.yml` no tenía ninguna
de las dos, y es el que más tiene para perder: un push rebotado son seis
horas de datos. Ahora comparten el grupo `escribe-data`.

**4 · Un scoreboard caído se commiteaba igual.** `api()` devuelve `{}`
cuando fallan los dos hosts de ESPN. Para un roster suelto está bien;
para un scoreboard significa que esa competición entera desaparece de
`partidos.json` y el cron lo sube sin decir nada.
`abortar_si_falto_una_liga()` corta antes de escribir. Un partidos.json
viejo se nota porque dice cuándo se actualizó; uno incompleto no.

**5 · La primera carga bajaba 2,1 MB.** Tres cosas, medidas:

```
                              antes      después
indentación de dos JSON      +290 KB     compactos
cache-buster ?t=Date.now()   sin cache   ?v=<sello del cron>
planteles + estadisticas     bloqueaban  segunda tanda

primera carga                2183 KB  ->  722 KB
segunda visita entre corridas 2183 KB  ->  281 KB
```

El corte de la segunda tanda no es una corazonada: se renderizaron los
59 renglones de la portada con y sin esos dos archivos y el HTML sale
idéntico. `DETALLE_LISTO` cubre la ventana de ~2 segundos.

**6 · `verificar_app.js` decía "sin problemas duros"** sobre los dos
bugs de arriba. Tres puntos ciegos: exentaba a toda función mencionada
en cualquier suite (así se escondió `senalDividida`), no miraba
declaraciones repetidas, y volcaba 80 clases de CSS en una lista sin
orden donde las que pesan quedaban invisibles. Corregido y **verificado
corriendo la versión nueva contra el `index.html` anterior**: aparecen
los dos.

### Lo que se midió y quedó anotado sin tocar

- **36 clases de CSS sin emisor**, 62 reglas, 5.663 bytes (5,9% del
  CSS). Restos de las siete pestañas: el rediseño renombró con sufijo
  (`paso2`, `h2hc`, `h2hr`, `cbar`) y las viejas quedaron. No se
  borraron porque la vara automática no puede confirmarlas sin riesgo de
  llevarse una viva —se probó y reportaba `.alto` como muerta— y
  borrarlas de a una pide verificar cada una. La lista ordenada por peso
  sale de `verificar_app.js`.
- **Seis campos que el motor escribe y la app nunca lee** (17,7 KB):
  `ciudad`, `estadio`, `compLogo`, `cornersH`, `preload` (siempre `{}`)
  y `note`, que es una explicación en prosa de cómo se calculó λ,
  generada en cada corrida y nunca mostrada.
- **`lectura().corto`** se calcula en las cuatro ramas y no se
  renderiza; sus tres reglas de CSS apuntan a un elemento que ya no
  existe.
- **`eval_fecha.js`** revienta con `ERR_INVALID_ARG_TYPE` si se corre
  sin argumentos, en vez de imprimir su uso. Junto con `barrer_valor.js`
  y `verificar_app.js`, no figura en la tabla de CLAUDE.md.
- **El cron de `foto_props` cubre 07:00–20:00 ARG, no 07:00–21:00**:
  `0 10-23` en UTC−3 termina a las 20:00, y el comentario dice "hasta
  las 00:00 UTC", que `10-23` no incluye.
- **§22 se apoya en que `foto_props.py` mejora la resolución del CLV
  desde el 31/08.** Se miraron las 28 corridas: todas exitosas, 26
  encontraron cero partidos y las otras tres fotografiaron el mismo
  partido. No está roto —es el parate de selecciones— pero el
  instrumento lleva fotografiado uno.
- **`calibracion_lineas.json` y `calibracion_jugadores.json` son del
  2026-08-24.** La app los usa para decirle al usuario de qué fiarse.
- **`conf` 80 en fra.1 contra 70 en esp.1** con ROI indistinguible
  (−5.22% ±8.71 contra −5.33% ±8.52). Francia lo tiene desde antes de
  que §24 escribiera el criterio.

### Lo que está bien, y conviene que quede escrito

`doble_via.py` da 6,66e-16: el port a JavaScript no derivó. CI corre por
glob y no por lista, porque una lista a mano ya dejó dos suites afuera.
No hay un secreto en el repo. El parser de football-data descarta 1 fila
de 39.421. La accesibilidad tiene las bases: `lang`, viewport, 38
`<button>` reales y cero `<div onclick>`, `:focus-visible` global,
`prefers-reduced-motion` respetado, `alt=""` correcto en los escudos.

Y la densidad de comentarios que explican **por qué** y no **qué** es lo
que hizo posible esta auditoría: casi todos los hallazgos salieron de
leer un comentario que ya no coincidía con su código.

### La regla que sale de todo esto

Tres veces en dos días apareció la misma forma —§26 (un respaldo que
funcionaba tapaba que la fuente se apagó), §27 (`sinAncla` no podía dar
`True`), y hoy `senalDividida` con tests en verde— más una cuarta: la
herramienta que debía detectarlas tenía el mismo defecto.

**Cuando agregues una guarda, escribí el test de que puede dispararse.**
Y cuando escribas una cadena de respaldos, contá cuál se está usando.
Un camino de error que nunca se ejercita no es una red: es una decoración.

## 29. La banda de cuota 4 a 10: la hipótesis se investigó y dio que no (2026-09-03)

Lucas hizo la mejor pregunta del proyecto:

> "Si determinadas situaciones se dan en el fútbol, entonces pueden
> existir condiciones o contextos que aumenten considerablemente su
> probabilidad en partidos específicos. No hablo de cuotas de 30 o 60.
> Hablo de cuotas de 5, 8 o 10."

Y puso la condición correcta: *"no quiero que forcemos los datos para
confirmar mi hipótesis"*, recordando que "en un momento le dábamos mucho
papel a las lesiones o a los viajes, que nos distorsionaban los
partidos".

`medir_bandas.py` la contesta sobre **23.870 partidos** de cinco ligas,
walk-forward. La respuesta es no.

### El indicio que la motivó era malo, y lo puse yo

La hipótesis salió de `medir_calibracion.py`: banda 10-20%, decimos
16.4% y pasa 24.6%, con IC 95% [+4.7, +13.8]. O sea "subestimamos lo
improbable", y la banda 10-20% es la cuota 5 a 10.

Eran **85 partidos, sobre 12 mercados del mismo partido que están
correlacionados entre sí**, con el modelo anterior a la corrección de
escala. Sobre 23.870 partidos y solo 1X2, el efecto no existe — y va al
revés.

### El resultado

```
TEST     cuota      n  decimos  mercado     pasó  nos-merc  real-merc
         4.0-6   5377    23.2%    20.3%    20.0%     +2.9      -0.2
        6.0-10   2006    17.0%    12.8%    12.0%     +4.2      -0.8
           10+    572    10.5%     6.7%     6.5%     +3.8      -0.3
```

`real − mercado` es negativo en las tres bandas largas: el mercado paga
apenas de MENOS, no de más. El sesgo favorito-perdedor existe, es chico
y corre **en contra** de la hipótesis.

Contra plata, en test, apostar solo donde le ganamos al mercado da
**−7.38% ±2.82** — más de dos errores estándar negativo. No es "no hay
ventaja": es que **cuando discrepamos ahí, discrepamos para el lado
equivocado**.

Por liga: eng −2.33%, fra −5.28%, arg −8.44%, bra −10.26%, spa −10.99%.
Somos menos malos donde el mercado es más eficiente, que es lo contrario
de la intuición de "en Sudamérica miran menos, ahí está la grieta". Es
cierto sobre la casa y cierto sobre nosotros, y perdemos más de lo que
ellos aflojan.

### El bolsillo que murió, y por qué estaba la guarda

El local perdedor a 4-10 era el único subconjunto cerca de cero (ROI
−1.91%, pasa 18.7% contra 18.1% del mercado). Mirado en serio:

```
   train   1001   ROI +5.52% ±6.95
    test    807   ROI -7.85% ±7.14
   por liga:  eng +7.32%  ·  arg -5.61%  ·  bra -10.03%  ·  spa -2.12%
```

Cambio de signo, los dos dentro del ruido, sin consistencia entre ligas.
Sin el corte train/test se reportaba como hallazgo — que es exactamente
el error que Lucas pidió no cometer, y el motivo de que la guarda
estuviera puesta **antes** de mirar.

### Lo que se aprendió del modelo, que es lo que queda

Se probaron dos correcciones y ninguna sobrevive:

- **Potencia global `p^k`.** Óptimo en train `k = 0.90` —aplanar, no
  afilar— y en test no mejora nada. Con `k = 1.3` las colas se arreglan
  (favoritos de −6.6 a +1.3, largas de +5.0 a +1.2) y se rompe la banda
  3.0-4, que tiene 10.653 selecciones.
- **Recalibración isotónica contra nuestra propia p.** Mejora el Brier
  de test en **0.00006**.

La segunda explica por qué: **agrupado por nuestra propia p, el modelo
está bien calibrado.** Decimos 22% y pasa 24%; decimos 75% y pasa 71%.

Las dos cosas son ciertas a la vez:

    agrupado por nuestra p     calibrado
    agrupado por la cuota      +3 a +5 en las largas

Eso solo puede pasar si nuestro error está **correlacionado con el
precio**: cuando el mercado pone a alguien a 6.00 y nosotros le damos
17%, el mercado sabe algo que nosotros no. **No estamos descalibrados,
estamos menos informados** — y eso no se arregla reformando nuestros
propios números. Las dos salidas son conseguir el dato, o encogerse
hacia el mercado, que `medir_encogimiento.py` ya midió que mejora el
Brier sin dar plata.

Es la razón más clara que encontró el proyecto de por qué el 1X2 está
cerrado, y es distinta de la que se creía.

### Lo accionable

La regla de valor pierde en TODAS las bandas y la pérdida crece
monótona con la cuota, en train y en test:

```
   1.0-2.0   -4.77%      3.0-3.5   -1.76%
   2.0-2.5   -2.30%      3.5-4.0   -9.40%
   2.5-3.0   -7.83%      4.0-4.5  -16.59% ±6.34
```

`MAX_ODDS = 4.5` admite el tramo donde pierde tres veces más. Recortarlo
no la vuelve positiva —`barrido_valor.py` se volvió a correr y sigue
dando 39 ventanas, ninguna positiva en train Y test— pero deja de firmar
las peores. **No se tocó**: es una decisión de producto y hoy la app no
marca nada de todos modos.

Y la hipótesis con la que se abrió esto —que las ventajas falsas de la
banda larga explicaran el resultado de `barrido_valor.py`— **no se
confirma**: la banda larga es la peor, pero todas son negativas, así que
sacarla no habría hecho positiva ninguna ventana.

### El rho del arnés, que es un hallazgo aparte

`medir_historico.evaluar()` mide con `rho = 0.05` fijo y **ninguna liga
usa ese valor** (arg −0.05, bra 0.00, eng −0.02, fra −0.05, esp 0.00).
Afecta a `medir_roi.py` y `medir_apertura.py`, que son los que deciden
qué liga entra a la app. Sobre la regla de valor:

```
   rho 0.05 (arnés)     6050 marcas   -6.29% ±1.74
   rho de producción    5386 marcas   -4.78% ±1.88
```

Ninguna conclusión se da vuelta —la diferencia es menor que el error
estándar y los dos son claramente negativos— pero el arnés genera 12%
más marcas de las que produciría producción y sobreestima la pérdida en
1,5 puntos. **No se arregló acá**: tocarlo invalida la comparación con
todos los números ya publicados en TRASPASO, y eso pide su propia
sesión.

### Lo que este resultado NO cierra

Mide **1X2 a cuota de cierre**, el mercado más trabajado que existe. No
dice nada de props —donde el proyecto sí tiene señal medida (§22bis)—,
ni de las combinadas armadas y su correlación, ni del en vivo, ni de
contextos que football-data no trae. Que no haya ventaja en el precio no
es lo mismo que que no haya nada que saber.

## 30. El meta-modelo: sabemos cuánto NO sabemos, pero no cuándo erramos (2026-09-03)

§29 dejó un hallazgo con signo: sobre 11.570 partidos, cuando le damos
más probabilidad que la apertura, la línea se mueve hacia abajo
(−0.108 ±0.034); cuando le damos menos, sube (+0.099 ±0.023). Monótono
en cinco tramos.

Algo con signo predecible se puede evitar. La pregunta de `medir_metamodelo.py`
no es "¿qué va a pasar?" sino **"¿cuánto hay que creerle a nuestro
número acá?"** — que es lo que separa a un experto de una calculadora.

Lucas puso el encuadre: investigador, no vendedor. Walk-forward, sin
leakage, buscando refutar. Y agregó la restricción que decide todo:
*"no quiero convertirnos en un modelo que simplemente copie al mercado"*.

### La guarda que hizo falta poner en el código

Las variables se partieron en dos grupos **antes** de mirar resultados:

    PROPIAS   descanso, asimetría de descanso, congestión, historia del
              modelo, momento de la temporada, λ total, volatilidad
    MERCADO   cuánto discrepamos del cierre

Más una **placebo**: ruido puro, en la misma tabla. Cualquier efecto que
no supere al placebo es el efecto de no haber medido nada.

### El resultado: la hipótesis murió

```
            variable        train      test    Q5-Q1 (test)
          congestion      -0.0016   +0.0018       +0.0001
        descanso_dif      -0.0021   +0.0027       +0.0005
        descanso_min      -0.0021   +0.0074       +0.0030
             jornada      -0.0244   -0.0013       -0.0031
        lambda_total      -0.0008   +0.0153       +0.0040
           n_previos      -0.0224   -0.0155       -0.0036
         volatilidad      -0.0103   -0.0137       -0.0010
-->        PLACEBO        -0.0070   -0.0033       -0.0025
        discrepancia $    +0.1777   +0.1319       +0.0412
```

**Todas las propias están en el orden de magnitud del placebo**, y la
mayoría cambia de signo entre train y test. El calendario —descanso,
congestión, partido a mitad de semana— no predice nada. Es la misma
familia de variables que en su momento "distorsionaban los partidos", y
ahora está medido que no.

Se probaron las dos formas de que la medición estuviera equivocada:

- **Contra el error ABSOLUTO**, por si el calendario nos afectara a
  nosotros y al mercado por igual y la resta lo borrara. No aparece.
- **Por liga**, por si existiera solo donde el mercado es más blando. El
  placebo solo, entre ligas, va de −0.0348 a +0.0196, y ninguna variable
  real sale de esa envolvente en varias a la vez.

### Lo único que predice nuestro error, y por qué no sirve

`discrepancia` da +0.1319 en test, monótona en los cinco quintiles
(+0.0008 → +0.0420), diez veces el placebo. Es de mercado, y lo único
accionable que se deduce es "discrepá menos" — copiar.

Pero dice algo más fuerte de lo que parece, y conviene leerlo entero:
**si nuestras discrepancias fueran a veces buenas, discrepar mucho daría
a veces ganancia grande.** Que prediga pérdida de forma monótona en toda
la escala significa que nuestro desacuerdo con el mercado **no tiene
contenido informativo a ninguna magnitud**. Es más duro que §29 y lo
explica.

### Lo que SÍ salió, y es una pieza de producto

Contra el error **absoluto**, dos variables propias son grandes y
estables en train y en test:

```
    volatilidad    -0.2371 / -0.2454      (qué tan desparejo es el cruce)
    lambda_total   -0.1312 / -0.1479      (goles esperados)
```

Eso no es ventaja: un cruce que damos 70-10 es más fácil **para todos**,
y por eso se borra al restarle el mercado. Pero es una medida honesta de
la **incertidumbre intrínseca del partido**, y la app hoy no la tiene:
publica el 45% de un partido parejo con la misma cara que el 78% de uno
desparejo.

La distinción, que es la que pidió Lucas:

    error ABSOLUTO   predecible      -> sirve para decir cuánto confiar
    error RELATIVO   no predecible   -> no hay ventaja que rescatar

### Dónde queda el proyecto

Camino cerrado número trece. Y con §29 forman un par que vale como
diagnóstico único: en el 1X2 no solo no tenemos ventaja — nuestro
desacuerdo con el mercado apunta sistemáticamente al lado equivocado, y
no hay variable observable que nos avise cuándo.

Eso descarta también el simulador **como modelo de 1X2**: sería una
estructura más rica sobre una λ que apunta mal, y produciría más
mercados equivocados, ahora correlacionados entre sí.

Lo que sigue vivo, y es donde apunta el proyecto:

- **El simulador para props y combinadas**, que se apoyaría en la serie
  por jugador —el único insumo con señal medida (§22bis)— y no en λ.
- **La arquitectura de escenarios**: dejar de precificar mercados
  aislados y modelar el partido como una trayectoria, que es lo único
  que permite ponerle precio propio a una combinada armada.

## 31. Paso 0 del simulador: el margen deja ocho veces menos espacio del que hace falta (2026-09-03)

Antes de construir el simulador de combinadas, Lucas pidió medir si el
margen deja lugar. Fue la decisión correcta: no hay que construirlo.

### Las precondiciones, y dos de tres fallan

Antes del margen se midieron las tres cosas que el simulador asume:

**Dinámica de estado — no existe.** El único dato temporal intra-partido
que tenemos es el marcador al descanso (`HTHG`/`HTAG`, que `historico.py`
ni siquiera parsea). Sobre 12.216 partidos:

```
    al descanso      n  local 2T  visita 2T  total 2T
       local +1   2912     0.854      0.657     1.511
         empate   5044     0.821      0.661     1.482
      visita +1   2266     0.832      0.693     1.526
```

La narrativa "el que gana se echa atrás y el que pierde empuja" **no
está**: el local que gana 1-0 marca MÁS en el segundo tiempo (0.854
contra 0.821) y el que pierde no empuja. Un simulador minuto a minuto
tendría que inventar esa dinámica, que es lo que Lucas pidió no hacer.

**Correlación entre mercados — 5%.** El que gana saca 5.01 córners, el
que pierde 4.77.

**Condicionar props por el equipo — ya medido y hace daño**
(`medir_ajuste_jugador.py`: −0.13 y −0.48).

### El margen, que es lo que cierra el tema

La escalera de jugador es de un solo lado, así que el margen se mide
comparando la implícita del precio contra la frecuencia real.

Primero hubo que arreglar el pool: **el 30% de los jugadores que Bet365
cotiza no terminan siendo titulares** (729 titulares contra 310 no, sobre
1039 cotizados). Apostar la escalera entera pierde 53%, y buena parte de
eso es apostarle a gente que no juega. Solo titulares:

```
  metrica  linea     n   precio  implicita    real   sobreprecio
  al_arco    0.5   361     3.11      40.8%   27.1%     +13.6 pp
  remates    0.5   347     1.51      71.9%   60.2%     +11.7 pp
  remates    1.5   361     3.36      45.7%   33.2%     +12.4 pp
  remates    2.5   347     7.73      28.3%   16.7%     +11.6 pp

  sobreprecio medio: +9.0 pp
  nuestra ventaja medida (§22bis): +1.15 pp de CLV
```

**La casa cobra ocho veces lo que ganamos.** Y una combinada multiplica
el margen: se verificó sobre boletas reales que la cuota combinada es el
producto exacto de las patas (9.01 = 1.75×1.62×1.70×1.87), o sea que no
hay descuento por juntar.

### El reparo que podría salvarlo, y por qué no se puede resolver

El "real" sale de los remates que cuenta ESPN. Si ESPN cuenta menos que
la fuente con la que Bet365 liquida —Opta cuenta los bloqueados, por
ejemplo— parte del sobreprecio es error de medición. Que el 0.5 de
remates de un titular dé 60% y no ~72% empuja en esa dirección.

No se puede separar sin datos de liquidación. La conclusión honesta es
doble y las dos llevan al mismo lado: **el margen parece diez veces
nuestra ventaja, y además no podemos medir nuestra ventaja real en este
mercado con los datos que tenemos.**

**El CLV de §22bis no depende de esto** —compara precio contra cierre y
no mira resultados— así que sigue en pie. Lo que queda en duda son los
ROI de `medir_props.py`.

### La conclusión estructural de todo el bloque §29-§31

Las dos condiciones nunca coinciden:

```
   mercado              margen        nuestra ventaja
   1X2 (Pinnacle)        3.1%         negativa (§29, §30)
   props de jugador     ~9 pp         +1.15 pp de CLV
   combinadas armadas   multiplicado  sin medir, y sin espacio
```

**Donde el margen es bajo somos malos; donde podríamos ser buenos el
margen es enorme.** Eso no es mala suerte: es lo que uno espera de un
mercado eficiente, y explica los trece caminos cerrados mejor que
cualquier explicación por camino.

El simulador queda cerrado como camino catorce **antes de escribirlo**,
que es exactamente para lo que servía el paso 0.

## 32. Auditoría de §31, y la corrección al CLV de §22bis (2026-09-03)

Lucas frenó §31 antes de que cerrara el simulador, con tres objeciones.
Dos resultaron correctas y una no. Esta sección las audita y corrige lo
que hay que corregir, incluida una relectura del hallazgo más importante
que tenía el proyecto.

### Las tres distinciones que faltaban, y que valen para todo el TRASPASO

Lucas señaló un vicio real en cómo veníamos cerrando caminos: se pasa
demasiado rápido de "esta implementación no funcionó" a "este concepto
está cerrado". De acá en adelante se distinguen tres cosas:

    hipótesis concreta refutada      →  cerrar
    implementación concreta que falló →  cerrar ESA implementación
    idea general poco investigada     →  no cerrar

§31 escribió "no existe espacio matemático ni práctico para combinadas".
Eso era del tercer tipo escrito como si fuera del primero.

### Objeción 1 — ¿el sobreprecio es margen o es nuestra fuente de datos?

**Descartada, y se puede medir.** Si ESPN contara menos remates que la
fuente con la que Bet365 liquida, parte del +9.8 pp sería medición:

```
   remates por equipo por partido
   eng   ESPN 13.70   football-data 13.04    105%
   fra   ESPN 13.94   football-data 12.49    112%
```

ESPN cuenta **más**, no menos. Y 13.70 repartidos entre once titulares
dan 1.25 por jugador, que es exactamente el promedio que mide
`medir_margen_props.py`. El dato es internamente coherente y la
hipótesis del proveedor no explica el sobreprecio.

### Objeción 2 — ¿2596 escalones o 26 partidos?

**Correcta como reflejo, no como hecho.** Los escalones de un mismo
partido no son independientes. Remuestreando por PARTIDO:

```
   sobreprecio observado   +9.8 pp
   IC 95% por partido      [+7.3, +12.0] pp
   e.e. por partido        1.2 pp   (el ingenuo daba 0.8)
```

El intervalo no toca el cero. El sobreprecio sobrevive.

### Objeción 3 — ¿el CLV es comparable con el sobreprecio?

**Correcta, y es la más importante de las tres.** §31 escribió que
"nuestra ventaja es un octavo del margen". Es un error conceptual: son
magnitudes distintas y no compiten, **se suman**.

```
   sobreprecio =  implícita(nuestro precio) − verdad
   CLV         =  implícita(cierre) − implícita(nuestro precio)

   → el cierre está  9.8 − 1.15 = +8.65 pp por encima de la verdad
```

**LO QUE ESTO CORRIGE DE §22bis**

§22bis presentó el CLV de props (+1.15 pp sobre la deriva, 3.0 e.e.)
como "el primer lead que sobrevive a sus controles". Sigue siendo un
hecho medido y los controles siguen valiendo. Lo que cambia es qué
prueba:

- **Prueba** que elegimos líneas que el mercado después mueve hacia
  nosotros: conseguimos mejor precio que el precio posterior.
- **NO prueba** que apostemos por encima de la probabilidad real.
- Su valor como evidencia **depende del margen del mercado**. En uno
  barato, ganarle al cierre por 1.15 pp es plata. En uno donde el cierre
  ya está 8.65 pp arriba de la verdad, no alcanza.

Esta corrección importa más allá de props, porque cambia cómo hay que
leer cualquier señal futura de CLV: **el CLV es condición necesaria, no
suficiente**, y su suficiencia se evalúa contra el margen del mercado
donde se midió.

### Lo que sí quedó medido: el margen por mercado

Sobre precios reales de Bet365, de los dos lados donde los publica:

```
   goles                 4.39%  /  5.10%
   1X2                   5.90%  /  6.56%
   córners               7.4%   –  9.1%
   ambos marcan          8.10%
   props de jugador      ~33% relativo (+9.8 pp sobre base ~30%)
```

**Los props son 5 a 7 veces más caros que los mercados de equipo en la
misma casa.** Bet365 no publica el "under" de la escalera de jugador —
verificado en el bloque crudo—, que es coherente con un mercado que no
pretende ser competitivo.

Umbral mínimo para que una combinada tenga esperanza positiva:

```
   dos patas de goles (5% c/u)   →  estimar ~10% mejor que la casa
   dos patas de props (33% c/u)  →  estimar ~77% mejor
```

### Las conclusiones, con el alcance que corresponde

**Props de jugador.** Lo que se cierra es esto y solo esto:

> Con los proveedores, precios y datos actuales, no hay evidencia
> suficiente de que la señal de CLV en props supere el costo estructural
> del mercado.

Eso NO dice que ningún análisis de props pueda tener ventaja. Dice que
el nuestro, contra estos precios, no está demostrado.

**Combinadas de mercados de equipo.** No se cierran, y §31 se equivocó
al hacerlo. El margen de dos patas baratas ronda el 10%: difícil, no
absurdo. Lo que bloquea hoy no es el peaje sino nuestra capacidad
predictiva, que en 1X2 medimos negativa (§29, §30). **Son dos
diagnósticos distintos y llevan a trabajos distintos.**

La pregunta queda abierta y formulada:

> ¿Podemos desarrollar una lectura que encuentre ventaja suficiente en
> mercados de equipo baratos Y estime bien las correlaciones entre ellos?

Hoy la respuesta no es sí. Tampoco es un no demostrado.

**El simulador.** No se construye: no hay evidencia que lo justifique.
No se cierra: la razón por la que no se justifica es nuestra ventaja en
los insumos, no la idea de modelar el partido como un todo.

## 33. La lectura acertaba repitiendo al modelo (2026-09-03)

Se auditaron los 28 análisis cargados buscando qué contienen de
verificable. Lucas pidió que no se forzaran categorías: solo mirar qué
hay.

### De qué hablan realmente

```
      bajas/suspensiones   28/28    ya medido: r = -0.06 ± 0.14, sin señal
             forma/racha   19/28    ES el insumo de fuerzas_equipos()
       descanso/desgaste   16/28    ya medido: al nivel del placebo (§30)
         tipo de partido   11/28    no medido
         jugador puntual   11/28    no medido
```

**Los tres temas dominantes están medidos como no predictivos o ya viven
dentro del modelo.** El análisis dedica su volumen a lo que el motor ya
sabe. Tres veredictos lo dicen con todas las letras: *"eso ya lo ve el
modelo en la forma de cada uno"*.

### Las señales estructuradas aciertan, y no aportan

De los 9 análisis con `senal`, 7 resueltos:

```
   ritmo=alto  n=1  ->  5.00 goles      (base 1.86)
   ritmo=bajo  n=2  ->  0.50 goles
   ambos=probable      n=1  -> 100% BTTS  (base 29%)
   ambos=poco_probable n=3  ->   0% BTTS
```

Cuatro de cuatro. Con n=7 eso no prueba capacidad predictiva — prueba
que el instrumento **puede existir**: las afirmaciones son concretas,
resolubles, y se resolvieron.

Pero al cruzarlas contra λ:

```
                 senal   λ total  goles
    bajo/poco_probable      1.67      1
    bajo/poco_probable      1.88      0
```

**Los dos partidos que la lectura llamó "de pocos goles" son exactamente
los dos de λ más bajo del conjunto.** La lectura acertaba diciendo en
palabras lo que λ ya decía en números.

El diagnóstico no es que la lectura sea mala. Es que está construida con
los mismos hechos que λ —goles recientes, forma, sede— así que
reproduce λ. `expediente.py` esconde λ de la skill, y eso no alcanza:
la contaminación no es de datos, es de pregunta.

### Qué es ortogonal a λ, medido

Sobre 12.095 partidos con λ y estadísticas:

```
   diferencia de remates   +0.459   λ YA LO SABE
   diferencia de al arco   +0.462   λ YA LO SABE
   diferencia de córners   +0.345   λ YA LO SABE

   TOTAL de córners        +0.077   ortogonal
   TOTAL de tarjetas       -0.110   ortogonal
   TOTAL de faltas         -0.199   parcial
   TOTAL de remates        +0.177   parcial
```

**λ encoda la asimetría del partido, no su volumen.**

Eso corrige la propuesta que se había hecho veinte minutos antes en esta
misma sesión: se iban a pedir señales de "dominio" y "quién genera más
llegadas", y las dos son diferencias que λ ya sabe con r ≈ 0.46. La
medición cambió el diseño.

### El esquema nuevo

`senal` pasa de tres campos sobre goles a cuatro sobre volumen y
jugadores:

| campo | se verifica contra |
|---|---|
| `corners_total` | córners del partido vs. media de liga |
| `fisico` | faltas + tarjetas vs. media de liga |
| `volumen_remates` | remates del partido vs. media de liga |
| `generador` | ¿ese jugador lideró los remates de su equipo? |

`generador` es ortogonal **por construcción**: λ es un número por equipo
y no tiene eje de jugador. Ningún ajuste del modelo puede replicarlo.

**`null` es respuesta válida y preferida.** No hay que llenar los cuatro
campos: cincuenta afirmaciones verificables valen más que quinientas
inventadas, y el instrumento se rompe si se completa por obligación. Por
eso tampoco hay valor "normal" — sería una afirmación disfrazada de
neutralidad.

Lo que queda prohibido: afirmar quién gana, cuántos goles o quién
domina. Las tres están adentro de λ.

### Las tres capas, separadas

`medir_senal.py` mide las tres por separado, porque son preguntas
distintas y una puede dar que sí y las otras que no:

    1. LECTURA            ¿hace afirmaciones concretas?
    2. VERIFICACIÓN       ¿se puede comprobar si ocurrió?
    3. VALOR INCREMENTAL  ¿aporta sobre lo que el modelo ya predice?

La tercera compara contra **el pronóstico numérico de esa misma
métrica** —`estadisticas.json` tiene el promedio de córners por equipo—
y no contra λ. Comparar contra λ sería tramposo: λ no predice córners y
cualquier cosa le ganaría.

### Por qué esto va primero

Hoy `medir_senal.py` no reporta nada: cero análisis tienen el esquema
nuevo. Ese es exactamente el punto.

De los tres caminos abiertos —estructura conjunta entre mercados,
movimiento de línea, y lectura verificable— los dos primeros usan datos
históricos que ya están en disco y pueden esperar seis meses. **Este
solo acumula si se enciende.** Con 29 análisis y dos por semana, empezar
hoy son ~80 en seis meses; no empezar son 29 y la misma frase de
siempre.

Lo que este instrumento va a poder contestar, y ningún otro: **qué tipos
de lectura futbolística aporta VALOR que los modelos numéricos no
capturan.**

## 33bis. El primer test del esquema, y los cuatro arreglos que produjo (2026-09-03)

Se corrió la skill con el esquema nuevo sobre **Ipswich–Liverpool**, y a
propósito como validación del instrumento, no del partido. Salió lo que
tenía que salir: tres de cuatro dimensiones en `null`, y cuatro defectos
de diseño encontrados antes de generar veinte análisis con ellos.

### Lo que pasó

`pjMax = 2`: la temporada europea lleva dos fechas. Con dos partidos por
equipo, ninguna señal de volumen tiene base. La única que produjo algo
fue `generador` — Enciso con 6 remates contra 3 del siguiente de Ipswich.

### Defecto 1 — el esquema no protegía contra los proxies de λ

El impulso al escribirlo fue poner `corners_total: "muchos"` porque
Liverpool ataca mucho, y `volumen_remates: "alto"` porque los cuatro
partidos previos habían tenido muchos goles. **Las dos son inferencias
desde la asimetría o desde los goles, que es exactamente lo que λ ya
sabe** (r = 0.35 a 0.46). Decir "no uses λ" no alcanza: λ tiene proxies
y se cuelan sin sentirse una violación.

La regla que entra, en una línea:

> **La evidencia para afirmar una dimensión tiene que ser una medición
> de esa misma métrica.**

Para decir "muchos córners" hace falta dato de córners. Y cada dimensión
tiene ahora su tabla de evidencia admisible y prohibida en la skill. La
prohibición más importante es la de `volumen_remates`: **goles y
resultados**, que es el insumo directo de λ.

### Defecto 2 — `fisico` juntaba dos cosas distintas

Un partido puede tener 25 faltas y 2 amarillas, o 15 faltas y 5. Con un
solo campo no se sabía cuál se estaba afirmando ni qué hacer al
verificar si una subía y la otra bajaba. Se parte en `faltas` y
`tarjetas`, que además se verifican por separado con datos que ya
guardamos.

### Defecto 3 — `generador` no tenía umbral

Sin umbral, la próxima corrida nombra al que tiene 7 remates sobre uno
de 6 y lo llama hallazgo. En Liverpool había cuatro jugadores entre 6 y
7: ahí la respuesta es `null`, porque elegir es tirar una moneda con
cara de análisis.

Entra el umbral: se nombra solo si lidera por **al menos 50% sobre el
segundo de su equipo**. Es experimental, salió de mirar un partido, y se
valida cuando haya muestra.

### Defecto 4 — el calendario, que no es del esquema pero manda

El instrumento va a producir casi puros `null` en Europa hasta octubre.
Argentina va por la fecha 7 y Brasil por la 24: **ahí sí hay muestra**.
La primera tanda va sobre esas dos.

Y se conservan algunos partidos europeos de muestra corta **como
control**: si el instrumento fabrica señales cuando la información no
alcanza, se tiene que ver ahí. `null` en Europa es el resultado
esperado, no una falla.

### Qué contesta la primera tanda, y qué no

No contesta si la lectura mejora el pronóstico — para eso falta muestra
y faltan las capas 2 y 3. Contesta una pregunta anterior y necesaria:

> **Cuando tiene información suficiente, ¿la skill produce señales
> nuevas, concretas, verificables y distintas de lo que λ ya sabe?**

Si la respuesta es que sí, recién ahí se mide acierto. Y después, valor
incremental.

## 34. El smoke test, y el umbral que salió de calibrar contra historial (2026-09-03)

Se corrieron cuatro partidos con el esquema de §33 —tres de arg/bra y
Arsenal–Chelsea como control de muestra corta— con el objetivo explícito
de **auditar el instrumento, no de generar muestra**. Encontró cinco
defectos, cuatro de ellos estructurales, y ninguno se habría visto
generando quince análisis de una.

### Defecto 0 — el expediente no traía la evidencia que el esquema exige

Anterior a la tanda y el más grave. La regla de §33bis dice que para
afirmar una dimensión hace falta una medición de esa misma métrica.
`expediente.py` no traía **ninguna**: sus `corners`/`fouls`/`cards` son
la expectativa del MODELO (`esperados()` de `actualizar.py`) o una
constante de liga.

Con eso, las cuatro dimensiones de volumen solo podían salir de
evidencia prohibida, o irse a `null` por falta de input — y un `null`
así no dice nada sobre el fútbol. Peor: ese esperado es el baseline
contra el que `medir_senal.py` mide el aporte en la capa 3, así que
dejarlo adentro hacía que el instrumento comparara al modelo consigo
mismo. `expediente_estadisticas.py` ya los excluía por este motivo con
el mismo argumento escrito: los dos expedientes se contradecían.

Salieron. Entró `metricasH`/`metricasA` desde `estadisticas.json`, con
`produce`, `concede`, split por sede, `n` y `desvio`.

### La tanda

```
  Rosario Central–Newell's   n=6   generador (Di María +100%)
  Central Córdoba–Indep.     n=6   todo null
  Fluminense–Vasco           n=4   faltas "muchas" + generador (Hulk)
  Arsenal–Chelsea            n=2   todo null      <- control
```

**El control funcionó.** Con n=2, la suma cruda de faltas daba 14.5
contra una vara de 22.6 (−19%): una señal "pocas" gritada. Cruzada
contra lo que cada equipo concede daba 22.0, o sea nada. Un instrumento
menos cuidadoso la afirmaba.

### Defecto 1 — las cuatro dimensiones de volumen no tenían umbral

`generador` tenía uno explícito (50%). Las otras cuatro, ninguno. Y eso
se rompió solo dentro de la misma tanda:

```
  córners de Rosario Central   +16% sobre la vara,  ee 2.0  ->  null
  faltas de Fluminense         +11% sobre la vara,  ee 3.0  ->  "muchas"
```

Se le aplicó la vara más dura a la señal más significativa. Sin umbral
el corte lo pone el criterio del momento y no es reproducible.

### Cómo se eligió el umbral, que es la parte que importa

Lucas puso la condición: **no elegirlo mirando estos cuatro partidos.**
Un umbral ajustado sobre la muestra que después se evalúa no es un
umbral, es una descripción del pasado. Por eso entra
`calibrar_senal.py`: **20.897 partidos de seis ligas europeas (2015/16 a
2025/26), walk-forward, con train/test temporal.** Los partidos de la
tanda son de septiembre de 2026 y no entran en el corpus.

La pregunta operativa: con los promedios que la app tiene ANTES del
partido, ¿desde qué distancia de la media de liga acertamos el lado más
seguido que tirando una moneda? Resultado en test:

```
  dimensión         gap   dispersión   n     test    tasa base   margen
  faltas            10%       15%      6    71.2%      54.1%     10.9 ee
  volumen_remates   10%       15%      6    63.6%      51.2%      6.2 ee
  corners_total     20%       20%      6    65.7%      52.0%      3.0 ee
  tarjetas           —         —       —      no supera su tasa base
```

**`tarjetas` no se afirma nunca.** En la grilla entera de umbrales nunca
le sacó más de 1.8 errores estándar a su propia tasa base. El recuento
de tarjetas varía tanto de partido a partido, contra lo poco que separa
a un equipo de otro, que el promedio previo no dice de qué lado va a
caer. El campo sigue existiendo y su único valor válido es `null`.

Y aparece la mitad de la regla que no existía: **el tope de dispersión**.
Los tres estimadores (`produce`, `sede`, `cruzado`) son tres formas de
mirar el mismo total, y cuando se contradicen esa contradicción ES la
información. Poner tope al gap sin ponerle tope a la discrepancia deja
pasar señales donde el promedio general dice una cosa y lo que concede
el rival dice otra.

### La cuenta la hace el expediente, no la skill

`senal_base` viene con el fallo ya calculado y el motivo (`muestra
corta`, `los tres estimadores se contradicen`, `demasiado cerca de la
media`). La skill copia `fallo` y no lo discute. Es lo que hace que dos
corridas sobre el mismo expediente den la misma `senal` — la aritmética
no es trabajo de criterio, y cuando lo fue salió inconsistente.

**Aplicada a la tanda, la regla dio vuelta tres de las cuatro lecturas:**

```
  Rosario córners        null    ->  muchos   (+20%)
  Fluminense faltas      muchas  ->  null     (n=4 < 6)
  Fluminense generador   Hulk    ->  Hulk + Colidio
```

La más instructiva es la segunda: era la afirmación más fuerte de la
tanda y el umbral la mata por muestra. Costo a tener presente: con
`n ≥ 6`, **arg.1 (n=5-6) y bra.1 (n=4-5) van a producir muy poco hasta
que los cachés se llenen.** Es el precio de la regla y es correcto
pagarlo.

### Defecto 2 — `generador`: por suma o por partido, sin definir

Colidio llevaba 14 remates en 3 partidos y su segundo 9 en 4. Por suma
es +56%; por partido, +107%. **La suma premia a quien jugó más**, que es
lo contrario de lo que la señal quiere decir. Pasa a medirse por
promedio por partido, con mínimo de 3 apariciones — una tasa sacada de
un partido no es una tasa. El expediente lo entrega calculado en
`liderazgoH`/`liderazgoA`.

**El 50% no se movió y sigue siendo experimental.** No se puede calibrar
todavía, y el motivo es concreto: las series por jugador **no están
alineadas entre sí** —cada una son las últimas N apariciones de ESE
jugador, no las últimas N del equipo— así que no hay forma de
reconstruir quién lideró un partido concreto y medirlo contra historial.

### Defecto 3 — un solo lugar para dos generadores

En Fluminense–Vasco los dos equipos tenían un líder que superaba el
umbral, y `generador` era un objeto único: había que elegir uno a dedo,
que es el mismo volado que el umbral existe para evitar. Pasa a ser una
**lista** de hasta uno por equipo. `medir_senal.py` sigue leyendo el
objeto viejo.

### Defecto 4 — el árbitro estaba en las dos skills diciendo cosas distintas

La tabla de evidencia admisible de la skill de inclinación listaba al
árbitro para `faltas` y `tarjetas`. La de estadísticas lo prohíbe. Ahora
hay **una sola regla para todo VALOR: el árbitro no es evidencia.**

Y de paso se corrigió una afirmación de más que este repo venía
repitiendo. El principio D decía que el efecto del árbitro **"da cero"**.
`medir_arbitros.py` no midió eso: midió que con 54 partidos y ~2 por
árbitro el azar igualaba lo observado el 33% de las veces en tarjetas y
el 19% en faltas. Eso es *no podemos medirlo con esta muestra*, que no
es lo mismo que *está probado que no existe*. Para la escritura el
resultado práctico es idéntico —no hay con qué sostenerlo, no se
escribe— pero la diferencia importa el día que haya muestra.

### Qué contestó la primera tanda

> Cuando tiene información suficiente, ¿la skill produce señales nuevas,
> concretas, verificables y distintas de lo que λ ya sabe?

**Sí, y ahora además de forma reproducible.** Las afirmaciones son
concretas, se resuelven sin criterio humano, ninguna es proxy de λ, y el
control no fabricó nada donde no había información.

Lo que **no** está contestado, y es lo que sigue: si aciertan, y si
aportan sobre el pronóstico numérico de la misma métrica. Para eso hace
falta la tanda de evaluación, con el instrumento congelado como quedó
acá — y con el caudal bajo que el umbral impone mientras los cachés de
arg.1 y bra.1 no lleguen a seis partidos medidos.

## 35. El instrumento queda congelado hasta tener muestra (2026-09-03)

Cierre del bloque §33–§34. No hay nada que hacer hasta que entren fechas,
y eso es una decisión, no una pausa por falta de ideas.

### Estado, en una línea por cosa

- **El umbral está calibrado** sobre 20.897 partidos europeos, con
  train/test temporal (§34). Vive en `expediente.UMBRAL_SENAL`.
- **La transferencia a arg/bra NO está validada.** `--transferencia` la
  probó con la regla congelada sobre 121 partidos de arg.1 y 55 de
  bra.1, y emitió **cero señales**: el corpus tiene ~2 partidos por
  equipo (abarca dos torneos) y `n` casi nunca llega a 6. Es *no
  concluyente*, ni fallo ni confirmación.
- **El censo dice que hoy no hay material.** `faltas` y
  `volumen_remates` —las dos dimensiones fuertes— no pueden producir una
  sola afirmación en arg ni en bra. arg.1 necesita una fecha; bra.1, dos.
- **No se toca nada.** Ni umbrales, ni criterios, ni el esquema.

### Las tres preguntas de la tanda, y son tres

Lucas pidió que no se mezclen, y el motivo es el mismo error de §33 con
otro disfraz:

1. **¿El instrumento consigue evidencia objetiva suficiente?** Es la
   pregunta del censo, y hoy la respuesta es "casi no".
2. **Cuando emite, ¿supera la tasa base?** Contra la tasa base de esa
   misma métrica, nunca contra 50% — las cuatro dimensiones tienen base
   entre 51% y 57% porque los recuentos son asimétricos.
3. **¿Aporta información incremental sobre el modelo cuantitativo?** Es
   la que importa y la única que justifica el instrumento.

**Acertar no es aportar.** La ortogonalidad a λ solo habilita a
investigar una dimensión; no prueba que sirva. Una señal puede acertar
el 70% y ser inútil si el pronóstico numérico de la misma métrica ya
acertaba el 70%. Eso es exactamente lo que pasó en §33 con el esquema
viejo: la lectura acertaba 4 de 4 repitiendo a λ con otras palabras.

### La regla de lenguaje, que no es cosmética

Sin muestra suficiente se escribe **"no concluyente"**, nunca "no
funciona". Son afirmaciones distintas y la segunda cierra un camino que
la evidencia no cerró. Este repo ya tenía una de esas: el principio D
decía que el árbitro "da cero" cuando lo medido era que con 54 partidos
no se podía concluir (§34).

Y si algún día la transferencia falla de verdad —señales emitidas, mal
acierto—, **primero se diagnostica por qué y después se recalibra.**
Recalibrar sin diagnóstico es ajustar hasta que el número guste.

### Qué hacer cuando entre la fecha del 4 al 7

```
python calibrar_senal.py --censo            ¿ya hay material?
python calibrar_senal.py --transferencia    ¿el corpus ya permite probarla?
```

Si el censo abre, correr la tanda con la regla **exactamente como está**.
Los cuatro análisis del smoke test (§34) ya están cargados y conformes a
la regla vigente, así que suman a la muestra.

## 36. Auditoría completa, y los tres arreglos de infraestructura (2026-09-03)

Se auditó el proyecto entero mientras esperamos muestra: pipeline,
leakage temporal, separación evidencia/expectativa, la regla congelada,
consistencia entre módulos, el LLM, los mercados, los arneses de
medición, los caches y el código muerto.

**Lo que NO encontró, y vale decirlo:** ningún leakage temporal en
producción ni en los arneses principales. `backtest.py` filtra con
`fecha < f` estricto y su línea base también es walk-forward;
`historia_reciente()` está bien guardada (`pasada = s < hoy.year`);
`historial()` filtra `completed`; `parametros_por_liga()` calcula dentro
de cada liga; el devig es Shin en los 13 módulos de producción; y
`doble_via.py` da 6.66e-16 entre Python y JavaScript. El motor está bien.

Se arreglaron tres cosas, en el orden que pidió Lucas. **Ninguna toca
parámetros, umbrales ni calibraciones**: las tres son infraestructura de
medición.

### C2 — medíamos un modelo y publicábamos otro

`medir_roi.py` → `medir_historico.evaluar` → `_probs_modelo` calculaba
`lh = mu_l * a_l * d_v` **crudo**, con `rho` fijo en 0.05. Producción
aplica después `corregir_escala()` y `encoger_diferencia()`, y usa el
`rho` de cada liga:

```
          rho prod   rho arnés   escala   diferencia
  arg.1     -0.05       0.05      0.50       0.95
  bra.1      0.00       0.05      0.50        —
  eng.1     -0.02       0.05      0.60        —
  fra.1     -0.05       0.05      0.60        —
  esp.1      0.00       0.05      0.70        —
```

`escala = 0.50` corta a la mitad la desviación de λ respecto del centro
de la liga. El `rho` está con el signo cambiado en cuatro de cinco. Con
λ 1.80/0.90 en arg, producción publica 1.635/0.848.

Entra `parametros_produccion(liga)` y `evaluar(..., liga=...)`. Reproduce
el orden exacto de `actualizar.py`: escala, diferencia, y recién después
recorte y redondeo a tres decimales — recortar antes da otro número, y
así estaba.

**Sin `liga` el arnés queda como estaba.** Es a propósito: `jpn`, `mex` y
`usa` son ligas solo-medición y no tienen modelo de producción que
reproducir.

### C3 — la evidencia de cada señal no sobrevivía a la corrida siguiente

`estadisticas.json` se sobrescribe y es una ventana móvil de ocho
partidos. El análisis guardaba el fallo ("muchos") y no contra qué. Así,
cuando la capa 2 fuera a verificar, iba a recomputar la vara desde un
`estadisticas.json` posterior **que ya incluye el partido que está
verificando**.

Es el mismo problema que `cuotas.json` y `props_jugadores.json` ya
resuelven acumulando fotos, por el mismo motivo, y que acá nadie había
visto.

Entra `python expediente.py --sellar <id>|--todos`, que escribe
`desarrollo.evidencia` con `senal_base` entero (los tres estimadores, la
vara, el gap, la dispersión, `n` y el motivo) más `liderazgo` de los dos
equipos. **Se niega a sellar un partido que ya tiene resultado**: un
sello puesto después no es una fotografía, es una reconstrucción, y no
se distingue de la buena mirando el archivo.

Los cuatro análisis del esquema nuevo quedaron sellados el 2026-09-03,
antes de que se jugaran.

### C1 — un proxy derogado de λ estaba apagando marcas doradas

`senalDividida()` leía `senal.ritmo_goleador`, `senal.estructura` y
`senal.ambos_marcan`: las tres que §33 derogó por describir cuántos
goles va a haber, que es lo que λ calcula. Con ellas ponía `esVal =
false` sobre goles y ambos marcan.

Dos cosas a la vez, y la segunda es la peor. Un proxy **medido** de λ
vetaba marcas de valor; y como el esquema nuevo no tiene esos campos,
solo disparaba en los nueve análisis viejos — el mismo partido marcaba
distinto según con qué esquema se lo hubiera analizado, sin que nada lo
dijera.

Se retiró la función, su llamado, sus exports y sus seis tests. **No se
reemplaza por otra cosa**: las cinco dimensiones del esquema nuevo hablan
de córners, faltas, remates y jugadores, y ninguna contradice una línea
de goles. Si algún día vuelve a haber tensión, se diseña y se mide
entonces.

Los nueve análisis viejos conservan su texto y su `senal`. Ya no tienen
efecto, y `medir_senal.py` los sigue contando aparte como "esquema
viejo" — eso es contabilidad explícita, no convivencia silenciosa.

### Qué queda invalidado, y qué no

**Hay que volver a medir** (nadie lo hizo todavía, y no se hace en el
mismo movimiento que se arregla el instrumento):

- los ROI de `medir_roi.py` — arg −9.17%, bra −9.13%, eng +1.01%, fra
  −5.22%, spa −5.33%, usa −1.86%, jpn +2.78%;
- y con ellos, **la regla `LIGAS_SIN_VALOR`**, que sale de esos números;
- todo lo que pase por `medir_historico.evaluar`: `medir_apertura.py` y
  las mediciones de atraso contra el cierre.

**Sigue en pie** todo lo que no pasa por ese arnés: `medir_props.py` y el
CLV de §22bis (precio real de Bet365, sin λ), `medir_margen_props.py`
(§31), `medir_bandas.py` y `medir_metamodelo.py` (arneses propios),
`calibrar_senal.py` (football-data, sin λ), `medir_devig.py`,
`medir_corners.py`, `medir_jugadores.py`, `medir_arbitros.py` y
`backtest.py` como medida de calibración.

**Lo que NO se puede concluir todavía**, y conviene escribirlo antes de
que la tentación aparezca: que los ROI viejos estuvieran mal *hacia
abajo* o *hacia arriba*. No sabemos el signo del sesgo. Arreglamos la
infraestructura; medir es el paso siguiente y es aparte.

### Hallazgos documentados y NO tocados

Quedan para decidir aparte, con su clasificación de la auditoría:

- 🟠 **capas 2 y 3 de `medir_senal.py` son un stub** — imprimen "sin
  resultados cargados" sin consultar `resultados.json`. De las tres
  preguntas separadas, solo la 1 existe como código.
- 🟠 **el umbral 50% de `generador` vive solo en prosa.** Las cuatro de
  volumen tienen `fallo` calculado; esta no. Es disciplina, no
  estructura.
- 🟠 **`LIGAS_SIN_VALOR` cruza por regex sobre el nombre visible**
  (`m.comp`) aunque `m.liga` existe y se agregó para evitar justamente
  eso.
- 🟠 **esp.1 marca valor con ROI −5.33% ±8.52** y no está en
  `LIGAS_SIN_VALOR`; arg (−9.17) y bra (−9.13) sí. El corte entre esos
  números no está medido. (Y este hallazgo ahora depende de C2.)
- 🟠 **`CLAUDE.md` está desactualizado**: dice seis competiciones con
  jpn.1 y no menciona esp.1; el código tiene esp.1 y no jpn.1 desde el
  commit `80a7dea`. `partidos.json` todavía trae jpn.1 — es una foto
  anterior al cambio.
- 🟡 la ventana de ocho partidos de `estadisticas.json` puede mezclar
  Apertura y Clausura.
- 🟡 cuatro clases CSS muertas y cuatro caches `esp.1-*.json` sin
  trackear.

## 37. Los ROI, vueltos a medir con el arnés corregido (2026-09-03)

Único recálculo de §36 C2. No se tocó nada más: mismo `VALOR_MIN`/
`VALOR_MAX`, misma cuota máxima, mismo precio de cierre, mismas ligas.
Lo único que cambió es que ahora el λ del arnés es el de producción.

### Los controles salieron idénticos

`jpn`, `mex` y `usa` no están en `COMPETICIONES`: son ligas solo-medición
y `parametros_produccion()` les devuelve `None`, así que el arnés las
mide igual que antes. Se usaron como control de que C2 no movió nada que
no debía:

```
  jpn  +2.78% ± 7.67  ->  +2.78% ± 7.67   1318 ap.   idéntico
  mex  −3.46% ± 7.50  ->  −3.46% ± 7.50   1302 ap.   idéntico
  usa  −1.86% ± 6.81  ->  −1.86% ± 6.81   1522 ap.   idéntico
```

Al decimal. El cambio de C2 solo alcanza a las ligas que la app publica.

### Las cinco que sí tienen modelo de producción

```
         antes              después            n      cambio
  arg  −9.17% ±6.44 SIG   −6.96% ±7.46 ruido  1442   +2.21 pp
  bra  −9.13% ±7.32 SIG   −4.99% ±7.74 ruido  1229   +4.14 pp
  eng  +1.01% ±8.92       +2.21% ±9.53         839   +1.20 pp
  fra  −5.22% ±8.71       −3.04% ±9.83         809   +2.18 pp
  spa  −5.33% ±8.52       −6.95% ±8.87         917   −1.62 pp
```

El `±` son **dos errores estándar**, así que "significativo" es que el
ROI en valor absoluto supere esa cifra.

**El resultado que importa: arg y bra dejan de ser significativos.**
Eran los dos únicos números del conjunto que salían del ruido, y eran
justamente los que sostienen `LIGAS_SIN_VALOR`. Con el λ de producción,
−6.96 contra ±7.46 y −4.99 contra ±7.74 caen los dos adentro del
intervalo.

`n` también se movió (arg de ? a 1442, bra a 1229) porque el λ corregido
produce otras ventajas y por lo tanto califica otro conjunto de
apuestas. Era esperable y no es un efecto aparte: es el mismo.

### Lo que NO se puede concluir de esto

Cuatro de cinco ligas mejoraron y una empeoró. **Eso no dice que el
modelo de producción sea mejor**: dice que el arnés estaba midiendo otra
cosa. Un ROI que pasa de −9.17% a −6.96% no es una mejora del producto —
es la primera vez que se mide el producto.

Y sobre todo: **ninguna liga pasó a ser rentable.** Siete de las ocho
tienen punto estimado negativo o cero adentro del intervalo. Lo que
cambió es la fuerza de la evidencia en contra de dos de ellas, no la
aparición de evidencia a favor de ninguna.

### Nuevo, y no estaba medido: over/under

El arnés corregido también reporta O/U donde football-data publica la
línea. Aparece un resultado que antes no figuraba en ningún lado:

```
  eng O/U   721 ap.   −2.45% ± 8.98   ruido
  spa O/U   790 ap.   −5.73% ± 8.54   ruido
  fra O/U   683 ap.  −10.59% ± 8.74   SIGNIFICATIVO
```

**Francia en goles es el único negativo significativo que queda en todo
el conjunto.** No se hizo nada con esto: queda anotado.

### `LIGAS_SIN_VALOR`: qué pasa con la regla

El criterio con el que se armó la lista fue "medido que ahí la regla
resta, significativo". Aplicado a los números nuevos **y solo a ellos**,
la lista quedaría vacía: ninguna liga es significativamente negativa.

**No se cambió.** Tres razones, y ninguna es cautela genérica:

1. **Sacar una guarda no es lo mismo que ponerla.** La lista se puso
   porque había evidencia de daño; sacarla ahora sería por *ausencia* de
   evidencia, que no es lo mismo. Los dos puntos estimados siguen siendo
   negativos (−6.96% y −4.99%).
2. **La segunda pata del argumento no se volvió a medir.** La decisión
   original se apoyaba también en `barrido_valor.py` — 39 ventanas de
   ventaja, ninguna positiva fuera de muestra. Ese script llama a
   `MH.evaluar()` **sin `liga`**, así que sigue midiendo el λ crudo. La
   pata (a) se cayó; la (b) está sin recalcular.
3. **Es un cambio de producto hacia afuera.** Vaciar la lista enciende
   la marca dorada en las dos ligas que son la mitad de la grilla.

Lo que corresponde antes de decidir: pasar `liga=` en `barrido_valor.py`
y en `medir_apertura.py` —los dos consumidores que quedan del arnés
crudo— y volver a correrlos. Recién ahí la regla tiene sus dos patas
sobre el modelo que se publica.

### Qué queda reemplazado y qué sigue en pie

**Reemplazados** (los números viejos ya no se citan):

- la tabla de ROI de §24, en las cinco ligas con modelo de producción;
- la frase "arg y bra restan, significativo" — ya no lo es;
- el argumento de §20 sobre el margen de DraftKings, que se apoyaba en
  el −9.17% como piso.

**En pie:**

- los tres controles, que son los mismos números de antes;
- el criterio de entrada de esp.1, que nunca fue el ROI sino la
  profundidad de la escalera de props;
- todo lo que no pasa por `medir_historico.evaluar` (§36).

## 38. C2 cerrado: los dos consumidores que faltaban (2026-09-03)

Se completó §36 C2 pasando `liga=` a los dos arneses que quedaban
tomando el λ crudo, y se revisó consumidor por consumidor cuál debe
hacerlo y cuál no.

### El barrido de consumidores

`evaluar()` tiene doce llamadores. No todos deben reproducir producción,
y confundirlos hace daño en las dos direcciones. La clasificación quedó
escrita en el docstring de `parametros_produccion()`:

```
  LO PASAN            medir_roi · barrido_valor · medir_apertura
  NO DEBEN PASARLO    barrido_escala_lambda · barrido_diferencia
                      medir_compresion
  PENDIENTES          medir_ejes · medir_condicional
                      medir_encogimiento · medir_bandas
```

Los tres del medio son **circulares** si lo pasan: los dos barridos
*derivan* `escala` y `diferencia`, y `medir_compresion` *diagnostica* el
defecto que motivó `escala`. Con el λ ya corregido medirían la
corrección encima de sí misma.

Los cuatro pendientes afirman cosas sobre la app y deberían pasarlo,
pero cambiarlos es volver a medir, no arreglar el arnés. Y hay un
choque real que resolver antes: **`prod["rho"]` pisa el `rho` del
llamador**, y `medir_encogimiento` y `medir_bandas` barren `rho` por su
cuenta.

### `barrido_valor.py` — la segunda pata aguanta

Es la otra mitad del argumento de `LIGAS_SIN_VALOR`: si la regla resta,
¿no habrá una ventana de ventaja donde sí dé? Rehecho con el λ de
producción, train/test temporal:

```
  arg   6270 partidos · train 3687 · test 2583
        36 ventanas con muestra suficiente
        NINGUNA da ROI positivo en train Y en test
        ventana de producción (6-12%): train −7.72%  test −5.90%

  bra   38 ventanas con muestra suficiente
        1 positiva en las dos mitades, y no se despega del ruido
          (piso 0.12 techo 0.16: test +2.35% ±36.08 sobre 68 apuestas)
        ventana de producción (6-12%): train −1.76%  test −11.84%
```

**El resultado no cambió.** Con el modelo crudo eran 39 ventanas y
ninguna positiva; con el de producción son 36 en arg y ninguna, y 38 en
bra con una que es ruido puro (±36 sobre 68 apuestas). Mover los
umbrales sigue sin convertir la regla en rentable.

### `medir_apertura.py` — el CLV no se movió, el ROI sí

```
  eng, Pinnacle        antes            después
    n en test           362              299
    ROI apertura      +2.79% ±14.82    +9.42% ±16.72
    CLV               −1.62% ± 0.82    −1.62% ± 0.92   sigue significativo

  eng, Bet365
    ROI apertura      −4.27% ±13.57    −1.99% ±14.90
    CLV               −0.44% ± 0.82    −0.44% ± 0.91   ruido
```

El λ corregido elige otro conjunto de apuestas —299 contra 362— y el
ROI se mueve seis puntos. **El CLV cae en el mismo número a dos
decimales en las dos casas.** No es identidad ni un arnés que ignore el
modelo (`apuestas_apertura` selecciona con `f["modelo"][i]`): es que el
CLV por apuesta está dominado por la deriva del mercado y es robusto a
qué subconjunto de apuestas de valor se elija. Eso lo hace la medida
estable que §20 decía que era, y ahora con evidencia de que la
estabilidad es real.

**Sigue en pie el hallazgo de §20**: contra Pinnacle en eng el CLV es
−1.62% con ±0.92 de dos errores estándar, o sea **negativo de verdad**.
La línea se mueve en contra el 60% de las veces. Y sigue en pie la
advertencia sobre el ROI positivo: ahora es +9.42% en vez de +2.79%, con
±16.72 encima y un CLV negativo abajo. Es más tentador y no más real.

### `LIGAS_SIN_VALOR`: la conclusión queda abierta, y se mantiene la guarda

Las dos patas del argumento original están ahora medidas sobre el modelo
que se publica, y dicen cosas distintas:

```
  (a) el ROI resta, significativo   →  CAYÓ.   arg −6.96% ±7.46,
                                       bra −4.99% ±7.74: los dos ruido
  (b) ninguna ventana lo arregla    →  AGUANTA. 36 y 38 ventanas,
                                       ninguna positiva fuera de ruido
```

No se cambió la lista. La evidencia de daño se debilitó, pero **no
apareció ninguna evidencia de que la regla funcione**: los dos puntos
estimados siguen negativos, y la pata que decía "no se arregla moviendo
umbrales" quedó intacta con el modelo bueno.

Lo que haría falta para sacar la guarda no es que el daño deje de ser
significativo — es evidencia positiva. Hoy no la hay en ninguna liga.

### Qué queda definitivamente reemplazado

- El ROI de las cinco ligas con producción (§37).
- "arg y bra restan, **significativo**" — la palabra se cae; el signo no.
- Los ROI de apertura de §20 en eng (Pinnacle +2.79% → +9.42%, Bet365
  −4.27% → −1.99%).
- El conteo de `barrido_valor`: eran 39 ventanas, ahora 36 en arg.

### Qué sigue necesitando evidencia

- **`fra` en over/under**: −10.59% ±8.74, el único negativo
  significativo que queda en todo el conjunto (§37). Nadie lo miró.
- **Los cuatro consumidores pendientes**, y antes el choque de `rho`.
- **`medir_apertura` en fra**: solo se rehizo eng.
- **Cualquier liga con evidencia positiva**: no hay ninguna. Siete de
  ocho tienen punto estimado negativo o el cero adentro.

## 39. Potencia: cuánta muestra hace falta, y qué no se puede medir (2026-09-03)

Aritmética sobre lo ya medido — las tasas de acierto, las tasas base y
las coberturas de `calibrar_senal.py`. No se recalibró nada, no se tocó
ninguna regla, no se usaron los partidos nuevos. `potencia_senal.py`.

### Capa 2 — se puede, y depende brutalmente de la cobertura

Prueba de una proporción contra la tasa base de cada métrica (no contra
50%), dos colas, α = 0.05:

```
  dimensión          base   esperado    delta   n 80%   n 90%
  faltas            54.1%     71.2%    +17.1%      64      83
  volumen_remates   51.2%     63.6%    +12.4%     125     166
  corners_total     52.0%     65.7%    +13.7%     102     135
```

Los `n` son razonables. El problema no está ahí — está en **cuántos
partidos cuesta juntar esas señales**, porque cada dimensión acumula su
propia muestra y la cobertura medida es muy distinta entre ellas:

```
  dimensión         cobertura   1 señal cada   partidos p/80%   ≈ tiempo
  faltas               14.8%      7 partidos            433     17 semanas
  volumen_remates      10.3%     10 partidos           1214     47 semanas
  corners_total         1.9%     53 partidos           5369      4.0 años
```

(a 26 partidos por fecha, que es arg.1 + bra.1 de la grilla de hoy.)

**Córners queda afuera por cobertura, no por tamaño de efecto.** Su
delta (+13.7%) es mayor que el de remates (+12.4%), pero su umbral es
20/20/6 contra 10/15/6, y emite en 1 de cada 53 partidos. Cuatro años.

Y si en Sudamérica la señal resulta más chica que en Europa, el `n` crece
con el cuadrado inverso del delta: a la mitad de señal, faltas pasa de 64
a 262 y remates de 125 a 507.

### Capa 3 — no es cuestión de muestra

Esto es lo importante del cálculo, y es incómodo.

Desde §34 las cuatro dimensiones de volumen **no las decide la lectura**.
El expediente calcula `senal_base` desde `estadisticas.json`, le aplica
el umbral, y entrega el `fallo`; la skill lo copia y tiene prohibido
discutirlo. Entonces:

```
  señal  =  f(estadisticas.json)
  base   =  g(estadisticas.json)
```

Las dos salen del mismo insumo y la primera es la segunda pasada por un
umbral. **El aporte incremental de una función determinista de su propio
baseline es cero por construcción.** Ninguna cantidad de datos lo cambia.

`generador` está igual: `liderazgo_remates()` calcula la ventaja y el
umbral es fijo. Queda un canal angosto —la lectura podría no nombrar a
un jugador que su research dice que no juega— pero no alcanza para
sostener una medición.

**Esto no es un defecto de §34.** Es el precio que se pagó a propósito:
sacar la aritmética de la cabeza del modelo arregló la inconsistencia
del smoke test (null a +16% y "muchas" a +11% en la misma tanda) y, en
el mismo movimiento, dejó a la lectura sin lugar donde aportar en esas
cuatro dimensiones.

### Lo que esto cambia sobre qué mide el instrumento

La capa 2 sigue siendo una pregunta legítima, pero **cambia de dueño**:
mide si el umbral calibrado en Europa transfiere a Sudamérica. Es la
validación de `calibrar_senal.py`, no de la lectura futbolística.

La lectura sí decide en `inclinacion` y en la prosa — y eso lo mide
`medir_analisis.py`, que es otro instrumento y ya existe.

### Qué haría falta para una capa 3 de verdad

Que la señal tuviera un insumo que el estimador no tiene. Dos caminos, y
los dos son decisiones de diseño **que hoy no están tomadas**:

- dejar que la lectura se aparte del `fallo` cuando tiene research que el
  número no ve (una cancha embarrada, un clásico con antecedente) — lo
  que §34 prohíbe hoy, y por buenos motivos;
- o medir contra un baseline más fuerte que el estimador que genera la
  señal, que es otra pregunta.

Sin una de las dos no hay qué medir. Con cualquiera de las dos, el
tamaño de muestra depende de un efecto que todavía no existe y no se
puede estimar honestamente. Lo único que se puede afirmar: detectar
aporte incremental es **siempre** más caro que detectar acierto — se
mide sobre pares discordantes, que son una fracción del total.

### Veredicto

```
  🟢 faltas            64 señales ·   433 partidos ·  0.3 años
  🟢 volumen_remates  125 señales ·  1214 partidos ·  0.9 años
  🔴 corners_total    102 señales ·  5369 partidos ·  4.0 años
  🔴 CAPA 3           no es cuestión de muestra
```

### 39bis. Cómo se lee la próxima tanda, decidido antes de verla

Lucas cerró §39 fijando la interpretación por adelantado, que es la
única forma de que después no se acomode a lo que salga:

- **faltas, remates y córners**: la tanda valida la **transferencia de
  la regla calibrada** a Sudamérica. No demuestra aporte incremental de
  la lectura, y no hay que reportarla como si lo hiciera.
- **`inclinacion` y la prosa**: ahí sigue viviendo la lectura
  futbolística que sí queremos evaluar. Su instrumento es
  `medir_analisis.py`, no `medir_senal.py`.
- **La lectura NO puede apartarse de `senal_base`**, y esto es una
  decisión, no una omisión. Permitirlo abriría la capa 3, pero
  reintroduciría exactamente la inconsistencia que §34 eliminó — dos
  corridas sobre el mismo expediente dando señales distintas. Si algún
  día se abre, se abre con un diseño y una medición, no aflojando la
  regla.

Y la capa 3 **no se rediseña ahora**. La pregunta todavía no está bien
definida, y hacer ingeniería sobre una pregunta mal definida es cómo se
llegó al esquema viejo de §33.

## 40. El veto de `inclinacion`, y por qué la culpa no era del reglamento (2026-09-03)

Sale de un hallazgo del recorrido por la app: **0 oportunidades en 62
partidos**. El diagnóstico tardó tres pasos y cada uno corrigió al
anterior.

### Paso 1 — la cadena de guardas, y quién bloquea de verdad

`marcaDeValor()` aplica cinco guardas conjuntivas. Contadas sobre la
grilla del 2026-09-03:

```
                bloquea en total   bloquea SOLA
  inclinacion         61 / 62            6
  sinMuestra          30                 0
  ligaSinValor        25                 1
  sin cuota            4                 0
```

`sinMuestra` y `ligaSinValor` **no bloquean nada por sí solas**: todo lo
que atrapan ya estaba atrapado por falta de dirección. Y se reparten la
grilla sin pisarse — `sinMuestra` cubre las 30 europeas,
`ligaSinValor` las 25 de arg/bra.

El primer diagnóstico fue "desalineación operativa": las ligas donde se
carga análisis y las ligas donde se puede marcar valor eran conjuntos
disjuntos.

### Paso 2 — se cargaron los 6 que sí llegan, y siguieron siendo 0

Se analizaron los seis de CONMEBOL, que hoy son los únicos que pasan
`ligaSinValor`, `sinMuestra` y `devig`. Los SEIS, no los dos que una
simulación decía que podían marcar: elegir mirando el cálculo habría
sido seleccionar por el resultado.

`inclinacion` salió `null` en los seis. **El primer diagnóstico estaba
incompleto**: no faltaban análisis, faltaban direcciones.

Dos que estuvieron cerca y por qué no:

- **Santa Fe–Vasco**: la altura de Bogotá es un factor válido y listado
  (principio N). El rastro la desarma — Santa Fe recibió a River, un
  equipo de llano, dos veces en esta misma copa y empató las dos.
- **Boca–São Paulo**: las bajas de agosto (Paredes, Pellegrino, Lozano)
  estaban VENCIDAS; los tres tienen partidos recientes de arranque.

Contaminación declarada: quien escribió esos análisis ya había visto la
simulación y sabía qué direcciones habrían marcado. Los dos casos
salieron `null` —o sea que no se reprodujo ninguna— pero **no cuentan
como evidencia independiente**.

### Paso 3 — la auditoría retrospectiva, y acá cambia todo

Se reconstruyó qué habría pasado con las 15 direcciones históricas si se
les aplicaran K, O y P:

```
  28 análisis  →  15 direcciones (54%)
                      ↓ K    12 sobreviven   (−3, −20%)
                      ↓ O    12              (−0)
                      ↓ P    12              (−0)
```

**Los tres principios, como están escritos, habrían dejado pasar 12 de
15.** La tasa habría caído de 54% a 43%. Cayó a 6%.

**K filtra el 20%** y es el único con veto real. Las tres que mata caen
por su prueba dura —tapá la frase de la baja y fijate si la dirección
sigue en pie—: en River–Santa Fe queda "racha floja", en
Tigre–Montevideo queda "líder invicto", y en el empate de espn401841522
el argumento se sostiene entero con forma.

**O filtra 0%.** En las 15, la localía aparece como acompañamiento y no
como argumento: se tapa "de local" y el desbalance de bajas queda en
pie. O corrige hacia DÓNDE apuntan las direcciones, no cuántas hay.

**P filtra 0%, y acá estaba el error de lectura.** P dice textualmente
que *"un factor no verificable puede sostener una `inclinacion`, no
puede sostener una frase terminante"*. **P no es un veto: es una
restricción de tono.** Solo mata una dirección en el estado "verificado
en contra" —el factor ya ocurrió y no pasó nada—, y ninguna de las 15
está en ese estado.

### La conclusión, y es sobre quién aplica, no sobre qué dice

El desplome de 54% a 6% **no lo explica el reglamento**. Lo explica cómo
se aplicó en las tandas nuevas: leyendo P como veto cuando es de tono, y
aplicando la prueba dura de K a veredictos que la habrían sobrevivido.

Queda fijado, para las próximas tandas:

- **P no se lee como veto automático.** Si un factor no es verificable
  pero sostiene razonablemente una dirección, la dirección existe; lo
  que cambia es el nivel de afirmación del texto.
- **K sigue siendo un filtro duro y real, y no se aplica más estricto de
  lo que dice.** Mencionar la forma no es sostenerse en la forma.
- **No se agregan filtros personales** por encima del texto de K, O y P.

Y una salvedad que no se puede omitir: **las 12 que sobreviven NO son
evidencia de que esas direcciones fueran buenas.** Solo significa que
esos principios no las descartarían. El propio K nació de medir que 5 de
6 direcciones coincidían con el modelo.

### Lo que queda abierto, y no se tocó

La pregunta conceptual sigue sin decidir: **¿`inclinacion` debe ser una
llave obligatoria con poder de veto, o una capa de contexto sin él?**

Un dato técnico que hay que tener presente antes de decidirlo, porque
vuelve asimétricas a las dos opciones: en `marcaDeValor()` la dirección
hace DOS trabajos. Es compuerta (`if(!dir) return null`) y es
**selector** (`dif = lectura(m).p[dir] - pq[dir]`) — elige sobre qué
resultado se calcula la ventaja. Quitarle el veto no es borrar una
llave: es trasladarle la elección al modelo, que pasaría a marcar valor
sobre su propia opinión. Eso es exactamente la circularidad que la regla
existe para impedir.

Y el costo medido del veto hoy es bajo: las marcas que suprime están en
arg/bra, donde el ROI medido es negativo, o en CONMEBOL, donde no hay
ROI medido. **No hay ninguna liga con evidencia positiva medida que el
veto esté bloqueando.**

El costo real es otro, y es el mismo patrón de §39: con 1 dirección cada
62 partidos, `medir_analisis.py` nunca junta muestra para evaluar si
`inclinacion` sirve. La regla impide su propia evaluación.

## 41. Lo que se hizo mirando la app corriendo (2026-09-03)

Se levantó `index.html` en un servidor local y se recorrió pantalla por
pantalla: Portada, Veredicto, Lectura, Datos, Registro, Método y móvil.
**La auditoría de código de §36 no había visto ninguno de los tres bugs
que aparecieron acá.** Vale como método: mirar la app encontró en veinte
minutos lo que leer el código no encontró en horas.

### Tres bugs de cara al usuario

**1. La app citaba un ROI que nosotros mismos habíamos dejado viejo.**
Decía *"está medido que la regla de valor resta plata (−9.2% de ROI
walk-forward)"*. Ese número murió con §37. Ahora dice −7.0% y −5.0%, y
—más importante— se sacó **"está medido que resta"**: con intervalos de
±7.46 era afirmar de más. Queda lo que sí se sostiene, que es el punto
estimado negativo más las 74 ventanas de `barrido_valor` sin una sola
positiva. `LIGAS_SIN_VALOR` no se tocó.

**2. El caché hacía invisible toda carga manual.** `traer()` cachea con
`?v=VERSION_DATOS`, y esa versión es el sello de `partidos.json`. Pero
`analisis.json` y `analisis_estadisticas.json` son **carga manual**:
cambian sin que `partidos.json` cambie. Consecuencia: se sube un
análisis y el usuario no lo ve **hasta doce horas después**, cuando el
cron vuelve a correr.

No es teoría — es lo que pasó al cargar la segunda skill: el archivo en
disco tenía diez entradas, el servidor servía diez, un `fetch` a mano
traía diez, y la app leía seis. Los dos archivos quedan exceptuados de
la versión compartida; pesan 75 KB de 2,1 MB.

**3. Las dos afirmaciones de la pantalla de límites eran falsas**, y es
la pantalla donde la app explica de qué NO se fía. *"Cinco partidos por
equipo"* estaba escrito a mano cuando los números reales eran mediana 4,
mínimo 2 — falso para las tres ligas europeas enteras. Ahora se calcula.
Y *"Una sola casa de cuotas — DraftKings"* dejó de ser cierto cuando
entró `mercadoExtra`: Bet365 alimenta 59 de 62 partidos y el usuario la
ve por nombre.

### Lo que se revisó y estaba bien

Registro (empty state correcto), el resto de Método, móvil 375×812 sin
scroll horizontal, y la capa **Datos** — que resultó ser la pantalla más
honesta de la app: avisa que abajo de 4 partidos por sede el split no
dice nada, marca `SEÑAL BAJA/ALTA/SIN MEDIR` por métrica, muestra el
2.09× de remates, y dice que el plantel no revela lesionados **donde se
mira el plantel**. Las tres capas renderizan en los 62 partidos sin una
sola excepción.

### Las dos tandas de análisis que no están en §40

§40 documenta la tanda de CONMEBOL. Faltan las otras dos:

- **7 de arg.1** con candidato a `generador`, elegidos por eso y no por
  si podían marcar. Los 7 emitieron `generador`; volumen todo en `null`
  por muestra. Una sola `inclinacion`, San Lorenzo–Talleres en `"E"`,
  por el debut de Omar De Felippe.
- **8 más** (4 de esp.1, 4 de bra.1), la última antes de que se corte la
  disponibilidad de escribir análisis. Subieron `generador` de 14 a 24
  señales. Una `inclinacion`: Athletic–Atlético en `"E"`, por Álex Baena
  —43% de los goles del Atlético— reportado lesionado y **la única
  ausencia de todas las publicadas que el plantel permitía pesar**.

Total: **25 análisis con esquema nuevo, los 25 sellados antes de
jugarse**, con 25 afirmaciones de las cuales 24 son `generador`.

### El control de merge atajó un error que se habría perdido en silencio

En la última tanda, el chequeo contra `califica` **abortó el merge**: se
había escrito "Túlio Eduardo Silva" y el plantel dice "Túlio Eduardo
Silva De Oliveira". La capa 2 cruza por nombre EXACTO, así que esa señal
se habría resuelto como "no está en el plantel cacheado" —o sea, no
resoluble— y **habría desaparecido de la muestra sin que nadie lo
notara**. Es la misma familia que `senalDividida()`: la pérdida
silenciosa no se ve como un error, se ve como menos datos.

### Un hallazgo anotado y NO tocado

`friccion` se escribió en los cuatro análisis de estadísticas y **no se
muestra en ninguno**. No es un bug: el bloque Fricción exige que el peso
propio de cada equipo supere 0.25 y en arg.1 el encogimiento no llega,
así que la app se calla con razón. Pero significa que un campo se puede
escribir y no llegar nunca a pantalla, sin que nada lo avise.

## 42. La tanda del 4/9, dos bugs de datos y el censo que abrió (2026-09-04)

Se analizaron los **7 partidos de la fecha con las dos skills** — 5 de
inclinación nuevos más los 2 que ya la tenían del 3/9, y los 7 de
estadísticas, que no tenía ninguno. Todos sellados antes de jugarse.

### El resultado de la tanda

```
  hora   liga     partido                            inclinacion
  14:00  fra.1    Lyon – Auxerre                     null
  16:00  eng.1    Ipswich – Liverpool                null
  16:00  esp.1    Betis – Real Madrid                null   (3/9)
  16:05  fra.1    PSG – Monaco                       null
  16:45  arg.1    Estudiantes RC – Sarmiento         null
  19:00  arg.1    Belgrano – Huracán                 null   (3/9)
  19:00  arg.1    Platense – Riestra                 "E"
```

**1 dirección de 7**, y la única sale de un factor que el modelo no
puede ver: Platense juega el martes siguiente contra Fluminense en el
Maracaná por los cuartos de la Libertadores y su entrenador reparte
minutos. La prueba dura de K la pasa — tapada esa frase, los dos
empatan en ocho puntos y no queda razón para elegir nada. Se escribió
en tono de expectativa, no de hecho, porque la rotación está anunciada
como probable: es el estado "no verificable" de P, que **baja el tono y
no pone `null`** (§40).

### Lo que la tanda dice sobre por qué Europa da puros `null`

No es el reglamento: es el calendario. Con `pjMax = 2`, la maquinaria
de pesaje del principio J no tiene con qué trabajar. Las ausencias de
los cuatro partidos europeos eran **todas** de una de dos clases:

- **de larga data** — Bradley operado en enero, Ekitike con el Aquiles
  en abril, Minamino con el cruzado en diciembre, los tres de Auxerre.
  Ninguno jugó los partidos que el modelo ya vio, así que están dentro
  del precio;
- **impesables** — jugadores con `pj = 1` y `peso_goles = 0`, o que ni
  figuran en el plantel.

En los cuatro europeos hubo además **cuatro entrenadores nuevos** —
O'Neil en Ipswich, Iraola en Liverpool, Still en Auxerre, Filipe Luís en
Monaco. Los cuatro son factores exclusivos por definición y los cuatro
tienen dos fechas de rastro, que son exactamente los resultados que el
modelo ya tiene. **Un factor exclusivo cuyo rastro completo ya está
dentro de λ no agrega dirección.**

### Bug 1 — la serie del jugador viene al revés en `expediente.py`

`planteles.json` guarda la serie del más nuevo al más viejo.
`expediente_estadisticas.py` la da vuelta y lo declara en un aviso
(verificado contra ESPN partido por partido, §19.5).
**`expediente.py` la pasa cruda y no dice en qué orden viene.**

Caso: Kail Boudache aparece con remates `[0, 6]` en el expediente de
inclinación y `[6, 0]` en el de estadísticas. El correcto es `[6, 0]` —
seis remates el 22/08 en Toulouse, ninguno el 29/08 contra Le Havre.

Una skill que lee de izquierda a derecha como se lee el tiempo la lee al
revés. Es la misma pérdida silenciosa de §19.5, viva en el otro archivo.
No contaminó esta tanda porque no se afirmó ninguna tendencia por serie
en los campos de inclinación. **No se tocó** — queda como tarea aparte,
con test que fije la dirección.

### Bug 2 — un córner faltante entra como cero y apaga la señal por el motivo equivocado

PSG figura con `concede.corners = 0.0` sobre `n = 2`: **el único de los
110 equipos del caché**. Y `concede.remates` (9.0), `concede.pases`
(250.0) y `concede.tarjetas` (2.0) le dan **desvío 0.0** en dos partidos
contra rivales distintos y en canchas distintas. No es una medición, es
un faltante leído como cero.

Lo que lo hace grave no es el dato sino a dónde llega. `veredicto_senal()`
calcula `e3 = (sh + ca)/2 + (sa + ch)/2`, y `ch` es ese cero. En
PSG–Monaco el estimador cruzado de córners cae a **9.2** contra 12.0 de
`produce` y 11.5 de `sede`, y eso empuja la dispersión a **0.273**, por
encima del tope de 0.20. Con muestra suficiente, un dato que falta
habría apagado la señal reportando *"los tres estimadores se
contradicen"* cuando lo cierto es *"falta un dato"*.

Es la regla de CLAUDE.md sobre descartes silenciosos, en otra forma: no
se ve como un error, se ve como datos. **No se tocó**; queda como tarea
aparte. En el análisis publicado no se usó el bloque `concede` de PSG.

### Bug 3 — la sede escrita a mano contra la sede del expediente

El análisis de Betis–Real Madrid del 3/9 decía "en el Benito Villamarín"
cuando `partidos.json` trae `Estadio La Cartuja`. El dato correcto
estaba en el expediente y se escribió otro. Corregido en la prosa; no
toca `inclinacion` ni el sello, que cubre `desarrollo.evidencia`.

### El censo abrió, y la transferencia sigue sin poder probarse

Las dos corridas que §35 dejó agendadas para esta ventana. Salidas
completas en `data/censo_2026-09-04.txt` y
`data/transferencia_2026-09-04.txt`.

**Censo** — qué puede producir el instrumento sobre la grilla de hoy:

```
                     partidos con      corners      generador
                     al menos una      AFIRMA       (equipos)
  arg.1                8 de 15            1           8 / 30
  esp.1                8 de 11            0          10 / 22
  bra.1                5 de 10            0           6 / 20
  conmebol.lib         2 de 3             0           2 / 6
  conmebol.sud         1 de 3             0           2 / 6
  eng.1                0 de 10            0           0 / 20
  fra.1                0 de 9             0           0 / 18
```

**arg.1 produjo la primera afirmación de volumen posible del proyecto**:
las quince tienen `n >= 6` en córners, siete pasan dispersión y una pasa
el gap. `faltas` y `volumen_remates` siguen con `n` mediano de 5 y piden
6 — **falta exactamente una fecha**, que es lo que §35 anticipó.

El caso más cerca, medido en esta tanda: en Platense–Riestra, `faltas`
tiene gap **+22.9%** (pide 10%) y dispersión **0.112** (tope 0.15) — las
dos condiciones cumplidas — y muere solo por `n = 5 < 6`. Y su
`corners_total` tiene gap **−22.8%**, que pasa el 20%, y muere por
dispersión 0.207 contra el tope de 0.20.

**Transferencia** — sigue **no concluyente**, igual que en §35: sobre 95
partidos de arg.1 y 30 de bra.1 la regla congelada **no emitió una sola
señal**, porque el corpus tiene ~2 partidos por equipo. No es que falle:
no se la puede probar ahí. La regla de lenguaje de §35 sigue en pie.

### Lo que hay que hacer cuando entre la fecha siguiente

Volver a correr `--censo`. Si `faltas` en arg.1 llega a `n >= 6`, ahí
empieza a haber muestra de verdad para la capa 2 — y conviene correrla
con la regla exactamente como está, sin tocar un umbral.

## 43. Pronóstic: el producto se replantea desde arriba (2026-09-05)

Sale de una sesión entera de diseño con Lucas, no de una medición nueva.
La frase que la abrió: *"tenemos mucho análisis, muchos datos y muchas
herramientas, pero falta convertir eso en criterio, orientación y una
respuesta útil"*.

Vive en la rama **`pronostic`**. **No toca `actualizar.py`, el motor, ni
el contrato de `data/partidos.json`.** Detalle completo en
`docs/superpowers/specs/2026-09-05-pronostic-diseno.md`; en `CLAUDE.md`
está la tabla de archivos.

### El diagnóstico, y no era la interfaz

De los 32 análisis cargados entre el 1 y el 4 de septiembre, **29 tienen
`inclinacion: null`**; los otros 3 son `E`. Cero `L`, cero `V`. Como
`inclinacion` es la llave de `marcaDeValor()`, la app no marcó nada en
ninguno de los 32.

No es un bug: es el principio K de la skill, que prohíbe inclinar por
forma, tabla, localía o fuerza — el 90% de lo que hace legible un
partido. El caso que lo muestra entero es el veredicto de Estudiantes de
Río Cuarto–Sarmiento del 4/9, que **describe un partido desparejo y se
niega a concluirlo porque la conclusión es obvia**.

**La causa raíz: un solo campo hace dos trabajos incompatibles.** Es el
instrumento de medición (ortogonal a λ, para poder medir si la capa
cualitativa aporta) y es la opinión del producto. La regla que lo hace
bueno como instrumento es la que lo deja mudo como producto. §40 llegó al
mismo lugar desde el otro lado y dejó la pregunta abierta.

**La solución no toca el experimento.** `inclinacion` queda exactamente
igual. La opinión pasa a una capa nueva que puede coincidir con el
modelo — coincidir es confirmar, y confirmar es información.

### Tres decisiones de producto, tomadas por Lucas

1. **Arma boleta siempre, con la etiqueta puesta.** No espera a tener
   ventaja demostrada: dice qué jugaría, a qué precio, cuánto y qué la
   rompe, y dice con todas las letras cuándo no le gana al mercado.
   *La honestidad va en la etiqueta, no en el silencio.*
2. **Las dos superficies**: da la jugada **y** audita las ideas de Lucas.
3. **Cobertura completa**: populares y de estadística. No se achica a un
   nicho — un intento intermedio de hacerlo fue rechazado y con razón.

### Lo verificado de paso, que cambia cosas de acá

- **`medir_metamodelo.py:201` no calcula lo que dice.** La variable
  `volatilidad` computa `abs(p_local − p_visitante)` —desbalance— y el
  diccionario de la línea 149 la documenta como *"varianza reciente"*.
  La correlación −0.245 con el error absoluto es real, pero es en buena
  parte una propiedad de la escala, no un hallazgo. **§30 se lee mal si
  uno confía en el nombre.**
- **`cuotas.json` tiene el movimiento de la línea y nadie lo miraba.**
  123 partidos con fotos con hora. En Platense–Riestra el local abrió
  2.25 y cerró 2.65, el visitante 3.65 → 3.10: el mercado se movió fuerte
  hacia Riestra en tres días, coincidiendo con la rotación por
  Libertadores. Lo mismo en `props_jugadores.json`, con 12.221 líneas.
- **El goleador está a una línea.** `mercado_extra.py:159` baja solo
  remates, al arco y faltas de jugador; el comentario del propio archivo
  dice que en arg.1 queda `"Player To Score or Assist"` sin usar.
- **Bet365 le gana al modelo en las ocho líneas de gol** de los dos
  partidos del 4/9 que se revisaron: el mercado está por encima de
  nuestro número en todas, sistemáticamente.

### Estado al cierre

Construido y probado sin gastar API: `voz.md`, `datos.py` (12
herramientas), `motor.py`, `bot.py`, `informe.py`, `vigilante.py`,
`memoria.json`. **Nunca se corrió contra un modelo real** — no había
clave. Es lo primero que puede fallar.

Falta `cierre.py` (el que mide a Lucas contra el asesor), el goleador, y
mudarlo a un servidor.

### Lo que queda abierto, y es lo único que importa ahora

**Si la voz suena a experto.** Todo lo demás es ingeniería resuelta; eso
no se sabe hasta usarlo. Y no se cierra con otra auditoría: este diseño
encontró 10 huecos en dos pasadas y después 4 más en una tercera, lo que
prueba que auditar desde la silla no converge. **Lo cierra una fecha
real**, y cada vez que Lucas quede con ganas de algo que el asesor no
hizo, eso es un campo 23.

Nota de contexto que condiciona todo: **Lucas no paga API.** La ruta por
defecto es el nivel gratuito de Gemini, y su suscripción Gemini Pro
**no** da acceso a la API (es de interfaz de chat) — pero sí funciona
dentro de Antigravity, así que el modo de `experto/SIN_CLAVE.md` corre
con mejor modelo que el bot.
