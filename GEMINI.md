# VALOR / Pronóstic — por dónde entrar

**Leé esto entero antes de abrir cualquier otro archivo.** Existe porque
Antigravity y las herramientas de Google buscan `GEMINI.md` por nombre, y
porque `CLAUDE.md` describe sobre todo un producto que **ya no es donde
se trabaja**: de sus 300 líneas, unas 260 son de la app anterior.

---

## Lo único que se toca hoy

**`experto/` — Pronóstic**, un asesor de fútbol y apuestas
conversacional. Rama **`pronostic`**, no `main`.

Si venís a construir, leé en este orden y nada más:

1. `docs/superpowers/specs/2026-09-05-pronostic-diseno.md` — la carta.
   La §4 tiene **los 22 campos** contra los que se audita el producto.
2. `experto/PENDIENTE.md` — qué falta y en qué orden.
3. La sección `experto/` de `CLAUDE.md` — la tabla de los archivos y las
   tres reglas de la carpeta.
4. `experto/ARRANCAR.md` — cómo se corre.

Antes de tocar nada: **`git pull`**, y después
`python experto/probar.py`, que verifica la instalación sin gastar API.

## Lo que sigue vivo y NO se toca

Estos producen los datos que Pronóstic lee. Andan solos y cambiarlos
rompe todo lo de arriba:

| | |
|---|---|
| `actualizar.py` | El motor. Baja ESPN y calcula λ. Corre en GitHub Actions 2×/día |
| `mercado_extra.py`, `foto_props.py` | La cuota de Bet365 y las fotos de línea |
| `data/*.json` | Lo escribe el cron. **Nunca a mano** |
| `backtest.py`, `medir_clv.py` | El motor matemático. `experto/datos.py` los importa a propósito, no los reescribe |

## Lo que quedó de lado — no trabajes ahí

Sigue en el repo porque tiene historia y mediciones que valen, pero
**Lucas lo dejó de lado y no hay que tocarlo ni proponer cambios sobre
ello**:

- **`index.html`** — la PWA anterior. Es el producto que Pronóstic
  reemplaza. Si un archivo te lleva ahí, volvé.
- **Las dos skills de análisis** (`.claude/skills/valor-analisis-*`) y
  `data/analisis*.json` — carga manual, y el flujo que las usaba es el
  que dejó de andar.
- **`test_alineacion.js`, `test_ejes.js`, `test_registro.js`,
  `verificar_app.js`** — verifican `index.html`. No los corras para
  validar trabajo en `experto/`; para eso están `experto/probar.py` y
  `test_cierre.py`.
- Los **30 scripts `medir_*.py` y `barrido_*.py`** — son el historial de
  mediciones. Se **leen** para no repetir un camino cerrado; no se
  ejecutan ni se modifican como parte de este trabajo.

**Por qué importa:** el proyecto perdió trabajo tres veces por
herramientas tocando lo mismo sin saber una de la otra. La regla vive en
`CLAUDE.md` y sigue vigente: **una herramienta por área.** Mientras
alguien esté en `experto/`, que no entre otra.

---

## Si venís a USAR Pronóstic en vez de construirlo

Antigravity puede hacer de asesor sin ninguna clave de API: leés
`experto/voz.md`, corrés `python experto/datos.py <id_partido>` y
contestás con esa voz. Está en **`experto/SIN_CLAVE.md`**.

**No mezcles las dos cosas en la misma sesión.** Una sesión edita código,
otra hace de asesor; un agente haciendo las dos se confunde de rol.

---

## Dónde está el detalle

`CLAUDE.md` tiene la tabla completa de archivos —incluida la sección de
`experto/`— y las restricciones duras. `TRASPASO.md` tiene el historial:
qué salió mal, qué se midió y qué está cerrado. **Es más nuevo que
`CLAUDE.md`: si se contradicen, gana `TRASPASO.md`.** La §43 es la de
Pronóstic.

Si editás reglas del proyecto, editá **`CLAUDE.md`** y sincronizá
`AGENTS.md` y este archivo en el mismo commit — ya divergieron una vez.
