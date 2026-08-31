/* ══════════════════════════════════════════════════════════════════
   TEST DEL CONTRATO DE EJES

   Corré:  node test_ejes.js

   Extrae la región marcada de `index.html` — no una copia — igual que
   `test_registro.js`. Lo que se prueba acá no es cuánto sabe el modelo:
   es que la app NO PUEDA declarar más confianza de la que hay medida.

   Las dos reglas duras de la arquitectura (TRASPASO §17):

     1. Un eje sin `medido_por` no puede declarar más que `sin_medir`.
     2. Solo `confianza === "con_plata"` puede llevar una apuesta, que
        es lo único que después se pinta de mostaza.

   Sin estos tests, las dos reglas son disciplina — o sea, se pierden
   la primera vez que alguien agrega un eje con apuro. Con ellos, son
   estructura: para saltearlas hay que romper un test a propósito.
   ══════════════════════════════════════════════════════════════════ */

const fs = require("fs");
const path = require("path");

const RAIZ = __dirname;
const INICIO = "/* ==== INICIO EJES ==== */";
const FIN    = "/* ==== FIN EJES ==== */";

function cargarEjes(){
  const html = fs.readFileSync(path.join(RAIZ, "index.html"), "utf8");
  const a = html.indexOf(INICIO), b = html.indexOf(FIN);
  if(a < 0 || b < 0)
    throw new Error(`index.html no tiene la región marcada ${INICIO} … ${FIN}`);
  const src = html.slice(a + INICIO.length, b);
  const salida = {};
  new Function("exportar", src + `
    exportar({CONFIANZAS, CONTRATO, MEDICIONES, sellar, construirEjes});
  `)(o => Object.assign(salida, o));
  return salida;
}

let ok = 0, mal = 0;
const test = (nombre, fn) => {
  try { fn(); console.log("  ok   " + nombre); ok++; }
  catch(e){ console.log("  FALLA " + nombre + "\n         " + e.message); mal++; }
};
const igual = (a, b, msg) => {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if(A !== B) throw new Error(`${msg||""} esperaba ${B}, dio ${A}`);
};
const cierto = (v, msg) => { if(!v) throw new Error(msg || "esperaba verdadero"); };

const { CONFIANZAS, CONTRATO, MEDICIONES, sellar, construirEjes } = cargarEjes();

/* Un partido de mentira, con los números ya calculados: `construirEjes`
   es puro a propósito — no vuelve a correr el motor, lo recibe. Así el
   contrato se puede probar sin arrastrar la matriz, y el motor sigue
   teniendo una sola implementación (regla de CLAUDE.md). */
const DATOS = {
  liga: "eng.1",
  probs: {L: 0.52, E: 0.26, V: 0.22},
  goles: {esperados: 2.95, mas25: 0.58, ambos: 0.54},
  mercado: {casa: "draftkings", L: 1.85, E: 3.60, V: 4.20},
};

console.log("\nContrato de ejes — las dos reglas duras\n");

/* ══════════════════════════════════════════════════════════════════
   1. La forma del registro
   ══════════════════════════════════════════════════════════════════ */

test("el contrato tiene exactamente las diez claves acordadas", () => {
  igual([...CONTRATO].sort(), [
    "ancla","aporte","apuesta","confianza","eje",
    "estimacion","lectura","medido_por","mercado","titulo",
  ]);
});

test("todo eje sale con todas las claves, ninguna de más", () => {
  construirEjes(DATOS).forEach(e => {
    igual(Object.keys(e).sort(), [...CONTRATO].sort(), `eje ${e.eje}:`);
  });
});

test("sin estadísticas salen los dos ejes que siempre existieron", () => {
  igual(construirEjes(DATOS).map(e => e.eje), ["resultado", "volumen"]);
});

/* ══════════════════════════════════════════════════════════════════
   1bis. Dominio — el primer eje que se muestra sin poder marcarse
   ══════════════════════════════════════════════════════════════════ */

const DOM = {
  local:  {remates: 14.2, al_arco: 5.1, corners: 6.0},
  visita: {remates: 9.8,  al_arco: 3.2, corners: 4.0},
};
const CON_DOM = Object.assign({}, DATOS, {dominio: DOM});

test("con estadísticas de los dos equipos aparece Dominio", () => {
  igual(construirEjes(CON_DOM).map(e => e.eje), ["resultado", "volumen", "dominio"]);
});

test("con las estadísticas de uno solo, el eje no aparece a medias", () => {
  const solo = Object.assign({}, DATOS, {dominio: {local: DOM.local}});
  cierto(!construirEjes(solo).some(e => e.eje === "dominio"),
         "medio eje invita a comparar contra un hueco");
});

test("en una liga medida, Dominio sale calibrado con su aporte por métrica", () => {
  const e = construirEjes(CON_DOM).find(x => x.eje === "dominio");
  igual(e.confianza, "calibrada");
  igual(e.aporte, {remates: 9.9, al_arco: 7.3, corners: 4.8});
  igual(e.medido_por, "medir_dominio.py");
});

