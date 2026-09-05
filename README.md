# VALOR

Fútbol y apuestas. Un motor de datos que corre solo, y **Pronóstic**, un
asesor conversacional encima.

## Por dónde entrar

**Si sos una IA o venís a programar: leé `GEMINI.md` primero.** Dice qué
se toca, qué vive y no se toca, y qué quedó de lado. Ese último punto
importa: buena parte del repo describe un producto anterior.

- **`experto/`** — Pronóstic, el asesor. Rama `pronostic`. Es donde se
  trabaja hoy.
- **`actualizar.py` + `data/`** — el motor. Baja ESPN y Bet365 dos veces
  por día por GitHub Actions y calcula los goles esperados. No se toca a
  mano.
- **`docs/superpowers/specs/2026-09-05-pronostic-diseno.md`** — qué es
  Pronóstic, por qué, y los 22 campos contra los que se audita.
- **`TRASPASO.md`** — el historial: qué salió mal, qué se midió, qué está
  cerrado. Más nuevo que `CLAUDE.md`; si se contradicen, gana este.

## Para usarlo

```
git pull origin main
python experto/probar.py        # chequeo, no gasta API
python experto/bot.py --consola
```

El paso a paso completo está en **`experto/ARRANCAR.md`**. Y sin ninguna
clave de API, en **`experto/SIN_CLAVE.md`**.

## Lo que este repo no promete

No encuentra apuestas con ventaja sobre el mercado. Está medido que no:
ROI dentro del ruido en las cinco ligas, 39 ventanas de umbral sin una
positiva fuera de muestra, y el desacuerdo con el precio sin contenido
informativo. Lo que hace es leer el partido, decir qué está caro y
acompañar la decisión — diciendo siempre cuándo no le está ganando al
mercado.
