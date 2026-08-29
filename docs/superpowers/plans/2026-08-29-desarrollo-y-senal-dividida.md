# `desarrollo` del partido y señal dividida — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la app VALOR "cuente el partido" agregando a cada análisis un campo `desarrollo` (cómo se va a jugar el partido) y que la escalera use su señal estructural (`senal`) para mostrar señal dividida cuando el análisis contradice a los mercados — sin tocar `inclinacion` ni `marcaDeValor`.

**Architecture:**
- **Frente 2 (contenido):** la skill `valor-analisis-inclinacion` emite un campo `desarrollo` por partido (objeto `{texto, senal}`). El expediente ya le entrega todo el material (no cambia su estructura). `index.html` lo renderiza como bloque propio en la pestaña Análisis. Es sobre todo contenido (SKILL.md) + un render.
- **Frente 3a (lógica):** `index.html` agrega una función `senalDividida(m)` (paralela a `divergen`) que detecta tensión entre `desarrollo.senal` y las opciones de la escalera (Goles/Ambos). El render muestra la señal dividida **visible y etiquetada** — nunca oculta ni borra valor del modelo.

**Tech Stack:** Python 3 (estándar, sin dependencias) para `expediente.py`; JS vanilla en `index.html` (SPA, sin build); Node para `test_alineacion.js`; la skill es un markdown en `.claude/skills/`.

**Spec:** `docs/superpowers/specs/2026-08-29-desarrollo-del-partido-y-senal-dividida.md`

## Global Constraints

- **Nunca autorizado en el lado del análisis:** la skill no recibe ni usa λ, cuotas, EV, xG (`expediente.py` los excluye; el `senal` sale de la lectura del partido, no del mercado).
- **`incierto` es la salida por omisión de `senal`** y es correcta; nunca forzar un valor sin base.
- **`desarrollo.senal` describe el partido, no el mercado:** léxico cerrado (`ritmo_goleador`: alto/bajo/incierto; `estructura`: abierto/trabado/neutral/incierto; `ambos_marcan`: probable/poco_probable/incierto). Sin etiquetas `over`/`under` en la skill.
- **`ritmo_goleador: bajo` y `estructura: trabado` modulan igual** (solo goles altos, líneas ≥ 2.5). Sin filtro más fuerte para `trabado`; sin extrapolaciones a remates/córners/llegadas.
- **Nunca borrar valor del modelo por narrativa:** la contradicción es señal dividida **visible y etiquetada**, no un silenciamiento.
- **`inclinacion` y `marcaDeValor` no cambian:** siguen dependiendo solo de `inclinacion`; la dirección sigue alineándose como hoy.
- **No tocar la región `INICIO RESOLUCION`** de `index.html` (la lee `test_registro.js`).
- **No cambiar el contrato de `data/partidos.json`** ni de `data/analisis.json` retroactivamente: los análisis viejos quedan intactos y la app sin `desarrollo` se ve como hoy.
- **Convención de archivos del repo:** pruebas corriendo vía `node test_*.js` / `python test_*.py`; sprite de tests de `index.html` carga la lógica recortando antes de `RENDER Y RUTEO` (ver `cargarLogica()`), así que las funciones nuevas en la lógica quedan exportables.

---

### Task 1: Skill — documentar el campo `desarrollo`

**Files:**
- Modify: `.claude/skills/valor-analisis-inclinacion/SKILL.md`

**Interfaces:**
- Consumes: nada (doc).
- Produces: la definición canónica del campo `desarrollo` que Tasks 2-4 asumen. Task 4 depende del léxico cerrado que se define acá.

Esta tarea define el contrato del campo; no hay test automático de la skill (se verifica a mano). El resto del plan asume este contrato.

- [ ] **Step 1: Agregar `desarrollo` a la forma JSON de salida (sección 4)**

En la sección 4, el ejemplo de salida (bloque JSON con `local`/`visitante`/`contexto`/`veredicto`) se extiende con `desarrollo`. Insertar después de `veredicto`:

