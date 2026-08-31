/* Cómo le fue al motor en una fecha, contra resultados reales.
   Usa el index.html PUBLICADO, no una copia: si la app cambia, esto
   mide la app que cambió.
       node eval_fecha.js 2026-08-30 resultados.json               */
const fs = require("fs"), path = require("path");

function cargar(){
  const html = fs.readFileSync(path.join(__dirname,"index.html"),"utf8");
  const s = html.slice(html.indexOf("<script>")+8, html.lastIndexOf("</script>"));
  const corte = s.indexOf("RENDER Y RUTEO");
  const src = s.slice(0, s.lastIndexOf("/*", corte));
  const alm={}, localStorage={getItem:k=>k in alm?alm[k]:null,setItem:(k,v)=>{alm[k]=String(v)}};
  const out={};
  new Function("localStorage","exportar", src + `
    exportar({escalera, lectura, mercados, TESTS,
              cargar:(ms,an)=>{MATCHES=ms;ANALISIS=an||{}}});`)(localStorage,o=>Object.assign(out,o));
  return out;
}
const L = cargar();
const FECHA = process.argv[2] || "2026-08-30";
const RES = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const MS = (JSON.parse(fs.readFileSync(path.join(__dirname,"data","partidos.json"),"utf8")).partidos || [])
  .filter(m => m.date === FECHA && RES[m.id] && m.lh != null);
L.cargar(MS, {});

let leanOK=0, leanN=0, escOK=0, escN=0, favOK=0, favN=0;
const porFranja = [[0,0],[0,0],[0,0]];
const filas = [];
MS.forEach(m=>{
  const [i,j] = String(RES[m.id]).split("-").map(Number);
  const real = i>j ? "L" : i===j ? "E" : "V";
  const lec = L.lectura(m);
  leanN++; if(lec.lean === real) leanOK++;
  // vara honesta: apostar siempre al local
  favN++; if(real === "L") favOK++;
  const esc = L.escalera(m);
  const marcas = esc.map((f,k)=>{
    if(!f.op) return "—";
    escN++; porFranja[k][1]++;
    const ok = L.TESTS[f.op.id] ? L.TESTS[f.op.id](i,j) : null;
    if(ok){ escOK++; porFranja[k][0]++; }
    return (ok?"✓":"✗") + f.op.id;
  });
  filas.push(`  ${(m.home.slice(0,15)+" v "+m.away.slice(0,14)).padEnd(33)} ${RES[m.id].padStart(4)}  ${real}  lean ${lec.lean}${lec.lean===real?"✓":"✗"}  ${marcas.join(" ")}`);
});
console.log(`\n  FECHA ${FECHA} — ${MS.length} partidos con resultado\n`);
console.log(filas.join("\n"));
console.log(`\n  lean (1X2):      ${leanOK}/${leanN} = ${(leanOK/leanN*100).toFixed(0)}%`);
console.log(`  siempre local:   ${favOK}/${favN} = ${(favOK/favN*100).toFixed(0)}%   <- la vara`);
console.log(`  escalera:        ${escOK}/${escN} = ${(escOK/escN*100).toFixed(0)}%`);
["Lo más probable","Intermedia","Arriesgada"].forEach((n,k)=>{
  const [o,t]=porFranja[k];
  if(t) console.log(`    ${n.padEnd(16)} ${o}/${t} = ${(o/t*100).toFixed(0)}%`);
});
console.log();
