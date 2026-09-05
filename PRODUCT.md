> ## ⚠️ Este documento describe el producto ANTERIOR
>
> Desde el **2026-09-05** la dirección es **Pronóstic**: un asesor
> conversacional que vive en `experto/`, rama `pronostic`. Lo de acá
> abajo —la PWA de `index.html`, el lenguaje de EV y Kelly, la promesa de
> "encontrar valor"— **quedó de lado**, y la última en concreto porque
> las mediciones del repo no la sostienen.
>
> **Empezá por `GEMINI.md`.** El diseño nuevo está en
> `docs/superpowers/specs/2026-09-05-pronostic-diseno.md`.
>
> Este archivo se conserva porque su historia y sus mediciones valen. No
> se toma como especificación de lo que se construye hoy.

# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Lucas, uso personal exclusivo hoy, con arquitectura modular pensada para poder escalar a más usuarios en el futuro sin reescrituras costosas (sin cuentas ni autenticación especulativa por ahora).

## Product Purpose

VALOR es un **asesor personal de fútbol**, no un tipster ni una calculadora fría de estadísticas y cuotas: investiga → analiza → interpreta → contrasta → discierne → explica → sugiere, por el usuario, para que sienta que "alguien ya hizo el trabajo pesado". Enfocado en fútbol sudamericano (Liga Profesional Argentina, Brasileirão Série A, Copa Libertadores, Copa Sudamericana). Simple de entender por delante aunque complejo por detrás — nadie debería necesitar saber qué es Poisson, Dixon-Coles o Kelly para entender qué dice VALOR. Ver `data/presentacion-claude.md` para la visión completa.

Combina un modelo bivariado de goles esperados (Poisson / Dixon-Coles con calibración de $\rho$) y cálculo de valor esperado (EV, cuota justa desviggeada, stake fraccional de Criterio de Kelly) con el contexto cualitativo del partido (posiciones, zonas, promedios de descenso, historial H2H, plantel con peso goleador y métricas de disciplina) producido por una skill de análisis independiente del modelo. **Los dos deben trabajar juntos, no en silos:** cuando coinciden es relevante, cuando discrepan también — la contradicción se muestra con confianza rebajada, no se oculta.

## Positioning

Un **asesor de decisiones, no una calculadora árida ni un canal de tipster tradicional**. La probabilidad NO es la recomendación: cuota, contexto y calidad de la estimación entran todos en el criterio final, y una recomendación existe solo cuando tiene razón de ser — VALOR puede decir 0, 1, 2 o excepcionalmente 3 sugerencias por partido, nunca por llenar tarjetas, y nunca tres mercados que repiten la misma tesis (ver estado real más abajo: esto último **hoy no se cumple**).

1. **Asesoría basada en Veredictos Honestos:** Diagnósticos claros por mercado (*Oportunidad Detectada*, *Mercado Neutral / Sin Ventaja*, *Riesgo no compensado*), respaldados por matemáticas rigurosas.
2. **Matriz de Marcadores Dixon-Coles calibrada por competición:** Cálculo de goles esperados (lambda) por equipo a partir de los goles observados, con ajuste de fuerza de ataque/defensa y calibración de correlación ($\rho$) para marcadores bajos. No es xG: xG mide la calidad de las ocasiones, y ESPN solo lo devuelve por jugador destacado, nunca por equipo.
3. **Tableros Deportivos Interactivos:** Mercados organizados en cuadrículas limpias de 3 columnas (1X2, Doble Oportunidad) y pares de 2 columnas (Total de Goles, Ambos Marcan, Primer Tiempo) con reactividad en vivo al tipear cuotas.
4. **Contexto Completo de Torneos:** Tablas de Posiciones por Zonas (Zona A, Zona B), Tabla Anual acumulada para copas y Tabla de Promedios para el descenso.
5. **Boleta de Combinadas Limpia:** Cálculo de probabilidad conjunta exacta sobre la matriz multivariada con sumatoria directa para apuestas del mismo partido.

## Estado real vs. visión (2026-08-30, ver `data/PROBLEMAS.md`)

