/* ══════════════════════════════════════════════════════════════════
   TEST DE LA PROBABILIDAD DE UNA LÍNEA

   Corré:  node test_probabilidad.js

   Por qué existe: el mercado no vende promedios, vende LÍNEAS. Un
   promedio de 2.0 remates no contesta "¿pasa 3.5?", y peor: dos
   jugadores con el mismo promedio pueden tener chances opuestas según
   lo regulares que sean. Lucas lo dijo antes que nadie acá: "no es lo
   mismo un jugador que remató 5 veces en 5 partidos pero hizo 4 en 1".

   El test central es ese: con la MISMA media, más irregularidad tiene
   que subir la chance por encima de la media y bajarla por debajo. Si
   eso no se cumple, la herramienta no sirve para lo que se hizo.
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
    exportar({ probMayor, lineasDe, pesoEquipo, bloqueLineas, lineaJugador, filaJugador,
               cargarJug: p => { PARAM_JUG = p; },
               cargarEst: (eq, par) => { ESTADISTICAS = eq; PARAMETROS = par; } });
  `)(localStorage, o => Object.assign(salida, o));
  return salida;
}

const { probMayor, lineasDe, pesoEquipo, bloqueLineas, cargarEst,
        lineaJugador, filaJugador, cargarJug } = cargarLogica();

let ok = 0, fallan = 0;
function prueba(nombre, cond){
  if(cond){ ok++; console.log("  ok   " + nombre); }
  else    { fallan++; console.log("  FALLA " + nombre); }
}
const cerca = (a, b, tol) => Math.abs(a - b) < (tol || 0.005);

console.log("");
console.log("probMayor() — cuánto de la campana queda arriba de la línea");
console.log("");

/* Poisson puro (disp = 1) contra el valor exacto: P(X>=1) = 1 - e^-2. */
prueba("Poisson da el valor exacto conocido",
       cerca(probMayor(2, 1, 0.5), 1 - Math.exp(-2)));
/* P(X>=0) es todo: ninguna línea de 0.5 para abajo se puede perder. */
prueba("una línea por debajo de cero es segura", probMayor(3, 1, -0.5) === 1);

prueba("baja cuando sube la línea",
       probMayor(10, 1.5, 8.5) > probMayor(10, 1.5, 10.5));
prueba("sube cuando sube la media",
       probMayor(12, 1.5, 10.5) > probMayor(8, 1.5, 10.5));
prueba("siempre queda entre 0 y 1", [0.5, 4.5, 20.5, 60.5]
       .every(L => { const p = probMayor(9, 2.9, L); return p >= 0 && p <= 1; }));

console.log("");
console.log("el hallazgo de Lucas: la irregularidad cambia de signo");
console.log("");

/* Misma media, distinta constancia. Arriba de la media el irregular
   tiene MÁS chance; abajo, MENOS. Es el mismo jugador para un promedio
   y dos apuestas opuestas para una línea. */
const MU = 2;
const parejo = probMayor(MU, 1, 3.5), errat = probMayor(MU, 2.5, 3.5);
prueba("arriba de la media, el irregular tiene más chance", errat > parejo);
const parejoB = probMayor(MU, 1, 0.5), erratB = probMayor(MU, 2.5, 0.5);
prueba("abajo de la media, el irregular tiene menos chance", erratB < parejoB);
prueba("y la diferencia no es decorativa", (errat - parejo) > 0.02);

/* Al revés con una métrica MÁS regular que Poisson: las tarjetas
   midieron disp 0.72. Ahí las colas se achican, no se agrandan. */
prueba("una métrica más regular que Poisson achica la cola de arriba",
       probMayor(2.3, 0.72, 5.5) < probMayor(2.3, 1, 5.5));
prueba("y engorda el centro",
       probMayor(2.3, 0.72, 1.5) > probMayor(2.3, 1, 1.5));

console.log("");
console.log("lo que no se puede calcular no se inventa");
console.log("");

prueba("sin media no hay probabilidad", probMayor(null, 1.5, 2.5) === null);
prueba("una media de cero tampoco", probMayor(0, 1.5, 2.5) === null);
prueba("una media inválida tampoco", probMayor(NaN, 1.5, 2.5) === null);
prueba("una dispersión ausente cae a Poisson, no rompe",
       cerca(probMayor(2, null, 0.5), 1 - Math.exp(-2)));

/* Con medias altas y dispersión alta la cuenta itera mucho: no puede
   devolver NaN ni pasarse de 1 por acumulación de error. */
const alto = probMayor(400, 25, 380.5);
prueba("con números grandes sigue siendo un número", isFinite(alto));
prueba("y sigue estando en rango", alto >= 0 && alto <= 1);


console.log("");
console.log("lineasDe() — las líneas que rodean a lo esperado");
console.log("");

prueba("centra la escalera en lo esperado",
       JSON.stringify(lineasDe(4.7)) === JSON.stringify([3.5, 4.5, 5.5, 6.5]));
prueba("no ofrece líneas negativas ni la de cero",
       lineasDe(0.6).every(L => L > 0));
prueba("siempre son medias líneas (no hay empate posible)",
       lineasDe(9.2).every(L => Math.abs(L % 1) === 0.5));
prueba("con media alta se corre con ella",
       lineasDe(13.4)[0] === 11.5);

console.log("");
console.log("pesoEquipo() — cuánto de este número es del equipo y cuánto de la liga");
console.log("");

