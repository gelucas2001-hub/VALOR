/* ══════════════════════════════════════════════════════════════════
   BARRIDO DE LAS CONSTANTES DE VALOR

   Corré:  node barrer_valor.js

   El TRASPASO (sección 5) fija el piso de la marca de valor en 6pp y
   deja la tabla del barrido con el que se eligió. Pero esa tabla se
   midió sobre 30 partidos de otra semana, y la regla del proyecto es
   explícita: "No copiar las constantes a ciegas: reproducir la
   medición." Esto la reproduce.

   Usa las funciones REALES de app.html — no una copia — sobre el
   snapshot congelado, por la misma razón que test_registro.js: el cron
   reescribe data/partidos.json dos veces por día y el mismo código
   daría números distintos a la mañana y a la tarde.

   IMPORTANTE: esto MIDE, no ajusta. Si el barrido no favorece al 6pp,
   el hallazgo es que no lo favorece — no se toca la constante para que
   un número quede lindo.
   ══════════════════════════════════════════════════════════════════ */

const fs = require("fs");
const path = require("path");

/* ── Cargar la lógica de app.html ──────────────────────────────────
   Se corta antes de "RENDER Y RUTEO": de ahí para abajo hay acceso al
   DOM. Todo lo de arriba es motor, constantes y reglas. */
function cargarLogica(){
  const html = fs.readFileSync(path.join(__dirname, "app.html"), "utf8");
  const script = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));
  const corte = script.indexOf("RENDER Y RUTEO");
  if(corte < 0) throw new Error("no encontré el corte 'RENDER Y RUTEO' en app.html");
  const src = script.slice(0, script.lastIndexOf("/*", corte));

  /* localStorage de mentira: el bloque de ESTADO lo lee al cargar. */
  const almacen = {};
  const localStorage = {
    getItem: k => (k in almacen ? almacen[k] : null),
    setItem: (k,v) => { almacen[k] = String(v); },
  };
  const salida = {};
  new Function("localStorage", "exportar", src + `
    exportar({MATCHES, escalera, lectura, mercados, devig, pMercado, alerta,
              analizado, FRANJAS, matrix, sumIf, umbral, ev, kelly,
              MIN_EV, MAX_ODDS, EV_ABSURDO, VENTAJA_MIN, VALOR_MIN, VALOR_MAX, ALERTA_MIN,
              fijarDatos: (ms, an) => { MATCHES = ms; ANALISIS = an || {}; }});
  `)(localStorage, o => Object.assign(salida, o));
  return salida;
}

const L = cargarLogica();
const snap = JSON.parse(fs.readFileSync(path.join(__dirname, "tests", "partidos-snapshot.json"), "utf8"));
const PARTIDOS = snap.partidos.filter(m => m.lh != null && m.la != null);
L.fijarDatos(PARTIDOS, {});

const pc = n => (n*100).toFixed(1) + "%";

console.log(`\nBarrido de las constantes de valor`);
console.log(`Snapshot: tests/partidos-snapshot.json — ${snap.actualizado} — ${PARTIDOS.length} partidos\n`);
console.log(`Constantes que rigen hoy en app.html:`);
console.log(`  VALOR_MIN ${L.VALOR_MIN}   VALOR_MAX ${L.VALOR_MAX}   ALERTA_MIN ${L.ALERTA_MIN}`);
console.log(`  MIN_EV ${L.MIN_EV}   MAX_ODDS ${L.MAX_ODDS}   EV_ABSURDO ${L.EV_ABSURDO}   VENTAJA_MIN ${L.VENTAJA_MIN}\n`);

/* ══════════════════════════════════════════════════════════════════
   1. La ventaja cruda: cuánto nos apartamos de la línea limpia

   El TRASPASO dice que el modelo se aparta 9-15pp en promedio, y que
   por eso un piso de 3pp queda DENTRO del propio error. Se remide.
   ══════════════════════════════════════════════════════════════════ */
const ventajas = [];
PARTIDOS.forEach(m=>{
  const mk = m.mercado || {};
  const pq = L.devig(mk);
  if(!pq) return;
  const lec = L.lectura(m);
  ["L","E","V"].forEach(k=> ventajas.push(Math.abs(lec.p[k] - pq[k])));
});
ventajas.sort((a,b)=>a-b);
const media = ventajas.reduce((s,v)=>s+v,0) / ventajas.length;
const mediana = ventajas[Math.floor(ventajas.length/2)];
const p90 = ventajas[Math.floor(ventajas.length*0.9)];
console.log(`── Cuánto nos apartamos de la línea limpia (1X2, valor absoluto) ──`);
console.log(`  ${ventajas.length} comparaciones sobre ${PARTIDOS.filter(m=>L.devig(m.mercado||{})).length} partidos con cuota`);
console.log(`  media ${pc(media)}   mediana ${pc(mediana)}   percentil 90 ${pc(p90)}`);
console.log(`  El TRASPASO decía 9-15pp. ${media>=0.09&&media<=0.15 ? "Se reproduce." : "NO se reproduce — ver abajo."}\n`);

