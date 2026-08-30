# PROBLEMAS.md — Resumen ejecutivo de lo que falla en la app

Fecha del documento: 2026-08-30. Este archivo consolida los problemas REALES y
medidos de la app VALOR, con números. No es una lista de quejas subjetivas: cada
punto apunta a un dato que podés volver a medir con los scripts del repo.

**Advertencia de método (léela antes de citar este archivo):** los ejemplos del
29/08/2026 son UNA fecha con una cantidad anormal de empates (9 de 15, ~60%). Un
solo día NO prueba un bug del modelo ni que la app está rota — la varianza hace
eso. Sirven para **ilustrar** los patrones que ya están medidos con muestras
grandes (calibración, ROI, calibración por liga). Para orientar la discusión,
no como evidencia definitiva.

---

## 1. La app pierde plata (el problema de fondo)

Esto es lo único que importa y lo que siempre debería ir primero. Todo lo demás
son detalles de presentación comparados con esto.

- ROI histórico en Argentina: **−6.18%** (977 apuestas, EV≥4%, cuota≤4.5) — antes
  de que `historia_reciente()` + el fix de `VIDA_MEDIA_DIAS` 45→300 estuvieran.
  Después del fix: **−0.94%**, z=−0.2, estadísticamente indistinguible de cero.
  Ver `TRASPASO.md`, sección de rentabilidad.
- Walk-forward contra la cuota de cierre real de Pinnacle: **−3.27% ±6.19**. El
  intervalo incluye cero; no hay evidencia de ventaja real sobre el mercado.
- Mercado de estadísticas (córners, remates, faltas): solo los córners calibran
  bien. Las faltas tienen ~9 puntos de sesgo y los remates ~7. Ver
  `medir_lineas.py`, `medir_corners.py`.
- Regla dura del repo: **un ajuste del modelo solo entra si una medición
  walk-forward fuera de muestra lo sostiene**. Hasta la fecha ningún cambio ha
  demostrado mejorar el ROI de forma robusta OOS.

## 2. La escalera de pronósticos es un espejo de presentación que no gana dinero

Problema ya documentado en `TRASPASO.md` (Regla 5) y hoy re-confirmado contra
resultados reales.

**Qué es el patrón:** la escalera ordena por probabilidad de mercado, así que
siempre caen arriba los mercados triviales de alta probabilidad y cuota bajísima
(`ov1.5` 80%+, `un3.5` 76-83%, `un2.5`, `un1.5`, `btts`). Le pagan a la casa
~1.05-1.15 por una apuesta que "casi siempre gana": acertar mucho a cuota baja
NO es ganar plata, es regalar margen.

**Primera evidencia en vivo (29/08/2026, 15 partidos):**
- La escalera acertó **29/44 mercados (65.9%)** contra los resultados reales.
- Pero los aciertos están concentrados en los mercados triviales de arriba
  (`ov1.5`, `un3.5`, `un2.5`, `un1.5`), que pagan ~1.10. Cuando baja a los
  mercados de cuota decente falla: `1x2_v` Strasbourg, `1x2_l` Brest, los
  `un1.5` casi todos, varios `btts`. Auxerre fue **0/3**.
- En **ninguno de los 15 partidos** la escalera marca `ventaja=` ni
  `MARCA DE VALOR` — la app misma no encuentra valor, pero igual te muestra una
  columna de "recomendados".

**Evidencia de fondo ya medida:** ROI walk-forward negativo (−3.27%±6.19). La
escalera es la puerta de entrada de esa pérdida.

## 3. La escalera repite under de goles, y no es recomendación, es mecánico

En la misma fecha, 7 de 15 partidos mostraron al menos doble under y 4 mostraron
**triple under** (`un3.5 un2.5 un1.5`: Bournemouth, Coventry, Lyon, Rosario
Central). "Recomendar" tres mercados de menos goles en fila no es una opinión
del modelo: es que los under 1.5/2.5/3.5 son los mercados de mayor probabilidad
disponibles, así que la regla de ordenamiento siempre los pone arriba. Es un
efecto mecánico de `escalera()`, no una lectura del partido.

## 4. La escalera NO está ligada a la lectura (el "acierto mentiroso")

La escala usa una lógica distinta a la lectura 1X2, y se ve:

- **Lyon**: `lectura()` dio local 59.8% — el pronóstico más fuerte de la fecha, y
  sin embargo la escalera puso `un3.5 un2.5 un1.5`: tres under, sin NINGUNA
  apuesta a que gana el local, que era su pick más confiado.
- **Brest**: lean local 39.9%, la escalera sí cuela `1x2_l` al final.
- **Strasbourg**: lean visitante 41.7%, la escalera lo refleja con `1x2_v`.

O sea: a veces coincide (Strasbourg), a veces se contradice (Lyon). La columna
"recomendados" da la impresión de que el modelo respalda esa apuesta cuando en
realidad es solo un ordenamiento por probabilidad de mercado.

## 5. Favoritismo hacia el local (sí, pero hasta donde la muestra grande lo sostiene)

