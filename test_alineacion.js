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
              mercados, otrosMercados, divergen, senalDividida, tabHistorial, tarjeta, tabPlantel,
              tabEstadisticas,
              onceProbable, tabAnalisis, aQuien, jugadores, METRICAS, incompatibles,
              fiabilidadJugador, devigShin, pMercado, cuotaReal, cuotaUsada, CUOTA_MIN_VAL, combinada,
              cargar: (ms, an, pl, es, calj, parj) => { MATCHES = ms; ANALISIS = an || {};
                                            PLANTELES = pl || {}; ESTADISTICAS = es || {};
                                            CAL_JUG = calj || {}; PARAM_JUG = parj || PARAM_JUG; }});
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

test("otrosMercados marca AL MENOS el mercado que ganó la escalera", ()=>{
  /* Antes esto era "y ninguno más": con mercadoExtra, un partido puede
     tener ventaja real en más de un mercado (goles extra, ambos
     marcan) sin que sea de la familia que la escalera eligió para su
     única franja. El pick de la escalera sigue teniendo que aparecer
     acá — eso no cambió. */
  let revisados = 0;
  PARTIDOS.forEach(m=>{
    const lean = L.lectura(m).lean;
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:lean}});
    const marcado = L.escalera(m).find(f=> f.valor);
    if(!marcado) return;
    revisados++;
    const marcados = L.otrosMercados(m).filter(x=> x.esVal);
    cierto(marcados.some(x=> x.op.id === marcado.op.id),
           `${m.home} vs ${m.away}: no incluyó el pick de la escalera`);
  });
  cierto(revisados > 0, "ningún partido tuvo marca de valor para revisar");
});

// Vélez vs Defensa: btts_no da 56.97% en el modelo — con -8pp de
// ventaja (adentro de [VALOR_MIN, VALOR_MAX] = [0.06, 0.12]) y libro
// sin margen, la cuota implícita da ~2.04, bien arriba del piso.
const BASE_BTTS = PARTIDOS.find(m=> m.home === "Vélez Sarsfield" && m.away === "Defensa y Justicia");

test("otrosMercados marca cualquier fila con ventaja real dentro de la banda, no solo la de la escalera", ()=>{
  const lean = L.lectura(BASE_BTTS).lean;
  const pNo = L.mercados(L.lectura(BASE_BTTS).M, BASE_BTTS).find(o=> o.id==="btts_no").p;
  const target = pNo - 0.08;
  const m = {...BASE_BTTS, mercadoExtra: {btts: {si: 1/(1-target), no: 1/target}}};
  L.cargar([m], {[m.id]: {contexto:"x", inclinacion:lean}});
  const btts = L.otrosMercados(m).find(x=> x.op.id === "btts_no");
  cierto(btts && Math.abs(btts.ventaja - 0.08) < 1e-6, `ventaja mal calculada: ${btts && btts.ventaja}`);
  cierto(!L.contradice(btts.op, lean), "el fixture eligió mal: btts sí contradice el lean");
  cierto(1/target >= L.CUOTA_MIN_VAL, "el fixture eligió mal: la cuota construida ya está bajo el piso");
  cierto(btts.esVal, "no marcó valor en una fila con ventaja real fuera de la escalera");
});

// Corinthians vs Rosario Central: btts_no da 83.80% en el modelo —
// una probabilidad alta a propósito, para poder lograr una ventaja
// real DENTRO de la banda con una cuota que paga bajo el piso (algo
// que con probabilidades del medio no se puede construir: para que
// la ventaja sea positiva, el mercado tiene que estar todavía más
// convencido que nosotros, y con p~0.55 eso nunca cruza 1.50).
const BASE_ALTA = PARTIDOS.find(m=> m.home === "Corinthians" && m.away === "Rosario Central");

test("el piso de cuota apaga la marca aunque la ventaja sea real y esté en la banda", ()=>{
  const lean = L.lectura(BASE_ALTA).lean;
  const pNo = L.mercados(L.lectura(BASE_ALTA).M, BASE_ALTA).find(o=> o.id==="btts_no").p;
  const target = pNo - 0.08;
  const cuotaEsperada = 1/target;
  cierto(cuotaEsperada < L.CUOTA_MIN_VAL,
         `el fixture no sirve para este caso: la cuota construida (${cuotaEsperada.toFixed(2)}) ya está arriba del piso`);
  const m = {...BASE_ALTA, mercadoExtra: {btts: {si: 1/(1-target), no: cuotaEsperada}}};
  L.cargar([m], {[m.id]: {contexto:"x", inclinacion:lean}});
  const btts = L.otrosMercados(m).find(x=> x.op.id === "btts_no");
  cierto(Math.abs(btts.ventaja - 0.08) < 1e-6, `ventaja mal calculada: ${btts.ventaja}`);
  cierto(!btts.esVal,
         `marcó valor con una ventaja real (${(btts.ventaja*100).toFixed(1)}pp) pero cuota ${cuotaEsperada.toFixed(2)}, bajo el piso de ${L.CUOTA_MIN_VAL}`);
});

test("cuotaUsada() trae la cuota cruda de cada fuente, en el mismo orden que pMercado()", ()=>{
  const mk = {local: 1.8, empate: 3.2, visitante: 4.5, totalLinea: 2.5, totalOver: 1.9, totalUnder: 1.9};
  const mx = {goles: {"1.5": [1.3, 3.2]}, btts: {si: 1.85, no: 1.95}};
  igual(L.cuotaUsada({req:["L"]}, null, mk, mx), 1.8, "1X2 local");
  igual(L.cuotaUsada({req:["E"]}, null, mk, mx), 3.2, "1X2 empate");
  igual(L.cuotaUsada({linea:1.5, lado:"over"}, null, mk, mx), 1.3, "Bet365 antes que DraftKings");
  igual(L.cuotaUsada({linea:2.5, lado:"over"}, null, mk, mx), 1.9, "cae a DraftKings sin Bet365");
  igual(L.cuotaUsada({linea:9.5, lado:"over"}, null, mk, mx), null, "inventó una línea sin cruce");
  igual(L.cuotaUsada({id:"btts_si"}, null, mk, mx), 1.85, "ambos marcan, sí");
});

test("sin análisis, aunque haya ventaja real en mercadoExtra, no marca nada", ()=>{
  const base = PARTIDOS.find(m=> m.lh != null && m.la != null);
  const m = {...base, mercadoExtra: {btts: {si: 1.01, no: 50}}};
  L.cargar([m], {});
  cierto(!L.otrosMercados(m).some(x=> x.esVal),
         "marcó valor con mercadoExtra pero sin análisis cargado");
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

/* ══════════════════════════════════════════════════════════════════
   7. Divergencia modelo/análisis — cuando "Nuestra lectura" de
   Pronósticos nombra a un equipo y "Hacia dónde inclina" de Análisis
   nombra al otro, el usuario tiene que enterarse de que son dos
   lecturas separadas a propósito, no un error de la app.
   ══════════════════════════════════════════════════════════════════ */
test("divergen() detecta cuando el análisis humano no coincide con el modelo", ()=>{
  let vistas = 0;
  PARTIDOS.forEach(m=>{
    const lean = L.lectura(m).lean;
    const otras = DIRS.filter(d=> d !== lean);
    if(!otras.length) return;
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion: otras[0]}});
    const d = L.divergen(m);
    cierto(d, `${m.home} vs ${m.away}: análisis ${otras[0]} vs modelo ${lean}, divergen() dio null`);
    igual(d.dirHumana, otras[0]); igual(d.dirModelo, lean);
    vistas++;
  });
  cierto(vistas > 0, "no se probó ningún caso de divergencia real");
});

