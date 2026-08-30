# Tareas pendientes — diagnóstico 2026-08-30

## Estado del proyecto

### Lo que se diagnosticó hoy (2026-08-30)

#### 1. `senalDividida` — REVISADO, SIN BUG

- **Función:** `index.html` líneas 1673-1709
- **Diagnóstico:** Ejecutado `sonda_senal.js` (script creado en sesión anterior, nunca corrió). Confirmó que la función devuelve opciones en conflicto, no recomendadas.
- **Veredicto:** No hay bug. La función detecta cuando el desarrollo (ritmo/estructura/ambos_marcan) choca con mercados de goles o ambos-marcan, y devuelve esa lista para que la UI las excluya de la marca dorada.
- **Confusión posible:** `dir` es la dirección de la señal del desarrollo, NO una recomendación de apuesta. `opciones` son los mercados en conflicto, NO los elegidos.
- **Consumo:** En `tabPronosticos` (líneas 2335, 2394) se usa para excluir de la marca: `!(senal && senal.opciones.includes(op.id))`. Correcto.

#### 2. Francia — 4 partidos fallidos (27 ago 2026, journée 2)

| Partido | λ del modelo | Resultado real | Error |
|---|---|---|---|
| AJ Auxerre 1-3 Angers | lh=1.424, la=0.853 | Gana Angers (visitante) | Local puso como favorito (49%) |
| Brest 2-2 Toulouse | lh=1.483, la=1.348 | Empate 2-2 | Local puso como favorito (36% vs 36%) |
| Lorient 1-2 Troyes | lh=1.533, la=1.069 | Gana Troyes (visitante) | Local puso como favorito (51%) |
| Lyon 1-1 Le Havre | lh=1.863, la=0.887 | Empate 1-1 | Local puso como favorito (65%) |

- **Causa:** Francia agregada el 2026-08-25. El `barrido_lambda.py` del 29 **no evaluó Francia** en su partición OOS (walk-forward). Los λ son una extensión no calibrada del modelo con `vida_media=300`, `prior=8`, `rho=-0.05`.
- **Sin análisis cargado:** Estos 4 partidos NO tienen entrada en `data/analisis.json`, así que `senalDividida` ni siquiera entró en juego. El error es del modelo λ, no de presentación.

### Estado de otras áreas

- **ROI histórico:** −0.94% (z = −0.2), indistinguible de cero. Corregido de −6.18% con `historia_reciente()` + `VIDA_MEDIA_DIAS=300`.
- **Barrido lambda (2026-08-29):** Producción en óptimo. No tocar λ salvo fuente nueva.
- **Mercado:** Tiramos perdiendo vs cierre (0.645 vs 0.623). Sin evidencia de ventaja hasta que `medir_clv.py` tenga datos.

---

## Listo para Claude Code (llegada ~5:20 hs)

### Ya diagnosticado — no duplicar trabajo

1. `senalDividida`: revisado, sin bug documentado. No hace falta patch.
2. Francia 4 partidos: λ no calibrado. Cohorte nueva sin barrido OOS. Si Claude Code quiere evaluar, tiene los datos en `data/historial_pronosticos.json` (ids: `espn401876484`, `espn401876483`, `espn401876482`, `espn401876481`).

### Pendiente de validación

1. **Calibrar λ para Francia:** ¿Vida media adecuada para una liga nueva? ¿Prior diferente? ¿rho diferente? Requiere datos de más partidos o barrido específico para Francia.
2. **Regla de alineación:** Verificar que está actuando correctamente cuando hay análisis cargado. Los 4 franceses no tenían análisis, así que no pudo actuar.
3. **Criterios A-E en `index.html`:** Pendiente de implementar si está en el plan.

---

## Pendiente para OpenCode (si hay algo mecánico claro)

Sin tareas mecánicas claras identificadas hoy. Si hay algo específico, documentarlo aquí antes de asignar.

---

## Prioridades para las próximas horas

1. **Si hay más partidos de Francia disponibles:** evaluar si el patrón de error se repite (local sobreestimado). Si sí, es λ mal para Francia.
2. **Esperar Claude Code para:** decisión sobre calibrar λ para Francia, implementación de criterios A-E, cualquier cambio en motor/valores.
3. **No tocar nada sin diagnóstico:** el repositorio tiene historia de 3 IAs editando `index.html` en paralelo. Una herramienta por tarea, documentar estado antes de cada cambio.
