#!/usr/bin/env python3
"""Las herramientas de Pronóstic sobre los datos que ya existen.

Este módulo NO tiene LLM adentro y no habla con nadie: son funciones
puras que leen los JSON del cron y devuelven diccionarios listos para
mandarle al modelo como resultado de herramienta.

Dos reglas de este archivo, y salen de `CLAUDE.md`:

1. **El motor se copia, no se reescribe.** La matriz de Dixon-Coles se
   importa de `backtest.py` y el devig de Shin de `medir_clv.py`. Si se
   reimplementaran acá, un signo cambiado no tiraría excepción: daría
   probabilidades sutilmente mal para siempre.

2. **Nada de dependencias.** Solo biblioteca estándar, igual que
   `actualizar.py` y `mercado_extra.py`.

Todo lo que devuelve una función de acá termina leído por el modelo, así
que los diccionarios traen unidades y contexto, no números pelados. Y
traen `desde_cuando`: el cron corre dos veces por día y una cuota de
hace seis horas no es la cuota de ahora.
"""

import datetime
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RAIZ, "data")
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import backtest as _B          # matriz(), mercados(), pois(), tau()
import medir_clv as _C         # devig_shin()

# Tope de apuesta como fracción de la banca. Sale de `PRODUCT.md`:
# Kelly fraccional con tope de 4%.
TOPE_STAKE = 0.04
# Fracción de Kelly. Kelly pleno es demasiado agresivo para un modelo
# cuya ventaja NO está demostrada (ver la carta, §9).
FRACCION_KELLY = 0.25


# ---------------------------------------------------------------- caché

_cache = {}


def _cargar(nombre):
    """Lee un JSON de data/ una sola vez por proceso."""
    if nombre not in _cache:
        ruta = os.path.join(DATA, nombre)
        if not os.path.exists(ruta):
            _cache[nombre] = None
        else:
            with open(ruta, encoding="utf-8") as f:
                _cache[nombre] = json.load(f)
    return _cache[nombre]


def recargar():
    """Vacía la caché. La llama el bot cuando el cron reescribió los datos."""
    _cache.clear()


def _partidos():
    d = _cargar("partidos.json") or {}
    return d.get("partidos", []), d.get("actualizado")


def _buscar_partido(id_partido):
    ps, act = _partidos()
    for m in ps:
        if m.get("id") == id_partido:
            return m, act
    return None, act


def _antiguedad(sello):
    """Cuánto hace que se bajaron los datos, en horas y en criollo."""
    if not sello:
        return {"sello": None, "horas": None, "texto": "no sé de cuándo son estos datos"}
    try:
        t = datetime.datetime.fromisoformat(sello)
    except ValueError:
        return {"sello": sello, "horas": None, "texto": "no sé de cuándo son estos datos"}
    horas = (datetime.datetime.now() - t).total_seconds() / 3600.0
    if horas < 1:
        txt = "recién bajados"
    elif horas < 4:
        txt = "de hace un par de horas"
    else:
        txt = "de hace %d horas — confirmá el precio antes de jugar" % int(horas)
    return {"sello": sello, "horas": round(horas, 1), "texto": txt}


# ------------------------------------------------------------ mercados

def _implicitas(cuotas):
    """Probabilidades sin la comisión de la casa, y cuánto cobra.

    Shin para tres opciones; en dos opciones Shin devuelve el
    proporcional, que es lo correcto y no un atajo (ver `medir_devig.py`).
    """
    cuotas = [c for c in cuotas if c and c > 1]
    if not cuotas:
        return None, None
    margen = sum(1.0 / c for c in cuotas) - 1.0
    try:
        p = _C.devig_shin(cuotas)
    except Exception:
        s = sum(1.0 / c for c in cuotas)
        p = [(1.0 / c) / s for c in cuotas]
    return [round(x, 4) for x in p], round(margen, 4)


def _pct(x):
    return None if x is None else round(x * 100, 1)


def _de_cada_cien(x):
    """Cómo se le dice a un número al usuario. La prosa la escribe el
    modelo, pero el dato ya viene en la escala correcta."""
    return None if x is None else int(round(x * 100))


# ------------------------------------------------------- HERRAMIENTAS