test("divergen() no marca nada cuando el análisis coincide con el modelo, o no hay análisis", ()=>{
  PARTIDOS.forEach(m=>{
    const lean = L.lectura(m).lean;
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion: lean}});
    igual(L.divergen(m), null, `${m.home} vs ${m.away} coincide y igual divergió:`);
  });
  L.cargar(PARTIDOS, {});
  PARTIDOS.forEach(m=>{
    igual(L.divergen(m), null, `${m.home} vs ${m.away} sin análisis y igual divergió:`);
  });
});

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
  const m = L.marcaDeValor(claro);
  cierto(m==="L" || m===null, "marca no se rompe (sigue siendo direccion pura)");
});

/* ══════════════════════════════════════════════════════════════════
   8. Historial debe mostrar la forma actual, no solo la de la propia
   competición. Un equipo con partidos infrecuentes en copa (fase de
   grupos) tenía forma vieja de meses en pantalla mientras el archivo
   ya traía forma_general fresca — el bug era no usarla acá.
   ══════════════════════════════════════════════════════════════════ */
test("tabHistorial usa formH_general/formA_general, no formH/formA", ()=>{
  const m = {
    id: "test1", home: "Local FC", away: "Visita FC",
    homeLogo: "", awayLogo: "", h2h: [],
    formH: [{d:"01/08/26", r:"W", marcador:"1-0", local:true, rival:"Viejo Rival"}],
    formA: [{d:"01/08/26", r:"W", marcador:"1-0", local:true, rival:"Viejo Rival"}],
    formH_general: [{d:"16/08/26", r:"L", marcador:"0-1", local:true, rival:"Rival Fresco"}],
    formA_general: [{d:"16/08/26", r:"L", marcador:"0-1", local:true, rival:"Rival Fresco"}],
  };
  const html = L.tabHistorial(m);
  cierto(html.includes("Rival Fresco"), "tabHistorial no muestra el rival de formH_general/formA_general");
  cierto(!html.includes("Viejo Rival"), "tabHistorial sigue mostrando formH/formA en vez de la forma general");
});

test("tarjeta (portada) usa formH_general/formA_general, no formH/formA", ()=>{
  const base = PARTIDOS[0];
  const m = { ...base,
    formH: [{d:"01/08/26", r:"W", marcador:"1-0", local:true, rival:"Viejo Rival"}],
    formA: [{d:"01/08/26", r:"W", marcador:"1-0", local:true, rival:"Viejo Rival"}],
    formH_general: [{d:"16/08/26", r:"L", marcador:"0-1", local:true, rival:"Rival Fresco"}],
    formA_general: [{d:"16/08/26", r:"L", marcador:"0-1", local:true, rival:"Rival Fresco"}],
  };
  L.cargar(PARTIDOS, {});
  const html = L.tarjeta(m, 0, 1);
  // tiraForma no imprime el nombre del rival, solo G/E/P: formH da "W"
  // (letra G), formH_general da "L" (letra P). Si sigue leyendo formH,
  // la tarjeta muestra "G" donde debería mostrar "P".
  const franja = html.slice(html.indexOf('class="eq"'));
  cierto(franja.includes('class="p">P<'), "la tarjeta de portada sigue mostrando formH/formA, no la forma general");
});

/* ══════════════════════════════════════════════════════════════════
   9. Plantel — la pestaña decía "todavía no está la lista de jugadores"
   porque se creía que las estadísticas pedían un llamado por jugador.
   Medido contra la API el 2026-08-20: vienen todas en el mismo pedido
   del roster. Ahora se muestran, y el peso goleador es el número que
   permite distinguir la baja de un titular de la de un suplente.
   ══════════════════════════════════════════════════════════════════ */
const PL_DEMO = {
  "99": [
    {id:"1", nombre:"Hugo Rodallega", pos:"F", pj:26, goles:13, asist:4,
     remates:50, al_arco:22, amarillas:3, rojas:0, peso_goles:0.565},
    {id:"2", nombre:"Suplente Cualquiera", pos:"M", pj:3, goles:0, asist:0,
     remates:1, al_arco:0, amarillas:0, rojas:0, peso_goles:0},
  ],
};

test("tabPlantel muestra los jugadores cuando hay plantel cargado", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.tabPlantel(m);
  cierto(html.includes("Hugo Rodallega"), "no aparece el jugador del plantel");
  cierto(html.includes("Suplente Cualquiera"), "no aparecen los jugadores de menos peso");
  cierto(!html.includes("Sin jugadores"),
         "sigue diciendo 'Sin jugadores' aunque el plantel está cargado");
});

test("tabPlantel muestra el peso goleador, que es lo que pesa una baja", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.tabPlantel(m);
  cierto(/57\s*%|56\s*%/.test(html),
         "no muestra la fracción de goles del equipo que puso el goleador");
});

test("tabPlantel sin plantel cargado lo declara, no miente", ()=>{
  const m = { ...PARTIDOS[0], homeId:"77", awayId:"76" };
  L.cargar(PARTIDOS, {}, {});
  const html = L.tabPlantel(m);
  cierto(!html.includes("Hugo Rodallega"), "mostró un plantel que no corresponde");
  cierto(/todav[íi]a no|no tenemos|sin jugadores/i.test(html),
         "sin plantel cargado no declara el hueco");
});

/* ══════════════════════════════════════════════════════════════════
   10. El once probable que dibuja la cancha. El prototipo de Claude
   Design traía un 4-3-3 hardcodeado como placeholder, esperando datos.
   Ahora los datos existen, así que el esquema se DERIVA de quién juega
   en vez de inventarse — un equipo que juega con tres delanteros y uno
   que juega con dos no pueden dibujarse igual.
   ══════════════════════════════════════════════════════════════════ */
const j_ = (id, pos, pj) => ({id:String(id), nombre:"J"+id, pos, pj,
  goles:0, asist:0, peso_goles:0});

test("onceProbable elige once jugadores, los de más partidos", ()=>{
  const plantel = [
    j_(1,"G",30), j_(2,"G",5),
    j_(3,"D",30), j_(4,"D",29), j_(5,"D",28), j_(6,"D",27), j_(7,"D",4),
    j_(8,"M",30), j_(9,"M",29), j_(10,"M",28), j_(11,"M",27),
    j_(12,"F",30), j_(13,"F",29), j_(14,"F",3),
  ];
  const o = L.onceProbable(plantel);
  const todos = o.lineas.flat();
  igual(todos.length, 11, "no eligió once jugadores");
  cierto(!todos.some(j=> j.id==="7" || j.id==="14" || j.id==="2"),
         "metió a un suplente de pocos partidos en el once");
});

