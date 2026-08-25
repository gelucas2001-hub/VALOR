#!/usr/bin/env python3
"""Tests de historia_equipos.py — la historia larga, cruzada a ids de ESPN.

Qué protegen, y por qué cada uno existe:

- **Que los estadísticos resumidos digan lo mismo que los valores
  sueltos.** El archivo guarda `n`, `suma` y `suma2` en vez de 80.000
  números, y de ahí salen la media y la varianza. Si el resumen y la
  lista cruda no coinciden, todo lo que se calcule después está mal y
  no hay forma de notarlo mirando el JSON.
- **Que lo que no cruza quede escrito en el archivo.** Es la regla que
  ya costó 1521 partidos en `historico.py`: un descarte silencioso no
  se ve como un error, se ve como menos datos.
- **Que una liga sin estadísticas no genere una entrada vacía.**
  ARG.csv y BRA.csv no traen ni una columna de estadísticas en 11.855
  partidos. Una entrada con cero equipos se parece demasiado a una
  entrada con datos.

    python test_historia_equipos.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import historia_equipos as HE

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def cerca(a, b, tol=1e-9):
    return a is not None and abs(a - b) < tol


print("")
print("resumir() — tres números que reemplazan a la lista entera")
print("")

_m = {"corners": {"10": [4.0, 6.0, 8.0], "20": [5.0, 5.0]},
      "faltas": {"10": [12.0, 14.0]}}
r = HE.resumir(_m)

prueba("cuenta los partidos", r["corners"]["10"]["n"] == 3)
prueba("suma los valores", cerca(r["corners"]["10"]["suma"], 18.0))
prueba("y la suma de cuadrados",
       cerca(r["corners"]["10"]["suma2"], 16.0 + 36.0 + 64.0))
prueba("cada equipo por separado", r["corners"]["20"]["n"] == 2)
prueba("y cada metrica por separado", "faltas" in r and "10" in r["faltas"])

# EL test: los tres numeros tienen que devolver la media y la varianza
# exactas, porque despues nadie va a poder comparar contra la lista.
d = r["corners"]["10"]
prueba("la media sale del resumen", cerca(HE.media(d), 6.0))
prueba("y la varianza tambien",
       cerca(HE.varianza(d), (4 + 0 + 4) / 3))
prueba("un equipo de un solo partido tiene varianza cero",
       cerca(HE.varianza({"n": 1, "suma": 5.0, "suma2": 25.0}), 0.0))
prueba("sin partidos no hay media", HE.media({"n": 0, "suma": 0, "suma2": 0}) is None)
prueba("ni varianza", HE.varianza({"n": 0, "suma": 0, "suma2": 0}) is None)

prueba("un equipo con un solo partido igual se guarda",
       HE.resumir({"corners": {"9": [7.0]}})["corners"]["9"]["n"] == 1)
prueba("muestras vacias dan resumen vacio", HE.resumir({}) == {})
prueba("y None tampoco explota", HE.resumir(None) == {})


print("")
print("prior() — la historia como ancla del equipo, no de la liga")
print("")

# El metodo medido el 2026-08-25: la historia encogida hacia la liga es
# el ancla, y encima va la temporada en curso. Ver TRASPASO.md.
p = HE.prior({"n": 100, "suma": 700.0, "suma2": 5600.0}, media_liga=5.0, k=10.0)
prueba("con mucha historia, el ancla es casi la del equipo",
       cerca(p, (700.0 + 10.0 * 5.0) / 110.0))
prueba("y ese numero esta cerca del 7 del equipo", 6.5 < p < 7.0)

p2 = HE.prior({"n": 2, "suma": 14.0, "suma2": 98.0}, media_liga=5.0, k=10.0)
prueba("con poca historia, el ancla se pega a la liga", p2 < 5.5)
prueba("nunca cae fuera del equipo y la liga", 5.0 <= p2 <= 7.0)

prueba("sin historia, el ancla ES la liga",
       cerca(HE.prior({"n": 0, "suma": 0.0, "suma2": 0.0}, 5.0, 10.0), 5.0))
prueba("sin resumen tampoco inventa", cerca(HE.prior(None, 5.0, 10.0), 5.0))
prueba("con k enorme, el ancla es la liga aunque haya historia",
       cerca(HE.prior({"n": 100, "suma": 700.0, "suma2": 5600.0}, 5.0, 1e9),
             5.0, tol=1e-3))


print("")
print("construir() — la forma del archivo, sobre datos de mentira")
print("")

# Dos ligas: una con estadisticas y otra sin ellas, que es el caso real
# de arg/bra. Cada partido trae los dos equipos.
#
# La liga tiene 11 equipos y no 3 porque `parametros_metricas()` exige
# MIN_EQUIPOS=8 antes de estimar `k` — con menos, la estimacion del
# ruido es mas ruidosa que lo que quiere medir. Un fixture de 3 equipos
# probaba contra una guarda real y correcta.
def _relleno():
    """Ocho equipos mas, con medias distintas para que `k` se pueda estimar."""
    out = []
    for i in range(4):
        casa, visita = f"F{2*i+1}", f"F{2*i+2}"
        for j in range(12):
            out.append({"home": casa, "away": visita,
                        "est": {"corners": {"h": 4.0 + i + (j % 3),
                                            "a": 3.0 + i + (j % 2)},
                                "faltas": {"h": 11.0 + i, "a": 13.0 - i}}})
    return out


_PARTIDOS = {
    "xx": [{"home": "Alfa", "away": "Beta",
            "est": {"corners": {"h": 6.0, "a": 4.0},
                    "faltas": {"h": 12.0, "a": 14.0}}}
           for _ in range(12)]
    + [{"home": "Gamma", "away": "Alfa",
        "est": {"corners": {"h": 3.0, "a": 7.0},
                "faltas": {"h": 10.0, "a": 11.0}}} for _ in range(12)]
    + _relleno(),
    "yy": [{"home": "Uno", "away": "Dos", "est": None} for _ in range(50)],
}
_IDX = {"xx": dict({"alfa": "1", "beta": "2", "gamma": "3"},
                   **{f"f{i}": str(100 + i) for i in range(1, 9)}),
        "yy": {"uno": "10", "dos": "20"}}

doc = HE.construir(_PARTIDOS, _IDX, ligas={"xx": "xx.1", "yy": "yy.1"})

prueba("la liga con estadisticas entra", "xx.1" in doc["ligas"])
prueba("con sus equipos", len(doc["ligas"]["xx.1"]["equipos"]) == 11)
prueba("y sus parametros de liga",
       "corners" in doc["ligas"]["xx.1"]["parametros"])
prueba("contando los partidos que aportaron",
       doc["ligas"]["xx.1"]["partidos"] == 72)

# EL test de la liga sin estadisticas: no puede quedar una entrada vacia
# que se parezca a una entrada con datos.
prueba("la liga SIN estadisticas no genera entrada", "yy.1" not in doc["ligas"])
prueba("pero se dice que se la miro", "yy.1" in doc.get("sin_estadisticas", []))

# Alfa jugo 24 partidos (12 de local con 6, 12 de visitante con 7).
alfa = doc["ligas"]["xx.1"]["equipos"]["1"]["corners"]
prueba("un equipo acumula local y visitante", alfa["n"] == 24)
prueba("con la suma de los dos lados", cerca(alfa["suma"], 12 * 6.0 + 12 * 7.0))

prueba("el archivo dice cuando se hizo", bool(doc.get("actualizado")))
prueba("y de donde salio", bool(doc.get("fuente")))

# Lo que no cruza tiene que quedar escrito.
_IDX2 = {"xx": {k: v for k, v in _IDX["xx"].items() if k != "gamma"}}
doc2 = HE.construir({"xx": _PARTIDOS["xx"]}, _IDX2, ligas={"xx": "xx.1"})
prueba("un nombre sin cruzar se registra",
       "Gamma" in doc2["ligas"]["xx.1"]["sin_cruzar"])
prueba("y no aparece entre los equipos",
       len(doc2["ligas"]["xx.1"]["equipos"]) == 10)
prueba("pero sus partidos siguen contados",
       doc2["ligas"]["xx.1"]["partidos"] == 72)


print("")
print("construir() — solo las metricas que la fuente realmente trae")
print("")

mets = set(doc["ligas"]["xx.1"]["parametros"])
prueba("estan las que vinieron", {"corners", "faltas"} <= mets)
prueba("y NO se inventan las que no", "posesion" not in mets)
prueba("las de un equipo son las mismas",
       set(doc["ligas"]["xx.1"]["equipos"]["1"]) <= mets | {"corners", "faltas"})


print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
