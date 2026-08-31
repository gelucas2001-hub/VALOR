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

# football-data cambia el formato de fecha SIN avisar, y no por archivo
# sino por temporada: E0-1617, F1-1516, F1-1617 y F1-1718 usan ano de
# dos digitos y el resto de cuatro. Encontrado el 2026-08-25 porque los
# totales no cerraban — se perdian 380 partidos de Inglaterra y 1141 de
# Francia, una temporada entera y tres, descartados en silencio por el
# `except ValueError` de la fecha.
#
# Es el modo de falla mas caro que tiene este archivo: no rompe nada, no
# imprime nada, solo mide menos de lo que dice medir.
dos = H.normalizar([fila(fecha="13/08/16")])
prueba("acepta el ano de dos digitos", len(dos) == 1)
prueba("y lo resuelve al siglo correcto",
       dos and dos[0]["fecha"].year == 2016)
cuatro = H.normalizar([fila(fecha="13/08/2016")])
prueba("y sigue aceptando el de cuatro",
       cuatro and cuatro[0]["fecha"].year == 2016)
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
print("el otro formato de football-data: las ligas clasicas")
print("")

# Por que existe esta seccion. El `/new/` de football-data cubre las
# ligas "nuevas" (ARG, BRA, MEX...) en UN archivo con columnas
# Home/Away/HG/AG. Las clasicas de Europa viven en otra carpeta
# (`mmz4281/{temporada}/{codigo}.csv`), un archivo POR TEMPORADA y con
# otros nombres de columna: HomeTeam/AwayTeam/FTHG/FTAG.
#
# Y traen algo que las nuevas no: las estadisticas de cada partido
# (remates, al arco, corners, faltas, tarjetas). Medido el 2026-08-25:
# ARG.csv y BRA.csv no tienen ninguna de esas columnas; E0 y F1 las
# tienen todas, en 11 temporadas. Esa diferencia es la razon por la que
# en Inglaterra podemos distinguir equipos y en Argentina no.

f_clasica = {"Date": "16/08/2024", "HomeTeam": "Man United",
             "AwayTeam": "Fulham", "FTHG": "1", "FTAG": "0",
             "PSCH": "1.85", "PSCD": "3.60", "PSCA": "4.40",
             "HS": "12", "AS": "9", "HST": "5", "AST": "3",
             "HC": "6", "AC": "4", "HF": "11", "AF": "13",
             "HY": "2", "AY": "3"}

c = H.normalizar([f_clasica])
prueba("lee el formato clasico (HomeTeam/FTHG)", len(c) == 1)
prueba("y saca bien los equipos",
       c and c[0]["home"] == "Man United" and c[0]["away"] == "Fulham")
prueba("y los goles", c and (c[0]["gh"], c[0]["ga"]) == (1, 0))
prueba("y la cuota de cierre de Pinnacle",
       c and c[0]["cuotas"] == [1.85, 3.60, 4.40])

# Las estadisticas por partido. Son el insumo del mercado de
# estadisticas, asi que tienen que llegar hasta el otro lado.
prueba("trae las estadisticas del partido", c and c[0].get("est"))
e = (c[0].get("est") or {}) if c else {}
prueba("remates de los dos lados",
       e.get("remates") == {"h": 12.0, "a": 9.0})
prueba("al arco", e.get("al_arco") == {"h": 5.0, "a": 3.0})
prueba("corners", e.get("corners") == {"h": 6.0, "a": 4.0})
prueba("faltas", e.get("faltas") == {"h": 11.0, "a": 13.0})
prueba("tarjetas", e.get("tarjetas") == {"h": 2.0, "a": 3.0})

# Y el formato viejo NO tiene que romperse ni inventar estadisticas.
v = H.normalizar([fila()])
prueba("el formato /new/ sigue funcionando", len(v) == 1)
prueba("y no inventa estadisticas donde no las hay", not v[0].get("est"))

# Una fila clasica sin estadisticas (pasa en temporadas viejas) tiene
# que dar el partido igual: se pierde la estadistica, no el partido.
sin_est = H.normalizar([{"Date": "01/01/2016", "HomeTeam": "A",
                         "AwayTeam": "B", "FTHG": "0", "FTAG": "0"}])
prueba("una fila clasica sin estadisticas conserva el partido",
       len(sin_est) == 1)
prueba("y declara que no las tiene", not sin_est[0].get("est"))


print("")
print("LIGAS — las dos que se agregaron el 2026-08-25")
print("")

prueba("esta Inglaterra", "eng" in H.LIGAS)
prueba("esta Francia", "fra" in H.LIGAS)
prueba("y siguen las de antes", "arg" in H.LIGAS and "bra" in H.LIGAS)
prueba("las clasicas declaran su formato",
       H.LIGAS.get("eng", {}).get("formato") == "temporadas")