```json
{
  "espn401841517": {
    "actualizado": "AAAA-MM-DD",
    "inclinacion": "L",
    "local": "Cómo juega y cómo llega el local.",
    "visitante": "Lo mismo del visitante.",
    "contexto": "Lo que cruza a los dos.",
    "veredicto": "Lectura final: hacia dónde inclina.",
    "desarrollo": {
      "texto": "Se espera un partido trabado de pocas llegadas; el local va a esperar tener la pelota y el visitante a salir de contra.",
      "senal": {
        "ritmo_goleador": "bajo",
        "estructura": "trabado",
        "ambos_marcan": "incierto"
      }
    }
  }
}
```

- [ ] **Step 2: Documentar el significado y las reglas del campo**

Agregar, justo después del ejemplo (tras el texto que explica `veredicto`), un sub-bloque "`desarrollo` — el desarrollo esperado":

- Qué es: **único por partido** — describe la interacción de los dos equipos (cómo se va a jugar), no dos descripciones separadas. 2-4 frases en `texto`, tono de analista deportivo, sin jerga cuantitativa.
- Guiones internos (no estructura visible en el output) — cuatro dimensiones: (1) control territorial/posesión; (2) transiciones y espacios; (3) ritmo probable; (4) factores capaces de alterar el guion.
- **Sin guion cerrado:** si la evidencia es insuficiente o contradictoria, expresá la incertidumbre explícitamente ("sin base para afirmar el desarrollo", "no se puede sostener un ritmo abierto") en vez de rellenar con narrativa genérica.
- `senal` — qué significa y el léxico cerrado (tabla):

| campo | valores | para qué sirve |
|---|---|---|
| `ritmo_goleador` | alto / bajo / incierto | señal de cuántos goles esperar |
| `estructura` | abierto / trabado / neutral / incierto | carácter del partido |
| `ambos_marcan` | probable / poco_probable / incierto | si van a convertir los dos |

- **`incierto` es la salida por omisión y es correcta**: sin base, no se fuerza. `bajo` y `trabado` tienen hoy el mismo efecto (solo tensión con mercados de goles altos); no extrapolés `trabado` a remates/córners/llegadas (relación no es equivalencia, se validaría empíricamente en el futuro).
- **Nunca mirar cuotas ni λ para el `senal`**: sale de la misma lectura que el `texto` (forma, sede, plantel, h2h). Violar esto rompe la independencia de la marca dorada.

- [ ] **Step 3: Agregar la entrada a la auto-verificación (sección 6)**

En la lista de casillas de la sección 6, agregar dos (en el estilo de las existentes, una línea cada una):

```text
- [ ] `desarrollo`· ¿es una dirección camuflada? Si nombrás a un ganador, va en `veredicto`/`inclinacion`, no en `desarrollo`.
- [ ] `desarrollo`· ¿estás vendiendo un guion cerrado inventado? Si no hay base para afirmar el desarrollo, decilo con incertidumbre — `incierto`/explicitarlo es correcto, la narrativa convincente no.
```

- [ ] **Step 4: Verificar coherencia del archivo**

