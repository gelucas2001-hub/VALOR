#!/usr/bin/env python3
"""Pronóstic — Cierre de apuestas y balance.

Corre a la mañana siguiente para liquidar las apuestas de `memoria.json`:
1. Cruza apuestas abiertas contra `data/resultados.json` y `data/cache_disciplina.json`.
2. Resuelve 1X2, goles y líneas de jugador sin salir a la red (datos locales).
   Si un jugador no está en `_jugadores`, no jugó -> apuesta nula.
3. Evalúa si la entrada fue buena o mala usando CLV (Closing Line Value)
   en puntos de probabilidad implícita (1/cierre - 1/entrada), no opinión del modelo.
4. Mide el acierto discriminado por `quien` (Lucas vs. Pronóstic).
   Con < 50 apuestas, el ROI va después del CLV y con su error estándar (ROI ± SE).

Uso:
    python experto/cierre.py           # Liquida y manda mensaje por Telegram
    python experto/cierre.py --ver     # Muestra el informe en consola sin mandar
    python experto/cierre.py --semana  # Muestra el corte semanal / balance acumulado
"""

import json
import os
import re
import sys
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import datos as D
import bot as B

CAMPOS_JUGADOR = ("remates", "al_arco", "faltas", "amarillas", "goles", "asist", "titular")


def norma(s):
    """Sin acentos, sin apóstrofos, sin guiones, en minúscula.

    Misma normalización estricta que medir_props.py: evita fundir
    jugadores distintos por similitud difusa.
    """
    s = unicodedata.normalize("NFD", str(s)).lower()
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.replace("'", " ").replace("-", " ").split())


def parsear_mercado_jugador(mercado):
    """Extrae jugador, métrica, dirección y línea de un texto de mercado.

    Ejemplos:
        "Matías Fernández más de 2.5 remates"
        "Fernández más de 1.5 al arco"
        "Francisco Álvarez más de 3.5 faltas"
        "Franco Vázquez gol"
    """
    m = norma(mercado)
    metricas = {
        "al_arco": ["al arco", "al_arco", "tiros al arco", "remates al arco",
                    "shots on target", "a puerta", "a arco"],
        "remates": ["remates", "tiros", "shots", "disparos"],
        "faltas": ["faltas", "fouls"],
        "amarillas": ["amarillas", "tarjetas", "yellow cards", "cards"],
        "gol_o_asist": ["gol o asistencia", "marcar o asistir", "score or assist"],
        "goles": ["gol", "goles", "anota", "marca", "marcara", "score"],
        "asist": ["asistencias", "asistencia", "asist", "assists"],
    }
    metrica_hallada = None
    for met, patterns in metricas.items():
        for pat in patterns:
            if pat in m:
                metrica_hallada = met
                break
        if metrica_hallada:
            break

    dir_linea = re.search(r"(mas de|sobre|over|mayor a|\+)\s*(\d+(?:\.\d+)?)", m)
    direccion = "mas"
    linea = None
    if dir_linea:
        direccion = "mas"
        linea = float(dir_linea.group(2))
    else:
        dir_linea = re.search(r"(menos de|bajo|under|menor a|\-)\s*(\d+(?:\.\d+)?)", m)
        if dir_linea:
            direccion = "menos"
            linea = float(dir_linea.group(2))
        elif metrica_hallada in ("goles", "asist", "amarillas", "gol_o_asist"):
            linea = 0.5
            direccion = "mas"

    limpio = m
    if dir_linea:
        limpio = limpio.replace(dir_linea.group(0), "")
    if metrica_hallada:
        for pat in metricas[metrica_hallada]:
            limpio = limpio.replace(pat, "")
    limpio = re.sub(r"[,.\-_/]", " ", limpio).strip()
    nombre_jugador = " ".join(limpio.split())

    return {
        "jugador": nombre_jugador,
        "metrica": metrica_hallada,
        "direccion": direccion,
        "linea": linea,
    }


