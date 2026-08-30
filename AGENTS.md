# VALOR — reglas del repo

**Archivo canónico: `CLAUDE.md`.** Este archivo existe porque algunas
herramientas (OpenCode, Hermes, y otras que sigan la convención
`AGENTS.md`) lo buscan por nombre en vez de `CLAUDE.md`. Antes duplicaba
todo el contenido de `CLAUDE.md` — la tabla de archivos, las rutas de
skill, nombres de herramientas — y esa copia se desactualizó sola: una
herramienta editaba acá, otra editaba `CLAUDE.md`, y nadie sincronizaba
las dos. Es el mismo problema que originó el repo (tres IAs, mismo
archivo, sin saber una de la otra) pero entre documentos en vez de
código. La solución: **un solo lugar con el detalle, este archivo solo
apunta y guarda lo que no cambia seguido.**

**Leé `CLAUDE.md` entero antes de tocar nada** — ahí está la tabla de
qué es cada archivo, quién lo toca, la ruta real de la skill de
análisis, y el resto del detalle operativo. Después, para el historial
completo de qué salió mal, qué está resuelto y en qué orden seguir, leé
las secciones relevantes de `TRASPASO.md` (más nuevo que `CLAUDE.md`:
si contradice, gana `TRASPASO.md`).

## Restricciones duras — no negociables, quedan acá porque no cambian seguido

- **`actualizar.py`: solo biblioteca estándar.** Corre en GitHub Actions
  sin `pip install`. Nada de dependencias.
- **Una clave de API se lee del entorno, nunca del repo.** `os.environ`,
  secret de GitHub Actions. Sin la clave, todo sigue andando igual que
  antes — la fuente nueva agrega mercados, no reemplaza los que ya
  funcionan.
- **No cambiar el contrato de `data/partidos.json`.** Agregar campos sí;
  renombrar o cambiar tipos rompe el frontend.
- **Tocar una constante del modelo solo entra si una medición walk-forward
  fuera de muestra lo sostiene.** No por tunear hacia atrás ni para que
  un número dé mejor.
- **Un barrido que mejora en el borde de la grilla no encontró nada.**
  Extendé la grilla antes de festejar.
- **Un parámetro de liga se calcula DENTRO de la liga**, nunca sobre un
  pozo con varias competiciones mezcladas.
- **Cruzar nombres de equipo solo por igualdad exacta, nunca por
  parecido.** Un cruce difuso funde historias de equipos distintos y no
  se ve como error — se ve como datos.
- **Comparar el error contra el ruido, no contra cero.** Con muestra
  chica, un modelo perfecto ya desvía por puro azar.
- **Una sola forma de sacarle el margen a una cuota: Shin.** No
  normalización a mano.
- **Antes de calibrar algo, medir si ya sirve.** Calibración no es lo
  mismo que rentabilidad.
- **Medir antes de afirmar.** Este repo tiene historial de afirmaciones
  sobre los datos que resultaron falsas al chequearlas contra la API
  real.

Detalle, ejemplos y números de cada una de estas: `CLAUDE.md` y
`TRASPASO.md`.

## Para evitar el problema que originó este archivo

**Una herramienta por área.** Si vas a usar otra IA en paralelo, que sea
para algo distinto (backend vs. interfaz vs. contenido) o en una rama
aparte. Nunca dos herramientas editando el mismo archivo a la vez —
código o documentación por igual, este archivo es el ejemplo de lo que
pasa cuando no se respeta.

**Si vas a editar reglas o contexto del proyecto, editá `CLAUDE.md`,
no este archivo.** Si tu herramienta solo lee `AGENTS.md` por
convención y necesitás que el cambio se vea, actualizá los dos en el
mismo commit — no dejes que diverjan de nuevo.
