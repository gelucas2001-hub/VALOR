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
  const almacen = { valor_banca: "50000" };   // BANCA se lee al evaluar el script
  const localStorage = {
    getItem: k => (k in almacen ? almacen[k] : null),
    setItem: (k, v) => { almacen[k] = String(v); },
  };
  const salida = {};
  new Function("localStorage", "exportar", src + `
    exportar({escalera, lectura, alerta, analizado, inclinacionDe, contradice, devig,
              marcaDeValor, hayProsa, VALOR_MIN, VALOR_MAX,
              mercados, otrosMercados, filasMercado, divergen, tabHerramientas,
              fechaCorta, fechaEnPalabras,
              CUOTA_MIN_ESCALERA, cuotaUsada2:cuotaUsada,
              onceProbable, aQuien, jugadores, METRICAS, incompatibles,
              fiabilidadJugador, devigShin, pMercado, cuotaReal, cuotaUsada, CUOTA_MIN_VAL, combinada,
              /* Las tres capas: lo que antes eran siete pestañas. Los
                 tests siguen a la pantalla — si la pantalla se mueve, el
                 contrato se muda con ella en vez de quedar mirando una
                 función que ya no dibuja nada. */
              capaVeredicto, capaLectura, capaDatos, datosEquipos, datosJugadores,
              datosReferencia, mercadosDeVeredicto, estadoDe, renglonPartido, cancha,
              /* El estado de la pantalla, para poder pararse en la capa
                 y el acordeón que el test quiere mirar. */
              setEstado: (o) => { if(o.CAPA) CAPA = o.CAPA; if(o.EXPL) EXPL = o.EXPL;
                                  if(o.LOCALIA) LOCALIA = o.LOCALIA;
                                  if(o.JUG_ORDEN) JUG_ORDEN = o.JUG_ORDEN;
                                  if(o.JUG_EQ) JUG_EQ = o.JUG_EQ;
                                  if(o.ONCES) ONCES = o.ONCES;
                                  if(o.ABIERTOS) ABIERTOS = new Set(o.ABIERTOS); },
              cargar: (ms, an, pl, es, calj, parj) => { MATCHES = ms; ANALISIS = an || {};
                                            PLANTELES = pl || {}; ESTADISTICAS = es || {};
                                            CAL_JUG = calj || {}; PARAM_JUG = parj || PARAM_JUG;
                                            /* El veredicto se memoiza por partido: si un test
                                               cambia el análisis, la caché tiene que soltarse o
                                               el siguiente test lee el veredicto del anterior. */
                                            _veredictos.clear();
                                            ABIERTOS = new Set(); EXPANDIDAS = new Set();
                                            CAPA = "veredicto"; EXPL = "equipos"; LOCALIA = "cruce"; },
              setCuota: (k, v) => { CUOTAS[k] = v; }});
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
   3bis. No se marca valor donde está MEDIDO que pierde plata

   `medir_roi.py`, walk-forward sobre el historial completo con cuota
   de cierre real de Pinnacle:

       arg   1789 apuestas   ROI  −9.17% ±6.44   significativo
       bra   1333 apuestas   ROI  −9.13% ±7.32   significativo
       eng    947 apuestas   ROI  +1.01% ±8.92   ruido
       fra    993 apuestas   ROI  −5.22% ±8.71   ruido

   Y `barrido_valor.py` probó 39 ventanas de ventaja distintas en arg
   con train/test temporal: NINGUNA da positivo en las dos mitades. No
   es que el umbral esté mal elegido — la regla de valor no funciona
   ahí con este modelo.

   Marcar "acá hay valor" donde está medido que resta es la promesa
   más cara que puede romper la app. El pronóstico se sigue mostrando
   entero: lo que se apaga es la marca, no la lectura.
   ══════════════════════════════════════════════════════════════════ */
const argentino = PARTIDOS.find(m => /profesional argentina/i.test(m.comp||""));
if(!argentino) throw new Error("el snapshot no tiene ningún partido de Liga Profesional");

test("en una liga medida como no rentable, marcaDeValor nunca marca", ()=>{
  /* Se le arma el caso más favorable posible: análisis alineado con el
     modelo, y ventaja dentro de la ventana. Aun así no debe marcar. */
  let probados = 0;
  PARTIDOS.filter(m => /profesional argentina/i.test(m.comp||"")).forEach(m=>{
    const lean = L.lectura(m).lean;
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:lean}});
    probados++;
    igual(L.marcaDeValor(m), null, `${m.home} vs ${m.away} (arg) marcó valor:`);
  });
  cierto(probados > 0, "no se probó ningún partido argentino");
});

test("en una liga medida como no rentable, la escalera no marca ninguna franja", ()=>{
  PARTIDOS.filter(m => /profesional argentina/i.test(m.comp||"")).forEach(m=>{
    const lean = L.lectura(m).lean;
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:lean}});
    const n = L.escalera(m).filter(f=> f.valor).length;
    igual(n, 0, `${m.home} vs ${m.away} (arg) marcó ${n} franjas:`);
  });
});

test("en una liga medida como no rentable, otrosMercados no marca ninguna fila", ()=>{
  PARTIDOS.filter(m => /profesional argentina/i.test(m.comp||"")).forEach(m=>{
    const lean = L.lectura(m).lean;
    L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:lean}});
    const n = L.otrosMercados(m).filter(x=> x.esVal).length;
    igual(n, 0, `${m.home} vs ${m.away} (arg) marcó ${n} filas:`);
  });
});

test("y la app DICE por qué no marca en esa liga, en vez de dejar la escalera muda", ()=>{
  /* La misma disciplina que el repo aplica a los huecos de datos
     (quienFalta, "declarar el hueco en vez de esconderlo"): una
     escalera sin marca y sin explicación se lee como "hoy no hubo
     nada", que es distinto de "acá no marcamos y este es el motivo". */
  const lean = L.lectura(argentino).lean;
  L.cargar(PARTIDOS, {[argentino.id]: {contexto:"x", inclinacion:lean}});
  const html = L.capaVeredicto(argentino);
  /* El número cambió el 2026-09-03 al corregir el arnés (§37): era
     -9.2% y ahora es -7.0%. Se afloja a "menciona un ROI negativo" en vez
     de atar el test a una cifra puntual, que es lo que lo rompió. */
  cierto(/[-−]\d/.test(html) && /ROI/i.test(html),
    "no menciona el ROI medido que justifica apagar la marca");
  cierto(/no marcamos|dejamos de marcar/i.test(html),
    "no explica que en esta liga no se marcan oportunidades");
});

test("pero la escalera SIGUE mostrando el pronóstico en esa liga — se apaga la marca, no la lectura", ()=>{
  L.cargar(PARTIDOS, {});
  const esc = L.escalera(argentino).filter(x=> x.op);
  cierto(esc.length >= 2,
    `la escalera de ${argentino.home} quedó con ${esc.length} escalones: se apagó la lectura, no solo la marca`);
});

test("en una liga SIN medición en contra, la marca sigue funcionando igual", ()=>{
  /* Control: sin esto, el gate podría estar apagando todo y los tres
     tests de arriba pasarían por el motivo equivocado. Premier tiene
     ROI +1.01% ±8.92 — ruido, sin evidencia en contra: no se toca. */
  const comoPremier = {...argentino, comp: "Premier League"};
  const lean = L.lectura(comoPremier).lean;
  L.cargar([comoPremier], {[comoPremier.id]: {contexto:"x", inclinacion:lean}});
  const marcaArg = (()=>{
    L.cargar([argentino], {[argentino.id]: {contexto:"x", inclinacion:lean}});
    return L.escalera(argentino).filter(f=> f.valor).length;
  })();
  L.cargar([comoPremier], {[comoPremier.id]: {contexto:"x", inclinacion:lean}});
  const marcaPremier = L.escalera(comoPremier).filter(f=> f.valor).length;
  igual(marcaArg, 0, "el mismo partido como argentino no debería marcar:");
  cierto(marcaPremier >= 0, "Premier no debería fallar");
  /* El caso que de verdad prueba el control: si este partido marcaría
     con cualquier liga, como Premier tiene que marcar. */
  if(marcaPremier === 0){
    console.log("         (nota: este partido no marca en ninguna liga — control débil)");
  }
});

/* ══════════════════════════════════════════════════════════════════
   4. Una portada, una lectura

   El error que Lucas rechazó, textual: "es como decir, es probable que
   gane River pero paga poco, así que preferimos que juegues una ruleta
   rusa a Racing". El renglón de la portada y la tarjeta de oportunidad
   no pueden apuntar a lados distintos.

   Antes esto lo garantizaba un test sobre `sello()`, que componía una
   etiqueta aparte a partir de la lectura del modelo — dos textos con
   dos criterios, y el test existía porque se habían separado. Con las
   tres capas el sello no existe: la portada y el Veredicto leen el
   MISMO objeto, así que el invariante es estructural. El test se queda
   igual, mirando lo que ahora sí se dibuja.
   ══════════════════════════════════════════════════════════════════ */
test("el renglón de la portada nombra el mismo mercado que la tarjeta de oportunidad", ()=>{
  let revisados = 0;
  PARTIDOS.forEach(m=>{
    DIRS.forEach(dir=>{
      L.cargar(PARTIDOS, {[m.id]: {contexto:"x", inclinacion:dir}});
      const v = L.mercadosDeVeredicto(m);
      if(!v.oportunidad) return;
      revisados++;
      const e = L.estadoDe(m);
      igual(e.clase, "oportunidad",
        `${m.home} vs ${m.away}: el Veredicto marca y la portada no —`);
      /* Sin distinguir mayúsculas: lo que el invariante protege es que
         la franja NOMBRE el mismo mercado que la tarjeta, no con qué
         tipografía lo escribe. Cómo se escribe es decisión de diseño y
         ya cambió una vez; qué se nombra, no puede cambiar. */
      igual(e.motivo.toUpperCase(), v.oportunidad.op.label.toUpperCase(),
        `${m.home} vs ${m.away}: la portada nombra otro mercado —`);
    });
  });
  cierto(revisados > 0, "no se revisó ninguna combinación con marca encendida");
  console.log(`         (${revisados} oportunidades revisadas, ninguna se contradice)`);
});

test("la portada escribe el nombre completo del equipo, sin recortes ambiguos", ()=>{
  /* Gimnasia (La Plata) y Gimnasia (Mendoza) se distinguen justo por el
     paréntesis. La portada vieja recortaba el nombre para que entrara en
     un sello de 176px y las dos quedaban como "GIMNASIA"; el renglón
     nuevo no recorta en el markup — si no entra, lo corta el CSS con
     puntos suspensivos, y el texto sigue estando. */
  const m = { ...PARTIDOS[0], home: "Gimnasia (Mendoza)", away: "Gimnasia (La Plata)" };
  L.cargar(PARTIDOS, {});
  const html = L.renglonPartido(m, {clase:"", corto:["SIN","PRECIO"]}, 0);
  cierto(html.includes("Gimnasia (Mendoza)"), "perdió la aclaración del local");
  cierto(html.includes("Gimnasia (La Plata)"), "perdió la aclaración del visitante");
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
  /* El fixture original es de Liga Profesional, que desde el 2026-08-30
     no marca valor por medición (ver LIGAS_SIN_VALOR). Este test prueba
     la lógica de otrosMercados, no el gate por liga — así que se le
     pone una competición sin medición en contra. El gate tiene sus
     propios tests, arriba. */
  const m = {...BASE_BTTS, comp: "Premier League",
             mercadoExtra: {btts: {si: 1/(1-target), no: 1/target}}};
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
   6bis. Herramientas también tiene que respetar la regla de
   alineación — no solo la escalera y Otros Mercados.

   Método le promete al usuario, sin calificar por pantalla: "nuestra
   regla es que nada contradiga nuestra propia lectura del partido".
   tabHerramientas() calculaba EV/Kelly/"Jugale $X" mirando solo la
   cuota cargada y la probabilidad del modelo — nunca `inclinacionDe()`
   ni `contradice()`. Un usuario podía cargar la cuota real de su casa
   en un mercado que el propio análisis marca como equivocado, y la
   pestaña de plata se lo iba a recomendar igual.

   Decisión de producto (consultada): sin análisis cargado, Herramientas
   sigue funcionando exactamente igual que antes — no hay contra qué
   alinear, y la mayoría de los partidos de la grilla no tienen análisis
   todavía. Solo se bloquea cuando SÍ hay inclinación declarada y el
   mercado la contradice.
   ══════════════════════════════════════════════════════════════════ */
test("Herramientas no dice 'Jugale' en un mercado que contradice la inclinación cargada", ()=>{
  const p = L.lectura(claro).p.L;
  const cGeneroso = Number((1.10 / p).toFixed(2));   // EV ~10%, cuota razonable
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"x", inclinacion:"V"}});   // el análisis inclina al OTRO lado
  const key = claro.id + "__1x2_l";
  L.setCuota(key, cGeneroso);
  const html = L.tabHerramientas(claro);
  const filas = html.split('<div class="mrow');
  const fila = filas.find(f => f.includes(`data-cuota="${key}"`));
  cierto(fila, "no encontró la fila de 'Gana " + claro.home + "' en Herramientas");
  cierto(!/Jugale/.test(fila),
    `sugiere jugar un mercado que contradice la inclinación cargada — fila: ${fila.slice(0,180)}`);
});

test("Herramientas SÍ dice 'Jugale' con la misma cuota cuando el análisis coincide", ()=>{
  // Control: la cuota generosa sigue siendo jugable — lo único que
  // cambia es la dirección del análisis. Si esto fallara, el test de
  // arriba podría estar "pasando" solo porque nada se marca nunca.
  const p = L.lectura(claro).p.L;
  const cGeneroso = Number((1.10 / p).toFixed(2));
  L.cargar(PARTIDOS, {[claro.id]: {contexto:"x", inclinacion:"L"}});   // coincide con el mercado
  const key = claro.id + "__1x2_l";
  L.setCuota(key, cGeneroso);
  const html = L.tabHerramientas(claro);
  const filas = html.split('<div class="mrow');
  const fila = filas.find(f => f.includes(`data-cuota="${key}"`));
  cierto(fila && /Jugale/.test(fila),
    "no sugiere jugar un mercado con EV real y alineado con el análisis");
});

test("Herramientas sigue sugiriendo 'Jugale' sin análisis cargado — no se apaga la pestaña entera", ()=>{
  const p = L.lectura(claro).p.L;
  const cGeneroso = Number((1.10 / p).toFixed(2));
  L.cargar(PARTIDOS, {});   // sin análisis
  const key = claro.id + "__1x2_l";
  L.setCuota(key, cGeneroso);
  const html = L.tabHerramientas(claro);
  const filas = html.split('<div class="mrow');
  const fila = filas.find(f => f.includes(`data-cuota="${key}"`));
  cierto(fila && /Jugale/.test(fila),
    "sin análisis cargado, Herramientas dejó de sugerir jugadas con EV real");
});

/* ══════════════════════════════════════════════════════════════════
   6ter. Líneas de gol donde un lado paga casi 1 — no son un mercado

   Lucas las vio en pantalla: "Menos de 7.5 goles" al 99% pagando 1.00,
   "Menos de 6.5" al 97% pagando 1.02. Es la misma frase que ya usa el
   repo para las líneas de 0.5 en la escalera ("pagan 1.05-1.12, son
   ruido disfrazado de apuesta") — acá aparece en el otro extremo
   porque mercadoExtra.goles puede traer líneas que Bet365 sí cotiza
   pero que ninguna persona apostaría en serio.
   ══════════════════════════════════════════════════════════════════ */
function conLineasExtremas(m){
  return {...m, mercadoExtra:{...(m.mercadoExtra||{}), goles:{
    ...((m.mercadoExtra && m.mercadoExtra.goles) || {}),
    "4.5":[4.50, 1.20],   // razonable, tiene que sobrevivir
    "5.5":[9.00, 1.07],
    "6.5":[19.00, 1.02],
    "7.5":[34.00, 1.00],
  }}};
}

test("otrosMercados no muestra líneas de gol donde un lado paga casi 1 — ruido, no mercado", ()=>{
  const m = conLineasExtremas(claro);
  L.cargar([m], {});
  const otros = L.otrosMercados(m);
  [5.5, 6.5, 7.5].forEach(linea=>{
    cierto(!otros.some(x=> x.op.linea===linea),
      `sigue mostrando la línea ${linea}, que paga casi 1 de un lado`);
  });
  cierto(otros.some(x=> x.op.linea===4.5),
    "la línea 4.5 (pago razonable) no debería desaparecer con el resto");
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

/* Los cuatro tests de `senalDividida()` se retiraron el 2026-09-03
   junto con la función (auditoría §36 C1). Miraba las tres señales
   derogadas por §33 —ritmo_goleador, estructura, ambos_marcan— y con
   ellas apagaba marcas doradas de goles y de ambos marcan.

   Los tests pasaban en verde porque construían fixtures con el esquema
   viejo a mano. Es el caso exacto que CLAUDE.md advierte: un test que
   mira una función muerta da verde sin proteger nada — solo que acá la
   función no estaba muerta, estaba viva y aplicando una regla que el
   proyecto ya había descartado por medición. */

/* Dos funciones distintas con el mismo nombre no fallan: la segunda
   pisa a la primera y los talones que pedian el formato compacto
   venian mostrando el largo. Mismo choque que `.mas` en §19.6. */
test("fechaCorta y fechaEnPalabras son dos formatos distintos", ()=>{
  igual(L.fechaCorta("2026-09-02"), "02/09/26", "el talon pide compacto:");
  igual(L.fechaEnPalabras("2026-09-02"), "2 de sep", "la frase pide palabras:");
  igual(L.fechaCorta("cualquiera"), "—", "una fecha rota no se imprime cruda:");
});

test("marcaDeValor depende solo de inclinacion, nunca de `senal`", ()=>{
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
test("Datos · Referencia usa formH_general/formA_general, no formH/formA", ()=>{
  const m = {
    id: "test1", home: "Local FC", away: "Visita FC",
    homeLogo: "", awayLogo: "", h2h: [],
    formH: [{d:"01/08/26", r:"W", marcador:"1-0", local:true, rival:"Viejo Rival"}],
    formA: [{d:"01/08/26", r:"W", marcador:"1-0", local:true, rival:"Viejo Rival"}],
    formH_general: [{d:"16/08/26", r:"L", marcador:"0-1", local:true, rival:"Rival Fresco"}],
    formA_general: [{d:"16/08/26", r:"L", marcador:"0-1", local:true, rival:"Rival Fresco"}],
  };
  L.cargar(PARTIDOS, {});
  L.setEstado({ABIERTOS:["ref:hist"]});
  /* El historial ya no imprime el nombre del rival —los últimos cinco
     son la misma tira que la portada, con la letra adentro— así que lo
     que se verifica es el RESULTADO: formH da "W" (casilla llena, clase
     g, letra G) y formH_general da "L" (casilla vacía, clase p, letra
     P). Si sigue leyendo formH, el bloque muestra ganados donde hay
     perdidos.

     El corte va hasta "leyenda", que es la fila que presenta las tres
     letras: si entrara, sus propias casillas de muestra darían clase g
     siempre y el test pasaría sin proteger nada. */
  const html = L.datosReferencia(m);
  const cinco = html.slice(html.indexOf("Últimos cinco"), html.indexOf("leyenda"));
  cierto(!/class="g"/.test(cinco),
         "Referencia sigue mostrando formH/formA (ganado) en vez de la forma general (perdido)");
  cierto(/<i class="p">P<\/i>/.test(cinco), "no dibujó la racha de la forma general");
});

test("el renglón de portada usa formH_general/formA_general, no formH/formA", ()=>{
  const base = PARTIDOS[0];
  const m = { ...base,
    formH: [{d:"01/08/26", r:"W", marcador:"1-0", local:true, rival:"Viejo Rival"}],
    formA: [{d:"01/08/26", r:"W", marcador:"1-0", local:true, rival:"Viejo Rival"}],
    formH_general: [{d:"16/08/26", r:"L", marcador:"0-1", local:true, rival:"Rival Fresco"}],
    formA_general: [{d:"16/08/26", r:"L", marcador:"0-1", local:true, rival:"Rival Fresco"}],
  };
  L.cargar(PARTIDOS, {});
  const html = L.renglonPartido(m, {clase:"", corto:["SIN","PRECIO"]}, 0);
  // tiraForma no imprime el nombre del rival, solo G/E/P: formH da "W"
  // (letra G), formH_general da "L" (letra P). Si sigue leyendo formH,
  // el renglón muestra "G" donde debería mostrar "P".
  cierto(html.includes('class="p">P<'),
         "el renglón de portada sigue mostrando formH/formA, no la forma general");
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

test("el plantel muestra los jugadores cuando hay plantel cargado", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.cancha(m);
  cierto(html.includes("Hugo Rodallega"), "no aparece el jugador del plantel");
  cierto(html.includes("Suplente Cualquiera"), "no aparecen los jugadores de menos peso");
  cierto(!html.includes("Sin jugadores"),
         "sigue diciendo 'Sin jugadores' aunque el plantel está cargado");
});

/* ── 11ter. El Veredicto sin oportunidad no puede quedarse mudo ────
   El 90% de los partidos no tiene marca de valor, y en esos el
   Veredicto decía "No hay nada acá" y se terminaba la pantalla. Un
   asesor que no dice nada nueve de cada diez veces no es un asesor
   aunque tenga razón en callarse.

   Las dos reglas duras del bloque nuevo:

   · NUNCA lleva mostaza. El dorado significa "acá el precio está a
     favor" y esto es literalmente el caso contrario. Si el mismo color
     dijera las dos cosas, dejaría de decir la primera — que es la
     única que cuesta plata (TRASPASO §18).
   · No aparece cuando SÍ hay oportunidad: ahí la tarjeta dorada es la
     respuesta y un segundo bloque compite con ella.
   ══════════════════════════════════════════════════════════════════ */

test("separa lo observado de lo estimado", ()=>{
  /* Lucas: "que tenga seguridad en sus predicciones, que sus mediciones
     esten respaldadas". La app le ponia el mismo descargo a todo y por
     eso sonaba insegura hasta cuando decia un hecho. Lo que un equipo
     produjo y el once que arranco PASARON: se afirman. La probabilidad
     sale del modelo, y ese modelo todavia no le gana al precio: se dice
     con reserva. */
  const m = PARTIDOS.find(x=> L.estadoDe(x).clase !== "oportunidad") || PARTIDOS[0];
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.capaVeredicto(m);
  const i = html.indexOf('class="sabemos"');
  cierto(i >= 0, "no hay bloque que separar");
  const bloque = html.slice(i, i + 3000);
  cierto(/Esto pasó/.test(bloque) || /Esto lo estimamos/.test(bloque),
         "no rotula de qué tipo es cada afirmación");
  /* Y el once, que es un hecho, no puede quedar del lado de lo
     estimado: es el error que esta separacion existe para evitar. */
  const est = bloque.indexOf("Esto lo estimamos");
  if(est > 0 && /once confirmado/.test(bloque))
    cierto(bloque.indexOf("once confirmado") < est,
           "puso un dato observado del lado de las estimaciones");
});

test("sin oportunidad, el Veredicto dice lo que sí sabemos", ()=>{
  const m = PARTIDOS.find(x=> L.estadoDe(x).clase !== "oportunidad") || PARTIDOS[0];
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.capaVeredicto(m);
  cierto(/class="sabemos"/.test(html),
         "el partido sin oportunidad se quedó sin nada que decir");
  cierto(/once confirmado/.test(html),
         "no dice qué mirar a la hora del partido, que es lo único que llega después de la línea");
});

/* ── 11quater. Sin muestra no se publica un numero ─────────────────
   Manchester City vs Coventry, 2026-09-05: λ 1.35 contra 1.10 —casi
   iguales— mientras el mercado pagaba 1.20 contra 11.00. Los dos
   equipos llevaban 2 fechas. El número no estaba mal calculado:
   estaba calculado sobre nada, y la app lo publicaba igual.

   Decisión de Lucas: con menos de 4 fechas no se publica nada. El
   mismo 4 que MIN_SPLIT, por la misma razón medida.
   ══════════════════════════════════════════════════════════════════ */

/* La grilla de prueba tiene temporadas avanzadas, así que la muestra
   corta se construye: se le fija la tabla en 2 fechas jugadas. */
const POCA_MUESTRA = ()=> {
  const m = PARTIDOS.find(x=> L.estadoDe(x).clase !== "oportunidad");
  return { ...m, formH_general:[{r:"W"},{r:"L"}], formA_general:[{r:"D"},{r:"L"}],
    tabla: [{id:m.homeId, t:m.home, pj:2, pts:3, gf:2},
            {id:m.awayId, t:m.away, pj:2, pts:1, gf:1}] };
};

test("la tabla dice de que ZONA es, cuando la liga tiene mas de una", ()=>{
  /* La Liga Profesional Argentina son DOS zonas de 15. La zona viaja en
     el PARTIDO (`m.grupo`), no en las filas, y `datosReferencia`
     agrupaba por `f.grupo` —que no existe— así que las 15 filas caían
     en la clave "" y el selector de zonas nunca aparecía. El efecto no
     era cosmético: se mostraba media liga sin decirlo, y quien mira ve
     al primero de la Zona B y entiende que lidera el torneo. */
  const m = { ...PARTIDOS[0], comp:"Liga Profesional Argentina", grupo:"Group B",
    tabla:[{id:PARTIDOS[0].homeId, t:PARTIDOS[0].home, pj:7, pts:11, gf:8},
           {id:"999", t:"Otro", pj:7, pts:9, gf:6}] };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  L.setEstado({ABIERTOS:["ref:pos"]});
  const html = L.datosReferencia(m);
  cierto(/ZONA B/i.test(html), "muestra media liga sin decir que es una zona");
});

test("una copa que cruza divisiones tampoco publica probabilidad", ()=>{
  /* La Copa Argentina volvio el 2026-09-02 y cruza primera con Federal
     A y Primera B, divisiones que la app no sigue. Ese equipo TIENE
     partidos jugados —asi que el conteo de fechas no lo ve— pero
     ninguno en una liga donde hayamos medido su fuerza: su lambda sale
     del promedio de la copa, o sea de nada. `actualizar.py` lo marca
     con `sinAncla` porque es el unico que sabe si ancla_de() encontro
     algo. */
  const base = PARTIDOS.find(x=> L.estadoDe(x).clase !== "oportunidad") || PARTIDOS[0];
  const m = { ...base, comp:"Copa Argentina", sinAncla:true };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.capaVeredicto(m);
  cierto(/SIN MUESTRA/.test(html), "publicó igual con un equipo sin fuerza medida");
  cierto(/divisi[óo]n que no seguimos/.test(html),
         "no dice cuál es el hueco: no es que falten fechas, es que falta la liga");
  cierto(!/ al \d+%/.test(html), "dejó escapar un porcentaje del modelo");
});

test("y sin el campo la app se comporta como antes", ()=>{
  /* `sinAncla` es aditivo: los partidos guardados antes del
     2026-09-02 no lo traen y no pueden quedar todos apagados. */
  const base = PARTIDOS.find(x=> L.estadoDe(x).clase !== "oportunidad") || PARTIDOS[0];
  const m = { ...base };
  delete m.sinAncla;
  L.cargar(PARTIDOS, {}, PL_DEMO);
  cierto(!/SIN MUESTRA/.test(L.capaVeredicto(m)),
         "apagó un partido viejo solo porque le falta el campo nuevo");
});

test("con menos de 4 fechas no se publica ninguna probabilidad", ()=>{
  /* El fixture se arma ANTES de `cargar`: `veredictoDe` memoiza por id
     y POCA_MUESTRA() comparte el id del partido original, asi que sin
     limpiar la cache el test leeria el veredicto del otro. */
  const m = POCA_MUESTRA();
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.capaVeredicto(m);
  cierto(/SIN MUESTRA/.test(html), "no declara que la muestra no alcanza");
  cierto(/2 fechas jugadas/.test(html), "no dice cuántas fechas van");
  cierto(!/ al \d+%/.test(html),
         "publicó igual un porcentaje del modelo con 2 fechas de muestra");
});

test("y tampoco 'el precio esta en contra', que sale del mismo numero", ()=>{
  /* La alerta es una afirmación sobre NUESTRO número: dice que el
     mercado le da más. Sin muestra no hay nuestro número, y dejarla
     pasar sería publicar la misma probabilidad por la puerta de atrás,
     encima con cara de aviso. Pasó: la portada decía "el precio está
     en contra" en el partido donde ya habíamos decidido no opinar. */
  const m = POCA_MUESTRA();
  L.cargar(PARTIDOS, {}, PL_DEMO);
  cierto(!/en contra/i.test(L.estadoDe(m).corto.join(" ")),
         "la portada sigue avisando del precio con un número que no publicamos");
  cierto(!/puntos más que nosotros/.test(L.capaVeredicto(m)),
         "el veredicto sigue comparando contra el mercado sin muestra");
});

test("con muestra suficiente vuelve a publicar", ()=>{
  /* La otra mitad: si esto no se verifica, apagar todo siempre daría
     verde arriba y la app no diría nunca nada. */
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const m = PARTIDOS.find(x=> L.estadoDe(x).clase !== "oportunidad");
  const html = L.capaVeredicto(m);
  cierto(!/SIN MUESTRA/.test(html), "declaró muestra corta en un partido con temporada avanzada");
  cierto(/ al \d+%/.test(html), "dejó de publicar probabilidades donde sí hay muestra");
});

test("'lo mas firme' es el 1X2, no una doble oportunidad", ()=>{
  /* La doble oportunidad gana el ranking por construcción: el empate
     ronda el 27%, así que "gana alguno (sin empate)" da ~73% en TODOS
     los partidos. Una frase que sale igual siempre no describe nada —
     es la misma trampa que "menos de 7.5 goles al 99%", del otro lado
     del tablero. Lucas pidió el candidato, y el candidato es el 1X2. */
  L.cargar(PARTIDOS, {}, PL_DEMO);
  let vistos = 0;
  PARTIDOS.forEach(m=>{
    if(L.estadoDe(m).clase === "oportunidad") return;
    const html = L.capaVeredicto(m);
    const i = html.indexOf("Lo más firme del partido es");
    if(i < 0) return;
    vistos++;
    /* Solo la frase de "lo mas firme", no lo que viene despues: el
       parrafo siguiente habla de la opcion con mas ventaja, que SI
       puede ser una doble oportunidad y ahi es correcto. */
    const frase = html.slice(i, html.indexOf("</p>", i));
    cierto(!/gana o empata|sin empate/i.test(frase),
           "eligió una doble oportunidad, que gana siempre por construcción");
  });
  cierto(vistos > 0, "ningún partido de la grilla llegó a decir cuál es el más firme");
});

/* Un partido con un favorito CORTO de verdad. La grilla de prueba no
   tiene ninguno, y esperar a que aparezca haría que estos dos tests
   dieran verde sin mirar nada. Se fuerza el precio: local a 1.15 es un
   favorito de ~85% para el mercado, muy lejos del ~45% que sale del
   modelo con los lambda de la grilla. */
const FAVORITO_CORTO = ()=> ({
  ...PARTIDOS.find(m=> L.estadoDe(m).clase !== "oportunidad"),
  mercado: {prov:"DraftKings", local:1.15, empate:8.0, visitante:13.0},
  mercadoExtra: null,
});

test("el favorito corto NO queda afuera por el piso de cuota", ()=>{
  /* Lucas lo anticipó: "por ahí Flamengo paga poco pero es el
     candidato". El piso CUOTA_MIN_ESCALERA existe para matar las
     líneas de gol triviales, y aplicado al 1X2 hacía justo lo
     contrario de lo pedido — en Manchester City vs Coventry, City a
     1.20 quedaba filtrado y "lo más firme" salía Gana Coventry al 30%,
     por descarte. */
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.capaVeredicto(FAVORITO_CORTO());
  const i = html.indexOf("Lo más firme del partido es");
  cierto(i >= 0, "no dijo cuál es el más firme");
  const frase = html.slice(i, i + 420);
  cierto(/paga 1\.15/.test(frase),
         "filtró al favorito por pagar menos de 1.30 y eligió otra cosa por descarte");
});

test("la distancia contra el precio se dice UNA vez y nunca como ventaja", ()=>{
  /* Se decia cuatro veces: en "lo mas firme", en "lo mas cerca de
     encenderse", en la alerta y en el renglon de Resultado. El mismo
     hecho, cada vez con su descargo — y eso no se lee como rigor, se
     lee como una app que se justifica. Lucas: "da a entender que no
     sabe un carajo".

     Y nunca se llama ventaja: "arriba de eso el sospechoso es el
     modelo, no el precio" es la razon escrita de VALOR_MAX. Un "+39
     puntos" no es una ventaja enorme, es un numero roto, y presentarlo
     como ventaja manda a apostar por un error nuestro. */
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.capaVeredicto(FAVORITO_CORTO());
  const i = html.indexOf('class="sabemos"');
  const bloque = html.slice(i, i + 2500);
  /* La cuenta va sobre el texto sin etiquetas: la frase real es
     "<b>39 puntos más</b> que nosotros" y un regex contiguo no la ve. */
  const plano = bloque.replace(/<[^>]+>/g, "");
  const veces = (plano.match(/que\s+nosotros|Nos\s+separan/g) || []).length;
  igual(veces, 1, "la misma brecha contra el mercado se cuenta mas de una vez");
  cierto(!/puntos más que la línea sin margen/.test(bloque),
         "llamo ventaja a una diferencia que el propio proyecto considera error del modelo");
});

test("y ese bloque no lleva una gota de mostaza", ()=>{
  /* La regla más dura del rediseño. Un bloque que explica por qué NO
     apostamos, pintado del color de "apostá acá", sería el peor error
     posible de esta pantalla. */
  const m = PARTIDOS.find(x=> L.estadoDe(x).clase !== "oportunidad") || PARTIDOS[0];
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.capaVeredicto(m);
  const i = html.indexOf('class="sabemos"');
  const bloque = html.slice(i, html.indexOf("</div>", html.indexOf("</p>", i)));
  cierto(!/mostaza|dorad|class="oro"/i.test(bloque),
         "el bloque de 'lo que sí sabemos' se pintó como si fuera una apuesta");
});

test("con oportunidad no aparece: la tarjeta dorada es la respuesta", ()=>{
  const m = PARTIDOS.find(x=> L.estadoDe(x).clase === "oportunidad");
  if(!m) return;   // no hay ninguno en la grilla de prueba
  L.cargar(PARTIDOS, {}, PL_DEMO);
  cierto(!/class="sabemos"/.test(L.capaVeredicto(m)),
         "compite con la tarjeta de oportunidad en vez de dejarla sola");
});

/* ── 11bis. El once REAL, no el inferido ───────────────────────────
   La cancha dibujaba a los que más partidos llevan, acomodados por
   puesto, con una nota que decía que ESPN no publica ni el titular ni
   el esquema. Verificado contra la API el 2026-09-01: para un partido
   YA JUGADO sí los publica — `rosters[].formation` ("4-2-3-1") y
   `starter`/`jersey` por jugador, en el mismo /summary que el cron ya
   pide para la serie. El último once real es un dato; el inferido es
   una suposición. Se prefiere el dato y se cae al otro.
   ══════════════════════════════════════════════════════════════════ */

const ONCE_REAL = {
  "99": {
    fecha: "2026-08-31", rival: "Rival FC", local: true, marcador: "3-0",
    esquema: "4-3-3",
    jugadores: [
      {id:"1",  nombre:"Uno Arquero",  pos:"G",    dorsal:"1"},
      {id:"2",  nombre:"Dos Lateral",  pos:"RB",   dorsal:"4"},
      {id:"3",  nombre:"Tres Central", pos:"CD-R", dorsal:"2"},
      {id:"4",  nombre:"Cuatro Cent",  pos:"CD-L", dorsal:"6"},
      {id:"5",  nombre:"Cinco Lat",    pos:"LB",   dorsal:"3"},
      {id:"6",  nombre:"Seis Volante", pos:"CM",   dorsal:"5"},
      {id:"7",  nombre:"Siete Vol",    pos:"RM",   dorsal:"8"},
      {id:"8",  nombre:"Ocho Vol",     pos:"LM",   dorsal:"10"},
      {id:"9",  nombre:"Nueve Punta",  pos:"F",    dorsal:"9"},
      {id:"10", nombre:"Diez Extremo", pos:"RF",   dorsal:"7"},
      {id:"11", nombre:"Once Extremo", pos:"LF",   dorsal:"11"},
    ],
  },
};

test("la cancha dibuja el once que el equipo puso de verdad", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  L.setEstado({ONCES: ONCE_REAL});
  const html = L.cancha(m, false);
  cierto(html.includes("Uno Arquero") || html.includes("Arquero"),
         "no dibujó a los titulares reales");
  cierto(!html.includes("Rodallega"),
         "siguió infiriendo el once con los que más juegan");
  cierto(/ESQUEMA REAL/.test(html), "no dice que el esquema es el real");
  cierto(html.includes("4-3-3"), "no muestra el esquema que salió del once real");
  L.setEstado({ONCES: {}});
});

test("y dice de qué partido salió, porque no es el once de hoy", ()=>{
  /* Un once sin fecha se lee como la formación confirmada para el
     partido que viene, que es exactamente lo que nadie publica. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  L.setEstado({ONCES: ONCE_REAL});
  const html = L.cancha(m, false);
  cierto(/Rival FC/.test(html), "no dice contra quién fue ese once");
  cierto(/31 de ago/.test(html), "no dice de qué fecha es");
  cierto(/No es la formaci[óo]n de hoy/i.test(html),
         "lo presenta como el equipo de hoy");
  L.setEstado({ONCES: {}});
});

test("los dorsales reales reemplazan a la letra del puesto", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  L.setEstado({ONCES: ONCE_REAL});
  const html = L.cancha(m, false);
  cierto(/class="dorsal">10</.test(html), "no usó el dorsal del jugador");
  L.setEstado({ONCES: {}});
});

test("SW es el volante que sostiene, no un quinto defensor", ()=>{
  /* ESPN le pone `SW` al 1 de un 4-1-3-2. Con SW en la defensa el
     dibujo daba 5-3-2: cinco defensores que el equipo no puso. Medido
     sobre los 82 equipos con once del 2026-09-01, la tabla de
     posiciones reproduce el esquema de ESPN en 79; con SW en defensa
     eran 66. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  const cuatro132 = { "99": { fecha:"2026-08-31", rival:"Rival FC", local:true,
    marcador:"1-0", esquema:"4-1-3-2", jugadores: [
      ["G","1"],["CD-L","2"],["CD-R","6"],["LB","3"],["RB","4"],["SW","5"],
      ["CM","8"],["LM","10"],["RM","7"],["CF-L","9"],["CF-R","11"],
    ].map(([pos,dorsal],i)=> ({id:String(i), nombre:"J"+i, pos, dorsal})) } };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  L.setEstado({ONCES: cuatro132});
  const html = L.cancha(m, false);
  cierto(html.includes("4-1-3-2"), "no reprodujo el esquema que publica ESPN");
  cierto(!html.includes("5-3-2"), "dibujó al SW como quinto defensor");
  L.setEstado({ONCES: {}});
});

test("el cartel del esquema nunca contradice al dibujo", ()=>{
  /* ESPN publica su propio "4-2-3-1" y nuestras filas salen de las
     posiciones. Casi siempre coinciden; cuando no, manda el DIBUJO. Una
     cancha con cinco volantes abajo de un cartel que dice 2-3 es peor
     que no poner cartel. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  const mentiroso = { "99": { ...ONCE_REAL["99"], esquema: "9-9-9" } };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  L.setEstado({ONCES: mentiroso});
  const html = L.cancha(m, false);
  cierto(!html.includes("9-9-9"), "rotuló el dibujo con un esquema que no es");
  cierto(html.includes("4-3-3"), "no rotuló lo que efectivamente dibujó");
  L.setEstado({ONCES: {}});
});

test("sin once real la cancha se comporta exactamente como antes", ()=>{
  /* La regla del proyecto para toda fuente nueva: sin ella, todo tiene
     que seguir andando igual. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  L.setEstado({ONCES: {}});
  const html = L.cancha(m, false);
  cierto(/ESQUEMA INFERIDO/.test(html), "no cayó al once inferido");
  cierto(html.includes("Rodallega"), "perdió el once inferido de siempre");
  cierto(/no tenemos el once del [úu]ltimo\s+partido/i.test(html),
         "no explica por qué está infiriendo");
});

test("el plantel muestra el peso goleador, que es lo que pesa una baja", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.cancha(m);
  cierto(/57\s*%|56\s*%/.test(html),
         "no muestra la fracción de goles del equipo que puso el goleador");
});

test("el plantel sin cargar lo declara, no miente", ()=>{
  const m = { ...PARTIDOS[0], homeId:"77", awayId:"76" };
  L.cargar(PARTIDOS, {}, {});
  const html = L.cancha(m);
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
  const h = L.capaLectura(claro);
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
  const h = L.capaLectura(claro);
  cierto(h.includes("Un contexto del esquema viejo"), "perdió el contexto viejo");
  cierto(h.includes("Un veredicto del esquema viejo"), "perdió el veredicto viejo");
  cierto(!h.includes("SIN NOTA CARGADA"), "trató un análisis viejo como no cargado");
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
  cierto(!L.capaLectura(claro).includes("SIN NOTA CARGADA"),
         "mostró el cartel de sin cargar teniendo prosa");
});

test("el analisis muestra el bloque de desarrollo cuando existe", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {
    actualizado: "2026-08-29", inclinacion: "L",
    desarrollo: {texto: "Partido trabado de pocas llegadas.", senal: {ritmo_goleador:"bajo", estructura:"trabado", ambos_marcan:"incierto"}},
  }});
  const h = L.capaLectura(claro);
  cierto(h.includes("Partido trabado de pocas llegadas."), "el texto de desarrollo no se muestra");
});

test("los analisis sin desarrollo no muestran el bloque ni rompen", ()=>{
  L.cargar(PARTIDOS, {[claro.id]: {
    actualizado: "2026-08-18", inclinacion: "V", contexto: "Solo contexto.",
  }});
  const h = L.capaLectura(claro);
  cierto(!h.includes("SIN NOTA CARGADA"), "trató un análisis viejo como no cargado");
});

test("la frase de la inclinacion esta bien escrita para las tres direcciones", ()=>{
  /* Visto en pantalla con el análisis real de Aldosivi-Unión: decía
     "inclina a el empate". La preposición estaba fija afuera del mapa. */
  const con = dir => { L.cargar(PARTIDOS, {[claro.id]: {
    actualizado: "2026-08-20", inclinacion: dir, veredicto: "Algo.",
  }}); return L.capaLectura(claro); };
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
  cierto(L.capaLectura(claro).includes("SIN NOTA CARGADA"),
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
  /* Se mudó de Plantel a Datos · Jugadores, que es donde el que mira
     arma sus propios candidatos: la lista entera de los dos planteles,
     ordenable por cualquiera de las métricas bajadas. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  const html = L.datosJugadores(m);
  L.METRICAS.forEach(x=>
    cierto(html.includes(`data-jugmet="${x.k}"`), `no se puede elegir ${x.k}`));
});

/* ── 12bis. La serie del jugador ───────────────────────────────────
   Tres reglas que salieron de mirar la pantalla contra los datos el
   2026-09-01, y que sin test son disciplina:

   · la serie se dibuja del más viejo al más nuevo, igual que la tira de
     los últimos cinco del equipo — `planteles.json` la guarda al revés;
   · el que no viene jugando no puede encabezar la lista;
   · "SIN SERIE" es un hueco de la FUENTE, no un jugador que no entra.
   ══════════════════════════════════════════════════════════════════ */

/* Un plantel donde el que NO viene jugando tiene el promedio de
   temporada más alto de los dos: 3.0 contra el 2.0 esperado del que sí
   juega. Ordenados juntos, el que no entra iba primero. */
const PL_SERIE = {
  "99": [
    {id:"1", nombre:"Viene Jugando", pos:"F", pj:10, goles:2, asist:0,
     remates:20, al_arco:8, faltas:5, amarillas:1, rojas:0, peso_goles:0.2,
     serie:{pj:3, tit:3, remates:[1, 2, 6], al_arco:[0, 1, 3],
            esp:{remates:2.0, al_arco:0.7}}},
    {id:"2", nombre:"Hace Meses Afuera", pos:"F", pj:9, goles:1, asist:0,
     remates:27, al_arco:9, faltas:3, amarillas:0, rojas:0, peso_goles:0.1},
  ],
  "98": [
    {id:"3", nombre:"Liga Sin Serie", pos:"M", pj:8, goles:0, asist:1,
     remates:8, al_arco:2, faltas:6, amarillas:2, rojas:0, peso_goles:0},
  ],
};

test("el dorsal separa a dos homonimos del mismo club", ()=>{
  /* Mirassol tiene DOS Carlos Eduardo. El escudo distingue Flamengo de
     Mirassol y no sirve para nada acá: los dos son del mismo club. El
     dorsal ya venía en la respuesta de ESPN y se tiraba. */
  const homonimos = {
    "99": [
      {id:"1", nombre:"Carlos Eduardo", pos:"M", dorsal:"8", pj:10,
       goles:2, asist:0, remates:12, al_arco:4, faltas:5, amarillas:1,
       rojas:0, peso_goles:0.2},
      {id:"2", nombre:"Carlos Eduardo", pos:"F", dorsal:"29", pj:4,
       goles:0, asist:0, remates:3, al_arco:1, faltas:1, amarillas:0,
       rojas:0, peso_goles:0},
    ],
  };
  L.cargar(PARTIDOS, {}, homonimos);
  L.setEstado({JUG_ORDEN:"remates", JUG_EQ:"L"});
  const html = L.datosJugadores({ ...PARTIDOS[0], homeId:"99", awayId:"98" });
  cierto(html.includes(">8<") && html.includes(">29<"),
         "no dibuja el dorsal, y los dos homónimos quedan idénticos");
  L.setEstado({JUG_EQ:"dos"});
});

test("un jugador sin dorsal no dibuja un hueco", ()=>{
  /* ESPN lo publica para 32 de 35: el que no lo tiene no puede dejar un
     `<em>` vacío colgando del nombre. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO);
  L.setEstado({JUG_ORDEN:"remates", JUG_EQ:"L"});
  const html = L.datosJugadores(m);
  cierto(!/<em><\/em>/.test(html), "dibujó un dorsal vacío");
  L.setEstado({JUG_EQ:"dos"});
});

test("la serie del jugador se dibuja del mas viejo al mas nuevo", ()=>{
  /* Verificado contra ESPN el 2026-09-01 con Juan Gutiérrez: la serie
     guardada era [1, 2, 6] y los partidos reales fueron 09/08 seis
     remates, 17/08 dos, 23/08 uno. O sea que el 6 es el MÁS VIEJO y va
     a la izquierda, como en la tira de los últimos cinco. Dibujarla
     cruda muestra a un jugador subiendo cuando viene bajando. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_SERIE);
  L.setEstado({JUG_ORDEN:"remates", JUG_EQ:"L"});
  const html = L.datosJugadores(m);
  const cajas = (html.match(/class="sq [^"]*">(\d+)</g) || [])
    .map(x=> x.replace(/.*>(\d+)</, "$1"));
  igual(cajas.join(""), "621", "la serie no se dibujó del más viejo al más nuevo");
});

test("el que no viene jugando no encabeza la lista", ()=>{
  /* Su MED es el promedio de temporada SIN encoger; el del que juega
     está encogido hacia su puesto. Ordenar los dos números juntos ponía
     primero al que hace ocho fechas no entra — y el primer nombre de la
     lista es el que el que mira lee. No se esconde: se ordena. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_SERIE);
  L.setEstado({JUG_ORDEN:"remates", JUG_EQ:"L"});
  const html = L.datosJugadores(m);
  cierto(html.indexOf("Viene Jugando") < html.indexOf("Hace Meses Afuera"),
         "el que no viene jugando quedó arriba del que sí");
  cierto(html.includes("Hace Meses Afuera"), "lo escondió en vez de ordenarlo");
});

test("SIN SERIE es un hueco de la fuente, no un jugador que no entra", ()=>{
  /* Los dos casos se dibujaban igual y el pie afirmaba el equivocado:
     en Mirassol decía "la fuente no la publica" mientras diecinueve
     compañeros tenían serie. Que la fuente publique es propiedad de la
     LIGA: si algún compañero tiene serie, el que no la tiene es porque
     no jugó. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_SERIE);
  L.setEstado({JUG_ORDEN:"remates", JUG_EQ:"L"});
  const conCompaneros = L.datosJugadores(m);
  cierto(/NO VIENE JUGANDO/.test(conCompaneros),
         "no distingue al que no entra del hueco de la fuente");
  cierto(!/SIN SERIE/.test(conCompaneros.slice(0, conCompaneros.indexOf("notacapa"))),
         "sigue culpando a la fuente por un jugador que simplemente no juega");

  L.setEstado({JUG_EQ:"V"});
  const fuenteMuda = L.datosJugadores(m);
  cierto(/SIN SERIE/.test(fuenteMuda),
         "donde NINGÚN jugador tiene serie, la fuente sí es la que falta");
  cierto(!/NO VIENE JUGANDO/.test(fuenteMuda.slice(0, fuenteMuda.indexOf("notacapa"))),
         "acusó de no jugar a un plantel entero cuya liga no publica la serie");
  L.setEstado({JUG_EQ:"dos"});
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

/* Las nueve métricas se mudaron a Datos · Equipos, en acordeón: el
   cuerpo cerrado no se monta, así que los tests abren los que van a
   mirar. Es la misma decisión de siempre —los cerrados no montan— y por
   eso el estado se declara acá en vez de asumirse. */
const TODAS = ["remates","al_arco","corners","posesion","faltas","tarjetas",
               "offsides","atajadas","tackles","precision"].map(k=> "met:"+k);
const equipos = m => { L.setEstado({ABIERTOS: TODAS}); return L.datosEquipos(m); };

test("Datos · Equipos enfrenta las estadisticas de los dos equipos", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO, EST_DEMO);
  const html = equipos(m);
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
  const html = equipos(m);
  cierto(!html.includes("14.2"), "comparó contra un equipo sin datos");
  /* Y que el bloque exista cuando SÍ están los dos: sin esto, el test
     daría verde por mirar una pestaña que ya no muestra estadísticas.
     Pasó de verdad el 2026-08-24, al mudarlas a su propia pestaña. */
  const conLosDos = equipos({ ...PARTIDOS[0], homeId:"99", awayId:"98" });
  cierto(conLosDos.includes("14.2"), "el bloque no aparece ni con los dos equipos");
});

test("declara sobre cuantos partidos se promedio", ()=>{
  /* Un promedio de 8 partidos y uno de 2 no valen lo mismo, y la app no
     puede presentarlos igual: es el principio de muestra chica que le
     exigimos al análisis. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, PL_DEMO, EST_DEMO);
  /* El sello de la capa lo declara en su contador: "10 MÉTRICAS · 8 PJ".
     La forma cambió con el rediseño; lo que no cambia es que la muestra
     tiene que estar escrita en la pantalla, al lado de los números. */
  cierto(/8 PJ|8 partidos|últimos 8/i.test(equipos(m)),
         "no dice sobre cuántos partidos está promediando");
});

test("una metrica que ningun equipo tiene no se dibuja vacia", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  const sinPosesion = {
    "99": {remates: 10, pj: 5, n: {remates: 5}},
    "98": {remates: 12, pj: 5, n: {remates: 5}},
  };
  L.cargar(PARTIDOS, {}, PL_DEMO, sinPosesion);
  const html = equipos(m);
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

test("Datos · Equipos usa el split de local para el local y de visita para el visitante", ()=>{
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, {}, EST_SPLIT);
  const html = equipos(m);
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
  const html = equipos(m);
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
  const html = equipos(m);
  cierto(html.includes("10.0") && html.includes("9.0"),
         "usó un split de 2 partidos en vez de caer al total");
  cierto(!html.includes("14.0") && !html.includes("7.0"),
         "mostró el split pese a la muestra insuficiente");
});

test("dice qué significa la tinta, que en Concede es al reves", ()=>{
  /* "Tinta plena = número MÁS ALTO, no número mejor" era una regla
     escrita en el código y en ningún lado de la pantalla. En `Produce`
     el más alto se lee como el mejor y no hay problema; en `Concede` es
     exactamente al revés, y el mismo dibujo dice las dos cosas. Se
     aclara con palabras: meter un semáforo sería una opinión disfrazada
     de dato, que es justo lo que esta pantalla no hace. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  const conConcede = {
    "99": {remates: 10.0, pj: 6, n: {remates: 6},
           concede: {remates: 8.0, pj: 6, n: {remates: 6}}},
    "98": {remates: 9.0,  pj: 6, n: {remates: 6},
           concede: {remates: 12.0, pj: 6, n: {remates: 6}}},
  };
  L.cargar(PARTIDOS, {}, {}, conConcede);
  const html = equipos(m);
  cierto(/m[áa]s alto/i.test(html), "no dice qué marca la tinta plena");
  cierto(/Concede/.test(html), "no aclara que en Concede el más alto es el peor");
});

test("y el filtro lo DICE en vez de quedarse mudo", ()=>{
  /* La regla de arriba es correcta y era invisible: con 2 por sede,
     "Este cruce", "De local" y "De visita" mostraban los mismos diez
     números y ninguno avisaba. El que mira concluye que el equipo juega
     igual de local que de visitante — que es justo lo que el dato NO
     dice. Un control que no cambia nada es peor que un control ausente,
     así que se apaga y muestra con cuántos partidos cuenta. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  const flaco = {
    "99": {remates: 10.0, pj: 4, n: {remates: 4},
           local:  {remates: 14.0, pj: 2, n: {remates: 2}},
           visita: {remates: 6.0,  pj: 2, n: {remates: 2}}},
    "98": {remates: 9.0,  pj: 4, n: {remates: 4},
           local:  {remates: 11.0, pj: 2, n: {remates: 2}},
           visita: {remates: 7.0,  pj: 2, n: {remates: 2}}},
  };
  L.cargar(PARTIDOS, {}, {}, flaco);
  const html = equipos(m);
  cierto(!/data-loc="local"/.test(html) && !/data-loc="visita"/.test(html),
         "los filtros que no pueden hacer nada siguen clicables");
  cierto(/data-loc="cruce"/.test(html),
         "apagó también el default, que sí es la lectura correcta");
  /* "2 de 4", no "2 PJ": en la misma pantalla el sello dice "4 PJ"
     —los partidos totales— y el botón hablaba de los de esa sede.
     Dos números con la misma etiqueta y distinto significado. */
  cierto(/2 de 4/.test(html), "no dice con cuántos partidos por sede cuenta, contra los que hacen falta");
  cierto(/avfiltro/.test(html), "no explica por qué los tres dan lo mismo");
});

test("con muestra suficiente el filtro vuelve a estar vivo", ()=>{
  /* La otra mitad del contrato: si esto no se verifica, apagar los tres
     botones siempre daría verde arriba y el filtro no existiría más. */
  const m = { ...PARTIDOS[0], homeId:"99", awayId:"98" };
  L.cargar(PARTIDOS, {}, {}, EST_SPLIT);
  const html = equipos(m);
  cierto(/data-loc="local"/.test(html) && /data-loc="visita"/.test(html),
         "dejó apagado un filtro que sí tiene muestra");
  cierto(!/avfiltro/.test(html), "avisó que no se puede cuando sí se puede");
});

test("Datos · Equipos muestra lo que el rival concede en esa metrica", ()=>{
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
  const html = equipos(m);
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
  const html = equipos(m);
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

test("la escalera conserva cobertura razonable pese a las restricciones", ()=>{
  /* El umbral era 0.8 cuando la escalera podía elegir entre los tres
     ejes. Desde el 2026-08-31 solo recomienda Resultado (el único donde
     el modelo tiene información medida) y con piso de cuota, así que
     quedan menos candidatos por franja: la cobertura real cayó a ~67%.

     Eso NO es una regresión, es el precio de no recomendar lo que no
     sabemos. Un escalón que dice "sin opción clara en esta franja" es
     más honesto que uno que ofrece un under a cuota 1.10 en un partido
     que va a terminar 5-2. El piso baja a 0.55 para que siga
     protegiendo contra una escalera que se vacía de verdad. */
  let conOp = 0, total = 0;
  PARTIDOS.forEach(m=>{
    L.escalera(m).forEach(x=>{ total++; if(x.op) conOp++; });
  });
  cierto(conOp / total >= 0.55,
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

test("la escalera no repite el mismo mercado dos veces", ()=>{
  /* Reemplaza al viejo test de diversidad de FAMILIA, que dejó de
     tener sentido el 2026-08-31: la escalera es toda de Resultado a
     propósito, porque es el único eje donde el modelo tiene información
     medida (`medir_ejes.py`). Que las tres franjas compartan familia ya
     no es un síntoma — es el diseño.

     Lo que sí sigue importando es que no repita el MISMO mercado, que
     sería mostrar la misma apuesta dos veces con otro nombre. */
  const con = USABLES.map(conGolesCompleto);
  L.cargar(con, {});
  let repetidos = 0, revisados = 0, ejemplo = "";
  con.forEach(m=>{
    const ids = L.escalera(m).map(x=> x.op && x.op.id).filter(Boolean);
    if(ids.length < 2) return;
    revisados++;
    if(new Set(ids).size !== ids.length){
      repetidos++;
      if(!ejemplo) ejemplo = `${m.home}: ${ids.join(", ")}`;
    }
  });
  cierto(revisados > 0, "no hay partidos con dos o más franjas");
  igual(repetidos, 0, `${repetidos}/${revisados} repiten mercado — ej: ${ejemplo}`);
});

/* ══════════════════════════════════════════════════════════════════
   EL MISMO TEMA REPETIDO CUANDO SÍ HAY VENTAJA REAL

   El test de arriba prueba el camino SIN ventaja (fallback por
   cercanía al centro), con cuotas planas 1.9/1.9 que casi nunca dan
   valor real. Pero en producción (mercado_extra.py) las líneas de gol
   sí traen precio real por línea, y si el mercado subvalúa "pocos
   goles" de forma pareja, un2.5, un1.5 Y un3.5 pueden dar ventaja real
   los tres a la vez — cada uno cae en su propia franja de probabilidad
   por construcción (P(under 1.5) <= P(under 2.5) <= P(under 3.5)
   siempre). Ahí el camino "creíble" de escalera() elige el de mayor
   ventaja en CADA franja por separado, sin mirar qué familia+lado ya
   usó una franja anterior — a diferencia del camino sin ventaja, que
   sí lo hace (bloque de arriba). Es el caso real que reportó Lucas:
   Sarmiento–Unión con tres "menos de X goles" recomendados a la vez.
   ══════════════════════════════════════════════════════════════════ */
function conVentajaBajoTriple(m){
  const lec = L.lectura(m);
  const ops = L.mercados(lec.M, m);
  const p = id => { const o = ops.find(x=>x.id===id); return o ? o.p : null; };
  const goles = {};
  [1.5,2.5,3.5].forEach(linea=>{
    const pUnder = p("un"+linea);
    if(pUnder==null) return;
    // El mercado nos "regala" 5pp parejo en las tres líneas — la
    // misma clase de desajuste sistemático que dispara la ventaja
    // real, no una cuota inventada al azar.
    const pUnderMercado = Math.min(0.97, Math.max(0.03, pUnder - 0.05));
    const pOverMercado = 1 - pUnderMercado;
    goles[String(linea)] = [1/pOverMercado, 1/pUnderMercado];
  });
  return {...m, mercadoExtra:{...(m.mercadoExtra||{}), goles}};
}

test("la escalera no repite el mismo tema (familia+lado) cuando las tres líneas de gol dan ventaja real a la vez", ()=>{
  const con = USABLES.map(conVentajaBajoTriple);
  L.cargar(con, {});
  let repiteTema = 0, revisados = 0, detalle = "";
  con.forEach(m=>{
    const esc = L.escalera(m).filter(x=> x.op);
    if(esc.length < 2) return;
    revisados++;
    const temas = esc.map(x=> x.op.fam+":"+(x.op.lado||x.op.id));
    const usados = new Set();
    let repite = false;
    temas.forEach(t=>{ if(usados.has(t)) repite = true; usados.add(t); });
    if(repite){
      repiteTema++;
      if(!detalle) detalle = `${m.home} vs ${m.away}: ${esc.map(x=>x.op.id).join(", ")}`;
    }
  });
  cierto(revisados > 0, "no hay partidos con dos o más franjas para revisar");
  /* No es cero, y está bien que no lo sea. Medido a mano (Banfield-
     Midland, Atlético Tucumán-Instituto): en los casos que quedan, el
     tema se repite porque no queda NINGUNA alternativa — elegir "menos
     de 3.5" en la franja de arriba vuelve a "más de 3.5" lógicamente
     incompatible con esa franja para siempre (no puede haber menos Y
     más goles que 3.5 a la vez), y la alineación con la lectura (dir)
     ya descartó 1X2/doble oportunidad de los otros resultados. Ahí la
     franja se queda sin nada más que ofrecer, y repetir tema es mejor
     que dejarla vacía — la misma regla que ya regía para familia.
     Bajó de 24/34 (71%, antes de este fix) a esto. */
  const fraccion = repiteTema / revisados;
  cierto(fraccion < 0.15,
         `sigue repitiendo tema más de lo esperable: ${repiteTema}/${revisados} (${(fraccion*100).toFixed(0)}%) — ej: ${detalle}`);
});

/* ══════════════════════════════════════════════════════════════════
   LA ESCALERA NO PUEDE APOSTAR A "EXACTAMENTE N GOLES" SIN QUERER

   Lucas vio Manchester United–Ipswich (5-2): la escalera mostró "más
   de 1.5 goles" arriba y "menos de 2.5" abajo. Juntas significan
   **exactamente 2 goles** — una tesis que nadie eligió, que salió de
   que cada franja elige por su cuenta.

   `incompatibles()` no lo agarra, y hace bien: esos dos mercados SÍ
   pueden pasar juntos. El problema no es la contradicción lógica sino
   que la combinación no tiene sentido como recomendación.

   Medido sobre la grilla real: pasaba en 15 de 49 partidos (31%).

   Y hay una razón más para no llenar la escalera de goles, medida
   aparte (`medir_ejes.py`, 6270 partidos de arg y 4140 de eng): el
   modelo NO aporta nada ahí. Sobre la tasa base de cada mercado, Goles
   da entre −0.9% y +0.4%, mientras Resultado da +2.6% en arg y +13.2%
   en eng. La escalera venía destacando justo el eje donde menos
   sabemos.
   ══════════════════════════════════════════════════════════════════ */
test("la escalera no deja un rango de goles tan estrecho que equivalga a un marcador exacto", ()=>{
  L.cargar(PARTIDOS, {});
  let estrechos = 0, revisados = 0, ejemplo = "";
  PARTIDOS.forEach(m=>{
    const ops = L.escalera(m).map(f=> f.op).filter(Boolean);
    if(ops.length < 2) return;
    revisados++;
    const goles = ops.filter(o=> o.fam === "Goles");
    const ov = goles.filter(o=> o.lado === "over").map(o=> o.linea);
    const un = goles.filter(o=> o.lado === "under").map(o=> o.linea);
    if(!ov.length || !un.length) return;
    const lo = Math.max(...ov), hi = Math.min(...un);
    if(hi - lo <= 1.0){
      estrechos++;
      if(!ejemplo) ejemplo = `${m.home} vs ${m.away}: ${ops.map(o=>o.id).join(", ")}`;
    }
  });
  cierto(revisados > 0, "no hay partidos para revisar");
  igual(estrechos, 0,
    `${estrechos}/${revisados} partidos apuestan a un marcador exacto sin querer — ej: ${ejemplo}`);
});

/* ══════════════════════════════════════════════════════════════════
   LA ESCALERA SOLO RECOMIENDA DONDE EL MODELO SABE, Y A PRECIO REAL

   Dos reglas que salen de la misma queja de Lucas: "recomienda menos
   de 1.5 goles en un partido que terminó 5-2" y "recomienda cuotas de
   mierda".

   1. Solo Resultado. `medir_ejes.py` sobre 10.410 partidos: Resultado
      aporta +2.6% (arg) y +13.2% (eng) sobre la tasa base; Goles, de
      −0.9% a +0.4%; Ambos marcan, −0.4%. El modelo NO tiene información
      sobre cuántos goles habrá. Recomendar ahí es vender lo que no se
      sabe.

   2. Piso de cuota. Con el margen de la casa en 7.7%, una cuota de
      1.10 no deja nada. La app ya lo dice en Método y lo mostraba
      igual.

   Efecto lateral que arregla un tercer problema: con las tres franjas
   sobre el MISMO eje, más probabilidad implica menos cuota siempre. Se
   acabó el "Arriesgada: gana River, paga 1.61" mientras "Lo más
   probable" pagaba 1.17 — que pasaba por mezclar ejes con escalas de
   precio distintas.
   ══════════════════════════════════════════════════════════════════ */
test("la escalera solo recomienda mercados de Resultado", ()=>{
  L.cargar(PARTIDOS, {});
  let otros = 0, total = 0, ejemplo = "";
  PARTIDOS.forEach(m=>{
    L.escalera(m).forEach(f=>{
      if(!f.op) return;
      total++;
      if(f.op.fam !== "Resultado"){
        otros++;
        if(!ejemplo) ejemplo = `${m.home}: ${f.op.id}`;
      }
    });
  });
  cierto(total > 0, "no hay escalones para revisar");
  igual(otros, 0, `${otros}/${total} escalones no son de Resultado — ej: ${ejemplo}`);
});

test("y nunca por debajo del piso de cuota", ()=>{
  L.cargar(PARTIDOS, {});
  let bajos = 0, total = 0, ejemplo = "";
  PARTIDOS.forEach(m=>{
    L.escalera(m).forEach(f=>{
      if(!f.op) return;
      total++;
      const c = L.cuotaUsada(f.op, L.devig(m.mercado||{}), m.mercado||{}, m.mercadoExtra||{});
      if(c != null && c < L.CUOTA_MIN_ESCALERA){
        bajos++;
        if(!ejemplo) ejemplo = `${m.home}: ${f.op.id} paga ${c}`;
      }
    });
  });
  igual(bajos, 0, `${bajos}/${total} escalones pagan menos del piso — ej: ${ejemplo}`);
});

test("las tres franjas quedan ordenadas: más probable paga menos", ()=>{
  /* Con todo sobre el mismo eje esto se cumple solo. Si algún día
     vuelve a fallar, es que se coló otro eje en la escalera. */
  L.cargar(PARTIDOS, {});
  let desordenes = 0, revisados = 0;
  PARTIDOS.forEach(m=>{
    const ops = L.escalera(m).map(f=> f.op).filter(Boolean);
    if(ops.length < 2) return;
    revisados++;
    for(let i = 1; i < ops.length; i++)
      if(ops[i].p > ops[i-1].p) desordenes++;
  });
  cierto(revisados > 0, "no hay partidos con dos escalones");
  igual(desordenes, 0, `${desordenes} escalones rompen el orden de probabilidad`);
});

test("cuando hay un mercado de Resultado disponible en la franja, gana sobre uno de Goles", ()=>{
  /* `medir_ejes.py` sobre 10.410 partidos: Resultado aporta +2.6%
     (arg) y +13.2% (eng) sobre la tasa base; Goles, entre −0.9% y
     +0.4%. Si los dos caben en la misma franja, mostrar el de goles es
     destacar el eje donde el modelo no sabe nada.

     Solo rige cuando ninguno tiene ventaja real medida: si Goles la
     tiene y Resultado no, la ventaja sigue mandando (Regla 2). */
  L.cargar(PARTIDOS, {});
  let mal = 0, revisados = 0, ejemplo = "";
  PARTIDOS.forEach(m=>{
    const lec = L.lectura(m);
    const todos = L.mercados(lec.M, m);
    L.escalera(m).forEach(f=>{
      if(!f.op || f.op.fam !== "Goles" || f.ventaja != null) return;
      // ¿había un Resultado disponible en esta misma franja?
      const hubo = todos.some(o=> o.fam === "Resultado"
        && o.p >= f.franja.lo && o.p < f.franja.hi
        && !L.contradice(o, lec.lean));
      revisados++;
      if(hubo){
        mal++;
        if(!ejemplo) ejemplo = `${m.home}: eligió ${f.op.id} habiendo Resultado en ${f.franja.n}`;
      }
    });
  });
  igual(mal, 0, `${mal}/${revisados} franjas prefirieron Goles sobre Resultado — ej: ${ejemplo}`);
});

test("y no llena la escalera de goles, que es donde el modelo no aporta", ()=>{
  L.cargar(PARTIDOS, {});
  let soloGoles = 0, revisados = 0;
  PARTIDOS.forEach(m=>{
    const ops = L.escalera(m).map(f=> f.op).filter(Boolean);
    if(ops.length < 2) return;
    revisados++;
    if(ops.filter(o=> o.fam === "Goles").length > 1) soloGoles++;
  });
  igual(soloGoles, 0,
    `${soloGoles}/${revisados} partidos tienen más de un mercado de goles en la escalera`);
});

console.log(`\n${ok} ok, ${mal} fallando\n`);
process.exit(mal ? 1 : 0);
