#!/usr/bin/env python3
"""
VALOR — actualizador de datos
Trae partidos de Liga Profesional, Libertadores, Sudamericana y Copa
Argentina desde la API pública no oficial de ESPN (no necesita key).
Para cada partido futuro calcula los goles esperados (lambda) de cada
equipo a partir del promedio de goles a favor/en contra jugando en su
condición (local de local, visitante de visitante).

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
HOSTS = [
    "https://site.api.espn.com/apis/site/v2/sports/soccer",
    "https://site.web.api.espn.com/apis/site/v2/sports/soccer",
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

OUT = Path("data/partidos.json")
ARG_TZ = datetime.timezone(datetime.timedelta(hours=-3))
DIAS_ADELANTE = 5          # próximos N días (incluye hoy)

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


def historial(slug, team_id):
    """/teams/{id}/schedule de la competición: partidos jugados esta
    temporada, con condición (local/visitante) y goles a favor/en contra.
    Devuelve (lista_jugados, forma_ultimos_5)."""
    d = api(f"{slug}/teams/{team_id}/schedule")
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
        jugados.append({
            "fecha": e.get("date", ""),
            "local": propio.get("homeAway") == "home",
            "gf": gf, "gc": gc,
        })
    jugados.sort(key=lambda x: x["fecha"], reverse=True)
    forma = []
    for p in jugados[:5]:
        forma.append("W" if p["gf"] > p["gc"] else ("D" if p["gf"] == p["gc"] else "L"))
    return jugados, forma


def promedio_condicion(jugados, local):
    """Promedio de goles a favor/en contra restringido a los partidos
    jugados en la condición pedida (local=True → de local)."""
    sub = [p for p in jugados if p["local"] == local]
    if not sub:
        return None
    gf = sum(p["gf"] for p in sub) / len(sub)
    gc = sum(p["gc"] for p in sub) / len(sub)
    return gf, gc, len(sub)


def main():
    hoy = datetime.date.today()
    ventana = {(hoy + datetime.timedelta(days=i)).isoformat() for i in range(DIAS_ADELANTE)}
    # margen de un día a cada lado: la fecha UTC de ESPN puede correrse
    # respecto al día calendario argentino en partidos nocturnos.
    desde = (hoy - datetime.timedelta(days=1)).strftime("%Y%m%d")
    hasta = (hoy + datetime.timedelta(days=DIAS_ADELANTE)).strftime("%Y%m%d")

    partidos = []
    cache_hist = {}   # (slug, team_id) -> (jugados, forma) — no pedir 2 veces el mismo equipo

    def get_hist(slug, tid):
        k = (slug, tid)
        if k not in cache_hist:
            cache_hist[k] = historial(slug, tid)
        return cache_hist[k]

    for slug, meta in COMPETICIONES.items():
        print(f"· {meta['nombre']} — scoreboard")
        d = api(f"{slug}/scoreboard?dates={desde}-{hasta}")
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

            jug_loc, form_loc = get_hist(slug, loc_id)
            jug_vis, form_vis = get_hist(slug, vis_id)

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

            partidos.append({
                "id": f"espn{ev['id']}",
                "date": fecha, "comp": meta["nombre"], "hora": hora,
                "home": loc_nombre, "away": vis_nombre,
                "lh": lh, "la": la, "rho": meta["rho"], "conf": conf,
                "corners": meta["corners"],
                "cornersH": round(meta["corners"] * 0.56, 1),
                "fouls": meta["fouls"], "cards": meta["cards"],
                "note": nota,
                "formH": form_loc, "formA": form_vis,
                "h2h": [], "tabla": [], "preload": {},
            })

    partidos.sort(key=lambda p: (p["date"], p["hora"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "actualizado": datetime.datetime.now().isoformat(timespec="minutes"),
        "requests": _req_count,
        "partidos": partidos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n✓ {len(partidos)} partidos · {_req_count} requests a ESPN")


if __name__ == "__main__":
    main()
