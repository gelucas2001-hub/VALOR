#!/usr/bin/env python3
"""
VALOR — actualizador de datos
Trae partidos de Liga Profesional, Libertadores, Sudamericana y Copa
Argentina desde la API pública no oficial de ESPN (no necesita key).
Para cada partido futuro calcula los goles esperados (lambda) de cada
equipo a partir del promedio de goles a favor/en contra jugando en su
condición (local de local, visitante de visitante), y adjunta escudos,
historial directo y tabla de posiciones.

Las cuotas NO se traen: se cargan a mano en la app.
"""

import json, sys, datetime, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# site.api.espn.com es el host "oficial" no documentado; algunas redes lo
# bloquean (Akamai). site.web.api.espn.com sirve las mismas respuestas y
# sirve de respaldo automático.
HOSTS = ["https://site.api.espn.com", "https://site.web.api.espn.com"]
SITE_V2 = "apis/site/v2/sports/soccer"      # scoreboard, teams/{id}/schedule
CORE_V2 = "apis/v2/sports/soccer"           # standings
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

OUT = Path("data/partidos.json")
RESULTADOS = Path("data/resultados.json")   # "espn401841517" -> "2-1", en la
                            # perspectiva local-visitante. Se ACUMULA entre
                            # corridas y nunca se borra una clave: es la
                            # memoria de marcadores que el frontend necesita
                            # para resolver el registro de apuestas de forma
                            # exacta. Sin esto, el registro tiene que cruzar
                            # por nombre de rival contra formH/formA, que
                            # funciona pero se equivoca cuando dos equipos se
                            # cruzan más de una vez con el mismo local (fase
                            # de grupos). Sale gratis: los marcadores ya
                            # vienen en el mismo pedido que calibra fuerzas.
CACHE_DISCIPLINA = Path("data/cache_disciplina.json")  # event_id -> {team_id:
                            # {fouls,corners,cards}}. Persiste ENTRE corridas
                            # (a diferencia de todos los otros caches, que
                            # son solo de la corrida actual): /summary pesa
                            # ~400KB por partido — pedirlo de nuevo cada vez
                            # para partidos que ya terminaron hace rato sería
                            # tirar minutos de corrida a la basura. Un evento
                            # ya jugado no cambia, así que cachearlo para
                            # siempre es seguro.
CACHE_LIGAS = Path("data/cache_ligas.json")  # team_id -> slug de su liga local
                            # ("bra.1"). Persiste ENTRE corridas, como
                            # cache_disciplina: un equipo no cambia de liga en
                            # mitad de la temporada, así que preguntarlo una
                            # vez alcanza para siempre.
DISCIPLINA_N = 3           # últimos N partidos por equipo para córners/
                            # faltas/tarjetas — más chico que los 5 de forma()
                            # a propósito, por el costo de /summary.
ARG_TZ = datetime.timezone(datetime.timedelta(hours=-3))
DIAS_ADELANTE = 7          # próximos N días (incluye hoy) — coincide con
                            # los 7 días que muestra la tira en el frontend
TEMPORADAS_H2H = 3         # temporadas hacia atrás para el historial directo
RECENCY_ALPHA = 0.90       # peso por antigüedad en promedio_condicion()
                            # (Copa Argentina, que no tiene fuerzas.py).
                            # 0.90: el partido 13 atrás pesa ~25% del más
                            # reciente. Gentil a propósito — es un ajuste
                            # fino, no un reemplazo del promedio.

# Competiciones con red de cruces suficiente (todos-contra-varios) como
# para calibrar la fuerza de ataque/defensa de cada equipo contra la de
# sus rivales, en vez de solo promediar los partidos propios. Copa
# Argentina es eliminación directa desde el arranque — no hay red de
# cruces repetidos, sigue con el promedio simple.
CON_FUERZAS = {"arg.1", "conmebol.libertadores", "conmebol.sudamericana"}
VIDA_MEDIA_DIAS = 45       # en fuerzas_equipos(): un partido de hace 45
                            # días pesa la mitad que uno de hoy; uno de
                            # hace 90, un cuarto. Por calendario, no por
                            # ronda, porque acá se mezclan los partidos
                            # de todos los equipos a la vez.
MIN_PARTIDOS_FUERZA = 3    # un equipo con menos partidos que esto en toda
                            # la temporada no tiene fuerza confiable
PRIOR_FUERZA = 3           # "partidos fantasma" a nivel promedio (fuerza 1.0)
                            # que se suman en fuerzas_equipos() para regularizar.
                            # Sin esto, un equipo con 1-2 partidos jugados (común
                            # en Libertadores/Sudamericana, que mezclan fases
                            # con muy pocos cruces por equipo) puede terminar
                            # con ataque/defensa disparados a valores absurdos
                            # (probado: sin este freno salió una defensa de
                            # 6.07 en Sudamericana). Con muestra grande (Liga
                            # Profesional, 20+ partidos por equipo) el efecto
                            # es mínimo.