prueba("las nuevas siguen sin declararlo, o lo declaran unico",
       H.LIGAS.get("arg", {}).get("formato", "unico") == "unico")
prueba("Inglaterra apunta al codigo correcto",
       H.LIGAS.get("eng", {}).get("archivo") == "E0")
prueba("Francia tambien", H.LIGAS.get("fra", {}).get("archivo") == "F1")


print("")
print("temporadas_de() — que temporadas pedir de una liga clasica")
print("")

t = H.temporadas_de(3, hasta=2026)
prueba("devuelve tantas como se piden", len(t) == 3)
prueba("con el formato de football-data (aaaa)", all(len(x) == 4 for x in t))
prueba("la mas nueva primero o ultima, pero ordenadas",
       list(t) == sorted(t))
prueba("2526 esta entre ellas", "2526" in t)
prueba("y no pide temporadas del futuro", "2627" not in t)


print("")
print("cuotas_ou() — el mercado de goles, que estaba sin parsear")
print("")

# El formato clásico (E0, F1) trae over/under 2.5 con cierre de
# Pinnacle; el formato "new" (ARG, BRA) no trae ninguno. Eso no es un
# error del parser: la fuente no los publica para esas ligas.
_FILA_ENG = {"PC>2.5": "1.95", "PC<2.5": "1.90",
             "AvgC>2.5": "1.90", "AvgC<2.5": "1.88",
             "B365C>2.5": "1.91", "B365C<2.5": "1.89"}

c, fte = H.cuotas_ou(_FILA_ENG)
prueba("saca el par over/under del cierre", c == [1.95, 1.90])
prueba("y prefiere Pinnacle, igual que en el 1X2", fte == "pinnacle")

c2, fte2 = H.cuotas_ou({"AvgC>2.5": "1.90", "AvgC<2.5": "1.88"})
prueba("si no hay Pinnacle cae al promedio del mercado", c2 == [1.90, 1.88])
prueba("y lo declara", fte2 == "promedio")

prueba("sin ninguna fuente devuelve None, no inventa",
       H.cuotas_ou({"Home": "x"}) == (None, None))
prueba("una cuota rota (<= 1.00) descarta la fuente, no el partido",
       H.cuotas_ou({"PC>2.5": "1.00", "PC<2.5": "1.90",
                    "AvgC>2.5": "1.90", "AvgC<2.5": "1.88"})[0] == [1.90, 1.88])

# El desenlace del mercado de goles, en el mismo orden que las cuotas.
prueba("desenlace_ou: 4-1 son 5 goles, gana el over",
       H.desenlace_ou({"gh": 4, "ga": 1}) == [1, 0])
prueba("0-0 gana el under", H.desenlace_ou({"gh": 0, "ga": 0}) == [0, 1])
prueba("2-1 son exactamente 3, gana el over (la línea es 2.5)",
       H.desenlace_ou({"gh": 2, "ga": 1}) == [1, 0])
prueba("1-1 son 2, gana el under", H.desenlace_ou({"gh": 1, "ga": 1}) == [0, 1])

print("")
print("cuotas_de() — cada casa por separado, para comparar entre ellas")
print("")

# El metodo de consenso (arXiv 1710.02824) no compara un modelo contra
# el mercado: compara UNA casa contra el promedio de las demas. Para eso
# hacen falta las cuotas separadas por proveedor, no la "mejor" que
# elige cuotas_cierre().
_F = {"AvgCH": "2.10", "AvgCD": "3.40", "AvgCA": "3.50",
      "B365CH": "2.20", "B365CD": "3.30", "B365CA": "3.40",
      "PSCH": "2.15", "PSCD": "3.45", "PSCA": "3.55"}

prueba("saca el consenso del mercado", H.cuotas_de(_F, "promedio") == [2.10, 3.40, 3.50])
prueba("saca Bet365 por separado", H.cuotas_de(_F, "bet365") == [2.20, 3.30, 3.40])
prueba("y Pinnacle", H.cuotas_de(_F, "pinnacle") == [2.15, 3.45, 3.55])
prueba("una casa que no esta devuelve None, no la de al lado",
       H.cuotas_de({"AvgCH": "2.1"}, "bet365") is None)
prueba("una fila incompleta no se completa a medias",
       H.cuotas_de({"B365CH": "2.2", "B365CD": "3.3"}, "bet365") is None)
prueba("una cuota rota descarta la casa entera",
       H.cuotas_de({"B365CH": "1.00", "B365CD": "3.3", "B365CA": "3.4"}, "bet365") is None)

print("")
print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