test("en una liga NO medida no hereda el número: se declara sin medir", () => {
  const arg = Object.assign({}, CON_DOM, {liga: "arg.1"});
  const e = construirEjes(arg).find(x => x.eje === "dominio");
  igual(e.aporte, null, "arg no tiene estadísticas por partido en la fuente:");
  igual(e.confianza, "sin_medir",
        "sin medición en ESTA liga, calibrada sería mentira:");
});

test("y sin liga tampoco se cuelga de la medición de otra", () => {
  const sinLiga = Object.assign({}, CON_DOM, {liga: null});
  igual(construirEjes(sinLiga).find(x => x.eje === "dominio").confianza, "sin_medir");
});

test("Dominio tampoco puede llevar apuesta: contra plata no se midió", () => {
  construirEjes(CON_DOM).forEach(e => igual(e.apuesta, null, `${e.eje}:`));
});

/* ══════════════════════════════════════════════════════════════════
   1ter. Jugadores — y el estado "medido, y da mal"
   ══════════════════════════════════════════════════════════════════ */

const JUGS = [{nombre: "Neymar", equipo: "Santos", pos: "F", pj: 11,
               esp: {goles: 0.42, al_arco: 0.91, remates: 3.23}}];
const CON_JUG = Object.assign({}, DATOS, {jugadores: JUGS});

test("mal_calibrada existe y vale MENOS que calibrada", () => {
  cierto(CONFIANZAS.indexOf("mal_calibrada") < CONFIANZAS.indexOf("calibrada"),
         "el orden de CONFIANZAS es lo que permite bajar sin poder subir");
  cierto(CONFIANZAS.indexOf("sin_medir") < CONFIANZAS.indexOf("mal_calibrada"),
         "medido y malo sigue siendo más que no medido");
});

test("con jugadores aparece el eje", () => {
  cierto(construirEjes(CON_JUG).some(e => e.eje === "jugadores"));
});

test("sin jugadores el eje no aparece", () => {
  cierto(!construirEjes(DATOS).some(e => e.eje === "jugadores"));
});

test("el que llama puede BAJAR la confianza del eje", () => {
  const e = construirEjes(Object.assign({}, CON_JUG,
    {confianzaJugadores: "mal_calibrada"})).find(x => x.eje === "jugadores");
  igual(e.confianza, "mal_calibrada",
        "si una métrica en pantalla no es de fiar, el eje entero baja:");
});

test("pero sigue sin poder subirla", () => {
  const e = construirEjes(Object.assign({}, CON_JUG,
    {confianzaJugadores: "con_plata"})).find(x => x.eje === "jugadores");
  igual(e.confianza, "calibrada", "la tabla manda hacia arriba:");
});

test("una confianza inventada no baja ni sube nada", () => {
  const e = construirEjes(Object.assign({}, CON_JUG,
    {confianzaJugadores: "excelente"})).find(x => x.eje === "jugadores");
  igual(e.confianza, "calibrada");
});

test("y bajar la confianza tampoco habilita una apuesta", () => {
  construirEjes(Object.assign({}, CON_JUG,
    {confianzaJugadores: "mal_calibrada"}))
    .forEach(e => igual(e.apuesta, null, `${e.eje}:`));
});

/* ══════════════════════════════════════════════════════════════════
   1quater. Contexto — el único eje que escribe una persona
   ══════════════════════════════════════════════════════════════════ */

const CTX = {inclinacion: "L", actualizado: "2026-08-19",
             veredicto: "Palmeiras recupera a su capitán pero sigue golpeado.",
             contexto: "Vuelta de los octavos de Libertadores."};
const CON_CTX = Object.assign({}, DATOS, {contexto: CTX});

test("con análisis cargado aparece el eje Contexto", () => {
  cierto(construirEjes(CON_CTX).some(e => e.eje === "contexto"));
});

test("sin inclinación declarada NO aparece: prosa sola no es un eje", () => {
  const solo = Object.assign({}, DATOS, {contexto: {veredicto: "algo"}});
  cierto(!construirEjes(solo).some(e => e.eje === "contexto"));
});

test("Contexto se declara sin medir aunque tenga script", () => {
  const e = construirEjes(CON_CTX).find(x => x.eje === "contexto");
  igual(e.medido_por, "medir_analisis.py");
  igual(e.confianza, "sin_medir",
        "el sesgo al local se corrigió el 30/08 y no se volvió a medir:");
});

test("es el único eje que trae la lectura escrita", () => {
  const ejes = construirEjes(Object.assign({}, CON_CTX, {dominio: DOM}));
  const ctx = ejes.find(e => e.eje === "contexto");
  igual(ctx.lectura, CTX.veredicto);
  ejes.filter(e => e.eje !== "contexto")
      .forEach(e => igual(e.lectura, null, `${e.eje}:`));
});