def buscar_jugador_en_plantel(nombre_buscado, candidatos):
    """Encuentra un jugador en la lista de (id, nombre) del partido.

    Cruce por igualdad exacta o por coincidencia inequívoca de apellido.
    Si hay ambigüedad (dos jugadores comparten apellido), no adivina.
    """
    b = norma(nombre_buscado)
    # 1. Coincidencia exacta de nombre completo normalizado
    for pid, nom in candidatos:
        if b == norma(nom):
            return pid, nom

    # 2. Coincidencia de tokens / apellido inequívoco
    tokens_b = set(b.split())
    coincidencias = []
    for pid, nom in candidatos:
        tokens_nom = set(norma(nom).split())
        if tokens_b and tokens_b.issubset(tokens_nom):
            coincidencias.append((pid, nom))

    if len(coincidencias) == 1:
        return coincidencias[0]
    return None, None


def linea_clavada(id_partido, mercado, cuotas_data, props_data):
    """¿La línea se movió entre la primera foto y la última?

    Si no se movió, un CLV de 0 no significa "elegiste neutro": significa
    que no tenemos con qué opinar. Son dos cosas distintas y el mensaje
    tiene que decirlas distinto.
    """
    info_j = parsear_mercado_jugador(mercado)
    if info_j.get("metrica") and info_j.get("linea") is not None:
        for clave, fotos in (props_data or {}).items():
            if not clave.startswith(id_partido + "__"):
                continue
            partes = clave.split("__", 2)
            if len(partes) != 3 or partes[1] != info_j["metrica"]:
                continue
            if norma(partes[2]) != info_j["jugador"]:
                continue
            if not fotos or len(fotos) < 2:
                return True          # una sola foto: tampoco hay movimiento
            pri = (fotos[0] or {}).get("lineas", {})
            ult = (fotos[-1] or {}).get("lineas", {})
            return all(pri.get(k) == ult.get(k) for k in pri if k in ult)
        return True
    fotos = (cuotas_data or {}).get(id_partido) or []
    if len(fotos) < 2:
        return True
    return all(fotos[0].get(k) == fotos[-1].get(k)
               for k in ("local", "empate", "visitante", "totalOver", "totalUnder")
               if k in fotos[0] and k in fotos[-1])


def obtener_clv(id_partido, mercado, cuota_entrada, cuotas_data, props_data):
    """Calcula el CLV en puntos de probabilidad implícita: 1/cierre - 1/entrada.

    No cociente: pp es simétrico y evita que cuotas largas distorsionen la señal.
    Devuelve (clv_pp, precio_cierre) o (None, None) si no hay foto.

    **"Cierre" es una licencia y conviene no creérsela.** Es la última
    foto que tenemos, y el cron corre 09:00 y 15:00 mientras los partidos
    arrancan hasta las 21:00: puede ser de seis horas antes del pitazo
    (`medir_props.py`). Y si la línea no se movió entre fotos —63 de 96
    en aquella medición— el CLV da 0 **por construcción** y no mide nada;
    `linea_clavada()` distingue ese caso.

    Límite conocido del CLV de goles: `cuotas.json` guarda una sola línea
    de total, la que publica ESPN. Una apuesta a más de 3.5 nunca va a
    tener foto. Las 17 líneas de Bet365 viven en `mercadoExtra`, que no
    acumula historia.
    """
    if not cuota_entrada or cuota_entrada <= 1:
        return None, None

    m_norm = norma(mercado)

    # 1. Mercados de jugador (remates, al arco, faltas)
    info_j = parsear_mercado_jugador(mercado)
    if info_j.get("metrica") and info_j.get("linea") is not None:
        met = info_j["metrica"]
        # Buscar en props_jugadores.json por id_partido__metrica__nombre
        for clave, fotos in (props_data or {}).items():
            if not clave.startswith(id_partido + "__"):
                continue
            partes = clave.split("__", 2)
            if len(partes) != 3:
                continue
            _, met_clave, nom_clave = partes
            if met_clave != met:
                continue
            # IGUALDAD EXACTA, nunca substring. Con `in`, "Celiz" cruzaba
            # con "Milton Celiz" y "ferreira" cruzaría con Clever Ferreira
            # y con Pablo Ferreira a la vez (`medir_props.py`). Un nombre
            # sin cruzar se nota; uno mal cruzado se ve como datos.
            if norma(nom_clave) != info_j["jugador"]:
                continue
            if fotos and isinstance(fotos, list):
                ult_lineas = fotos[-1].get("lineas", {})
                # Buscar la línea exacta o flotante
                for k_ln, v_precio in ult_lineas.items():
                    try:
                        if abs(float(k_ln) - info_j["linea"]) < 1e-4:
                            cierre = float(v_precio)
                            clv_pp = (1.0 / cierre - 1.0 / cuota_entrada) * 100
                            return clv_pp, cierre
                    except (ValueError, TypeError):
                        continue
        # Era una apuesta de jugador y no se encontró su línea. El flujo
        # TERMINA acá: si cayera al bloque de abajo, "más de 1.5 remates"
        # matchearía contra la línea de GOLES del partido y devolvería el
        # precio del over como si fuera el del jugador — un número
        # plausible y falso, que es la peor clase de error.
        return None, None

    # 2. Mercados de partido en cuotas.json (1X2, goles)
    fotos_c = (cuotas_data or {}).get(id_partido)
    if fotos_c and isinstance(fotos_c, list) and len(fotos_c) > 0:
        ult = fotos_c[-1]
        cierre = None
        if "local" in m_norm or "1x2 local" in m_norm:
            cierre = ult.get("local")
        elif "empate" in m_norm or "1x2 empate" in m_norm:
            cierre = ult.get("empate")
        elif "visitante" in m_norm or "1x2 visitante" in m_norm:
            cierre = ult.get("visitante")
        elif "mas de" in m_norm or "menos de" in m_norm:
            tot_linea = ult.get("totalLinea")
            # Si la línea coincide con la cotizada por el cron
            if tot_linea:
                if f"mas de {tot_linea}" in m_norm or f"over {tot_linea}" in m_norm:
                    cierre = ult.get("totalOver")
                elif f"menos de {tot_linea}" in m_norm or f"under {tot_linea}" in m_norm:
                    cierre = ult.get("totalUnder")

        if cierre and cierre > 1:
            clv_pp = (1.0 / cierre - 1.0 / cuota_entrada) * 100
            return clv_pp, cierre

    return None, None