test("onceProbable pone exactamente un arquero, y es el que más jugó", ()=>{
  const plantel = [
    j_(1,"G",30), j_(2,"G",12),
    j_(3,"D",30), j_(4,"D",29), j_(5,"D",28), j_(6,"D",27),
    j_(8,"M",30), j_(9,"M",29), j_(10,"M",28), j_(11,"M",27),
    j_(12,"F",30),
  ];
  const o = L.onceProbable(plantel);
  igual(o.lineas[0].length, 1, "la línea del arquero no tiene exactamente uno");
  igual(o.lineas[0][0].id, "1", "eligió al arquero suplente");
  igual(o.lineas.flat().filter(j=> j.pos==="G").length, 1,
        "hay más de un arquero en el once");
});

test("el esquema sale de los datos, no de un 4-3-3 fijo", ()=>{
  /* Un equipo con cinco defensores y dos delanteros no puede dibujarse
     como 4-3-3: sería inventar una formación que el equipo no usa. */
  const cincoAtras = [
    j_(1,"G",30),
    j_(2,"D",30), j_(3,"D",29), j_(4,"D",28), j_(5,"D",27), j_(6,"D",26),
    j_(7,"M",30), j_(8,"M",29), j_(9,"M",28),
    j_(10,"F",30), j_(11,"F",29),
  ];
  igual(L.onceProbable(cincoAtras).esquema, "5-3-2");

  const cuatroTres = [
    j_(1,"G",30),
    j_(2,"D",30), j_(3,"D",29), j_(4,"D",28), j_(5,"D",27),
    j_(6,"M",30), j_(7,"M",29), j_(8,"M",28),
    j_(9,"F",30), j_(10,"F",29), j_(11,"F",28),
  ];
  igual(L.onceProbable(cuatroTres).esquema, "4-3-3");
});

test("el esquema nunca sale imposible, aunque la fuente clasifique mal", ()=>{
  /* Medido sobre los 42 equipos reales del 2026-08-20: 13 daban
     esquemas que no existen en fútbol — el peor, 7-0-3. No es que esos
     equipos jueguen así: es que ESPN etiqueta como defensor a gente que
     juega de volante. Acotar a rangos reales corrige un error de la
     fuente; no es imponerle una formación al equipo. */
  const malClasificado = [
    j_(1,"G",30),
    j_(2,"D",30), j_(3,"D",29), j_(4,"D",28), j_(5,"D",27),
    j_(6,"D",26), j_(7,"D",25), j_(8,"D",24),
    j_(9,"F",30), j_(10,"F",29), j_(11,"F",28),
  ];
  const o = L.onceProbable(malClasificado);
  const [d, m, f] = o.esquema.split("-").map(Number);
  igual(d + m + f, 10, `${o.esquema}: los de campo no suman diez`);
  cierto(d >= 3 && d <= 5, `${o.esquema}: ${d} defensores no es una defensa real`);
  cierto(f >= 1 && f <= 3, `${o.esquema}: ${f} delanteros no es un ataque real`);
  cierto(m >= 2, `${o.esquema}: un equipo no juega sin mediocampo`);
  igual(o.lineas.flat().length, 11, "perdió jugadores al acotar las líneas");
});

test("onceProbable no rompe con un plantel incompleto", ()=>{
  const o = L.onceProbable([j_(1,"G",5), j_(2,"D",4)]);
  cierto(o && Array.isArray(o.lineas), "devolvió algo que no se puede dibujar");
  cierto(o.lineas.flat().length <= 11, "inventó jugadores que no existen");
  const vacio = L.onceProbable([]);
  cierto(vacio && vacio.lineas.flat().length === 0, "un plantel vacío rompió");
});

/* ── 11. Una lectura por equipo ─────────────────────────────────────
   El 2026-08-19 Lucas leyó el análisis de River-Santa Fe y encontró que
   solo enumeraba bajas de River: "es como que no sé nada de
   Independiente Santa Fe, o sea solo nombrás bajas y qué? Cómo juega?
   Viene bien? Es fuerte de local?".

   La causa no era el texto sino el esquema: con un único campo `contexto`
   nada obligaba a cubrir a los dos equipos, y el hueco no se veía. Con
   un campo por equipo, dejar al rival afuera se nota en la pantalla. */

const analisisCompleto = m => ({[m.id]: {
  actualizado: "2026-08-20", inclinacion: "L",
  local: "El local llega con cuatro victorias seguidas en su cancha.",
  visitante: "El visitante no gana de visitante desde el 12 de mayo.",
  contexto: "Es la vuelta de la llave; la ida terminó 1-1.",
  veredicto: "Llega mejor el local.",
}});

test("el analisis muestra la lectura de cada equipo, con su nombre", ()=>{
  L.cargar(PARTIDOS, analisisCompleto(claro));
  const h = L.tabAnalisis(claro);
  cierto(h.includes("cuatro victorias seguidas"), "no muestra la lectura del local");
  cierto(h.includes("no gana de visitante"), "no muestra la lectura del visitante");
  cierto(h.includes(claro.home) && h.includes(claro.away),
         "no dice de qué equipo habla cada bloque");
});

test("los analisis viejos, con solo contexto y veredicto, siguen andando", ()=>{
  /* `analisis.json` ya tiene partidos escritos con el esquema anterior.
     Agregar campos no puede romperlos: se agrega, no se reemplaza. */
  L.cargar(PARTIDOS, {[claro.id]: {
    actualizado: "2026-08-18", inclinacion: "V",
    contexto: "Un contexto del esquema viejo.",
    veredicto: "Un veredicto del esquema viejo.",
  }});
  const h = L.tabAnalisis(claro);
  cierto(h.includes("Un contexto del esquema viejo"), "perdió el contexto viejo");
  cierto(h.includes("Un veredicto del esquema viejo"), "perdió el veredicto viejo");
  cierto(!h.includes("SIN CARGAR"), "trató un análisis viejo como no cargado");
});

test("un analisis con solo lectura por equipo cuenta como cargado", ()=>{
  /* Al revés del anterior: si la skill escribe local/visitante pero deja
     `contexto` vacío porque no había nada que cruce a los dos equipos,
     eso es un análisis válido, no un partido sin analizar. */
  L.cargar(PARTIDOS, {[claro.id]: {
    actualizado: "2026-08-20", inclinacion: "L",
    local: "Algo del local.", visitante: "Algo del visitante.",
  }});
  cierto(L.hayProsa(claro.id), "lo contó como partido sin nota");
  cierto(!L.tabAnalisis(claro).includes("SIN CARGAR"),
         "mostró el cartel de sin cargar teniendo prosa");
});

test("el analisis muestra el bloque de desarrollo cuando existe", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {
    actualizado: "2026-08-29", inclinacion: "L",
    desarrollo: {texto: "Partido trabado de pocas llegadas.", senal: {ritmo_goleador:"bajo", estructura:"trabado", ambos_marcan:"incierto"}},
  }});
  const h = L.tabAnalisis(claro);
  cierto(h.includes("Partido trabado de pocas llegadas."), "el texto de desarrollo no se muestra");
});

test("los analisis sin desarrollo no muestran el bloque ni rompen", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {
    actualizado: "2026-08-18", inclinacion: "V", contexto: "Solo contexto.",
  }});
  const h = L.tabAnalisis(claro);
  cierto(!h.includes("SIN CARGAR"), "trató un análisis viejo como no cargado");
});