Run: `git diff --stat .claude/skills/valor-analisis-inclinacion/SKILL.md`
Expected: solo los cambios de la sección 4 (ejemplo + bloque nuevo) y de la sección 6 (dos casillas). No se cambia la versión del encabezado (`v2.5`).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/valor-analisis-inclinacion/SKILL.md
git commit -m "skill: campo desarrollo (texto + senal) en el analisis de partido"
```

---

### Task 2: Expediente — `_leeme` actualizado (documentación)

**Files:**
- Modify: `expediente.py:263` (el string `_leeme`)

**Interfaces:**
- Consumes: nada.
- Produces: la skill sabe que el expediente cubre el `desarrollo`; el contrato del expediente no cambia (misma estructura, mismos campos entra/sale).

El `desarrollo` se escribe con el material que el expediente ya entrega, así que `expediente.py` **no cambia su estructura**. Solo se actualiza la nota `_leeme` para que la skill sepa que debe producir el desarrollo.

- [ ] **Step 1: Editar `_leeme`**

En `expediente.py`, el string `_leeme` (línea ~263) termina con la explicación de `plantel`. Agregar una frase final que indique que el análisis debe incluir un `desarrollo` (cómo se va a jugar el partido) y su `senal`, con la misma regla de independencia. Texto sugerido:

```text
" Leé también para `desarrollo`: describe cómo se VA a jugar el partido (quién tendrá la pelota, abierto o trabado, ritmo, qué puede alterar el guion) — SIEMPRE desde el expediente (forma, sede, plantel, h2h), nunca desde el mercado. Y `desarrollo.senal` usa el léxico cerrado: ritmo_goleador alto|bajo|incierto, estructura abierto|trabado|neutral|incierto, ambos_marcan probable|poco_probable|incierto; cuando no haya base, `incierto`."
```

- [ ] **Step 2: Verificar que el expediente sigue andando**

Run: `python test_expediente.py`
Expected: todos los tests pasan (el `_leeme` es texto; no debe romper la estructura del expediente). Los tests existentes verifican que no se filtre el modelo y que llegue el material — no deben fallar.

- [ ] **Step 3: Commit**

```bash
git add expediente.py
git commit -m "expediente: _leeme documenta el campo desarrollo y su senal"
```

---

### Task 3: Frontend — render del bloque `desarrollo` en Análisis

**Files:**
- Modify: `index.html` (`tabAnalisis`, ~líneas 2091-2121)
- Test: `test_alineacion.js` (agregar casos cerca de `analisisCompleto`, ~línea 635)

**Interfaces:**
- Consumes: `ANALISIS[m.id].desarrollo` (objeto `{texto, senal}`, o ausente — borrado de `_schema` ya manejado en index.html:3631).
- Produces: la pestaña Análisis muestra `desarrollo.texto` como bloque propio. Los análisis viejos (sin `desarrollo`) no cambian.

- [ ] **Step 1: Escribir los tests que definen el render**

En `test_alineacion.js`, cerca de `analisisCompleto` (~línea 635), agregar dos tests. Primero necesitás ver cómo está definido `claro` (partido de ejemplo) y `analisisCompleto` — mirá las líneas 620-680 antes de escribir.

```js
test("el analisis muestra el bloque de desarrollo cuando existe", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {
    actualizado: "2026-08-29", inclinacion: "L",
    desarrollo: {texto: "Partido trabado de pocas llegadas.", senal: {ritmo_goleador:"bajo", estructura:"trabado", ambos_marcan:"incierto"}},
  }});
  const h = L.tabAnalisis(claro);
  si(!h.includes("Partido trabado de pocas llegadas."), "el texto de desarrollo no se muestra");
});

test("los analisis viejos (sin desarrollo) no muestran el bloque ni rompen", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {
    actualizado: "2026-08-18", inclinacion: "V", contexto: "Solo contexto.",
  }});
  const h = L.tabAnalisis(claro);
  si(h.includes("SIN CARGAR"), "con contexto + inclinacion sigue contando como cargado");
});
```

Fijate cómo se escriben los helpers `test`/`si`/`igual`/`cierto` en este archivo (líneas 52-60) y usá los mismos (`si` para condicional con mensaje, o el patrón que ya usa el archivo). `claro` es un partido del snapshot con mercado real — mirá cómo se define en las líneas ~85-90.

- [ ] **Step 2: Correr los tests, deben FALLAR (el render no existe)**

Run: `node test_alineacion.js`
Expected: los tests nuevos FALLAN (el texto de desarrollo no aparece en `tabAnalisis`).

- [ ] **Step 3: Implementar el render de `desarrollo`**

En `index.html` `tabAnalisis`, dentro de la rama "NUESTRA NOTA" (donde se muestran `local`/`visitante`/`contexto`/`veredicto`), después del bloque de `veredicto` (línea ~2106) y antes del bloque "Hacia dónde inclina" (línea ~2111), insertar el bloque de desarrollo. La variable de análisis ya es `const a = ANALISIS[m.id]` (línea 2060). Insertar:

```js
  const des = a.desarrollo;
  if(des && des.texto){
    h += `<div class="rot"><span>El desarrollo</span></div><p class="prosa">${esc_(des.texto)}</p>`;
  }
