#!/usr/bin/env python3
"""Chequeo de doble vía: el motor en Python y el motor en JavaScript
tienen que dar el MISMO número sobre los mismos datos.

Corré:  python doble_via.py

Por qué existe (TRASPASO, fase 2, paso 10): un signo cambiado en
Dixon-Coles no tira una excepción. Da probabilidades sutilmente mal,
para siempre, y en silencio. La única forma de cazarlo es calcular lo
mismo por dos caminos independientes y comparar.

Python es la vía de referencia (`backtest.py`, que fue lo que se usó
para calibrar). JavaScript es la vía que corre en el frontend
(`app.html`). Si divergen, manda Python y hay que arreglar el JS.

Solo biblioteca estándar, como el resto del repo.
"""

import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))

from backtest import matriz, suma_si  # el motor de referencia

SNAPSHOT = RAIZ / "tests" / "partidos-snapshot.json"

# Los mismos mercados que calcula el frontend, con el criterio de cobro
# escrito acá de cero — a propósito. Si copiara el TESTS del JS, las dos
# vías compartirían el error y el chequeo no serviría de nada.
CRITERIOS = {
    "1x2_l":  lambda i, j: i > j,
    "1x2_e":  lambda i, j: i == j,
    "1x2_v":  lambda i, j: i < j,
    "dc_lx":  lambda i, j: i >= j,
    "dc_x2":  lambda i, j: i <= j,
    "dc_12":  lambda i, j: i != j,
    "btts_si": lambda i, j: i > 0 and j > 0,
    "btts_no": lambda i, j: i == 0 or j == 0,
}
for n in (1.5, 2.5, 3.5):
    CRITERIOS[f"ov{n}"] = (lambda nn: lambda i, j: i + j > nn)(n)
    CRITERIOS[f"un{n}"] = (lambda nn: lambda i, j: i + j < nn)(n)


JS = r"""
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const script = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));
const corte = script.indexOf("RENDER Y RUTEO");
const src = script.slice(0, script.lastIndexOf("/*", corte));

const almacen = {};
const localStorage = {
  getItem: k => (k in almacen ? almacen[k] : null),
  setItem: (k, v) => { almacen[k] = String(v); },
};
let api = {};
new Function("localStorage", "exportar", src +
  "\nexportar({matrix, sumIf, TESTS, mercados, lectura});")(
  localStorage, o => { api = o; });

const partidos = JSON.parse(fs.readFileSync(process.argv[3], "utf8")).partidos
  .filter(m => m.lh != null && m.la != null);

const salida = partidos.map(m => {
  const M = api.matrix(m.lh, m.la, m.rho);
  const probs = {};
  Object.keys(api.TESTS).forEach(id => { probs[id] = api.sumIf(M, api.TESTS[id]); });
  return { id: m.id, lh: m.lh, la: m.la, rho: m.rho, probs };
});
process.stdout.write(JSON.stringify(salida));
"""


def main():
    partidos = [m for m in json.loads(SNAPSHOT.read_text(encoding="utf-8"))["partidos"]
                if m.get("lh") is not None and m.get("la") is not None]

    tmp = RAIZ / "_doble_via.js"
    tmp.write_text(JS, encoding="utf-8")
    try:
        crudo = subprocess.run(
            ["node", str(tmp), str(RAIZ / "app.html"), str(SNAPSHOT)],
            capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout
    except subprocess.CalledProcessError as e:
        print("El lado JavaScript falló:\n" + (e.stderr or ""))
        return 1
    finally:
        tmp.unlink(missing_ok=True)

    delJs = {x["id"]: x for x in json.loads(crudo)}

    print(f"\nChequeo de doble vía — Python (backtest.py) vs JavaScript (app.html)")
    print(f"Snapshot congelado: {SNAPSHOT.name} — {len(partidos)} partidos")
    print(f"Mercados por partido: {len(CRITERIOS)}  →  "
          f"{len(partidos) * len(CRITERIOS)} probabilidades comparadas\n")

    peor, peor_donde = 0.0, ""
    faltan, comparadas = 0, 0

    for m in partidos:
        js = delJs.get(m["id"])
        if not js:
            faltan += 1
            continue
        # Las lambdas tienen que coincidir, o no estaríamos comparando lo mismo.
        for campo in ("lh", "la", "rho"):
            if abs(js[campo] - m[campo]) > 1e-12:
                print(f"  {m['id']}: {campo} distinto entre vías — {js[campo]} vs {m[campo]}")
                return 1

        M = matriz(m["lh"], m["la"], m["rho"])
        for id_, cond in CRITERIOS.items():
            p_py = suma_si(M, cond)
            p_js = js["probs"].get(id_)
            if p_js is None:
                print(f"  el JS no calcula el mercado {id_}")
                return 1
            d = abs(p_py - p_js)
            comparadas += 1
            if d > peor:
                peor, peor_donde = d, f"{m['home']} vs {m['away']} — {id_}"

    print(f"  diferencia máxima: {peor:.3e}")
    print(f"  donde: {peor_donde}")
    if faltan:
        print(f"  partidos que el JS no devolvió: {faltan}")

    # El umbral es la precisión de un float de 64 bits acumulada sobre una
    # matriz de 10x10 sumas, no un número elegido a dedo.
    TOLERANCIA = 1e-12
    if peor <= TOLERANCIA and not faltan:
        print(f"\n  Las dos vías coinciden dentro de {TOLERANCIA:.0e}.")
        print(f"  El port a JavaScript no introdujo error numérico.\n")
        return 0

    print(f"\n  DIVERGEN por encima de {TOLERANCIA:.0e}. Manda Python: revisá el JS.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