test("la frase de la inclinacion esta bien escrita para las tres direcciones", ()=>{
  /* Visto en pantalla con el análisis real de Aldosivi-Unión: decía
     "inclina a el empate". La preposición estaba fija afuera del mapa. */
  const con = dir => { L.cargar(PARTIDOS, {[claro.id]: {
    actualizado: "2026-08-20", inclinacion: dir, veredicto: "Algo.",
  }}); return L.tabAnalisis(claro); };
  cierto(con("E").includes("al <b>empate"), "escribió 'a el empate'");
  cierto(!con("E").includes("a el "), "quedó una preposición mal armada");
  cierto(con("L").includes("a <b>" + claro.home), "rompió la frase del local");
  cierto(con("V").includes("a <b>" + claro.away), "rompió la frase del visitante");
});

test("aQuien contrae la preposicion para el empate y no para los equipos", ()=>{
  /* El mismo error estaba escrito en dos lugares (Análisis y
     Pronósticos). Vive en una función para arreglarse una sola vez. */
  igual(L.aQuien("E", claro), "al <b>empate</b>");
  igual(L.aQuien("L", claro), `a <b>${claro.home}</b>`);
  igual(L.aQuien("V", claro), `a <b>${claro.away}</b>`);
});

test("sin nada escrito sigue mostrando el hueco declarado", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {actualizado: "2026-08-20", inclinacion: "L"}});
  cierto(L.tabAnalisis(claro).includes("SIN CARGAR"),
         "una inclinación sin prosa no es una nota escrita");
});

/* ── 12. Las estadísticas por jugador ───────────────────────────────
   Lucas empezó a mirar apuestas de estadísticas (remates, al arco,
   faltas, tarjetas) y pidió poder verlas. Los números ya estaban
   bajados en planteles.json desde el 2026-08-20; la pestaña mostraba
   goles y asistencias nada más, y el resto viajaba sin usarse.

   En 375px no entran ocho columnas por fila. La forma en que esto se
   mira de verdad es "quién remata más en este equipo", así que la
   lista se ordena por la métrica elegida en vez de apretar todo. */

test("METRICAS cubre lo que hay bajado, sin inventar campos", ()=>{
  /* Contra el archivo real que escribe el cron, no contra un fixture:
     lo que este test protege es que la pantalla no ofrezca una métrica
     que el pipeline no baja. */
  const pl = JSON.parse(
    fs.readFileSync(path.join(__dirname, "data", "planteles.json"), "utf8"));
  const alguno = Object.values(pl.equipos).find(e=> e.length);
  const campos = Object.keys(alguno[0]);
  L.METRICAS.forEach(x=>{
    cierto(campos.includes(x.k), `la métrica ${x.k} no existe en el plantel`);
    cierto(x.et && x.et.length <= 10, `la etiqueta de ${x.k} no entra en pantalla`);
  });
  cierto(L.METRICAS.some(x=> x.k === "remates"), "falta remates");
  cierto(L.METRICAS.some(x=> x.k === "al_arco"), "falta remates al arco");
  cierto(L.METRICAS.some(x=> x.k === "faltas"), "falta faltas");
});

test("la lista se ordena por la metrica elegida", ()=>{
  const plantel = {"99": [
    {id:"1", nombre:"El Goleador",  pos:"F", pj:10, goles:9, asist:0,
     remates:20, al_arco:9, faltas:2,  amarillas:0, rojas:0, peso_goles:0.9},
    {id:"2", nombre:"El Rompepatas", pos:"M", pj:10, goles:0, asist:0,
     remates:2,  al_arco:0, faltas:30, amarillas:7, rojas:1, peso_goles:0},
  ]};
  L.cargar(PARTIDOS, {}, plantel);
  const porFaltas = L.jugadores("Equipo", "99", "faltas");
  const porGoles  = L.jugadores("Equipo", "99", "goles");
  cierto(porFaltas.indexOf("Rompepatas") < porFaltas.indexOf("Goleador"),
         "ordenando por faltas, el que más falta no quedó primero");
  cierto(porGoles.indexOf("Goleador") < porGoles.indexOf("Rompepatas"),
         "ordenando por goles, el goleador no quedó primero");
});

test("muestra el promedio por partido, que es lo que se mira para esto", ()=>{
  /* "26 remates" no dice nada sin saber en cuántos partidos. Para mirar
     una línea de jugador lo que importa es el número por partido. */
  const plantel = {"99": [
    {id:"1", nombre:"Rematador", pos:"F", pj:10, goles:0, asist:0,
     remates:21, al_arco:7, faltas:0, amarillas:0, rojas:0, peso_goles:0},
  ]};
  L.cargar(PARTIDOS, {}, plantel);
  const h = L.jugadores("Equipo", "99", "remates");
  cierto(h.includes("2.1"), "no muestra los 2.1 remates por partido");
  cierto(h.includes("21"), "perdió el total");
});

test("no divide por cero con un jugador sin partidos", ()=>{
  const plantel = {"99": [
    {id:"1", nombre:"Nunca Jugó", pos:"M", pj:0, goles:0, asist:0,
     remates:0, al_arco:0, faltas:0, amarillas:0, rojas:0, peso_goles:0},
  ]};
  L.cargar(PARTIDOS, {}, plantel);
  const h = L.jugadores("Equipo", "99", "remates");
  cierto(!/NaN|Infinity/.test(h), "el promedio salió NaN o Infinity");
});

test("la metrica sin dato no se inventa en cero", ()=>{
  /* `atajadas` todavía no está en planteles.json: el cron no la baja.
     Un jugador sin el campo no puede aparecer como si tuviera cero
     atajadas medidas — eso sería afirmar un dato que no existe. */
  const plantel = {"99": [
    {id:"1", nombre:"Arquero", pos:"G", pj:10, goles:0, asist:0,
     remates:0, al_arco:0, faltas:0, amarillas:0, rojas:0, peso_goles:0},
  ]};
  L.cargar(PARTIDOS, {}, plantel);
  const h = L.jugadores("Equipo", "99", "atajadas");
  cierto(/—|sin dato/i.test(h), "inventó un cero donde no hay medición");
});

test("el selector de metrica esta en la pantalla y marca la elegida", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.tabPlantel(m);
  L.METRICAS.forEach(x=>
    cierto(html.includes(`data-plmet="${x.k}"`), `no se puede elegir ${x.k}`));
});

/* ── 13. Las estadísticas del equipo ────────────────────────────────
   Vienen del mismo /summary que el pipeline ya pedía para los córners
   del modelo: 25 métricas por equipo y por partido, de las que se
   guardaban 3. Acá se muestran los promedios, enfrentando a los dos
   equipos — que es como se lee esto ("¿quién remata más?"). */

