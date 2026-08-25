#!/usr/bin/env python3
"""Tests de registrar_pronosticos() — el historial tiene que decir con qué
modelo se hizo cada pronóstico.

Por qué existe:

El 2026-08-24 `rho` de arg.1 pasó de +0.05 a -0.05 por un barrido sobre
5 temporadas. `historial_pronosticos.json` ya tenía registros hechos con
el valor viejo. Los dos conviven en el mismo archivo y, hasta ahora, sin
nada que los distinga.

`rho` ya se guardaba por registro. Lo que faltaba son las otras dos
constantes que mueven λ y que también se tocaron este mes:
`VIDA_MEDIA_DIAS` y el `prior` de la competición. Sin ellas, agregar el
historial para medir calibración mezcla eras del modelo sin avisar.

Lo que estos tests protegen, y es lo que importa de verdad:

**Un registro viejo no se estampa con las constantes de hoy.** Sería
peor que no tener el dato: convertiría "no sé con qué se calculó esto"
en una afirmación falsa. Solo se sella lo que se calcula ahora.

    python test_pronosticos.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
import actualizar as A

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def correr(partidos, previo=None):
    """Corre registrar_pronosticos aislada y devuelve el historial escrito."""
    with tempfile.TemporaryDirectory() as d:
        destino = Path(d) / "historial.json"
        if previo is not None:
            destino.write_text(json.dumps(previo, ensure_ascii=False),
                               encoding="utf-8")
        original = A.HISTORIAL_PRON
        A.HISTORIAL_PRON = destino
        try:
            # sin red: los pendientes no se resuelven, que no es lo que se mide acá
            A.registrar_pronosticos(partidos, season=2026, hoy="2026-08-24",
                                    traer_resultados=lambda slug: [])
            return json.loads(destino.read_text(encoding="utf-8"))
        finally:
            A.HISTORIAL_PRON = original


def partido(pid="espn1", comp="Liga Profesional Argentina"):
    return {
        "id": pid, "date": "2026-08-24", "comp": comp,
        "home": "Racing Club", "away": "Boca Juniors",
        "lh": 1.4, "la": 1.1, "rho": -0.05,
        "mercado": {"local": 2.10, "empate": 3.20, "visitante": 3.60},
    }


print("\nel sello del modelo — con qué constantes se calculó esto\n")

h = correr([partido()])
reg = h["espn1"]

prueba("el registro nuevo trae un bloque de modelo", "modelo" in reg)
prueba("declara la vida media que se usó",
       (reg.get("modelo") or {}).get("vida_media") == A.VIDA_MEDIA_DIAS)
prueba("declara el prior de la competición del partido",
       (reg.get("modelo") or {}).get("prior")
       == A.COMPETICIONES["arg.1"]["prior"])
prueba("sigue guardando rho, que ya se guardaba", reg["rho"] == -0.05)

# El campo `mercado` es la probabilidad implicita SIN margen. Hasta el
# 2026-08-25 se calculaba repartiendo el margen parejo entre las tres
# opciones, que es el metodo que el repo retiro ese mismo dia: infla la
# probabilidad del batacazo y desinfla la del favorito. Nadie lo lee
# hoy, pero un campo calculado con una vara retirada es un pie de
# banana para el que venga.
import medir_clv as _C
_esperado = _C.devig_shin([2.10, 3.20, 3.60])
prueba("el mercado guardado sale de Shin, como todo el resto del repo",
       all(abs(a - round(b, 4)) < 1e-4
           for a, b in zip(reg["mercado"], _esperado)))
prueba("y NO del reparto parejo, que da otro numero",
       reg["mercado"] != [round(x, 4) for x in _C.devig([2.10, 3.20, 3.60])])
prueba("y sigue guardando los λ", (reg["lh"], reg["la"]) == (1.4, 1.1))

# El prior es por competición, no global: si se sellara uno solo para
# todos, el sello mentiría en cuanto entrara una segunda liga.
h2 = correr([partido("espn2", "Brasileirão Série A")])
prueba("el prior sale de la competición, no de un valor único",
       h2["espn2"]["modelo"]["prior"] == A.COMPETICIONES["bra.1"]["prior"])
prueba("y son distintos entre ligas, que es la razón de guardarlo",
       A.COMPETICIONES["arg.1"]["prior"] != A.COMPETICIONES["bra.1"]["prior"])

# Las copas CONMEBOL no tienen prior propio.
h3 = correr([partido("espn3", "CONMEBOL Libertadores")])
prueba("una competición sin prior propio no rompe",
       "modelo" in h3["espn3"])
prueba("y lo declara vacío en vez de inventar un número",
       h3["espn3"]["modelo"].get("prior") is None)


print("\nlo viejo no se toca — un sello retroactivo sería una mentira\n")

# Este es el test que justifica el archivo. Un registro guardado antes
# de que existiera el sello se calculó con OTRAS constantes (rho +0.05,
# y quién sabe qué vida media). Estamparlo hoy con los valores actuales
# lo haría parecer comparable con los nuevos, que es justo lo contrario
# de lo que el sello existe para lograr.
viejo = {
    "espn0": {
        "fecha": "2026-08-01", "comp": "Liga Profesional Argentina",
        "home": "River Plate", "away": "Platense",
        "lh": 1.8, "la": 0.9, "rho": 0.05,
        "mercado": [0.55, 0.25, 0.20], "cuotas": [1.8, 4.0, 5.0],
        "resultado": [2, 0],
    }
}
h4 = correr([partido()], previo=viejo)

prueba("el registro viejo sigue existiendo", "espn0" in h4)
prueba("NO se le inventa el sello del modelo de hoy",
       "modelo" not in h4["espn0"])
prueba("y conserva su rho original, el que de verdad se usó",
       h4["espn0"]["rho"] == 0.05)
prueba("su resultado ya resuelto no se pisa",
       h4["espn0"]["resultado"] == [2, 0])
prueba("el registro nuevo de la misma corrida sí lo trae",
       "modelo" in h4["espn1"])

# Reprocesar dos veces no debe duplicar ni recalcular lo ya escrito.
h5 = correr([partido()], previo=h)
prueba("volver a correr no reescribe un registro ya guardado",
       h5["espn1"]["modelo"] == h["espn1"]["modelo"])


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