/* Con k=200 (remates: los equipos no se distinguen con esta muestra)
   cuatro partidos casi no mueven la aguja. Con k=7.1 (faltas, que sí
   son estilo del equipo) los mismos cuatro partidos pesan un tercio.
   Decirlo es la diferencia entre informar y aparentar precisión. */
prueba("con k alto el equipo casi no pesa", pesoEquipo(4, 200) < 0.05);
prueba("con k bajo el equipo pesa de verdad",
       pesoEquipo(4, 7.1) > 0.3 && pesoEquipo(4, 7.1) < 0.4);
prueba("sin partidos no pesa nada", pesoEquipo(0, 7) === 0);
prueba("más partidos siempre pesan más", pesoEquipo(9, 7) > pesoEquipo(4, 7));

console.log("");
console.log("bloqueLineas() — la escalera en pantalla");
console.log("");

const PAR = {
  corners:  {media: 4.73, disp: 1.75, k: 72.7,  disp_total: 1.01},
  tarjetas: {media: 2.28, disp: 0.72, k: 38.5,  disp_total: 0.88},
};
const EQ = {
  "9":  {pj: 5, n: {corners: 5}, esperado: {corners: 5.2, tarjetas: 2.4}},
  "20": {pj: 4, n: {corners: 4}, esperado: {corners: 4.4, tarjetas: 2.1}},
};
const M = {homeId: "9", awayId: "20", home: "Boca", away: "River"};

cargarEst(EQ, PAR);
const html = bloqueLineas(M);

prueba("dibuja algo", html.length > 100);
prueba("nombra a los dos equipos", html.includes("Boca") && html.includes("River"));
prueba("tiene la fila del total del partido", /total/i.test(html));
prueba("muestra porcentajes", (html.match(/%/g) || []).length >= 8);

/* El test que justifica todo el trabajo: el total NO se calcula
   sumando dos equipos independientes. Tiene que usar disp_total (1.01),
   no disp (1.75). Con la línea de 9.5 los dos dan distinto. */
const muT = 5.2 + 4.4;
const conTotal = Math.round(probMayor(muT, PAR.corners.disp_total, 9.5) * 100);
const conSuelta = Math.round(probMayor(muT, PAR.corners.disp, 9.5) * 100);
prueba("los dos caminos dan distinto (si no, el test no prueba nada)",
       conTotal !== conSuelta);
prueba("el total usa la dispersión medida del total, no la del equipo",
       html.includes(conTotal + "%") && !html.includes(conSuelta + "%"));

/* Sin datos de uno de los dos no se dibuja media escalera. */
cargarEst({"9": EQ["9"]}, PAR);
prueba("con un solo equipo no se dibuja nada", bloqueLineas(M) === "");
cargarEst(EQ, {});
prueba("sin parámetros medidos no se inventa nada", bloqueLineas(M) === "");
cargarEst(EQ, PAR);


console.log("");
console.log("lineaJugador() — el pedido original: 4 en un partido no es 1 en cada uno");
console.log("");

const PJUG = {
  F: {remates: {media: 1.41, disp: 1.37, k: 3.6},
      goles:   {media: 0.14, disp: 0.94, k: 10.1}},
  D: {remates: {media: 0.48, disp: 1.23, k: 20.9}},
};
cargarJug(PJUG);

const regular  = {pos: "F", serie: {remates: [1, 1, 1, 1, 1], pj: 5, esp: {remates: 1.2}}};
const explosivo = {pos: "F", serie: {remates: [4, 0, 0, 0, 1], pj: 5, esp: {remates: 1.2}}};

const r = lineaJugador(regular, "remates");
const x = lineaJugador(explosivo, "remates");

prueba("da una línea y una chance", r && r.linea > 0 && r.prob >= 0 && r.prob <= 1);
prueba("los dos parten del mismo esperado",
       regular.serie.esp.remates === explosivo.serie.esp.remates);
prueba("y por eso la línea es la misma", r.linea === x.linea);

/* Con el mismo esperado, la chance sale de la campana del PUESTO — que
   es lo que hay. La serie no se usa para la campana porque con 5
   partidos un desvío propio es ruido; se muestra para que se lea. */
prueba("la campana es la del puesto, no la del jugador", r.prob === x.prob);

prueba("sin serie no hay línea", lineaJugador({pos: "F"}, "remates") === null);
prueba("sin parámetros del puesto tampoco",
       lineaJugador({pos: "Z", serie: {remates: [1], pj: 1, esp: {remates: 1}}},
                    "remates") === null);
prueba("una métrica sin mercado no da línea",
       lineaJugador(regular, "atajadas") === null);
prueba("un delantero rematador supera más seguido una línea baja que un defensor",
       lineaJugador({pos: "F", serie: {remates: [3, 3], pj: 2, esp: {remates: 2.5}}},
                    "remates").prob
       > lineaJugador({pos: "D", serie: {remates: [0, 0], pj: 2, esp: {remates: 0.4}}},
                      "remates").prob);

console.log("");
console.log("la serie se muestra tal cual, que es lo que se pidió ver");
console.log("");

const fila = filaJugador(explosivo, "remates");
prueba("dibuja la serie partido por partido", /4.+0.+0.+0.+1/.test(fila));
prueba("y la chance de pasar la línea", fila.includes("%"));
prueba("un jugador sin serie no rompe la fila",
       typeof filaJugador({pos: "M"}, "remates") === "string");
console.log("");
console.log(ok + " ok, " + fallan + " fallando");
console.log("");
process.exit(fallan ? 1 : 0);
