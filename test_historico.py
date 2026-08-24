#!/usr/bin/env python3
"""Tests de historico.py

El hallazgo que lo motiva: `medir_vs_mercado.py` ya bajaba el CSV de
football-data.co.uk y después filtraba a la temporada en curso — 289
partidos de los 6310 que el archivo trae, de 2012 a 2026.

Y el CSV es autosuficiente: tiene Home, Away, HG, AG y Date, o sea todo
lo que `fuerzas_equipos()` necesita. No hace falta cruzar nombres con
ESPN, que era lo que ataba la medición a una sola temporada.

    python test_historico.py
"""

import datetime
import sys

sys.stdout.reconfigure(encoding="utf-8")
import historico as H

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


def fila(fecha="15/03/2024", home="Boca", away="River", hg="2", ag="1", **extra):
    base = {"Date": fecha, "Home": home, "Away": away, "HG": hg, "AG": ag,
            "Season": "2024", "League": "Liga Profesional", "Country": "Argentina"}
    base.update(extra)
    return base


print("")
print("cuotas_cierre() — Pinnacle primero, el promedio como respaldo")
print("")

# El CSV trae varias fuentes de cuota de cierre. Pinnacle es la que la
# industria usa de vara para CLV: margen medio 3.18% contra 7.07% del
# promedio del mercado (medido sobre los 6310 partidos de arg.1). Cuando
# está, se usa esa.
con_pin = fila(PSCH="1.80", PSCD="3.50", PSCA="4.20",
               AvgCH="1.75", AvgCD="3.40", AvgCA="4.00")
c, fuente = H.cuotas_cierre(con_pin)
prueba("usa Pinnacle cuando está", c == [1.80, 3.50, 4.20])
prueba("y lo dice", fuente == "pinnacle")

solo_avg = fila(PSCH="", PSCD="", PSCA="",
                AvgCH="1.75", AvgCD="3.40", AvgCA="4.00")
c2, f2 = H.cuotas_cierre(solo_avg)
prueba("cae al promedio si no hay Pinnacle", c2 == [1.75, 3.40, 4.00])
prueba("y también lo dice", f2 == "promedio")

sin_nada = fila(PSCH="", PSCD="", PSCA="", AvgCH="", AvgCD="", AvgCA="")
prueba("sin ninguna cuota devuelve None", H.cuotas_cierre(sin_nada) == (None, None))

# Una cuota de 1.00 o menos no existe: es un dato roto, no un favorito.
rota = fila(PSCH="1.00", PSCD="3.50", PSCA="4.20",
            AvgCH="1.75", AvgCD="3.40", AvgCA="4.00")
c3, f3 = H.cuotas_cierre(rota)
prueba("una cuota imposible descarta esa fuente, no el partido", f3 == "promedio")

texto = fila(PSCH="-", PSCD="3.50", PSCA="4.20", AvgCH="", AvgCD="", AvgCA="")
prueba("un valor no numérico no rompe", H.cuotas_cierre(texto) == (None, None))

print("")
print("normalizar() — al formato que ya entiende fuerzas_equipos()")
print("")

# fuerzas_equipos() pide {fecha, home, away, gh, ga}. Los nombres del CSV
# sirven de id tal cual: para ajustar fuerzas contra la propia historia
# del CSV no hace falta cruzar con ESPN.
ms = H.normalizar([fila(), fila(fecha="20/03/2024", home="River", away="Racing",
                        hg="0", ag="0")])
prueba("devuelve un partido por fila", len(ms) == 2)
p = ms[0]
prueba("la fecha es un date", isinstance(p["fecha"], datetime.date))
prueba("parsea DD/MM/YYYY", p["fecha"] == datetime.date(2024, 3, 15))
prueba("los goles son enteros", p["gh"] == 2 and p["ga"] == 1)
prueba("el nombre del CSV es el id", p["home"] == "Boca" and p["away"] == "River")
prueba("trae la cuota si la hay", "cuotas" in p)

print("")
print("el orden cronológico no es opcional")
print("")

# Todo lo que sigue es walk-forward: ajustar con lo anterior y predecir
# lo siguiente. Si el orden viene mal, se filtra el futuro al pasado y
# la medición miente a nuestro favor sin avisar.
desordenadas = [fila(fecha="20/03/2024"), fila(fecha="01/01/2024"),
                fila(fecha="15/06/2023")]
orden = [m["fecha"] for m in H.normalizar(desordenadas)]
prueba("ordena del más viejo al más nuevo", orden == sorted(orden))

print("")
print("lo que no se puede leer se descarta, no se inventa")
print("")

prueba("una fila sin goles se descarta",
       H.normalizar([fila(hg="", ag="")]) == [])
prueba("una fila sin fecha se descarta",
       H.normalizar([fila(fecha="")]) == [])
prueba("una fecha con otro formato se descarta",
       H.normalizar([fila(fecha="2024-03-15")]) == [])
prueba("una fila sin equipos se descarta",
       H.normalizar([fila(home="", away="")]) == [])
prueba("una lista vacía no rompe", H.normalizar([]) == [])

# Un partido SIN cuota igual sirve: alimenta el ajuste de fuerzas
# aunque no se pueda usar para comparar contra el mercado. Descartarlo
# tiraría historia que no cuesta nada guardar.
sin_cuota = H.normalizar([fila(PSCH="", PSCD="", PSCA="",
                               AvgCH="", AvgCD="", AvgCA="")])
prueba("un partido sin cuota se conserva igual", len(sin_cuota) == 1)
prueba("pero declara que no la tiene", sin_cuota[0]["cuotas"] is None)

print("")
print("con_cuota() — el subconjunto que sirve para medir contra el mercado")
print("")

mezcla = H.normalizar([
    fila(fecha="01/03/2024", PSCH="1.80", PSCD="3.50", PSCA="4.20"),
    fila(fecha="02/03/2024", PSCH="", PSCD="", PSCA="",
         AvgCH="", AvgCD="", AvgCA=""),
])
prueba("filtra a los que tienen cuota", len(H.con_cuota(mezcla)) == 1)
prueba("no toca la lista original", len(mezcla) == 2)
prueba("una lista vacía no rompe", H.con_cuota([]) == [])

print("")
print("resultado real, en el mismo orden que las cuotas")
print("")

prueba("gana el local", H.desenlace({"gh": 2, "ga": 1}) == [1, 0, 0])
prueba("empatan", H.desenlace({"gh": 1, "ga": 1}) == [0, 1, 0])
prueba("gana el visitante", H.desenlace({"gh": 0, "ga": 3}) == [0, 0, 1])

print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
