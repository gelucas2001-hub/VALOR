#!/usr/bin/env python3
"""El expediente del MERCADO DE ESTADÍSTICAS, para la segunda skill.

Un partido son dos mercados distintos y el proyecto los venía mezclando:

  · el mercado del RESULTADO — quién gana, cuántos goles. Lo analiza
    `valor-analisis-inclinacion` con `expediente.py`.
  · el mercado de las ESTADÍSTICAS — córners, remates, al arco, faltas,
    tarjetas, y quién de cada equipo las produce. **Nunca tuvo skill.**

Este script arma el expediente del segundo. Sigue el mismo molde que
`expediente.py` y por la misma razón: la skill tiene que leer el partido
con datos observados, no con la salida de nuestro modelo. Si ve λ, o la
cuota, termina escribiendo con otra voz lo que el modelo ya dijo — que
es exactamente lo que pasó en agosto con la otra skill (TRASPASO
§6nonies) y costó rehacerla.

La forma barata de garantizarlo no es pedirle que ignore campos: es no
dárselos.

Qué SÍ viaja, y por qué cada cosa:

  · lo que cada equipo produce por partido (remates, al arco, córners,
    faltas, tarjetas, posesión, tackles) y **lo que concede su rival**
    en lo mismo. Sin el segundo no se puede decir "a este rival le
    rematan de afuera": solo se puede describir al propio equipo;
  · el split de local y visitante, cuando está;
  · la serie reciente por jugador de las métricas que se cotizan;
  · el árbitro, con el aviso de que su efecto sobre las tarjetas está
    medido y **da cero**;
  · cuánto se le cree a cada métrica, que sale de una medición y no de
    una opinión (`data/calibracion_jugadores.json`).

    python expediente_estadisticas.py espn401841208
    python expediente_estadisticas.py --lista
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

RAIZ = Path(__file__).resolve().parent
PARTIDOS = RAIZ / "data" / "partidos.json"
ESTADISTICAS = RAIZ / "data" / "estadisticas.json"
PLANTELES = RAIZ / "data" / "planteles.json"
CALIBRACION = RAIZ / "data" / "calibracion_jugadores.json"

VENTANA_DIAS = 1

# Cuántos jugadores por equipo viajan. Menos que en el expediente del
# resultado: acá interesan los que efectivamente producen la estadística,
# no el plantel entero.
TOPE_PLANTEL = 18

# Las métricas de equipo que se cotizan en algún lado. `posesion` y
# `tackles` no se cotizan pero entran igual: son las dos únicas que
# superaron el techo de falsa señal en `medir_discriminacion.py`, o sea
# lo único donde de verdad distinguimos un equipo de otro.
METRICAS_EQUIPO = ("remates", "al_arco", "corners", "faltas", "tarjetas",
                   "posesion", "tackles")

# Lo del jugador que se cotiza por separado en Bet365, más las dos de
# disciplina que la app ya muestra.
METRICAS_JUGADOR = ("remates", "al_arco", "faltas", "amarillas",
                    "goles", "asist")

# Lo que SÍ ve la skill del partido. Igual que en `expediente.py`: lo que
# no esté acá queda afuera por omisión, para que agregar un campo al
# pipeline no filtre la salida del modelo sin que nadie se entere.
DEL_PARTIDO = ["comp", "fecha", "hora", "estadio", "ciudad", "arbitro"]

EXCLUIDOS = {
    "lh": "λ del local — salida del modelo",
    "la": "λ del visitante — salida del modelo",
    "rho": "corrección Dixon-Coles — salida del modelo",
    "conf": "confianza del modelo en sus propios λ",
    "corners": "córners esperados POR NOSOTROS — salida del modelo. Los "
               "promedios crudos de cada equipo sí viajan, y son otra cosa",
    "fouls": "faltas esperadas por nosotros — mismo motivo",
    "cards": "tarjetas esperadas por nosotros — mismo motivo",
    "mercado": "cuotas de DraftKings: si la skill ya vio el precio, su "
               "lectura deja de ser independiente de él",
    "mercadoExtra": "cuotas de Bet365, incluidas las de córners y las de "
                    "jugador — mismo motivo, y acá sería peor porque son "
                    "justo las de este mercado",
}


def cargar(ruta, defecto=None):
    if not ruta.exists():
        return defecto
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return defecto


def partidos():
    d = cargar(PARTIDOS, [])
    return (d.get("partidos") if isinstance(d, dict) else d) or []


def metricas_equipo(est):
    """Lo que el equipo produce y lo que le conceden, en un solo objeto.

    `produce` es lo que hace el equipo; `concede` es lo que le hacen a
    él. Los dos hacen falta: sin el segundo, la skill solo puede
    describir a un equipo, y la pregunta del mercado de estadísticas es
    casi siempre sobre el CRUCE.
    """
    if not est:
        return None
    out = {"partidos": est.get("pj")}
    for clave, origen in (("produce", est), ("concede", est.get("concede"))):
        if not origen:
            continue
        datos = {m: origen.get(m) for m in METRICAS_EQUIPO
                 if origen.get(m) is not None}
        if datos:
            out[clave] = datos
    for lado in ("local", "visita"):
        d = est.get(lado) or {}
        datos = {m: d.get(m) for m in METRICAS_EQUIPO if d.get(m) is not None}
        if datos:
            out[lado] = datos
    return out if len(out) > 1 else None


def jugadores_de(plantel, tope=TOPE_PLANTEL):
    """Los que más juegan, con su serie reciente de lo que se cotiza.

    Viaja la SERIE y no solo el promedio: "1, 0, 6" y "2, 2, 3" tienen
    la misma media y no son el mismo jugador, y esa diferencia es
    justamente de lo que puede escribir una skill y no un promedio.
    """
    out = []
    for j in sorted(plantel or [], key=lambda x: -(x.get("pj") or 0))[:tope]:
        serie = j.get("serie") or {}
        fila = {"nombre": j.get("nombre"), "pos": j.get("pos"),
                "pj": j.get("pj"), "partidos_en_serie": serie.get("pj"),
                "titular_en": serie.get("tit")}
        vistos = {m: serie[m] for m in METRICAS_JUGADOR if serie.get(m)}
        if vistos:
            fila["serie"] = vistos
        out.append(fila)
    return out


def fiabilidad(cal):
    """De qué métricas fiarse, medido contra el ruido y no contra cero.

    Va en el expediente a propósito: sin esto la skill escribe con la
    misma seguridad sobre remates —que se desvía 2.09 veces lo que
    explica el azar— que sobre goles, que está bien.
    """
    mets = (cal or {}).get("metricas") or {}
    return {m: {"nivel": v.get("nivel"), "casos": v.get("n")}
            for m, v in mets.items() if v.get("nivel")}


def expediente(p, est=None, planteles=None, cal=None):
    est = cargar(ESTADISTICAS, {}) if est is None else est
    planteles = cargar(PLANTELES, {}) if planteles is None else planteles
    cal = cargar(CALIBRACION, {}) if cal is None else cal
    equipos = (est or {}).get("equipos") or {}
    plant = (planteles or {}).get("equipos") or {}

    e = {
        "espn_id": p.get("id"),
        "mercado": "estadisticas",
        "equipo_local": p.get("home"),
        "equipo_visitante": p.get("away"),
    }
    for k in DEL_PARTIDO:
        if p.get(k):
            e[k] = p[k]

    avisos = []
    for lado, tid, nombre in (("Local", p.get("homeId"), p.get("home")),
                              ("Visitante", p.get("awayId"), p.get("away"))):
        m = metricas_equipo(equipos.get(str(tid)))
        if m:
            e["equipo" + lado] = m
        else:
            avisos.append(f"Sin estadísticas de equipo para {nombre}: no "
                          f"escribas del cruce como si las tuvieras.")
        js = jugadores_de(plant.get(str(tid)))
        if js:
            e["jugadores" + lado] = js
        else:
            avisos.append(f"Sin plantel cargado para {nombre}.")

    f = fiabilidad(cal)
    if f:
        e["fiabilidad_medida"] = f
    if p.get("arbitro"):
        avisos.append("El árbitro viaja como dato, pero su efecto sobre las "
                      "tarjetas está medido con prueba de permutación y da "
                      "CERO. No escribas que un árbitro 'saca muchas'.")
    avisos.append("Las series por jugador son de pocos partidos: mirá "
                  "`partidos_en_serie` antes de afirmar una tendencia.")
    e["avisos"] = avisos
    return e


def main():
    args = sys.argv[1:]
    ps = partidos()
    if "--lista" in args:
        hoy = date.today()
        tope = hoy + timedelta(days=VENTANA_DIAS)
        for p in ps:
            d = (p.get("date") or "")[:10]
            try:
                f = date.fromisoformat(d)
            except ValueError:
                continue
            if hoy <= f <= tope:
                print(f"{p['id']}  {p.get('hora','')}  {p.get('home')} vs "
                      f"{p.get('away')}  ({p.get('comp')})")
        return 0

    if not args:
        print(__doc__)
        return 1

    ident = args[0]
    p = next((x for x in ps if x.get("id") == ident), None)
    if not p:
        print(f"No encontré {ident} en data/partidos.json", file=sys.stderr)
        return 1
    print(json.dumps(expediente(p), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
