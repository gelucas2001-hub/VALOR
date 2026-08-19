#!/usr/bin/env python3
"""Arma el expediente objetivo de un partido, para dárselo a la skill de análisis.

Existe por una razón concreta: la skill tiene que producir una lectura
INDEPENDIENTE de la del modelo. Si ve λ, o la cuota del mercado, y después
dice "gana el local", la regla de alineación de la app termina comparando el
modelo contra sí mismo y el texto de Método pasa a ser falso.

La forma barata de garantizarlo no es pedirle a la skill que ignore campos:
es no dárselos. Este script hace ese recorte, y lo hace en un solo lugar en
vez de a mano cada vez.

Se va con la biblioteca estándar, igual que actualizar.py.

    python expediente.py espn401896916      un partido
    python expediente.py --fecha 2026-08-19 todos los de esa fecha, uno por uno
    python expediente.py --lista            lo de hoy y mañana (ventana de research)
    python expediente.py --lista --todos    la grilla completa, sin recortar
"""

import json
import sys
from datetime import date
from pathlib import Path

# La consola de Windows escribe en cp1252 y se rompe con la λ y con los
# nombres de equipo acentuados. La salida de este script es JSON que va a
# parar a otra herramienta: tiene que ser UTF-8 sí o sí.
for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8")
    except AttributeError:      # flujo redirigido que no lo soporta
        pass

RAIZ = Path(__file__).resolve().parent
PARTIDOS = RAIZ / "data" / "partidos.json"

# La prensa habla fuerte recién 24-48h antes del partido: research hecho una
# semana antes se pisa con la nota que sale la víspera. Por eso --lista
# recorta a esta ventana por omisión — el research se hace el día antes o el
# mismo día, no con toda la grilla de la semana por delante.
VENTANA_DIAS = 1

# Lo que SÍ ve la skill. Todo lo que no esté acá queda afuera por omisión,
# que es la única forma de que agregar un campo nuevo al pipeline no filtre
# sin querer la salida del modelo hacia el análisis.
EXPEDIENTE = [
    "comp", "grupo", "fecha", "hora", "estadio", "ciudad",
    "formH", "formA", "formH_general", "formA_general", "h2h", "tabla",
    "corners", "cornersH", "fouls", "cards",
]

# Lo que queda afuera, y por qué. Está escrito para que se lea, no para que
# el código lo use: si mañana alguien duda de por qué falta un campo, acá está.
EXCLUIDOS = {
    "lh": "λ del local — salida del modelo",
    "la": "λ del visitante — salida del modelo",
    "rho": "corrección Dixon-Coles — salida del modelo",
    "conf": "confianza del modelo en sus propios λ",
    "mercado": "cuotas. No son nuestras, pero la marca de valor es "
               "'nuestra lectura contra el mercado': si el análisis ya vio "
               "la cuota, la comparación no mide nada",
    "note": "explica cómo se calcularon los λ — nombra el modelo",
    "compLogo": "decoración",
    "homeLogo": "decoración",
    "awayLogo": "decoración",
    "preload": "interno del frontend",
}


def cargar():
    with open(PARTIDOS, encoding="utf-8") as f:
        d = json.load(f)
    return d["partidos"] if isinstance(d, dict) and "partidos" in d else d