const EST_DEMO = {
  "99": {remates: 14.2, al_arco: 5.1, corners: 6.4, faltas: 11.0,
         posesion: 57.3, tarjetas: 2.1, atajadas: 2.4, offsides: 2.0,
         tackles: 15.0, pases: 380, pases_tot: 470,
         pj: 8, n: {remates: 8, al_arco: 8, corners: 6, faltas: 8}},
  "98": {remates: 8.5, al_arco: 2.6, corners: 3.1, faltas: 14.5,
         posesion: 42.7, tarjetas: 3.4, atajadas: 4.1, offsides: 1.0,
         tackles: 19.0, pases: 240, pases_tot: 350,
         pj: 8, n: {remates: 8, al_arco: 8, corners: 8, faltas: 8}},
};

test("tabEstadisticas enfrenta las estadisticas de los dos equipos", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO, EST_DEMO);
  const html = L.tabEstadisticas(m);
  cierto(html.includes("14.2") && html.includes("8.5"),
         "no muestra los remates de los dos equipos");
  cierto(html.includes("57.3") || html.includes("57"),
         "no muestra la posesión");
});

test("no muestra estadisticas si falta la de alguno de los dos", ()=>{
  /* Enfrentar un número contra un hueco invita a compararlos igual.
     Si de un equipo no hay dato, no hay comparación que mostrar. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"55" };
  L.cargar(PARTIDOS, {}, PL_DEMO, EST_DEMO);
  const html = L.tabEstadisticas(m);
  cierto(!html.includes("14.2"), "comparó contra un equipo sin datos");
  /* Y que el bloque exista cuando SÍ están los dos: sin esto, el test
     daría verde por mirar una pestaña que ya no muestra estadísticas.
     Pasó de verdad el 2026-08-24, al mudarlas a su propia pestaña. */
  const conLosDos = L.tabEstadisticas({ ...PARTIDOS[0], homeId:"99", awayId:"98" });
  cierto(conLosDos.includes("14.2"), "el bloque no aparece ni con los dos equipos");
});

test("declara sobre cuantos partidos se promedio", ()=>{
  /* Un promedio de 8 partidos y uno de 2 no valen lo mismo, y la app no
     puede presentarlos igual: es el principio de muestra chica que le
     exigimos al análisis. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO, EST_DEMO);
  cierto(/8 partidos|últimos 8/i.test(L.tabEstadisticas(m)),
         "no dice sobre cuántos partidos está promediando");
});

test("una metrica que ningun equipo tiene no se dibuja vacia", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  const sinPosesion = {
    "99": {remates: 10, pj: 5, n: {remates: 5}},
    "98": {remates: 12, pj: 5, n: {remates: 5}},
  };
  L.cargar(PARTIDOS, {}, PL_DEMO, sinPosesion);
  const html = L.tabEstadisticas(m);
  cierto(!/posesi[óo]n/i.test(html), "dibujó una fila sin ningún dato");
  cierto(html.includes("10") && html.includes("12"), "perdió la que sí tenía");
});

/* ── 13bis. Local y visitante, no el total mezclado ──────────────────
   Lucas: "no es lo mismo un jugador que remató 5 veces en 5 partidos
   pero hizo 4 en 1" — para el equipo es el mismo problema con el lado
   de la cancha: mostrar el promedio general de los dos equipos cuando
   el partido de HOY tiene uno de local y otro de visitante mezcla dos
   situaciones distintas. actualizar.py ahora guarda `local`/`visita`/
   `concede` además del total; la comparativa tiene que usar el split
   que corresponde a cada uno en ESTE partido. */

const EST_SPLIT = {
  "99": {remates: 10.0, pj: 8, n: {remates: 8}, desvio: {remates: 3.0},
         local: {remates: 14.0, pj: 4, n: {remates: 4}, desvio: {remates: 1.0}},
         visita: {remates: 6.0, pj: 4, n: {remates: 4}, desvio: {remates: 1.0}}},
  "98": {remates: 9.0, pj: 8, n: {remates: 8}, desvio: {remates: 2.0},
         local: {remates: 11.0, pj: 4, n: {remates: 4}, desvio: {remates: 0.5}},
         visita: {remates: 7.0, pj: 4, n: {remates: 4}, desvio: {remates: 0.5}}},
};

test("la comparativa usa el split de local para el local y de visita para el visitante", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, {}, EST_SPLIT);
  const html = L.tabEstadisticas(m);
  cierto(html.includes("14.0"), "no usó el promedio DE LOCAL del equipo 99");
  cierto(html.includes("7.0"), "no usó el promedio DE VISITA del equipo 98");
  cierto(!html.includes("10.0") && !html.includes("9.0"),
         "mostró el total general en vez del split");
});

test("sin split disponible, cae al total en vez de romper", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  const sinSplit = {
    "99": {remates: 10.0, pj: 8, n: {remates: 8}},
    "98": {remates: 9.0,  pj: 8, n: {remates: 8}},
  };
  L.cargar(PARTIDOS, {}, {}, sinSplit);
  const html = L.tabEstadisticas(m);
  cierto(html.includes("10.0") && html.includes("9.0"),
         "no cayó al total cuando no hay local/visita");
});

test("un split con muestra insuficiente NO se usa, aunque exista", ()=>{
  /* Medido el 2026-08-23 sobre los datos reales: el caché tiene mediana
     3 partidos por equipo (tope de DISCIPLINA_N), así que al partirlo en
     local/visita quedan 1-2 por lado. Un promedio con un decimal sobre 2
     partidos es el mismo "muestra chica" que el propio proyecto le
     prohíbe al análisis (principio B). Con menos de MIN_SPLIT se usa el
     total, que al menos duplica la muestra. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  const flaco = {
    "99": {remates: 10.0, pj: 4, n: {remates: 4},
           local:  {remates: 14.0, pj: 2, n: {remates: 2}}},
    "98": {remates: 9.0,  pj: 4, n: {remates: 4},
           visita: {remates: 7.0,  pj: 2, n: {remates: 2}}},
  };
  L.cargar(PARTIDOS, {}, {}, flaco);
  const html = L.tabEstadisticas(m);
  cierto(html.includes("10.0") && html.includes("9.0"),
         "usó un split de 2 partidos en vez de caer al total");
  cierto(!html.includes("14.0") && !html.includes("7.0"),
         "mostró el split pese a la muestra insuficiente");
});

test("la comparativa muestra lo que el rival concede en esa metrica", ()=>{
  /* Lo que Lucas pidió primero: ajustar por rival. "Remata 10" significa
     una cosa contra un equipo que concede 6 y otra contra uno que
     concede 15. El dato ya se calculaba y no se mostraba en ningún
     lado. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  const conConcede = {
    "99": {remates: 10.0, pj: 6, n: {remates: 6},
           concede: {remates: 8.0, pj: 6, n: {remates: 6}}},
    "98": {remates: 9.0,  pj: 6, n: {remates: 6},
           concede: {remates: 15.0, pj: 6, n: {remates: 6}}},
  };
  L.cargar(PARTIDOS, {}, {}, conConcede);
  const html = L.tabEstadisticas(m);
  /* Debajo del local va lo que concede SU RIVAL (el visitante), porque
     eso es contra lo que va a rematar. Y al revés. */
  cierto(html.includes("15.0"), "no muestra lo que concede el visitante bajo el local");
  cierto(html.includes("8.0"), "no muestra lo que concede el local bajo el visitante");
});

