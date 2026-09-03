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
PLANTELES = RAIZ / "data" / "planteles.json"
ESTADISTICAS = RAIZ / "data" / "estadisticas.json"

# Las métricas MEDIDAS que viajan por equipo. Son la evidencia admisible
# de `desarrollo.senal`: la regla es que para afirmar una dimensión hace
# falta una medición de esa misma métrica, y hasta el 2026-09-03 este
# expediente no traía ninguna — solo el esperado del modelo, que es un
# pronóstico de la métrica, no una medición de ella.
METRICAS_SENAL = ("remates", "al_arco", "corners", "faltas", "tarjetas")

# ── El umbral de las cuatro dimensiones de volumen de `senal` ────────
#
# Calibrado el 2026-09-03 por `calibrar_senal.py` sobre 20.897 partidos
# de seis ligas europeas (2015/16 a 2025/26), walk-forward y con
# train/test temporal. NO se eligió mirando la primera tanda: esos
# partidos son de septiembre de 2026 y no entran en el corpus. La
# condición la puso Lucas y es la que hace que el umbral signifique
# algo — un umbral elegido sobre la muestra que después se evalúa no
# es un umbral, es una descripción.
#
#   (gap mínimo, dispersión máxima, partidos mínimos)  → acierto en test
#
#   faltas    10% · 15% · 6   71.2% contra una tasa base de 54.1%  (10.9 ee)
#   remates   10% · 15% · 6   63.6% contra 51.2%                   ( 6.2 ee)
#   corners   20% · 20% · 6   65.7% contra 52.0%                   ( 3.0 ee)
#   tarjetas  —                     no supera su tasa base en NINGÚN
#                                   umbral de la grilla: máximo 1.8 ee
#
# Por eso `tarjetas` no se afirma nunca. No es que sea difícil: es que
# el recuento de tarjetas por partido varía tanto contra lo que separa
# a un equipo de otro que el promedio previo no dice de qué lado va a
# caer. Coincide con `medir_arbitros.py`, que tampoco encuentra señal
# usable del lado del árbitro.
UMBRAL_SENAL = {
    "faltas":   {"gap": 0.10, "spread": 0.15, "n": 6},
    "remates":  {"gap": 0.10, "spread": 0.15, "n": 6},
    "corners":  {"gap": 0.20, "spread": 0.20, "n": 6},
    "tarjetas": None,
}

# Qué campo de `senal` afirma cada métrica, y con qué palabras.
CAMPO_SENAL = {
    "corners": ("corners_total", "muchos", "pocos"),
    "faltas":  ("faltas", "muchas", "pocas"),
    "tarjetas": ("tarjetas", "muchas", "pocas"),
    "remates": ("volumen_remates", "alto", "bajo"),
}

# Cuántos jugadores por equipo viajan al análisis. Un roster completo son
# 38-40, de los cuales un tercio no jugó nunca. Los 25 que más jugaron
# cubren a cualquiera que pueda ser noticia; el resto es ruido que compite
# por la atención del que lee.
TOPE_PLANTEL = 25

# Los únicos campos del plantel que sirven para pesar una baja. Remates,
# faltas y tarjetas están en planteles.json y son útiles en la app, pero
# acá no cambian ninguna conclusión.
CAMPOS_JUGADOR = ("nombre", "pos", "pj", "goles", "asist", "peso_goles")

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
]

