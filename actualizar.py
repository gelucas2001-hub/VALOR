#!/usr/bin/env python3
"""
VALOR — actualizador de datos
Trae partidos de Liga Profesional, Libertadores y Sudamericana desde
API-Football, calcula los goles esperados (lambda) de cada equipo a partir
de su rendimiento separado por localía, y escribe data/partidos.json.

Las cuotas NO se traen: se cargan a mano en la app.

Presupuesto de requests: ~15-25/día. El free tier da 100/día.
"""

import os, json, sys, datetime, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

KEY  = os.environ.get("API_FOOTBALL_KEY", "").strip()
HOST = "v3.football.api-sports.io"
OUT  = Path("data/partidos.json")
CACHE = Path("data/cache_ligas.json")

# ── competiciones ────────────────────────────────────────────────
# Los IDs de API-Football. Si alguno no devuelve nada, verificalo en
# https://dashboard.api-football.com  →  Leagues
LIGAS = {
    128: {"nombre": "Liga Profesional Argentina", "rho": -0.10, "conf": 75,
          "corners": 9.4, "fouls": 25.5, "cards": 5.4},
    13:  {"nombre": "CONMEBOL Libertadores",      "rho": -0.10, "conf": 65,
          "corners": 9.8, "fouls": 24.0, "cards": 5.0},
    11:  {"nombre": "CONMEBOL Sudamericana",      "rho": -0.14, "conf": 65,
          "corners": 9.6, "fouls": 24.5, "cards": 5.2},
    130: {"nombre": "Copa Argentina",             "rho": -0.14, "conf": 60,
          "corners": 9.0, "fouls": 26.0, "cards": 5.6},
}

DIAS_ADELANTE = 4          # cuántos días de fixtures traer
SEASON = datetime.date.today().year

_req_count = 0

def api(path):
    """Una llamada a la API, contando el gasto."""
    global _req_count
    if not KEY:
        raise SystemExit("Falta API_FOOTBALL_KEY en el entorno.")
    _req_count += 1
    r = Request(f"https://{HOST}/{path}", headers={"x-apisports-key": KEY})
    try:
        with urlopen(r, timeout=25) as resp:
            d = json.loads(resp.read().decode())
    except (HTTPError, URLError) as e:
        print(f"  ! error en {path}: {e}", file=sys.stderr)
        return {"response": []}
    if d.get("errors"):
        print(f"  ! API devolvió errores en {path}: {d['errors']}", file=sys.stderr)
    time.sleep(0.4)                      # respetar rate limit
    return d


def perfil_liga(liga_id):
    """
    De /standings sale, en UNA sola request, el rendimiento de todos los
    equipos separado en local y visitante. Con eso se calculan las medias
    de la liga y la fuerza relativa de cada equipo.
    """
    d = api(f"standings?league={liga_id}&season={SEASON}")
    equipos, gl_tot, gv_tot, pj_tot = {}, 0.0, 0.0, 0

    for liga in d.get("response", []):
        for grupo in liga.get("league", {}).get("standings", []):
            for fila in grupo:
                t = fila["team"]
                h, a = fila.get("home", {}), fila.get("away", {})
                pjh, pja = h.get("played", 0), a.get("played", 0)
                if pjh + pja == 0:
                    continue
                equipos[t["id"]] = {
                    "nombre": t["name"],
                    "gf_local":  h.get("goals", {}).get("for", 0),
                    "gc_local":  h.get("goals", {}).get("against", 0),
                    "pj_local":  pjh,
                    "gf_visita": a.get("goals", {}).get("for", 0),
                    "gc_visita": a.get("goals", {}).get("against", 0),
                    "pj_visita": pja,
                }
                gl_tot += h.get("goals", {}).get("for", 0)
                gv_tot += a.get("goals", {}).get("for", 0)
                pj_tot += pjh

    if pj_tot < 4:                       # muestra insuficiente
        return None
    return {
        "media_local":  gl_tot / pj_tot,
        "media_visita": gv_tot / pj_tot,
        "equipos": equipos,
    }


def lambdas(perfil, id_local, id_visita):
    """
    lambda_local = ataque del local (como local) x flojera defensiva del
    visitante (como visitante) x media de goles de local de la liga.

    Ojo: el rendimiento ya sale de partidos como local, así que la ventaja
    de localía YA está adentro. No se suma de nuevo.
    """
    if not perfil:
        return None
    E = perfil["equipos"]
    L, V = E.get(id_local), E.get(id_visita)
    if not L or not V or L["pj_local"] < 2 or V["pj_visita"] < 2:
        return None

    ml, mv = perfil["media_local"], perfil["media_visita"]
    if ml <= 0 or mv <= 0:
        return None

    ataque_L   = (L["gf_local"]  / L["pj_local"])  / ml
    defensa_V  = (V["gc_visita"] / V["pj_visita"]) / ml
    ataque_V   = (V["gf_visita"] / V["pj_visita"]) / mv
    defensa_L  = (L["gc_local"]  / L["pj_local"])  / mv

    lh = ataque_L * defensa_V * ml
    la = ataque_V * defensa_L * mv

    # Techo y piso: la muestra corta produce números absurdos.
    lh = max(0.35, min(3.20, lh))
    la = max(0.30, min(3.00, la))
    n  = min(L["pj_local"], V["pj_visita"])
    return round(lh, 3), round(la, 3), n


