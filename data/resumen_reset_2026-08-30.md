# Resumen del reset 2026-08-30

Qué se revirtió, qué se conservó, y por qué. Escribirlo acá para que no se
pierda el análisis de la sesión de diagnóstico del 30/08, que quedó
descartado por no estar respaldado por medición.

## Decisión de fondo

Se revirtió el trabajo experimental de la sesión del 30/08 (herramienta
que dejó `actualizar.py`, `index.html` y `test_alineacion.js` modificados,
con `doble_via.py` roto y tests en rojo). Motivo: la medición real y la
propia conclusión de esa herramienta decían que los cambios no aportaban,
y violaban la regla del repo de "no tocar λ salvo fuente nueva".

## Revivido a HEAD (descartado, por medición / por romper verificación)

### actualizar.py — shrinkage de λ (K=6, floor 0.75) + H2H + forma reciente
- Medido el 30/08 con walk-forward estricto sobre el historial largo
  (mismo arnés que `medir_historico.py`), comparando contra resultados:
  - ARG: efecto del engine ~nulo (media sh≈0.98, solo 203/2583 partidos
    con sh<0.95). El Brier "mejora" ~0.0003 — ruido, y el patrón que
    mejora es el borde de la grilla (sh0.80), señal de converger al promedio
    de liga (pierde discriminación, ver `medir_discriminacion.py`).
  - BRA: el shrinkage **empeora** el Brier de forma creciente.
  - Mismas dos ligas con signos opuestos = firma de ruido (igual que
    `medir_encogimiento.py` ya documentó a nivel de probabilidades).
- Las ramas "forma reciente" (sh<0.65) y "H2H" (sh<0.75) eran **código
  muerto**: nunca disparan porque el floor deja sh≥0.75.
- `k_shrink: 10` agregado a arg.1/bra.1 no se usaba (K=6 hardcodeado).
- Conclusión: no tocar λ. El `barrido_lambda.py` del 29/08 ya había cerrado
  producción en el óptimo.

### index.html — τ() reescrito (Dixon-Coles "corregido")
- El τ commiteado ya era Dixon-Coles estándar, idéntico a la referencia
  Python (`backtest.py`). La reescritura **no arregló nada** (la propia
  nota de la herramienta admite "no cambia quién es el favorito") y
  **rompió `doble_via.py`** (diferencia pasó de 6.7e-16 a 3.1e-02).
- Además `coherenteGoles()` y los espejos de `senalDividida` ("muchos
  goles", "btts_si") con umbrales elegidos a ojo (2.2/1.8/2.8/1.6) sin
  medición, y 6 tests nuevos que fallaban.

### test_alineacion.js — 6 tests de los espejos (los acompaña la reversión)

## Conservado (legítimo / no es experimento)

- `AGENTS.md`, `CLAUDE.md`, `TRASPASO.md`: documentación del
  `barrido_lambda` del 29/08 (correcta, previa a la sesión).
- `data/analisis.json`: solo **agrega una entrada** (`espn401841525`,
  Unión con su `desarrollo`). No cambió ninguna `inclinacion`.
- `data/backtest.json`: salida de script, válida.

## Cosas útiles que NO se pierden (deuda real, sin tocar el motor)

1. **Sesgo de localía / sobreconfianza en favoritos 1X2 real** — el modelo
   dice local 44-47% y el local gana ~33-36% (visible en
   `data/backtest.json`). Es un problema de presentación/calibración de
   favoritos, no un bug de λ. `medir_encogimiento.py` ya mostró que
   encoger hacia la tasa base NO rinde OOS en arg. Pendiente: umbral de
   favorito (≥55%) en la UI — tarea de presentación, NO de motor.
2. **Bug H2H comparaba IDs con nombres** — real, pero el fix vive en
   código muerto (solo corría si sh<0.75, que no pasa). No se pierde nada
   real al revertirlo.
3. **Francia sin calibrar** — 4 partidos malos (journée 2) porque es liga
   nueva agregada el 25/08 y `barrido_lambda` no la evaluó OOS. Tarea
   aparte: correr `barrido_lambda.py fra` cuando haya más data.

## Cómo verificar

- `python doble_via.py` → debe volver a ~6.7e-16 (sin divergencia).
- `node test_alineacion.js` → 90/sin los 6 espejos (verde).