```

Nota: `des.texto` se escapa con `esc_` (ya definido) por seguridad de XSS, igual que los demás campos de prosa.

- [ ] **Step 4: Correr los tests, deben PASAR**

Run: `node test_alineacion.js`
Expected: los tests nuevos PASAN y ningún test existente falla (regresión cero).

- [ ] **Step 5: Verificar el render a mano con un análisis real**

Cargar la app localmente y abrir un partido. Como `analisis.json` real no tiene `desarrollo` todavía, usá la rama SIN CARGA como referencia de que no rompe. (Paso de verificación manual — los tests de Node cubren el render con datos simulados.)

- [ ] **Step 6: Commit**

```bash
git add index.html test_alineacion.js
git commit -m "frontend: muestra el bloque desarrollo en la pestana Analisis"
```

---

### Task 4: Frontend — `senalDividida` y render de señal dividida en la escalera

**Files:**
- Modify: `index.html` (`escaleera`→escalera/otrosMercados/tabPronosticos; nueva función cerca de `divergen` ~1568)
- Test: `test_alineacion.js`

**Interfaces:**
- Consumes: `escalera(m)` (retorna array de `{franja, op, ventaja, valor}`; `op` tiene `.fam` "Goles"/"Ambos"/"Resultado", `.lado` "over"/"under", `.linea`), `otrosMercados(m)` (array de `{op, ventaja, esVal}`), `lectura(m).lean`, `ANALISIS[id].desarrollo.senal`.
- Produces: `senalDividida(m)` — devuelve `null` si no hay análisis o no hay tensión; devuelve un objeto descriptivo si la `senal` contradice a las opciones que la escalera/otrosMercados considerarían. `marcaDeValor` y la dirección no cambian.

**Contrato de `senalDividida(m)`** (lo que Task 5 usa):

```js
/*
 * Devuelve null cuando no hay tensión (sin análisis, senal incierto/ausente,
 * o senales coherentes con las opciones). Devuelve un objeto cuando la senal
 * del desarrollo contradice a mercados de goles/ambos:
 *   { fenom: "goles", dir: "pocos",   // senal indica pocos goles
 *     opciones: [ids de opciones de goles altos en conflicto] }
 *   { fenom: "ambos", dir: "no",       // senal indica que no marcan ambos
 *     opciones: [ids de btts en conflicto] }
 */
function senalDividida(m){
  const a = ANALISIS[m.id];
  const s = a && a.desarrollo && a.desarrollo.senal;
  if(!s) return null;
  if(s.ritmo_goleador === "bajo" || s.estructura === "trabado"){
    const ops = escalera(m).map(f=> f.op).filter(Boolean)
      .filter(o=> o.fam==="Goles" && o.lado==="over" && o.linea>=2.5);
    if(ops.length) return {fenom:"goles", dir:"pocos", opciones: ops.map(o=>o.id)};
  }
  if(s.ambos_marcan === "poco_probable"){
    const ops = escalera(m).map(f=> f.op).filter(Boolean)
      .filter(o=> o.id==="btts_si");
    if(ops.length) return {fenom:"ambos", dir:"no", opciones: ops.map(o=>o.id)};
  }
  return null;
}
```

La fórmula de detección (goles altos = `lado==="over" && linea>=2.5`; ambos = `btts_si`) es la traducción del spec. La exponés para tests.

- [ ] **Step 1: Escribir los tests**

Agregar al `test_alineacion.js`, después de los tests de `divergen` (~línea 455), usando el patrón de `L.escalera`/`L.cargar` ya existente. Necesitás un partido con mercado real para que haya opciones de Goles; usá `claro` (definido ~85). Los tests:

```js
test("senalDividida() sin senal (o sin analisis) devuelve null", ()=>{
  L.cargar(PARTIDOS, {});
  cierto(!L.senalDividida(claro), "sin analisis:");
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"x", inclinacion:"L", desarrollo:{texto:"t.", senal:{ritmo_goleador:"incierto", estructura:"neutral", ambos_marcan:"incierto"}}}});
  igual(L.senalDividida(claro), null, "senal incierto:");
});

test("senalDividida() con ritmo bajo detecta opciones de goles altos", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"x", inclinacion:"L",
    desarrollo:{texto:"trabado", senal:{ritmo_goleador:"bajo", estructura:"trabado", ambos_marcan:"incierto"}}}});
  const sd = L.senalDividida(claro);
  cierto(sd && sd.fenom==="goles", "deberia marcar senal de goles");
  cierto(sd.opciones.length >= 1, "deberia haber al menos una opcion de goles altos en conflicto");
});

test("senalDividida() con ambos poco probable detecta btts_si", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"x", inclinacion:"L",
    desarrollo:{texto:"cerrado", senal:{ritmo_goleador:"incierto", estructura:"neutral", ambos_marcan:"poco_probable"}}}});
  const sd = L.senalDividida(claro);
  cierto(sd && sd.fenom==="ambos", "deberia marcar senal de ambos");
  cierto(sd.opciones.includes("btts_si"), "la opcion en conflicto es ambos marcan");
});

