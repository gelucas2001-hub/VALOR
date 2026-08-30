# VALOR — Documento de reposicionamiento (para evaluación externa)

> **Cómo usar este documento:** es material de presentación para que un evaluador
> externo (en este caso, Claude) opine sobre la **dirección del producto VALOR**,
> contrastando la visión contra la implementación actual.
>
> Este documento es **una sola voz**: fusiona la visión de producto y el criterio
> de recomendación en una única pieza coherente (sin las contradicciones internas
> que tenían las versiones previas), y agrega el **estado real y medido** de la
> app hoy — porque sin eso no se puede responder si la app va por la línea de la
> visión.
>
> La pregunta que se le va a hacer al evaluador está al final.

---

## 1. Qué quiero que sea VALOR

VALOR es una aplicación experta en **fútbol + análisis + pronósticos + apuestas**.
No es un "tipster" clásico ("yo te digo qué apostar") ni una calculadora fría de
estadísticas y cuotas. El concepto central:

> **VALOR debe hacer por el usuario gran parte del trabajo que tendría que hacer
> antes de apostar, y convertirlo en una lectura clara, humana y útil del partido.**

Una persona entra a VALOR, elige un partido y siente: *"acá alguien ya hizo el
trabajo pesado por mí."* La intuición detrás del producto es un **asesor
personal de fútbol**: alguien que investiga → analiza → interpreta → contrasta →
discierne → explica → sugiere.

El usuario final no sabe de estadística ni quiere estudiar fútbol horas. Por eso
la app debe ser **simple de entender aunque compleja por detrás**. Nadie debería
necesitar entender Poisson, Dixon-Coles, Brier, Shin, EV, Kelly ni calibración
para entender qué dice VALOR.

## 2. La información debe convertirse en criterio

VALOR no debe enumerar información, sino interpretarla:

> ❌ "River ganó 4 de sus últimos 6, tiene 58% de posesión, el rival recibió 7
> goles, hay dos lesionados, la cuota es 1.40."
>
> ✅ "River llega como favorito, pero sus resultados recientes esconden una
> defensa que viene concediendo con frecuencia. La baja en X y el contexto hacen
> que el partido probablemente sea más cerrado de lo que su cuota sugiere."

**Datos → interpretación → conclusión.** Con narrativa y personalidad, PERO con
una regla dura: **narrativa no significa inventar**. La chispa surge de
interpretar bien la información, no de fabricar certezas.

## 3. Qué debería responder por cada partido

- ¿Qué creemos que puede pasar? (lectura general)
- ¿Por qué creemos eso? (argumentos futbolísticos y evidencia)
- ¿Qué cosas nos llaman la atención? (estadísticas, tendencias, contexto, bajas)
- ¿Qué sugerencias consideramos interesantes? (NO las de mayor probabilidad)
- ¿Qué tan convencidos estamos, y qué riesgos/dudas existen?

## 4. Probabilidad no es recomendación

Que un mercado tenga probabilidad alta NO significa que sea la mejor sugerencia.
La app debe distinguir entre **probabilidad, confianza, calidad de la
estimación, contexto, atractivo de la cuota, riesgo y recomendación**. La
recomendación final surge de la evaluación conjunta de todo eso.

## 5. No forzar pronósticos — y poder decir 0

Una recomendación existe porque tiene razón de ser, no porque la interfaz
necesite llenar tarjetas. VALOR puede decir **0, 1, 2 o excepcionalmente 3**
recomendaciones, según lo que el partido realmente ofrezca. Si no hay una
sugerencia clara, dice: *"No encontramos una opción que nos convenza lo
suficiente."* Pero también debe evitar el extremo opuesto (no siempre decir
"no apostar"): **criterio para recomendar y criterio para abstenerse**.

Además, las recomendaciones no deben ser **redundantes entre sí**: tres mercados
que expresan la misma tesis (p.ej. Empate + Under 2.5 + BTTS No) no deben
presentarse como tres opiniones distintas. Importa la diversidad de ideas, no la
cantidad.

## 6. El criterio de recomendación (cuota + probabilidad + contexto)

La tasa de acierto es un objetivo fundamental, pero NO es suficiente. Una
recomendación no se evalúa solo por acertar o fallar: **importa el precio al que
se ofrece esa posibilidad**.

- Un pronóstico de alta probabilidad puede ser MALA recomendación si la cuota es
  demasiado baja para el riesgo.
- Un pronóstico de menor probabilidad puede ser MUY interesante si la cuota
  compensa el riesgo y el análisis lo respalda.

VALOR busca el equilibrio entre **calidad del pronóstico + probabilidad +
contexto + cuota + riesgo + atractivo de la oportunidad**. Esto NO quiere decir
convertirse en una plataforma de value-betting puro (no es maximizar una fórmula
de EV ni transformar cada decisión en inversión financiera). El objetivo:

> **encontrar pronósticos y situaciones que tengan sentido futbolístico y que,
> cuando las condiciones del mercado lo permitan, representen una oportunidad
> atractiva para alguien que va a apostar.**

La cuota es parte del criterio, pero no lo domina ciegamente. **No hay reglas
simplistas** tipo "cuota alta = buena" o "cuota baja = mala": una cuota 1.30
puede ser razonable si la probabilidad estimada y la lectura lo justifican, y
pobre en otro contexto.

**Objetivo final:** VALOR busca **mejorar la calidad de las decisiones de
apuesta del usuario**, idealmente con resultados económicamente favorables a
largo plazo. La rentabilidad **no se asume ni se promete: debe demostrarse** con
evaluación histórica, muestras grandes y pruebas fuera de muestra.

> **VALOR debe intentar encontrar buenas decisiones, no simplemente apuestas
> ganadoras.**