- "La app favorece al local": medido a lo grande (`backtest.json`, 2026-08-29),
  el modelo NO sobreestima al local en agregado. ARG predice 41.7% local y salió
  43.7%; BRA 47.0% vs 46.3%; Ligue 1 39.9% vs 42.2%; Premier 41.9% vs 40.6%. El
  "desequilibrio local" que reportó Hermes venía de ~22 partidos (trampa de
  muestra pequeña).
- Lo que SÍ está documentado como real es el problema de **presentación**:
  "1X2 de favoritos sobreconfiados" (`TRASPASO.md:427`). La app muestra al
  favorito con una confianza que luego no sostiene.
- En vivo (29/08): la app marcó **local (L) en 11 de 15** partidos, y de esos 11
  solo ganó 1. El `lean` acertó **2/15 (13%)**. Fecha anómala (9 empates), pero
  ilustra la sobrepresentación del favorito local.

## 6. Diagnóstico de la fecha 29/08/2026 (evidencia ilustrativa de TODO el anterior)

Predicción de la app (`lectura()`) vs. resultado real confirmado en múltiples
fuentes (ESPN, Guardian, Reuters-agencia, TyC, TN, ge/O Globo, 365scores):

| Partido | Resultado | App 1X2 (L/E/V) | Lean | Escalera (aciertos) |
|---|---|---|---|---|
| Liverpool–Nottm Forest | 2-2 | 55.5/22.7/21.8 | L | ov1.5✓ btts✓ ov3.5✓ (3/3) |
| Bournemouth–Everton | 1-1 | 45.6/27.0/27.5 | L | un3.5✓ un2.5✓ un1.5✗ (2/3) |
| Coventry–Hull | 0-1 | 42.2/27.6/30.2 | L | un3.5✓ un2.5✓ un1.5✓ (3/3) |
| Strasbourg–Lens | 2-1 | 33.1/25.2/41.7 | V | ov1.5✓ btts✓ 1x2_v✗ (2/3) |
| Tottenham–Newcastle | 0-2 | 35.4/24.0/40.6 | V | ov1.5✓ dc_x2✓ 1x2_v✓ (3/3) |
| Riestra–Vélez | 1-1 | 33.7/36.3/30.1 | E | un2.5✓ un1.5✗ 1x2_e✓ (2/3) |
| Auxerre–Angers | 1-3 | 49.7/28.3/21.9 | L | un3.5✗ btts_no✗ un1.5✗ (0/3) |
| Brest–Toulouse | 2-2 | 39.9/26.3/33.9 | L | ov1.5✓ ov2.5✓ 1x2_l✗ (2/3) |
| Lorient–Troyes | 1-2 | 47.3/26.8/25.9 | L | ov1.5✓ btts✓ ov3.5✗ (2/3) |
| Lyon–Le Havre | 1-1 | 59.8/23.3/16.9 | L | un3.5✓ un2.5✓ un1.5✗ (2/3) |
| Rosario Central–Gimnasia | 1-2 | 52.0/28.5/19.6 | L | un3.5✓ btts_no✗ un1.5✗ (1/3) |
| Huracán–Est. Río Cuarto | 1-1 | 53.7/32.5/13.8 | L | un2.5✓ un1.5✗ (1/2) |
| Vasco–Cruzeiro | 3-1 | 33.4/26.5/40.1 | V | dc_12✓ dc_x2✗ un1.5✗ (1/3) |
| Atl. Tucumán–Belgrano | 0-0 | 34.0/32.7/33.3 | L | un2.5✓ btts_no✓ un1.5✓ (3/3) |
| Talleres–Central Córdoba | 0-0 | 45.8/30.3/23.9 | L | un3.5✓ un2.5✓ btts_si✗ (2/3) |

Totales de la fecha: **lean 2/15 (13%) · escalera 29/44 (65.9%) · 9/15 empates**.

---

## Qué cambiar (si se decide hacerlo), en orden de impacto

1. **La escalera no debería "recomendar" lo que no tiene valor.** Si no hay
   `MARCA DE VALOR`, no mostrar recomendados — o mostrar los mercados ordenados
   por valor esperado (EV), no por probabilidad de mercado. Es un cambio de
   presentación, no del motor.
2. **Alinear la escalera con la lectura.** Que el pick destacado sea el de la
   lectura 1X2, no el mercado de mayor probabilidad.
3. **No repetir el mismo mercado de goles** (triple under) salvo que sea
   intencional y con valor.
4. **Revisar la presentación del favorito local** ("1X2 de favoritos
   sobreconfiados"): la confianza mostrada debe corresponder a la evidencia.
5. Todo esto es **presentación**. El problema de fondo — que la app no gana
   plata — sigue abierto y es el único que justifica tocar el motor, y solo
   respaldado por una medición OOS.

## Fuentes de los números

- Rentabilidad, favoritos sobreconfiados, Regla 5: `TRASPASO.md`.
- Calibración por liga / home bias agregado: `data/backtest.json`.
- Pronósticos del día: reproducción con el motor publicado
  (`repro_29.js`, reusa el harness de `test_alineacion.js`, suite verde 93/0).
- Resultados reales: corroborados en la web (ESPN, Guardian, agencias, medios
  locales de AR/BR/FR).
- Scripts de medición: `medir_historico.py`, `medir_lineas.py`, `medir_corners.py`, `medir_encogimiento.py`, `backtest.py`.
