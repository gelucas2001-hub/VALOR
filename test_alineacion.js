/* ══════════════════════════════════════════════════════════════════
   TEST DE LA REGLA DE ALINEACIÓN

   Corré:  node test_alineacion.js

   Método le promete al usuario esto, textual: "nuestra regla es que
   nada contradiga nuestra propia lectura del partido. Si esa lectura la
   produjera el mismo modelo que después dice dónde hay valor, sería el
   modelo dándose la razón a sí mismo. La lectura tiene que venir de
   donde el modelo no llega."

   Estos tests verifican que el código cumpla esa promesa: que la
   dirección de la alineación salga del campo `inclinacion` del análisis
   cargado a mano, y no del lean del modelo.
   ══════════════════════════════════════════════════════════════════ */

const fs = require("fs");
const path = require("path");

function cargarLogica(){
  const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  const script = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));
  const corte = script.indexOf("RENDER Y RUTEO");
  const src = script.slice(0, script.lastIndexOf("/*", corte));
  const almacen = {};
  const localStorage = {
    getItem: k => (k in almacen ? almacen[k] : null),
    setItem: (k, v) => { almacen[k] = String(v); },
  };
  const salida = {};
  new Function("localStorage", "exportar", src + `
    exportar({escalera, lectura, alerta, analizado, inclinacionDe, contradice, devig,
              marcaDeValor, hayProsa, sello, fraseCorta, nombreSello, VALOR_MIN, VALOR_MAX,
              mercados, otrosMercados,
              cargar: (ms, an) => { MATCHES = ms; ANALISIS = an || {}; }});
  `)(localStorage, o => Object.assign(salida, o));
  return salida;
}

const L = cargarLogica();
const DIRS = ["L","E","V"];

const PARTIDOS = JSON.parse(
  fs.readFileSync(path.join(__dirname, "tests", "partidos-snapshot.json"), "utf8")
).partidos.filter(m => m.lh != null && m.la != null);

let ok = 0, mal = 0;
const test = (n, fn) => {
  try { fn(); console.log("  ok   " + n); ok++; }
  catch(e){ console.log("  FALLA " + n + "\n         " + e.message); mal++; }
};
const igual = (a, b, m) => {
  if(JSON.stringify(a) !== JSON.stringify(b))
    throw new Error(`${m||""} esperaba ${JSON.stringify(b)}, dio ${JSON.stringify(a)}`);
};
const cierto = (v, m) => { if(!v) throw new Error(m || "esperaba verdadero"); };

/* La misma regla de recorte que usa sello(): nombre entero salvo que
   pase de 13 caracteres, y ahí solo la primera palabra. Se replica acá
   a propósito — si el test importara la función, no probaría nada. */
const comoSello = (n, otro) => {
  const recortar = x => (x.length > 13 ? x.split(" ")[0] : x).toUpperCase();
  if(recortar(n) !== recortar(otro)) return recortar(n);
  const propias = n.split(" ").filter(w => !otro.split(" ").includes(w));
  return (propias.join(" ").replace(/[()]/g, "").trim() || n).toUpperCase();
};

/* Un partido donde el modelo tiene una preferencia clara, para poder
   contrastar la inclinación humana contra ella. */
const claro = PARTIDOS.find(m => {
  const lec = L.lectura(m);
  return lec.lean === "L" && lec.p.L >= 0.5 && L.devig(m.mercado || {});
});
if(!claro) throw new Error("el snapshot no tiene un partido con local claro y cuota");

console.log(`\nRegla de alineación — ${PARTIDOS.length} partidos reales`);
console.log(`Partido de prueba: ${claro.home} vs ${claro.away} ` +
            `(el modelo inclina a ${L.lectura(claro).lean})\n`);

/* ══════════════════════════════════════════════════════════════════
   1. Sin análisis cargado no se analiza nada
   ══════════════════════════════════════════════════════════════════ */
test("sin análisis, el partido no cuenta como analizado", ()=>{
  L.cargar(PARTIDOS, {});
  igual(L.analizado(claro.id), false, "sin entrada:");
});

test("con texto pero SIN inclinacion, tampoco cuenta como analizado", ()=>{
  /* Es el punto entero del cambio: un análisis que no dice para dónde
     inclina no sirve para la regla de alineación, por más lindo que
     esté escrito. */
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"Algo escrito", veredicto:"Algo más"}});
  igual(L.analizado(claro.id), false, "texto sin dirección:");
});