# Lo que queda afuera, y por qué. Está escrito para que se lea, no para que
# el código lo use: si mañana alguien duda de por qué falta un campo, acá está.
EXCLUIDOS = {
    "lh": "λ del local — salida del modelo",
    "la": "λ del visitante — salida del modelo",
    "rho": "corrección Dixon-Coles — salida del modelo",
    "conf": "confianza del modelo en sus propios λ",
    # Salieron el 2026-09-03, con el esquema nuevo de `senal`. Son la
    # expectativa DEL MODELO para esas mismas métricas (`esperados()` en
    # actualizar.py), o una constante de liga cuando ESPN no trajo
    # estadística propia. La regla de evidencia admisible pide una
    # medición de la métrica que se afirma; esto es un pronóstico de la
    # métrica que se afirma, que es otra cosa y es justo el baseline
    # contra el que `medir_senal.py` mide el aporte. Dejarlos adentro
    # convertía la capa 3 en una comparación del modelo contra sí mismo.
    # `expediente_estadisticas.py` ya los excluía por este motivo; los
    # dos expedientes decían cosas distintas sobre el mismo dato.
    "corners": "córners esperados POR NOSOTROS — salida del modelo. Los "
               "promedios crudos de cada equipo sí viajan, en `metricas`",
    "cornersH": "la parte del local de ese esperado — mismo motivo",
    "fouls": "faltas esperadas por nosotros — mismo motivo",
    "cards": "tarjetas esperadas por nosotros — mismo motivo",
    "mercado": "cuotas de DraftKings. No son nuestras, pero la marca de "
               "valor es 'nuestra lectura contra el mercado': si el "
               "análisis ya vio la cuota, la comparación no mide nada",
    "mercadoExtra": "cuotas de Bet365 (goles extra, ambos marcan, "
                     "córners, jugador) — mismo motivo que 'mercado'",
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


def cargar_estadisticas():
    """{team_id: {métricas}}. Si el cron todavía no lo escribió, vacío."""
    try:
        with open(ESTADISTICAS, encoding="utf-8") as f:
            return json.load(f).get("equipos", {})
    except (FileNotFoundError, ValueError):
        return {}


def metricas_medidas(est):
    """Lo que el equipo produce y lo que le conceden, los dos medidos.

    `concede` hace tanta falta como `produce`: los córners de un partido
    los generan los dos equipos, y un rival que defiende con bloque bajo
    los produce sin tener la pelota. Viaja `n` porque con tres partidos
    un promedio es una racha (principio E), y `desvio` porque un equipo
    de 4.0 ± 0.5 y uno de 4.0 ± 3.0 no permiten la misma afirmación.
    """
    if not est:
        return None
    out = {"partidos": est.get("pj")}
    for clave, origen in (("produce", est), ("concede", est.get("concede"))):
        if not origen:
            continue
        d = {m: origen.get(m) for m in METRICAS_SENAL
             if origen.get(m) is not None}
        if d:
            out[clave] = d
    for lado in ("local", "visita"):
        o = est.get(lado) or {}
        d = {m: o.get(m) for m in METRICAS_SENAL if o.get(m) is not None}
        if d:
            out[lado] = d
    for extra in ("n", "desvio"):
        o = est.get(extra) or {}
        d = {m: o.get(m) for m in METRICAS_SENAL if o.get(m) is not None}
        if d:
            out[extra] = d
    return out if len(out) > 1 else None


# `generador` se decide por PROMEDIO POR PARTIDO, no por la suma. Con
# `pj` desparejo las dos lecturas dan cosas distintas y en la primera
# tanda ya pasó: Colidio tenía 14 remates en 3 partidos y su segundo 9
# en 4 — por suma es +56%, por partido es +107%. La suma le da ventaja
# a quien jugó más, que es lo contrario de lo que la señal quiere decir.
MIN_APARICIONES_GENERADOR = 3


def liderazgo_remates(plantel):
    """Quién patea más por partido en su equipo, y por cuánto.

    Devuelve el candidato y su ventaja sobre el segundo, sin decidir: el
    umbral vive en la skill. Pide un mínimo de apariciones porque una
    tasa sacada de un partido no es una tasa.
    """
    filas = []
    for j in plantel or []:
        s = j.get("serie") or {}
        r = s.get("remates") or []
        if len(r) < MIN_APARICIONES_GENERADOR:
            continue
        filas.append({"nombre": j.get("nombre"), "pos": j.get("pos"),
                      "por_partido": round(sum(r) / len(r), 2),
                      "apariciones": len(r), "titular": s.get("tit", 0)})
    filas.sort(key=lambda f: -f["por_partido"])
    if len(filas) < 2 or filas[1]["por_partido"] <= 0:
        return None
    lider, segundo = filas[0], filas[1]
    return {
        "lider": lider, "segundo": segundo,
        "ventaja": round(lider["por_partido"] / segundo["por_partido"] - 1, 3),
    }


def vara_liga(estadisticas, ids_liga):
    """La media de la liga para el TOTAL del partido, por métrica.

    Es la vara contra la que `medir_senal.py` resuelve la afirmación, así
    que tiene que salir del mismo lado: el promedio por equipo de la
    competición, por dos.
    """
    out = {}
    for m in METRICAS_SENAL:
        vs = [estadisticas[i][m] for i in ids_liga
              if i in estadisticas and estadisticas[i].get(m) is not None]
        if vs:
            out[m] = round(sum(vs) / len(vs) * 2, 2)
    return out


def veredicto_senal(mh, ma, vara):
    """Los tres estimadores del total, el gap contra la vara, y el fallo.

    Existe porque en la primera tanda (§34) la skill hacía esta cuenta a
    ojo y salió inconsistente consigo misma: declaró `null` una señal a
    +16% de la vara y afirmó otra a +11%. La aritmética no es trabajo de
    criterio, así que la hace el expediente y la skill recibe el fallo.

    Los tres estimadores son distintas formas de mirar el mismo total, y
    cuando se contradicen entre sí eso ES la información: significa que
    el promedio general, el de sede y lo que concede el rival no cuentan
    la misma historia, y ahí la respuesta correcta es callarse.
    """
    out = {}
    for m in METRICAS_SENAL:
        campo = CAMPO_SENAL.get(m)
        if not campo or m not in vara or not vara[m]:
            continue
        nombre, arriba, abajo = campo
        um = UMBRAL_SENAL.get(m)
        ph, pa = (mh.get("produce") or {}).get(m), (ma.get("produce") or {}).get(m)
        ch, ca = (mh.get("concede") or {}).get(m), (ma.get("concede") or {}).get(m)
        if None in (ph, pa, ch, ca):
            continue
        sh = (mh.get("local") or {}).get(m, ph)
        sa = (ma.get("visita") or {}).get(m, pa)
        e1 = ph + pa
        e2 = sh + sa
        e3 = (sh + ca) / 2 + (sa + ch) / 2
        est = (e1 + e2 + e3) / 3
        v = vara[m]
        n = min((mh.get("n") or {}).get(m, 0), (ma.get("n") or {}).get(m, 0))
        gap = est / v - 1
        spread = (max(e1, e2, e3) - min(e1, e2, e3)) / v
        fila = {
            "estimadores": {"produce": round(e1, 1), "sede": round(e2, 1),
                            "cruzado": round(e3, 1)},
            "estimado": round(est, 1), "vara": v,
            "gap": round(gap, 3), "dispersion": round(spread, 3), "n": n,
        }
        if um is None:
            fila["fallo"] = None
            fila["por_que"] = ("esta dimensión no se afirma nunca: no supera "
                               "su tasa base en ningún umbral medido")
        elif n < um["n"]:
            fila["fallo"] = None
            fila["por_que"] = f"muestra corta ({n} < {um['n']} partidos)"
        elif spread > um["spread"]:
            fila["fallo"] = None
            fila["por_que"] = (f"los tres estimadores se contradicen "
                               f"({spread:.0%} > {um['spread']:.0%})")
        elif abs(gap) < um["gap"]:
            fila["fallo"] = None
            fila["por_que"] = (f"demasiado cerca de la media de la liga "
                               f"({gap:+.0%}, hace falta {um['gap']:.0%})")
        else:
            fila["fallo"] = arriba if gap > 0 else abajo
            fila["por_que"] = f"{gap:+.0%} contra la media de la liga"
        out[nombre] = fila
    return out


def cargar_planteles():
    """{team_id: [jugadores]}. Si el cron todavía no lo escribió, vacío."""
    try:
        with open(PLANTELES, encoding="utf-8") as f:
            return json.load(f).get("equipos", {})
    except (FileNotFoundError, ValueError):
        return {}


# Lo que se pasa de la serie reciente. `esp` queda afuera a proposito:
# es la media encogida que usa el modelo de lineas, y el expediente
# existe justamente para que el analisis no vea numeros del modelo.
CAMPOS_SERIE = ("remates", "al_arco", "faltas", "amarillas", "goles",
                "asist", "pj", "tit")


def recortar_plantel(plantel):
    """Los que más jugaron, con los campos que pesan una baja y nada más.

    Además del acumulado va la serie de los últimos partidos, porque el
    acumulado solo no distingue al que viene jugando del que se lesionó
    hace dos meses: los dos siguen figurando con los mismos PJ y goles
    de temporada. Pasó — el plantel decía pj=5 goles=3 de un jugador que
    no había debutado en el torneo, y el análisis escribió que estaba
    jugando y convirtiendo. Quien no jugó no tiene serie, y eso se ve.
    """
    js = sorted(plantel or [], key=lambda j: -j.get("pj", 0))[:TOPE_PLANTEL]
    out = []
    for j in js:
        fila = {k: j.get(k) for k in CAMPOS_JUGADOR}
        s = j.get("serie")
        if s:
            fila["serie"] = {k: s[k] for k in CAMPOS_SERIE if k in s}
        out.append(fila)
    return out


def expediente(p, planteles=None, estadisticas=None, grilla=None):
    """El objeto que recibe la skill. Los avisos son para el humano que revisa."""
    planteles = cargar_planteles() if planteles is None else planteles
    estadisticas = cargar_estadisticas() if estadisticas is None else estadisticas
    # La vara de `senal` es la media de la competición, así que hace falta
    # saber qué equipos la juegan. Un parámetro y no una lectura global:
    # los tests le pasan una grilla chica.
    try:
        _todos = cargar() if grilla is None else grilla
    except (FileNotFoundError, ValueError, KeyError):
        _todos = []
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

    # El plantel de cada equipo, con partidos jugados y peso goleador. Es lo
    # que separa "no está Driussi" de "no está Arambarri": sin estos números
    # el análisis solo puede enumerar nombres, que es exactamente lo que
    # pasaba antes de que esto viajara.
    faltan_plantel = []
    faltan_metricas = []
    for lado, tid, nombre in (("H", p.get("homeId"), p["home"]),
                              ("A", p.get("awayId"), p["away"])):
        m = metricas_medidas(estadisticas.get(str(tid)))
        if m:
            e["metricas" + lado] = m
        else:
            faltan_metricas.append(nombre)
        ld = liderazgo_remates(planteles.get(str(tid)))
        if ld:
            e["liderazgo" + lado] = ld
        js = recortar_plantel(planteles.get(str(tid)))
        if js:
            e["plantel" + lado] = js
            # "Jugó 5" no dice nada sin saber sobre cuántos, y ningún dato de
            # la fuente trae los partidos del equipo. El máximo del plantel es
            # la mejor escala disponible — y se entrega diciendo que es eso.
            e["pjMax" + lado] = max(j["pj"] for j in js)
        else:
            faltan_plantel.append(nombre)

    # El fallo de cada dimensión de volumen, ya calculado. La skill no
    # hace aritmética: recibe "muchas / pocas / null" y el motivo.
    mh, ma = e.get("metricasH"), e.get("metricasA")
    if mh and ma:
        ids = {str(q.get("homeId")) for q in _todos if q.get("liga") == p.get("liga")}
        ids |= {str(q.get("awayId")) for q in _todos if q.get("liga") == p.get("liga")}
        vara = vara_liga(estadisticas, ids)
        if vara:
            e["senal_base"] = veredicto_senal(mh, ma, vara)

    # Avisos de calidad del expediente. Sin esto la skill trata cualquier dato
    # como firme, y hay campos que a veces vienen flacos o directamente son un
    # supuesto del pipeline.
    avisos = []
    if faltan_plantel:
        avisos.append(
            f"Sin plantel de {' ni de '.join(faltan_plantel)}: para ese equipo "
            "no podés pesar una baja con números propios. Si nombrás una "
            "ausencia suya, decí de dónde sale el peso o no le atribuyas peso.")
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
    # El aviso del respaldo por liga (corners * 0.56) se fue con los campos
    # que lo motivaban: desde el 2026-09-03 el esperado del modelo no viaja.
    # Lo que sí hace falta avisar es cuándo NO hay medición propia, porque
    # sin ella las cuatro dimensiones de volumen de `senal` van a `null` por
    # falta de evidencia admisible — y eso hay que poder distinguirlo de un
    # `null` por criterio.
    if faltan_metricas:
        avisos.append(
            f"Sin estadística medida de {' ni de '.join(faltan_metricas)}: "
            "no tenés evidencia admisible para corners_total, faltas, "
            "tarjetas ni volumen_remates. Esas cuatro van en null — no las "
            "deduzcas de goles, de la tabla ni de quién es mejor.")
    else:
        pocos = sorted({
            m
            for lado in ("H", "A")
            for m, k in ((mm, (e.get("metricas" + lado) or {}).get("n", {}).get(mm))
                         for mm in METRICAS_SENAL)
            if isinstance(k, int) and k < 4
        })
        if pocos:
            avisos.append(
                f"Menos de 4 partidos medidos en: {', '.join(pocos)}. Con esa "
                "muestra un promedio es una racha, no una tendencia "
                "(principio E): null es la respuesta correcta salvo que la "
                "diferencia sea enorme.")
    if avisos:
        e["_avisos"] = avisos

    e["_leeme"] = (
        "metricasH/metricasA son lo MEDIDO por equipo, por partido: `produce` "
        "es lo que hace el equipo y `concede` lo que le hacen a él — los dos "
        "hacen falta, porque los córners de un partido los generan los dos "
        "lados. `local`/`visita` es el split por sede, `n` cuántos partidos "
        "hay detrás de cada número y `desvio` cuánto varía. Son la ÚNICA "
        "evidencia admisible para las cuatro dimensiones de volumen de "
        "`desarrollo.senal`. El esperado de córners/faltas/tarjetas que este "
        "expediente traía hasta el 2026-09-03 ya no viaja: era salida del "
        "modelo, no una medición. "
        "En formH/formA, 'local' dice si ese partido lo jugó de local. "
        "formH_general/formA_general son los últimos 5 del equipo cruzando TODAS "
        "las competencias que seguimos, ordenados por fecha real — a diferencia de "
        "formH/formA, que son solo de esta competencia. Usá la de competencia como "
        "base (pesa más, porque el equipo encara distinto un torneo que otro) y la "
        "general para contrastar o cuando la de competencia esté vieja. "
        "En h2h, 'h' es quien fue local y 's' el marcador. "
        "tabla es la del grupo o zona del LOCAL — el visitante puede no estar ahí — "
        "y no trae goles en contra, solo 'gf'. "
        "plantelH/plantelA son los 25 que más jugaron de cada equipo: 'pj' son "
        "partidos jugados sumando todas las competencias que seguimos, 'peso_goles' "
        "es la fracción de los goles del equipo que hizo ese jugador (0.5 = la mitad). "
        "pjMaxH/pjMaxA es el 'pj' más alto del plantel: sirve de escala para leer un "
        "'pj' (5 sobre 5 es titular fijo, 1 sobre 26 es indiferente), pero no es un "
        "dato de la fuente sobre cuántos partidos jugó el equipo — es el máximo "
        "observado. El plantel no dice quién está lesionado: ESPN devuelve a todos "
        "como activos. Sirve para PESAR una baja que encontraste en tu research, "
        "no para descubrirla — y tampoco para descartarla: 'pj'/'goles' son "
        "acumulado de TODA la temporada, así que un jugador lesionado hace meses "
        "puede seguir mostrando partidos y goles de ANTES de lesionarse. Si el "
        "research trae una fecha de baja, esa fecha manda sobre el plantel."
        " El expediente también sirve para el campo 'desarrollo': describí cómo "
        "se VA a jugar el partido (quién va a tener la pelota, abierto o trabado, "
        "ritmo, qué puede alterar el guion) — SIEMPRE desde el expediente (forma, "
        "sede, plantel, h2h), nunca desde el mercado. Y 'desarrollo.senal' usa el "
        "léxico cerrado, que cambió el 2026-09-03 y son CINCO campos: "
        "corners_total muchos|pocos|null, faltas muchas|pocas|null, "
        "tarjetas SIEMPRE null, volumen_remates alto|bajo|null, y generador "
        "una LISTA de {equipo, jugador} con hasta uno por equipo (o []). "
        "No existe 'incierto' ni 'normal': cuando no hay base la respuesta "
        "es null, y null es la respuesta preferida. Las viejas "
        "(ritmo_goleador, estructura, ambos_marcan) están DEROGADAS: las tres "
        "describían cuántos goles, que es lo que el modelo ya calcula. "
        "LAS CUATRO DE VOLUMEN NO LAS DECIDE LA SKILL: vienen resueltas en "
        "`senal_base`, con el fallo ya calculado y el motivo. Copiá `fallo` "
        "tal cual; si es null, va null. `senal_base` trae los tres "
        "estimadores del total (produce, sede, cruzado), el gap contra la "
        "media de la liga, la dispersión entre ellos y los partidos medidos, "
        "y aplica el umbral calibrado por calibrar_senal.py sobre 20.897 "
        "partidos europeos con train/test temporal: faltas y remates piden "
        "10% de gap, 15% de dispersión y 6 partidos; corners pide 20/20/6; "
        "tarjetas no se afirma nunca porque no supera su tasa base en ningún "
        "umbral. La aritmética la hace el expediente porque cuando la hacía "
        "la skill salía inconsistente consigo misma. "
        "`generador` sale de liderazgoH/liderazgoA, que ya trae la ventaja "
        "del que más patea sobre el segundo medida POR PARTIDO (no por la "
        "suma: con apariciones desparejas la suma premia a quien jugó más). "
        "El umbral sigue siendo 50% y sigue siendo experimental. "
        "El ARBITRO no es evidencia admisible de faltas ni de tarjetas, "
        "en ninguna skill de VALOR."
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
