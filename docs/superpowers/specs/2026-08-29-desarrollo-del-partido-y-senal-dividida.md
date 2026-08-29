# VALOR — `desarrollo` del partido y señal dividida

Fecha: 2026-08-29
Estado: diseño aprobado por Lucas (brainstorming). Pendiente de plan de implementación.
Alcance: Frente 2 (expediente + skill con `desarrollo`) y Frente 3a (la escalera usa la señal del `desarrollo` para la "señal dividida"). Frente 1 (acumular historia de estadísticas por equipo en Sudamérica) quedó **pausado** por decisión de Lucas.

## Por qué

La app VALOR se sentía genérica: en un partido analizado decía *quién* podía ganar (veredicto, dirección) y *cómo llega cada uno* (local/visitante), pero no le contaba al usuario **cómo se va a jugar el partido** — qué tipo de desarrollo esperar. Un producto que se presenta como asesor experto tiene que poder describir el *cómo*, no solo el *quién*. Y cuando la descripción de ese desarrollo contradice lo que los números marcan como valor, hay que decirlo — no ocultarlo (error de silencio) ni borrar el valor del modelo (error metodológico).

Objetivo: que la app actúe como asesor experto que "cuenta el partido" con datos reales y coherente con las apuestas que recomienda, sin sacrificar la premisa central del producto: que la lectura humana y la del modelo son lecturas separadas, y la marca de valor sale de la humana.

## Qué NO toca esto

- **El contrato de `data/partidos.json`** (AGENTS.md): no se cambia.
- **`actualizar.py` como motor / la regla de alineación de la dirección:** `inclinacion` sigue siendo la única fuente de la dirección con la que se alinea y de `marcaDeValor`. El campo nuevo no la toca.
- **La independencia del análisis:** la skill sigue sin recibir λ, cuotas, EV, xG. El recorte estructural de `expediente.py` se mantiene.
- **Los análisis ya cargados (19 en `data/analisis.json`):** quedan intactos; sin el campo nuevo, la app se comporta como hoy.

## Frente 2 — el campo `desarrollo`

### El problema

Hoy la app analizada dice: veredicto (dirección), local/visitante (cómo juega y llega cada uno), contexto (lo que cruza). Falta la capa que describe **el desarrollo esperado**: quién tendrá la pelota, si el partido será abierto o trabado, qué ritmo, qué puede alterar el guion. Es la diferencia entre "qué esperar como resultado" y "qué esperar como partido".

### La solución

Un campo nuevo **`desarrollo`**, **único por partido** (representa la interacción de los dos equipos, no dos descripciones individuales), en la salida JSON de la skill, en paralelo a `local`/`visitante`/`contexto`/`veredicto`. Un bloque propio en la pestaña Análisis.

Condiciones fijadas por Lucas (todas incorporadas al diseño):

1. **Capa independiente**: describe el desarrollo esperado, separada de `veredicto`, sin acceso a números del modelo ni del mercado, sin modificar la regla actual de `inclinacion`.
2. **Sin guion cerrado**: cuando la evidencia sea insuficiente o contradictoria, expresa incertidumbre explícitamente en lugar de rellenar con narrativa genérica. "No hay base para afirmar el desarrollo" es una salida válida.
3. **Bloque propio** en Análisis; los históricos no lo muestran si no existe.
4. **Único por partido.**

### Contenido y límites del texto `desarrollo`

2-4 frases, tono de analista deportivo de TV, sin jerga cuantitativa. Guía interna (no estructura visible) apoyada en cuatro dimensiones:

1. **Control territorial / posesión** — quién espera tener la pelota, dónde va a pasar el partido.
2. **Transiciones y espacios** — quién sale a la contra, qué espacios deja, de qué vive cada uno.
3. **Ritmo probable** — abierto o trabado, pocas o muchas llegadas.
4. **Factores capaces de alterar el guion** — a quién le sirve el empate, si uno necesita sí o sí el resultado, expulsiones/condiciones.

Lo que puede usar: todo lo que el expediente ya trae y la skill ya procesa (forma con marcadores y fechas, sede, localía, tabla respetando el aviso de zonas, h2h, plantel con `peso_goles`/posiciones). Aplica los principios existentes: A (inventar=no), B (muestra chica), I (expediente > research), P (el factor con rastro), E (independencia del modelo).

### Cambios por archivo (Frente 2)

- **`expediente.py`**: el expediente es agnóstico de los campos que escribe la skill. Solo se actualiza `_leeme` (una línea sobre `desarrollo`) para que la skill sepa qué se espera. `EXPEDIENTE`/`EXCLUIDOS` no cambian: el desarrollo se escribe con lo que ya viaja.
- **`SKILL.md`** (`.claude/skills/valor-analisis-inclinacion/`): agregar el campo a la forma de salida (sección 4), su definición y delimitaciones, y una entrada en la auto-verificación (sección 6): "¿`desarrollo` es una dirección camuflada o un guion cerrado inventado?" y la regla de incertidumbre explícita.
- **`data/analisis.json`**: el campo nuevo convive con los viejos. Se actualiza `_schema` documentando `desarrollo`. Los 19 análisis existentes no se tocan.
- **`index.html` pestaña Análisis** (`tabAnalisis`): renderizar `desarrollo` como bloque propio cuando exista. Si no viene, nada extra.

## Frente 3a — señal dividida por desarrollo en la escalera

### El problema

Hoy hay dos mecanismos de señal dividida, ambos limitados:

- `divergen(m)` (index.html:1568): solo compara **direcciones** (L/E/V) y solo cuando la humana no es `null`.
- Regla de alineación `contradice` (index.html:1428): descarta lo que contradice la **dirección**.

