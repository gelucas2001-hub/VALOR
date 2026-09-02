#!/usr/bin/env python3
"""La cuota que ESPN no publica: líneas de gol, córners y jugadores.

Por qué existe:

ESPN expone **una sola casa** (DraftKings, el endpoint core devuelve
`count: 1`) y de ella **tres cosas**: 1X2, una línea de goles —siempre
2.5— y una de hándicap. Todo lo demás que la app muestra en "Otros
mercados" (más de 1.5, más de 3.5, ambos marcan) sale del modelo solo,
sin nada real contra qué compararse: `pMercado()` devuelve `None` y
esas filas nunca pueden marcar valor ni descartarlo.

Y en el mercado de estadísticas el hueco es total: verificado sobre 30
partidos argentinos, DraftKings publica **cero** líneas de córners de
equipo y **cero** de jugador. Toda la parte sudamericana de ese mercado
no existía para nosotros.

odds-api.io tiene las dos cosas, de Bet365, en un solo pedido por
partido: 73 mercados para un partido de Liga Profesional, incluidas 16
líneas de gol con los dos lados, córners del partido y **por equipo**,
y la escalera de remates de cada jugador.

Los dos lados importan. Los córners de acá vienen con `over` **y**
`under`, así que se les puede quitar el margen con `devigShin` como a
cualquier mercado de dos opciones. Los de ESPN venían como escalera
acumulada de un solo lado, que es autoconsistente por construcción y no
deja sacar margen (ver TRASPASO.md §6vicies ter).

Cómo se cruza un partido, y por qué no por nombre:

Los nombres no sirven: ellos escriben "CA River Plate (ARG)", "CR
Flamengo RJ", "Racing Club Avellaneda". Medido el 2026-08-26, cruzan
exacto 8 de 30 en Argentina y **0 de 20** en Brasil. Y el atajo —cruzar
por parecido— es justo lo que este repo prohíbe: **"Racing Club" somos
Racing de Avellaneda y ellos tienen además "Racing Club De Lens"**.

Se cruza por **fixture**: liga, fecha, y los dos equipos a la vez. En
una liga, en un día, hay pocos partidos, así que alcanza con que los
nombres se distingan entre ESOS, no en todo el mundo. Y si dos
candidatos empatan en compatibilidad, no se elige ninguno.

Medido sobre los 46 partidos del caché: **46 cruzan único, 0 ambiguos,
0 sin cruzar**, y el mapa de equipos que sale de ahí es una biyección
perfecta de 91 equipos — ninguno nuestro apunta a dos de ellos y
ninguno de ellos es reclamado por dos nuestros. Racing de Avellaneda y
Racing de Lens quedaron separados, que era el caso peligroso.

Sin clave (`ODDS_API_KEY`) no hace nada y la app queda igual que antes.

    python mercado_extra.py            # qué cruzaría, sin escribir nada
"""

import datetime
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

import equipos as EQ

BASE = "https://api.odds-api.io/v3"
CASA = "Bet365"

# Nuestro slug de competición -> el suyo. Verificados el 2026-08-26
# contra su listado de ligas de fútbol; `arg.copa` el 2026-09-02 con
# `--ligas`, el día que volvió a la app.
#
# Que falte una entrada acá no es un detalle de cobertura: la
# competición se queda sin Bet365 **y sin props**, y los props no se
# recuperan hacia atrás. Ver `eventos_de()`.
#
# Ojo con los vecinos, que es donde se elige mal: `argentina-copa-
# argentina` no es `argentina-super-cup`, y Japón publica tres divisiones
# con nombres casi iguales (`japan-jleague`, `japan-jleague-2`,
# `japan-j-league-3`) de las cuales Bet365 solo cotiza la segunda.
LIGAS = {
    "arg.1": "argentina-primera-lpf-clausura",
    "arg.copa": "argentina-copa-argentina",
    "bra.1": "brazil-brasileiro-serie-a",
    "eng.1": "england-premier-league",
    "fra.1": "france-ligue-1",
    "esp.1": "spain-laliga",
    "conmebol.libertadores":
        "international-clubs-conmebol-libertadores-knockout-stage",
    "conmebol.sudamericana":
        "international-clubs-conmebol-sudamericana-knockout-stage",
}