test("senalDividida() nunca toca marcaDeValor (sigue dependiendo solo de inclinacion)", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"x", inclinacion:"L",
    desarrollo:{texto:"x", senal:{ritmo_goleador:"bajo", estructura:"trabado", ambos_marcan:"poco_probable"}}}});
  // marcaDeValor sigue siendo direccion pura; la senal no lo cambia
  const m = L.marcaDeValor(claro);
  cierto(m==="L" || m===null, "marca no se rompe");
});
```

Si `claro` no genera opciones de goles altos `over` con `linea>=2.5` en su escalera, ajustá el `senalDividida` de detección con el `mercad` real del snapshot, o elegí en el test un partido del snapshot que sí tenga opciones de goles con línea ≥2.5. Verificá qué opciones produce `L.escalera(claro)` antes de fijar el test (corré `node` con un console.log).

- [ ] **Step 2: Correr, deben FALLAR**

Run: `node test_alineacion.js`
Expected: los tests de `senalDividida` FALLAN (función no exportada / no definida). Los demás pasan.

- [ ] **Step 3: Exportar y definir la función**

En `test_alineacion.js`, agregar `senalDividida` a la lista de `exportar({...})` (línea ~32). En `index.html`, definir la función justo después de `divergen` (línea ~1573), con el cuerpo del contrato de arriba.

- [ ] **Step 4: Correr, deben PASAR**

Run: `node test_alineacion.js`
Expected: los nuevos tests pasan; regresión cero en el resto.

- [ ] **Step 5: Render de la señal dividida visible en `tabPronosticos`**

En `tabPronosticos` (línea ~2140), donde ya se usa `divergen(m)`, agregar un aviso de señal dividida por desarrollo. Después del bloque de `divergen` (ya cerrado con `if(dv){...}`), agregar:

```js
    const sd = senalDividida(m);
    if(sd){
      const que = sd.fenom==="goles"
        ? "nuestra lectura del desarrollo dice que va a ser un partido de pocos goles"
        : "nuestra lectura del desarrollo dice que es poco probable que marquen los dos";
      h += `<div class="nota">El modelo ve ventaja en opciones de
        ${sd.fenom==="goles" ? "goles altos" : "ambos marcan"}, pero ${que}.
        Por eso no te las marcamos en dorado: la lectura del desarrollo no
        acompaña, y no recomendamos sobre algo que contradice nuestra propia
        lectura. Quedan acá visibles por si querés decidir con los números y la
        lectura a la vista.</div>`;
    }
```

Esto cumple la regla del spec: **visible y etiquetada**, no oculta, no borra el valor del modelo (las opciones siguen en la escalera, solo no marcadas en dorado — el `marcar` de cada paso ya exige `valar`/`valor`, y acá se le quita el dorado por la señal dividida pero se muestra el aviso).

- [ ] **Step 6: Ajustar el dorado en la escalera por señal dividida**

En `tabPronosticos`, la variable `marcar` de cada paso (línea ~2162 `const marcar = op && valor && hay;`) se endurece para no marcar en dorado lo que la señal dividida descalifica:

```js
    const sdAnula = senalDividida(m);
    ...
    const marcar = op && valor && hay && !(sdAnula && sdAnula.opciones.includes(op.id));