test("con inclinacion, sí cuenta como analizado", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"Algo", inclinacion:"L"}});
  igual(L.analizado(claro.id), true, "con dirección:");
});

test("una inclinacion inventada se ignora", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"Algo", inclinacion:"Z"}});
  igual(L.analizado(claro.id), false, "valor fuera de L/E/V:");
});

test("inclinacion null es una respuesta válida: no inclina, no marca", ()=>{
  /* Que el analista diga "este partido no inclina para ningún lado" es
     información, y tiene que poder decirlo sin que la app lo trate como
     si no hubiera escrito nada. */
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"Parejo", inclinacion:null}});
  igual(L.analizado(claro.id), false, "sin inclinación declarada:");
});

/* ══════════════════════════════════════════════════════════════════
   2. La dirección sale del análisis, no del modelo

   Es la promesa de Método. Si el lean de la alineación viniera del
   modelo, cambiar la inclinación humana no cambiaría nada.
   ══════════════════════════════════════════════════════════════════ */
test("la inclinacion humana manda sobre el lean del modelo", ()=>{
  const lec = L.lectura(claro);
  igual(lec.lean, "L", "el modelo de este partido:");
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"x", inclinacion:"V"}});
  igual(L.inclinacionDe(claro.id), "V", "la humana:");
  cierto(L.inclinacionDe(claro.id) !== lec.lean,
    "el test no prueba nada si las dos direcciones coinciden");
});

test("con el análisis inclinado al visitante, no se elige nada que exija local", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"x", inclinacion:"V"}});
  L.escalera(claro).forEach(f=>{
    if(!f.op || !f.op.req) return;
    cierto(f.op.req.includes("V"),
      `${f.op.label} exige ${f.op.req.join("/")} y el análisis inclina a V`);
  });
});

test("dar vuelta la inclinacion cambia lo que la escalera elige", ()=>{
  /* La prueba directa de que la dirección no la pone el modelo.

     No sirve exigirlo partido por partido: hay cruces donde los tres
     escalones caen en opciones que no opinan sobre quién gana — "gana
     alguno" vale para L y para V, y los mercados de goles nunca
     contradicen. En esos, dar vuelta la inclinación no cambia nada y
     está bien que no cambie. Lo que sí tiene que pasar es que en el
     archivo haya partidos donde cambie; si no cambiara en ninguno, el
     filtro de alineación no estaría haciendo nada. */
  let cambian = 0, iguales = 0;
  PARTIDOS.forEach(m=>{
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:"L"}});
    const conL = L.escalera(m).map(f=> f.op && f.op.id).join("|");
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:"V"}});
    const conV = L.escalera(m).map(f=> f.op && f.op.id).join("|");
    if(conL === conV) iguales++; else cambian++;
  });
  cierto(cambian > 0,
    `en los ${PARTIDOS.length} partidos, dar vuelta la inclinación nunca cambió la escalera`);
  console.log(`         (cambia en ${cambian} de ${PARTIDOS.length}; en ${iguales} los picks no opinan sobre quién gana)`);
});

test("los mercados de goles nunca contradicen: no opinan sobre quién gana", ()=>{
  ["L","E","V"].forEach(dir=>{
    igual(L.contradice({id:"ov2.5", req:null}, dir), false, `ov2.5 con inclinación ${dir}:`);
    igual(L.contradice({id:"btts_si", req:null}, dir), false, `btts con inclinación ${dir}:`);
  });
});

/* ══════════════════════════════════════════════════════════════════
   3. La marca de la portada se calcula sobre la lectura humana

   Es la marca más estricta de la app: 1X2, sobre la dirección que
   declaró el analista. Si se calculara sobre el lean del modelo, dar
   vuelta la inclinación no cambiaría a qué casilla apunta.
   ══════════════════════════════════════════════════════════════════ */
test("sin inclinacion no hay marca de portada, aunque haya prosa", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"mucho texto", veredicto:"más texto"}});
  igual(L.marcaDeValor(claro), null, "prosa sin dirección:");
});