def partidos_del_dia(fecha=None):
    """Qué se juega. `fecha` en 'AAAA-MM-DD'; sin fecha, de hoy en adelante.

    Trae una pista de legibilidad por partido para poder ordenar la
    fecha por cuánto sabemos en vez de por horario. La pista NO es una
    recomendación: sale de cuán desparejo es el partido y cuántos goles
    se esperan, que es lo único medido (ver la carta, §3).
    """
    ps, act = _partidos()
    hoy = datetime.date.today().isoformat()
    out = []
    for m in ps:
        d = m.get("date")
        if fecha and d != fecha:
            continue
        if not fecha and (not d or d < hoy):
            continue
        lh, la = m.get("lh"), m.get("la")
        pista = None
        if lh and la:
            mk = _B.mercados(_B.matriz(lh, la, m.get("rho", 0.0)))
            desbalance = abs(mk["1X2 local"] - mk["1X2 visitante"])
            goles = lh + la
            if desbalance > 0.20:
                pista = "hay un favorito claro"
            elif goles < 2.1:
                pista = "pinta cerrado y de pocos goles"
            else:
                pista = "parejo, difícil de leer"
        out.append({
            "id": m.get("id"), "fecha": d, "hora": m.get("hora"),
            "competicion": m.get("comp"), "local": m.get("home"),
            "visitante": m.get("away"), "estadio": m.get("estadio"),
            "pista": pista,
            "tiene_precio_bet365": bool(m.get("mercadoExtra")),
            "jugadores_cotizados": len((m.get("mercadoExtra") or {}).get("remates", {})),
        })
    out.sort(key=lambda x: (x["fecha"] or "", x["hora"] or ""))
    return {"partidos": out, "cuantos": len(out), "desde_cuando": _antiguedad(act)}


def datos_partido(id_partido):
    """Todo lo numérico de un partido: lo que esperamos y lo que cobra la casa.

    Devuelve nuestras probabilidades y las de la casa **en la misma
    escala**, para que se puedan comparar sin cuentas. Si las dos dicen
    lo mismo, ahí no hay negocio y hay que decirlo.
    """
    m, act = _buscar_partido(id_partido)
    if not m:
        return {"error": "no tengo ese partido cargado"}

    lh, la, rho = m.get("lh"), m.get("la"), m.get("rho", 0.0)
    if not lh or not la:
        return {"error": "ese partido no tiene números calculados todavía"}

    mk = _B.mercados(_B.matriz(lh, la, rho))
    nuestro = {k: _de_cada_cien(v) for k, v in mk.items()}
    nuestro["Menos de 2.5"] = 100 - nuestro["Más de 2.5"]
    nuestro["Menos de 1.5"] = 100 - nuestro["Más de 1.5"]
    nuestro["Menos de 3.5"] = 100 - nuestro["Más de 3.5"]
    nuestro["No marcan los dos"] = 100 - nuestro["Ambos marcan"]

    salida = {
        "partido": "%s vs %s" % (m.get("home"), m.get("away")),
        "id": id_partido, "fecha": m.get("date"), "hora": m.get("hora"),
        "competicion": m.get("comp"), "estadio": m.get("estadio"),
        "goles_que_esperamos": {
            "local": round(lh, 2), "visitante": round(la, 2),
            "total": round(lh + la, 2),
        },
        "nuestro_numero_de_cada_cien": nuestro,
        "esperado_del_partido": {
            "corners_total": m.get("corners"), "corners_local": m.get("cornersH"),
            "faltas": m.get("fouls"), "tarjetas": m.get("cards"),
        },
        "desde_cuando": _antiguedad(act),
        "avisos": [],
    }

    # --- Bet365, que es la casa profunda
    e = m.get("mercadoExtra") or {}
    casa = {}
    if e.get("1x2"):
        c = [e["1x2"]["local"], e["1x2"]["empate"], e["1x2"]["visitante"]]
        p, mg = _implicitas(c)
        casa["quien_gana"] = {
            "cuotas": {"local": c[0], "empate": c[1], "visitante": c[2]},
            "casa_de_cada_cien": {"local": _de_cada_cien(p[0]),
                                  "empate": _de_cada_cien(p[1]),
                                  "visitante": _de_cada_cien(p[2])},
            "comision": _pct(mg),
        }
    for linea, par in sorted((e.get("goles") or {}).items(), key=lambda x: float(x[0])):
        p, mg = _implicitas(par)
        if not p:
            continue
        casa.setdefault("goles", {})[linea] = {
            "mas": par[0], "menos": par[1],
            "casa_mas_de_cada_cien": _de_cada_cien(p[0]),
            "casa_menos_de_cada_cien": _de_cada_cien(p[1]),
            "comision": _pct(mg),
        }
    if e.get("btts"):
        p, mg = _implicitas([e["btts"]["si"], e["btts"]["no"]])
        casa["ambos_marcan"] = {
            "si": e["btts"]["si"], "no": e["btts"]["no"],
            "casa_si_de_cada_cien": _de_cada_cien(p[0]),
            "casa_no_de_cada_cien": _de_cada_cien(p[1]),
            "comision": _pct(mg),
        }
    if e.get("dc"):
        casa["doble_oportunidad"] = e["dc"]
    if e.get("corners"):
        casa["corners"] = e["corners"]
        salida["avisos"].append(
            "Córners POR EQUIPO: está medido que acertamos peor que la casa "
            "(atraso +0.0205 ±0.0093, ROI negativo en los seis umbrales). "
            "Se puede comentar, NO se recomienda apostar.")

    salida["precio_bet365"] = casa or None
    if not casa:
        salida["avisos"].append("Este partido no tiene precio de Bet365 cargado.")

    # --- DraftKings, la que trae ESPN, para poder comparar casas
    if m.get("mercado"):
        q = m["mercado"]
        salida["precio_draftkings"] = {
            "quien_gana": {"local": q.get("local"), "empate": q.get("empate"),
                           "visitante": q.get("visitante")},
            "goles_linea": q.get("totalLinea"),
            "goles_mas": q.get("totalOver"), "goles_menos": q.get("totalUnder"),
        }

    if m.get("sinAncla"):
        salida["avisos"].append(
            "Este equipo no tiene historia larga cargada: los números de "
            "córners y remates salen de pocos partidos.")
    return salida


