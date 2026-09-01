# Brief para Claude Design — afinar las tres capas ya implementadas

Escrito el 2026-09-01, después de aplicar entero el handoff
`design_handoff_valor_tres_capas` sobre `index.html`.

**Lo estructural está hecho y verificado. Lo que falta es el ajuste
fino visual, y eso es lo que se pide acá.** Este documento existe para
que ese ajuste no rompa lo que está medido: la app tiene mediciones
detrás de casi cada decisión de color y de jerarquía, y varias no se
ven en la pantalla.

---

## Dónde está el trabajo

- Rama: **`rediseno-tres-capas`**. No está mergeada a `main`: la app
  publicada sigue siendo la vieja hasta que alguien lo decida.
- Todo vive en **`index.html`** — un archivo, CSS y JS embebidos, sin
  build. No hay framework y no se agrega ninguno.
- El handoff original está en `docs/design-handoff/tres-capas/`, con una
  nota arriba de qué se resolvió distinto y por qué.
- El razonamiento completo del rediseño: **`TRASPASO.md` §18**.

## Antes de tocar nada, correr esto

```bash
node verificar_app.js && node test_ejes.js && node test_registro.js && node test_alineacion.js && node test_probabilidad.js
```

`verificar_app.js` avisa de clases aplicadas sin regla de CSS, CSS que
no puede aplicar nunca, funciones muertas, colores fuera de los tokens y
estilos inline. Las cuatro suites cuidan el motor y el contrato de
pantalla. **Todo tiene que seguir en verde al terminar.** El workflow
`tests.yml` las corre solo en cada push.

---

## Qué se puede mover libremente

- Espaciados, tamaños, pesos e interlineados dentro de la escala que ya
  usa la hoja.
- El ritmo vertical de cualquier capa: qué respira más, qué se junta.
- La jerarquía tipográfica adentro de un bloque.
- Las 20 declaraciones `style="..."` fijas que quedaron en el JS:
  convertirlas en clases es bienvenido (es lo que pedía el handoff).
- Los estados vacíos, los pies de talón y los separadores.
- Los acordeones: cuál abre por defecto, cómo se ve el cerrado.

## Qué NO se puede tocar

**1. El motor.** Todo lo que está antes del comentario `HELPERS DE
PRESENTACIÓN` en el `<script>`: Dixon-Coles, Kelly, `probMayor()`,
`escalera()`, `otrosMercados()`, `devigShin()`. Está validado contra el
motor de Python (`doble_via.py`) y reescribirlo arriesga errores
numéricos que no se ven.

**2. Las dos regiones marcadas.**

- `==== INICIO RESOLUCION ====` … `==== FIN RESOLUCION ====`
- `==== INICIO EJES ====` … `==== FIN EJES ====`

`test_registro.js` y `test_ejes.js` las leen **por su nombre exacto**.
Si se mueven o se renombran, las suites dejan de encontrarlas y quedan
en verde sin probar nada. Es a propósito.

**3. La regla del dorado.** `--mostaza` (`#D6963A`) significa una sola
cosa: *acá el precio está a favor*. Vive **solo** en la capa Veredicto —
la tarjeta de oportunidad, el talón de la portada, la franja del día.
Ningún dato crudo lo usa nunca, y nunca se usa para marcar selección de
interfaz. Lo mismo con `--terracota` (`#C27152`), que dice *alerta* y
nada más. Si un bloque necesita destacarse y no es ninguna de esas dos
cosas, el recurso es tinta plena o el filete de salvia.

**4. Lo que la pantalla declara.** Estos textos no son relleno: cada uno
sale de una medición y sacarlos convierte a la app en algo que promete
lo que no puede cumplir.

- Los estados de mercado: `SIN VENTAJA` · `SIN PRECIO` · `SIN DATO` ·
  `NO OPINAMOS`, cada uno con su motivo.
- El veredicto vacío ("No hay nada acá"). Es el estado **más
  frecuente**, no un caso de borde: el ROI medido es −3.27% ±6.19 y el
  intervalo cruza el cero.
- Los marcadores de señal (`SEÑAL ALTA/MEDIA/BAJA/SIN MEDIR`) al lado de
  cada métrica. Son un atributo del número, no un disclaimer al pie: si
  se van abajo o se achican hasta no leerse, el número queda
  aparentando una precisión que no tiene.
- El intervalo del ROI en Registro. Las tres marcas —banda, punto y
  cero— salen de la misma escala calculada del dato. **Una barra que
  contradice sus propios números es el peor error posible en esa
  pantalla.**
- Los cuatro bloques de Límites en Método.

**5. Los nombres de campo del JSON.** `produce`, `concede`, `esperado`,
`serie.tit`, `fiabilidad_medida`. El diseño se adapta a ellos, no al
revés. (El handoff original hablaba de un campo `arranca` que en el JSON
no existe: la titularidad sale de `serie.tit` / `serie.pj`.)

---

## Lo que sí está flojo y conviene mirar

Dicho por Lucas: la implementación es fiel a la estructura del handoff
pero no al acabado. Lo que a mí me quedó sin resolver bien:

1. **El Veredicto de un partido sin análisis** son siete u ocho renglones
   que dicen casi lo mismo (`NO OPINAMOS`). Es honesto y es casi ruido.
   Agrupar los que comparten motivo, o darles menos peso, sin perder que
   cada mercado esté nombrado.
2. **El acordeón de métricas de Datos · Equipos** abre uno y deja nueve
   cerrados; la pantalla se ve más vacía de lo que es.
3. **La fila de mercado** apila nombre, motivo de dos líneas, estado y
   `+` en 375px: el estado a veces queda flotando lejos de su renglón.
4. **La lista de jugadores** mezcla dos números en la misma columna (el
   esperado de hoy cuando hay serie reciente, el promedio de temporada
   cuando la fuente no la publica). Está dicho en el pie, pero se lee
   como una sola cosa.
5. **El talón abierto de la portada** no se pudo ver con datos reales
   —hoy no hay ninguna oportunidad en la grilla— así que su ajuste fino
   está sin verificar contra contenido de verdad.
6. Los estilos inline fijos que quedaron (`verificar_app.js` los cuenta).

## Una sola regla de trabajo

**Mientras Claude Design tenga `index.html`, ninguna otra herramienta lo
toca.** Ese es el accidente que originó `CLAUDE.md`: tres herramientas
editando el mismo archivo en paralelo, trabajo perdido y funcionalidad
borrada. Si hace falta trabajo de backend o de datos en el medio, va en
otra rama y sobre otros archivos.
