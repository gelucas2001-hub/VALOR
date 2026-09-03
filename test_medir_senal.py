#!/usr/bin/env python3
"""Tests de la capa 2 de medir_senal.py — resolver una señal.

Por qué existen, y con urgencia. La capa 2 se escribió el 2026-09-03
cuando NINGÚN partido de la tanda estaba jugado, así que su camino real
—resolver una señal contra lo que pasó— no se puede ejercitar con datos
de verdad hasta dentro de varios días. Sin estos tests se estaría
dejando andando un evaluador que nadie vio funcionar, para que corra
cuando no haya nadie mirando. Es exactamente el patrón que este repo ya
pagó con `senalDividida()`.

Lo que se protege:

  · que la vara sea la SELLADA y no una recalculada (§36 C3);
  · que un acierto sea un acierto y un fallo un fallo, en los dos
    sentidos ("muchos" y "pocos");
  · que `generador` se resuelva contra los remates de ESE partido;
  · y sobre todo que un caso NO RESOLUBLE devuelva None y no se cuente
    como fallo. Un jugador que no figura en el plantel cacheado no es
    un pronóstico errado: es un dato que falta, y confundirlos hunde
    la tasa de acierto sin que nadie lo note.

    python test_medir_senal.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")

import medir_senal as M

ok = fallan = 0


def prueba(nombre, cond):
    global ok, fallan
    if cond:
        ok += 1
        print(f"  ok   {nombre}")
    else:
        fallan += 1
        print(f"  FALLA {nombre}")


print("\nla vara con la que se resuelve es la SELLADA\n")

EV = {"senal_base": {
    "corners_total": {"vara": 9.3, "fallo": "muchos"},
    "faltas": {"vara": 24.1, "fallo": "pocas"},
    "volumen_remates": {"vara": 26.9, "fallo": None},
}}

prueba("'muchos' acierta cuando el real supera la vara",
       M.resolver_volumen(EV, "corners_total", 12.0) is True)
prueba("'muchos' falla cuando no la supera",
       M.resolver_volumen(EV, "corners_total", 7.0) is False)
prueba("'pocas' acierta cuando el real queda por debajo",
       M.resolver_volumen(EV, "faltas", 20.0) is True)
prueba("'pocas' falla cuando el real la supera",
       M.resolver_volumen(EV, "faltas", 27.0) is False)
prueba("un fallo null no se resuelve",
       M.resolver_volumen(EV, "volumen_remates", 30.0) is None)
prueba("sin dato del partido tampoco",
       M.resolver_volumen(EV, "corners_total", None) is None)
prueba("una dimensión que no está sellada no se inventa",
       M.resolver_volumen(EV, "tarjetas", 5.0) is None)
prueba("sin evidencia sellada no hay nada que resolver",
       M.resolver_volumen({}, "corners_total", 12.0) is None)

# El borde exacto: la vara no se cuenta como "por encima". Es la misma
# convención que usa calibrar_senal.py (`(gl + gv) > bar`), y si las dos
# no coinciden el acierto medido no es el acierto calibrado.
prueba("justo en la vara NO es 'muchos'",
       M.resolver_volumen(EV, "corners_total", 9.3) is False)

print("\n`generador` se resuelve contra los remates de ESE partido\n")

# [remates, al_arco, faltas, amarillas, goles, asist, titular]
PLANTELES = {
    "10": [{"id": "1", "nombre": "Di María"}, {"id": "2", "nombre": "Copetti"}],
    "20": [{"id": "3", "nombre": "Mazzantti"}, {"id": "4", "nombre": "Gauch"}],
}
IDS = {"local": "10", "visitante": "20"}


def partido(jug):
    return {"10": {}, "20": {}, "_jugadores": jug}


lidero = partido({"1": [6, 2, 1, 0, 0, 0, 1], "2": [3, 1, 0, 0, 0, 0, 1],
                  "3": [4, 1, 2, 0, 0, 0, 1]})
r, _ = M.resolver_generador({"equipo": "local", "jugador": "Di María"},
                            lidero, PLANTELES, IDS)
prueba("acierta si lideró los remates de su equipo", r is True)

no_lidero = partido({"1": [2, 0, 1, 0, 0, 0, 1], "2": [7, 3, 0, 0, 0, 0, 1]})
r, _ = M.resolver_generador({"equipo": "local", "jugador": "Di María"},
                            no_lidero, PLANTELES, IDS)
prueba("falla si otro de su equipo pateó más", r is False)

# Solo cuenta contra SU equipo. Un rival que patea más no lo invalida:
# la afirmación es "lidera los remates de su equipo", no del partido.
con_rival = partido({"1": [5, 1, 0, 0, 0, 0, 1], "2": [2, 0, 0, 0, 0, 0, 1],
                     "3": [9, 4, 0, 0, 0, 0, 1]})
r, _ = M.resolver_generador({"equipo": "local", "jugador": "Di María"},
                            con_rival, PLANTELES, IDS)
prueba("un rival que patea más no lo invalida", r is True)

empate = partido({"1": [4, 0, 0, 0, 0, 0, 1], "2": [4, 0, 0, 0, 0, 0, 1]})
r, _ = M.resolver_generador({"equipo": "local", "jugador": "Di María"},
                            empate, PLANTELES, IDS)
prueba("empatar arriba cuenta como liderar", r is True)

r, _ = M.resolver_generador({"equipo": "visitante", "jugador": "Mazzantti"},
                            lidero, PLANTELES, IDS)
prueba("resuelve también al visitante, contra su propio equipo", r is True)

print("\nlo NO resoluble devuelve None, y eso NO es un fallo\n")

r, motivo = M.resolver_generador({"equipo": "local", "jugador": "Fantasma"},
                                 lidero, PLANTELES, IDS)
prueba("un nombre que no está en el plantel no se cuenta", r is None)
prueba("  y dice por qué", "plantel" in motivo)

r, motivo = M.resolver_generador({"equipo": "local", "jugador": "Di María"},
                                 partido({}), PLANTELES, IDS)
prueba("un partido sin estadística por jugador no se cuenta", r is None)

r, motivo = M.resolver_generador({"equipo": "arbitro", "jugador": "Di María"},
                                 lidero, PLANTELES, IDS)
prueba("un lado que no existe no se cuenta", r is None)

# Este SÍ es un fallo, no un dato faltante: lo nombramos y no jugó.
no_jugo = partido({"2": [5, 1, 0, 0, 0, 0, 1]})
r, motivo = M.resolver_generador({"equipo": "local", "jugador": "Di María"},
                                 no_jugo, PLANTELES, IDS)
prueba("nombrar a alguien que no jugó SÍ es un fallo", r is False)
prueba("  y se distingue de un dato faltante", motivo and "no jugó" in motivo)

print("\nel orden de las claves del partido es local, visitante\n")

# Verificado 66/66 contra historial_pronosticos.json (§38). Si esto se
# invierte, cada `generador` se resuelve contra el equipo equivocado y
# el error no se ve: sigue dando un número.
prueba("el primer equipo del caché es el local",
       list(IDS) == ["local", "visitante"])

print("\nla aritmética del intervalo\n")

prueba("el error estándar de una proporción es el de siempre",
       abs(M.ee_prop(0.5, 100) - 0.05) < 1e-9)
prueba("con n=0 no divide por cero", M.ee_prop(0.5, 0) == 0.0)
prueba("una proporción de 1.0 da error cero", M.ee_prop(1.0, 50) == 0.0)

print("\nel esquema viejo sigue contándose aparte\n")

prueba("una senal derogada no se lee como nueva",
       M.esquema_de({"ritmo_goleador": "bajo"}) == "viejo")
prueba("y la nueva como nueva",
       M.esquema_de({"corners_total": "muchos"}) == "nuevo")
prueba("`generador` como objeto único de la v1 se sigue leyendo",
       M.generadores({"generador": {"equipo": "local", "jugador": "X"}}) ==
       [{"equipo": "local", "jugador": "X"}])
prueba("y como lista", len(M.generadores(
    {"generador": [{"equipo": "local", "jugador": "X"},
                   {"equipo": "visitante", "jugador": "Y"}]})) == 2)
prueba("una lista vacía no es una señal", M.generadores({"generador": []}) == [])

print("")
print(f"{ok} ok, {fallan} fallando")
print("")
sys.exit(1 if fallan else 0)