# Ligas que odds-api lista, cuyo fixture cruza, y que Bet365 NO cotiza.
#
# Estar en LIGAS y no tener cobertura son dos cosas distintas, y hasta
# el 2026-09-02 se confundían: el pedido salía igual y volvía vacío.
# Para `jpn.1` eso son 1 pedido de eventos + 10 de odds por corrida, dos
# veces por día, más los de `foto_props.py` cada hora — cuota quemada
# para recibir `{}`.
#
# Hoy está vacío, y eso no significa que la idea no sirviera: `jpn.1`
# vivió acá unas horas el 2026-09-02 y después salió de la app entera,
# porque una liga que no se puede jugar al precio bueno no es una liga
# barata — es una liga que no está. Su slug era `japan-jleague` y la
# verificación fue de las dos puntas: cero bloques en tres partidos, y
# la J.League ausente de la web de Bet365, donde sí está la J.League 2.
#
# El conjunto queda porque la situación se repite: una liga puede estar
# bien identificada, cruzar el fixture, y no ser ofrecida por la casa.
# Eso es distinto de un slug mal puesto y hay que poder decirlo sin
# borrar el slug, que es información correcta y cara de conseguir.
SIN_COBERTURA = set()

# Tokens que NO identifican a un club: tipo de sociedad y artículos.
#
# La lista es corta a propósito. La primera versión metía acá
# "atletico", "deportivo" y las siglas de provincia, y con eso
# Atlético-MG y Athletico-PR se quedaban sin un solo token y dejaban de
# cruzar: en Brasil y en Argentina esas palabras SON el nombre. Un
# filtro de ruido demasiado ancho borra la señal.
RUIDO = {"ca", "cd", "cr", "ec", "fc", "sc", "ac", "afc", "csd", "cs",
         "afbc", "se", "club", "clube", "de", "do", "da", "del",
         "la", "el", "the"}

# Qué bloque de odds-api alimenta qué campo nuestro. Varios nombres
# suyos son el mismo mercado ("Team Corners Home" y "Corners Totals
# Home" traen la misma línea), así que se juntan; el primero que
# escribe una línea la gana y los demás no la pisan.
#
# Nada de HT acá: "Corners Totals HT" es del primer tiempo, y mezclarlo
# con el total del partido sería comparar el modelo contra otra cosa.
GOLES = ("Alternative Total Goals", "Alternative Goal Line",
         "Goals Over/Under", "Totals")
CORNERS = {
    "total": ("Corners Totals", "Corners 2-Way", "Corners",
              "Alternative Corners"),
    "local": ("Team Corners Home", "Corners Totals Home"),
    "visita": ("Team Corners Away", "Corners Totals Away"),
}
# `faltas` entró el 2026-09-02, verificada contra la fuente: en
# Ipswich-Liverpool el bloque trae 171 entradas con la forma IDÉNTICA a
# la de remates —{"label": "Wataru Endo (2)", "hdp": 0.5, "over":
# "1.083"}—, así que `_escalera()` la lee sin cambiar una línea.
#
# Las otras dos que Bet365 manda y NO entran, con el motivo:
#
#   "Player Cards"          no trae `hdp`: es otra forma, no una escalera.
#   "Player to be Booked"   trae `hdp` 0.5, pero la etiqueta es "Nombre
#                           (Booked)" en vez de "Nombre (1)". `_escalera()`
#                           dejaría el "(Booked)" pegado al nombre y ese
#                           jugador no cruzaría nunca contra ESPN, que
#                           cruza por igualdad exacta. Entra el día que
#                           se le enseñe a leer esa etiqueta.
#   "Player To Be Fouled"   forma correcta, pero son las faltas RECIBIDAS
#                           y el modelo no tiene esa métrica.
#
# Ojo con la cobertura: esto es de Premier. En un partido de arg.1 el
# único bloque de jugador sin usar era "Player To Score or Assist", o
# sea que faltas puede no existir en todas las ligas. Que no venga es
# un estado normal — `extraer()` no escribe la clave y listo.
JUGADOR = {
    "remates": ("Player Shots", "Player Shots O/U"),
    "al_arco": ("Player Shots on Target", "Player Shots on Target O/U"),
    "faltas": ("Player Fouls Committed", "Player Fouls"),
}