def expediente(p):
    """El objeto que recibe la skill. Los avisos son para el humano que revisa."""
    e = {
        "espn_id": p["id"],
        "equipo_local": p["home"],
        "homeId": p.get("homeId", ""),
        "equipo_visitante": p["away"],
        "awayId": p.get("awayId", ""),
        "fecha": p.get("date", ""),
    }
    for k in EXPEDIENTE:
        if k in p and k not in e:
            e[k] = p[k]

    # Avisos de calidad del expediente. Sin esto la skill trata cualquier dato
    # como firme, y hay campos que a veces vienen flacos o directamente son un
    # supuesto del pipeline.
    avisos = []
    if len(p.get("h2h", [])) == 0:
        avisos.append("Sin historial entre estos dos: no hables de antecedentes.")
    elif len(p.get("h2h", [])) < 3:
        avisos.append(
            f"Solo {len(p['h2h'])} cruce(s) de historial: es una anécdota, "
            "no una tendencia. No la uses para inclinar.")
    # Encontrado en auditoría (River-Vélez, 2026-08-18): un análisis dijo
    # "los dos últimos cruces en el Monumental" cuando los dos más recientes
    # del h2h se habían jugado en la cancha del visitante, y los que sí fueron
    # en el Monumental eran los dos más viejos. El orden (más reciente primero)
    # y la sede (campo "h") son independientes — hay que leer "h" fila por
    # fila, no asumir que los últimos cruces fueron en esta cancha.
    if len(p.get("h2h", [])) >= 2:
        avisos.append(
            "h2h viene del más reciente al más viejo, pero la sede no sigue "
            "ningún patrón: mirá el campo 'h' en CADA fila antes de decir "
            "dónde se jugó un cruce. 'los últimos cruces fueron en esta "
            "cancha' es una afirmación sobre 'h', no sobre el orden de la lista.")
    # La forma sale de /{slug}/teams/{id}/schedule: el slug de la competición
    # va en la ruta, así que SOLO trae partidos de esta competencia. Un equipo
    # que juega liga y copa tiene dos formas distintas en el mismo archivo —
    # verificado con Boca, que aparece con 5 partidos de Liga en un partido y
    # 3 de Sudamericana en otro, sin un solo cruce en común.
    avisos.append(
        f"formH/formA son SOLO partidos de {p.get('comp','esta competencia')}. "
        "No son los últimos partidos del equipo: los de otros torneos, en el "
        "mismo período, no están. No escribas 'los últimos cinco partidos' — "
        "escribí 'los últimos cinco de este torneo'. Para eso está "
        "formH_general/formA_general: los últimos 5 del equipo sin importar "
        "torneo, con fecha real — usalo cuando formH/formA esté vieja o "
        "cuando quieras hablar del momento actual del equipo en general.")

    # En copas de baja frecuencia (grupos, ida y vuelta) el partido más
    # viejo de formH/formA puede tener meses — visto con River en
    # Sudamericana: los 5 partidos de su forma iban del 16/04 al 28/05,
    # tres meses antes del partido que se estaba analizando. Con fecha ya
    # en la forma, esto se puede medir en vez de suponer.
    hoy = date.today()
    for lado, quien in (("formH", "el local"), ("formA", "el visitante")):
        fechas = [f.get("d", "") for f in p.get(lado, [])]
        if not fechas or not fechas[-1]:
            continue
        try:
            dd, mm, aa = fechas[-1].split("/")
            viejo = date(2000 + int(aa), int(mm), int(dd))
        except (ValueError, IndexError):
            continue
        dias = (hoy - viejo).days
        if dias > 45:
            avisos.append(
                f"La forma d{'el' if quien=='el local' else 'el'} {quien[3:]} "
                f"({lado}) abarca {dias} días — el partido más viejo es del "
                f"{fechas[-1]}. Es vieja para hablar de 'cómo llega' hoy: "
                f"apoyate en {lado}_general en vez de esta.")

    from collections import Counter
    for lado, quien in (("formH", "el local"), ("formA", "el visitante")):
        reps = [r for r, c in Counter(f["rival"] for f in p.get(lado, [])).items()
                if c > 1]
        if reps:
            avisos.append(
                f"En la forma d{'el' if quien=='el local' else 'el'} "
                f"{quien[3:]} se repite {', '.join(reps)}: es una fase de "
                "grupos, ida y vuelta contra los mismos rivales. Eso describe "
                "el fixture, no un momento del equipo.")

    if len(p.get("formH", [])) < 5 or len(p.get("formA", [])) < 5:
        avisos.append(
            f"Forma corta: {len(p.get('formH', []))} partidos del local y "
            f"{len(p.get('formA', []))} del visitante.")
    if not p.get("tabla"):
        avisos.append("Sin tabla: no hay contexto de campaña ni de posiciones.")
    else:
        # `tabla` es la del LOCAL. Medido sobre los 34 partidos: en 27 de 31
        # con tabla, el visitante no figura — juega en otro grupo (copas) o en
        # la otra zona (Liga Profesional). Comparar posiciones sin chequear
        # esto produce un análisis que inventa en la mayoría de los partidos.
        ids = {f.get("id") for f in p["tabla"]}
        fuera = [n for n, i in ((p["home"], p.get("homeId")),
                                (p["away"], p.get("awayId"))) if i not in ids]
        if fuera:
            avisos.append(
                f"La tabla es la del grupo/zona del local, y {' y '.join(fuera)} "
                "no está en ella: juega en otro grupo o zona. No compares "
                "posiciones ni puntos entre los dos equipos.")
    # cornersH = corners * 0.56 es el respaldo por liga de actualizar.py, no un
    # dato medido. Un análisis que lo interprete estaría leyendo una constante.
    if p.get("corners") and abs(p.get("cornersH", 0) - round(p["corners"] * 0.56, 1)) < 1e-9:
        avisos.append(
            "Córners/faltas/tarjetas son el promedio de la liga, no de estos "
            "equipos: ESPN no trajo estadística propia. No los interpretes.")
    if avisos:
        e["_avisos"] = avisos

    e["_leeme"] = (
        "corners/fouls/cards son totales del PARTIDO (los dos equipos sumados); "
        "cornersH es la parte del local. cards suma amarillas y rojas. "
        "En formH/formA, 'local' dice si ese partido lo jugó de local. "
        "formH_general/formA_general son los últimos 5 del equipo cruzando TODAS "
        "las competencias que seguimos, ordenados por fecha real — a diferencia de "
        "formH/formA, que son solo de esta competencia. Usá la de competencia como "
        "base (pesa más, porque el equipo encara distinto un torneo que otro) y la "
        "general para contrastar o cuando la de competencia esté vieja. "
        "En h2h, 'h' es quien fue local y 's' el marcador. "
        "tabla es la del grupo o zona del LOCAL — el visitante puede no estar ahí — "
        "y no trae goles en contra, solo 'gf'."
    )
    return e


