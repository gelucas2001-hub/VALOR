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
import re
import sys
import unicodedata

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


def _analisis_goles_recientes(m, lh, la):
    """Calcula promedios de goles recientes y detecta divergencias con el modelo.

    No emite veredictos de apuesta (no prohíbe el Under ni fuerza el Over):
    identifica cuándo la muestra reciente tensiona la proyección estadística
    para que el analista evalúe si la diferencia está explicada por el
    contexto (rivales, rojas, bajas) o aconseja abstenerse en goles.
    """
    def _parse_scores(forma_list):
        scored, conceded = [], []
        for f in (forma_list or []):
            sc = f.get("marcador")
            if sc and "-" in str(sc):
                try:
                    p1, p2 = [int(x) for x in str(sc).split("-")]
                    es_local = bool(f.get("local"))
                    scored.append(p1 if es_local else p2)
                    conceded.append(p2 if es_local else p1)
                except (ValueError, TypeError):
                    pass
        return scored, conceded

    h_gf, h_gc = _parse_scores(m.get("formH"))
    a_gf, a_gc = _parse_scores(m.get("formA"))

    h2h_totales = []
    for h in (m.get("h2h") or []):
        sc = h.get("s")
        if sc and "-" in str(sc):
            try:
                p1, p2 = [int(x) for x in str(sc).split("-")]
                h2h_totales.append(p1 + p2)
            except (ValueError, TypeError):
                pass

    prom_h_gf = round(sum(h_gf) / len(h_gf), 1) if h_gf else None
    prom_a_gf = round(sum(a_gf) / len(a_gf), 1) if a_gf else None
    prom_h_tot = round(sum(x + y for x, y in zip(h_gf, h_gc)) / len(h_gf), 1) if h_gf else None
    prom_a_tot = round(sum(x + y for x, y in zip(a_gf, a_gc)) / len(a_gf), 1) if a_gf else None
    prom_h2h = round(sum(h2h_totales) / len(h2h_totales), 1) if h2h_totales else None

    resumen = {
        "local": {"nombre": m.get("home"), "partidos": len(h_gf), "promedio_favor": prom_h_gf, "promedio_total_partido": prom_h_tot},
        "visitante": {"nombre": m.get("away"), "partidos": len(a_gf), "promedio_favor": prom_a_gf, "promedio_total_partido": prom_a_tot},
        "h2h_promedio_goles": prom_h2h,
        "h2h_partidos": len(h2h_totales),
    }

    alertas = []
    lambda_total = (lh or 0.0) + (la or 0.0)

    # 1. Tensión modelo bajo vs muestra reciente activa
    if lambda_total < 3.0:
        motivos = []
        if prom_h_gf and prom_h_gf >= 2.3 and len(h_gf) >= 3:
            motivos.append("%s promedia %.1f goles a favor en sus últimos %d partidos" % (m.get("home"), prom_h_gf, len(h_gf)))
        if prom_a_gf and prom_a_gf >= 2.3 and len(a_gf) >= 3:
            motivos.append("%s promedia %.1f goles a favor en sus últimos %d partidos" % (m.get("away"), prom_a_gf, len(a_gf)))
        if (prom_h_tot and prom_h_tot >= 4.0 and len(h_gf) >= 3) or (prom_a_tot and prom_a_tot >= 4.0 and len(a_gf) >= 3):
            motivos.append("partidos recientes con alto promedio de goles (%s: %.1f, %s: %.1f)" % (m.get("home"), prom_h_tot or 0, m.get("away"), prom_a_tot or 0))
        elif prom_h_tot and prom_a_tot and (prom_h_tot >= 3.2 and prom_a_tot >= 3.2) and len(h_gf) >= 3:
            motivos.append("ambos vienen de partidos con alto promedio de goles (%.1f y %.1f)" % (prom_h_tot, prom_a_tot))
        if prom_h2h and prom_h2h >= 4.0 and len(h2h_totales) >= 2:
            motivos.append("los cruces directos promedian %.1f goles (muestra chica: %d cruces)" % (prom_h2h, len(h2h_totales)))

        if motivos:
            alertas.append(
                "Tensión metodológica (modelo bajo vs muestra reciente activa): " + "; ".join(motivos) +
                ". El modelo estadístico proyecta %.2f goles esperados, pero la racha reciente muestra "
                "alto movimiento. No seguir narrativas ni descartar el modelo ciegamente: analizar si la "
                "diferencia responde a rivales específicos o si genera incertidumbre suficiente para "
                "abstenerse en el mercado de goles." % lambda_total
            )

    # 2. Tensión modelo alto vs muestra reciente cerrada
    elif lambda_total >= 3.0:
        motivos = []
        if prom_h_tot and prom_a_tot and (prom_h_tot <= 1.8 and prom_a_tot <= 1.8) and len(h_gf) >= 3 and len(a_gf) >= 3:
            motivos.append("partidos recientes de ambos promedian solo %.1f y %.1f goles" % (prom_h_tot, prom_a_tot))
        if prom_h2h and prom_h2h <= 1.5 and len(h2h_totales) >= 2:
            motivos.append("cruces directos promedian solo %.1f goles (muestra chica: %d cruces)" % (prom_h2h, len(h2h_totales)))

        if motivos:
            alertas.append(
                "Tensión metodológica (modelo alto vs muestra reciente cerrada): " + "; ".join(motivos) +
                ". El modelo estadístico proyecta un cruce abierto (%.2f goles esperados), pero la forma "
                "reciente muestra tanteadores bajos. Evaluar si la diferencia está justificada por la propuesta "
                "táctica de hoy o si conviene abstenerse en goles." % lambda_total
            )

    return resumen, alertas


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
    nuestro["Doble oportunidad 1X"] = nuestro["1X2 local"] + nuestro["1X2 empate"]
    nuestro["Doble oportunidad X2"] = nuestro["1X2 visitante"] + nuestro["1X2 empate"]
    nuestro["Doble oportunidad 12"] = nuestro["1X2 local"] + nuestro["1X2 visitante"]

    resumen_goles, alertas_goles = _analisis_goles_recientes(m, lh, la)

    salida = {
        "partido": "%s vs %s" % (m.get("home"), m.get("away")),
        "id": id_partido, "fecha": m.get("date"), "hora": m.get("hora"),
        "competicion": m.get("comp"), "estadio": m.get("estadio"),
        "goles_que_esperamos": {
            "local": round(lh, 2), "visitante": round(la, 2),
            "total": round(lh + la, 2),
        },
        "nuestro_numero_de_cada_cien": nuestro,
        "resumen_goles_recientes": resumen_goles,
        "esperado_del_partido": {
            "corners_total": m.get("corners"), "corners_local": m.get("cornersH"),
            "faltas": m.get("fouls"), "tarjetas": m.get("cards"),
        },
        "desde_cuando": _antiguedad(act),
        "avisos": list(alertas_goles),
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

    # --- Comparativa de valor y cálculo de stake garantizado por diseño
    banca_actual = _memoria().get("banca")
    comparativa = []

    def _comp_item(mercado, prob_nuestro, cuota_casa, prob_casa=None):
        if not cuota_casa or not prob_nuestro:
            return
        stk = stake(prob_nuestro, cuota_casa, banca_actual)
        item = {
            "mercado": mercado,
            "nuestro_de_cada_cien": prob_nuestro,
            "cuota_bet365": cuota_casa,
            "stake_kelly_pct": stk["de_cada_cien_pesos_de_banca"],
        }
        if prob_casa is not None:
            item["casa_de_cada_cien"] = prob_casa
            item["diferencia_puntos"] = prob_nuestro - prob_casa
        if stk.get("plata"):
            item["monto_pesos"] = stk["plata"]
        if stk["de_cada_cien_pesos_de_banca"] > 0:
            txt = "Margen a favor. Stake sugerido: %.1f%%" % stk["de_cada_cien_pesos_de_banca"]
            if stk.get("plata"):
                txt += " ($%s)" % stk["plata"]
            item["evaluacion"] = txt
        else:
            item["evaluacion"] = stk.get("por_que", "A ese precio estás pagando de más")
        comparativa.append(item)

    if casa.get("quien_gana"):
        c = casa["quien_gana"]["cuotas"]
        p_c = casa["quien_gana"]["casa_de_cada_cien"]
        _comp_item("1X2 local", nuestro["1X2 local"], c.get("local"), p_c.get("local"))
        _comp_item("1X2 empate", nuestro["1X2 empate"], c.get("empate"), p_c.get("empate"))
        _comp_item("1X2 visitante", nuestro["1X2 visitante"], c.get("visitante"), p_c.get("visitante"))

    if casa.get("doble_oportunidad"):
        dc = casa["doble_oportunidad"]
        _comp_item("Doble oportunidad 1X", nuestro["Doble oportunidad 1X"], dc.get("1X"))
        _comp_item("Doble oportunidad X2", nuestro["Doble oportunidad X2"], dc.get("X2"))
        _comp_item("Doble oportunidad 12", nuestro["Doble oportunidad 12"], dc.get("12"))

    for linea, par in sorted(casa.get("goles", {}).items(), key=lambda x: float(x[0])):
        _comp_item("Más de %s" % linea, nuestro.get("Más de %s" % linea), par.get("mas"), par.get("casa_mas_de_cada_cien"))
        _comp_item("Menos de %s" % linea, nuestro.get("Menos de %s" % linea), par.get("menos"), par.get("casa_menos_de_cada_cien"))

    if casa.get("ambos_marcan"):
        bm = casa["ambos_marcan"]
        _comp_item("Ambos marcan", nuestro["Ambos marcan"], bm.get("si"), bm.get("casa_si_de_cada_cien"))
        _comp_item("No marcan los dos", nuestro["No marcan los dos"], bm.get("no"), bm.get("casa_no_de_cada_cien"))

    comparativa.sort(key=lambda x: -x["stake_kelly_pct"])
    salida["comparativa"] = comparativa

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

    resumen_goles, alertas_goles = _analisis_goles_recientes(m, m.get("lh", 0.0), m.get("la", 0.0))

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
        "resumen_goles_recientes": resumen_goles,
        "alerta_contexto": alertas_goles[0] if alertas_goles else None,
        "aviso_h2h": ("Un solo cruce no es historial, es una anécdota."
                      if len(h2h) == 1 else None),
        "desde_cuando": _antiguedad(act),
    }


