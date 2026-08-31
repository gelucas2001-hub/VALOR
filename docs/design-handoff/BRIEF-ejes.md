# Brief para Claude Design — ordenar la pestaña Pronósticos

Escrito el 2026-08-31, después de que Lucas dijera lo que hay que
arreglar: *"siento que está todo muy mal ubicado… estamos rellenando
mucho un espacio y no estamos generando ese orden en la app en general
para que no se vea sobrecargada."*

Tiene razón. Esto explica **qué se puede mover libremente y qué no**,
para que el rediseño no rompa lo que está medido.

---

## El problema, en una línea

La pestaña Pronósticos creció apilando bloques uno abajo del otro. Hoy
son cinco, en este orden, y ninguno cede espacio al otro:

1. **Nuestra lectura** — una frase con el favorito y su probabilidad
2. **Escalera de riesgo** — 1 a 3 escalones (mercados de Resultado)
3. **Quién ataca más** — remates, al arco, córners esperados por equipo
4. **Quién puede marcar y quién puede rematar** — 6 jugadores en 3 líneas
5. **Otros mercados** — ~15 filas con probabilidad, cuota y umbral

Scrollear los cinco de punta a punta son unos 3000 px. El 5 es el más
largo y el menos importante.

---

## La arquitectura, que es lo que hace barato el rediseño

Desde el 2026-08-31 la app no tiene "bloques": tiene **ejes**, y todos
emiten **el mismo registro de diez claves**. La interfaz no sabe qué es
un córner — sabe dibujar un eje.

```
eje · titulo · estimacion · ancla · medido_por
confianza · aporte · mercado · lectura · apuesta
```

**Qué significa para vos:** podés reorganizarlos como quieras —
pestañas, acordeón, tarjetas, una vista resumen con detalle a demanda—
y agregar o sacar ejes **sin tocar una línea de lógica**. Todos los
ejes se dibujan con el mismo componente.

Los ejes de hoy y su estado real:

| eje | título en pantalla | confianza |
|---|---|---|
| resultado | Quién gana | calibrada |
| volumen | Cuántos goles | calibrada, sin aporte |
| dominio | Quién ataca más | calibrada (eng/fra) · sin medir (arg/bra) |
| jugadores | Quién puede marcar y quién puede rematar | mal_calibrada |

---

## Lo que NO se puede cambiar

Estas cuatro cosas no son estética: son el resultado de mediciones que
costaron semanas. Cambiarlas rompe la honestidad del producto.

**1. La regla de los dos metales** (`DESIGN.md`). Un color, un trabajo:

- **mostaza** `#D6963A` = *acá hay algo mejor que el precio*. Nada más.
- **terracota** `#C06848` = *cuidado, esto no rinde*. Nada más.
- **salvia** `#76846A` = voz secundaria. Nunca dice estado.

Hoy **ningún eje puede llevar mostaza**, y no es un olvido: contra el
precio no hay ventaja medida en ninguno. Si el rediseño necesita un
acento, que no sea ninguno de esos dos.

**2. El chip de confianza de cada eje.** Dice de qué fiarse, y sale de
una medición, no de una opinión. Puede cambiar de forma, de lugar o de
tipografía; no puede desaparecer ni suavizarse.

**3. La distinción lectura / recomendación.** Todo eje se **muestra**;
solo lo que pasa la vara del dinero se **marca**. Si el rediseño hace
que una lectura parezca una recomendación, deshace el trabajo entero.

**4. Los pies que explican los huecos.** *"No lo marcamos como
oportunidad y no es un descuido — contra el precio nunca se midió."*
Declarar el hueco es la disciplina del proyecto. Se puede reescribir
más corto; no se puede borrar.

---

## Lo que sí conviene cambiar, y es tu decisión

- **Los cinco bloques no pueden pesar igual.** Resultado es el único
  eje con información demostrada; Otros mercados es el más largo y el
  que menos aporta.
- **Jugadores y Dominio son lectura, no apuesta**, y hoy se ven igual
  de "duros" que la escalera. Deberían leerse como contexto.
- **Otros mercados son ~15 filas idénticas.** Es una tabla disfrazada
  de tarjetas.
- **Nada está colapsado.** No hay forma de ver el partido de un vistazo.

---

## Dónde mirarlo

```bash
python -m http.server 8765
```

Un partido con los cuatro ejes: `http://localhost:8765/#p/espn401841208`
→ pestaña **Pronósticos**. (Argentina y Brasil tienen los cuatro;
Premier y Ligue 1 a veces no tienen el de jugadores.)

Referencias en el repo: `DESIGN.md` (tokens y la regla de los dos
metales), `TRASPASO.md` §17 (la arquitectura de ejes y por qué existe),
`index.html` región `/* ==== INICIO EJES ==== */` (el contrato).
