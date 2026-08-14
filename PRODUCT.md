# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Lucas, personal use only, today. Lucas explicitly wants the app built so it *could* grow to other users later if it proves out — so avoid decisions that would be expensive to walk back for that (e.g. don't hard-code single-user assumptions into new features), but don't build multi-user infrastructure (accounts, auth, tenancy) speculatively either. No accounts, no sharing, no multi-user concerns *yet*.

## Product Purpose

VALOR es un **Asesor y Guía Inteligente de Apuestas Deportivas (Copiloto Cuantitativo)** enfocado en el fútbol argentino y copas CONMEBOL (Liga Profesional, Copa Libertadores, Copa Sudamericana, Copa Argentina). Su propósito es traducir modelos estadísticos avanzados en **veredictos de valor claros, recomendaciones guiadas y diagnósticos precisos** para el apostador.

Combina un modelo bivariado de goles esperados (Poisson / Dixon-Coles con calibración de $\rho$) y cálculo de valor esperado (EV, cuota justa desviggeada, stake de Criterio de Kelly) con el contexto cualitativo del partido (bajas, DT, rotaciones). En lugar de ser una calculadora pasiva de números fríos, actúa como un asistente analítico que responde directamente: *¿Dónde está la ventaja matemática hoy?*, *¿Por qué tiene valor esta jugada?*, y *¿Qué combinadas son matemáticamente viables frente a cuáles son trampas de baja diversificación?*.

## Positioning

Un **copiloto analítico de decisiones, no una calculadora árida ni un canal de tipster tradicional**. El mecanismo que lo sustenta es:
1. **Asesoría basada en Veredictos Honestos:** Diagnósticos claros por mercado (*Oportunidad de Valor*, *Mercado Neutral/Sin Ventaja*, *Desventaja Matemática / Riesgo no compensado*), respaldados por números y nivel de muestra en el backtest.
2. **Matriz de Marcadores Dixon-Coles calibrada por competición:** Cálculo de lambda por equipo con ajuste de fuerza de ataque/defensa y calibración de correlación ($\rho$) para marcadores bajos.
3. **Probabilidad Conjunta Real en Combinadas del mismo partido:** Lectura directa sobre la matriz (no producto ingenuo de probabilidades) con advertencia de redundancia en patas correlacionadas.
4. **Tratamiento estricto de PUSH (DNB) y Desvigg Proporcional:** Cuota justa y EV ponderando devoluciones de capital.
5. **Backtest Walk-Forward Out-of-Sample:** Auditoría histórica de calibración continua para sustentar las recomendaciones con evidencia empírica.

## Operating Context

Daily pipeline (`actualizar.py`) pulls upcoming fixtures, form, and standings from ESPN's public (unofficial, keyless) API, computes expected goals per team, and writes `data/partidos.json` plus supporting caches. Odds are never fetched automatically — they don't come from any single fixed bookmaker, so they're entered by hand in the app for whichever match/market Lucas is checking at the time. `backtest.py` is run manually, not part of the daily pipeline (it's slow and doesn't change day to day); it reconstructs what the model would have predicted using only pre-match history and compares against actual results, writing `data/backtest.json`. The frontend (`index.html`) is a single-file installable PWA (manifest + icons), mobile-first, in Argentine Spanish (`es-AR`).

## Capabilities and Constraints

- Expected goals (lambda) per team from home/away-conditioned scoring averages; competitions with enough cross-play (`arg.1`, `conmebol.libertadores`, `conmebol.sudamericana`) get an attack/defense strength calibration instead of a plain average; Copa Argentina (single-elimination, no repeated cross-play) uses a recency-weighted simple average.
- Markets covered include 1X2, Draw No Bet, over/under goals, and — from team-level Poisson rates — corners and cards.
- EV, fair odds (via proportional de-vig), and Kelly stake are computed per market; ranking is by EV, not by raw model probability.
- Push outcomes (e.g. DNB draws) scale EV by the probability the bet actually resolves, rather than being treated as a loss.
- Combo/parlay probability for legs within the same match is the true joint probability read off the scoreline matrix (AND-ed and summed over it), not the product of independent probabilities; a trap check warns when combined legs are measuring almost the same outcome, since the combined odds rarely compensate for the lack of real diversification.
- The app now auto-recommends same-match combos (`recomendarCombinada()`): it only proposes leg pairs/trios that both have a real joint-probability path (no cross-family independence approximation) and clear real EV — the true joint probability regularly differs meaningfully from the naive product of the legs' individual probabilities (verified: one pair came back at 0.194 true joint vs. 0.236 naive product for a real seeded match), so this genuinely relies on the matrix math, not a shortcut.
- Calibration confidence (`confianza()`) maps a live pick's market + probability to its historical hit-rate bucket from `data/backtest.json`, covering only what `backtest.py` actually measures (1X2, over/under goals, both-teams-to-score) — everything else (corners, cards, exact score, handicap, DNB, player props) returns no confidence figure rather than an invented one. Buckets under 15 samples are flagged as thin rather than shown as confident.
- Calibration is validated by a separate walk-forward backtest, not asserted by the live model.
- No real-money integration, no bet placement, no bookmaker account linkage — this is a decision-support / research tool only.
- Cross-match combos (legs from different matches) remain undecided/unbuilt — the recommendation engine is same-match only per Lucas's own scoping ("para el partido"); manual cross-match combo building still exists separately in the Combo tab.

## Evidence on Hand

Live match, form, standings, and head-to-head data comes from ESPN's public API (`data/partidos.json`, `equipos.json`, `cache_disciplina.json`). Backtest results live in `data/backtest.json`. No fabricated testimonials, pricing, or third-party endorsements — none should be introduced.

## Product Principles

- Rank by EV, never by raw probability — a high-probability pick with no market mispricing isn't the point.
- Distrust your own model until it's backtested: no EV claim ships without a calibration check behind it.
- Real joint probability over shortcuts — combo odds and correlated-leg detection come from the actual scoreline matrix, not independence assumptions.
- Manual odds entry is a deliberate constraint, not a gap to "fix" with a live odds feed unless Lucas asks for one.
- Personal tool: no multi-user, account, or sharing complexity unless the scope changes.