test("sin dato de concede, la fila sigue mostrando lo propio", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  const sinConcede = {
    "99": {remates: 10.0, pj: 6, n: {remates: 6}},
    "98": {remates: 9.0,  pj: 6, n: {remates: 6}},
  };
  L.cargar(PARTIDOS, {}, {}, sinConcede);
  const html = L.tabEstadisticas(m);
  cierto(html.includes("10.0") && html.includes("9.0"),
         "perdió los números propios cuando falta concede");
  cierto(!/NaN|undefined/.test(html), "dibujó basura donde no hay concede");
});

/* ── 14. La escalera no puede contradecirse a sí misma ──────────────
   Lucas, después de usar la app varios días: "la incoherencia en las
   apuestas, por ahí te ponía que apuesta segura eran menos de 0.5
   goles y intermedia más de 0.5 goles. Medio que confunde."

   Tenía razón, y era un bug de verdad: escalera() elegía cada franja
   por separado, sin mirar lo que ya habían elegido las otras. Medido
   sobre los 20 partidos reales del 2026-08-23: 3 (15%) mostraban un
   mercado y su contrario al mismo tiempo — "Más de 1.5" arriba y
   "Menos de 1.5" abajo, o "No marcan los dos" y "Ambos marcan".

   Recomendar las dos es decirle al usuario que apueste a que algo pasa
   y a que no pasa. No es un matiz de riesgo: es ruido. */

test("incompatibles() detecta dos mercados que no pueden pasar juntos", ()=>{
  cierto(L.incompatibles("ov1.5", "un1.5"), "más y menos de 1.5 son incompatibles");
  cierto(L.incompatibles("btts_si", "btts_no"), "ambos marcan y no marcan los dos");
  cierto(L.incompatibles("1x2_l", "1x2_e"), "gana el local y empate");
  cierto(L.incompatibles("1x2_l", "dc_x2"), "gana el local y el visitante gana o empata");
  cierto(L.incompatibles("ov2.5", "un1.5"), "más de 2.5 y menos de 1.5");
});

test("incompatibles() no marca lo que sí puede pasar junto", ()=>{
  cierto(!L.incompatibles("1x2_l", "ov2.5"), "el local puede ganar 2-1");
  cierto(!L.incompatibles("1x2_l", "dc_lx"), "gana el local implica que no pierde");
  cierto(!L.incompatibles("btts_si", "ov1.5"), "si ambos marcan hay 2+ goles");
  cierto(!L.incompatibles("un2.5", "1x2_l"), "el local puede ganar 1-0");
});

test("la escalera nunca recomienda un mercado y su contrario", ()=>{
  /* La prueba sobre los partidos reales del snapshot, que es donde
     apareció. No sobre un caso armado: el bug dependía de dónde caían
     las probabilidades reales dentro de las franjas. */
  let choques = 0, detalle = "";
  PARTIDOS.forEach(m=>{
    const ops = L.escalera(m).filter(x=> x.op).map(x=> x.op);
    for(let i=0; i<ops.length; i++)
      for(let j=i+1; j<ops.length; j++)
        if(L.incompatibles(ops[i].id, ops[j].id)){
          choques++;
          if(!detalle) detalle = `${m.home}-${m.away}: "${ops[i].label}" + "${ops[j].label}"`;
        }
  });
  igual(choques, 0, `la escalera se contradice en ${choques} casos. Ej: ${detalle}`);
});

test("al resolver el choque no se pierde la franja si hay alternativa", ()=>{
  /* Sacar la opción contradictoria no puede dejar el escalón vacío
     cuando había otro mercado válido en esa franja: el usuario perdería
     una recomendación legítima por un problema que no es suyo. */
  let conOp = 0, total = 0;
  PARTIDOS.forEach(m=>{
    L.escalera(m).forEach(x=>{ total++; if(x.op) conOp++; });
  });
  cierto(conOp / total >= 0.8,
         `solo ${conOp} de ${total} escalones quedaron con recomendación`);
});

/* ── 15. La lista de jugadores declara de qué fiarse ────────────────
   Hasta el 2026-08-24 esta lista mostraba "+0.5 → 62%" sin que nadie
   hubiera comprobado que cuando dice 62% pasa el 62%. Se midió
   (medir_jugadores.py) y salió que depende mucho de la métrica: remates
   le erra el doble de lo que explica el azar y asistencias casi no le
   erra. El punto de estos tests es que ese hallazgo llegue a la
   pantalla y no se quede en un informe. */

const CALJ = {
  remates:  {n: 618, desvio: 7.3, ruido: 3.5, nivel: "mal", serie: 2,
             texto: "No le creas el porcentaje."},
  asist:    {n: 616, desvio: 0.1, ruido: 0.8, nivel: "bien", serie: 2,
             texto: "Le viene acertando."},
};

test("el veredicto sale del archivo, no se recalcula en el navegador", ()=>{
  L.cargar(PARTIDOS, {}, {}, {}, CALJ);
  const f = L.fiabilidadJugador("remates");
  cierto(f && f.nivel === "mal", "no leyó el nivel medido");
  cierto(f.n === 618, "no leyó sobre cuántas predicciones va");
});

test("una metrica sin medir no inventa un veredicto", ()=>{
  L.cargar(PARTIDOS, {}, {}, {}, CALJ);
  cierto(L.fiabilidadJugador("faltas") === null,
         "devolvió un veredicto para una métrica que no está en el archivo");
  cierto(L.fiabilidadJugador("inventada") === null,
         "devolvió un veredicto para una métrica inexistente");
});

test("un archivo incompleto no se toma como veredicto", ()=>{
  L.cargar(PARTIDOS, {}, {}, {}, {remates: {n: 618, desvio: 7.3}});
  cierto(L.fiabilidadJugador("remates") === null,
         "aceptó una entrada sin nivel ni texto");
});

test("sin archivo de calibracion la app se calla en vez de afirmar", ()=>{
  L.cargar(PARTIDOS, {}, {}, {}, {});
  cierto(L.fiabilidadJugador("remates") === null,
         "afirmó algo sin haber medido");
});

/* ── 16. Quitar el margen: la app usa el mismo método que las mediciones ──

   La `ventaja` que enciende la marca dorada es una resta contra la
   probabilidad de mercado. Cómo se le saca el margen a la cuota decide
   ese número, así que no es un detalle interno.

   Hasta el 2026-08-25 la app repartía el margen parejo entre las tres
   opciones mientras medir_clv.py y medir_historico.py usaban Shin: se
   medía el modelo con una vara y se marcaba valor con otra. Medido
   sobre 11.854 partidos con cuota de cierre real (medir_devig.py),
   Shin le erra la mitad con márgenes como el de DraftKings.

   Los valores esperados de acá salen de correr `devig_shin` en Python.
   Si las dos implementaciones se separan, estos tests son lo que avisa. */

const SHIN_PYTHON = [
  {cuotas: [2.10, 3.20, 3.60], esperado: [0.4520784799, 0.2910292376, 0.2568922824]},
  {cuotas: [1.30, 5.50, 9.00], esperado: [0.7422563048, 0.1634983007, 0.0942453945]},
  {cuotas: [4.50, 3.60, 1.85], esperado: [0.2099630220, 0.2649391954, 0.5250977827]},
  {cuotas: [1.10, 12.0, 26.0], esperado: [0.8944980885, 0.0747893786, 0.0307125328]},
  {cuotas: [2.50, 3.10, 3.05], esperado: [0.3825647289, 0.3061067470, 0.3113285242]},
];