def liquidar_marcador(mercado, marcador):
    """Gana, pierde o nula según el marcador final. None si no se deduce de ahí."""
    if not marcador or "-" not in marcador:
        return None
    try:
        gl, gv = (int(x) for x in marcador.split("-"))
    except (ValueError, AttributeError):
        return None

    m = norma(mercado)
    t = gl + gv

    # 1X2 y ganador
    if m in ("1x2 local", "local", "gana local"):
        return "ganada" if gl > gv else "perdida"
    if m in ("1x2 empate", "empate", "x"):
        return "ganada" if gl == gv else "perdida"
    if m in ("1x2 visitante", "visitante", "gana visitante"):
        return "ganada" if gl < gv else "perdida"

    # Doble oportunidad
    if m in ("doble oportunidad 1x", "1x", "local o empate"):
        return "ganada" if gl >= gv else "perdida"
    if m in ("doble oportunidad x2", "x2", "empate o visitante"):
        return "ganada" if gv >= gl else "perdida"
    if m in ("doble oportunidad 12", "12", "local o visitante"):
        return "ganada" if gl != gv else "perdida"

    # Empate no acción / DNB
    if m in ("dnb local", "empate no cuenta local", "local sin empate"):
        if gl > gv:
            return "ganada"
        if gl < gv:
            return "perdida"
        return "nula"
    if m in ("dnb visitante", "empate no cuenta visitante", "visitante sin empate"):
        if gv > gl:
            return "ganada"
        if gv < gl:
            return "perdida"
        return "nula"

    # Ambos marcan
    if m in ("ambos marcan", "btts", "gol de ambos"):
        return "ganada" if gl > 0 and gv > 0 else "perdida"
    if m in ("no marcan los dos", "no ambos marcan"):
        return "ganada" if not (gl > 0 and gv > 0) else "perdida"

    # Totales de goles
    for prefijo, cmp in (("mas de ", lambda l: t > l),
                         ("menos de ", lambda l: t < l)):
        if m.startswith(prefijo):
            try:
                linea = float(m[len(prefijo):].replace("goles", "").strip())
                return "ganada" if cmp(linea) else "perdida"
            except ValueError:
                return None

    return None