## 7. Motor + skill + contexto (trabajan juntos, no en silos)

VALOR tiene dos fuentes de conocimiento:

- **Motor cuantitativo:** estadísticas, probabilidades, modelos, datos
  históricos, cuotas, información estructurada (Poisson/Dixon-Coles, EV, Kelly).
- **Skill de análisis:** investigación web, lesiones, suspensiones,
  alineaciones, noticias, contexto, dinámica de equipos, lectura futbolística.

No deben sustituirse mutuamente: **deben trabajar juntos**. Cuando coinciden,
eso es relevante; cuando discrepan, también. Una contradicción entre modelo y
contexto no se oculta: **se detecta, y puede bajar legítimamente la confianza**
("Hay señales contradictorias y nuestra confianza disminuye"). Nunca se fuerza a
que ambas terminen diciendo lo mismo.

## 8. El usuario también quiere ver los datos

No quiero una caja negra absoluta. VALOR debe tener dos funciones simultáneas:
**hacer el análisis por el usuario** y **darle información para que pueda
cuestionar o complementar ese análisis**.

## 9. No sobreingeniería

Un producto sofisticado detrás, sencillo delante. No agregar métricas, módulos,
scores, estados o pantallas "por si acaso". Cada complejidad debe justificar qué
problema real resuelve. La pregunta permanente:
**¿Esto hace a VALOR mejor pronosticador, o solo más complicado?**

---

## 10. ESTADO REAL DE LA APP HOY (lo que Claude necesita saber para opinar)

Todo lo anterior es la **visión**. Lo que sigue es el **estado medido** de la
implementación actual, en el día de hoy (2026-08-30).

### Arquitectura que ya existe

- **Motor cuantitativo** en `index.html` + `actualizar.py`: Poisson/Dixon-Coles,
  devig con Shin, EV, Kelly fraccional. Validado con `doble_via.py` (paridad
  Python↔JS).
- **Skill de análisis cualitativa** (`valor-analisis-inclinacion`, que escribe
  `analisis.json` con `inclinacion/local/visitante/contexto/veredicto`): la
  lectura humana independiente del modelo.
- Los **dos flujos existen y son independientes** — lo que la visión quiere
  (que trabajen juntos y se contrasten) es exactamente la pieza que hoy **no
  está conectada**.

### Lo que está medido (honestidad de base)

- **Rentabilidad:** ROI walk-forward contra la cuota de cierre real de Pinnacle:
  **−3.27% ± 6.19**. Estadísticamente **indistinguible de cero**. Histórico en
  Argentina llegó a −6.18% y tras fixes bajó a −0.94% (z=−0.2).
- **Calibración por liga:** el modelo NO sobreestima al local en agregado (ARG
  41.7% vs 43.7%, BRA 47.0% vs 46.3%, etc.).
- **Mercado de estadísticas:** solo córners calibran bien; faltas ~9 puntos de
  sesgo; remates ~7.
- **Conclusión honesta:** hasta ahora, ninguna medición demuestra que el motor
  supere al mercado en nada medible. No está probado que el pronóstico tenga
  ventaja real.

### Problemas que contradicen la visión (encontrados y documentados)

La **escalera de pronósticos** (la columna de "recomendados" que el usuario ve)
hoy contradice la visión en varios puntos:

1. **Ordena por probabilidad de mercado, no por valor.** Presenta como
   "recomendaciones" los mercados de mayor probabilidad (`ov1.5` ~80%, `un3.5`
   ~77-83%, `un2.5`, `un1.5`), que pagan ~1.05-1.15. Esto es exactamente lo que
   la sección 4 prohíbe ("probabilidad no es recomendación").
2. **Siempre muestra 3 tarjetas** (a veces triple under: `un3.5 un2.5 un1.5` en
   un mismo partido = una sola idea repetida). Jamás dice "no hay nada que nos
   convenza". Contradice las secciones 5 y 12.
3. **No está ligada a la lectura.** Ejemplo real: Lyon con local 59.8% (el pick
   más confiado de la fecha) mostró una escalera de TRES under de goles sin
   ninguna apuesta a que gana el local. Contradice la sección 7 (motor+skill
   juntos).
4. **"Acierto mentiroso":** en una fecha real (29/08, 15 partidos) la escalera
   acertó 29/44 mercados (66%), pero casi todos los aciertos fueron a cuota
   ~1.10 — acertar mucho a cuota baja no es ganar plata, es regalar margen.

### La pregunta de fondo que la visión NO resuelve

La mejor capa de criterio y presentación del mundo no convierte EV negativo en
positivo. La visión de "asesor personal" es excelente como capa de claridad y
confianza, **pero el producto solo se sostiene si el pronóstico detrás tiene
valor real** — y eso hoy no está demostrado. Es la pregunta que domina a todas
las demás.

---

## 11. Preguntas concretas para el evaluador (Claude)

1. ¿La dirección del producto que describe este documento es coherente y
   defendible? ¿Hay alguna inconsistencia interna que deba resolverse?
2. ¿El estado real de la app (sección 10) va por esta línea, o se desvió? ¿Dónde
   exactamente?
3. ¿Qué partes de la implementación actual están bien alineadas y NO deberían
   cambiarse?
4. ¿Qué partes contradicen esta filosofía y deberían priorizarse para corregir?
5. Priorización: dado que el motor no tiene ventaja demostrada hoy, ¿por dónde
   atacar primero — la capa de criterio/recomendación, o demostrar valor real en
   el pronóstico?
6. ¿Qué le falta a VALOR para sentirse realmente como el producto descrito acá?

No se quiere una respuesta complaciente. Si la app se está desviando, decirlo. Si
la visión misma es inconsistente o contraproducente, cuestionarla. No asumir que
una implementación existente está bien solo porque funciona.