/* ══════════════════════════════════════════════════════════════════
   2. El barrido del piso

   Un "pick" es un escalón de la escalera con opción elegida. La marca
   se enciende si la ventaja contra la línea limpia cae en la banda
   [piso, VALOR_MAX] — la misma cuenta que hace escalera().

   OJO con la lectura: la marca en pantalla además exige que el partido
   esté analizado a mano (regla de alineación), y analisis.json está
   vacío. Este barrido mide la CAPACIDAD de la regla, no lo que hoy se
   ve — que es cero por falta de contenido.
   ══════════════════════════════════════════════════════════════════ */
function barrer(piso){
  let picks = 0, marcados = 0, conMarca = 0;
  PARTIDOS.forEach(m=>{
    const filas = L.escalera(m);
    let alguno = false;
    filas.forEach(f=>{
      if(!f.op) return;
      picks++;
      if(f.ventaja != null && f.ventaja >= piso && f.ventaja <= L.VALOR_MAX){ marcados++; alguno = true; }
    });
    if(alguno) conMarca++;
  });
  return {picks, marcados, conMarca};
}

console.log(`── Barrido del piso de la marca (techo fijo en ${L.VALOR_MAX}) ──`);
console.log(`  piso    marcados   % de picks   partidos con marca`);
const filas = [];
for(const pp of [3,4,5,6,7,8,9,10]){
  const r = barrer(pp/100);
  filas.push({pp, ...r});
  const pct = r.picks ? (r.marcados/r.picks*100).toFixed(0) : "0";
  const elegido = pp === Math.round(L.VALOR_MIN*100) ? "   ← el que rige" : "";
  console.log(`  ${String(pp).padStart(2)}pp   ${String(r.marcados).padStart(6)}   ${String(pct).padStart(8)}%   ${String(r.conMarca).padStart(3)} de ${PARTIDOS.length}${elegido}`);
}

/* ══════════════════════════════════════════════════════════════════
   3. ¿El piso que rige sigue estando por encima del propio error?

   Es la pregunta que motivó el 6pp. No se responde con opinión.
   ══════════════════════════════════════════════════════════════════ */
console.log(`\n── El chequeo que motivó el 6pp ──`);
const dentro = L.VALOR_MIN < mediana;
console.log(`  piso ${pc(L.VALOR_MIN)} vs mediana del error ${pc(mediana)}`);
console.log(`  ${dentro
  ? `El piso sigue estando POR DEBAJO de la mediana del error. Es el problema que\n  el TRASPASO señalaba para el 3pp, y a este nivel de datos también le toca al piso\n  actual. Hallazgo, no ajuste: hay que decidirlo midiendo contra resultados.`
  : `El piso está POR ENCIMA de la mediana del error. Es la condición que se buscaba.`}`);

/* ══════════════════════════════════════════════════════════════════
   4. Techo de valor y alerta: cuántos casos tocan cada borde
   ══════════════════════════════════════════════════════════════════ */
let sobreTecho = 0, alertas = 0;
PARTIDOS.forEach(m=>{
  L.escalera(m).forEach(f=>{
    if(f.op && f.ventaja != null && f.ventaja > L.VALOR_MAX) sobreTecho++;
  });
  if(L.alerta(m)) alertas++;
});
console.log(`\n── Los otros dos bordes ──`);
console.log(`  picks con ventaja arriba del techo (${pc(L.VALOR_MAX)}), descartados por valor falso: ${sobreTecho}`);
console.log(`  partidos con alerta encendida (mercado nos saca ${pc(L.ALERTA_MIN)}): ${alertas} de ${PARTIDOS.length}`);
console.log(`  El TRASPASO decía que la alerta se enciende en el 8% de los partidos con cuota.`);
const conCuota = PARTIDOS.filter(m=>L.devig(m.mercado||{})).length;
console.log(`  Acá: ${conCuota ? (alertas/conCuota*100).toFixed(0) : 0}% de ${conCuota} con cuota.\n`);