# ── competiciones ────────────────────────────────────────────────
# slug de ESPN → metadata.
#
# rho (corrección Dixon-Coles): arg.1 = +0.05 MEDIDO, no inventado.
# Los valores viejos (-0.10 / -0.14) venían del diseño original sin
# ningún respaldo en datos, y backtest.py mostró que tenían el signo
# equivocado: con -0.10 el modelo predecía 32.4% de empates cuando la
# realidad de la temporada fue 26.7%. Validado fuera de muestra —
# eligiendo rho con los primeros 162 partidos y evaluando en 108 que el
# ajuste nunca vio, +0.05 da Brier 0.22344 contra 0.22581 de -0.10, y
# la mejora es monótona en ambos conjuntos.
#
# Las copas quedan en 0.00 (Poisson sin corrección): NO están validadas
# — con 52-56 partidos evaluables no alcanza para ajustar nada. Se pone
# el neutro en vez del negativo original porque la única competición que
# sí se pudo medir dice que ese negativo estaba mal. Recalibrar cuando
# haya más temporada jugada.
COMPETICIONES = {
    "arg.1": {"nombre": "Liga Profesional Argentina", "rho": 0.05, "conf": 75,
              "corners": 9.4, "fouls": 25.5, "cards": 5.4},
    "conmebol.libertadores": {"nombre": "CONMEBOL Libertadores", "rho": 0.00, "conf": 65,
              "corners": 9.8, "fouls": 24.0, "cards": 5.0},
    "conmebol.sudamericana": {"nombre": "CONMEBOL Sudamericana", "rho": 0.00, "conf": 65,
              "corners": 9.6, "fouls": 24.5, "cards": 5.2},
    "arg.copa": {"nombre": "Copa Argentina", "rho": 0.00, "conf": 60,
              "corners": 9.0, "fouls": 26.0, "cards": 5.6},
}

_req_count = 0

