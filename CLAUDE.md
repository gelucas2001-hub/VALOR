# VALOR — reglas del repo

Leé esto antes de tocar nada. Existe porque tres herramientas de IA
editaron `index.html` en paralelo sin saber una de la otra, y el
resultado fue trabajo perdido y funcionalidad borrada.

## Antes de empezar

Leé `docs/superpowers/specs/2026-08-16-rediseno-desde-cero-design.md`.
Ahí está qué es el producto, la línea gráfica, y las reglas de cómo se
recomienda. No improvises por encima de eso.

## Qué es cada cosa

| Archivo | Qué hace | Quién lo toca |
|---|---|---|
| `actualizar.py` | Baja datos de ESPN y calcula λ. Corre solo, 2 veces por día, vía GitHub Actions | Con cuidado — es el motor |
| `index.html` | La app en vivo | Ver "rediseño en curso" |
| `backtest.py` | Calibración contra resultados | A mano |
| `medir_sesgo.py` | Cuánto nos apartamos de la línea del mercado | A mano, antes y después de tocar el modelo |
| `medir_vs_mercado.py` | Brier contra la cuota de cierre real | A mano |
| `calibrar_ligas.py` | Cuánto vale cada liga sudamericana | A mano, cada tanto |
| `data/*.json` | Lo escribe el cron. **No editar a mano** | Nadie |
| `data/analisis.json`, `data/equipos.json` | Análisis cualitativo, carga manual. El cron **nunca** los toca | A mano |

## Restricciones duras

- **`actualizar.py`: solo biblioteca estándar.** Corre en GitHub Actions sin `pip install`. Nada de dependencias.
- **Sin claves de API.** Todo sale de endpoints públicos.
- **No cambiar el contrato de `data/partidos.json`.** Agregar campos sí; renombrar o cambiar tipos rompe el frontend.
- **No tocar constantes del modelo para que un número dé mejor.** Si una medición no mejora, el hallazgo es que no mejoró. Hay scripts para medir: usalos.

## Rediseño en curso

Se está reescribiendo la interfaz de cero según el spec. Reglas:

- La interfaz nueva se construye en un **archivo aparte**, no editando `index.html`.
- `index.html` queda en vivo hasta que la nueva esté terminada y verificada.
- El motor matemático (Dixon-Coles, Kelly, combinadas) se **copia**, no se reescribe: está validado y reescribirlo arriesga errores numéricos silenciosos.
- Referencia del motor verificado: tag `motor-verificado`.
- Trabajo previo descartado: rama `ui-antigravity` (no borrar, es respaldo).

## Para evitar el problema que originó este archivo

Una herramienta por área. Si vas a usar otra IA en paralelo, que sea
para algo distinto (backend vs. interfaz vs. contenido) o en una rama
aparte. Dos herramientas sobre el mismo archivo terminan pisándose.

## Verificar antes de dar algo por hecho

Este proyecto tiene historial de afirmaciones que resultaron falsas al
chequearlas contra la API real (que `/teams/{id}/schedule` traía todas
las competiciones — no; que no había cuotas históricas — sí las hay en
football-data.co.uk). Si vas a afirmar algo sobre los datos, medilo.