test("el devig de la app da lo mismo que el de Python", ()=>{
  SHIN_PYTHON.forEach(({cuotas, esperado})=>{
    const p = L.devigShin(cuotas);
    cierto(p != null, `devolvió null para ${cuotas.join("/")}`);
    esperado.forEach((e, i)=>{
      cierto(Math.abs(p[i] - e) < 1e-9,
             `${cuotas.join("/")} pos ${i}: JS ${p[i]} vs Python ${e}`);
    });
  });
});

test("las probabilidades sin margen suman uno", ()=>{
  SHIN_PYTHON.forEach(({cuotas})=>{
    const s = L.devigShin(cuotas).reduce((a,b)=>a+b, 0);
    cierto(Math.abs(s - 1) < 1e-9, `${cuotas.join("/")} sumó ${s}`);
  });
});

test("le saca más margen a la cuota alta que a la baja", ()=>{
  // Es la propiedad que define a Shin y la razón de haberlo portado.
  const cuotas = [1.30, 5.50, 9.00];
  const shin = L.devigShin(cuotas);
  const crudo = cuotas.map(c=> 1/c), t = crudo.reduce((a,b)=>a+b, 0);
  const prop = crudo.map(x=> x/t);
  cierto(shin[0] > prop[0], "no le dio más probabilidad al favorito");
  cierto(shin[2] < prop[2], "no le sacó más a la cuota alta");
});

test("sin margen coincide con el reparto parejo", ()=>{
  const justas = [1/0.5, 1/0.3, 1/0.2];
  const shin = L.devigShin(justas);
  [0.5, 0.3, 0.2].forEach((e, i)=>{
    cierto(Math.abs(shin[i] - e) < 1e-6,
           `sin margen movió la probabilidad: ${shin[i]} vs ${e}`);
  });
});

test("una cuota rota no devuelve números inventados", ()=>{
  cierto(L.devigShin(null) === null, "aceptó null");
  cierto(L.devigShin([2.1, 0, 3.6]) === null, "aceptó una cuota en cero");
  cierto(L.devigShin([2.1, -1, 3.6]) === null, "aceptó una cuota negativa");
});

test("devig() sigue devolviendo las tres direcciones con nombre", ()=>{
  const d = L.devig({local: 2.10, empate: 3.20, visitante: 3.60});
  cierto(d && "L" in d && "E" in d && "V" in d, "cambió la forma del retorno");
  cierto(Math.abs(d.L - 0.4520784799) < 1e-9, "L no coincide con Python");
  cierto(Math.abs(d.L + d.E + d.V - 1) < 1e-9, "las tres no suman uno");
  cierto(L.devig(null) === null, "no se protegió de un mercado ausente");
  cierto(L.devig({}) === null, "no se protegió de un mercado vacío");
});

/* ══════════════════════════════════════════════════════════════════
   MERCADOEXTRA (Bet365 vía odds-api.io) — respaldo real de goles y
   ambos marcan. mercados() suma las líneas que Bet365 cotiza de verdad
   a las tres de siempre; pMercado() les saca el margen con Shin, igual
   que a cualquier mercado de dos vías.
   ══════════════════════════════════════════════════════════════════ */

test("mercados() agrega las líneas reales de mercadoExtra.goles", ()=>{
  const M = L.lectura({lh:1.4, la:1.1, rho:0}).M;
  const sinExtra = L.mercados(M, {home:"A", away:"B"});
  const conExtra = L.mercados(M, {home:"A", away:"B",
    mercadoExtra: {goles: {"0.5": [1.1, 8.0], "4.5": [1.05, 12.0]}}});
  cierto(!sinExtra.some(o=>o.id==="ov0.5"), "sin mercadoExtra ya tenía 0.5 de línea");
  cierto(conExtra.some(o=>o.id==="ov0.5") && conExtra.some(o=>o.id==="un0.5"),
         "no agregó la línea 0.5 de Bet365");
  cierto(conExtra.some(o=>o.id==="ov4.5") && conExtra.some(o=>o.id==="un4.5"),
         "no agregó la línea 4.5 de Bet365");
  cierto(conExtra.some(o=>o.id==="ov2.5"), "se comió la línea de siempre");
});

test("pMercado() usa Bet365 cuando hay línea real, y no inventa si no la hay", ()=>{
  const op = {linea: 4.5, lado: "over"};
  const mx = {goles: {"4.5": [1.90, 1.90]}};
  const p = L.pMercado(op, null, {}, mx);
  cierto(Math.abs(p - 0.5) < 1e-9, `esperaba ~0.5 sin margen, dio ${p}`);
  cierto(L.pMercado(op, null, {}, {}) === null, "inventó un precio sin mercadoExtra");
  cierto(L.pMercado(op, null, {}, null) === null, "no tolera mercadoExtra ausente");
});

test("pMercado() sigue cayendo a DraftKings cuando Bet365 no tiene esa línea", ()=>{
  const op = {linea: 2.5, lado: "under"};
  const mk = {totalLinea: 2.5, totalOver: 1.83, totalUnder: 2.00};
  const p = L.pMercado(op, null, mk, {goles: {"4.5": [1.9, 1.9]}});
  const co = 1/1.83, cu = 1/2.00;
  cierto(Math.abs(p - cu/(co+cu)) < 1e-9, "no cayó al precio de DraftKings");
});

test("pMercado() devigea 'ambos marcan' con el precio real de Bet365", ()=>{
  const mx = {btts: {si: 1.90, no: 1.90}};
  const psi = L.pMercado({id:"btts_si"}, null, {}, mx);
  const pno = L.pMercado({id:"btts_no"}, null, {}, mx);
  cierto(Math.abs(psi - 0.5) < 1e-9, `esperaba ~0.5, dio ${psi}`);
  cierto(Math.abs(psi + pno - 1) < 1e-9, "las dos puntas no suman uno");
  cierto(L.pMercado({id:"btts_si"}, null, {}, {}) === null,
         "inventó ambos marcan sin mercadoExtra");
});

/* ══════════════════════════════════════════════════════════════════
   cuotaReal() — la cuota de Bet365 lista para Herramientas, sin que
   el usuario la tipee. Cero si no hay cruce: ahí sigue pidiendo la
   carga manual, igual que siempre.
   ══════════════════════════════════════════════════════════════════ */

const M_CON_EXTRA = {
  mercadoExtra: {
    "1x2": {local: 2.0, empate: 3.3, visitante: 3.6},
    dc: {"1X": 1.25, "12": 1.35, "X2": 1.7},
    btts: {si: 1.85, no: 1.9},
    goles: {"2.5": [1.9, 1.95]},
  },
};

test("cuotaReal() trae el 1X2 real de Bet365", ()=>{
  igual(L.cuotaReal(M_CON_EXTRA, {id:"1x2_l"}), 2.0);
  igual(L.cuotaReal(M_CON_EXTRA, {id:"1x2_e"}), 3.3);
  igual(L.cuotaReal(M_CON_EXTRA, {id:"1x2_v"}), 3.6);
});