def _normalizar_mercado(nombre, local=None, visitante=None):
    """Devuelve la clave canónica de un mercado a partir de texto libre."""
    if not nombre:
        return None
    t = str(nombre).strip()
    s = "".join(c for c in unicodedata.normalize('NFD', t)
                if unicodedata.category(c) != 'Mn').lower()
    s = " ".join(s.split())

    # Directos de 1X2
    loc_s = "".join(c for c in unicodedata.normalize('NFD', str(local or "")) if unicodedata.category(c) != 'Mn').lower()
    vis_s = "".join(c for c in unicodedata.normalize('NFD', str(visitante or "")) if unicodedata.category(c) != 'Mn').lower()

    if s in ("1x2 local", "local", "gana local", "1") or (loc_s and s in ("gana " + loc_s, loc_s + " gana", loc_s)):
        return "1X2 local"
    if s in ("1x2 empate", "empate", "x", "empata", "empatan"):
        return "1X2 empate"
    if s in ("1x2 visitante", "visitante", "gana visitante", "2") or (vis_s and s in ("gana " + vis_s, vis_s + " gana", vis_s)):
        return "1X2 visitante"

    # Doble oportunidad
    if s in ("doble oportunidad 1x", "1x", "local o empate", "1x local o empate", "doble oportunidad local o empate"):
        return "Doble oportunidad 1X"
    if s in ("doble oportunidad x2", "x2", "empate o visitante", "x2 empate o visitante", "doble oportunidad empate o visitante"):
        return "Doble oportunidad X2"
    if s in ("doble oportunidad 12", "12", "local o visitante", "12 local o visitante", "doble oportunidad local o visitante"):
        return "Doble oportunidad 12"

    # Ambos marcan
    if s in ("ambos marcan", "btts", "ambos anotan", "gol de ambos", "si ambos marcan", "ambos marcan si"):
        return "Ambos marcan"
    if s in ("no marcan los dos", "no ambos marcan", "ambos no marcan", "ambos marcan no"):
        return "No marcan los dos"

    # Si es de remates o tiros de jugador, no normalizar a goles del partido
    if any(pal in s for pal in ("remate", "remates", "tiro", "tiros", "disparo", "disparos")):
        return t

    # Goles: Mas de / Menos de
    m_mas = re.search(r'(?:\bmas de\b|\bover\b|\+)\s*(\d+(?:\.\d+)?)', s)
    if m_mas:
        return "Más de %s" % m_mas.group(1)
    m_menos = re.search(r'(?:\bmenos de\b|\bunder\b|-)\s*(\d+(?:\.\d+)?)', s)
    if m_menos:
        return "Menos de %s" % m_menos.group(1)

    return t


