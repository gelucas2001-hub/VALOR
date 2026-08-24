# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Lucas, uso personal exclusivo hoy, con arquitectura modular pensada para poder escalar a más usuarios en el futuro sin reescrituras costosas (sin cuentas ni autenticación especulativa por ahora).

## Product Purpose

VALOR es un **Asesor Deportivo Inteligente y Copiloto Cuantitativo de Apuestas** enfocado en el fútbol argentino y copas internacionales CONMEBOL (Liga Profesional de Fútbol, Copa Libertadores, Copa Sudamericana, Copa Argentina). Su propósito es traducir modelos estadísticos avanzados en **veredictos de valor claros, recomendaciones guiadas y tableros deportivos interactivos** para la toma de decisiones informada.

Combina un modelo bivariado de goles esperados (Poisson / Dixon-Coles con calibración de $\rho$) y cálculo de valor esperado (EV, cuota justa desviggeada, stake fraccional de Criterio de Kelly) con el contexto cualitativo del partido (posiciones, zonas, promedios de descenso, historial H2H con escudos oficiales y métricas de disciplina).

## Positioning

Un **copiloto analítico de decisiones, no una calculadora árida ni un canal de tipster tradicional**:
1. **Asesoría basada en Veredictos Honestos:** Diagnósticos claros por mercado (*Oportunidad Detectada*, *Mercado Neutral / Sin Ventaja*, *Riesgo no compensado*), respaldados por matemáticas rigurosas.
2. **Matriz de Marcadores Dixon-Coles calibrada por competición:** Cálculo de xG (lambda) por equipo con ajuste de fuerza de ataque/defensa y calibración de correlación ($\rho$) para marcadores bajos.
3. **Tableros Deportivos Interactivos:** Mercados organizados en cuadrículas limpias de 3 columnas (1X2, Doble Oportunidad) y pares de 2 columnas (Total de Goles, Ambos Marcan, Primer Tiempo) con reactividad en vivo al tipear cuotas.
4. **Contexto Completo de Torneos:** Tablas de Posiciones por Zonas (Zona A, Zona B), Tabla Anual acumulada para copas y Tabla de Promedios para el descenso.
5. **Boleta de Combinadas Limpia:** Cálculo de probabilidad conjunta exacta sobre la matriz multivariada con sumatoria directa para apuestas del mismo partido.

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
- **Probabilidad Conjunta Real:** En combinadas del mismo partido, la probabilidad se calcula sobre la matriz de eventos correlacionados, nunca como un producto ingenuo.
- **Cero Fricción y Claridad Visual:** Presentación limpia, sin redundancias ni formularios pesados, con retroalimentación inmediata.
- **Disciplina de Banca:** Asignación proporcional conservadora (1% a 4% del saldo) para proteger el capital en cualquier racha.