def jugadores_partido(id_partido):
    """Las escaleras de remates de Bet365 cruzadas con la serie real.

    Es el mercado donde está la única señal medida del proyecto
    (+1.15 pp de CLV, 3 errores estándar) y también donde está el
    principal modo de perder plata: 3 de cada 10 jugadores que la casa
    cotiza no terminan siendo titulares.
    """
    m, act = _buscar_partido(id_partido)
    if not m:
        return {"error": "no tengo ese partido cargado"}
    escaleras = (m.get("mercadoExtra") or {}).get("remates") or {}
    if not escaleras:
        return {"error": "este partido no tiene escaleras de jugador cargadas"}

    pl = _cargar("planteles.json") or {}
    equipos = pl.get("equipos", {})
    onces = pl.get("once", {})

    series = {}
    for tid in (m.get("homeId"), m.get("awayId")):
        for j in equipos.get(str(tid), []):
            s = j.get("serie") or {}
            if s.get("remates"):
                series[j["nombre"]] = {
                    "remates": s["remates"], "al_arco": s.get("al_arco"),
                    "partidos_medidos": len(s["remates"]),
                    "titular_en": s.get("tit"), "puesto": j.get("pos"),
                }

    def _norm(n):
        # Cruce por igualdad exacta después de normalizar tildes. Nunca
        # por parecido: `equipos.py` documenta por qué (Paris SG vs Paris FC).
        tabla = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
        return n.translate(tabla).lower().strip()

    idx = {_norm(k): k for k in series}

    jugadores = []
    for nombre, d in escaleras.items():
        real = idx.get(_norm(nombre))
        s = series.get(real) if real else None
        lineas = {k: v for k, v in sorted(d.get("lineas", {}).items(),
                                          key=lambda x: float(x[0]))}
        jugadores.append({
            "nombre": nombre,
            "equipo": m.get("home") if d.get("lado") == "L" else m.get("away"),
            "cuotas_por_linea": lineas,
            "serie_de_remates": s["remates"] if s else None,
            "promedio": round(sum(s["remates"]) / len(s["remates"]), 1) if s else None,
            "partidos_medidos": s["partidos_medidos"] if s else None,
            "puesto": s["puesto"] if s else None,
            "cruzo_con_nuestra_serie": bool(s),
        })
    jugadores.sort(key=lambda j: -(j["promedio"] or -1))

    once = {}
    for lado, tid in (("local", m.get("homeId")), ("visitante", m.get("awayId"))):
        o = onces.get(str(tid))
        if o:
            once[lado] = {
                "ojo": "Es el once del partido ANTERIOR, no el de este. "
                       "No lo presentes como confirmado.",
                "fecha": o.get("fecha"), "rival": o.get("rival"),
                "esquema": o.get("esquema"),
                "jugadores": [j.get("nombre") for j in o.get("jugadores", [])],
            }

    return {
        "partido": "%s vs %s" % (m.get("home"), m.get("away")),
        "cuantos_cotiza_la_casa": len(escaleras),
        "jugadores": jugadores,
        "once_anterior": once or None,
        "desde_cuando": _antiguedad(act),
        "aviso": ("La casa cotiza %d jugadores y no pueden jugar todos. Está "
                  "medido que 3 de cada 10 cotizados no arrancan: cualquier "
                  "jugada de acá depende de confirmar el once."
                  % len(escaleras)),
    }