def _predicado(nombre, local=None, visitante=None):
    """Traduce el nombre de un mercado a una condición sobre el marcador.

    Es lo que permite calcular una combinada de DOS PATAS DEL MISMO
    PARTIDO de verdad: se suman las casillas de la matriz donde pasan las
    dos a la vez, en vez de multiplicar dos probabilidades que no son
    independientes. "Gana el local" y "menos de 2.5 goles" se pisan —
    multiplicarlas da un número que no existe.
    """
    canonico = _normalizar_mercado(nombre, local, visitante)
    fijos = {
        "1X2 local": lambda i, j: i > j,
        "1X2 empate": lambda i, j: i == j,
        "1X2 visitante": lambda i, j: i < j,
        "Doble oportunidad 1X": lambda i, j: i >= j,
        "Doble oportunidad X2": lambda i, j: j >= i,
        "Doble oportunidad 12": lambda i, j: i != j,
        "Ambos marcan": lambda i, j: i > 0 and j > 0,
        "No marcan los dos": lambda i, j: not (i > 0 and j > 0),
    }
    if canonico in fijos:
        return fijos[canonico]
    for prefijo, cmp in (("Más de ", lambda t, l: t > l),
                         ("Menos de ", lambda t, l: t < l)):
        if canonico.startswith(prefijo):
            try:
                linea = float(canonico[len(prefijo):])
                return lambda i, j, l=linea, c=cmp: c(i + j, l)
            except ValueError:
                return None
    return None


def _conjunta(id_partido, mercados):
    """Probabilidad de que pasen TODOS estos mercados en el mismo partido."""
    m, _ = _buscar_partido(id_partido)
    if not m or not m.get("lh"):
        return None
    loc = m.get("home")
    vis = m.get("away")
    conds = [_predicado(x, loc, vis) for x in mercados]
    if any(c is None for c in conds):
        return None
    M = _B.matriz(m["lh"], m["la"], m.get("rho", 0.0))
    return sum(M[i][j] for i in range(len(M)) for j in range(len(M))
               if all(c(i, j) for c in conds))