def liquidar_jugador(apuesta, cache_disciplina, planteles):
    """Liquida una apuesta de jugador usando estrictamente cache_disciplina.json.

    Regla dura de TRASPASO: no se usa la serie de planteles (carece de ids/fechas).
    Solo entran a _jugadores quienes jugaron: si no figura, no jugó -> apuesta nula.
    """
    eid = apuesta.get("id_partido", "").replace("espn", "")
    partido_cache = cache_disciplina.get(eid)
    if not partido_cache:
        return None

    jugadores_en_cancha = partido_cache.get("_jugadores", {})
    info_j = parsear_mercado_jugador(apuesta.get("mercado", ""))
    if not info_j["jugador"] or not info_j["metrica"] or info_j["linea"] is None:
        return None

    # Candidatos de ambos equipos en planteles.json
    team_ids = [str(k) for k in partido_cache if not str(k).startswith("_")]
    candidatos = []
    for tid in team_ids:
        for pl in planteles.get("equipos", {}).get(tid, []):
            if pl.get("nombre") and pl.get("id"):
                candidatos.append((str(pl["id"]), pl["nombre"]))

    pid, nom_real = buscar_jugador_en_plantel(info_j["jugador"], candidatos)
    if not pid:
        # No se encontró un jugador inequívoco en el plantel
        return None

    # Si no está en _jugadores, no jugó ningún minuto -> APUESTA NULA
    if pid not in jugadores_en_cancha:
        return {
            "resultado": "nula",
            "devolucion": 0,
            "marcador_final": "%s no jugó (apuesta nula)" % nom_real,
        }

    stats = jugadores_en_cancha[pid]
    # ("remates", "al_arco", "faltas", "amarillas", "goles", "asist", "titular")
    val = 0
    met = info_j["metrica"]
    if met == "gol_o_asist":
        val = stats[4] + stats[5]
    elif met in CAMPOS_JUGADOR:
        val = stats[CAMPOS_JUGADOR.index(met)]
    else:
        return None

    linea = info_j["linea"]
    gano = (val > linea) if info_j["direccion"] == "mas" else (val < linea)
    res = "ganada" if gano else "perdida"
    cuota = float(apuesta.get("cuota", 1.0))
    monto = float(apuesta.get("monto", 0.0))
    dev = round(monto * cuota - monto) if gano else -round(monto)

    return {
        "resultado": res,
        "devolucion": dev,
        "marcador_final": "%d %s (línea %.1f)" % (val, met, linea),
    }


def resolver_apuestas(id_partido=None):
    """Cruza memoria.json contra marcadores y cache_disciplina.json.

    Devuelve (cerradas_en_esta_corrida, siguen_abiertas).
    Guarda atómicamente la memoria si hubo cambios.
    """
    mem = D._memoria()
    res = D._cargar("resultados.json") or {}
    cache_disc = D._cargar("cache_disciplina.json") or {}
    planteles = D._cargar("planteles.json") or {}
    cuotas_data = D._cargar("cuotas.json") or {}
    props_data = D._cargar("props_jugadores.json") or {}

    cerradas_ahora, pendientes = [], []

    for a in mem.get("apuestas", []):
        if a.get("resultado"):
            continue
        if id_partido and a.get("id_partido") != id_partido:
            continue

        pid = a.get("id_partido")
        marcador = res.get(pid)
        eid = pid.replace("espn", "") if pid else ""
        partido_en_cache = eid in cache_disc

        if not marcador and not partido_en_cache:
            pendientes.append({**a, "por_que": "todavía no hay resultado cargado"})
            continue

        solucion = None
        # 1. Intentar liquidar por marcador final (1X2, goles, etc.)
        if marcador:
            res_m = liquidar_marcador(a.get("mercado", ""), marcador)
            if res_m is not None:
                cuota = float(a.get("cuota", 1.0))
                monto = float(a.get("monto", 0.0))
                dev = (round(monto * cuota - monto) if res_m == "ganada"
                       else (0 if res_m == "nula" else -round(monto)))
                solucion = {
                    "resultado": res_m,
                    "devolucion": dev,
                    "marcador_final": marcador,
                }

        # 2. Si no se liquidó por marcador, intentar liquidar por jugador
        if solucion is None and partido_en_cache:
            solucion = liquidar_jugador(a, cache_disc, planteles)

        if solucion is None:
            pendientes.append({**a, "por_que": "no se pudo liquidar automáticamente"})
            continue

        # Medir CLV de la apuesta contra la última foto antes del partido
        clv_pp, cierre = obtener_clv(pid, a.get("mercado", ""),
                                     float(a.get("cuota", 1.0)),
                                     cuotas_data, props_data)

        a["resultado"] = solucion["resultado"]
        a["devolucion"] = solucion["devolucion"]
        a["marcador_final"] = solucion["marcador_final"]
        if clv_pp is not None:
            a["clv_pp"] = round(clv_pp, 2)
            a["cierre"] = round(cierre, 3)
            # Sin movimiento no hay medición, aunque el número dé 0.
            a["linea_clavada"] = linea_clavada(pid, a.get("mercado", ""),
                                               cuotas_data, props_data)

        cerradas_ahora.append(a)

    if cerradas_ahora:
        D._guardar_memoria(mem)

    return cerradas_ahora, pendientes


