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
ARG_TZ = datetime.timezone(datetime.timedelta(hours=-3))
DIAS_ADELANTE = 7          # próximos N días (incluye hoy) — coincide con
                            # los 7 días que muestra la tira en el frontend
TEMPORADAS_H2H = 3         # temporadas hacia atrás para el historial directo
RECENCY_ALPHA = 0.90       # peso por antigüedad en promedio_condicion().
                            # 0.90: el partido 13 atrás pesa ~25% del más
                            # reciente. Gentil a propósito — es un ajuste
                            # fino, no un reemplazo del promedio.

# ── competiciones ────────────────────────────────────────────────
# slug de ESPN → metadata. rho: -0.10 en ligas/fase de grupos regular,
# -0.14 en llaves de eliminación directa (más varianza).
COMPETICIONES = {
    "arg.1": {"nombre": "Liga Profesional Argentina", "rho": -0.10, "conf": 75,
              "corners": 9.4, "fouls": 25.5, "cards": 5.4},
    "conmebol.libertadores": {"nombre": "CONMEBOL Libertadores", "rho": -0.10, "conf": 65,
              "corners": 9.8, "fouls": 24.0, "cards": 5.0},
    "conmebol.sudamericana": {"nombre": "CONMEBOL Sudamericana", "rho": -0.14, "conf": 65,
              "corners": 9.6, "fouls": 24.5, "cards": 5.2},
    "arg.copa": {"nombre": "Copa Argentina", "rho": -0.14, "conf": 60,
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
            "local": local,
            "gf": gf, "gc": gc,
            "rival_id": rival.get("team", {}).get("id", ""),
            "home": propio["team"]["displayName"] if local else rival["team"]["displayName"],
            "away": rival["team"]["displayName"] if local else propio["team"]["displayName"],
            "marcador": f"{int(gh)}-{int(ga)}",
        })
    jugados.sort(key=lambda x: x["fecha"], reverse=True)
    return jugados


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


def forma(jugados, n=5):
    return ["W" if p["gf"] > p["gc"] else ("D" if p["gf"] == p["gc"] else "L")
            for p in jugados[:n]]


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

    def get_tabla(slug):
        if slug not in cache_tabla:
            cache_tabla[slug] = tabla_competicion(slug, season)
        return cache_tabla[slug]

    for slug, meta in COMPETICIONES.items():
        print(f"· {meta['nombre']} — scoreboard")
        d = api(f"{SITE_V2}/{slug}/scoreboard?dates={desde}-{hasta}")
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

            jug_loc = get_hist(slug, loc_id)
            jug_vis = get_hist(slug, vis_id)

            cond_loc = promedio_condicion(jug_loc, local=True)   # local jugando de local
            cond_vis = promedio_condicion(jug_vis, local=False)  # visitante jugando de visitante

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
                        dd = p["fecha"][:10]
                        h2h.append({
                            "d": f"{dd[8:10]}/{dd[5:7]}/{dd[2:4]}",
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

            partidos.append({
                "id": f"espn{ev['id']}",
                "date": fecha, "comp": meta["nombre"], "hora": hora,
                "home": loc_nombre, "away": vis_nombre,
                "homeId": loc_id, "awayId": vis_id,
                "homeLogo": escudo(loc["team"]), "awayLogo": escudo(vis["team"]),
                "lh": lh, "la": la, "rho": meta["rho"], "conf": conf,
                "corners": meta["corners"],
                "cornersH": round(meta["corners"] * 0.56, 1),
                "fouls": meta["fouls"], "cards": meta["cards"],
                "note": nota,
                "formH": forma(jug_loc), "formA": forma(jug_vis),
                "h2h": h2h, "tabla": tabla, "grupo": grupo,
                "preload": {},
            })

    partidos.sort(key=lambda p: (p["date"], p["hora"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "actualizado": datetime.datetime.now().isoformat(timespec="minutes"),
        "requests": _req_count,
        "partidos": partidos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    con_h2h = sum(1 for p in partidos if p["h2h"])
    con_tabla = sum(1 for p in partidos if p["tabla"])
    print(f"\n✓ {len(partidos)} partidos · {con_h2h} con historial directo · "
          f"{con_tabla} con tabla · {_req_count} requests a ESPN")


if __name__ == "__main__":
    main()
