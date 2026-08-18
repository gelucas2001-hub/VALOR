/* ══════════════════════════════════════════════════════════════════
   TEST DE LA RESOLUCIÓN AUTOMÁTICA DEL REGISTRO

   Corré:  node test_registro.js

   Extrae la lógica de resolución del propio `index.html` — no una copia —
   y la corre contra un snapshot congelado de `data/partidos.json`.

   Por qué contra el archivo real y no contra una copia: el proyecto ya
   perdió tiempo comparando mediciones hechas sobre corridas distintas
   del cron. `tests/partidos-snapshot.json` es una foto fija; el cron
   reescribe `data/partidos.json` dos veces por día y haría que este
   test diga cosas distintas el mismo día.
   ══════════════════════════════════════════════════════════════════ */

const fs = require("fs");
const path = require("path");

const RAIZ = __dirname;
const INICIO = "/* ==== INICIO RESOLUCION ==== */";
const FIN    = "/* ==== FIN RESOLUCION ==== */";

/* ── Extracción: la región marcada de index.html, evaluada tal cual ── */
function cargarResolucion(){
  const html = fs.readFileSync(path.join(RAIZ, "index.html"), "utf8");
  const a = html.indexOf(INICIO), b = html.indexOf(FIN);
  if(a < 0 || b < 0)
    throw new Error(`index.html no tiene la región marcada ${INICIO} … ${FIN}`);
  const src = html.slice(a + INICIO.length, b);
  const salida = {};
  new Function("exportar", src + `
    exportar({TESTS, norm, buscarResultado, resolver,
              fijarResultados: r => { RESULTADOS = r || {}; }});
  `)(o => Object.assign(salida, o));
  return salida;
}

const MATCHES = JSON.parse(
  fs.readFileSync(path.join(RAIZ, "tests", "partidos-snapshot.json"), "utf8")
).partidos;

/* ── Mini-runner ── */
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

const { TESTS, buscarResultado, resolver, fijarResultados } = cargarResolucion();

console.log("\nResolución automática del registro — " + MATCHES.length + " partidos reales\n");

/* ══════════════════════════════════════════════════════════════════
   1. El cruce encuentra el marcador, y lo encuentra ORIENTADO

   Fixture verificado a mano contra los dos historiales, que son
   fuentes independientes:
     Aldosivi   (formH, k=2, local=true)  → "1-2"  ⇒ Aldosivi 1, Gimnasia 2
     Gimnasia   (formA, k=2, local=false) → "2-1"  ⇒ Gimnasia 2, Aldosivi 1
   Los dos dicen lo mismo: local Aldosivi, 1-2.
   ══════════════════════════════════════════════════════════════════ */
test("cruza un partido pasado y lo orienta con el local primero", ()=>{
  const r = buscarResultado("Aldosivi", "Gimnasia La Plata", MATCHES, "2026-08-01");
  cierto(r, "no encontró el cruce Aldosivi–Gimnasia");
  igual([r.i, r.j], [1, 2], "Aldosivi 1 – Gimnasia 2:");
});

test("dar vuelta local y visitante no devuelve el mismo partido", ()=>{
  /* El cruce es estricto con la localía, y tiene que serlo: pedir
     "Gimnasia vs Aldosivi" es preguntar por el partido en cancha de
     Gimnasia, que es OTRO partido. En fase de grupos los dos existen.
     Acá la vuelta no está en la ventana del archivo, así que no hay
     nada que devolver — y devolver el de ida sería mentir. */
  igual(buscarResultado("Gimnasia La Plata", "Aldosivi", MATCHES, "2026-08-01"),
        null, "la vuelta no existe en el archivo:");
});

test("con los dos partidos de una llave, cada orden trae el suyo", ()=>{
  /* Independiente Rivadavia y Fluminense se cruzaron dos veces en la
     fase de grupos: 0-0 en Brasil y 1-1 en Mendoza. Es justamente el
     caso que rompía el cruce sin candados. */
  const ida = buscarResultado("Fluminense", "Independiente Rivadavia", MATCHES, "2026-08-01");
  const vta = buscarResultado("Independiente Rivadavia", "Fluminense", MATCHES, "2026-08-01");
  igual([ida.i, ida.j], [0, 0], "en cancha de Fluminense:");
  igual([vta.i, vta.j], [1, 1], "en cancha de Independiente Rivadavia:");
});

test("cruza también cuando el dueño del historial jugó de visitante", ()=>{
  /* Banfield (k=0, local:false, "1-0") ⇒ Racing 0 – Banfield 1 */
  const r = buscarResultado("Racing Club", "Banfield", MATCHES, "2026-08-01");
  cierto(r, "no encontró el cruce Racing–Banfield");
  igual([r.i, r.j], [0, 1], "Racing 0 – Banfield 1:");
});