def api(path):
    """GET a la API de ESPN. Prueba site.api.espn.com y si falla cae a
    site.web.api.espn.com."""
    global _req_count
    last_err = None
    for host in HOSTS:
        _req_count += 1
        r = Request(f"{host}/{path}", headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urlopen(r, timeout=25) as resp:
                d = json.loads(resp.read().decode())
            time.sleep(0.2)
            return d
        except (HTTPError, URLError) as e:
            last_err = e
            continue
    print(f"  ! error en {path}: {last_err}", file=sys.stderr)
    return {}


def fecha_hora_arg(iso_utc):
    """'2026-08-14T23:30Z' → ('2026-08-14', '20:30') en hora argentina."""
    dt = datetime.datetime.strptime(iso_utc, "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc)
    local = dt.astimezone(ARG_TZ)
    return local.date().isoformat(), local.strftime("%H:%M")


def americana_a_decimal(cuota):
    """Cuota americana ('-140','+250') a decimal ('1.71','3.50')."""
    try:
        am = float(cuota)
    except (TypeError, ValueError):
        return None
    return round(1 + am / 100, 2) if am > 0 else round(1 + 100 / abs(am), 2)


def mercado_referencia(comp):
    """Cuota de mercado que trae ESPN (DraftKings) en el propio scoreboard
    — cero requests extra. OJO: DraftKings no opera en Argentina, esto NO
    es una cuota apostable acá. Es solo una referencia para comparar contra
    lo que ofrece tu casa real y detectar precios raros — nunca reemplaza
    la carga manual."""
    o = next((x for x in (comp.get("odds") or []) if isinstance(x, dict) and x.get("provider")), None)
    if not o:
        return None

    def cierre(rama):
        return americana_a_decimal((rama or {}).get("close", {}).get("odds"))

    ml = o.get("moneyline") or {}
    ps = o.get("pointSpread") or {}
    tot = o.get("total") or {}

    def linea(rama, prefijo=""):
        s = (rama or {}).get("close", {}).get("line", "")
        try:
            return float(s[len(prefijo):]) if s else None
        except ValueError:
            return None

    ref = {
        "prov": o["provider"].get("name", ""),
        "local": cierre(ml.get("home")), "empate": cierre(ml.get("draw")),
        "visitante": cierre(ml.get("away")),
        "totalLinea": linea(tot.get("over"), "o"),
        "totalOver": cierre(tot.get("over")), "totalUnder": cierre(tot.get("under")),
        "hcapLinea": linea(ps.get("home")),
        "hcapLocal": cierre(ps.get("home")), "hcapVisitante": cierre(ps.get("away")),
    }
    return ref if any(v is not None for k, v in ref.items() if k != "prov") else None


def escudo(team):
    """El logo viene como 'logo' (scoreboard) o 'logos':[{href}] (standings)."""
    if team.get("logo"):
        return team["logo"]
    for l in team.get("logos") or []:
        if "dark" not in (l.get("rel") or []):
            return l.get("href")
    return ""


def historial(slug, team_id, season=None):
    """/teams/{id}/schedule: partidos ya jugados, con condición, goles y rival.
    season=None trae la temporada en curso."""
    q = f"{SITE_V2}/{slug}/teams/{team_id}/schedule"
    if season:
        q += f"?season={season}"
    d = api(q)
    jugados = []
    for e in d.get("events", []):
        comp = (e.get("competitions") or [{}])[0]
        st = comp.get("status", {}).get("type", {})
        if not st.get("completed"):
            continue
        competidores = comp.get("competitors", [])
        propio = next((c for c in competidores if c.get("team", {}).get("id") == str(team_id)), None)
        rival  = next((c for c in competidores if c.get("team", {}).get("id") != str(team_id)), None)
        if not propio or not rival:
            continue
        gf = (propio.get("score") or {}).get("value")
        gc = (rival.get("score") or {}).get("value")
        if gf is None or gc is None:
            continue
        local = propio.get("homeAway") == "home"
        gh, ga = (gf, gc) if local else (gc, gf)
        jugados.append({
            "fecha": e.get("date", ""),
            "id": e.get("id", ""),
            "local": local,
            "gf": gf, "gc": gc,
            "rival_id": rival.get("team", {}).get("id", ""),
            "home": propio["team"]["displayName"] if local else rival["team"]["displayName"],
            "away": rival["team"]["displayName"] if local else propio["team"]["displayName"],
            "marcador": f"{int(gh)}-{int(ga)}",
        })
    jugados.sort(key=lambda x: x["fecha"], reverse=True)
    return jugados


def liga_domestica(team_id, slug_consulta, cache):
    """Slug de la liga local del equipo, vía el campo defaultLeague.

    Hace falta porque /teams/{id}/schedule bajo el slug de una copa
    devuelve SOLO los partidos de esa copa (verificado: Palmeiras da 7
    eventos bajo conmebol.libertadores y 23 bajo bra.1). Para saber
    cuánto vale un equipo necesitamos su liga, donde sí tiene muestra.

    Devuelve None si ESPN no informa defaultLeague; el llamador debe
    seguir andando sin ancla en ese caso.
    """
    clave = str(team_id)
    if clave in cache:
        return cache[clave]          # puede ser None cacheado: no reintentar
    slug = None
    try:
        d = api(f"{SITE_V2}/{slug_consulta}/teams/{team_id}")
        slug = ((d.get("team") or {}).get("defaultLeague") or {}).get("slug")
    except Exception:
        return None                  # error de red: NO cachear, reintentar luego
    cache[clave] = slug
    return slug


def promedio_condicion(jugados, local):
    """Promedio de goles a favor/en contra restringido a los partidos
    jugados en la condición pedida (local=True → de local), ponderado por
    recencia: cada partido pesa RECENCY_ALPHA^antigüedad (0 = el más
    reciente). Se rankea por antigüedad relativa, no por fecha calendario,
    para que copas con fechas espaciadas no distorsionen el decaimiento.
    Con pocos partidos el efecto es chico casi por definición (poco donde
    aplicar el descuento); con historial largo sí pesa la forma actual."""
    sub = [p for p in jugados if p["local"] == local]
    if not sub:
        return None
    pesos = [RECENCY_ALPHA ** i for i in range(len(sub))]
    tot = sum(pesos)
    gf = sum(p["gf"] * w for p, w in zip(sub, pesos)) / tot
    gc = sum(p["gc"] * w for p, w in zip(sub, pesos)) / tot
    return gf, gc, len(sub)


def fecha_corta(iso):
    """La fecha de ESPN (ISO) a DD/MM/AA. Un solo formato de fecha en todo
    lo que sale hacia el análisis: si conviven dos, el que lee tiene que
    adivinar cuál es cuál."""
    d = (iso or "")[:10]
    return f"{d[8:10]}/{d[5:7]}/{d[2:4]}" if len(d) == 10 else ""


def forma(jugados, n=5):
    """Últimos n partidos con contra quién, de local o visitante, y el
    resultado — no solo la letra W/D/L, así se puede juzgar si esa forma
    fue floja porque perdió con candidatos o porque le fue mal con
    cualquiera.

    Con fecha, porque sin ella la forma flota: cinco partidos pueden ser
    cinco semanas o cinco meses, y eso cambia por completo si "viene de
    tres derrotas" describe un momento o media temporada. En copas de
    llave la diferencia es enorme."""
    out = []
    for p in jugados[:n]:
        r = "W" if p["gf"] > p["gc"] else ("D" if p["gf"] == p["gc"] else "L")
        rival = p["away"] if p["local"] else p["home"]
        out.append({
            "d": fecha_corta(p.get("fecha")),
            "r": r, "rival": rival, "local": p["local"],
            "marcador": f'{int(p["gf"])}-{int(p["gc"])}',
        })
    return out


def forma_general(*listas_jugados, n=5):
    """Los últimos n partidos de un equipo sin importar torneo — la fecha
    manda, no la competencia.

    Existe porque una copa de baja frecuencia (fase de grupos de
    Sudamericana, por ejemplo) deja la forma de ESA competencia con meses
    de antigüedad mientras el equipo sigue jugando cada semana en otro
    lado. La API no tiene una ruta que traiga el historial de un equipo
    sin scope de competencia (probado contra site.api.espn.com:
    /teams/{id}/schedule sin slug da 404 Not Found), así que se arma
    juntando el historial ya pedido de cada competencia por separado."""
    todos = [j for lista in listas_jugados for j in lista]
    todos.sort(key=lambda p: p.get("fecha") or "", reverse=True)
    return forma(todos, n)


def tabla_competicion(slug, season):
    """/standings: devuelve {team_id: [filas del grupo]} para poder mostrar
    la zona del equipo que juega. En liga sin grupos ESPN igual devuelve
    'children', así que el manejo es el mismo."""
    d = api(f"{CORE_V2}/{slug}/standings?season={season}")
    por_equipo = {}
    for grupo in d.get("children", []) or []:
        entries = (grupo.get("standings") or {}).get("entries") or []
        filas, ids = [], []
        for e in entries:
            t = e.get("team", {})
            s = {x.get("name"): x for x in e.get("stats", [])}
            val = lambda k: int((s.get(k) or {}).get("value") or 0)
            filas.append({
                "t": t.get("displayName", ""),
                "id": t.get("id", ""),
                "logo": escudo(t),
                "pts": val("points"), "pj": val("gamesPlayed"),
                "g": val("wins"), "e": val("ties"), "p": val("losses"),
                "gf": val("pointsFor"),
            })
            ids.append(t.get("id", ""))
        filas.sort(key=lambda f: (-f["pts"], -f["gf"]))
        info = {"grupo": grupo.get("name", ""), "filas": filas}
        for i in ids:
            por_equipo[i] = info
    return por_equipo


def resumen_partido(slug, event_id):
    """/summary?event=: córners ganados, faltas cometidas y tarjetas de
    cada equipo en ESE partido puntual. No hay versión masiva de esto
    (a diferencia del scoreboard con goles) — es un pedido por partido,
    por eso solo se pide para los últimos partidos de los equipos que
    juegan esta semana, no para toda la temporada."""
    d = api(f"{SITE_V2}/{slug}/summary?event={event_id}")
    # Distinguir "ESPN respondió pero no tiene stats de ese partido" (out
    # vacío o con None → cachear, no va a cambiar nunca) de "el pedido
    # falló" (devuelve None → NO cachear, hay que reintentar la próxima).
    # Sin esto, un error de red pasajero envenenaba el caché persistente
    # para siempre: ese partido no se volvía a pedir nunca más.
    if not d or "boxscore" not in d:
        return None
    out = {}
    for t in (d.get("boxscore") or {}).get("teams", []) or []:
        tid = t.get("team", {}).get("id", "")
        s = {x.get("name"): x.get("displayValue") for x in t.get("statistics", [])}
        def num(k):
            try:
                return float(s.get(k))
            except (TypeError, ValueError):
                return None
        out[tid] = {"fouls": num("foulsCommitted"), "corners": num("wonCorners"),
                    "cards": (num("yellowCards") or 0) + (num("redCards") or 0)}
    return out


def disciplina_equipo(slug, team_id, jugados, cache_resumen, n=DISCIPLINA_N):
    """Promedio de córners ganados / faltas cometidas / tarjetas propias
    en los últimos n partidos jugados. Un pedido por partido (cacheado
    por event id, así dos equipos que ya se cruzaron entre sí no pagan
    el mismo partido dos veces)."""
    corners, fouls, cards, cuenta = 0.0, 0.0, 0.0, 0
    for p in jugados[:n]:
        eid = p.get("id")
        if not eid:
            continue
        if eid not in cache_resumen:
            r = resumen_partido(slug, eid)
            if r is None:      # pedido fallido: no cachear, reintentar la próxima
                continue
            cache_resumen[eid] = r
        datos = cache_resumen[eid].get(str(team_id))
        if not datos or datos["fouls"] is None or datos["corners"] is None:
            continue
        corners += datos["corners"]; fouls += datos["fouls"]; cards += datos["cards"]
        cuenta += 1
    if cuenta == 0:
        return None
    return corners/cuenta, fouls/cuenta, cards/cuenta, cuenta


def resultados_temporada(slug, season, hoy):
    """Todos los partidos ya jugados de la competición en esta temporada,
    en un solo pedido (ESPN deja subir el límite con &limit=). Es la data
    cruda para calibrar fuerzas.py — de acá sale con quién jugó cada
    equipo y con qué resultado, no solo contra los dos de hoy.

    El rango se corta al 31/12 de la temporada pedida: ESPN devuelve 400
    si el rango pasa del año, así que pedir una temporada vieja con
    hasta=hoy fallaba en silencio y devolvía cero partidos."""
    desde = f"{season}0101"
    fin_temporada = datetime.date(season, 12, 31)
    hasta = min(hoy, fin_temporada).strftime("%Y%m%d")
    d = api(f"{SITE_V2}/{slug}/scoreboard?dates={desde}-{hasta}&limit=1000")
    partidos = []
    for ev in d.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        st = comp.get("status", {}).get("type", {})
        if not st.get("completed"):
            continue
        competidores = comp.get("competitors", [])
        loc = next((c for c in competidores if c.get("homeAway") == "home"), None)
        vis = next((c for c in competidores if c.get("homeAway") == "away"), None)
        if not loc or not vis:
            continue
        # OJO: acá "score" viene como string plano ("2"), no como el
        # objeto {"value":...} que da /teams/{id}/schedule — son dos
        # formas de la API con la misma info representada distinto.
        try:
            gh = float(loc.get("score"))
            ga = float(vis.get("score"))
        except (TypeError, ValueError):
            continue
        try:
            fecha = datetime.datetime.strptime(ev["date"], "%Y-%m-%dT%H:%MZ").date()
        except ValueError:
            continue
        partidos.append({
            "fecha": fecha, "home": loc["team"]["id"], "away": vis["team"]["id"],
            "gh": gh, "ga": ga,
            # el id del evento no lo usa el ajuste de fuerzas, pero sirve para
            # cruzar contra los pronósticos ya registrados (registrar_pronosticos)
            "id": ev.get("id", ""),
        })
    return partidos


def fuerzas_equipos(resultados, hoy, anclas=None):
    """Ataque/defensa de cada equipo, calibrados juntos contra toda la red
    de cruces de la temporada (no cada uno contra su propia muestra
    suelta) — el ajuste que le faltaba al promedio simple. Pondera cada
    partido por antigüedad en días (VIDA_MEDIA_DIAS), así un resultado de
    hace un mes sigue contando pero mucho menos que uno de la semana
    pasada. Devuelve (fuerzas, mu_local, mu_visita, partidos_por_equipo);
    fuerzas = {team_id: (ataque, defensa)}, ambos alrededor de 1.0 = nivel
    promedio de la competición; >1 ataque fuerte / <1 defensa débil.

    anclas: {team_id: (ataque, defensa)} — hacia dónde empujan los
    PRIOR_FUERZA partidos fantasma. Sin ancla un equipo con poca muestra
    se va hacia 1.0, el promedio de ESTA competición, que en copas es
    justamente el problema: hace ver parecidos a Palmeiras y a un equipo
    chico, y ahí la localía termina decidiendo el partido. Con ancla se va
    hacia lo que ese equipo vale en su liga local. Sin el parámetro, el
    cálculo queda idéntico al de siempre."""
    if not resultados:
        return {}, 1.0, 1.0, {}

    pesos = [0.5 ** ((hoy - p["fecha"]).days / VIDA_MEDIA_DIAS) for p in resultados]
    w_home = sum(pesos)
    mu_local  = sum(p["gh"] * w for p, w in zip(resultados, pesos)) / w_home
    mu_visita = sum(p["ga"] * w for p, w in zip(resultados, pesos)) / w_home

    equipos = set()
    for p in resultados:
        equipos.add(p["home"]); equipos.add(p["away"])
    partidos_por_equipo = {t: 0 for t in equipos}
    for p in resultados:
        partidos_por_equipo[p["home"]] += 1
        partidos_por_equipo[p["away"]] += 1

    ataque  = {t: 1.0 for t in equipos}
    defensa = {t: 1.0 for t in equipos}

    anc = anclas or {}
    for _ in range(40):
        # PRIOR_FUERZA "partidos fantasma": no mueven la razón de un equipo
        # con muestra grande, pero empujan a uno con 1-2 partidos reales en
        # vez de dejarlo irse a un extremo. num = PRIOR * ancla y den =
        # PRIOR, así que sin partidos reales la razón da exactamente el
        # ancla; sin ancla, ancla = 1.0 y queda el comportamiento de antes.
        num_a = {t: PRIOR_FUERZA * anc.get(t, (1.0, 1.0))[0] for t in equipos}
        den_a = {t: PRIOR_FUERZA for t in equipos}
        for p, w in zip(resultados, pesos):
            num_a[p["home"]] += w * p["gh"]; den_a[p["home"]] += w * mu_local  * defensa[p["away"]]
            num_a[p["away"]] += w * p["ga"]; den_a[p["away"]] += w * mu_visita * defensa[p["home"]]
        nueva_ataque = {t: (num_a[t]/den_a[t] if den_a[t] > 0 else 1.0) for t in equipos}

        num_d = {t: PRIOR_FUERZA * anc.get(t, (1.0, 1.0))[1] for t in equipos}
        den_d = {t: PRIOR_FUERZA for t in equipos}
        for p, w in zip(resultados, pesos):
            num_d[p["home"]] += w * p["ga"]; den_d[p["home"]] += w * mu_visita * nueva_ataque[p["away"]]
            num_d[p["away"]] += w * p["gh"]; den_d[p["away"]] += w * mu_local  * nueva_ataque[p["home"]]
        nueva_defensa = {t: (num_d[t]/den_d[t] if den_d[t] > 0 else 1.0) for t in equipos}

        # renormalizar a media 1: si no, ataque y defensa derivan juntos
        # (subir todos los ataques y bajar todas las defensas explica los
        # mismos goles igual de bien, así que hay que fijar la escala).
        m_a = sum(nueva_ataque.values())/len(nueva_ataque)
        m_d = sum(nueva_defensa.values())/len(nueva_defensa)
        ataque  = {t: v/m_a for t, v in nueva_ataque.items()}
        defensa = {t: v/m_d for t, v in nueva_defensa.items()}

    fuerzas = {t: (ataque[t], defensa[t]) for t in equipos}
    return fuerzas, mu_local, mu_visita, partidos_por_equipo


MIN_PARTIDOS_ANCLA = 8     # partidos en la liga local para que el ancla valga.
                            # Más exigente que MIN_PARTIDOS_FUERZA (3) porque el
                            # ancla se propaga a todos los partidos de copa de
                            # ese equipo: si está mal, contamina más.
FACTORES_LIGA = Path("data/factores_liga.json")   # lo genera calibrar_ligas.py
HISTORIAL_PRON = Path("data/historial_pronosticos.json")  # qué dijimos nosotros y
                            # qué decía la línea, por partido. Crece con el
                            # tiempo; nunca se borra. Es la única forma de medir
                            # copas, donde no hay dataset histórico de cuotas.


def factores_liga():
    """Cuánto vale cada liga, para poder comparar fuerzas entre países.

    Sin esto el ancla compara peras con manzanas: un 1.30 de ataque en
    Brasil y un 1.30 en Paraguay se tratarían igual. Medido: el ancla sin
    factores solo bajó 1.3pp el sesgo de Libertadores y empeoró
    Sudamericana. Los factores salen de calibrar_ligas.py, que los estima
    con 805 cruces de copa entre países de tres temporadas.

    Si el archivo no existe, devuelve {} y todo funciona como si cada liga
    valiera 1.0 — o sea, el comportamiento anterior.
    """
    if not FACTORES_LIGA.exists():
        return {}
    try:
        return json.loads(FACTORES_LIGA.read_text(encoding="utf-8")).get("factores", {})
    except Exception:
        return {}


def ancla_de(team_id, slug_consulta, season, hoy, cache_ligas, cache_dom, factores=None):
    """(ataque, defensa) del equipo en SU liga local, o None.

    Es el valor hacia el que la regularización va a empujar a este equipo
    en la copa, en vez de empujarlo a 1.0 (el promedio de la copa). Un
    equipo con 6 partidos de Libertadores no tiene fuerza medible ahí,
    pero sí tiene ~23 en su liga: por eso el modelo hoy cree que Palmeiras
    y un equipo chico son parecidos, y la localía termina decidiendo.

    Devuelve None (y el llamador cae al comportamiento viejo) cuando no
    se conoce la liga, la liga no responde, o el equipo tiene menos de
    MIN_PARTIDOS_ANCLA partidos en ella.
    """
    slug_liga = liga_domestica(team_id, slug_consulta, cache_ligas)
    if not slug_liga or slug_liga == slug_consulta:
        return None            # ya lo estamos ajustando en esa misma competición

    if slug_liga not in cache_dom:
        try:
            print(f"  · fuerza doméstica — {slug_liga}")
            resultados = resultados_temporada(slug_liga, season, hoy)
            cache_dom[slug_liga] = fuerzas_equipos(resultados, hoy)
        except Exception:
            cache_dom[slug_liga] = ({}, 1.0, 1.0, {})   # liga que no responde
    fuerzas, _mu_l, _mu_v, pj = cache_dom[slug_liga]

    if pj.get(str(team_id), 0) < MIN_PARTIDOS_ANCLA:
        return None
    par = fuerzas.get(str(team_id))
    if not par:
        return None

    # Pasar la fuerza a una vara común entre países. Sin esto, el ataque
    # de Palmeiras (relativo a Brasil) y el de Cerro (relativo a Paraguay)
    # se comparan como si fueran lo mismo. Un ataque vale más si viene de
    # una liga fuerte; una defensa del mismo modo, por eso divide.
    q = (factores or {}).get(slug_liga, 1.0)
    ataque, defensa = par
    return (ataque * q, defensa / q)


def registrar_pronosticos(partidos, season, hoy, traer_resultados=None):
    """Guarda, por partido, qué probabilidad implicaba la línea y con qué
    λ pronosticamos nosotros — y resuelve los que ya se jugaron.

    Existe porque ESPN borra las cuotas cuando el partido termina: si no
    las capturamos ahora, después no hay forma de saber qué decía el
    mercado. Para Liga Profesional hay dataset histórico (ver
    medir_vs_mercado.py), pero para copas esto es la única fuente posible.

    Guarda λ y rho en vez de la probabilidad ya calculada: así, si mañana
    cambia la fórmula, se puede recalcular qué habríamos dicho con el
    modelo de hoy sobre partidos viejos.
    """
    hist = {}
    if HISTORIAL_PRON.exists():
        try:
            hist = json.loads(HISTORIAL_PRON.read_text(encoding="utf-8"))
        except Exception:
            hist = {}

    nuevos = 0
    for m in partidos:
        mk = m.get("mercado")
        if m["id"] in hist or not mk or not mk.get("local"):
            continue
        crudas = [1 / mk["local"], 1 / mk["empate"], 1 / mk["visitante"]]
        tot = sum(crudas)
        hist[m["id"]] = {
            "fecha": m["date"], "comp": m["comp"],
            "home": m["home"], "away": m["away"],
            "lh": m["lh"], "la": m["la"], "rho": m["rho"],
            "mercado": [round(x / tot, 4) for x in crudas],   # ya sin margen
            "cuotas": [mk["local"], mk["empate"], mk["visitante"]],
            "resultado": None,
        }
        nuevos += 1

    # Resolver los pendientes: un pedido por competición, no uno por partido.
    pendientes = [k for k, v in hist.items() if v["resultado"] is None]
    resueltos_ahora = 0
    if pendientes:
        slug_de = {meta["nombre"]: slug for slug, meta in COMPETICIONES.items()}
        por_comp = {}
        for k in pendientes:
            por_comp.setdefault(hist[k]["comp"], []).append(k)
        for comp, claves in por_comp.items():
            slug = slug_de.get(comp)
            if not slug:
                continue
            try:
                # `traer_resultados` viene de main con los resultados ya
                # pedidos para calibrar fuerzas y para data/resultados.json.
                # Sin eso, esta función volvía a pedir la temporada completa
                # de cada competición — hasta cuatro pedidos repetidos por
                # corrida, con la respuesta idéntica.
                crudos = (traer_resultados(slug) if traer_resultados
                          else resultados_temporada(slug, season, hoy))
                jugados = {f"espn{p['id']}": p for p in crudos}
            except Exception:
                continue
            for k in claves:
                p = jugados.get(k)
                if p:
                    hist[k]["resultado"] = [int(p["gh"]), int(p["ga"])]
                    resueltos_ahora += 1

    HISTORIAL_PRON.write_text(json.dumps(hist, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    total_resueltos = sum(1 for v in hist.values() if v["resultado"])
    print(f"· pronósticos: {len(hist)} registrados (+{nuevos} nuevos) · "
          f"{total_resueltos} resueltos (+{resueltos_ahora})")


def main():
    hoy = datetime.date.today()
    ventana = {(hoy + datetime.timedelta(days=i)).isoformat() for i in range(DIAS_ADELANTE)}
    # margen de un día a cada lado: la fecha UTC de ESPN puede correrse
    # respecto al día calendario argentino en partidos nocturnos.
    desde = (hoy - datetime.timedelta(days=1)).strftime("%Y%m%d")
    hasta = (hoy + datetime.timedelta(days=DIAS_ADELANTE)).strftime("%Y%m%d")
    season = hoy.year

    partidos = []
    cache_hist = {}    # (slug, team_id, season) -> jugados
    cache_tabla = {}   # slug -> {team_id: info de grupo}

    def get_hist(slug, tid, yr=None):
        k = (slug, tid, yr)
        if k not in cache_hist:
            cache_hist[k] = historial(slug, tid, yr)
        return cache_hist[k]

    def get_hist_general(tid):
        # Un pedido por competencia que seguimos, no por partido: si el
        # equipo ya se consultó en su propio slug (jug_loc/jug_vis, más
        # abajo) esa llamada se recicla vía cache_hist. Las que no
        # participa devuelven lista vacía y forma_general las ignora sola.
        return [get_hist(s, tid) for s in COMPETICIONES]

    def get_tabla(slug):
        if slug not in cache_tabla:
            cache_tabla[slug] = tabla_competicion(slug, season)
        return cache_tabla[slug]

    cache_fuerzas = {}   # slug -> (fuerzas, mu_local, mu_visita, partidos_por_equipo)
    cache_dom = {}       # slug de liga local -> lo mismo, para las anclas
    factores = factores_liga()   # cuánto vale cada liga, para comparar entre países
    cache_ligas = {}     # team_id -> slug de su liga local (persiste en disco)
    if CACHE_LIGAS.exists():
        try:
            cache_ligas = json.loads(CACHE_LIGAS.read_text(encoding="utf-8"))
        except Exception:
            cache_ligas = {}

    # Los resultados crudos de la temporada se piden UNA vez por competición
    # y se reusan: los usa la calibración de fuerzas y también la memoria de
    # marcadores de data/resultados.json. Antes esto vivía adentro de
    # get_fuerzas y no se podía reusar sin repetir el pedido.
    cache_resultados = {}

    def get_resultados(slug):
        if slug not in cache_resultados:
            cache_resultados[slug] = resultados_temporada(slug, season, hoy)
        return cache_resultados[slug]

    def get_fuerzas(slug):
        if slug not in cache_fuerzas:
            print(f"  · calibrando fuerzas de ataque/defensa — {slug}")
            resultados = get_resultados(slug)
            # Ancla: cada equipo se regulariza hacia lo que vale en su liga
            # local, no hacia el promedio de esta copa. En arg.1 no aplica
            # (la liga local ES esta competición) y ancla_de devuelve None.
            equipos = {p["home"] for p in resultados} | {p["away"] for p in resultados}
            anclas = {}
            for tid in equipos:
                a = ancla_de(tid, slug, season, hoy, cache_ligas, cache_dom, factores)
                if a:
                    anclas[tid] = a
            if anclas:
                print(f"    ancladas {len(anclas)} de {len(equipos)} fuerzas a la liga local")
            cache_fuerzas[slug] = fuerzas_equipos(resultados, hoy, anclas=anclas)
        return cache_fuerzas[slug]

    # cache_resumen persiste ENTRE corridas (a diferencia de cache_hist/
    # cache_fuerzas, que son solo de esta corrida): un partido ya jugado no
    # cambia, y /summary es pesado — no tiene sentido repagarlo cada vez.
    cache_resumen = {}
    if CACHE_DISCIPLINA.exists():
        try:
            cache_resumen = json.loads(CACHE_DISCIPLINA.read_text(encoding="utf-8"))
        except Exception:
            cache_resumen = {}
    resumenes_antes = len(cache_resumen)

    for slug, meta in COMPETICIONES.items():
        print(f"· {meta['nombre']} — scoreboard")
        d = api(f"{SITE_V2}/{slug}/scoreboard?dates={desde}-{hasta}")
        comp_logo = escudo((d.get("leagues") or [{}])[0])
        for ev in d.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            st = comp.get("status", {}).get("type", {})
            if st.get("state") != "pre":          # solo partidos no jugados
                continue
            competidores = comp.get("competitors", [])
            loc = next((c for c in competidores if c.get("homeAway") == "home"), None)
            vis = next((c for c in competidores if c.get("homeAway") == "away"), None)
            if not loc or not vis:
                continue

            fecha, hora = fecha_hora_arg(ev["date"])
            if fecha not in ventana:
                continue

            loc_id, vis_id = loc["team"]["id"], vis["team"]["id"]
            loc_nombre, vis_nombre = loc["team"]["displayName"], vis["team"]["displayName"]
            mercado = mercado_referencia(comp)

            # Estadio y ciudad: vienen en el propio scoreboard, sin pedido
            # extra. Verificado el 2026-08-18 contra arg.1: 15 de 15 eventos
            # traen venue.fullName. Puede faltar, así que cae a "".
            venue = comp.get("venue") or {}
            estadio = venue.get("fullName") or ""
            ciudad = (venue.get("address") or {}).get("city") or ""

            jug_loc = get_hist(slug, loc_id)
            jug_vis = get_hist(slug, vis_id)

            if slug in CON_FUERZAS:
                # ataque/defensa calibrados contra toda la red de cruces de
                # la temporada, no solo contra la muestra propia de cada uno.
                fuerzas, mu_local, mu_visita, pj = get_fuerzas(slug)
                a_loc, d_loc = fuerzas.get(loc_id, (1.0, 1.0))
                a_vis, d_vis = fuerzas.get(vis_id, (1.0, 1.0))
                n_loc, n_vis = pj.get(loc_id, 0), pj.get(vis_id, 0)
                if n_loc >= MIN_PARTIDOS_FUERZA and n_vis >= MIN_PARTIDOS_FUERZA:
                    lh = mu_local * a_loc * d_vis
                    la = mu_visita * a_vis * d_loc
                    lh = round(max(0.35, min(3.20, lh)), 3)
                    la = round(max(0.30, min(3.00, la)), 3)
                    n = min(n_loc, n_vis)
                    conf = meta["conf"] - (10 if n < 6 else 0)
                    nota = (f"λ calculados ajustando ataque/defensa de {loc_nombre} y "
                            f"{vis_nombre} contra toda la red de cruces de {meta['nombre']} "
                            f"esta temporada ({n_loc} y {n_vis} partidos jugados), pesado por "
                            f"antigüedad. Confirmá alineaciones antes de jugar.")
                else:
                    lh, la, conf = 1.35, 1.10, 45
                    nota = (f"Sin muestra suficiente en ESPN para calcular λ (menos de "
                            f"{MIN_PARTIDOS_FUERZA} partidos jugados esta temporada). Los "
                            "valores son genéricos: ajustalos a mano en Modelo.")
            else:
                # Copa Argentina: eliminación directa, sin red de cruces —
                # promedio simple ponderado por recencia de la muestra propia.
                cond_loc = promedio_condicion(jug_loc, local=True)
                cond_vis = promedio_condicion(jug_vis, local=False)
                if cond_loc and cond_vis and cond_loc[2] >= 2 and cond_vis[2] >= 2:
                    gf_loc, gc_loc, n_loc = cond_loc
                    gf_vis, gc_vis, n_vis = cond_vis
                    lh = (gf_loc + gc_vis) / 2
                    la = (gf_vis + gc_loc) / 2
                    lh = round(max(0.35, min(3.20, lh)), 3)
                    la = round(max(0.30, min(3.00, la)), 3)
                    n = min(n_loc, n_vis)
                    conf = meta["conf"] - (10 if n < 4 else 0)
                    nota = (f"λ calculados con datos de ESPN: {loc_nombre} promedia sus últimos "
                            f"{n_loc} partidos de local, {vis_nombre} sus últimos {n_vis} de "
                            f"visitante. Confirmá alineaciones antes de jugar.")
                else:
                    lh, la, conf = 1.35, 1.10, 45
                    nota = ("Sin muestra suficiente en ESPN para calcular λ (menos de 2 partidos "
                            "de local/visitante esta temporada). Los valores son genéricos: "
                            "ajustalos a mano en Modelo.")

            # ── historial directo: cruces contra este rival en las últimas
            # temporadas de la misma competición ──
            h2h = []
            for yr in range(season, season - TEMPORADAS_H2H, -1):
                previos = jug_loc if yr == season else get_hist(slug, loc_id, yr)
                for p in previos:
                    if p["rival_id"] == vis_id:
                        h2h.append({
                            "d": fecha_corta(p["fecha"]),
                            "h": p["home"], "a": p["away"], "s": p["marcador"],
                        })
            vistos_h2h, h2h_unico = set(), []
            for x in h2h:
                k = (x["d"], x["s"])
                if k not in vistos_h2h:
                    vistos_h2h.add(k)
                    h2h_unico.append(x)
            h2h = h2h_unico[:5]

            # ── tabla de posiciones de la zona donde juegan ──
            tablas = get_tabla(slug)
            info_grupo = tablas.get(loc_id) or tablas.get(vis_id)
            tabla = info_grupo["filas"] if info_grupo else []
            grupo = info_grupo["grupo"] if info_grupo else ""

            # ── córners/faltas/tarjetas: promedio propio de los últimos
            # partidos de cada equipo (vía /summary, un pedido por partido),
            # no la constante fija de toda la competición. Si no hay data
            # (partido sin boxscore, equipo nuevo), cae a la constante.
            disc_loc = disciplina_equipo(slug, loc_id, jug_loc, cache_resumen)
            disc_vis = disciplina_equipo(slug, vis_id, jug_vis, cache_resumen)
            if disc_loc and disc_vis:
                c_loc, f_loc, t_loc, _ = disc_loc
                c_vis, f_vis, t_vis, _ = disc_vis
                corners  = round(c_loc + c_vis, 1)
                cornersH = round(c_loc, 1)
                fouls    = round(f_loc + f_vis, 1)
                cards    = round(t_loc + t_vis, 1)
            else:
                corners, cornersH = meta["corners"], round(meta["corners"] * 0.56, 1)
                fouls, cards = meta["fouls"], meta["cards"]

            partidos.append({
                "id": f"espn{ev['id']}",
                "date": fecha, "comp": meta["nombre"], "compLogo": comp_logo, "hora": hora,
                "home": loc_nombre, "away": vis_nombre,
                "homeId": loc_id, "awayId": vis_id,
                "homeLogo": escudo(loc["team"]), "awayLogo": escudo(vis["team"]),
                "lh": lh, "la": la, "rho": meta["rho"], "conf": conf,
                "corners": corners, "cornersH": cornersH,
                "fouls": fouls, "cards": cards,
                "note": nota,
                "formH": forma(jug_loc), "formA": forma(jug_vis),
                "formH_general": forma_general(*get_hist_general(loc_id)),
                "formA_general": forma_general(*get_hist_general(vis_id)),
                "h2h": h2h, "tabla": tabla, "grupo": grupo,
                "estadio": estadio, "ciudad": ciudad,
                "mercado": mercado,
                "preload": {},
            })

    # ── memoria de marcadores ────────────────────────────────────────
    # Se acumula: lo que ya está no se toca ni se borra. Un marcador de
    # un partido jugado no cambia, y si ESPN un día deja de devolver una
    # temporada vieja, el registro del usuario no puede quedarse sin el
    # resultado de una apuesta que ya anotó.
    resultados_previos = {}
    if RESULTADOS.exists():
        try:
            resultados_previos = json.loads(RESULTADOS.read_text(encoding="utf-8"))
        except Exception:
            resultados_previos = {}
    antes_res = len(resultados_previos)

    for slug in COMPETICIONES:
        # arg.copa no calibra fuerzas, así que para esa competición este es
        # el único pedido de resultados de la corrida. Para las otras tres
        # ya está en cache y no cuesta nada.
        for p in get_resultados(slug):
            eid = p.get("id")
            if not eid:
                continue
            resultados_previos[f"espn{eid}"] = f"{int(p['gh'])}-{int(p['ga'])}"

    RESULTADOS.parent.mkdir(parents=True, exist_ok=True)
    RESULTADOS.write_text(
        json.dumps(resultados_previos, ensure_ascii=False, indent=0, sort_keys=True),
        encoding="utf-8")
    print(f"· marcadores guardados: {len(resultados_previos)} "
          f"(+{len(resultados_previos) - antes_res} nuevos)")

    partidos.sort(key=lambda p: (p["date"], p["hora"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "actualizado": datetime.datetime.now().isoformat(timespec="minutes"),
        "requests": _req_count,
        "partidos": partidos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    CACHE_DISCIPLINA.parent.mkdir(parents=True, exist_ok=True)
    CACHE_DISCIPLINA.write_text(json.dumps(cache_resumen, ensure_ascii=False), encoding="utf-8")
    CACHE_LIGAS.write_text(json.dumps(cache_ligas, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    registrar_pronosticos(partidos, season, hoy, traer_resultados=get_resultados)

    con_h2h = sum(1 for p in partidos if p["h2h"])
    con_tabla = sum(1 for p in partidos if p["tabla"])
    print(f"\n✓ {len(partidos)} partidos · {con_h2h} con historial directo · "
          f"{con_tabla} con tabla · {len(cache_resumen)-resumenes_antes} resúmenes nuevos "
          f"({len(cache_resumen)} en caché) · {_req_count} requests a ESPN")


if __name__ == "__main__":
    main()
