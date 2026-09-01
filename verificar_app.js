/* ══════════════════════════════════════════════════════════════════
   verificar_app.js — la revisión interna de index.html

   Existe por un pedido concreto de Lucas: "yo mucha idea no tengo de qué
   hacer para corroborar que la app esté ordenada y perfecta
   internamente". Esto contesta esa pregunta con una corrida, no con una
   opinión.

   Lo que mira, y por qué cada cosa:

     1. CLASES USADAS Y NO DEFINIDAS — el error que no se ve. Un
        `class="talon-nuevo"` sin regla de CSS no rompe nada: dibuja el
        bloque sin estilo y parece que "quedó feo", no que falta algo.
     2. CLASES DEFINIDAS Y NO USADAS — CSS muerto. Cada regla que nadie
        aplica es una que alguien va a tratar de mantener el día que
        cambie la paleta.
     3. FUNCIONES DEFINIDAS Y NO LLAMADAS — código muerto. Peor que una
        función de más: el que viene no sabe cuál de las dos dibuja la
        pantalla. Ya pasó en este repo.
     4. COLORES CRUDOS FUERA DE :root — la hoja tiene tokens
        (--mostaza, --terracota...). Un `#D6963A` escrito a mano en una
        regla es un color que el día que cambie la paleta no cambia.
     5. ESTILOS INLINE EN EL MARKUP — el handoff de diseño lo pide
        explícito: "cada patrón repetido debe volverse una clase
        reutilizable, no estilos inline duplicados".
     6. LAS REGIONES MARCADAS — las bandas "INICIO RESOLUCION" e
        "INICIO EJES" que hay adentro del script las leen
        test_registro.js y test_ejes.js tal cual. Si alguien las mueve o
        les cambia el nombre, las suites dejan de encontrarlas y quedan
        en verde sin probar nada.

        (Acá van sin los delimitadores de comentario a propósito:
        escribir un cierre de comentario adentro de un comentario lo
        termina antes de tiempo, y el resto del encabezado se lee como
        código. Pasó al escribir este archivo.)

   Lo que NO mira, y hay que saberlo: no juzga si la app se ve bien, no
   corre el motor (para eso están las cuatro suites) y no detecta una
   clase que se arma concatenando strings en el JS. Por eso el punto 2
   dice "candidatas": son para revisar a mano, no para borrar de una.

   Uso:  node verificar_app.js
   Sale con código 1 si hay algo de lo DURO roto (clases sin definir,
   regiones perdidas). Lo demás es informe.
   ══════════════════════════════════════════════════════════════════ */
"use strict";
const fs = require("fs");
const path = require("path");

const ARCHIVO = path.join(__dirname, "index.html");
const html = fs.readFileSync(ARCHIVO, "utf8");

const css = html.slice(html.indexOf("<style>") + 7, html.indexOf("</style>"));
const js  = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));
const body = html.slice(html.indexOf("</style>"), html.indexOf("<script>"));

let duros = 0;
const titulo = t => console.log("\n" + t + "\n" + "─".repeat(t.length));
const linea = (ok, txt) => console.log(`  ${ok ? "ok  " : "→   "} ${txt}`);

/* ── 1 y 2. Las clases ──────────────────────────────────────────────
   Definidas: todo selector `.algo` del <style>.
   Usadas: cualquier palabra que aparezca adentro de un class="..." del
   markup o del JS, más las que el JS manipula por classList. Se toman
   TODAS las palabras del atributo aunque el atributo tenga `${...}`
   adentro: es preferible perderse una clase muerta que acusar de muerta
   a una que se arma por template. */
const definidas = new Set();
css.replace(/\.([a-zA-Z][\w-]*)/g, (_, c) => definidas.add(c));

const usadas = new Set();
/* Las expresiones interpoladas se sacan ANTES de buscar los atributos.
   Si se sacaran después no alcanza: `class="${a?"on":""}"` tiene comillas
   adentro, así que el atributo se corta al medio y quedan pedazos de
   expresión haciéndose pasar por nombres de clase. Se repite el borrado
   porque hay `${}` anidados. */