def movimiento(id_partido, jugador=None):
    """Cómo se movió el precio desde que lo miramos por primera vez.

    Sale de `cuotas.json` y `props_jugadores.json`, que el cron viene
    acumulando foto por corrida. Nadie los estaba mirando.
    """
    salida = {"id": id_partido, "quien_gana": None, "jugador": None}

    c = _cargar("cuotas.json") or {}
    fotos = c.get(id_partido)
    if fotos and len(fotos) >= 2:
        pri, ult = fotos[0], fotos[-1]
        def _d(a, b):
            if not a or not b:
                return None
            return {"abrio": a, "ahora": b, "cambio": round(b - a, 2)}
        salida["quien_gana"] = {
            "primera_foto": pri.get("t"), "ultima_foto": ult.get("t"),
            "fotos": len(fotos),
            "local": _d(pri.get("local"), ult.get("local")),
            "empate": _d(pri.get("empate"), ult.get("empate")),
            "visitante": _d(pri.get("visitante"), ult.get("visitante")),
        }
    elif fotos:
        salida["quien_gana"] = {"fotos": 1, "nota": "una sola foto: no puedo decir si se movió"}

    if jugador:
        p = _cargar("props_jugadores.json") or {}
        clave = "%s__remates__%s" % (id_partido, jugador)
        fj = p.get(clave)
        if fj and len(fj) >= 2:
            pri, ult = fj[0].get("lineas", {}), fj[-1].get("lineas", {})
            cambios = {}
            for ln in sorted(set(pri) & set(ult), key=float):
                if pri[ln] != ult[ln]:
                    cambios[ln] = {"abrio": pri[ln], "ahora": ult[ln]}
            salida["jugador"] = {
                "nombre": jugador, "fotos": len(fj),
                "desde": fj[0].get("t"), "hasta": fj[-1].get("t"),
                "lineas_que_se_movieron": cambios or "ninguna, quedó clavada",
            }
        elif fj:
            salida["jugador"] = {"nombre": jugador, "fotos": 1,
                                 "nota": "una sola foto: no puedo decir si se movió"}
        else:
            salida["jugador"] = {"nombre": jugador, "nota": "no tengo fotos de ese jugador"}

    if not salida["quien_gana"] and not salida["jugador"]:
        return {"nota": "no tengo historia de precios de ese partido"}
    return salida


def historial(id_partido):
    """Cómo llega cada uno: forma, cruces anteriores y tabla."""
    m, act = _buscar_partido(id_partido)
    if not m:
        return {"error": "no tengo ese partido cargado"}

    def _forma(fs):
        return [{"fecha": f.get("d"), "rival": f.get("rival"),
                 "donde": "local" if f.get("local") else "visitante",
                 "resultado": {"W": "ganó", "D": "empató", "L": "perdió"}.get(f.get("r")),
                 "marcador": f.get("marcador")} for f in (fs or [])]

    tabla = m.get("tabla") or []
    def _fila(tid, nombre):
        for i, f in enumerate(tabla, 1):
            if f.get("id") == str(tid) or f.get("t") == nombre:
                return {"puesto": i, "puntos": f.get("pts"), "jugados": f.get("pj"),
                        "ganados": f.get("g"), "empatados": f.get("e"),
                        "perdidos": f.get("p"), "goles_a_favor": f.get("gf")}
        return None

    h2h = [{"fecha": h.get("d"), "local": h.get("h"), "visitante": h.get("a"),
            "marcador": h.get("s")} for h in (m.get("h2h") or [])]

    return {
        "partido": "%s vs %s" % (m.get("home"), m.get("away")),
        "local": {"nombre": m.get("home"),
                  "ultimos_en_esta_competicion": _forma(m.get("formH")),
                  "ultimos_en_todas": _forma(m.get("formH_general")),
                  "tabla": _fila(m.get("homeId"), m.get("home"))},
        "visitante": {"nombre": m.get("away"),
                      "ultimos_en_esta_competicion": _forma(m.get("formA")),
                      "ultimos_en_todas": _forma(m.get("formA_general")),
                      "tabla": _fila(m.get("awayId"), m.get("away"))},
        "cruces_anteriores": h2h,
        "aviso_h2h": ("Un solo cruce no es historial, es una anécdota."
                      if len(h2h) == 1 else None),
        "desde_cuando": _antiguedad(act),
    }


