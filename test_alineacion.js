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
              mercados, otrosMercados, divergen, tabHistorial, tarjeta, tabPlantel,
              onceProbable,
              cargar: (ms, an, pl) => { MATCHES = ms; ANALISIS = an || {}; PLANTELES = pl || {}; }});
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

console.log(`\n${ok} ok, ${mal} fallando\n`);
process.exit(mal ? 1 : 0);