def clave(entorno=None):
    """La clave de odds-api.io, del entorno. None si no está.

    Que falte es un estado normal: sin clave la app se comporta igual
    que antes de que esta fuente existiera.
    """
    v = (entorno if entorno is not None else os.environ).get("ODDS_API_KEY")
    v = (v or "").strip()
    return v or None


def cuota(v):
    """Un precio decimal, o None. Una cuota de 1.00 o menos no paga nada."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 1.0 else None


def _linea(hdp):
    """La línea como texto estable: 10 y 10.0 dan '10'; 0.5 da '0.5'.

    Es clave de diccionario y termina en JSON, así que tiene que ser la
    misma cadena siempre — si no, la misma línea entra dos veces.
    """
    try:
        f = float(hdp)
    except (TypeError, ValueError):
        return None
    return str(int(f)) if f == int(f) else str(f)


def binaria(hdp):
    """True si la línea es X.5 — no puede empatar ni partirse en dos.

    Bet365 cotiza líneas de tres formas: X.5 (gana o pierde), enteras
    (2, 3, 4... — si el marcador cae justo ahí, empata y devuelve la
    apuesta, "push") y de cuarto (X.25, X.75 — reparte la apuesta en
    dos mitades y liquida cada una con la línea vecina).

    Todo nuestro motor es binario: `TESTS` en `index.html`, el Brier de
    `medir_corners.py`, el registro de pronósticos. Ninguno sabe qué
    hacer con un push o una apuesta partida en dos. Compararlos igual
    no tiraría un error — daría un EV mal calculado sin que nada avise,
    que es peor que no tener la línea.
    """
    try:
        f = float(hdp)
    except (TypeError, ValueError):
        return False
    doble = f * 2
    entero = round(doble)
    return abs(doble - entero) < 1e-6 and entero % 2 == 1


def dos_lados(odds):
    """{línea: [over, under]} de un bloque de dos lados.

    Una línea a la que le falta un lado se descarta entera. Con media
    cuota no se puede quitar el margen, y compararse contra la cruda
    hace ver ventaja donde solo hay comisión — es el error que
    `medir_devig.py` ya midió.
    """
    out = {}
    for o in odds or []:
        ln = _linea((o or {}).get("hdp"))
        a, b = cuota((o or {}).get("over")), cuota((o or {}).get("under"))
        if ln is None or a is None or b is None:
            continue
        out.setdefault(ln, [a, b])
    return out


def _escalera(odds):
    """{jugador: {lado, lineas:{línea: cuota}}} de un bloque de jugador.

    Ojo: esto es de UN solo lado. Cada escalón dice "más de N remates" y
    no hay "menos de N", así que no hay margen que quitar acá y no se
    puede comparar contra el modelo como si fuera un par. Se invierte la
    escalera con Poisson, igual que con `propBets` de ESPN.

    La etiqueta viene como "Nombre (1)", donde 1 es local y 2 visitante.
    """
    out = {}
    for o in odds or []:
        etiqueta = ((o or {}).get("label") or "").strip()
        ln, c = _linea((o or {}).get("hdp")), cuota((o or {}).get("over"))
        if not etiqueta or ln is None or c is None:
            continue
        lado = None
        if etiqueta.endswith("(1)"):
            lado = "L"
        elif etiqueta.endswith("(2)"):
            lado = "V"
        nombre = etiqueta[:-3].strip() if lado else etiqueta
        if not nombre:
            continue
        d = out.setdefault(nombre, {"lado": lado, "lineas": {}})
        d["lineas"].setdefault(ln, c)
    return out


def extraer(bloques):
    """Los mercados que nos importan, normalizados. {} si no hay nada.

    `bloques` es la lista que odds-api devuelve bajo
    `bookmakers[CASA]`: cada uno con `name` y `odds`.
    """
    por_nombre = {}
    for b in bloques or []:
        n = (b or {}).get("name")
        if n:
            por_nombre.setdefault(n, []).extend(b.get("odds") or [])

    out = {}

    ml = (por_nombre.get("ML") or [{}])[0]
    tri = {"local": cuota(ml.get("home")), "empate": cuota(ml.get("draw")),
           "visitante": cuota(ml.get("away"))}
    if all(tri.values()):
        out["1x2"] = tri

    dc = (por_nombre.get("Double Chance") or [{}])[0]
    tres = {k: cuota(dc.get(k)) for k in ("1X", "12", "X2")}
    if all(tres.values()):
        out["dc"] = tres

    bt = (por_nombre.get("Both Teams To Score") or [{}])[0]
    par = {"si": cuota(bt.get("yes")), "no": cuota(bt.get("no"))}
    if all(par.values()):
        out["btts"] = par

    goles = {}
    for n in GOLES:
        for ln, v in dos_lados(por_nombre.get(n)).items():
            if binaria(ln):
                goles.setdefault(ln, v)
    if goles:
        out["goles"] = goles

    corners = {}
    for donde, nombres in CORNERS.items():
        d = {}
        for n in nombres:
            for ln, v in dos_lados(por_nombre.get(n)).items():
                if binaria(ln):
                    d.setdefault(ln, v)
        if d:
            corners[donde] = d
    if corners:
        out["corners"] = corners

    for campo, nombres in JUGADOR.items():
        d = {}
        for n in nombres:
            for jug, v in _escalera(por_nombre.get(n)).items():
                if jug in d:
                    for ln, c in v["lineas"].items():
                        d[jug]["lineas"].setdefault(ln, c)
                else:
                    d[jug] = v
        if d:
            out[campo] = d

    return out


def tokens(nombre):
    """Las palabras que identifican a un club, sin el tipo de sociedad."""
    return {t for t in EQ.normalizar(nombre).split() if t not in RUIDO}


def compat(a, b):
    """Cuántas palabras comparten dos nombres. 0 = incompatibles."""
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) if ta and tb else 0


def cruzar_fixture(partido, eventos):
    """El id de evento de odds-api para uno de nuestros partidos, o None.

    Exige que los DOS equipos sean compatibles y que el candidato sea
    único. Dos candidatos empatados devuelven None: sin cuota se nota,
    con la cuota del partido equivocado no.
    """
    if not partido:
        return None
    try:
        d0 = datetime.date.fromisoformat(partido.get("date"))
    except (TypeError, ValueError):
        return None
    # Nuestra fecha es la local del partido; la de ellos, UTC. Un
    # partido de noche en América cae al día siguiente en UTC.
    dias = {d0.isoformat(), (d0 + datetime.timedelta(days=1)).isoformat()}

    pts = []
    for e in eventos or []:
        if str((e or {}).get("date"))[:10] not in dias:
            continue
        s = (compat(partido.get("home"), e.get("home"))
             * compat(partido.get("away"), e.get("away")))
        if s:
            pts.append((s, e.get("id")))
    if not pts:
        return None
    pts.sort(key=lambda x: -x[0])
    if len(pts) > 1 and pts[0][0] == pts[1][0]:
        return None
    return pts[0][1]


# ── red ──────────────────────────────────────────────────────────────

def _pedir(ruta, key, timeout=45):
    url = f"{BASE}/{ruta}{'&' if '?' in ruta else '?'}apiKey={key}"
    req = urllib.request.Request(url, headers={"User-Agent": "VALOR/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read()), r.headers.get("x-ratelimit-remaining")


def eventos_de(slug, key, avisar=True):
    """Los partidos que odds-api tiene para una de nuestras competiciones.

    Una competición que la app publica y que no está en LIGAS se queda
    sin Bet365 **y sin props**, que salen del mismo pedido. Hasta el
    2026-09-02 eso pasaba callado: `LIGAS.get()` devolvía None y la
    función `[]`, igual que si la red hubiera fallado.

    Costó caro y no se vio. Cuando entró `jpn.1` —la única liga que pasa
    todos los filtros del veredicto, agregada justamente para que la app
    tuviera dónde hablar— nadie la sumó acá: sus partidos salieron con
    la cuota de DraftKings (7.7% de margen contra 3.1%) y no se guardó
    una sola línea de jugador. Esas líneas no se recuperan: para ligas
    domésticas, una vez jugado el partido `v3/events` ni siquiera
    devuelve el id del evento.

    Es el mismo patrón que ya está anotado dos veces en TRASPASO: un
    descarte silencioso no se ve como un error, se ve como menos datos.
    Por eso ahora avisa.
    """
    if slug in SIN_COBERTURA:
        return []
    liga = LIGAS.get(slug)
    if not liga:
        if avisar:
            print(f"  ! {slug} no está en LIGAS: se queda sin Bet365 y sin "
                  f"props. Verificá su slug con `python mercado_extra.py "
                  f"--ligas` y agregalo.", file=sys.stderr)
        return []
    evs, _ = _pedir(f"events?sport=football&league={liga}", key)
    return evs or []


def ligas_disponibles(key, filtro=""):
    """El listado de ligas de odds-api, para sacar un slug de la fuente.

    Los seis slugs de LIGAS se verificaron así el 2026-08-26, contra su
    listado de 908 ligas. La regla del repo es mirar la fuente antes de
    transcribir a mano; esto deja el paso a un comando en vez de a una
    sesión que hay que recordar.
    """
    d, _ = _pedir("leagues?sport=football", key)
    ligas = d if isinstance(d, list) else (d or {}).get("leagues") or []
    f = filtro.lower()
    out = []
    for lg in ligas:
        if isinstance(lg, str):
            nombre, slug = lg, lg
        else:
            slug = lg.get("slug") or lg.get("id") or ""
            nombre = lg.get("name") or slug
        if not f or f in str(slug).lower() or f in str(nombre).lower():
            out.append((str(slug), str(nombre)))
    return sorted(set(out))


def bloques_sin_usar(bloques):
    """Los mercados que Bet365 manda en la MISMA respuesta y no leemos.

    `odds_de()` pide `odds?eventId=...&bookmakers=Bet365` y recibe todos
    los bloques de la casa de una vez. `extraer()` consume los nombres
    de GOLES, CORNERS y JUGADOR y descarta el resto sin dejar rastro.

    Eso importa desde que se midió que la única señal del proyecto está
    en los props (TRASPASO §22, §22bis): el modelo tiene seis métricas de
    jugador y acá se leen dos. Las otras cuatro puede que ya estén
    llegando en cada respuesta. Antes de escribir nombres a mano —"Player
    Fouls" o "Player Fouls Committed", quién sabe— conviene preguntarle
    a la fuente cómo se llaman, que es gratis: el pedido ya se hizo.
    """
    usados = {"ML", "Double Chance", "Both Teams To Score"}
    usados.update(GOLES)
    for nombres in CORNERS.values():
        usados.update(nombres)
    for nombres in JUGADOR.values():
        usados.update(nombres)
    vistos = {(b or {}).get("name") for b in bloques or []}
    return sorted(n for n in vistos if n and n not in usados)


def odds_de(event_id, key):
    """Los mercados de Bet365 para un evento, ya normalizados."""
    d, quedan = _pedir(f"odds?eventId={event_id}&bookmakers={CASA}", key)
    bloques = ((d or {}).get("bookmakers") or {}).get(CASA) or []
    return extraer(bloques), quedan


def main():
    key = clave()
    print(__doc__)
    if not key:
        print("  FALTA ODDS_API_KEY. Sin ella la app anda igual que antes.\n")
        return 1

    # `--ligas [filtro]`: el listado de la fuente, para sacar un slug sin
    # adivinarlo. `python mercado_extra.py --ligas japan`
    if "--ligas" in sys.argv:
        i = sys.argv.index("--ligas")
        filtro = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
        try:
            ligas = ligas_disponibles(key, filtro)
        except Exception as e:
            print(f"  no se pudo pedir el listado: {e}\n")
            return 1
        print(f"\n  {len(ligas)} ligas" + (f" que contienen '{filtro}'" if filtro else ""))
        for slug, nombre in ligas:
            print(f"    {slug:55} {nombre}")
        print()
        return 0

    partidos = json.loads(
        (open("data/partidos.json", encoding="utf-8").read()))
    ps = partidos.get("partidos", partidos)
    COMP = {"Liga Profesional Argentina": "arg.1",
            "Copa Argentina": "arg.copa",
            "Brasileirão Série A": "bra.1",
            "Premier League": "eng.1", "Ligue 1": "fra.1",
            "Spanish LALIGA": "esp.1",
            "J.League": "jpn.1",
            "CONMEBOL Libertadores": "conmebol.libertadores",
            "CONMEBOL Sudamericana": "conmebol.sudamericana"}

    cache, ok, sin, sin_mapa, sin_cobertura = {}, 0, [], {}, {}
    for p in ps:
        slug = COMP.get(p.get("comp"))
        if not slug:
            # Antes era `continue` a secas. Una competición que la app
            # publica y que no está mapeada se saltaba sin dejar rastro,
            # que es como `jpn.1` estuvo sin Bet365 ni props el día que
            # entró, sin que nada lo dijera.
            sin_mapa[p.get("comp")] = sin_mapa.get(p.get("comp"), 0) + 1
            continue
        if slug in SIN_COBERTURA:
            # No cruzan porque no se piden. Mezclarlos con los que
            # fallaron el cruce hace ver un problema de nombres donde
            # hay una casa que no ofrece la liga.
            sin_cobertura[slug] = sin_cobertura.get(slug, 0) + 1
            continue
        if slug not in cache:
            cache[slug] = eventos_de(slug, key)
            print(f"  · {slug}: {len(cache[slug])} eventos")
        eid = cruzar_fixture(p, cache[slug])
        if eid:
            ok += 1
        else:
            sin.append(f"{p['home']} - {p['away']}")
    print(f"\n  cruzan: {ok}   sin cruzar: {len(sin)}")
    for s in sin:
        print(f"    x {s}")
    if sin_cobertura:
        print("\n  no se piden — Bet365 no cotiza estas competiciones")
        print("  (ver SIN_COBERTURA; el slug es correcto, la casa no la ofrece):")
        for slug, n in sorted(sin_cobertura.items()):
            print(f"    - {slug}  ({n} partidos)")
    if sin_mapa:
        print("\n  COMPETICIONES QUE LA APP PUBLICA Y ACÁ NO ESTÁN MAPEADAS:")
        print("  se quedan sin Bet365 y sin props, y los props no se")
        print("  recuperan hacia atrás.\n")
        for comp, n in sorted(sin_mapa.items(), key=lambda x: -x[1]):
            print(f"    ! {comp}  ({n} partidos)")
        print("\n  Buscá su slug con `python mercado_extra.py --ligas <texto>`")
        print("  y agregalo a LIGAS y al COMP de este main().")
    print("\n  (no se pidieron cuotas ni se escribió nada)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