test("sin veredicto cae al contexto, y si no hay ninguno queda en null", () => {
  const soloCtx = Object.assign({}, DATOS,
    {contexto: {inclinacion: "V", contexto: "solo contexto"}});
  igual(construirEjes(soloCtx).find(e => e.eje === "contexto").lectura,
        "solo contexto");
  const pelado = Object.assign({}, DATOS, {contexto: {inclinacion: "V"}});
  igual(construirEjes(pelado).find(e => e.eje === "contexto").lectura, null);
});

test("y tampoco puede llevar apuesta", () => {
  construirEjes(CON_CTX).forEach(e => igual(e.apuesta, null, `${e.eje}:`));
});

/* ══════════════════════════════════════════════════════════════════
   2. Regla 1 — sin script que lo mida, no se declara nada
   ══════════════════════════════════════════════════════════════════ */

test("un eje sin medido_por queda en sin_medir aunque la tabla diga otra cosa", () => {
  const e = sellar("__inventado__", "eng.1", {titulo: "Eje que nadie midió"});
  igual(e.medido_por, null);
  igual(e.confianza, "sin_medir");
});

test("una confianza que no está en la lista se degrada, no se acepta", () => {
  const guardado = MEDICIONES.resultado.confianza;
  MEDICIONES.resultado.confianza = "buenisima";
  try {
    igual(sellar("resultado", "eng.1", {}).confianza, "sin_medir");
  } finally { MEDICIONES.resultado.confianza = guardado; }
});

test("el que llama no puede subir la confianza por su cuenta", () => {
  const e = sellar("resultado", "eng.1", {confianza: "con_plata"});
  igual(e.confianza, MEDICIONES.resultado.confianza,
        "la confianza sale de la tabla de mediciones, no del llamador:");
});

/* ══════════════════════════════════════════════════════════════════
   3. Regla 2 — la apuesta solo existe donde hay plata medida
   ══════════════════════════════════════════════════════════════════ */

test("una apuesta en un eje calibrado se cae", () => {
  const e = sellar("resultado", "eng.1", {apuesta: {op: "L", cuota: 2.10}});
  igual(e.confianza, "calibrada");
  igual(e.apuesta, null, "calibrada no alcanza para recomendar:");
});

test("con plata medida, la apuesta sobrevive", () => {
  const guardado = MEDICIONES.resultado.confianza;
  MEDICIONES.resultado.confianza = "con_plata";
  try {
    const e = sellar("resultado", "eng.1", {apuesta: {op: "L", cuota: 2.10}});
    igual(e.apuesta, {op: "L", cuota: 2.10});
  } finally { MEDICIONES.resultado.confianza = guardado; }
});

test("hoy ningún eje sale con plata — y eso es el estado real, no un bug", () => {
  construirEjes(DATOS).forEach(e => {
    cierto(e.confianza !== "con_plata", `${e.eje} dice tener plata medida y no la tiene`);
    igual(e.apuesta, null, `${e.eje}:`);
  });
});

/* ══════════════════════════════════════════════════════════════════
   4. El aporte es por liga, y falta cuando falta
   ══════════════════════════════════════════════════════════════════ */

test("el aporte se lee de la liga del partido", () => {
  igual(sellar("resultado", "eng.1", {}).aporte, 13.2);
  igual(sellar("resultado", "arg.1", {}).aporte, 2.6);
});

test("una liga sin medición no hereda el número de otra", () => {
  igual(sellar("resultado", "bra.1", {}).aporte, null);
  igual(sellar("resultado", undefined, {}).aporte, null);
});

/* ══════════════════════════════════════════════════════════════════
   5. Lo que cada eje efectivamente dice
   ══════════════════════════════════════════════════════════════════ */

test("Resultado publica las tres probabilidades que ya publicaba", () => {
  const e = construirEjes(DATOS)[0];
  igual(e.estimacion, {L: 0.52, E: 0.26, V: 0.22});
  igual(e.mercado, DATOS.mercado);
});

test("Volumen publica goles esperados y sus dos mercados", () => {
  const e = construirEjes(DATOS)[1];
  igual(e.estimacion, {esperados: 2.95, mas25: 0.58, ambos: 0.54});
});

test("sin datos de mercado el eje sigue existiendo, con mercado en null", () => {
  const e = construirEjes({liga: "eng.1", probs: DATOS.probs, goles: DATOS.goles})[0];
  igual(e.mercado, null);
  igual(e.confianza, "calibrada", "que no haya precio no cambia lo que sabemos:");
});

test("la lectura arranca vacía: el texto lo compone la pantalla, no el contrato", () => {
  construirEjes(DATOS).forEach(e => igual(e.lectura, null, `${e.eje}:`));
});

console.log("");
console.log(`${ok} ok, ${mal} fallando`);
console.log("");
process.exit(mal ? 1 : 0);