def forma(equipo_id, n=5):
    """Últimos n resultados. 1 request por equipo — el gasto más grande."""
    d = api(f"fixtures?team={equipo_id}&last={n}")
    out = []
    for f in d.get("response", []):
        if f["fixture"]["status"]["short"] not in ("FT", "AET", "PEN"):
            continue
        gh, ga = f["goals"]["home"], f["goals"]["away"]
        if gh is None:
            continue
        local = f["teams"]["home"]["id"] == equipo_id
        gp, gc = (gh, ga) if local else (ga, gh)
        out.append("W" if gp > gc else ("D" if gp == gc else "L"))
    return out[:n]


def h2h(a, b, n=5):
    d = api(f"fixtures/headtohead?h2h={a}-{b}&last={n}")
    out = []
    for f in d.get("response", []):
        gh, ga = f["goals"]["home"], f["goals"]["away"]
        if gh is None:
            continue
        out.append({
            "d": f["fixture"]["date"][:10].split("-")[::-1][0] + "/" +
                 f["fixture"]["date"][5:7] + "/" + f["fixture"]["date"][2:4],
            "h": f["teams"]["home"]["name"],
            "a": f["teams"]["away"]["name"],
            "s": f"{gh}-{ga}",
        })
    return out


def main():
    hoy = datetime.date.today()
    fechas = [(hoy + datetime.timedelta(days=i)).isoformat()
              for i in range(DIAS_ADELANTE)]

    # Perfiles de liga: cambian lento, se cachean por 3 días.
    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    vencido = cache.get("_fecha", "") < (hoy - datetime.timedelta(days=3)).isoformat()

    perfiles = {}
    for lid in LIGAS:
        k = str(lid)
        if not vencido and k in cache:
            perfiles[lid] = cache[k]
            print(f"· perfil {LIGAS[lid]['nombre']} — desde caché")
        else:
            print(f"· perfil {LIGAS[lid]['nombre']} — consultando")
            perfiles[lid] = perfil_liga(lid)
            cache[k] = perfiles[lid]
    cache["_fecha"] = hoy.isoformat()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    partidos, vistos = [], set()
    for lid, meta in LIGAS.items():
        for fecha in fechas:
            d = api(f"fixtures?league={lid}&season={SEASON}&date={fecha}")
            for f in d.get("response", []):
                fid = f["fixture"]["id"]
                if fid in vistos:
                    continue
                vistos.add(fid)

                loc, vis = f["teams"]["home"], f["teams"]["away"]
                lam = lambdas(perfiles.get(lid), loc["id"], vis["id"])

                if lam:
                    lh, la, n = lam
                    conf = meta["conf"] - (10 if n < 4 else 0)
                    nota = f"λ calculados sobre {n} partidos de local/visitante. Confirmá alineaciones antes de jugar."
                else:
                    lh, la, conf = 1.35, 1.10, 45
                    nota = "Sin muestra suficiente para calcular λ. Los valores son genéricos: ajustalos a mano en Modelo."

                partidos.append({
                    "id": f"api{fid}",
                    "date": f["fixture"]["date"][:10],
                    "comp": meta["nombre"],
                    "hora": f["fixture"]["date"][11:16],
                    "home": loc["name"], "away": vis["name"],
                    "homeId": loc["id"], "awayId": vis["id"],
                    "lh": lh, "la": la, "rho": meta["rho"], "conf": conf,
                    "corners": meta["corners"],
                    "cornersH": round(meta["corners"] * 0.56, 1),
                    "fouls": meta["fouls"], "cards": meta["cards"],
                    "note": nota,
                    "formH": [], "formA": [], "h2h": [], "tabla": [],
                    "preload": {},
                })

    # Detalle solo para los partidos de HOY: no gastar en los de pasado mañana.
    de_hoy = [p for p in partidos if p["date"] == hoy.isoformat()][:6]
    for p in de_hoy:
        p["formH"] = forma(p["homeId"])
        p["formA"] = forma(p["awayId"])
        p["h2h"]   = h2h(p["homeId"], p["awayId"])

    partidos.sort(key=lambda p: (p["date"], p["hora"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "actualizado": datetime.datetime.now().isoformat(timespec="minutes"),
        "requests": _req_count,
        "partidos": partidos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n✓ {len(partidos)} partidos · {_req_count} requests gastadas de 100")


if __name__ == "__main__":
    main()