```

O, más limpio: calcular `const sd = senalDividida(m)` una vez arriba (con el bloque ya existente del paso 5) y referenciarla. Asegurate de que la señal dividida **solo quite el dorado, nunca oculte la fila**.

- [ ] **Step 7: Correr tests, PASAN + sin regresión**

Run: `node test_alineacion.js`
Expected: los tests de `senalDividida` y los de render pasan; regresión cero.

- [ ] **Step 8: Verificar regresión de los últimos 5 tests de escalera + otrosMercados**

Run: `node test_alineacion.js`
Expected: los tests existentes de escalera/otrosMercados/marcaDeValor pasan (la señal dividida no rompe el flujo normal cuando no hay `senal`).

- [ ] **Step 9: Commit**

```bash
git add index.html test_alineacion.js
git commit -m "frontend: senal dividida por desarrollo visible en la escalera"
```

---

### Task 5: `analisis.json` — `_schema` documentándo `desarrollo`

**Files:**
- Modify: `data/analisis.json` (solo el campo `_schema`)

**Interfaces:**
- Consumes: nada.
- Produces: el contrato del `_schema` documenta `desarrollo`; los 19 análisis reales no se tocan.

`data/analisis.json` tiene un `_schema` con `_comentario`/`_inclinacion`/`_ejemplo` (líneas 2-6+). Agregar documentación del campo `desarrollo` y su `senal`. Nota: el frontend borra `_schema` al cargar (index.html:3631), así que esto es solo documentación humana — no afecta runtime.

- [ ] **Step 1: Agregar al `_schema`**

Dentro de `_schema`, agregar una entrada `_desarrollo` documentando el campo. Formato libre en el estilo de `_inclinacion`/`_ejemplo` existentes:

```json
"_desarrollo": "Campo nuevo (2026-08-29). Objeto {texto, senal}. texto: como se VA a jugar el partido (quien tendra la pelota, abierto o trabado, ritmo, que puede alterar el guion), unico por partido, sin numeros del modelo ni del mercado, incertidumbre explicita. senal: {ritmo_goleador: alto|bajo|incierto, estructura: abierto|trabado|neutral|incierto, ambos_marcan: probable|poco_probable|incierto}. Incierto = sin base, correcto. No toca inclinacion ni marcaDeValor.",
```

- [ ] **Step 2: Verificar que el JSON es válido y la app no rompe**

Run: `python -c "import json; json.load(open('data/analisis.json', encoding='utf-8')); print('OK')"`
Expected: `OK`. (El frontend borra `_schema`, así que la app se comporta igual.)

- [ ] **Step 3: Commit**

```bash
git add data/analisis.json
git commit -m "analisis.json: _schema documenta el campo desarrollo"
```

---

### Task 6: Verificación integral

**Files:**
- Test: conjunto completo

**Interfaces:**
- Consumes: todas las tareas anteriores.

- [ ] **Step 1: Correr toda la suite de la app**

Run: `node test_alineacion.js; node test_registro.js; node test_probabilidad.js`
Expected: todo verde.

- [ ] **Step 2: Correr la suite Python que toca el expediente**

Run: `python test_expediente.py; python test_pronosticos.py`
Expected: verde. (`doble_via.py` no aplica: no se tocó el motor.)

- [ ] **Step 3: Verificar contra una marca real**

Cargar `index.html` localmente. Verificar:
- Sin análisis (`analisis.json` sin `desarrollo` cargado) → la app se ve como hoy.
- Un partido donde la `senal` fuera `bajo`/`trabado` + opciones de goles altos con valor → se muestra el aviso de señal dividida y no se marca en dorado esa opción.
- `marcaDeValor` en portada/tarjeta sigue exactamente como antes (solo `inclinacion`).

- [ ] **Step 4: Commit final** (si algo quedó sin commitear)

```bash
git status
git add -A
git commit -m "desarrollo y senal dividida: verificacion integral"
```

---

## Self-Review

**1. Spec coverage:**
- Frente 2 (campo `desarrollo`, bloque propio, único, sin números modelo/mercado, sin guion cerrado, 4 dimensiones): Task 1 (skill), Task 2 (expediente _leeme), Task 3 (render), Task 5 (_schema). ✓
- Frente 3a (senal estructural, léxico de partido, señal dividida visible y etiquetada, no ocultar ni borrar valor, incierto por omisión, bajo==trabado, goles altos >=2.5): Task 4. ✓
- `marcaDeValor`/`inclinacion` intocadas: Task 4 tests + Task 6 verificación. ✓
- Análisis viejos intactos: Task 3 y Task 5 (no se tocan los 19). ✓

**2. Placeholder scan:** ningún paso tiene "TBD"/"implementar después". Todos incluyen el código. ✓

**3. Type consistency:**
- `desarrollo` = `{texto, senal}` consistente en Task 1, 2, 3, 4, 5. ✓
- `senalDividida(m)` contrato consistente (null u `{fenom, dir, opciones}`) en Task 4 test y definición. ✓
- `op.fam`/`op.lado`/`op.linea` usados en `senalDividida` coinciden con `mercados()` (index.html:1231-1235). ✓