def calcular_metricas(apuestas):
    """Calcula CLV promedio y ROI con su error estándar (ROI ± SE).

    Misma metodología que medir_props.py.
    """
    cerradas = [a for a in apuestas if a.get("resultado") in ("ganada", "perdida", "nula")]
    decididas = [a for a in cerradas if a.get("resultado") in ("ganada", "perdida")]
    n = len(decididas)
    nulas = len(cerradas) - n
    ganadas = sum(1 for a in decididas if a["resultado"] == "ganada")
    perdidas = n - ganadas

    # CLV
    clvs = [a["clv_pp"] for a in cerradas if a.get("clv_pp") is not None]
    n_clv = len(clvs)
    if n_clv > 0:
        clv_media = sum(clvs) / n_clv
        var_clv = sum((c - clv_media) ** 2 for c in clvs) / n_clv if n_clv > 1 else 0.0
        clv_ee = (var_clv / n_clv) ** 0.5
    else:
        clv_media, clv_ee = None, None

    # ROI con error estándar
    total_apostado = sum(float(a.get("monto", 0.0)) for a in decididas)
    total_retorno = sum(float(a.get("devolucion", 0.0)) for a in cerradas)
    if n > 0 and total_apostado > 0:
        # Ganancia fraccional por apuesta: (devolucion / monto)
        ganancias = [float(a.get("devolucion", 0.0)) / float(a.get("monto", 1.0))
                     for a in decididas]
        media_r = sum(ganancias) / n
        var_r = sum((g - media_r) ** 2 for g in ganancias) / n if n > 1 else 0.0
        ee_r = (var_r / n) ** 0.5 * 100
        roi_pct = media_r * 100
    else:
        roi_pct, ee_r = 0.0, 0.0

    return {
        "total": len(cerradas),
        "decididas": n,
        "ganadas": ganadas,
        "perdidas": perdidas,
        "nulas": nulas,
        "acierto_pct": round(ganadas / n * 100, 1) if n > 0 else 0.0,
        "apostado": round(total_apostado),
        "retorno": round(total_retorno),
        "roi_pct": round(roi_pct, 2),
        "roi_ee": round(ee_r, 2),
        "clv_pp": round(clv_media, 2) if clv_media is not None else None,
        "clv_ee": round(clv_ee, 2) if clv_ee is not None else None,
        "n_clv": n_clv,
    }