def revisar_boleta(patas):
    """La probabilidad real de una combinada, y qué pata la está hundiendo.

    `patas` es una lista de {"id_partido", "mercado", "cuota"}, donde
    `mercado` es una clave de `nuestro_numero_de_cada_cien`.

    Dos patas del MISMO partido no se multiplican: se piden sobre la
    matriz. Eso todavía no está implementado, así que se avisa en vez de
    dar un número mal — un número mal acá no se ve como un error, se ve
    como datos.
    """
    if not patas:
        return {"error": "no me pasaste ninguna pata"}

    detalle, prob, cuota_total = [], 1.0, 1.0
    por_partido = {}
    for p in patas:
        d = datos_partido(p.get("id_partido"))
        if "error" in d:
            return {"error": "una de las patas no la tengo: %s" % p.get("id_partido")}
        nombre = p.get("mercado")
        n = d["nuestro_numero_de_cada_cien"].get(nombre)
        if n is None:
            return {"error": "no conozco el mercado '%s'. Los que tengo: %s"
                             % (nombre, ", ".join(d["nuestro_numero_de_cada_cien"]))}
        pp = n / 100.0
        prob *= pp
        c = p.get("cuota")
        if c:
            cuota_total *= c
        por_partido.setdefault(p["id_partido"], []).append(nombre)
        detalle.append({"partido": d["partido"], "mercado": nombre,
                        "nuestro_numero_de_cada_cien": n, "cuota": c})

    repetidos = {k: v for k, v in por_partido.items() if len(v) > 1}

    # Cuál pata aporta más a la probabilidad de fallar.
    fallo_total = 1 - prob
    for d in detalle:
        pp = d["nuestro_numero_de_cada_cien"] / 100.0
        d["cuanto_aporta_al_fallo"] = (
            round((1 - pp) / sum(1 - x["nuestro_numero_de_cada_cien"] / 100.0
                                 for x in detalle) * 100)
            if fallo_total > 0 else 0)

    peor = max(detalle, key=lambda d: d["cuanto_aporta_al_fallo"])
    justa = round(1 / prob, 2) if prob > 0 else None

    salida = {
        "patas": detalle,
        "sale_de_cada_cien_veces": _de_cada_cien(prob),
        "cuota_justa": justa,
        "cuota_que_te_pagan": round(cuota_total, 2) if cuota_total > 1 else None,
        "la_pata_que_la_hunde": peor["mercado"] + " — " + peor["partido"],
    }
    if cuota_total > 1 and justa:
        salida["comision_total_de_la_casa"] = _pct((justa - cuota_total) / justa)
    if repetidos:
        salida["cuidado"] = (
            "Hay patas del MISMO partido (%s). Esas no son independientes y la "
            "multiplicación de arriba las cuenta mal: el número real es distinto. "
            "Avisale a Lucas y no le des ese número como bueno."
            % ", ".join(repetidos))
    if len(detalle) >= 4:
        salida["nota"] = (
            "Son %d patas. La comisión de la casa se multiplica, no se reparte."
            % len(detalle))
    return salida


def stake(de_cada_cien, cuota, banca=None):
    """Cuánto poner. Kelly fraccional con tope, copiado de index.html:1569.

    Se usa un cuarto de Kelly porque la ventaja del modelo NO está
    demostrada: Kelly pleno supone que la probabilidad propia es
    correcta, y eso es justo lo que las mediciones no sostienen.
    """
    p = de_cada_cien / 100.0 if de_cada_cien > 1 else de_cada_cien
    b = cuota - 1
    if b <= 0:
        return {"fraccion": 0, "por_que": "esa cuota no paga nada"}
    k = max(0.0, (p * b - (1 - p)) / b)
    f = min(k * FRACCION_KELLY, TOPE_STAKE)
    out = {
        "de_cada_cien_pesos_de_banca": round(f * 100, 1),
        "tope": "%d%%" % int(TOPE_STAKE * 100),
    }
    if k <= 0:
        out["por_que"] = ("A ese precio no da para apostar: la casa te paga "
                          "menos de lo que vale.")
    if banca:
        out["plata"] = round(banca * f)
    return out