const sinExpresiones = texto => {
  let t = texto, antes;
  do { antes = t; t = t.replace(/\$\{[^{}]*\}/g, " "); } while(t !== antes);
  return t;
};
const recogerClases = crudo => {
  const texto = sinExpresiones(crudo);
  texto.replace(/class="([^"]*)"/g, (_, v) => {
    /* Lo que va adentro de un ${...} es una EXPRESIÓN, no un nombre de
       clase: `class="${cls}"` no aplica una clase llamada "cls". Se
       borra antes de leer — sin esto el informe acusa de "clase sin
       definir" a cada variable interpolada, que es lo que hizo la
       primera versión de este archivo. */
    v.replace(/[a-zA-Z][\w-]*/g, w => usadas.add(w));
    return "";
  });
  /* classList.add("x"), toggle("x", ...), y los strings sueltos que el
     JS interpola adentro de un class. */
  texto.replace(/classList\.\w+\(\s*"([^"]+)"/g, (_, v) => { usadas.add(v); return ""; });
};
recogerClases(body);
recogerClases(js);

/* Palabras que el JS tiene en strings sueltos y podrían terminar en un
   class por interpolación (`class="${cls}"`). Se suman como "usadas
   posibles" para no reportar falsos muertos. */
const posibles = new Set();
/* Cualquier string corto del JS, aunque arranque con espacio — `" mio"`
   sale de `${yo ? " mio" : ""}` y es una clase que sí se aplica. */
js.replace(/"([^"\n]{1,60})"/g, (_, v) => {
  v.trim().split(/\s+/).forEach(w => { if(/^[a-zA-Z][\w-]*$/.test(w)) posibles.add(w); });
  return "";
});

/* Pseudo-clases, estados y utilidades del navegador que no son clases
   nuestras aunque el regex las levante. */
const NO_SON_CLASES = new Set([
  "hover","focus","active","first-child","last-child","not","before","after",
  "webkit-scrollbar","5px","6px","62","7","24","3","06","08","1","2","4","5","8",
]);

const sinDefinir = [...usadas].filter(c => !definidas.has(c) && !NO_SON_CLASES.has(c));

/* Las que no se aplican en ningún `class="..."` literal se parten en dos
   montones, porque no valen lo mismo:

     · la palabra NO aparece en ninguna parte del JS  → muerta, casi
       seguro. Nadie puede armarla ni por template.
     · la palabra aparece suelta en el JS  → hay que mirar. Puede ser una
       clase que se arma por interpolación, o puede ser coincidencia con
       el nombre de una variable (`eq`, `linea`, `barra` son las dos
       cosas en este archivo).

   Partirlo evita el peor final posible de una herramienta así: una lista
   larga de "candidatas" que nadie revisa porque revisarlas cuesta más
   que ignorarlas. */
const apareceEnJS = c => new RegExp("\\b" + c.replace(/-/g, "\\-") + "\\b").test(js);
const noAplicadas = [...definidas].filter(c => !usadas.has(c) && !NO_SON_CLASES.has(c));
const sinUsar = noAplicadas.filter(c => !apareceEnJS(c));
const dudosas = noAplicadas.filter(c => apareceEnJS(c));

titulo("1. Clases usadas en el markup y sin regla de CSS  (duro)");
if(sinDefinir.length){
  duros += sinDefinir.length;
  sinDefinir.forEach(c => linea(false, `.${c} — se aplica y no existe`));
} else linea(true, "ninguna: todo lo que se aplica tiene estilo");

titulo("2. Clases con CSS que no aparecen en ninguna parte del JS  (muertas)");
if(sinUsar.length) console.log("  →    " + sinUsar.map(c => "." + c).join("  "));
else linea(true, "ninguna");

titulo("2bis. Clases que no se aplican literal pero la palabra existe en el JS  (mirar)");
if(dudosas.length) console.log("  →    " + dudosas.map(c => "." + c).join("  "));
else linea(true, "ninguna");