def armar_mensaje(cerradas_hoy, balance_semanal=False):
    """Redacta el informe de cierre en voz bar-style.

    Campo 17: evalúa si la entrada fue buena o mala según CLV (aritmética, no opinión).
    Campo 18: con < 50 apuestas, el ROI va después del CLV y con su intervalo ± SE.
    """
    bloques = []

    if cerradas_hoy:
        bloques.append("CIERRE DE APUESTAS")
        for a in cerradas_hoy:
            res = a.get("resultado")
            monto = a.get("monto", 0)
            dev = a.get("devolucion", 0)
            partido = a.get("partido", "Partido")
            mercado = a.get("mercado", "")
            cuota = a.get("cuota", 0)
            clv = a.get("clv_pp")
            cierre = a.get("cierre")
            marcador = a.get("marcador_final", "")

            icono = "✅" if res == "ganada" else ("❌" if res == "perdida" else "⚪")
            plata = ("+$%d" % dev) if dev > 0 else ("-$%d" % abs(dev) if dev < 0 else "$0")

            lineas_a = [
                "%s %s — %s (%s, cuota %.2f)" % (icono, partido, mercado, plata, cuota),
                "   Salió: %s." % marcador,
            ]

            # Juicio por CLV: aritmética sobre la última foto, no opinión.
            # "Última foto" y no "cierre": el cron corre 09:00 y 15:00 y
            # los partidos arrancan hasta las 21:00.
            if clv is None or not cierre:
                lineas_a.append("   No tengo con qué medir si entraste bien.")
            elif a.get("linea_clavada"):
                lineas_a.append(
                    "   La línea no se movió (quedó en %.2f): acá no puedo "
                    "decir si entraste bien o mal." % cierre)
            elif clv > 0.1:
                lineas_a.append(
                    "   Buena entrada: pagaste %.2f y la última foto la tenía "
                    "a %.2f (+%.1f pp a favor)." % (cuota, cierre, clv))
            elif clv < -0.1:
                lineas_a.append(
                    "   Entrada cara: pagaste %.2f y la última foto la tenía "
                    "a %.2f (%.1f pp en contra)." % (cuota, cierre, clv))
            else:
                lineas_a.append(
                    "   Entraste justo al precio de la última foto (%.2f)."
                    % cierre)

            bloques.append("\n".join(lineas_a))

    if balance_semanal:
        mem = D._memoria()
        todas = mem.get("apuestas", [])
        lucas_ap = [a for a in todas if a.get("quien") == "lucas"]
        pron_ap = [a for a in todas if a.get("quien") == "pronostic"]

        m_lucas = calcular_metricas(lucas_ap)
        m_pron = calcular_metricas(pron_ap)

        bloques.append("BALANCE Y CORTE (LUCAS vs PRONÓSTIC)")

        def _formatear_grupo(nombre, m):
            lineas = [
                "**%s** (%d apuestas cerradas: %dG - %dP - %dN):"
                % (nombre, m["total"], m["ganadas"], m["perdidas"], m["nulas"]),
            ]
            if m["decididas"] == 0:
                lineas.append("   Todavía sin apuestas cerradas.")
                return "\n".join(lineas)

            # Si < 50 cerradas: CLV manda, ROI va después y con ± SE
            if m["n_clv"] > 0 and m["clv_pp"] is not None:
                lineas.append("   CLV: %+.2f pp ±%.2f (%d con cierre)"
                              % (m["clv_pp"], m["clv_ee"], m["n_clv"]))
            else:
                lineas.append("   CLV: sin fotos suficientes todavía")

            lineas.append("   ROI: %+.1f%% ±%.1f (retorno neto %s$%d)"
                          % (m["roi_pct"], m["roi_ee"],
                             "+" if m["retorno"] >= 0 else "-", abs(m["retorno"])))

            if m["decididas"] < 50:
                lineas.append("   Poca muestra (%d/50 apuestas) — el ROI es puro ruido, manda el CLV."
                              % m["decididas"])
            return "\n".join(lineas)

        bloques.append(_formatear_grupo("LUCAS", m_lucas))
        bloques.append(_formatear_grupo("PRONÓSTIC", m_pron))

    return "\n\n".join(bloques)


def main():
    ver = "--ver" in sys.argv
    semana = "--semana" in sys.argv

    D.recargar()
    cerradas, pendientes = resolver_apuestas()

    if not cerradas and not semana:
        print("Nada nuevo para cerrar.")
        return

    texto = armar_mensaje(cerradas, balance_semanal=semana)

    if ver:
        print("\n" + texto + "\n")
        return

    chat = D.chat_guardado()
    if not chat:
        print("\nNo sé a qué chat mandarlo. Escribile al bot una vez y queda guardado.\n")
        print(texto)
        return

    B.responder(chat, texto)
    print("Cierre enviado por Telegram.")


if __name__ == "__main__":
    main()
