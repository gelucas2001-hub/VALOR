# VALOR — reglas del repo

**Archivo canónico: `CLAUDE.md`.** Este archivo existe porque
Antigravity y otras herramientas de Google buscan `GEMINI.md` por
nombre. **No duplica contenido a propósito**: en este repo ya pasó que
dos documentos con las mismas reglas divergieran porque cada herramienta
editaba el suyo, y es el mismo problema que originó todo (tres IAs, el
mismo archivo, sin saber una de la otra). Un solo lugar con el detalle;
este apunta.

**Leé `CLAUDE.md` entero antes de tocar nada.** Ahí está la tabla de qué
es cada archivo y quién lo toca. Después, `TRASPASO.md` — es más nuevo:
si contradice a `CLAUDE.md`, gana `TRASPASO.md`.

Las restricciones duras están listadas en `AGENTS.md`, que es el mismo
puntero para las herramientas que siguen esa convención. Si editás
reglas del proyecto, editá **`CLAUDE.md`** y sincronizá los tres en el
mismo commit.

---

## Si venís a trabajar en Pronóstic

Es el trabajo en curso, y vive en la rama **`pronostic`**, no en `main`.

Leé en este orden:

1. **`docs/superpowers/specs/2026-09-05-pronostic-diseno.md`** — qué es,
   por qué, y los **22 campos** contra los que se audita.
2. **`experto/PENDIENTE.md`** — qué falta, en qué orden, y qué no tocar.
3. **`experto/ARRANCAR.md`** — cómo se corre.

## Si venís a USAR Pronóstic desde acá

Antigravity puede hacer de asesor sin ninguna clave de API: leés
`experto/voz.md`, corrés `python experto/datos.py <id_partido>` y
contestás con esa voz. Está explicado en **`experto/SIN_CLAVE.md`**.

**Una herramienta por área.** Mientras alguien esté en `experto/`, que no
entre otra.