def revisar_boleta(patas):
    """La probabilidad real de una combinada, y qué pata la está hundiendo.

    `patas` es una lista de {"id_partido", "mercado", "cuota"}, donde
    `mercado` puede ser cualquier mercado de equipo (1X2, Doble Oportunidad,
    Goles, Ambos Marcan) o de jugador (remates).

    **Dos patas del MISMO partido no se multiplican.** Se resuelven sobre
    la matriz de marcadores, sumando las casillas donde pasan todas a la
    vez. Los mercados de jugador se tratan como independientes.
    """
    if not patas:
        return {"error": "no me pasaste ninguna pata"}

    detalle, cuota_total = [], 1.0
    por_partido_mercados = {}
    margenes_individuales = []

    for p in patas:
        pid = p.get("id_partido")
        d = datos_partido(pid)
        if "error" in d:
            return {"error": "una de las patas no la tengo: %s" % pid}

        m_obj, _ = _buscar_partido(pid)
        loc = m_obj.get("home") if m_obj else None
        vis = m_obj.get("away") if m_obj else None

        raw_mercado = p.get("mercado", "")
        canonico = _normalizar_mercado(raw_mercado, loc, vis)
        n = d["nuestro_numero_de_cada_cien"].get(canonico)
        c = p.get("cuota")
        es_jugador = False
        nota_pata = None
        serie = []
        aciertos = None
        margen_pata = 5.5

        # Si no es de equipo, buscar si coincide con un jugador
        if n is None:
            jp = jugadores_partido(pid)
            if "jugadores" in jp:
                for jug in jp["jugadores"]:
                    norm_jug = "".join(ch for ch in unicodedata.normalize('NFD', jug["nombre"])
                                       if unicodedata.category(ch) != 'Mn').lower()
                    norm_m = "".join(ch for ch in unicodedata.normalize('NFD', raw_mercado)
                                     if unicodedata.category(ch) != 'Mn').lower()
                    if norm_jug in norm_m:
                        es_jugador = True
                        m_lin = re.search(r'(\d+(?:\.\d+)?)', norm_m)
                        linea_str = m_lin.group(1) if m_lin else "1.5"
                        if not c:
                            c = jug.get("cuotas_por_linea", {}).get(linea_str)
                        serie = jug.get("serie_de_remates") or []
                        if serie:
                            fl = float(linea_str)
                            aciertos = sum(1 for x in serie if x > fl)
                            nota_pata = ("Mercado de jugador (%s pasar %s remates): serie descriptiva %s "
                                         "(acertó en %d de %d partidos recientes). No es probabilidad estadística calibrada."
                                         % (jug["nombre"], linea_str, serie, aciertos, len(serie)))
                        else:
                            nota_pata = "Mercado de jugador (%s): sin serie reciente." % jug["nombre"]
                        margen_pata = 8.5
                        canonico = "%s pasar %s remates" % (jug["nombre"], linea_str)
                        break

        if n is None and not es_jugador:
            return {"error": "no conozco el mercado '%s'. Los que tengo: %s"
                             % (raw_mercado, ", ".join(d["nuestro_numero_de_cada_cien"]))}

        if c:
            cuota_total *= c
            bet = d.get("precio_bet365") or {}
            if canonico in ("1X2 local", "1X2 empate", "1X2 visitante") and bet.get("quien_gana"):
                margen_pata = bet["quien_gana"].get("comision", 5.5)
            elif canonico.startswith("Más de ") or canonico.startswith("Menos de "):
                lin = canonico.split()[-1]
                if bet.get("goles", {}).get(lin):
                    margen_pata = bet["goles"][lin].get("comision", 5.5)
            elif canonico in ("Ambos marcan", "No marcan los dos") and bet.get("ambos_marcan"):
                margen_pata = bet["ambos_marcan"].get("comision", 7.0)
            elif canonico.startswith("Doble oportunidad"):
                margen_pata = 5.0

        margenes_individuales.append(margen_pata)

        pata_info = {
            "partido": d["partido"], "id": pid, "mercado": canonico,
            "nuestro_numero_de_cada_cien": n, "cuota": c, "es_jugador": es_jugador
        }
        if es_jugador:
            pata_info["serie_reciente"] = serie
            pata_info["aciertos_en_serie"] = ("%d de %d partidos" % (aciertos, len(serie))) if serie else "sin serie"
        if nota_pata:
            pata_info["nota"] = nota_pata
        detalle.append(pata_info)

        if not es_jugador:
            por_partido_mercados.setdefault(pid, []).append(canonico)

    # Probabilidad conjunta de partidos de equipo
    prob_equipo, avisos, mismo = 1.0, [], []
    if not por_partido_mercados:
        prob_equipo = None
    else:
        for pid, mercados in por_partido_mercados.items():
            if len(mercados) == 1:
                prob_equipo *= next(d["nuestro_numero_de_cada_cien"] for d in detalle
                                    if d["id"] == pid and d["mercado"] == mercados[0]) / 100.0
                continue
            c_j = _conjunta(pid, mercados)
            nombre_partido = next(d["partido"] for d in detalle if d["id"] == pid)
            if c_j is None:
                avisos.append("En %s hay %d patas y no puedo resolver la "
                              "combinación exacta de esos mercados. NO le des "
                              "un número a esa parte." % (nombre_partido, len(mercados)))
                prob_equipo = None
                break
            ingenua = 1.0
            for m in mercados:
                ingenua *= next(d["nuestro_numero_de_cada_cien"] for d in detalle
                                if d["id"] == pid and d["mercado"] == m) / 100.0
            mismo.append({
                "partido": nombre_partido, "mercados": mercados,
                "juntas_de_cada_cien": _de_cada_cien(c_j),
                "multiplicando_daria": _de_cada_cien(ingenua),
                "por_que": ("Son del mismo partido: se resuelven sobre la matriz "
                            "de marcadores. Multiplicarlas da %d de cada cien y el "
                            "número real es %d."
                            % (_de_cada_cien(ingenua), _de_cada_cien(c_j)))})
            prob_equipo *= c_j

    # Comisión acumulada compuesta de la casa
    margen_compuesto = 1.0
    for mg in margenes_individuales:
        margen_compuesto *= (1 + mg / 100.0)
    margen_total_pct = round((margen_compuesto - 1) * 100, 1)

    hay_jugadores = any(d.get("es_jugador") for d in detalle)

    salida = {
        "patas": detalle,
        "cuota_que_te_pagan": round(cuota_total, 2) if cuota_total > 1 else None,
        "margen_estimado_de_la_casa": margen_total_pct,
        "nota_margen": ("La comisión de la casa se multiplica entre patas: en esta boleta el peaje acumulado de la casa es de %.1f%%." % margen_total_pct),
    }

    if hay_jugadores:
        salida["probabilidad_conjunta_calculable"] = False
        salida["sale_de_cada_cien_veces"] = None
        salida["cuota_justa"] = None
        if prob_equipo is not None and por_partido_mercados:
            salida["probabilidad_patas_equipo_de_cada_cien"] = _de_cada_cien(prob_equipo)
        jugs_nom = ", ".join(d["mercado"] for d in detalle if d.get("es_jugador"))
        salida["aviso_jugador"] = (
            "La boleta incluye mercado(s) de jugador (%s). "
            "VALOR no calcula probabilidad conjunta para combinadas con actuaciones individuales: "
            "dependen de si es titular, minutos de juego, planteo del rival y guion del partido. "
            "La serie histórica de remates es puramente descriptiva y NO debe multiplicarse como probabilidad estadística independiente. "
            "El peaje acumulado que te cobra la casa sí está medido: %.1f%%."
            % (jugs_nom, margen_total_pct)
        )
        patas_equipo = [d for d in detalle if not d.get("es_jugador")]
        if patas_equipo:
            peor = min(patas_equipo, key=lambda d: d.get("nuestro_numero_de_cada_cien") or 100)
            salida["la_pata_mas_arriesgada_del_equipo"] = peor["mercado"] + " — " + peor["partido"]
    else:
        if prob_equipo is None:
            return {"patas": detalle, "error_parcial": avisos,
                    "cuota_que_te_pagan": round(cuota_total, 2) if cuota_total > 1 else None}
        prob = prob_equipo
        fallo_total = 1 - prob
        for d in detalle:
            pp = d["nuestro_numero_de_cada_cien"] / 100.0
            d["cuanto_aporta_al_fallo"] = (
                round((1 - pp) / sum(1 - x["nuestro_numero_de_cada_cien"] / 100.0
                                     for x in detalle) * 100)
                if fallo_total > 0 else 0)

        peor = max(detalle, key=lambda d: d["cuanto_aporta_al_fallo"])
        justa = round(1 / prob, 2) if prob > 0 else None

        salida["probabilidad_conjunta_calculable"] = True
        salida["sale_de_cada_cien_veces"] = _de_cada_cien(prob)
        salida["cuota_justa"] = justa
        salida["la_pata_que_la_hunde"] = peor["mercado"] + " — " + peor["partido"]

        if cuota_total > 1 and justa:
            if cuota_total >= justa:
                ventaja = round((cuota_total - justa) / justa * 100, 1)
                salida["comparacion_con_nuestro_numero"] = {
                    "ventaja_teorica_pct": ventaja,
                    "evaluacion": "A este precio la casa paga %.1f%% por encima de nuestra cuota justa." % ventaja
                }
            else:
                desventaja = round((justa - cuota_total) / justa * 100, 1)
                salida["comparacion_con_nuestro_numero"] = {
                    "desventaja_pct": desventaja,
                    "evaluacion": "A este precio estás pagando %.1f%% de más respecto a nuestra cuota justa." % desventaja
                }

    if mismo:
        salida["patas_del_mismo_partido"] = mismo
    if len(detalle) >= 4:
        salida["nota"] = (
            "Son %d patas. La comisión de la casa se multiplica, no se reparte."
            % len(detalle))
    return salida