# ------------------------------------------------- memoria de Lucas

MEMORIA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "memoria.json")
VACIA = {"banca": None, "preferencias": {}, "apuestas": []}


def _memoria():
    if not os.path.exists(MEMORIA):
        return dict(VACIA)
    try:
        with open(MEMORIA, encoding="utf-8") as f:
            m = json.load(f)
    except (ValueError, OSError):
        return dict(VACIA)
    for k, v in VACIA.items():
        m.setdefault(k, v if not isinstance(v, (dict, list)) else type(v)())
    return m


def _guardar_memoria(m):
    """Escribe a un temporal y reemplaza. Si se corta a la mitad, el
    registro viejo sigue entero — es la plata de Lucas, no un caché."""
    tmp = MEMORIA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    os.replace(tmp, MEMORIA)


def recordar_chat(chat_id):
    """Guarda a qué chat de Telegram escribirle.

    `informe.py` y `vigilante.py` corren solos, sin que nadie les hable:
    sin esto no saben a dónde mandar el mensaje. Lo escribe `bot.py` la
    primera vez que Lucas dice algo.
    """
    m = _memoria()
    if m.get("chat_id") == chat_id:
        return
    m["chat_id"] = chat_id
    _guardar_memoria(m)


def chat_guardado():
    return _memoria().get("chat_id")


def poner_banca(monto):
    """Cuánta plata tiene Lucas para apostar. Sin esto no se puede decir
    cuánto poner."""
    m = _memoria()
    anterior = m.get("banca")
    m["banca"] = monto
    _guardar_memoria(m)
    return {"banca": monto, "antes": anterior, "guardado": True}


def anotar(id_partido, mercado, cuota, monto, quien="lucas", nota=None):
    """Deja anotada una apuesta.

    `quien` es "pronostic" si la propuso el asesor y "lucas" si fue idea
    de él. Esa distinción es la que después permite medir a cada uno por
    separado, que es la razón de ser del espejo. No la saques.
    """
    if quien not in ("lucas", "pronostic"):
        return {"error": "quien tiene que ser 'lucas' o 'pronostic'"}
    m, _ = _buscar_partido(id_partido)
    if not m:
        return {"error": "no tengo ese partido cargado, no la anoto"}

    mem = _memoria()
    ap = {
        "anotada": datetime.datetime.now().isoformat(timespec="minutes"),
        "id_partido": id_partido,
        "partido": "%s vs %s" % (m.get("home"), m.get("away")),
        "fecha_partido": m.get("date"),
        "mercado": mercado, "cuota": cuota, "monto": monto,
        "quien": quien, "nota": nota, "resultado": None,
    }
    mem["apuestas"].append(ap)
    _guardar_memoria(mem)

    exp = sum(a.get("monto", 0) for a in mem["apuestas"] if not a.get("resultado"))
    salida = {"anotada": True, "apuesta": ap, "expuesto_ahora": exp}
    if mem.get("banca"):
        pct = exp / mem["banca"] * 100
        salida["porcentaje_de_la_banca_expuesto"] = round(pct, 1)
        if pct > 15:
            salida["aviso"] = ("Con esta quedan %.0f%% de la banca en juego. "
                               "Decíselo." % pct)
    return salida


def resolver(id_partido=None):
    """Cierra las apuestas que ya se pueden cerrar con el marcador final.

    Solo resuelve lo que se deduce del marcador. Las de jugador quedan
    abiertas a propósito: se liquidan con los remates del partido, que
    no están en `resultados.json`.
    """
    mem = _memoria()
    res = _cargar("resultados.json") or {}
    cerradas, pendientes = [], []
    for a in mem["apuestas"]:
        if a.get("resultado"):
            continue
        if id_partido and a["id_partido"] != id_partido:
            continue
        marcador = res.get(a["id_partido"])
        if not marcador:
            pendientes.append({**a, "por_que": "todavía no hay marcador"})
            continue
        r = _desenlace(a["mercado"], marcador)
        if r is None:
            pendientes.append({**a, "por_que": "no lo puedo resolver del "
                                              "marcador; pedí los remates"})
            continue
        a["resultado"] = r
        a["marcador_final"] = marcador
        a["devolucion"] = (round(a["monto"] * a["cuota"] - a["monto"])
                           if r == "ganada" else -a["monto"])
        cerradas.append(a)
    if cerradas:
        _guardar_memoria(mem)
    return {"cerradas": cerradas, "siguen_abiertas": pendientes}