test("cuotaReal() trae la doble oportunidad real", ()=>{
  igual(L.cuotaReal(M_CON_EXTRA, {id:"dc_lx"}), 1.25);
  igual(L.cuotaReal(M_CON_EXTRA, {id:"dc_x2"}), 1.7);
  igual(L.cuotaReal(M_CON_EXTRA, {id:"dc_12"}), 1.35);
});

test("cuotaReal() trae ambos marcan real", ()=>{
  igual(L.cuotaReal(M_CON_EXTRA, {id:"btts_si"}), 1.85);
  igual(L.cuotaReal(M_CON_EXTRA, {id:"btts_no"}), 1.9);
});

test("cuotaReal() trae una línea de gol real, por lado", ()=>{
  igual(L.cuotaReal(M_CON_EXTRA, {linea:2.5, lado:"over"}), 1.9);
  igual(L.cuotaReal(M_CON_EXTRA, {linea:2.5, lado:"under"}), 1.95);
});

test("cuotaReal() da null sin cruce — Herramientas sigue pidiendo la carga a mano", ()=>{
  igual(L.cuotaReal({}, {id:"1x2_l"}), null);
  igual(L.cuotaReal({}, {linea:2.5, lado:"over"}), null);
  igual(L.cuotaReal(M_CON_EXTRA, {linea:4.5, lado:"over"}), null,
        "inventó una línea que Bet365 no cotiza en este partido");
});

/* ══════════════════════════════════════════════════════════════════
   BALANCE DE FAMILIAS EN LA ESCALERA

   mercados() creció de 3 líneas de gol a 7 para darle precio real a
   más filas de "Otros mercados". Eso multiplicó los candidatos de
   Goles a 14 contra 8 de Resultado+Ambos juntos — y cuando ninguno es
   "creíble", la escalera elige el más cercano al centro de la franja
   ENTRE TODOS mezclados, así que Goles gana casi siempre por pura
   cantidad, no porque sea mejor. Medido el 2026-08-26 sobre la grilla
   real: 115 de 135 franjas eran Goles (85%), y como consecuencia
   combinada() — que necesita una pata de "Resultado" — dejó de
   generar en 42 de 45 partidos (93%).

   La escalera tiene que elegir su franja del conjunto CHICO de
   siempre (Resultado, Ambos, y las tres líneas clásicas de gol). Las
   líneas extra siguen enteras en mercados() para Otros Mercados y
   Herramientas — no se pierde cobertura ahí, solo se saca de la
   competencia por el titular de cada franja.
   ══════════════════════════════════════════════════════════════════ */

// Le agrega las 7 líneas de gol como haría un cruce real con Bet365 —
// las cuotas no importan para este test (la densidad rompe el balance
// aunque no haya ventaja en ninguna), solo que existan.
function conGolesCompleto(m){
  const goles = {};
  for(let n=0.5; n<=6.5; n++) goles[String(n)] = [1.9, 1.9];
  return {...m, mercadoExtra: {...(m.mercadoExtra||{}), goles}};
}
const USABLES = PARTIDOS.filter(m=> m.lh != null && m.la != null);

test("escalera() no deja que las líneas extra de gol aplasten a Resultado y Ambos por cantidad", ()=>{
  const con = USABLES.map(conGolesCompleto);
  L.cargar(con, {});
  const conteo = {Resultado:0, Goles:0, Ambos:0};
  let total = 0;
  con.forEach(m=>{
    L.escalera(m).forEach(f=>{
      if(!f.op) return;
      total++; conteo[f.op.fam]++;
    });
  });
  cierto(total > 0, "no hay franjas para revisar");
  const fraccionGoles = conteo.Goles / total;
  cierto(fraccionGoles < 0.6,
         `Goles sigue aplastando: ${conteo.Goles}/${total} (${(fraccionGoles*100).toFixed(0)}%) — Resultado ${conteo.Resultado}, Ambos ${conteo.Ambos}`);
});

test("mercados() sigue trayendo las 7 líneas — Otros mercados y Herramientas no pierden cobertura", ()=>{
  const m = conGolesCompleto(USABLES[0]);
  const lineas = new Set(
    L.mercados(L.lectura(m).M, m).filter(o=>o.fam==="Goles").map(o=>o.linea)
  );
  [0.5,1.5,2.5,3.5,4.5,5.5,6.5].forEach(n=> cierto(lineas.has(n), `mercados() perdió la línea ${n}`));
});

test("combinada() vuelve a encontrar una pata de Resultado en la mayoría de los partidos", ()=>{
  const con = USABLES.map(conGolesCompleto);
  L.cargar(con, {});
  const conCombinada = con.filter(m=> L.combinada(m)).length;
  cierto(conCombinada / con.length > 0.3,
         `combinada() sigue casi sin generar: ${conCombinada}/${con.length}`);
});

/* ══════════════════════════════════════════════════════════════════
   DIVERSIDAD DE FAMILIA EN LA ESCALERA

   Cuando ninguna opción de una franja es "creíble" (sin ventaja real
   medida), se elige la más cercana al centro de la banda — y ESO
   favorece sistemáticamente a Goles sobre Resultado, con o sin
   Bet365: los totales de gol se reparten suave por toda la
   probabilidad; Local/Empate/Visita se agrupan en pocos valores
   correlacionados. Medido: 98 de 135 franjas se resuelven así (73%),
   y por eso combinada() — que necesita una pata de Resultado con
   p≥50% — pasó de generar en 22/45 (sin mercadoExtra) a 9/45.

   No se saca el pick sin evidencia (dejaría la mayoría de los
   partidos con la escalera vacía, que es peor que mostrar la lectura
   del modelo sin marca). En cambio, al elegir por cercanía al centro,
   se prioriza una familia que TODAVÍA no haya ganado una franja
   anterior de este mismo partido, si hay una opción razonable — así
   no repite lo mismo tres veces solo porque una familia tiene más
   candidatos. ══════════════════════════════════════════════════════════════════ */

test("la escalera no repite la misma familia en las tres franjas si hay alternativa", ()=>{
  // Con mercadoExtra real, Goles(1.5/2.5/3.5) tiene precio real en las
  // tres líneas (antes solo 2.5 vía DraftKings) y gana el "más cerca
  // del centro" más seguido — el mismo escenario que hoy en la app.
  const con = USABLES.map(conGolesCompleto);
  L.cargar(con, {});
  let mismaFamilia = 0, revisados = 0;
  con.forEach(m=>{
    const esc = L.escalera(m).filter(x=> x.op);
    if(esc.length < 2) return;
    revisados++;
    const familias = new Set(esc.map(x=> x.op.fam));
    if(familias.size === 1) mismaFamilia++;
  });
  cierto(revisados > 0, "no hay partidos con dos o más franjas para revisar");
  const fraccion = mismaFamilia / revisados;
  cierto(fraccion < 0.5,
         `sigue repitiendo la misma familia en las tres franjas: ${mismaFamilia}/${revisados} (${(fraccion*100).toFixed(0)}%)`);
});

console.log(`\n${ok} ok, ${mal} fallando\n`);
process.exit(mal ? 1 : 0);