def stake(de_cada_cien, cuota, banca=None):
    """Cuánto poner, como fracción de la banca.

        f = (p·b − (1−p)) / b,  con b = cuota − 1

    Es Kelly, y la fórmula está acá entera a propósito: no depende de
    ningún archivo del producto anterior. Se usa **un cuarto** de lo que
    da, con tope, porque Kelly pleno supone que la probabilidad propia es
    correcta — y eso es justo lo que las mediciones de este repo no
    sostienen.
    """
    if banca is None:
        banca = _memoria().get("banca")
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


def desenlace(mercado, marcador):
    """Gana, pierde o nula según el marcador. None si no se deduce de ahí.

    **Es la ÚNICA implementación de esta regla en el proyecto.** Vivía
    duplicada en `cierre.py` y las dos coincidían por casualidad, pero la
    de acá no conocía doble oportunidad ni DNB: como `resolver()` es una
    herramienta del bot, pedirle "resolvé mis apuestas" dejaba esas dos
    abiertas para siempre mientras `cierre.py` sí las cerraba. Dos
    caminos y dos resultados sobre la misma plata.

    Acepta los alias con los que el asesor puede escribir un mercado
    ("gana local", "btts", "1X"), porque el nombre lo redacta un modelo.
    """
    if not marcador or "-" not in str(marcador):
        return None
    try:
        gl, gv = (int(x) for x in str(marcador).split("-"))
    except (ValueError, AttributeError):
        return None

    t = gl + gv
    m = " ".join(str(mercado).lower().replace("á", "a").replace("é", "e")
                 .replace("í", "i").replace("ó", "o").replace("ú", "u").split())

    def _sn(cond):
        return "ganada" if cond else "perdida"

    directos = {
        ("1x2 local", "local", "gana local"): _sn(gl > gv),
        ("1x2 empate", "empate", "x"): _sn(gl == gv),
        ("1x2 visitante", "visitante", "gana visitante"): _sn(gl < gv),
        ("doble oportunidad 1x", "1x", "local o empate"): _sn(gl >= gv),
        ("doble oportunidad x2", "x2", "empate o visitante"): _sn(gv >= gl),
        ("doble oportunidad 12", "12", "local o visitante"): _sn(gl != gv),
        ("ambos marcan", "btts", "gol de ambos"): _sn(gl > 0 and gv > 0),
        ("no marcan los dos", "no ambos marcan"): _sn(not (gl > 0 and gv > 0)),
    }
    for claves, res in directos.items():
        if m in claves:
            return res

    # DNB: el empate devuelve la plata, no la pierde.
    if m in ("dnb local", "empate no cuenta local", "local sin empate"):
        return "nula" if gl == gv else _sn(gl > gv)
    if m in ("dnb visitante", "empate no cuenta visitante", "visitante sin empate"):
        return "nula" if gl == gv else _sn(gv > gl)

    for prefijo, cmp in (("mas de ", lambda l: t > l),
                         ("menos de ", lambda l: t < l)):
        if m.startswith(prefijo):
            try:
                return _sn(cmp(float(m[len(prefijo):].split()[0])))
            except (ValueError, IndexError):
                return None
    return None


# Nombre viejo, por si algo externo lo usaba.
_desenlace = desenlace


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


def _clasificar_factor_apuesta(apuesta):
    """Clasificación conservadora de factores compartidos para una apuesta.

    No inventa correlaciones matemáticas ni modelos de cópulas: identifica
    dimensiones directas y observables de riesgo compartido (guion de goles,
    perfil de cuota, o props individuales).
    """
    m_raw = apuesta.get("mercado", "")
    m = " ".join(str(m_raw).lower().replace("á", "a").replace("é", "e")
                 .replace("í", "i").replace("ó", "o").replace("ú", "u").split())
    try:
        cuota = float(apuesta.get("cuota", 0) or 0)
    except (ValueError, TypeError):
        cuota = 0.0
    try:
        monto = float(apuesta.get("monto", 0) or 0)
    except (ValueError, TypeError):
        monto = 0.0

    # 1. Dirección de goles (macro-guion)
    dir_goles = "otro"
    if any(k in m for k in ("menos de", "under", "no marcan", "no ambos", "ambos no")):
        dir_goles = "baja_anotacion"
    elif any(k in m for k in ("mas de", "over", "ambos marcan", "btts", "gol de ambos")):
        dir_goles = "alta_anotacion"

    # 2. Prop de jugador individual
    es_jugador = False
    if any(k in m for k in ("remate", "remates", "tiro", "tiros", "asistencia", "pase", "pases", "tarjeta", "gol de")):
        es_jugador = True
    elif "jugador" in apuesta:
        es_jugador = True

    return {
        "direccion_goles": dir_goles,
        "es_jugador": es_jugador,
        "cuota": cuota,
        "monto": monto,
    }