test("la marca de portada apunta a la dirección del analista, no a la del modelo", ()=>{
  /* Se recorre el archivo buscando un partido donde la marca se
     enciende, y se verifica que la casilla marcada sea exactamente la
     que declaró el análisis. */
  let probados = 0;
  PARTIDOS.forEach(m=>{
    DIRS.forEach(dir=>{
      L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:dir}});
      const marca = L.marcaDeValor(m);
      if(marca === null) return;
      probados++;
      igual(marca, dir, `${m.home} vs ${m.away} con inclinación ${dir}:`);
    });
  });
  cierto(probados > 0, "ningún partido enciende la marca en ninguna dirección");
  console.log(`         (${probados} combinaciones partido×dirección encienden la marca)`);
});

test("la marca puede caer en una dirección que NO es la del modelo", ()=>{
  /* La prueba fuerte: si la marca solo apareciera cuando el analista
     coincide con el modelo, la lectura humana no estaría mandando. */
  let contrarias = 0;
  PARTIDOS.forEach(m=>{
    const lean = L.lectura(m).lean;
    DIRS.filter(d=> d !== lean).forEach(dir=>{
      L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:dir}});
      if(L.marcaDeValor(m) === dir) contrarias++;
    });
  });
  cierto(contrarias > 0,
    "la marca solo se enciende cuando el analista coincide con el modelo — la lectura humana no manda");
  console.log(`         (${contrarias} casos marcan en dirección distinta a la del modelo)`);
});

test("con análisis alineado al modelo, la escalera llega a marcar en algunos partidos", ()=>{
  /* Si no marcara en ninguno, la regla sería inalcanzable y la app
     nunca diría nada — el hueco que hoy tiene por falta de contenido. */
  let alguna = 0;
  PARTIDOS.forEach(m=>{
    const lean = L.lectura(m).lean;
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:lean}});
    if(L.escalera(m).some(f=> f.valor)) alguna++;
  });
  cierto(alguna > 0, "ningún partido llega a marcar valor ni con el análisis alineado");
  console.log(`         (${alguna} de ${PARTIDOS.length} partidos marcarían con análisis alineado)`);
});

test("una sola marca por partido, la de mayor ventaja", ()=>{
  PARTIDOS.forEach(m=>{
    const lean = L.lectura(m).lean;
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:lean}});
    const n = L.escalera(m).filter(f=> f.valor).length;
    cierto(n <= 1, `${m.home} vs ${m.away} marcó ${n} veces`);
  });
});

/* ══════════════════════════════════════════════════════════════════
   4. Una tarjeta, una lectura

   El error que Lucas rechazó, textual: "es como decir, es probable que
   gane River pero paga poco, así que preferimos que juegues una ruleta
   rusa a Racing". El sello del veredicto y la marca dorada no pueden
   apuntar a lados distintos.
   ══════════════════════════════════════════════════════════════════ */
test("el sello del veredicto nunca contradice a la marca dorada", ()=>{
  let revisados = 0;
  PARTIDOS.forEach(m=>{
    DIRS.forEach(dir=>{
      L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:dir}});
      const marca = L.marcaDeValor(m);
      if(!marca) return;
      revisados++;
      const s = L.sello(L.lectura(m), m, dir);
      const esperado = marca === "E" ? "PARTIDO"
        : comoSello(marca === "L" ? m.home : m.away, marca === "L" ? m.away : m.home);
      igual(s[0], esperado,
        `${m.home} vs ${m.away}: marca ${marca} pero el sello dice "${s.join(" / ")}" —`);
    });
  });
  cierto(revisados > 0, "no se revisó ninguna combinación con marca encendida");
  console.log(`         (${revisados} tarjetas con marca revisadas, ninguna se contradice)`);
});

test("el sello sigue la dirección del análisis, no la del modelo", ()=>{
  let contra = 0;
  PARTIDOS.forEach(m=>{
    const lean = L.lectura(m).lean;
    DIRS.filter(d=> d !== lean).forEach(dir=>{
      L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:dir}});
      const s = L.sello(L.lectura(m), m, dir);
      const nom = dir === "E" ? "PARTIDO"
        : comoSello(dir === "L" ? m.home : m.away, dir === "L" ? m.away : m.home);
      igual(s[0], nom, `${m.home} vs ${m.away} con inclinación ${dir} (modelo dice ${lean}):`);
      contra++;
    });
  });
  cierto(contra > 0, "no se probó ninguna dirección distinta a la del modelo");
});