test("las dos fuentes de un mismo partido dicen lo mismo", ()=>{
  /* Chequeo de orientación sobre TODO el archivo, sin fixtures a mano.

     Un partido puede aparecer en dos historiales independientes: el
     del local (con local:true) y el del visitante (con local:false,
     y el marcador al revés). Para cada par ordenado (H,A) juntamos lo
     que dice cada fuente por separado; tienen que coincidir.

     Esto es lo que atrapa un error de signo. Si alguien invirtiera la
     rama del visitante, el fixture escrito a mano más arriba podría
     seguir pasando por casualidad; esto no. */
  const fuentes = new Map();   // "H|A" → {local:Set, visitante:Set}
  MATCHES.forEach(m=>{
    [[m.home, m.formH], [m.away, m.formA]].forEach(([dueno, forma])=>{
      (forma||[]).forEach(f=>{
        if(!f || !f.rival || !f.marcador) return;
        const [a, b] = String(f.marcador).split("-").map(Number);
        if(!isFinite(a) || !isFinite(b)) return;
        const [H, A] = f.local ? [dueno, f.rival] : [f.rival, dueno];
        const marcador = f.local ? `${a}-${b}` : `${b}-${a}`;   // siempre local-visitante
        const clave = `${H}|${A}`;
        if(!fuentes.has(clave)) fuentes.set(clave, {local:new Set(), visitante:new Set()});
        fuentes.get(clave)[f.local ? "local" : "visitante"].add(marcador);
      });
    });
  });

  let comparados = 0;
  fuentes.forEach((f, clave)=>{
    /* El historial son los últimos cinco. Si una de las dos fuentes no
       alcanza a cubrir el partido, no hay nada que comparar; y si los
       mismos dos equipos jugaron más de una vez en la misma cancha,
       las dos ventanas pueden cubrir partidos distintos — ese caso lo
       mide el test siguiente. */
    if(f.local.size !== 1 || f.visitante.size !== 1) return;
    comparados++;
    igual([...f.local], [...f.visitante],
      `${clave.replace("|", " vs ")} según cada historial:`);
  });
  cierto(comparados > 50, `solo comparó ${comparados} partidos, esperaba más de 50`);
});

test("con el mismo cruce repetido en la misma cancha, gana el más reciente", ()=>{
  /* Medido sobre el snapshot: de 78 partidos que aparecen en los dos
     historiales, 75 se jugaron una sola vez y coinciden sin
     excepción; 3 se repitieron con el mismo local.

     Olimpia y Vasco se cruzaron tres veces dentro de los últimos
     cinco de Olimpia, dos de ellas en Brasil: 0-0 y 3-0. La ventana
     de Vasco solo llega al 0-0. El desempate por `k` se queda con el
     más reciente, que es el que la ventana corta de todas maneras. */
  const r = buscarResultado("Vasco da Gama", "Club Olimpia", MATCHES, "2026-08-01");
  cierto(r, "no encontró el cruce Vasco–Olimpia");
  igual([r.i, r.j], [0, 0], "el más reciente en cancha de Vasco:");
  igual(r.k, 0, "y es el último partido de alguno de los dos:");
});

/* ══════════════════════════════════════════════════════════════════
   2. Candado 1 — solo historiales POSTERIORES al partido anotado

   Es el test de regresión que importa. Un historial cargado antes de
   nuestro partido no puede contenerlo, pero sí puede contener el cruce
   ANTERIOR entre los mismos dos equipos — y ahí la app anota como
   resultado un partido que no es el nuestro.
   ══════════════════════════════════════════════════════════════════ */
test("ningún partido de la grilla cruza consigo mismo (candado de fecha)", ()=>{
  const cruzan = MATCHES.filter(m => buscarResultado(m.home, m.away, MATCHES, m.date));
  igual(cruzan.map(m=>m.home+" vs "+m.away), [], "no debería cruzar ninguno:");
});

test("sin el candado de fecha aparecen falsos positivos", ()=>{
  /* Si esto diera 0, el candado no estaría protegiendo de nada y el
     test de arriba no probaría nada. */
  const cruzan = MATCHES.filter(m => buscarResultado(m.home, m.away, MATCHES, null));
  cierto(cruzan.length > 0,
    "sin candado no cruzó ninguno — el test anterior no está midiendo nada");
  console.log("         (sin candado cruzan " + cruzan.length + ": " +
    cruzan.map(m=>m.home+" vs "+m.away).join(", ") + ")");
});

/* ══════════════════════════════════════════════════════════════════
   3. Candado 2 — si sigue en la grilla con fecha ≥ hoy, no se jugó
   ══════════════════════════════════════════════════════════════════ */