def main():
    args = sys.argv[1:]
    ps = cargar()

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    if args[0] == "--lista":
        recorte = "--todos" not in args
        if recorte:
            hoy = date.today()
            def en_ventana(p):
                try:
                    d = date.fromisoformat(p.get("date", ""))
                except ValueError:
                    return False
                return 0 <= (d - hoy).days <= VENTANA_DIAS
            vista = [p for p in ps if en_ventana(p)]
        else:
            vista = ps
        for p in vista:
            print(f"{p['id']}  {p.get('date','')}  {p['comp'][:22]:22}  "
                  f"{p['home']} vs {p['away']}")
        if recorte:
            print(f"\n{len(vista)} de {len(ps)} — ventana de hoy a +{VENTANA_DIAS} día(s). "
                  "--todos para ver la grilla completa.")
        print(f"\n{len(ps)} partidos en total. Los campos que NO se entregan:")
        for k, v in EXCLUIDOS.items():
            print(f"  {k:10} {v}")
        return 0

    if args[0] == "--fecha":
        if len(args) < 2:
            print("Falta la fecha (AAAA-MM-DD).", file=sys.stderr)
            return 1
        sel = [p for p in ps if p.get("date") == args[1]]
    else:
        sel = [p for p in ps if p["id"] == args[0]]

    if not sel:
        print(f"No encontré nada para {args[-1]}. Probá --lista.", file=sys.stderr)
        return 1

    # Uno por partido: la skill se llama una vez por partido, no por fecha.
    salida = [expediente(p) for p in sel]
    print(json.dumps(salida[0] if len(salida) == 1 else salida,
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