test("cuando el análisis va contra los números, el sello lo dice sin inflarlo", ()=>{
  /* Ni "FAVORITO" ni "LLEGA MEJOR" para una dirección que el modelo ve
     por debajo del 40%: eso sería venderle al usuario una diferencia
     que no existe. */
  PARTIDOS.forEach(m=>{
    const lec = L.lectura(m);
    ["L","V"].forEach(dir=>{
      if(lec.p[dir] >= 0.40) return;
      L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:dir}});
      const s = L.sello(lec, m, dir);
      cierto(!["FAVORITO","LLEGA MEJOR","SIN GOLEADA"].includes(s[1]),
        `${m.home} vs ${m.away}: ${dir} vale ${(lec.p[dir]*100).toFixed(0)}% y el sello dice "${s[1]}"`);
    });
  });
});

/* ══════════════════════════════════════════════════════════════════
   5. El nombre del sello tiene que identificar a un equipo

   Apareció con datos reales: Gimnasia La Plata vs Gimnasia (Mendoza)
   recortaban los dos a "GIMNASIA" y el sello no decía nada.
   ══════════════════════════════════════════════════════════════════ */
test("el sello distingue dos equipos que comparten el nombre", ()=>{
  const g = PARTIDOS.find(m => m.home.startsWith("Gimnasia") && m.away.startsWith("Gimnasia"));
  cierto(g, "el snapshot no tiene el cruce de los dos Gimnasia");
  const local = L.nombreSello(g.home, g.away);
  const visita = L.nombreSello(g.away, g.home);
  cierto(local !== visita, `los dos dieron "${local}"`);
  console.log(`         (${g.home} → ${local} · ${g.away} → ${visita})`);
});

test("con nombres distintos, el recorte no cambia", ()=>{
  igual(L.nombreSello("Boca Juniors", "River Plate"), "BOCA JUNIORS", "nombre corto:");
  igual(L.nombreSello("Independiente Rivadavia", "Fluminense"), "INDEPENDIENTE", "nombre largo:");
});

/* ══════════════════════════════════════════════════════════════════
   6. Otros mercados — la escalera elige uno por franja, pero alguien
   que juega siempre 1X2 o siempre doble oportunidad tiene que poder
   ver esa lectura igual, aunque no haya sido la elegida.
   ══════════════════════════════════════════════════════════════════ */
test("otrosMercados devuelve TODOS los mercados elegibles, no solo los de la escalera", ()=>{
  PARTIDOS.slice(0, 10).forEach(m=>{
    const todos = L.mercados(L.lectura(m).M, m);
    const otros = L.otrosMercados(m);
    igual(otros.length, todos.length, `${m.home} vs ${m.away}:`);
  });
});

test("otrosMercados marca el mismo mercado que ganó la escalera, y ninguno más", ()=>{
  let revisados = 0;
  PARTIDOS.forEach(m=>{
    const lean = L.lectura(m).lean;
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:lean}});
    const marcado = L.escalera(m).find(f=> f.valor);
    if(!marcado) return;
    revisados++;
    const marcados = L.otrosMercados(m).filter(x=> x.esVal);
    igual(marcados.length, 1, `${m.home} vs ${m.away}:`);
    igual(marcados[0].op.id, marcado.op.id, `${m.home} vs ${m.away}:`);
  });
  cierto(revisados > 0, "ningún partido tuvo marca de valor para revisar");
});

test("sin análisis cargado, otrosMercados no marca nada — la escalera sola no alcanza", ()=>{
  /* escalera() calcula .valor a partir del lean del modelo si no hay
     inclinación humana, pero esa marca no es real sin análisis: la
     gatea `analizado()`, igual que en el render de Pronósticos. */
  L.cargar(PARTIDOS, {});
  let marcaron = 0;
  PARTIDOS.forEach(m=>{
    if(L.otrosMercados(m).some(x=> x.esVal)) marcaron++;
  });
  igual(marcaron, 0, "otrosMercados marcó valor sin análisis cargado");
});

console.log(`\n${ok} ok, ${mal} fallando\n`);
process.exit(mal ? 1 : 0);
