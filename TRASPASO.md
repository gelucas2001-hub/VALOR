# VALOR — informe de traspaso

**Para:** la IA que arranque el proyecto de cero en una carpeta nueva.
**Escrito:** 2026-08-17. **Repo de origen:** `gelucas2001-hub/VALOR`.

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
2. **Validar `VIDA_MEDIA_DIAS` y `PRIOR_FUERZA`** con train/test split.
   Nunca se hizo; son valores razonables pero no medidos.
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

### El elemento firma — estado: sin resolver

El spec lo definía como "la pieza memorable de VALOR, todavía sin
encontrar". **Sigue sin encontrarse.**

Se intentó una idea: **el cupón de Prode** — las tres casillas de
resultado llenándose de tinta hasta la altura de nuestra probabilidad,
para leer la forma del partido antes que ninguna palabra. La idea es
razonable y sale del mundo del producto, pero **a Lucas no le convenció
en dos ejecuciones distintas**. La primera era literalmente invisible
(opacidad 0.085 contra fondo oscuro); la segunda, con más contraste,
tampoco lo convenció.

**Recomendación para quien siga: no insistas una tercera vez con el
cupón sin antes hacer un brainstorm real con variantes comparadas.** Dos
intentos fallidos sobre la misma idea es señal de replantear, no de
seguir puliendo.

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
5. **Plantel** — resumen corto de estilo y actualidad por equipo, desde
   `data/equipos.json`, más estadísticas del equipo.
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

## 10. El hueco más grande del producto

**`data/analisis.json` y `data/equipos.json` están vacíos** — solo
tienen el esquema.

Esto no es un detalle: **la regla de alineación depende de que haya
análisis cargado.** Sin contenido, la app funciona pero nunca marca
valor. Es un pronosticador honesto pero mudo en la mitad de su promesa.

**Y hay un riesgo de producto sin resolver:** la app promete "análisis de
expertos en lenguaje simple", y hoy eso es Lucas escribiendo a mano. Si
un día hay seis partidos y no tiene tiempo de escribir seis análisis, la
app vuelve a ser una calculadora bonita. **Esto hay que resolverlo antes
de que sea urgente.**

Existe una skill, `analisis-futbol-valor-json`, pensada para generar ese
contenido. **Está desalineada y hay que arreglarla antes de usarla:** su
esquema de salida (`hallazgo_principal`, `factores_clave`, `texto_corto`)
no coincide con el de `analisis.json` (`contexto`, `veredicto`), y no
produce una **lectura direccional**, que es justamente lo que la regla de
alineación necesita. Hay que agregarle un campo tipo `inclinacion`.

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

**Fase 1 — Diseño, ANTES de código**
5. **Invocar la skill de brainstorming.** No saltear este paso: saltearlo
   es exactamente lo que falló la vez pasada.
6. Producir **variantes comparadas** de la portada y del detalle, no una
   sola propuesta. Mostrárselas a Lucas como imágenes.
7. **Resolver el elemento firma con un brainstorm propio.** El cupón de
   Prode ya se intentó dos veces y no convenció.
8. Recién con una dirección elegida y aprobada, escribir el sistema de
   diseño: escala de espacio, escala tipográfica, estados, movimiento.

**Fase 2 — Reglas antes de pantallas**
9. Portar las reglas de recomendación de la sección 5 y **volver a
   barrerlas contra los datos reales del momento**. No copiar las
   constantes a ciegas: reproducir la medición.
10. Confirmar que el port a JavaScript da el mismo número que el
    cálculo en Python. Esa doble vía es lo que detecta errores
    numéricos silenciosos.

**Fase 3 — Interfaz**
11. Construirla pantalla por pantalla, mostrando **capturas reales
    enviadas al chat** después de cada una.
12. Verificar en navegador: sin errores de consola, sin desborde
    horizontal en 375px, `prefers-reduced-motion` respetado.

**Fase 4 — Contenido**
13. Arreglar la skill `analisis-futbol-valor-json` (agregarle
    `inclinacion`).
14. Cargar análisis real de al menos 3-4 partidos y confirmar que la
    marca de valor aparece.

**Fase 5 — Modelo (opcional, con tiempo)**
15. Calibrar `rho` para copas.
16. Validar `VIDA_MEDIA_DIAS` y `PRIOR_FUERZA` con train/test.

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