/* ── 3. Funciones y constantes muertas ────────────────────────────── */
titulo("3. Funciones y constantes definidas que nadie llama");
/* Las suites cuentan como uso: ver el comentario de abajo. */
const suites = fs.readdirSync(__dirname).filter(f => /^test_.*\.js$/.test(f))
  .map(f => fs.readFileSync(path.join(__dirname, f), "utf8")).join("\n");
const defs = [...js.matchAll(/^(?:function|const|let)\s+([A-Za-z_$][\w$]*)/gm)].map(m => m[1]);
const muertas = defs.filter(n => {
  const patron = "\\b" + n.replace(/\$/g, "\\$") + "\\b";
  const usos = (js.match(new RegExp(patron, "g")) || []).length;
  /* Una función puede no llamarse desde index.html y aun así sostener
     una suite: `CONTRATO` es el contrato de ejes que lee test_ejes.js.
     Borrarla dejaría el test en verde probando otra cosa. */
  return usos <= 1 && !new RegExp(patron).test(suites);
});
if(muertas.length) muertas.forEach(n => linea(false, `${n}() — definida y nunca usada`));
else linea(true, "ninguna: no quedó código muerto");

/* ── 4. Colores crudos fuera de los tokens ────────────────────────── */
titulo("4. Colores escritos a mano fuera de :root");
const root = css.slice(css.indexOf(":root{"), css.indexOf("}", css.indexOf(":root{")));
const fuera = css.replace(root, "");
const hex = {};
/* El negro de una máscara CSS y el de un SVG no son colores de la
   paleta: en `mask-image` el color no se ve —lo que importa es el canal
   alfa— y adentro del troquel es tinta de un dibujo, no de la interfaz.
   Tokenizarlos sería peor: haría creer que cambiando el token cambia
   algo. */
const sinMascaras = fuera.replace(/mask-image:[^;}]*/g, "");
sinMascaras.replace(/#[0-9a-fA-F]{3,8}\b/g, h => { hex[h.toUpperCase()] = (hex[h.toUpperCase()] || 0) + 1; return h; });
const repetidos = Object.entries(hex).filter(([, n]) => n > 1).sort((a, b) => b[1] - a[1]);
if(repetidos.length) repetidos.forEach(([h, n]) => linea(false, `${h} escrito ${n} veces — debería ser un token`));
else linea(true, "ninguno repetido");

/* ── 5. Estilos inline en el markup ───────────────────────────────── */
titulo("5. Estilos inline");
const inline = (js.match(/style="/g) || []).length;
/* Los que llevan `${` adentro son valores calculados (un ancho de
   barra, un delay de animación): esos NO pueden ser una clase. Los
   fijos sí. */
const calculados = (js.match(/style="[^"]*\$\{/g) || []).length;
const fijos = inline - calculados;
linea(fijos === 0, `${inline} en total: ${calculados} con valor calculado (correcto), ${fijos} fijos`);
if(fijos > 0) console.log("        los fijos son los que el handoff pide convertir en clase");

/* ── 6. Las regiones que leen las suites ──────────────────────────── */
titulo("6. Regiones marcadas que leen los tests  (duro)");
[["INICIO RESOLUCION", "FIN RESOLUCION", "test_registro.js"],
 ["INICIO EJES", "FIN EJES", "test_ejes.js"]].forEach(([a, b, quien]) => {
  const ok = js.includes(a) && js.includes(b);
  if(!ok) duros++;
  linea(ok, `${a} … ${b} — la lee ${quien}`);
});

/* ── 7. Tamaño ────────────────────────────────────────────────────── */
titulo("7. Tamaño del archivo");
const kb = n => (n / 1024).toFixed(0) + " KB";
linea(true, `${kb(html.length)} en total · CSS ${kb(css.length)} · JS ${kb(js.length)}`);
linea(true, `${html.split("\n").length} líneas`);

console.log("");
if(duros){
  console.log(`${duros} problema${duros === 1 ? "" : "s"} DURO${duros === 1 ? "" : "S"} — hay que arreglarlos antes de mergear.`);
  process.exit(1);
}
console.log("Sin problemas duros. Lo de arriba que no diga 'ok' es para revisar, no para asustarse.");