test("un partido que todavía está en la grilla queda pendiente", ()=>{
  const hoy = "2026-08-18";
  const futuros = MATCHES.filter(m => m.date >= hoy);
  cierto(futuros.length > 0, "el snapshot no tiene partidos futuros");
  futuros.forEach(m=>{
    const r = resolver(carga(m, "1x2_l"), MATCHES, hoy);
    igual(r.estado, "pendiente", `${m.home} vs ${m.away} (${m.date}):`);
    igual(r.esperando, false, `${m.home} vs ${m.away} no debería estar esperando:`);
  });
});

test("ninguna carga de la grilla se resuelve sola antes de jugarse", ()=>{
  /* La garantía durable: pase lo que pase con los historiales, un
     partido sin jugar nunca se marca ganado ni perdido. */
  const hoy = "2026-08-18";
  const resueltos = MATCHES.filter(m => m.date >= hoy)
    .flatMap(m => Object.keys(TESTS).map(id => [m, resolver(carga(m, id), MATCHES, hoy)]))
    .filter(([, r]) => r.estado === "ganada" || r.estado === "perdida");
  igual(resueltos.map(([m, r]) => `${m.home} vs ${m.away} → ${r.estado}`), [],
    "sin jugarse:");
});

/* ══════════════════════════════════════════════════════════════════
   4. TESTS — el criterio que promete el cobro es el que lo verifica
   ══════════════════════════════════════════════════════════════════ */
test("los criterios de cobro deciden bien un 2-1", ()=>{
  const r = {i:2, j:1};
  const d = id => TESTS[id](r.i, r.j);
  cierto( d("1x2_l"),  "local gana 2-1");
  cierto(!d("1x2_e"),  "2-1 no es empate");
  cierto(!d("1x2_v"),  "visitante no gana 2-1");
  cierto( d("dc_lx"),  "local gana o empata");
  cierto(!d("dc_x2"),  "visitante no gana ni empata");
  cierto( d("dc_12"),  "hubo ganador");
  cierto( d("btts_si"),"marcaron los dos");
  cierto(!d("btts_no"),"no se quedó nadie en cero");
  cierto( d("ov2.5"),  "3 goles superan 2.5");
  cierto(!d("un2.5"),  "3 goles no bajan de 2.5");
});

test("un 0-0 se lee como empate sin goles", ()=>{
  const d = id => TESTS[id](0, 0);
  cierto( d("1x2_e"), "0-0 es empate");
  cierto( d("dc_lx"), "empate cobra doble oportunidad local");
  cierto( d("dc_x2"), "empate cobra doble oportunidad visitante");
  cierto(!d("dc_12"), "0-0 no tiene ganador");
  cierto( d("btts_no"),"nadie marcó");
  cierto( d("un1.5"), "0 goles bajan de 1.5");
});

test("la carga resuelta usa el criterio de su propio mercado", ()=>{
  /* Aldosivi 1 – Gimnasia 2: gana el visitante, 3 goles. */
  const m = {home:"Aldosivi", away:"Gimnasia La Plata", id:"x", date:"2026-08-01"};
  const est = id => resolver(carga(m, id), MATCHES, "2026-08-18").estado;
  igual(est("1x2_v"), "ganada",  "gana Gimnasia:");
  igual(est("1x2_l"), "perdida", "no gana Aldosivi:");
  igual(est("ov2.5"), "ganada",  "3 goles superan 2.5:");
  igual(est("un2.5"), "perdida", "3 goles no bajan de 2.5:");
  igual(est("btts_si"),"ganada", "marcaron los dos:");
});

/* ══════════════════════════════════════════════════════════════════
   5. Estados de borde
   ══════════════════════════════════════════════════════════════════ */
test("un partido ya jugado sin marcador a la vista queda esperando", ()=>{
  const m = {home:"Equipo Inventado", away:"Otro Inventado", id:"z", date:"2026-08-01"};
  const r = resolver(carga(m, "1x2_l"), MATCHES, "2026-08-18");
  igual(r.estado, "pendiente", "sin marcador:");
  igual(r.esperando, true, "ya se jugó, falta el resultado:");
});

test("la corrección a mano manda sobre el cruce", ()=>{
  const m = {home:"Aldosivi", away:"Gimnasia La Plata", id:"x", date:"2026-08-01"};
  const b = Object.assign(carga(m, "1x2_l"), {manual:true, estado:"ganada"});
  const r = resolver(b, MATCHES, "2026-08-18");
  igual(r.estado, "ganada", "el cruce dice perdida, pero lo marcó el usuario:");
  igual(r.auto, false, "no es automático:");
});

test("el estado guardado no manda si la carga es automática", ()=>{
  /* Aldosivi no ganó. Aunque el localStorage diga "ganada", se
     resuelve contra los datos frescos. */
  const m = {home:"Aldosivi", away:"Gimnasia La Plata", id:"x", date:"2026-08-01"};
  const b = Object.assign(carga(m, "1x2_l"), {estado:"ganada", manual:false});
  igual(resolver(b, MATCHES, "2026-08-18").estado, "perdida", "gana el dato fresco:");
});