Ninguno ve el **carácter del desarrollo**. Un partido puede tener dirección clara (modelo y análisis coinciden en quién gana) pero desarrollo contradictorio con los mercados que la escalera marca (ej: ganan los dos en que gana el local, pero el análisis describe un partido trabado de pocas llegadas mientras la escalera marca *Más de 2.5*).

### La solución

`desarrollo` lleva una **señal estructural** que la escalera puede leer. Reglas de diseño:

- **La señal describe el partido, no el mercado.** No se usan etiquetas tipo `over`/`under` (vocabulario del mercado) en la skill: son la skill pensando el partido como apuesta. La señal describe características del partido y la escalera **traduce** a coherencia/contradicción con cada mercado.
- **`incierto` es la salida por omisión y es correcta.** Sin base, no se fuerza. Prudente antes que convincente (prioridad de Lucas).
- **Misma modulación inicial para "partido de pocos goles" y "trabado".** `ritmo_goleador: bajo` y `estructura: trabado` afectan igual (solo la coherencia con mercados de goles altos). Sin filtro más fuerte para `trabado`, sin extrapolaciones automáticas a remates/córners/llegadas (relaciones no son equivalencias; validarlas empíricamente queda como trabajo futuro documentado, no implementado).
- **No borra valor del modelo por narrativa.** Reemplazar un sistema cuantitativo imperfecto por intuición lingüística no medible sería un error metodológico (misma regla del repo: un ajuste se aprueba por medición). Por eso la contradicción es **visible y etiquetada**, nunca un silenciamiento.

### Esquema de la señal

```json
"desarrollo": {
  "texto": "Se espera un partido trabado...",
  "senal": {
    "ritmo_goleador": "alto" | "bajo" | "incierto",
    "estructura":     "abierto" | "trabado" | "neutral" | "incierto",
    "ambos_marcan":   "probable" | "poco_probable" | "incierto"
  }
}
```

| campo | valores | qué traduce la escalera |
|---|---|---|
| `ritmo_goleador` | alto / bajo / incierto | `bajo` → entra en tensión con mercados de **goles altos** (líneas ≥2.5) |
| `estructura` | abierto / trabado / neutral / incierto | `trabado` → mismo efecto que `ritmo: bajo`; `abierto` → coherente con mercados de goles |
| `ambos_marcan` | probable / poco_probable / incierto | `poco_probable` → entra en tensión con **ambos marcan** |

`senal` nace de la misma lectura que `texto` (forma, sede, plantel, h2h, cómo juega cada uno) — **nunca de mirar cuotas ni λ**. Igual deudo con los principios A/B/I/P.

### Jerarquía de comportamiento en la escalera

Para cada opción de la escalera (y de Otros Mercados):

| caso | comportamiento |
|---|---|
| **Sin contradicción** (vacío, señales coherentes o `incierto`) | recomendación normal (como hoy). |
| **Valor cuantitativo + `senal` contradictoria** | **Señal dividida visible y etiquetada**: la opción NO se marca en dorado, pero se muestra con aviso (mismo patrón que `divergen`): "el modelo ve ventaja acá, nuestra lectura del desarrollo dice X". No se oculta. |
| **Sin análisis, o `senal` incierto / sin campo** | comportamiento de hoy, honesto, sin modular nada. |

### Cambios por archivo (Frente 3a)

- **`SKILL.md`**: documentar `desarrollo.senal` (léxico cerrado, `incierto` por omisión, regla de independencia, sin extrapolaciones).
- **`index.html`**:
  - `contradice` no cambia de firma para la dirección. Se agrega la lógica de **señal dividida por `senal`** como una capa aparte (una función nueva tipo `senalDividida(m)`, paralela a `divergen`) que evaluúa goles/ambos contra `senal`.
  - En `tabPronosticos` (render de escalera) y `tabAnalisis`, mostrar la señal dividida etiquetada cuando aplique (aviso, no ocultar).
  - `marcaDeValor` no cambia: sigue dependiendo solo de `inclinacion`.
- **Tests**: `test_alineacion.js` se extiende con casos de `senal` (contradicción visible, no ocultamiento; `incierto` = sin efecto; `marcaDeValor` intocada).

## Regla de alineación / premisa de marca — sin cambios

- `inclinacion` sigue saliendo solo de `veredicto` y sigue siendo la única fuente de la marca de valor (`marcaDeValor`, portada y tarjeta).
- `senal` modula solo la coherencia de los mercados de **goles y ambos** en la escalera — que no opinan sobre quién gana — así que no colisiona con la alineación de dirección.
- La independencia del análisis se preserva en todo momento.

## Criterios de éxito (para verificar en implementación)

1. Cargar un análisis con `desarrollo` → la pestaña Análisis muestra el bloque propio.
2. Un análisis con `senal` contradictoria a un marcador de la escalera → se muestra señal dividida etiquetada, no se oculta, no se marca en dorado.
3. `senal` `incierto` o ausente → sin efecto sobre la escalera (como hoy).
4. `marcaDeValor` depende solo de `inclinacion` (tests de alineación pasan).
5. `test_alineacion.js`, `test_expediente.py` y `test_registro.js` / `test_pronosticos.py` pasan. (`doble_via.py` no aplica: no se toca el motor.)
6. Los 19 análisis existentes siguen renderizando sin `desarrollo`.

## Fuera de alcance (documentado como futuro)

- **Frente 1** (acumular historia de estadísticas por equipo para Sudamérica): pausado. Relectura mostró que `cache_resumen` ya persiste entre corridas y es la materia prima natural — decidir enfoque si se retoma.
- **Filtro más fuerte para `trabado`** y extrapolación de `ritmo_goleador`/`estructura` a remates, córners, llegadas: requeriría validación empírica (relaciones no son equivalencias). No se implementa.