def cartera(apuestas_simuladas=None):
    """Evalúa la exposición agregada de la fecha y la concentración de riesgo.

    No calcula correlaciones teóricas no medidas: audita la concentración
    en un mismo partido, el sesgo direccional de goles (Unders vs Overs), la
    dependencia de favoritos y los escenarios de estrés ante trámites adversos.

    Separa estrictamente la exposición real (apuestas abiertas de memoria.json)
    de la potencial (apuestas_simuladas recibidas como argumento).
    """
    mem = _memoria()
    banca_total = mem.get("banca")

    # 1. Carga y consolidación de apuestas
    abiertas = [a for a in mem.get("apuestas", []) if not a.get("resultado")]
    consolidadas = []

    for a in abiertas:
        it = dict(a)
        it["origen"] = "real"
        try:
            it["monto"] = float(it.get("monto") or 0)
        except (ValueError, TypeError):
            it["monto"] = 0.0
        try:
            it["cuota"] = float(it.get("cuota") or 0)
        except (ValueError, TypeError):
            it["cuota"] = 0.0
        it["clasificacion"] = _clasificar_factor_apuesta(it)
        consolidadas.append(it)

    if apuestas_simuladas:
        sims = apuestas_simuladas if isinstance(apuestas_simuladas, list) else [apuestas_simuladas]
        for s in sims:
            if not isinstance(s, dict):
                continue
            it = dict(s)
            it["origen"] = "simulada"
            it.setdefault("resultado", None)
            try:
                it["monto"] = float(it.get("monto") or 0)
            except (ValueError, TypeError):
                it["monto"] = 0.0
            try:
                it["cuota"] = float(it.get("cuota") or 0)
            except (ValueError, TypeError):
                it["cuota"] = 0.0
            if not it.get("partido") and it.get("id_partido"):
                p_match, _ = _buscar_partido(it["id_partido"])
                if p_match:
                    it["partido"] = "%s vs %s" % (p_match.get("home"), p_match.get("away"))
                else:
                    it["partido"] = str(it.get("id_partido") or "desconocido")
            it["clasificacion"] = _clasificar_factor_apuesta(it)
            consolidadas.append(it)

    exp_real = sum(a["monto"] for a in consolidadas if a["origen"] == "real")
    exp_sim = sum(a["monto"] for a in consolidadas if a["origen"] == "simulada")
    exp_total = exp_real + exp_sim
    cant_real = sum(1 for a in consolidadas if a["origen"] == "real")
    cant_sim = sum(1 for a in consolidadas if a["origen"] == "simulada")
    cant_total = cant_real + cant_sim

    pct_real = round(exp_real / banca_total * 100, 1) if (banca_total and banca_total > 0) else None
    pct_sim = round(exp_sim / banca_total * 100, 1) if (banca_total and banca_total > 0) else None
    pct_total = round(exp_total / banca_total * 100, 1) if (banca_total and banca_total > 0) else None

    # Nivel de exposición operativa
    if pct_total is not None:
        if pct_total <= 10.0:
            nivel = "normal (exposición acotada, margen holgado de maniobra)"
        elif pct_total <= 20.0:
            nivel = "moderado (dentro de pautas operativas razonables)"
        else:
            nivel = "elevado (alerta operativa: riesgo de sobreexposición en una misma fecha)"
    else:
        nivel = "indeterminado (sin banca total configurada)"

    if cant_total == 0:
        return {
            "resumen_banca": {
                "banca_total": banca_total,
                "expuesto_real": {"monto": 0, "pct_banca": 0.0, "cantidad_apuestas": 0},
                "expuesto_simulado": {"monto": 0, "pct_banca": 0.0, "cantidad_apuestas": 0},
                "expuesto_total_proyectado": {"monto": 0, "pct_banca": 0.0, "cantidad_apuestas": 0},
                "nivel_exposicion": "sin exposición (cartera vacía)",
            },
            "concentracion_por_partido": [],
            "direccion_goles": {
                "baja_anotacion": {"monto": 0, "pct_goles": 0.0, "cantidad": 0, "apuestas": []},
                "alta_anotacion": {"monto": 0, "pct_goles": 0.0, "cantidad": 0, "apuestas": []},
                "alerta_sesgo": None,
            },
            "props_jugadores": {"monto": 0, "pct_total": 0.0, "cantidad": 0, "aviso": None},
            "escenarios_hipoteticos": [],
            "advertencias": [],
            "nota": "No hay apuestas abiertas ni jugadas simuladas para evaluar.",
        }

    # 2. Concentración por partido / evento
    por_partido_dict = {}
    for a in consolidadas:
        pid = a.get("id_partido") or a.get("partido") or "desconocido"
        pnom = a.get("partido") or pid
        if pid not in por_partido_dict:
            por_partido_dict[pid] = {
                "id_partido": pid,
                "partido": pnom,
                "monto_total": 0,
                "apuestas": [],
                "hay_simulada": False,
            }
        por_partido_dict[pid]["monto_total"] += a.get("monto", 0)
        por_partido_dict[pid]["apuestas"].append({
            "mercado": a.get("mercado"),
            "cuota": a.get("cuota"),
            "monto": a.get("monto"),
            "origen": a.get("origen"),
        })
        if a.get("origen") == "simulada":
            por_partido_dict[pid]["hay_simulada"] = True

    partidos_lista = []
    advertencias = []

    for p in por_partido_dict.values():
        mt = p["monto_total"]
        pct_c = round(mt / exp_total * 100, 1) if exp_total else 0
        pct_b = round(mt / banca_total * 100, 1) if (banca_total and banca_total > 0) else None
        conc = len(p["apuestas"]) > 1
        item_p = {
            "id_partido": p["id_partido"],
            "partido": p["partido"],
            "monto_total": mt,
            "cantidad_apuestas": len(p["apuestas"]),
            "pct_de_cartera": pct_c,
            "pct_de_banca": pct_b,
            "concentracion_evento": conc,
            "apuestas": p["apuestas"],
        }
        partidos_lista.append(item_p)
        if conc:
            origenes = set(ap["origen"] for ap in p["apuestas"])
            extra_sim = " (incluye jugada en evaluación)" if "simulada" in origenes else ""
            advertencias.append(
                "Concentración en un mismo partido%s: tenés %d apuestas en '%s' sumando $%.0f "
                "(%.1f%% de lo expuesto). Ambas quedan atadas al trámite de los mismos 90 minutos."
                % (extra_sim, len(p["apuestas"]), p["partido"], mt, pct_c)
            )

    partidos_lista.sort(key=lambda x: x["monto_total"], reverse=True)

    # 3. Dirección macro de goles
    baja_aps = [a for a in consolidadas if a["clasificacion"]["direccion_goles"] == "baja_anotacion"]
    alta_aps = [a for a in consolidadas if a["clasificacion"]["direccion_goles"] == "alta_anotacion"]
    monto_baja = sum(a.get("monto", 0) for a in baja_aps)
    monto_alta = sum(a.get("monto", 0) for a in alta_aps)
    monto_goles = monto_baja + monto_alta

    pct_goles_baja = round(monto_baja / monto_goles * 100, 1) if monto_goles else 0
    pct_goles_alta = round(monto_alta / monto_goles * 100, 1) if monto_goles else 0

    alerta_goles = None
    if monto_goles > 0 and (len(baja_aps) + len(alta_aps)) >= 2:
        if pct_goles_baja >= 70.0 and len(baja_aps) >= 2:
            alerta_goles = (
                "Fuerte sesgo hacia baja anotación: %.1f%% del capital en goles está en "
                "Unders / No marcan. Si la fecha arranca con goles tempranos, golpea en cadena." % pct_goles_baja
            )
            advertencias.append(alerta_goles)
        elif pct_goles_alta >= 70.0 and len(alta_aps) >= 2:
            alerta_goles = (
                "Fuerte sesgo hacia alta anotación: %.1f%% del capital en goles está en "
                "Overs / Ambos marcan. Una jornada de trámites cerrados arrastra la cartera." % pct_goles_alta
            )
            advertencias.append(alerta_goles)

    # 4. Props de jugadores individuales
    props_aps = [a for a in consolidadas if a["clasificacion"]["es_jugador"]]
    monto_props = sum(a.get("monto", 0) for a in props_aps)
    pct_props = round(monto_props / exp_total * 100, 1) if exp_total else 0
    aviso_props = None
    if props_aps:
        aviso_props = (
            "Hay %d jugadas en props individuales ($%.0f). Dependen de que los "
            "jugadores arranquen de titulares y sumen minutos."
            % (len(props_aps), monto_props)
        )

    # 5. Alerta general de exposición de banca
    if pct_total is not None and pct_total > 20.0:
        advertencias.insert(0,
            "Exposición agregada elevada: el total en juego proyecta el %.1f%% de la banca. "
            "La pauta de gestión operativa recomienda no comprometer más del 15-20%% en una misma fecha."
            % pct_total
        )

    # 6. Escenarios hipotéticos (simulación de qué pasa si...)
    escenarios = []

    def _formatear_afectadas(aps):
        return [{
            "partido": a.get("partido"),
            "mercado": a.get("mercado"),
            "cuota": a.get("cuota"),
            "monto": a.get("monto"),
            "origen": a.get("origen")
        } for a in aps]

    def _severidad(pct_banca_perdida):
        if pct_banca_perdida is None:
            return "indeterminada"
        if pct_banca_perdida < 5.0:
            return "leve"
        if pct_banca_perdida <= 10.0:
            return "moderada"
        return "severa (pone en riesgo la banca)"

    # Escenario A: Fecha abierta con goles
    if baja_aps:
        perdida_a = monto_baja
        pct_b_a = round(perdida_a / banca_total * 100, 1) if (banca_total and banca_total > 0) else None
        escenarios.append({
            "escenario": "Hipotético: fecha con muchos goles",
            "descripcion": "Si los partidos se abren temprano y superan las líneas de gol, caen las jugadas de baja anotación.",
            "capital_en_riesgo": perdida_a,
            "impacto_banca_pct": pct_b_a,
            "severidad": _severidad(pct_b_a),
            "apuestas_afectadas": _formatear_afectadas(baja_aps),
        })

    # Escenario B: Fecha cerrada sin goles
    if alta_aps:
        perdida_b = monto_alta
        pct_b_b = round(perdida_b / banca_total * 100, 1) if (banca_total and banca_total > 0) else None
        escenarios.append({
            "escenario": "Hipotético: fecha trabada sin goles",
            "descripcion": "Si los partidos salen muy cerrados y trabados, caen las selecciones de alta anotación.",
            "capital_en_riesgo": perdida_b,
            "impacto_banca_pct": pct_b_b,
            "severidad": _severidad(pct_b_b),
            "apuestas_afectadas": _formatear_afectadas(alta_aps),
        })

    # Escenario C: Trámite adverso en el partido con mayor exposición
    if partidos_lista and partidos_lista[0]["monto_total"] > 0:
        p_top = partidos_lista[0]
        perdida_c = p_top["monto_total"]
        pct_b_c = round(perdida_c / banca_total * 100, 1) if (banca_total and banca_total > 0) else None
        if len(partidos_lista) > 1 or p_top["concentracion_evento"]:
            escenarios.append({
                "escenario": "Hipotético: tropiezo en '%s'" % p_top["partido"],
                "descripcion": "Si se tuerce el partido donde más capital hay concentrado, caen todas sus jugadas.",
                "capital_en_riesgo": perdida_c,
                "impacto_banca_pct": pct_b_c,
                "severidad": _severidad(pct_b_c),
                "apuestas_afectadas": p_top["apuestas"],
            })

    return {
        "resumen_banca": {
            "banca_total": banca_total,
            "expuesto_real": {"monto": exp_real, "pct_banca": pct_real, "cantidad_apuestas": cant_real},
            "expuesto_simulado": {"monto": exp_sim, "pct_banca": pct_sim, "cantidad_apuestas": cant_sim},
            "expuesto_total_proyectado": {"monto": exp_total, "pct_banca": pct_total, "cantidad_apuestas": cant_total},
            "nivel_exposicion": nivel,
        },
        "concentracion_por_partido": partidos_lista,
        "direccion_goles": {
            "baja_anotacion": {
                "monto": monto_baja,
                "pct_goles": pct_goles_baja,
                "cantidad": len(baja_aps),
                "apuestas": _formatear_afectadas(baja_aps),
            },
            "alta_anotacion": {
                "monto": monto_alta,
                "pct_goles": pct_goles_alta,
                "cantidad": len(alta_aps),
                "apuestas": _formatear_afectadas(alta_aps),
            },
            "alerta_sesgo": alerta_goles,
        },
        "props_jugadores": {
            "monto": monto_props,
            "pct_total": pct_props,
            "cantidad": len(props_aps),
            "aviso": aviso_props,
        },
        "escenarios_hipoteticos": escenarios,
        "advertencias": advertencias,
    }


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
        "cartera": cartera(),
    }