test("una carga vieja sin home/away se resuelve por el nombre del partido", ()=>{
  /* Compatibilidad: las cargas anotadas antes de este cambio solo
     tienen `partido: "X vs Y"`. No se pueden perder. */
  const b = {key:"x__1x2_v", partido:"Aldosivi vs Gimnasia La Plata",
             fecha:"2026-08-01", matchId:"x", manual:false, estado:"pendiente"};
  igual(resolver(b, MATCHES, "2026-08-18").estado, "ganada", "carga vieja:");
});

/* ══════════════════════════════════════════════════════════════════
   6. La vía exacta: el marcador guardado por id de partido

   Es la mejora de fondo que señalaba el handoff y que ahora existe:
   actualizar.py persiste los marcadores finales en data/resultados.json.
   Cruza por id, así que no puede equivocarse de partido — y por eso
   resuelve el único caso que el cruce por historial no puede resolver
   bien: dos partidos entre los mismos equipos con el mismo local.
   ══════════════════════════════════════════════════════════════════ */
test("con marcador guardado, resuelve por id y no mira historiales", ()=>{
  const m = {home:"Equipo Inventado", away:"Otro Inventado", id:"espnXYZ", date:"2026-08-01"};
  /* Ninguno de los dos existe en los historiales del snapshot, así que
     el cruce por historial no puede resolverlo. El marcador guardado
     sí. */
  fijarResultados({"espnXYZ": "3-1"});
  const r = resolver(carga(m, "1x2_l"), MATCHES, "2026-08-18");
  igual(r.estado, "ganada", "local ganó 3-1:");
  igual([r.res.i, r.res.j], [3, 1], "marcador exacto:");
  igual(r.res.exacto, true, "marcado como exacto:");
  fijarResultados({});
});

test("el marcador guardado gana al cruce por historial", ()=>{
  /* Aldosivi 1-2 Gimnasia según los historiales. Si el archivo de
     resultados dijera otra cosa para ese id, manda el archivo: es dato
     directo del partido, no inferido por nombre de rival. */
  const m = {home:"Aldosivi", away:"Gimnasia La Plata", id:"espnAG", date:"2026-08-01"};
  fijarResultados({"espnAG": "4-0"});
  const r = resolver(carga(m, "1x2_l"), MATCHES, "2026-08-18");
  igual([r.res.i, r.res.j], [4, 0], "manda el guardado:");
  igual(r.estado, "ganada", "con 4-0 el local cobra:");
  fijarResultados({});
});

test("sin marcador guardado sigue funcionando el respaldo por historial", ()=>{
  /* El respaldo no se puede perder: cubre lo anotado antes de que
     resultados.json existiera. */
  fijarResultados({});
  const m = {home:"Aldosivi", away:"Gimnasia La Plata", id:"espnAG", date:"2026-08-01"};
  const r = resolver(carga(m, "1x2_v"), MATCHES, "2026-08-18");
  igual(r.estado, "ganada", "Gimnasia ganó 2-1:");
  igual(r.res.exacto, undefined, "vino del historial, no del archivo:");
});

test("un marcador guardado ilegible no rompe: cae al respaldo", ()=>{
  fijarResultados({"espnAG": "sin datos"});
  const m = {home:"Aldosivi", away:"Gimnasia La Plata", id:"espnAG", date:"2026-08-01"};
  const r = resolver(carga(m, "1x2_v"), MATCHES, "2026-08-18");
  igual(r.estado, "ganada", "resolvió igual por historial:");
  fijarResultados({});
});

test("el candado de la grilla manda incluso con marcador guardado", ()=>{
  /* Si el partido sigue en la grilla con fecha de hoy o posterior, no se
     jugó, y un marcador guardado para ese id sería un error de datos.
     El candado tiene que seguir adelante de todo. */
  const hoy = "2026-08-18";
  const futuro = MATCHES.find(m => m.date >= hoy);
  fijarResultados({[futuro.id]: "9-0"});
  const r = resolver(carga(futuro, "1x2_l"), MATCHES, hoy);
  igual(r.estado, "pendiente", `${futuro.home} vs ${futuro.away} sigue en grilla:`);
  fijarResultados({});
});

/* Una carga del registro, como la escribe anotar(). */
function carga(m, id){
  return {key: m.id + "__" + id, partido: `${m.home} vs ${m.away}`,
          home: m.home, away: m.away, fecha: m.date, matchId: m.id,
          manual:false, estado:"pendiente"};
}

console.log(`\n${ok} ok, ${mal} fallando\n`);
process.exit(mal ? 1 : 0);