def _desenlace(mercado, marcador):
    """Gana o pierde, según el marcador. None si no se deduce de ahí."""
    try:
        gl, gv = (int(x) for x in marcador.split("-"))
    except (ValueError, AttributeError):
        return None
    t, m = gl + gv, mercado.strip().lower()
    reglas = {
        "1x2 local": gl > gv, "1x2 empate": gl == gv, "1x2 visitante": gl < gv,
        "ambos marcan": gl > 0 and gv > 0,
        "no marcan los dos": not (gl > 0 and gv > 0),
    }
    if m in reglas:
        return "ganada" if reglas[m] else "perdida"
    for prefijo, cmp in (("más de ", lambda l: t > l), ("menos de ", lambda l: t < l)):
        if m.startswith(prefijo):
            try:
                return "ganada" if cmp(float(m[len(prefijo):])) else "perdida"
            except ValueError:
                return None
    return None


def banca():
    """Cuánto tiene, cuánto está expuesto y cómo viene la racha."""
    m = _memoria()
    abiertas = [a for a in m.get("apuestas", []) if not a.get("resultado")]
    cerradas = [a for a in m.get("apuestas", []) if a.get("resultado")]
    exp = sum(a.get("monto", 0) for a in abiertas)
    ult = [a.get("resultado") for a in cerradas[-5:]]
    return {
        "banca": m.get("banca"),
        "expuesto_ahora": exp,
        "apuestas_abiertas": len(abiertas),
        "ultimas_cinco": ult or "todavía no hay historial",
        "nota": ("Todavía no hay banca cargada. Preguntale a Lucas cuánta "
                 "tiene antes de decirle cuánto poner."
                 if not m.get("banca") else None),
    }


def registro(limite=30):
    """Qué apostó y cómo le fue. Es la única ventaja que nadie le puede vender."""
    m = _memoria()
    ap = m.get("apuestas", [])[-limite:]
    res = _cargar("resultados.json") or {}
    for a in ap:
        if not a.get("resultado") and a.get("id_partido") in res:
            a["marcador_final"] = res[a["id_partido"]]
    return {"apuestas": ap, "cuantas": len(ap),
            "nota": "todavía no hay nada anotado" if not ap else None}


def expediente(id_partido):
    """Todo lo que sabemos de un partido, en un solo diccionario.

    Existe para el modo sin clave: cualquier agente que corra en esta
    carpeta —Antigravity, OpenCode, Hermes— puede pedir esto, leer
    `voz.md`, y hacer de Pronóstic sin que haya ninguna API de por medio.
    """
    return {
        "numeros": datos_partido(id_partido),
        "historial": historial(id_partido),
        "jugadores": jugadores_partido(id_partido),
        "movimiento": movimiento(id_partido),
        "banca_y_registro": banca(),
    }


AYUDA = """\
Pronóstic — los datos, sin IA de por medio.

  python experto/datos.py fecha [AAAA-MM-DD]   qué se juega
  python experto/datos.py <id_partido>         el expediente completo
  python experto/datos.py banca                banca y apuestas abiertas

Sirve para dos cosas: mirar los datos a mano, y para el modo sin clave
—le pasás el expediente a Antigravity, OpenCode o Hermes junto con
`experto/voz.md` y hacen de asesor. Ver experto/SIN_CLAVE.md.
"""

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    salida = None
    if arg in (None, "-h", "--help", "ayuda"):
        print(AYUDA)
    elif arg == "fecha":
        salida = partidos_del_dia(sys.argv[2] if len(sys.argv) > 2 else None)
    elif arg == "banca":
        salida = {"banca": banca(), "registro": registro()}
    else:
        salida = expediente(arg)
    if salida is not None:
        print(json.dumps(salida, ensure_ascii=False, indent=1))