AYUDA = """\
Pronóstic — los datos, sin IA de por medio.

Consultas de partidos:
  python experto/datos.py fecha [AAAA-MM-DD]               qué se juega
  python experto/datos.py <id_partido>                     el expediente completo
  python experto/datos.py historial <id_partido>           forma y cruces anteriores
  python experto/datos.py jugadores <id_partido>           remates y once anterior
  python experto/datos.py movimiento <id_partido> [jugador] cómo varió el precio

Cuentas y combinadas:
  python experto/datos.py stake <de_cada_cien> <cuota> [banca]  cuánto poner (Kelly fraccional)
  python experto/datos.py boleta '<json_patas>'                 analizar combinada

Gestión de banca y registro:
  python experto/datos.py banca                            banca y apuestas abiertas
  python experto/datos.py cartera [json_simuladas]         riesgo de la fecha como cartera
  python experto/datos.py poner_banca <monto>              fijar banca total
  python experto/datos.py anotar <id> <mercado> <cuota> <monto> <quien> [nota]
  python experto/datos.py resolver [id_partido]            liquidar con marcadores

Sirve para mirar datos a mano y para el modo sin clave (ver experto/SIN_CLAVE.md).
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
    elif arg == "cartera":
        simuladas = None
        if len(sys.argv) > 2:
            raw = sys.argv[2].strip()
            try:
                simuladas = json.loads(raw)
            except Exception as e:
                salida = {"error": "no pude parsear apuestas_simuladas: %s" % e}
        if salida is None:
            salida = cartera(simuladas)
    elif arg == "stake":
        if len(sys.argv) < 4:
            salida = {"error": "uso: python experto/datos.py stake <de_cada_cien> <cuota> [banca]"}
        else:
            try:
                p = float(sys.argv[2])
                c = float(sys.argv[3])
                b = float(sys.argv[4]) if len(sys.argv) > 4 else None
                salida = stake(p, c, b)
            except ValueError as e:
                salida = {"error": "número inválido: %s" % e}
    elif arg == "poner_banca":
        if len(sys.argv) < 3:
            salida = {"error": "uso: python experto/datos.py poner_banca <monto>"}
        else:
            try:
                salida = poner_banca(float(sys.argv[2]))
            except ValueError as e:
                salida = {"error": "monto inválido: %s" % e}
    elif arg == "anotar":
        if len(sys.argv) < 7:
            salida = {"error": "uso: python experto/datos.py anotar <id_partido> <mercado> <cuota> <monto> <quien> [nota]"}
        else:
            try:
                nota = sys.argv[7] if len(sys.argv) > 7 else None
                salida = anotar(sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5]), sys.argv[6], nota)
            except ValueError as e:
                salida = {"error": "datos inválidos: %s" % e}
    elif arg == "boleta":
        if len(sys.argv) < 3:
            salida = {"error": "uso: python experto/datos.py boleta '<json_patas>' O python experto/datos.py boleta <id> <mercado> <cuota> ..."}
        else:
            raw = sys.argv[2].strip()
            if raw.startswith("[") or raw.startswith("{"):
                try:
                    patas = json.loads(raw)
                    if isinstance(patas, dict):
                        patas = [patas]
                    salida = revisar_boleta(patas)
                except Exception as e:
                    salida = {"error": "error en boleta: %s" % e}
            else:
                args = sys.argv[2:]
                patas = []
                i = 0
                while i < len(args):
                    if i + 2 < len(args):
                        try:
                            c = float(args[i + 2])
                            patas.append({"id_partido": args[i], "mercado": args[i + 1], "cuota": c})
                            i += 3
                            continue
                        except ValueError:
                            pass
                    if i + 1 < len(args):
                        patas.append({"id_partido": args[i], "mercado": args[i + 1]})
                        i += 2
                    else:
                        break
                if not patas:
                    salida = {"error": "no pude interpretar las patas de la boleta"}
                else:
                    salida = revisar_boleta(patas)
    elif arg == "historial":
        salida = historial(sys.argv[2] if len(sys.argv) > 2 else "")
    elif arg == "jugadores":
        salida = jugadores_partido(sys.argv[2] if len(sys.argv) > 2 else "")
    elif arg == "movimiento":
        jug = sys.argv[3] if len(sys.argv) > 3 else None
        salida = movimiento(sys.argv[2] if len(sys.argv) > 2 else "", jug)
    elif arg == "resolver":
        salida = resolver(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        salida = expediente(arg)
    if salida is not None:
        print(json.dumps(salida, ensure_ascii=False, indent=1))