- **Rentabilidad no demostrada:** ROI walk-forward contra cuota de cierre real de Pinnacle, **−3.27% ± 6.19** — el intervalo incluye cero. Ninguna medición hasta hoy demuestra ventaja real del motor sobre el mercado.
- **La escalera de recomendaciones contradice la Positioning de arriba:** ordena por probabilidad de mercado (no por valor), muestra siempre 3 tarjetas (nunca 0), y no está atada a la lectura 1X2 propia — caso medido: Lyon con local 59.8% (pick más confiado de la fecha) mostró tres unders de goles sin una sola apuesta a que gana el local. Es lógica de selección/presentación en `index.html`, no del motor — corregible sin tocar λ.
- **No usar lenguaje de "valor" (mostaza) donde no hay ventaja medida.** La interfaz no debe prometer más de lo que el motor puede sostener hoy.

## Operating Context

- Pipeline diario (`actualizar.py`): extrae fixtures, resultados, tablas y estadísticas disciplinarias (córners, tarjetas, faltas) desde la API pública de ESPN y genera `data/partidos.json` y `data/tablas.json`.
- Regla de Cuota Mínima Objetivo: el sistema calcula automáticamente la cuota umbral de entrada rentable ($\ge (1 + E_{min}) / p$) para cada mercado, permitiendo al usuario saber de inmediato a partir de qué número apostar en su bookie (Bet365, Betano, etc.) sin obligarlo a tipear cuotas a mano.
- Frontend (`index.html`): Progressive Web App (PWA) de archivo único, instalable en móviles y con layout adaptativo multipanel para desktop. **La línea gráfica la define `DESIGN.md`, no este archivo**: prensa deportiva argentina vieja, fondo `#1B1611`, mostaza `#D6963A` para valor y terracota `#C06848` para alerta. La paleta anterior (negro frío, cian, verde semáforo) quedó descartada el 2026-08-18 y estuvo escrita acá hasta el 2026-08-24 — si volvés a ver azul y cian en un documento, es viejo.

## Capabilities and Constraints

- Estimación de lambda (goles esperados) condicionada por localía/visita y calibración de fuerzas de ataque y defensa.
- Mercados modelados: 1X2, Doble Oportunidad, Draw No Bet (DNB), Más/Menos Goles (0.5, 1.5, 2.5, 3.5), Ambos Marcan (BTTS), Primer Tiempo (1T) y Marcadores Exactos.
- Evaluación de EV, cuota justa y tamaño de posición seguro (Kelly fraccional con tope de 4% de banca).
- Ordenamiento dinámico: Por Mayor Ventaja (+EV), Mayor Probabilidad (%) y Horario cronológico.
- Herramienta de soporte a la decisión: sin integración de dinero real ni colocación automática de apuestas.

## Evidence on Hand

- Fixtures, tablas de posiciones de Zona A/B/Anual/Promedios, últimos partidos con escudos y enfrentamientos H2H provistos por ESPN (`data/partidos.json`, `data/tablas.json`, `data/cache_disciplina.json`).
- Análisis y lecturas tácticas curadas en `data/analisis.json`.

## Product Principles

- **Priorizar el Valor (+EV) sobre el favoritismo ciego:** Una apuesta con alta probabilidad no es rentable si la cuota no compensa el riesgo.
- **No forzar recomendaciones:** una sugerencia existe porque tiene razón de ser, no porque la interfaz necesite llenar tarjetas. 0, 1, 2 o excepcionalmente 3 — nunca siempre 3, y nunca varios mercados que repiten la misma tesis.
- **La contradicción se muestra, no se oculta:** cuando el motor y la skill de análisis discrepan, la app lo dice explícito y baja la confianza — no filtra en silencio dándose la razón a sí misma.
- **Probabilidad Conjunta Real:** En combinadas del mismo partido, la probabilidad se calcula sobre la matriz de eventos correlacionados, nunca como un producto ingenuo.
- **Cero Fricción y Claridad Visual:** Presentación limpia, sin redundancias ni formularios pesados, con retroalimentación inmediata.
- **Disciplina de Banca:** Asignación proporcional conservadora (1% a 4% del saldo) para proteger el capital en cualquier racha.
- **No sobreingeniería:** producto sofisticado detrás, sencillo delante. Cada complejidad nueva debe justificar qué problema real resuelve — ¿esto hace a VALOR mejor pronosticador, o solo más complicado?
