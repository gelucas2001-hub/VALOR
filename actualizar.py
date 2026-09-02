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

import mercado_extra as ME

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
PLANTELES = Path("data/planteles.json")     # team_id -> plantel con números
# team_id -> promedios por partido (remates, córners, posesión, tackles...).
# Sale del mismo /summary que ya se pide para los córners del modelo: no
# cuesta un pedido más, cuesta dejar de descartar 22 de las 25 métricas.
ESTADISTICAS = Path("data/estadisticas.json")
CUOTAS = Path("data/cuotas.json")   # historia de la cuota de mercado, se acumula
PROPS_JUGADOR = Path("data/props_jugadores.json")  # historia de líneas de jugador (Bet365)
ESTADISTICAS_N = 8                          # sobre cuántos partidos promedia
                            # (PJ, goles, asistencias, remates, tarjetas por
                            # jugador) sumando liga doméstica + competición.
                            # Es un archivo APARTE de data/equipos.json a
                            # propósito: equipos.json es prosa cualitativa de
                            # carga manual y el cron no lo toca nunca. Acá van
                            # los números, que sí son automáticos.
CACHE_DISCIPLINA = Path("data/cache_disciplina.json")  # event_id -> {team_id:
                            # {fouls,corners,cards}}. Persiste ENTRE corridas
                            # (a diferencia de todos los otros caches, que
                            # son solo de la corrida actual): /summary pesa
                            # ~400KB por partido — pedirlo de nuevo cada vez
                            # para partidos que ya terminaron hace rato sería
                            # tirar minutos de corrida a la basura. Un evento
                            # ya jugado no cambia, así que cachearlo para
                            # siempre es seguro.
CACHE_TEMPORADAS = Path("data/cache_temporadas")  # slug-season.json con los
                            # resultados de una temporada YA TERMINADA. Persiste
                            # ENTRE corridas: una temporada pasada no cambia
                            # nunca, y sin esto el ajuste de fuerzas pediría
                            # TEMPORADAS_HISTORIA temporadas por competición en
                            # cada corrida — dos veces por día, para siempre, la
                            # misma respuesta. La temporada en curso no se
                            # cachea, justamente porque sí cambia.
CACHE_LIGAS = Path("data/cache_ligas.json")  # team_id -> slug de su liga local
                            # ("bra.1"). Persiste ENTRE corridas, como
                            # cache_disciplina: un equipo no cambia de liga en
                            # mitad de la temporada, así que preguntarlo una
                            # vez alcanza para siempre.
RUTA_HISTORIA = Path("data/historia_equipos.json")
                            # Historia larga por equipo, ya cruzada a ids de
                            # ESPN. La escribe `historia_equipos.py` A MANO —
                            # el cron NO la baja: son 22 pedidos a
                            # football-data por corrida para un archivo que
                            # cambia una vez por semana. Si no está, todo se
                            # comporta como antes de que existiera.
DISCIPLINA_N = 3           # últimos N partidos por equipo para córners/
                            # faltas/tarjetas — más chico que los 5 de forma()
                            # a propósito, por el costo de /summary.
ARG_TZ = datetime.timezone(datetime.timedelta(hours=-3))
DIAS_ADELANTE = 7          # próximos N días (incluye hoy) — coincide con
                            # los 7 días que muestra la tira en el frontend
TEMPORADAS_H2H = 3         # temporadas hacia atrás para el historial directo
RECENCY_ALPHA = 0.90       # peso por antigüedad en promedio_condicion()
                            # (competiciones sin red de cruces suficiente
                            # para calibrar fuerzas).
                            # 0.90: el partido 13 atrás pesa ~25% del más
                            # reciente. Gentil a propósito — es un ajuste
                            # fino, no un reemplazo del promedio.

# Competiciones con red de cruces suficiente (todos-contra-varios) como
# para calibrar la fuerza de ataque/defensa de cada equipo contra la de
# sus rivales, en vez de solo promediar los partidos propios. Copa
# Argentina es eliminación directa desde el arranque — no hay red de
# cruces repetidos, sigue con el promedio simple.
CON_FUERZAS = {"arg.1", "bra.1", "eng.1", "fra.1",
               "conmebol.libertadores", "conmebol.sudamericana"}
TEMPORADAS_HISTORIA = 5    # cuántos años calendario de resultados se le dan
                            # a fuerzas_equipos(). Hasta el 2026-08-24 era 1
                            # de hecho, porque resultados_temporada() pide del
                            # 1/1 a hoy: el ajuste arrancaba de cero cada enero.
                            # Va de la mano de VIDA_MEDIA_DIAS -- ver ahí por qué
                            # ninguno de los dos sirve sin el otro.
VIDA_MEDIA_DIAS = 300      # en fuerzas_equipos(): un partido de hace 300
                            # días pesa la mitad que uno de hoy; uno de
                            # hace 600, un cuarto. Por calendario, no por
                            # ronda, porque acá se mezclan los partidos
                            # de todos los equipos a la vez.
                            #
                            # Era 45 hasta el 2026-08-24. El par (5 temporadas,
                            # 300 días) lo eligieron arg y bra POR SEPARADO,
                            # barriendo 1-5 temporadas x 45-400 días contra la
                            # tasa base, walk-forward, eligiendo solo con datos
                            # anteriores a 2022 y confirmando con 2022+.
                            #
                            # Los dos números van juntos o no van. Medido en
                            # arg.1, % de la ventaja del mercado capturada
                            # (negativo = peor que apostar siempre al local):
                            #
                            #                    vida 45   vida 300
                            #   1 temporada       -26.8%     -44.7%
                            #   5 temporadas      -32.7%     +13.0%
                            #
                            # Más historia con olvido rápido EMPEORA: un partido
                            # de hace ocho meses pesaba 0.02 y la historia extra
                            # se tiraba. Olvido lento sin historia extra también
                            # empeora: diluye lo poco que hay. Si algún día se
                            # baja TEMPORADAS_HISTORIA, hay que bajar esto.
MIN_PARTIDOS_FUERZA = 3    # un equipo con menos partidos que esto en toda
                            # la temporada no tiene fuerza confiable
PRIOR_FUERZA = 3           # "partidos fantasma" a nivel promedio (fuerza 1.0)
                            # que se suman en fuerzas_equipos() para regularizar.
                            #
                            # OJO: esto es el RESPALDO. Cada liga tiene el suyo
                            # en COMPETICIONES["prior"], porque el valor bueno
                            # depende de cuantos partidos por equipo hay y eso
                            # cambia por torneo. Las copas usan este 3, que no
                            # se midio: ahi el prior empuja hacia el ancla
                            # domestica y no hacia el promedio, asi que
                            # extrapolar desde las ligas seria inventar.
                            #
                            # Barrido el 2026-08-24 (5 temporadas, vida 300,
                            # rho por liga), % de la ventaja del mercado
                            # capturada, eligiendo con datos < 2022:
                            #
                            #   prior   arg.1 DEV   arg.1 TEST   bra.1 DEV
                            #       3      44.7%       24.8%       57.2%
                            #       8      49.6%       37.7%       60.3% <-
                            #      12      50.3% <-    42.2%       60.3%
                            #      20      49.1%       45.6%       58.2%
                            #
                            # Argentina pide mas regularizacion que Brasil
                            # porque tiene la MITAD de partidos por equipo:
                            # 28-30 equipos a una vuelta contra 20 ida y
                            # vuelta. Es la misma sobre-parametrizacion que
                            # Elo evitaria usando un parametro por equipo en
                            # vez de dos — pero regularizar la ataca sin tirar
                            # la separacion ataque/defensa.
                            #
                            # En ROI no se detecto diferencia: todos los z
                            # entre -0.8 y +0.7 sobre ~1200 apuestas. Eso NO
                            # dice que no sirva, dice que esa prueba tiene un
                            # error de +/-4% y no puede verlo. Se aplica por la
                            # mejora de calibracion, que si esta medida.
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
# `rho` es la corrección de Dixon-Coles para los marcadores bajos (0-0,
# 1-0, 0-1, 1-1), que Poisson puro estima mal. Es propio de cada liga:
# depende de cómo se juega.
#
# Barrido el 2026-08-24 con 5 temporadas y vida 300, walk-forward,
# eligiendo con datos anteriores a 2022. Los dos mínimos quedaron
# ADENTRO de la grilla (-0.28 a 0.15), no en un borde:
#
#     rho     arg.1 DEV   bra.1 DEV
#    -0.12     0.63518     0.61113
#    -0.08     0.63481     0.61055
#    -0.05     0.63473 <-  0.61029
#     0.00     0.63495     0.61021 <-
#     0.05     0.63564     0.61055
#     0.10     0.63678     0.61132
#
# arg.1 estaba en 0.05, que es peor que el -0.05 medido. Ese 0.05 tuvo
# su propia medición antes (162 partidos para elegir, 108 para evaluar),
# y el barrido de 5 temporadas la dio vuelta: si volvés a leer que
# "+0.05 está MEDIDO", es un comentario viejo que sobrevivió a su dato.
#
# Las copas quedan en 0.00 (Poisson sin corrección) por falta de muestra
# propia, no por medición: con 52-56 partidos evaluables no alcanza para
# ajustar nada. Se pone el neutro y no el negativo del diseño original
# (-0.10 / -0.14, que nunca tuvo respaldo en datos) porque las dos ligas
# que sí se pudieron medir dicen que ese negativo estaba mal. Recalibrar
# cuando haya más temporada jugada.
# ══════════════════════════════════════════════════════════════════════
# ESCALA DE λ — el modelo exageraba su rango de goles
#
# Medido el 2026-08-30 (`medir_compresion.py`) sobre 6270 partidos de
# arg, walk-forward, partiendo por λ PREDICHO — la vista que ninguna
# medición anterior usaba:
#
#     franja λ      n   predicho   real   desvío
#      0.0-2.0    1583      1.80    2.07    +0.27
#      2.4-2.6     931      2.49    2.31    -0.18
#      3.0-3.3     129      3.11    2.44    -0.67
#
#     pendiente de real contra predicho: 0.368 ± 0.108
#
# El modelo predecía un rango de 1.80 a 3.11 goles donde la realidad va
# de 2.07 a 2.44: estiraba su rango ~2.7 veces de más. Donde decía
# mucho gol pasaban menos, y donde decía poco gol pasaban más.
#
# No es atenuación estadística: un modelo PERFECTO simulado con la misma
# muestra y la misma distribución de λ da pendiente 0.944 ± 0.091, y uno
# que exagera 2.7x da 0.335 ± 0.091. El real (0.368) está en el segundo
# grupo. Es la regla del repo aplicada — comparar contra el ruido, no
# contra cero.
#
# Por qué no se había visto nunca: EN AGREGADO SE CANCELA. Los partidos
# inflados y los desinflados se compensan, así que `medir_historico.py`
# (que parte por banda de probabilidad del 1X2) y `barrido_lambda.py`
# (que mide over 2.5 en total: 0.357 real contra 0.375 predicho, bien
# calibrado) daban los dos "sin problema".
#
# La corrección encoge λ hacia la media de la liga:
#
#     λ_corregido = μ_liga + k · (λ_modelo − μ_liga)
#
# `k` se barrió con train/test temporal (`barrido_escala_lambda.py`,
# train < 2022 elige, test >= 2022 confirma). Test PAREADO sobre el
# Brier de goles en test, contra producción (k=1.00):
#
#     arg (n=2583, k=0.50)   +0.00372 ± 0.00351   +2.1 e.e.   mejora
#     eng (n=1717, k=0.60)   +0.00245 ± 0.00342   +1.4 e.e.   misma dirección
#
# El 1X2 no se daña en ninguna de las dos (+0.4 y −0.6 e.e., dentro del
# ruido), y el óptimo cae DENTRO de la grilla en las dos — exagerar más
# (k=1.15) empeora, así que no es un borde.
#
# LO QUE ESTA CORRECCIÓN NO HACE, y hay que decirlo: **no mejora el
# ROI.** Medido en eng, el ROI de over/under con k=0.60 no mejora sobre
# producción. Entra porque corrige un defecto medido en un número que la
# app MUESTRA en pantalla ("2.7 goles esperados entre los dos"), no
# porque haga ganar plata. Mejorar el Brier y ganar plata no son la
# misma cosa — este repo ya se comió esa lección con
# `medir_encogimiento.py`.
#
# Una competición sin `escala` medida NO se corrige (queda en 1.0). Las
# copas no tienen cuotas históricas en football-data, así que no se
# pudieron medir, y extrapolar el k de una liga a una copa sería
# inventar — el mismo criterio que ya rige para `prior`.
ESCALA_DEFECTO = 1.0


def escala_de(slug):
    """El `k` de corrección de λ de una competición, o 1.0 si no se midió."""
    return (COMPETICIONES.get(slug) or {}).get("escala", ESCALA_DEFECTO)


def centro_de(slug):
    """Hacia dónde encoge `corregir_escala`: la media de λ de la liga.

    Es una constante medida y no un cálculo en vivo, por dos razones:

    - **Tiene que ser el MISMO valor con el que se midió la mejora.**
      El barrido que aprobó cada `k` usó la media de λ del train de esa
      liga; centrar en otro punto en producción mediría una cosa y
      aplicaría otra, que es el error del devig de §6vicies.
    - La media de la grilla del día son 5 a 15 partidos: demasiado
      ruidosa para un centro, y reintroduciría por la ventana la
      varianza que la corrección viene a sacar.
    """
    return (COMPETICIONES.get(slug) or {}).get("centro")


def diferencia_de(slug):
    """El `k` que conserva de (λ_local − λ_visita), o 1.0 si no se midió.

    Segundo eje del mismo defecto que `escala_de`. Aquella corrige
    **cuántos goles hay**; esta corrige **cuánta diferencia hay entre
    los dos equipos**, que es lo que mueve el 1X2.

    Medido el 2026-08-30 (`barrido_diferencia.py`), train/test temporal
    con test pareado sobre el Brier del 1X2:

        arg   k=0.95   +0.00046 ± 0.00039  (+2.4 e.e.)   MEJORA
        bra   k=1.00 es óptimo en train Y test
        eng   k=1.00 es óptimo en train Y test
        fra   train dice 0.95 pero en test EMPEORA

    **Solo pasa en Argentina, y eso encaja con todo lo demás.** arg
    juega 27 partidos por equipo a una sola vuelta con 28-30 equipos;
    Brasil juega 38 a doble vuelta. Con menos partidos por equipo, el
    ruido de estimación se lee como diferencia real entre equipos, y el
    modelo los separa más de lo que la realidad los separa. Es la misma
    raíz que explica que arg capture 7.7% de la ventaja del mercado
    contra 45.4% de bra y 80.9% de eng/fra, y que el modelo "opine más
    que el mercado" ahí (7.70% contra 7.02%).

    Es también la causa del "1X2 de favoritos sobreconfiados" que este
    repo arrastraba documentado sin explicación: `medir_calibracion.py`
    sobre lo publicado daba "1X2 local: decimos 43.5%, pasa 25.4%".
    """
    return (COMPETICIONES.get(slug) or {}).get("diferencia", 1.0)


def encoger_diferencia(lh, la, k):
    """Acerca los dos λ entre sí SIN mover el total de goles.

    Conservar el total es lo que hace que esta corrección sea
    independiente de `corregir_escala`: una toca el eje "cuántos goles",
    la otra el eje "quién gana". Si esta moviera el total, las dos se
    pisarían y ninguna de las dos mediciones valdría.
    """
    if k == 1.0:
        return lh, la
    total, diff = lh + la, (lh - la) * k
    return max(0.05, (total + diff) / 2), max(0.05, (total - diff) / 2)


def corregir_escala(lh, la, mu, k):
    """λ encogido hacia `mu`, manteniendo el reparto entre local y visita.

    Se corrige el TOTAL y se reparte con la misma proporción que tenía:
    lo que se midió mal es cuántos goles hay en el partido, no quién
    ataca más. Escalar lh y la por separado cambiaría también eso, que
    es otra corrección y no está medida.
    """
    total = lh + la
    # Sin centro medido no se corrige: una liga que no se barrió se
    # comporta exactamente como antes de que esto existiera.
    if total <= 0 or k == 1.0 or not mu:
        return lh, la
    nuevo = max(0.4, mu + k * (total - mu))
    f = nuevo / total
    return lh * f, la * f


COMPETICIONES = {
    # `conf` decide el tamano de la apuesta: en index.html, >=72 da cuarto
    # de Kelly, >=60 da octavo. arg.1 estuvo en 75 —el mismo escalon que
    # Brasil— hasta el 2026-08-25, y la medicion no lo sostiene.
    #
    # Walk-forward sobre 2583 partidos de la era 2022+, con vida media 300
    # y devig Shin: Argentina captura el 7.7% de la ventaja del mercado
    # sobre la tasa base y Brasil el 45.4%. En ventaja absoluta son 0.0013
    # contra 0.0190 — una quinceava parte.
    #
    # La causa no es que el modelo falle mas ahi: es que en el futbol
    # argentino hay menos para saber. El propio Pinnacle le gana a
    # "siempre local" por 0.9 puntos de acierto (43.7% contra 42.8%),
    # cuando en Brasil le saca 3.6. Nuestra distancia contra el cierre es
    # de las mas chicas de las 26 ligas medidas; lo que falta es senal.
    #
    # 70 y no 55: es el ajuste conservador. Reconoce la diferencia medida
    # sin recortar a un cuarto la mitad de la grilla. Queda en el mismo
    # escalon que las copas CONMEBOL, que tampoco calibran bien.
    # `escala`: ver el bloque ESCALA_DEFECTO, arriba. Medido con
    # train/test sobre 6270 partidos; test pareado del Brier de goles
    # contra producción: +0.00372 ± 0.00351 (2.1 e.e.), sin dañar el 1X2.
    "arg.1": {"nombre": "Liga Profesional Argentina", "rho": -0.05, "conf": 70,
              "prior": 12, "escala": 0.50, "centro": 2.266,
              # Unica liga donde el modelo exagera la diferencia entre
              # equipos: 27 partidos por equipo a una vuelta contra los
              # 38 de Brasil. Ver diferencia_de(), arriba.
              "diferencia": 0.95,
              "corners": 9.4, "fouls": 25.5, "cards": 5.4},
    # Brasil entra el 2026-08-24. Es la liga donde el motor demostrablemente
    # funciona: captura el 61% de la ventaja del mercado sobre la tasa base
    # contra el 13% de arg.1, y le gana a "siempre local" en tasa de acierto
    # (47.4% vs 46.7%). Hasta hoy el modelo corria SOLO en la liga donde
    # falla. Los promedios salen de medir 60 partidos de bra.1 2026 via
    # /summary, no de copiar los de Argentina.
    # `escala` 0.50 / `centro` 2.371: mismo barrido. Brier de goles
    # en test 0.49676 contra 0.50187 de producción. Tercera liga
    # independiente que mejora con k < 1, y la tercera donde el
    # óptimo cae dentro de la grilla.
    "bra.1": {"nombre": "Brasileirão Série A", "rho": 0.00, "conf": 75,
              "prior": 8, "escala": 0.50, "centro": 2.371,
              "corners": 10.0, "fouls": 25.1, "cards": 4.1},
    "conmebol.libertadores": {"nombre": "CONMEBOL Libertadores", "rho": 0.00, "conf": 65,
              "corners": 9.8, "fouls": 24.0, "cards": 5.0},
    "conmebol.sudamericana": {"nombre": "CONMEBOL Sudamericana", "rho": 0.00, "conf": 65,
              "corners": 9.6, "fouls": 24.5, "cards": 5.2},
    # ── Europa, agregada el 2026-08-25 ──────────────────────────────
    #
    # Por que estas dos y no otras. Se midieron TRES cosas sobre las 26
    # ligas del barrido, y hacian falta las tres juntas:
    #
    #                atraso (de 26)   jugadores/partido   k de corners
    #   eng.1          0.0137  (6o)         41               14.2
    #   fra.1          0.0147  (9o)         27               23.0
    #   ita.1          0.0167 (20o)         38               —
    #   arg.1          0.0147 (11o)          0            tope (200)
    #
    # Italia y Espana tienen mercado profundo y el modelo anda mal ahi
    # (20o y 18o): mercado grande donde peor jugamos no es una
    # oportunidad. Japon y Mexico son 1o y 2o y no tienen mercado de
    # jugadores. Estas dos ganan en las tres columnas.
    #
    # La tercera columna es la que decide, y es la que Argentina no
    # puede tener: ARG.csv y BRA.csv no traen NI UNA columna de
    # estadisticas por partido, y E0/F1 las traen todas en 11
    # temporadas. Con 246 partidos por equipo el `k` de corners baja de
    # 200 (el tope, o sea "no distingo un equipo de otro") a 14. Es la
    # diferencia entre publicar el promedio de la liga y tener opinion.
    #
    # rho y prior salen de barridos walk-forward propios sobre 4180 y
    # 3857 partidos con cuota de cierre de Pinnacle, eligiendo con datos
    # < 2022 y evaluando en >= 2022. NO se copiaron de Argentina.
    #
    # OJO con el prior de Inglaterra: el primer barrido (3,8,12,20,30)
    # dio 3, que era el borde de la grilla — o sea nada. Extendida a
    # 0.5/1/2 aparecio el optimo real adentro. Es la tercera vez que
    # pasa en este repo; ver la regla en CLAUDE.md.
    #
    #   conf 80: las dos capturan ~81% de la ventaja del mercado sobre
    #   la tasa base fuera de muestra, contra 45.4% de Brasil (conf 75)
    #   y 7.7% de Argentina (conf 70). Es el escalon de cuarto de Kelly,
    #   igual que Brasil — el numero mas alto reconoce la medicion sin
    #   inventar un escalon nuevo.
    # `escala` 0.60: mismo barrido que arg. El test pareado da +0.00245
    # ± 0.00342 (1.4 e.e.) — la misma dirección que arg pero sin
    # despegarse del ruido, con 1717 partidos de test contra 2583. Entra
    # porque el óptimo cae dentro de la grilla en las dos ligas y en las
    # dos el 1.00 de producción es peor que cualquier k < 1.
    "eng.1": {"nombre": "Premier League", "rho": -0.02, "conf": 80,
              "prior": 5, "escala": 0.60, "centro": 2.785,
              "corners": 10.33, "fouls": 21.51, "cards": 3.91},
    # `escala` 0.60 / `centro` 2.617: cuarta liga, misma direccion.
    # Brier de goles en test 0.49176 contra 0.49343 de produccion.
    "fra.1": {"nombre": "Ligue 1", "rho": -0.05, "conf": 80,
              "prior": 8, "escala": 0.60, "centro": 2.617,
              "corners": 9.47, "fouls": 24.22, "cards": 3.98},
    # ── Japon, agregada el 2026-09-02 ───────────────────────────────
    #
    # Entra por una razon y una sola: es la liga con MEJOR punto
    # estimado de ROI de las seis medidas, y era la unica de esas seis
    # que estaba medida y no estaba en la app.
    #
    #     jpn  +2.78% ± 7.67   (ruido)   <- no estaba
    #     eng  +1.01% ± 8.92   (ruido)
    #     mex  -3.46% ± 7.50   (ruido)   <- medido el 2026-09-02, no entra
    #     fra  -5.22% ± 8.71   (ruido)
    #     bra  -9.13% ± 7.32   negativo de verdad
    #     arg  -9.17% ± 6.44   negativo de verdad
    #
    # `historico.py` ya la traia "SOLO PARA MEDIR" desde el 2026-08-31 y
    # decia textual que "estar en COMPETICIONES es otra decision". Se
    # midio y la decision nunca se tomo: la app cubria cuatro ligas, dos
    # de ellas medidas perdiendo, y ninguna donde la medicion no dijera
    # que perdemos.
    #
    # OJO con como se leyo esto: primero se ranquearon las ligas por
    # `aporte` (mejora de Brier sobre la tasa base) y Mexico salia
    # primera con +5.5% contra +5.2% de Japon. Al medir su ROI dio
    # -3.46%. Es la leccion de TRASPASO §5 otra vez: calibrar no es
    # ganar plata, y el orden por Brier no es el orden por plata.
    #
    # `escala` 0.60 / `centro` 2.695: quinta liga, misma direccion que
    # las otras cuatro. En el barrido (4499 partidos, train 3103 / test
    # 1396) TODO k<1 le gana a produccion en test, y 1.00 es el peor de
    # la grilla salvo 1.15. Train elige 0.60 y test 0.50 — no coinciden,
    # asi que se toma el de train, que es el criterio conservador y el
    # mismo que se uso en eng y fra.
    #
    # `conf` 70 y no 80: el ROI de jpn es RUIDO (+2.78% ±7.67), no una
    # ventaja demostrada. 70 cae en el escalon de octavo de Kelly, no de
    # cuarto. Es el mismo movimiento que se le hizo a arg.1 cuando su
    # medicion no sostuvo el 75.
    #
    # corners/fouls/cards medidos sobre 60 partidos de ESPN el
    # 2026-09-02: football-data trae Japon en formato "unico", que no
    # publica estadisticas por partido, asi que no salen de ahi.
    "jpn.1": {"nombre": "J.League", "rho": 0.00, "conf": 70,
              "prior": 8, "escala": 0.60, "centro": 2.695,
              "corners": 9.53, "fouls": 22.65, "cards": 2.77},
    # Copa Argentina: salio el 2026-08-25 y VUELVE el 2026-09-02, a
    # pedido de Lucas y con la guarda que antes no existia.
    #
    # Por que salio: es eliminacion directa, sin red de cruces no hay
    # fuerzas que calibrar, y sus lambdas salian de
    # `promedio_condicion()` en vez del motor. Era la unica competicion
    # que se publicaba sin pasar por Dixon-Coles.
    #
    # Por que puede volver: `ancla_de()` ancla a cada equipo de copa a su
    # fuerza en SU liga local — es lo que hace andar la Libertadores. Un
    # equipo de Liga Profesional llega a la Copa con sus ~7 fechas ya
    # calibradas.
    #
    # Lo que queda y por eso lleva guarda: la Copa cruza primera con
    # Federal A y Primera B, divisiones que la app no sigue. Ese equipo
    # no tiene ancla en ningun lado y su lambda vuelve a salir del
    # promedio. `sin_ancla` lo detecta y el partido viaja con
    # `sinAncla: true`; la app no publica probabilidad ahi. Es el mismo
    # criterio que MIN_PARTIDOS, aplicado a un hueco que el conteo de
    # fechas no ve: el equipo TIENE partidos jugados, lo que no tiene es
    # una liga donde hayamos medido su fuerza.
    "arg.copa": {"nombre": "Copa Argentina", "rho": -0.05, "conf": 65,
              "prior": 8,
              "corners": 9.6, "fouls": 26.4, "cards": 4.8},
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


def eventos_extra(slug, key, cache):
    """Los eventos de odds-api.io para esta liga, cacheados por corrida.

    Un pedido por liga, no por partido. Si falla la red, no tira: la
    liga queda sin eventos esta corrida y ningún partido suyo cruza,
    que es el mismo resultado que si no hubiera clave."""
    if slug not in cache:
        try:
            cache[slug] = ME.eventos_de(slug, key)
        except Exception as e:
            print(f"  ! odds-api (eventos {slug}): {e}", file=sys.stderr)
            cache[slug] = []
    return cache[slug]


def mercado_extra_de(partido, eventos, key):
    """Los mercados de Bet365 (odds-api.io) para este partido, o None.

    None si falta la clave, no hay eventos, el fixture no cruza, o el
    pedido de odds falla — en los cuatro casos el partido queda igual
    que antes de que esta fuente existiera. Ver mercado_extra.py."""
    if not key or not eventos:
        return None
    eid = ME.cruzar_fixture(partido, eventos)
    if not eid:
        return None
    try:
        datos, _ = ME.odds_de(eid, key)
    except Exception as e:
        print(f"  ! odds-api (odds {eid}): {e}", file=sys.stderr)
        return None
    return datos or None


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


def roster(slug, team_id):
    """/teams/{id}/roster: el plantel entero con estadísticas, en UN solo
    pedido (~0,5s, 38-40 jugadores).

    Medido el 2026-08-20 contra la API real, porque la app afirmaba lo
    contrario — decía que las estadísticas pedían un llamado por jugador
    y que serían "unos 50 por pestaña". Es falso: vienen todas en la
    misma respuesta, anidadas en athletes[].statistics.

    Lo que NO sirve de este endpoint, también verificado: `injuries`
    viene vacío y `status` dice "Active" incluso para un jugador con
    rotura de ligamento cruzado (Carboni, Racing). Y el campo `coach`
    es una lista histórica vieja, no el DT actual (para River devolvió
    Gorosito/Cappa/Lopez/Almeyda, no a Coudet). Bajas y DT siguen
    saliendo del research, no de acá."""
    d = api(f"{SITE_V2}/{slug}/teams/{team_id}/roster")
    if not d:
        return []
    atletas = d.get("athletes") or []
    # Algunas ligas agrupan por posición ({position, items:[...]}) y otras
    # devuelven la lista plana. Se aceptan las dos formas.
    if atletas and isinstance(atletas[0], dict) and "items" in atletas[0]:
        atletas = [a for g in atletas for a in (g.get("items") or [])]
    return [stats_jugador(a) for a in atletas]


# Las únicas ligas domésticas que este pipeline sigue directamente — el
# resto de COMPETICIONES son copas. slugs_plantel() usa esto para saber
# si un partido YA es de liga (y entonces no hace falta, ni corresponde,
# sumar otra liga encima).
LIGAS_DOMESTICAS = {"arg.1", "bra.1", "eng.1", "fra.1"}


def slugs_plantel(slug_consulta, slug_liga):
    """De qué competiciones pedir el roster de un equipo.

    La liga doméstica se suma cuando el partido es de COPA — ahí sí
    falta muestra (~5 partidos) y la liga la completa (~25). Cuando el
    partido YA es de liga, no se suma nada más: `slug_liga` en ese caso
    solo puede ser la misma liga (deduplicada abajo) o, en un equipo
    recién ascendido o descendido, la categoría de la que salió —
    ESPN cachea el `defaultLeague` viejo y no lo actualiza.

    Encontrado el 2026-08-23: Estudiantes de Río Cuarto ascendió a Liga
    Profesional (arg.1), pero ESPN seguía devolviendo arg.2 (Primera
    Nacional) como su liga local. slugs_plantel("arg.1", "arg.2") sumaba
    las dos categorías del mismo jugador — no copa más liga, sino dos
    categorías distintas — y un mediocampista terminó con 52 partidos
    jugados en vez de los 16 reales de esta temporada en arg.1.

    COMPETICIONES es la única liga doméstica que este pipeline sigue
    directamente (arg.1); todo lo demás que aparece como slug_consulta
    es copa."""
    slugs = [slug_consulta]
    if slug_liga and slug_liga != slug_consulta and slug_consulta not in LIGAS_DOMESTICAS:
        slugs.append(slug_liga)
    return slugs


def solo_los_que_jugaron(plantel):
    """Saca del plantel a los que no jugaron ningún partido.

    Es un tercio del roster (juveniles, recién llegados, arqueros
    suplentes) y no aporta nada a la lectura de un partido. Se filtra
    acá y no en la app porque el archivo lo baja un teléfono. Si no
    jugó NADIE se devuelve entero: dejar la pestaña vacía sería peor
    que mostrar un plantel sin minutos."""
    jugaron = [j for j in plantel if j.get("pj", 0) > 0]
    return jugaron if jugaron else list(plantel)


def slugs_de_equipos(apariciones):
    """team_id -> competiciones de las que pedirle el roster, sin repetir.

    Recibe (team_id, slug_del_partido, slug_liga_domestica) por cada vez
    que un equipo aparece en la ventana. Se acumulan los SLUGS y no los
    planteles a propósito: un equipo con dos partidos de la misma
    competición devolvería el mismo roster dos veces, y fusionarlo
    consigo mismo duplicaría todos sus números."""
    mapa = {}
    for tid, slug, slug_liga in apariciones:
        vistos = mapa.setdefault(str(tid), set())
        vistos.update(slugs_plantel(slug, slug_liga))
    return {tid: sorted(s) for tid, s in mapa.items()}


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


def jugados_de_resultados(team_id, resultados):
    """Adapta la lista cruda de resultados_temporada() -- home/away como
    ID, sin nombre de rival, fecha como date -- al formato que usan
    forma()/forma_general() para UN equipo puntual.

    Existe para no pedir nada nuevo: esa lista ya se baja para anclar la
    fuerza de ataque/defensa de cada equipo a su liga local (ancla_de) en
    Libertadores y Sudamericana -- se pide igual, la única diferencia es
    que hoy se tira después de calcular las fuerzas. Reusarla acá le suma
    forma doméstica real a un equipo sudamericano, sin ningún pedido de
    red adicional."""
    tid = str(team_id)
    out = []
    for p in resultados:
        h, a = str(p["home"]), str(p["away"])
        if tid not in (h, a):
            continue
        local = h == tid
        gf, gc = (p["gh"], p["ga"]) if local else (p["ga"], p["gh"])
        fecha = p["fecha"]
        fecha = fecha.isoformat() if hasattr(fecha, "isoformat") else fecha
        out.append({
            "fecha": fecha, "local": local, "gf": gf, "gc": gc,
            "home": p.get("home_nombre", ""), "away": p.get("away_nombre", ""),
        })
    out.sort(key=lambda x: x["fecha"], reverse=True)
    return out


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


def stats_jugador(atleta):
    """Aplana un jugador de /roster: los números vienen anidados en
    splits.categories[].stats[], repartidos entre 'general', 'offensive'
    y 'goalKeeping' sin que la categoría importe para leerlos."""
    crudos = {}
    sp = (atleta.get("statistics") or {}).get("splits") or {}
    for cat in sp.get("categories", []) or []:
        for s in cat.get("stats", []) or []:
            crudos[s.get("name")] = s.get("value")

    def num(k):
        try:
            return float(crudos.get(k) or 0)
        except (TypeError, ValueError):
            return 0.0

    return {
        "id": str(atleta.get("id", "")),
        "nombre": atleta.get("displayName", ""),
        "pos": (atleta.get("position") or {}).get("abbreviation", ""),
        # El dorsal ya venia en la respuesta y se tiraba. Mirassol tiene
        # DOS Carlos Eduardo en el mismo plantel: en una lista de dos
        # equipos el nombre no alcanza ni sabiendo la liga, y el escudo
        # tampoco cuando los dos homonimos son del mismo club. ESPN lo
        # publica para 32 de 35 jugadores; el que no lo tiene queda con
        # cadena vacia, que la app no dibuja.
        "dorsal": str(atleta.get("jersey") or ""),
        "pj": num("appearances"),
        "goles": num("totalGoals"),
        "asist": num("goalAssists"),
        "remates": num("totalShots"),
        "al_arco": num("shotsOnTarget"),
        "faltas": num("foulsCommitted"),
        "amarillas": num("yellowCards"),
        "rojas": num("redCards"),
    }


# Los campos que se suman al fusionar dos competiciones. El resto
# (nombre, posición) identifica al jugador y se conserva tal cual.
SUMABLES = ("pj", "goles", "asist", "remates", "al_arco",
            "faltas", "amarillas", "rojas")


def fusionar_planteles(*listas):
    """Suma el mismo jugador a través de competiciones.

    Las estadísticas de /roster son POR COMPETICIÓN: el mismo River da
    5 partidos con el slug de la Liga y 3 con el de la Sudamericana.
    Ninguno de los dos solo sirve para pesar una baja — 'jugó 5 de 5'
    no significa nada si además jugó 3 de copa. Es el mismo problema
    que resolvió forma_general() para la forma reciente."""
    por_id = {}
    for lista in listas:
        for j in lista or []:
            base = por_id.get(j["id"])
            if base is None:
                por_id[j["id"]] = dict(j)
                continue
            for k in SUMABLES:
                base[k] = base.get(k, 0) + j.get(k, 0)
    # El que más juega primero: la pestaña Plantel muestra los de arriba,
    # y un plantel de 40 encabezado por suplentes no informa nada.
    return sorted(por_id.values(), key=lambda j: -j["pj"])


def peso_goleador(plantel):
    """Qué fracción de los goles del equipo puso cada jugador.

    Sin este número la baja de un goleador y la de un suplente se leen
    igual en el análisis. Con él, 'no está Rodallega' es 'no está el 57%
    de los goles del equipo'."""
    total = sum(j.get("goles", 0) for j in plantel)
    if not total:
        return {j["id"]: 0.0 for j in plantel}
    return {j["id"]: j.get("goles", 0) / total for j in plantel}


# Lo que se guarda de cada partido, y con qué nombre nuestro. ESPN manda
# 25 métricas por equipo en el mismo response que ya se pedía para los
# córners: se estaban tirando 22. Esto no cuesta un pedido más.
#
# No están todas a propósito — pases largos, centros y porcentajes
# derivados se pueden recalcular o no se miran nunca, y cada campo extra
# es peso que baja un teléfono.
METRICAS_PARTIDO = {
    "remates":   "totalShots",
    "al_arco":   "shotsOnTarget",
    "corners":   "wonCorners",
    "faltas":    "foulsCommitted",
    "posesion":  "possessionPct",
    "offsides":  "offsides",
    "atajadas":  "saves",
    "tackles":   "totalTackles",
    "pases":     "accuratePasses",
    "pases_tot": "totalPasses",
}


def estadisticas_equipo(crudo):
    """{team_id: {metrica: valor}} de UN partido, desde /summary.

    Lo que ESPN no trajo queda en None, nunca en 0: en pantalla un cero
    medido y un dato ausente se leen igual, y no son lo mismo. Un equipo
    que remató 0 veces es una noticia; uno cuyo partido no tiene
    estadísticas cargadas, no.
    """
    out = {}
    for t in (crudo or {}).get("boxscore", {}).get("teams", []) or []:
        tid = t.get("team", {}).get("id", "")
        s = {x.get("name"): x.get("displayValue") for x in t.get("statistics", [])}

        def num(k):
            v = s.get(k)
            if v is None:
                return None
            try:
                # Viene como texto y en algunas ligas con símbolo o
                # separador de miles: "58.7%", "1,203".
                return float(str(v).replace("%", "").replace(",", ""))
            except (TypeError, ValueError):
                return None

        fila = {n: num(k) for n, k in METRICAS_PARTIDO.items()}
        am, ro = num("yellowCards"), num("redCards")
        fila["tarjetas"] = None if am is None and ro is None else (am or 0) + (ro or 0)
        out[tid] = fila
    return out


# Lo que se guarda de cada jugador en cada partido, en orden. Va como
# lista y no como diccionario a proposito: son ~32 jugadores por partido
# por 179 partidos, y repetir once nombres de clave por fila multiplica
# por seis lo que ocupa el cache.
CAMPOS_JUGADOR_PARTIDO = ("remates", "al_arco", "faltas", "amarillas",
                          "goles", "asist", "titular")

_STAT_JUGADOR = {
    "remates":   "totalShots",
    "al_arco":   "shotsOnTarget",
    "faltas":    "foulsCommitted",
    "amarillas": "yellowCards",
    "goles":     "totalGoals",
    "asist":     "goalAssists",
}

# Cuantos partidos hacia atras se guarda la serie de un jugador. Es la
# misma ventana que usan las estadisticas de equipo.
SERIE_N = 8


def jugadores_partido(crudo):
    """{jugador_id: [remates, al_arco, faltas, amarillas, goles, asist,
    titular]} de UN partido, desde rosters[] del mismo /summary.

    Existe por el pedido original de Lucas: "no es lo mismo un jugador
    que remato 5 veces en 5 partidos pero hizo 4 en 1". El acumulado de
    temporada que trae el roster no distingue esos dos casos — y encima
    puede ser de antes de una lesion, que es como el plantel decia que
    Driussi venia jugando y convirtiendo cuando llevaba meses afuera.

    Solo entran los que jugaron: un cero de alguien que estuvo en el
    banco no es un cero, es una ausencia, y promediarlo hundiria su
    numero.
    """
    out = {}
    for lado in (crudo or {}).get("rosters", []) or []:
        for p in lado.get("roster") or []:
            pid = str((p.get("athlete") or {}).get("id") or "")
            if not pid or pid == "None":
                continue
            s = {x.get("name"): x.get("value") for x in (p.get("stats") or [])}
            if not s.get("appearances"):
                continue
            fila = [int(s.get(_STAT_JUGADOR[k]) or 0)
                    for k in CAMPOS_JUGADOR_PARTIDO[:-1]]
            fila.append(1 if p.get("starter") else 0)
            out[pid] = fila
    return out


def once_partido(crudo):
    """{team_id: {"esquema": "4-3-3", "jugadores": [...]}} de UN partido.

    Los ONCE QUE ARRANCARON, con dorsal y puesto, del mismo /summary que
    ya se pide para la serie. Cero pedidos nuevos.

    Existe porque la app dibujaba un once INFERIDO —los que mas partidos
    llevan, acomodados por puesto— con una nota que decia que ESPN no
    publica ni el titular ni el esquema. Eso es cierto para un partido
    que todavia no se jugo y falso para uno jugado: `rosters[]` trae
    `starter`, `jersey`, `formationPlace` y `formation` ("4-2-3-1").
    Verificado el 2026-09-01 contra la API. El ultimo once real es una
    aproximacion mejor que una inferencia, y ademas es un dato.

    Un lado con distinto de once titulares se descarta entero: un dibujo
    con ocho jugadores miente sobre el equipo tanto como uno con cuatro
    delanteros, y es el mismo criterio que ya usa `onceProbable()`.
    """
    out = {}
    for lado in (crudo or {}).get("rosters", []) or []:
        tid = str(((lado.get("team") or {}).get("id")) or "")
        if not tid or tid == "None":
            continue
        once = []
        for pl in lado.get("roster") or []:
            if not pl.get("starter"):
                continue
            at = pl.get("athlete") or {}
            once.append({
                "id": str(at.get("id") or ""),
                "nombre": at.get("displayName") or "",
                "pos": (pl.get("position") or {}).get("abbreviation") or "",
                "dorsal": str(pl.get("jersey") or ""),
            })
        if len(once) != 11:
            continue
        out[tid] = {"esquema": lado.get("formation") or "",
                    "jugadores": once}
    return out


def ultimo_once(team_id, jugados, cache_resumen):
    """El once del partido mas reciente de ese equipo que tenga uno.

    Recorre hacia atras y no se queda solo con el ultimo: un partido
    puede haber quedado sin `rosters` cargados, y en ese caso el once de
    hace una fecha sigue siendo mejor que ninguno. Se devuelve CON su
    fecha y su rival para que la pantalla pueda decir de que partido es
    — un once sin fecha se lee como el once de hoy.
    """
    tid = str(team_id)
    for pr in jugados:
        once = ((cache_resumen.get(pr.get("id")) or {}).get("_once") or {}).get(tid)
        if not once:
            continue
        local = bool(pr.get("local"))
        return {
            "fecha": (pr.get("fecha") or "")[:10],
            "rival": pr.get("away") if local else pr.get("home"),
            "local": local,
            "marcador": pr.get("marcador") or "",
            "esquema": once["esquema"],
            "jugadores": once["jugadores"],
        }
    return None


def serie_jugadores(jugados, cache_resumen, tope=SERIE_N, minimo=1):
    """{jugador_id: {metrica: [valor por partido], "pj": n, "tit": n}}.

    El orden es el de `jugados` — que viene del mas reciente al mas
    viejo — y solo se anotan los partidos que el jugador jugo. Asi la
    serie [0, 4, 0] y la serie [1, 1, 1, 1] se pueden leer una al lado
    de la otra: mismo total de remates, lecturas opuestas.
    """
    out = {}
    metricas = CAMPOS_JUGADOR_PARTIDO[:-1]
    for p in jugados[:tope]:
        filas = (cache_resumen.get(p.get("id")) or {}).get("_jugadores") or {}
        for pid, fila in filas.items():
            d = out.setdefault(pid, {"pj": 0, "tit": 0})
            for n, met in enumerate(metricas):
                d.setdefault(met, []).append(fila[n])
            d["pj"] += 1
            d["tit"] += fila[len(metricas)]
    # Una serie de un solo partido no distingue al regular del explosivo,
    # que es para lo unico que existe. Y son peso: planteles.json lo baja
    # el telefono entero en cada carga.
    return {pid: d for pid, d in out.items() if d["pj"] >= minimo}


# Los campos de la foto que definen si algo se movio. La hora no entra:
# si nada cambio, guardar otra foto es peso sin informacion.
CAMPOS_FOTO = ("local", "empate", "visitante",
               "totalLinea", "totalOver", "totalUnder", "lh", "la", "rho")


def snapshot_cuotas(previas, partidos, ahora):
    """Agrega una foto de la cuota de mercado de cada partido, junto con
    lo que pensaba el modelo en ese mismo momento.

    Existe porque ESPN BORRA el bloque de cuotas cuando el partido
    termina — se verifico el 2026-08-23 sobre 11 partidos ya jugados de
    arg.1: ninguno lo conservaba. O sea que el CLV (haber conseguido un
    precio mejor que el de cierre) no se puede medir hacia atras. Hay
    que ir guardando, y la ultima foto antes del inicio es la de cierre.

    Se acumula y no se borra nunca, como los marcadores: un partido que
    salio de la grilla conserva su historia, que es el unico lugar donde
    va a vivir su cuota de cierre.
    """
    out = {k: list(v) for k, v in (previas or {}).items()}
    for p in partidos or []:
        merc = p.get("mercado")
        if not merc:
            continue
        foto = {"t": ahora}
        for k in CAMPOS_FOTO:
            foto[k] = merc.get(k) if k in merc else p.get(k)
        historia = out.setdefault(p["id"], [])
        if historia and all(historia[-1].get(k) == foto[k] for k in CAMPOS_FOTO):
            continue                      # no se movio nada
        historia.append(foto)
    return out


CAMPOS_PROPS = ("remates", "al_arco")


def snapshot_props(previas, partidos, ahora):
    """Agrega una foto de las líneas de jugador de Bet365 (remates, al
    arco) por partido — igual idea que snapshot_cuotas(), y por el mismo
    motivo: la fuente no guarda el precio una vez jugado el partido.

    Acá es más grave que con la cuota de 1X2: `v3/events` de odds-api.io
    para ligas domésticas solo lista partidos PENDIENTES (150 de 150,
    verificado el 2026-08-26 sobre arg.1) y `status=settled` da cero. O
    sea que no hay ningún historial que pedir hacia atrás — si no se
    guarda antes de que se juegue, se pierde para siempre.

    Sin resultado todavía: esto solo junta precio. Cruzarlo contra lo que
    pasó de verdad (cache_disciplina.json._jugadores) es un paso aparte,
    para cuando haya partidos ya jugados con foto guardada."""
    out = {k: list(v) for k, v in (previas or {}).items()}
    for p in partidos or []:
        mx = p.get("mercadoExtra") or {}
        for met in CAMPOS_PROPS:
            for jugador, datos in (mx.get(met) or {}).items():
                lineas = (datos or {}).get("lineas") or {}
                if not lineas:
                    continue
                clave = f"{p.get('id')}__{met}__{jugador}"
                foto = {"t": ahora, "fecha": p.get("date"), "comp": p.get("comp"),
                        "home": p.get("home"), "away": p.get("away"),
                        "lado": datos.get("lado"), "lineas": dict(lineas)}
                historia = out.setdefault(clave, [])
                if historia and historia[-1].get("lineas") == foto["lineas"]:
                    continue
                historia.append(foto)
    return out


def arbitro_de(crudo):
    """El juez principal del partido, del mismo /summary que ya se pide.

    Se busca por posición y no por orden: `officials` trae también a los
    asistentes y al cuarto árbitro, y el primero de la lista no siempre
    es el que muestra las tarjetas.

    Devuelve "" y no None cuando no viene, para que la ausencia se pueda
    distinguir de "todavía no se preguntó" — ver `resumen_completo()`.
    """
    for o in (crudo or {}).get("gameInfo", {}).get("officials", []) or []:
        if (o.get("position") or {}).get("name") == "Referee":
            return o.get("fullName") or ""
    return ""


def aplanar_resumen(crudo):
    """Lo mismo, más los tres nombres que el motor viene usando desde
    antes (`corners`/`fouls`/`cards`). Se mantienen porque
    `disciplina_equipo()` los lee y los λ dependen de eso: renombrarlos
    rompería el modelo en silencio."""
    out = estadisticas_equipo(crudo)
    for tid, f in out.items():
        f["fouls"] = f["faltas"]
        f["cards"] = f["tarjetas"]
    # El arbitro es del partido, no de un equipo: va con guion bajo para
    # que todo lo que recorre los equipos del registro lo saltee.
    out["_arbitro"] = arbitro_de(crudo)
    out["_jugadores"] = jugadores_partido(crudo)
    out["_once"] = once_partido(crudo)
    return out


def promedios_equipo(partidos):
    """Promedio de cada métrica sobre los partidos que SÍ la traen, más su
    desvío (constancia).

    Dividir por la cantidad de partidos contaría los ausentes como cero y
    hundiría el promedio de cualquier equipo con un partido sin cargar.
    Por eso cada métrica lleva su propio divisor, y se informa en `n`.

    El desvío existe porque el promedio solo miente sobre la regularidad:
    "5 remates en 5 partidos, uno por partido" y "4 en uno, 1 en total en
    los otros cuatro" dan el mismo promedio (1.0) y son lecturas opuestas
    para una apuesta de estadísticas. Con menos de 2 partidos con dato no
    se calcula — un desvío sobre un solo valor no es una medición, sería
    ruido con forma de número.
    """
    if not partidos:
        return {}
    claves = list(METRICAS_PARTIDO) + ["tarjetas"]
    out, cuentas, desvios = {}, {}, {}
    for k in claves:
        vals = [p[k] for p in partidos if p.get(k) is not None]
        if not vals:
            continue
        media = sum(vals) / len(vals)
        out[k] = round(media, 2)
        cuentas[k] = len(vals)
        if len(vals) >= 2:
            var = sum((v - media) ** 2 for v in vals) / (len(vals) - 1)
            desvios[k] = round(var ** 0.5, 2)
    if not out:
        return {}
    out["pj"] = len(partidos)
    out["n"] = cuentas
    out["desvio"] = desvios
    return out


# Los dos nombres que `aplanar_resumen()` duplica para el motor. Son la
# misma columna que `faltas`/`tarjetas`: contarlos otra vez inventaría
# métricas repetidas.
ALIAS_MOTOR = ("fouls", "cards")

# Con cuántos equipos como mínimo tiene sentido estimar cuánta de la
# diferencia observada es real. Con menos, la estimación del ruido es
# más ruidosa que lo que quiere medir.
MIN_EQUIPOS = 8

# Tope de k. Cuando entre-equipos da cero, la fórmula tiende a infinito;
# el tope evita escribir un número absurdo en el JSON. A k=200 con 9
# partidos el encogimiento ya es del 99.96%: en la práctica es "usá el
# promedio de la liga", que es justo lo que k infinito quiere decir.
K_TOPE = 200.0


def muestras_por_equipo(cache_resumen):
    """{metrica: {team_id: [valor por partido]}} desde el caché de resúmenes.

    Los promedios ya calculados no sirven para saber si una diferencia
    entre dos equipos es real: para eso hacen falta los valores sueltos.
    """
    out = {}
    for eid, partido in (cache_resumen or {}).items():
        if str(eid).startswith("_") or not isinstance(partido, dict):
            continue
        for tid, fila in partido.items():
            if str(tid).startswith("_") or not isinstance(fila, dict):
                continue
            for met, v in fila.items():
                if met in ALIAS_MOTOR or not isinstance(v, (int, float)):
                    continue
                out.setdefault(met, {}).setdefault(str(tid), []).append(float(v))
    return out


def _media(v):
    return sum(v) / len(v)


def _var(v):
    """Varianza muestral. Con menos de dos valores no existe."""
    if len(v) < 2:
        return 0.0
    m = _media(v)
    return sum((x - m) ** 2 for x in v) / (len(v) - 1)


def parametros_metricas(muestras):
    """Por métrica: media de la liga, dispersión por partido y `k`.

    `k` es el corazón de esto. Mide cuánto hay que tirar el promedio de
    un equipo hacia el de la liga antes de creerle.

    Sale de partir la diferencia observada entre equipos en dos: la que
    se explica sola por tener pocos partidos (ruido de muestreo) y la
    que sobra (señal real). k = ruido / señal.

    Importa porque acá se midió lo contrario de lo que uno supone: con
    3 o 4 partidos por equipo, la diferencia de remates entre dos
    equipos NO es más grande que el ruido. Mostrar "12.5 contra 18.7"
    como si fuera una diferencia real es mentir con decimales. En
    cambio faltas, posesión y tackles sí se distinguen — son estilo, y
    el estilo es estable.

    No hay constante elegida a mano: se recalcula en cada corrida sobre
    todo el caché, así que el encogimiento se afloja solo a medida que
    se juntan partidos.
    """
    out = {}
    for met, por_eq in (muestras or {}).items():
        con_dato = {t: v for t, v in por_eq.items() if len(v) >= 2}
        if len(con_dato) < MIN_EQUIPOS:
            continue
        todos = [x for v in con_dato.values() for x in v]
        media = _media(todos)
        # Ruido: cuánto varía un mismo equipo de partido a partido.
        dentro = _media([_var(v) for v in con_dato.values()])
        medias = [_media(v) for v in con_dato.values()]
        nbar = _media([len(v) for v in con_dato.values()])
        # Señal: lo que sobra de la dispersión entre equipos después de
        # descontar el ruido que ya se espera por promediar pocos partidos.
        entre = _var(medias) - dentro / nbar
        k = K_TOPE if entre <= 0 else min(dentro / entre, K_TOPE)
        out[met] = {
            "media": round(media, 2),
            "disp": round(dentro / media, 2) if media > 0 else 0.0,
            "k": round(k, 1),
            "equipos": len(con_dato),
        }
    return out


def media_encogida(vals, media_liga, k):
    """El promedio de un equipo, corregido por cuánto se le puede creer.

    Con pocos partidos o con `k` alto, el resultado se apoya en la liga;
    con muchos partidos y `k` bajo, en lo del equipo. Nunca cae fuera de
    esos dos valores.
    """
    if not vals:
        return media_liga
    return (sum(vals) + k * media_liga) / (len(vals) + k)


# Cuántos partidos con los DOS equipos cargados hacen falta para estimar
# la dispersión de un total. Menos que esto es una varianza de juguete.
MIN_TOTALES = 20


# Las metricas de jugador que tienen mercado por linea.
METRICAS_JUGADOR = ("remates", "al_arco", "faltas", "amarillas", "goles", "asist")


def parametros_jugadores_por_liga(planteles, liga_de_equipo):
    """Los parametros por puesto, calculados DENTRO de cada liga.

    Mismo defecto que arreglaba `parametros_por_liga()`, del lado del
    jugador. Agrupar por puesto esta bien y es deliberado (ver
    `parametros_jugadores`), pero agrupar por puesto CRUZANDO LIGAS hace
    que un 9 ingles y un 9 argentino definan juntos "lo normal para un
    9", y las ligas no rematan igual: 13.65 remates por equipo y partido
    en Argentina contra 15.56 en Brasil, medido sobre el cache.

    Pesa mas que a nivel equipo por una razon de producto: el mercado de
    estadisticas de JUGADOR solo existe en Premier y Ligue 1. Encoger a
    un delantero ingles hacia un promedio que incluye Argentina
    deteriora justo el numero contra el que se compara la cuota.

    Una liga sin puestos suficientes queda afuera y su consumidor cae al
    pozo global — peor, pero honesto sobre su incertidumbre.
    """
    if not planteles or not liga_de_equipo:
        return {}
    por_liga = {}
    for tid, equipo in (planteles or {}).items():
        lg = liga_de_equipo.get(str(tid))
        if not lg:
            continue
        por_liga.setdefault(lg, {})[tid] = equipo
    out = {}
    for lg, sub in por_liga.items():
        par = parametros_jugadores(sub)
        if par:
            out[lg] = par
    return out


def parametros_jugadores(planteles):
    """Media, dispersion y k por PUESTO, no por jugador suelto ni por
    todos juntos.

    A nivel equipo se midio k=200 en remates: dos equipos no se
    distinguen con esta muestra. A nivel jugador da 2.5 — un delantero
    y un central si se distinguen, y por mucho (1.41 remates por partido
    contra 0.48). Por eso vale la pena creerle al numero de un jugador
    mucho mas que al de un equipo.

    Pero el ancla no puede ser el promedio de todos los jugadores:
    encogeria al 9 hacia abajo y al central hacia arriba, que es
    justamente borrar la diferencia que si es real. Se agrupa por
    puesto, que es la unica division que ESPN da gratis y la que mas
    explica.
    """
    por_pos = {}
    for equipo in (planteles or {}).values():
        for j in equipo or []:
            pos, serie = j.get("pos"), j.get("serie")
            if not pos or not serie:
                continue
            for met in METRICAS_JUGADOR:
                vals = serie.get(met)
                if vals:
                    (por_pos.setdefault(pos, {}).setdefault(met, {})
                     [str(j.get("id"))]) = [float(v) for v in vals]
    out = {}
    for pos, muestras in por_pos.items():
        par = parametros_metricas(muestras)
        if par:
            out[pos] = par
    return out


def esperado_jugador(serie, par_pos):
    """Lo que se espera de este jugador por partido, encogido hacia su
    puesto segun cuanto se le pueda creer a su propia muestra."""
    out = {}
    for met, p in (par_pos or {}).items():
        vals = [float(v) for v in (serie or {}).get(met) or []]
        out[met] = round(media_encogida(vals, p["media"], p["k"]), 2)
    return out


def dispersion_total(cache_resumen):
    """Cuánto varía el TOTAL del partido, no cada equipo por separado.

    Existe porque los dos no son lo mismo y la diferencia es grande. En
    córners, un equipo suelto mide 1.76 de dispersión y el total del
    partido 1.01. Si los dos equipos fueran independientes tendrían que
    coincidir; no lo son. Los córners son medio suma cero — el que
    ataca los genera y el otro no — así que el total se mueve MENOS de
    lo que predice sumar dos modelos sueltos. Con las tarjetas pasa al
    revés: un partido caliente le saca a los dos.

    Armar una línea de total sumando dos equipos independientes infla
    las colas y hace ver valor donde no hay. Por eso se mide aparte.
    """
    por_metrica = {}
    for eid, partido in (cache_resumen or {}).items():
        if str(eid).startswith("_") or not isinstance(partido, dict):
            continue
        # Las claves con guion bajo son del partido (arbitro, jugadores),
        # no equipos. `_jugadores` ademas ES un diccionario, asi que
        # filtrar por tipo no alcanza: contaria como un tercer equipo y
        # el partido entero se descartaria.
        filas = [f for k, f in partido.items()
                 if not str(k).startswith("_") and isinstance(f, dict)]
        if len(filas) != 2:
            continue                    # sin los dos lados no hay total
        for met in list(METRICAS_PARTIDO) + ["tarjetas"]:
            vals = [f.get(met) for f in filas]
            if any(not isinstance(v, (int, float)) for v in vals):
                continue
            por_metrica.setdefault(met, []).append(float(sum(vals)))
    out = {}
    for met, totales in por_metrica.items():
        if len(totales) < MIN_TOTALES:
            continue
        media = _media(totales)
        if media <= 0:
            continue
        out[met] = round(_var(totales) / media, 2)
    return out


def esperados(partidos, params, prior=None):
    """Lo que se espera de un equipo en cada métrica, no lo que hizo.

    `prior` es el ancla por métrica de ESTE equipo, sacada de su
    historia larga (ver `prior_equipo`). Cuando no está —que es el caso
    de arg.1 y bra.1, donde la fuente no trae estadísticas— el ancla
    vuelve a ser el promedio de la liga, o sea exactamente lo que esta
    función hacía antes de que el argumento existiera.

    Que el ancla sea el equipo y no la liga es lo que separa "publicamos
    el promedio de todos" de "tenemos opinión propia". Medido
    walk-forward el 2026-08-25 sobre eng.1 y fra.1: con el ancla de la
    liga se captura el 16% de lo que se puede capturar; con el ancla del
    equipo, el 71%. Ver TRASPASO.md §6vicies quinquies.

    El promedio crudo de 3 partidos es casi todo ruido en las métricas
    donde los equipos no se distinguen (ver `parametros_metricas`). Acá
    cada métrica se encoge según su propio `k`: las de estilo (faltas,
    posesión, quites) se quedan cerca de lo del equipo; remates y
    córners se pegan al promedio de la liga hasta que haya muestra para
    separarlos.

    Se calcula sobre la muestra total y no sobre el split de local o de
    visita a propósito: la media de la liga que sirve de ancla es la
    general, y anclar un split de 2 partidos a una media que no le
    corresponde metería un sesgo peor que el que corrige. Cuando el
    caché tenga sedes con muestra propia, esto se puede separar.
    """
    out = {}
    for met, p in (params or {}).items():
        vals = [x[met] for x in partidos if x.get(met) is not None]
        ancla = (prior or {}).get(met, p["media"])
        out[met] = round(media_encogida(vals, ancla, p["k"]), 2)
    return out


def params_de_partido(liga_local, liga_visita, parametros_liga, global_):
    """Los parámetros que describen a UN partido, o el global si no hay.

    Existe porque un partido de copa cruza países, y ahí el parámetro de
    una de las dos ligas no describe al partido. Es la misma regla que
    `paramsDe()` en `index.html`, y la misma de §6vicies ter: mezclar
    ligas hace leer la diferencia entre países como si fuera diferencia
    entre equipos.

    Cuando los dos equipos comparten liga y esa liga tiene parámetros
    propios, gana la liga. En cualquier otro caso, el global — que es
    peor, pero no inventa.
    """
    if liga_local and liga_local == liga_visita:
        propios = (parametros_liga or {}).get(liga_local)
        if propios:
            return propios
    return global_


def esperado_partido(propios_local, propios_visita, params,
                     prior_local=None, prior_visita=None):
    """Córners, faltas y tarjetas esperados en un partido. Un solo número.

    `prior_local` y `prior_visita` son las anclas de historia larga de
    cada equipo (ver `prior_equipo`). Sin ellas, cada equipo se ancla al
    promedio de la liga, que es lo que esta función hacía antes.

    Por qué existe:

    La app mostraba DOS expectativas distintas para lo mismo, en la misma
    pestaña y a doscientos píxeles de distancia:

      "Lo que esperamos acá → CÓRNERS 9.0"   promedio crudo de los
          últimos partidos de cada equipo, sumado (`disciplina_equipo`)
      "Total del partido: 9.4 esperados"      el mismo dato encogido
          hacia el promedio de la liga (`esperados`)

    Y el crudo — que además es el que sale en la tarjeta del partido y
    en Análisis, o sea el más visible — es el peor de los dos. Medido
    walk-forward sobre 179 partidos, error absoluto medio contra el
    total real:

        córners    crudo 3.39   encogido 2.67   (err² 17.48 vs 11.08)
        faltas     crudo 4.90   encogido 4.65
        tarjetas   crudo 1.77   encogido 1.55

    Gana el encogido en las tres, y en córners baja el error cuadrático
    un 37%. Así que queda uno solo, y es éste: el mismo `esperados()`
    que alimenta las líneas de la pestaña Estadísticas.

    Devuelve None cuando falta con qué: sin parámetros de liga o sin
    partidos de alguno de los dos, el llamador cae a la constante de la
    competición, que es lo que ya hacía.
    """
    if not params or not propios_local or not propios_visita:
        return None
    loc = esperados(propios_local, params, prior_local)
    vis = esperados(propios_visita, params, prior_visita)
    if not loc or not vis:
        return None
    def _sum(met):
        a, b = loc.get(met), vis.get(met)
        return None if a is None or b is None else a + b
    corners, faltas, tarjetas = _sum("corners"), _sum("faltas"), _sum("tarjetas")
    if corners is None or faltas is None or tarjetas is None:
        return None
    return {
        "corners": round(corners, 1),
        # La parte del local, para el mercado de córners del local. Sale
        # del mismo cálculo, no de una proporción supuesta.
        "cornersH": round(loc["corners"], 1),
        "fouls": round(faltas, 1),
        "cards": round(tarjetas, 1),
    }


def filas_partido(jug, cache_resumen, team_id):
    """Cruza el historial de un equipo (con `local`/`rival_id` por
    partido, de `historial()`) con el caché de resúmenes (con los
    números de cada equipo por partido, de `resumen_partido()`).

    Da, por cada partido con resumen cacheado, lo que hizo el equipo
    propio Y lo que hizo el rival en ese mismo cruce — que es lo que
    hace falta para separar de local/visitante y para medir cuánto
    concede el rival (no solo cuánto hace el equipo)."""
    tid = str(team_id)
    filas = []
    for p in jug:
        datos = cache_resumen.get(p.get("id")) or {}
        propio = datos.get(tid)
        if not propio:
            continue
        rival = datos.get(str(p.get("rival_id")))
        filas.append({"local": p.get("local"), "propio": propio, "rival": rival})
    return filas


def leer_historia(ruta=None):
    """`data/historia_equipos.json`, o {} si no está.

    Que falte es un estado normal, no un error: el archivo lo escribe
    `historia_equipos.py` a mano y hay ligas que nunca lo van a tener
    (la fuente no trae estadísticas de Argentina ni de Brasil). Sin
    archivo, todo aguas abajo se comporta como antes de que existiera.
    """
    p = Path(ruta) if ruta else RUTA_HISTORIA
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def params_con_historia(parametros_liga, historia):
    """Los parámetros de cada liga, con los de la historia donde los haya.

    La historia pisa **métrica por métrica**, no la tabla entera: de
    football-data salen córners, remates, al arco, faltas y tarjetas,
    pero posesión, tackles, offsides y pases solo existen en el caché de
    ESPN. Pisar la tabla completa los borraría.

    Donde pisa, pisa fuerte y a propósito: el `k` del caché sale de 5
    partidos por equipo y el de la historia de 296. No son dos
    estimaciones comparables de lo mismo — una está pegada al tope
    porque no tiene con qué distinguir, la otra midió.
    """
    if not historia:
        return parametros_liga
    out = {liga: dict(mets) for liga, mets in (parametros_liga or {}).items()}
    for liga, d in (historia.get("ligas") or {}).items():
        destino = out.setdefault(liga, {})
        for met, p in (d.get("parametros") or {}).items():
            # Copia y no referencia: el llamador le escribe `disp_total`
            # encima, y compartir el dict le estaría escribiendo adentro
            # del documento de historia que otros también leen.
            destino[met] = dict(p)
    return out


def prior_equipo(historia, liga, tid, params):
    """{métrica: ancla} para un equipo, desde su historia larga.

    El ancla es la historia del equipo encogida hacia la liga con el
    mismo `k` que después encoge la temporada en curso hacia el ancla.
    Un equipo sin historia devuelve {}, y entonces `esperados()` usa el
    promedio de la liga como siempre.
    """
    d = (((historia or {}).get("ligas") or {}).get(liga) or {})
    eq = (d.get("equipos") or {}).get(str(tid))
    if not eq:
        return {}
    out = {}
    for met, stats in eq.items():
        p = (params or {}).get(met)
        n = (stats or {}).get("n") or 0
        if not p or not n:
            continue
        out[met] = (stats["suma"] + p["k"] * p["media"]) / (n + p["k"])
    return out


def parametros_por_liga(muestras, liga_de_equipo):
    """Los mismos parametros que `parametros_metricas()`, pero calculados
    DENTRO de cada liga en vez de sobre todos los equipos juntos.

    Por que hace falta. Hasta el 2026-08-25 esto se corria una sola vez
    sobre todo el cache, mezclando competiciones. Con arg+bra ya era
    discutible; al entrar eng.1 y fra.1 pasa a ser incorrecto, y de una
    forma que se ve como una mejora.

    `k` sale de partir la variacion entre equipos en dos: el ruido de
    tener pocos partidos, y la senal que sobra. Si el pozo tiene cuatro
    ligas adentro, **la diferencia entre ligas entra como si fuera
    diferencia entre equipos**. Inglaterra hace 21.5 faltas por partido
    y Argentina 25.5: esa brecha infla la senal y hace bajar `k`, o sea
    que la app *parece* haber aprendido a distinguir equipos cuando lo
    unico que distingue es un pais de otro. Para decidir si Chelsea hace
    mas corners que Brighton, saber que Brasil hace mas que Argentina no
    aporta nada.

    Medido el mismo dia sobre el cache real, el `k` de corners daba 77.6
    mezclado, 200.0 en Brasil y 23.1 en Argentina. El numero del pozo no
    describia a ninguna de las dos.

    `liga_de_equipo` es {team_id: slug}, tal cual lo escribe
    `data/cache_ligas.json` — el cron ya lo mantiene, no hay que pedir
    nada nuevo.

    Una liga con menos de MIN_EQUIPOS queda AFUERA del resultado en vez
    de publicar una estimacion que su muestra no sostiene. Quien la
    consuma cae al parametro global, que es peor pero honesto sobre su
    propia incertidumbre.
    """
    if not muestras or not liga_de_equipo:
        return {}
    ligas = {}
    for met, por_eq in muestras.items():
        for tid, v in (por_eq or {}).items():
            lg = liga_de_equipo.get(tid)
            if not lg:
                continue
            ligas.setdefault(lg, {}).setdefault(met, {})[tid] = v
    out = {}
    for lg, sub in ligas.items():
        par = parametros_metricas(sub)
        if par:
            out[lg] = par
    return out


def resumen_completo(datos):
    """¿Este registro del caché se escribió con las métricas nuevas?

    El caché vive en disco entre corridas. Los registros anteriores al
    2026-08-20 guardaban tres campos; si se dan por buenos, las métricas
    nuevas no se pueblan nunca, porque el partido ya está cacheado y no
    se vuelve a pedir. Se reconocen por la ausencia de la clave nueva.

    Un partido que ESPN devolvió sin estadísticas cargadas SÍ cuenta como
    completo: se pidió, no había nada, y volver a pedirlo en cada corrida
    sería pagar para siempre por un dato que no existe.
    """
    if not datos:
        return False
    equipos = [v for k, v in datos.items() if not str(k).startswith("_")]
    if not equipos:
        return False
    # `_arbitro` puede venir vacio (ESPN no siempre lo informa) pero la
    # clave tiene que existir: es lo que distingue "no hay arbitro" de
    # "todavia no se pregunto", y sin eso los 177 partidos ya cacheados
    # nunca se volverian a pedir.
    if ("_arbitro" not in datos or "_jugadores" not in datos
            or "_once" not in datos):
        return False
    return all("remates" in v for v in equipos)


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
    # Guarda las 25 métricas del response, no las 3 que usa el modelo:
    # el pedido ya está hecho y pagado, tirar el resto era gratis pero
    # también era perderlo.
    return aplanar_resumen(d)


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
        # Un registro escrito antes de que se guardaran las 25 métricas
        # sirve para los λ pero no para lo que se muestra. Se re-pide una
        # sola vez: después queda completo y no se vuelve a pagar.
        if eid not in cache_resumen or not resumen_completo(cache_resumen[eid]):
            r = resumen_partido(slug, eid)
            if r is None:
                # Pedido fallido: no se cachea, se reintenta la próxima.
                # Si había un registro viejo, se usa igual — sirve para
                # los λ, y perderlo por un error de red sería cambiar un
                # dato bueno por ninguno.
                if eid not in cache_resumen:
                    continue
            else:
                cache_resumen[eid] = r
        datos = cache_resumen[eid].get(str(team_id))
        if not datos or datos["fouls"] is None or datos["corners"] is None:
            continue
        # `cards` puede venir en None desde que el resumen distingue
        # "no hay dato" de "cero": un partido sin tarjetas cargadas no
        # puede contarse como un partido sin tarjetas.
        corners += datos["corners"]; fouls += datos["fouls"]
        cards += datos.get("cards") or 0
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
            # el nombre tampoco lo usa el ajuste de fuerzas -- ya viene en la
            # misma respuesta, así que jugados_de_resultados() lo aprovecha
            # sin pedir nada de más.
            "home_nombre": loc["team"].get("displayName", ""),
            "away_nombre": vis["team"].get("displayName", ""),
        })
    return partidos


def _cache_temporada(slug, season):
    return CACHE_TEMPORADAS / f"{slug}-{season}.json"


def _leer_cache_temporada(slug, season):
    """Los resultados guardados de una temporada pasada, o None.

    Un cache ilegible se trata como si no existiera: se vuelve a pedir. Es
    preferible un pedido de más a ajustar las fuerzas con media temporada.
    """
    f = _cache_temporada(slug, season)
    if not f.exists():
        return None
    try:
        crudos = json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    out = []
    for p in crudos if isinstance(crudos, list) else []:
        try:
            p = dict(p)
            p["fecha"] = datetime.date.fromisoformat(p["fecha"])
        except (KeyError, TypeError, ValueError):
            return None          # formato viejo o roto: mejor pedirla de nuevo
        out.append(p)
    return out


def _guardar_cache_temporada(slug, season, partidos):
    """Guarda una temporada YA TERMINADA. Un fallo de disco no corta la corrida."""
    try:
        CACHE_TEMPORADAS.mkdir(parents=True, exist_ok=True)
        serializable = [dict(p, fecha=p["fecha"].isoformat()) for p in partidos]
        _cache_temporada(slug, season).write_text(
            json.dumps(serializable, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def historia_reciente(slug, season, hoy, temporadas=None):
    """Los resultados de las últimas `temporadas` temporadas, para ajustar fuerzas.

    Por qué no alcanza con `resultados_temporada()`:

    Esa función pide del 1/1 de la temporada a hoy, así que el ajuste
    arrancaba de cero cada enero y nunca veía más de un año calendario.
    Medido walk-forward sobre el historial completo (2026-08-24), con una
    sola temporada el modelo en arg.1 captura **-26.8%** de la ventaja
    del mercado sobre la tasa base — o sea que predice peor que apostar
    siempre al local. Con tres temporadas y VIDA_MEDIA_DIAS en 300,
    **+6.9%**.

    Los dos cambios solo sirven juntos, y eso también está medido: con
    vida media 45, sumar temporadas EMPEORA (-26.8% a -32.7%), porque un
    partido de hace ocho meses pesa 0.02 y la historia extra se ignora.
    Y aflojar el olvido sin historia extra también empeora (-44.7%).

    Las temporadas pasadas se cachean en disco: no cambian nunca, y sin
    cache esto serían N pedidos por competición en cada corrida del cron.
    La temporada en curso no se cachea, porque sí cambia.

    Si una temporada falla se sigue con las demás: ajustar con menos
    historia es peor que con toda, pero mucho mejor que no publicar.
    """
    n = TEMPORADAS_HISTORIA if temporadas is None else temporadas
    vistos, out = set(), []
    for s in range(season - n + 1, season + 1):
        pasada = s < hoy.year
        crudos = _leer_cache_temporada(slug, s) if pasada else None
        if crudos is None:
            try:
                crudos = resultados_temporada(slug, s, hoy)
            except Exception:                                    # noqa: BLE001
                print(f"  ! no se pudo traer {slug} {s}", file=sys.stderr)
                continue
            if pasada and crudos:
                _guardar_cache_temporada(slug, s, crudos)
        for p in crudos:
            # El mismo partido puede venir dos veces si dos temporadas se
            # solapan. Contarlo dos veces le daría peso doble en el ajuste.
            clave = p.get("id") or (p["fecha"], p["home"], p["away"])
            if clave in vistos:
                continue
            vistos.add(clave)
            out.append(p)
    out.sort(key=lambda p: p["fecha"])
    return out


def fuerzas_equipos(resultados, hoy, anclas=None, prior=None):
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
        pf = PRIOR_FUERZA if prior is None else prior
        num_a = {t: pf * anc.get(t, (1.0, 1.0))[0] for t in equipos}
        den_a = {t: pf for t in equipos}
        for p, w in zip(resultados, pesos):
            num_a[p["home"]] += w * p["gh"]; den_a[p["home"]] += w * mu_local  * defensa[p["away"]]
            num_a[p["away"]] += w * p["ga"]; den_a[p["away"]] += w * mu_visita * defensa[p["home"]]
        nueva_ataque = {t: (num_a[t]/den_a[t] if den_a[t] > 0 else 1.0) for t in equipos}

        num_d = {t: pf * anc.get(t, (1.0, 1.0))[1] for t in equipos}
        den_d = {t: pf for t in equipos}
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


def ancla_de(team_id, slug_consulta, season, hoy, cache_ligas, cache_dom, factores=None,
             cache_dom_resultados=None):
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
            resultados = historia_reciente(slug_liga, season, hoy)
            # El prior es el de la liga que se esta ajustando, no el de
            # la copa desde la que se pregunta: acá se está midiendo
            # cuánto vale el equipo EN SU LIGA.
            cache_dom[slug_liga] = fuerzas_equipos(
                resultados, hoy,
                prior=(COMPETICIONES.get(slug_liga) or {}).get("prior"))
            # Se guarda crudo además de reducido a fuerzas: jugados_de_resultados()
            # lo reusa para forma_general() de equipos sudamericanos sin pedir
            # nada nuevo -- este pedido ya se hace para anclar la fuerza.
            if cache_dom_resultados is not None:
                # Solo la temporada en curso: esto va a forma_general(), que
                # es "cómo llega el equipo". El ajuste de fuerzas sí quiere
                # los años anteriores; la forma reciente, no.
                cache_dom_resultados[slug_liga] = [
                    r for r in resultados if r["fecha"].year == season]
        except Exception:
            cache_dom[slug_liga] = ({}, 1.0, 1.0, {})   # liga que no responde
            if cache_dom_resultados is not None:
                cache_dom_resultados[slug_liga] = []
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

    Y sella cada registro nuevo con las constantes que lo produjeron
    (`modelo`). El 2026-08-24 `rho` de arg.1 pasó de +0.05 a -0.05 por
    un barrido sobre 5 temporadas: los registros de antes y los de
    después conviven en este archivo y no son comparables entre sí. Sin
    el sello, cualquier medición que agregue el historial mezcla eras
    del modelo sin enterarse.

    Solo se sella lo que se calcula ahora. A los registros viejos no se
    les estampa nada: no sabemos con qué constantes se hicieron, y
    ponerles las de hoy sería peor que dejarlos sin dato — los haría
    parecer comparables con los nuevos, que es justo lo que el sello
    existe para evitar.
    """
    # Import perezoso a proposito: medir_clv importa backtest, que importa
    # este modulo. Arriba seria circular y rompe el arranque del cron; aca
    # se resuelve en tiempo de llamada, con `actualizar` ya cargado.
    # `devig_shin` no se copia: una tercera copia del mismo devig es
    # exactamente lo que el repo acaba de terminar de unificar.
    import medir_clv

    hist = {}
    if HISTORIAL_PRON.exists():
        try:
            hist = json.loads(HISTORIAL_PRON.read_text(encoding="utf-8"))
        except Exception:
            hist = {}

    # nombre de competición → slug. Ya se usaba para resolver pendientes;
    # ahora también para saber qué `prior` rigió en cada pronóstico.
    slug_de = {meta["nombre"]: slug for slug, meta in COMPETICIONES.items()}

    nuevos = 0
    for m in partidos:
        mk = m.get("mercado")
        if m["id"] in hist or not mk or not mk.get("local"):
            continue
        # Shin y no reparto parejo: las casas le cargan mas margen a la
        # cuota alta. Medido sobre 11.854 partidos (medir_devig.py), el
        # proporcional le erra casi el doble cuando el margen es alto,
        # que es el caso de DraftKings. Los registros anteriores al
        # 2026-08-25 quedaron con el metodo viejo y NO se recalculan:
        # misma razon que el sello de `modelo`.
        pq = medir_clv.devig_shin(
            [mk["local"], mk["empate"], mk["visitante"]])
        if not pq:
            continue
        hist[m["id"]] = {
            "fecha": m["date"], "comp": m["comp"],
            "home": m["home"], "away": m["away"],
            "lh": m["lh"], "la": m["la"], "rho": m["rho"],
            "mercado": [round(x, 4) for x in pq],            # ya sin margen (Shin)
            "cuotas": [mk["local"], mk["empate"], mk["visitante"]],
            "resultado": None,
            "modelo": {
                "vida_media": VIDA_MEDIA_DIAS,
                "prior": (COMPETICIONES.get(slug_de.get(m["comp"])) or {}).get("prior"),
            },
        }
        nuevos += 1

    # Resolver los pendientes: un pedido por competición, no uno por partido.
    pendientes = [k for k, v in hist.items() if v["resultado"] is None]
    resueltos_ahora = 0
    if pendientes:
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

    def get_hist_general(tid, slug_consulta):
        # Un pedido por competencia que seguimos, no por partido: si el
        # equipo ya se consultó en su propio slug (jug_loc/jug_vis, más
        # abajo) esa llamada se recicla vía cache_hist. Las que no
        # participa devuelven lista vacía y forma_general las ignora sola.
        fuentes = [get_hist(s, tid) for s in COMPETICIONES]
        # Solo vale la pena preguntar en Libertadores/Sudamericana: ahí es
        # donde puede haber un rival de otro país. En las ligas
        # domésticas los dos equipos ya son de la misma, que ya está en
        # COMPETICIONES -- preguntar igual sería un pedido nuevo (resolver
        # la liga del equipo vía /teams/{id}) que no suma nada.
        if slug_consulta in ("conmebol.libertadores", "conmebol.sudamericana"):
            # cache_dom_resultados ya lo llenó get_fuerzas() al calibrar la
            # fuerza de este mismo partido -- acá no se pide nada de más.
            slug_liga = liga_domestica(tid, slug_consulta, cache_ligas)
            if slug_liga and slug_liga not in COMPETICIONES and slug_liga in cache_dom_resultados:
                fuentes.append(jugados_de_resultados(tid, cache_dom_resultados[slug_liga]))
        return fuentes

    def get_tabla(slug):
        if slug not in cache_tabla:
            cache_tabla[slug] = tabla_competicion(slug, season)
        return cache_tabla[slug]

    sin_ancla = {}       # slug -> equipos de copa sin fuerza en ninguna liga que sigamos
    cache_fuerzas = {}   # slug -> (fuerzas, mu_local, mu_visita, partidos_por_equipo)
    cache_dom = {}       # slug de liga local -> lo mismo, para las anclas
    cache_dom_resultados = {}   # slug de liga local -> resultados crudos, para forma_general
    factores = factores_liga()   # cuánto vale cada liga, para comparar entre países
    cache_roster = {}    # (slug, team_id) -> plantel, para no pedir dos veces
    apariciones = []     # (team_id, slug del partido, slug de su liga)
    jugados_equipo = {}  # team_id -> sus últimos partidos jugados
    planteles = {}       # team_id -> plantel fusionado, se escribe a disco
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

    # Historia larga, SOLO para ajustar fuerzas. Va aparte de get_resultados
    # a propósito: data/resultados.json y el registro quieren la temporada en
    # curso — meterles tres años cambiaría el archivo sin ninguna razón.
    cache_historia = {}

    def get_historia(slug):
        if slug not in cache_historia:
            cache_historia[slug] = historia_reciente(slug, season, hoy)
        return cache_historia[slug]

    def get_fuerzas(slug):
        if slug not in cache_fuerzas:
            print(f"  · calibrando fuerzas de ataque/defensa — {slug}")
            resultados = get_historia(slug)
            # Ancla: cada equipo se regulariza hacia lo que vale en su liga
            # local, no hacia el promedio de esta copa. En arg.1 no aplica
            # (la liga local ES esta competición) y ancla_de devuelve None.
            # Los equipos salen de la TEMPORADA EN CURSO, no de la historia
            # larga: anclar a un equipo que se fue hace dos años no sirve de
            # nada y cuesta un pedido de liga local por cabeza.
            actuales = get_resultados(slug)
            equipos = ({p["home"] for p in actuales}
                       | {p["away"] for p in actuales})
            anclas = {}
            for tid in equipos:
                a = ancla_de(tid, slug, season, hoy, cache_ligas, cache_dom, factores,
                             cache_dom_resultados=cache_dom_resultados)
                if a:
                    anclas[tid] = a
            if anclas:
                print(f"    ancladas {len(anclas)} de {len(equipos)} fuerzas a la liga local")
            # Quien quedo SIN ancla, y SOLO donde el ancla aplica.
            #
            # En una liga, `ancla_de` devuelve None a proposito: la liga
            # local ES esta competicion, asi que la fuerza sale de aca
            # mismo. Marcar eso como "sin ancla" apagaba Premier y Ligue
            # 1 enteras — 19 partidos, la primera corrida con esto
            # puesto. El hueco de verdad es el otro: una COPA donde un
            # equipo viene de una division que no seguimos, y entonces no
            # tiene fuerza calibrada en ningun lado.
            for tid in equipos:
                if tid in anclas:
                    continue
                propia = liga_domestica(tid, slug, cache_ligas)
                if propia == slug:
                    continue          # su liga es esta: la fuerza sale de aca
                sin_ancla.setdefault(slug, set()).add(tid)
            cache_fuerzas[slug] = fuerzas_equipos(
                resultados, hoy, anclas=anclas,
                prior=COMPETICIONES[slug].get("prior"))
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

    # Bet365 vía odds-api.io: agrega mercados que DraftKings no tiene
    # (córners, jugadores, más líneas de gol). Sin ODDS_API_KEY en el
    # entorno, odds_key queda None y mercado_extra_de() no hace nada —
    # la app anda igual que antes de que esta fuente existiera.
    odds_key = ME.clave()
    cache_eventos_odds = {}
    if odds_key:
        print("· odds-api.io: clave detectada, se agregan mercados de Bet365")

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
            eventos_odds = (eventos_extra(slug, odds_key, cache_eventos_odds)
                             if odds_key else [])
            mercado_extra = mercado_extra_de(
                {"date": fecha, "home": loc_nombre, "away": vis_nombre},
                eventos_odds, odds_key)

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
                    # El modelo exageraba su rango de goles ~2.7 veces
                    # (ver ESCALA_DEFECTO, arriba). Se encoge hacia el
                    # centro medido de la liga.
                    #
                    # OJO con el centro, que casi se elige mal: la
                    # tentación es `mu_local + mu_visita`, que parece el
                    # centro natural (es el λ de dos equipos promedio).
                    # No lo es: medido sobre arg da 2.025 mientras la
                    # media real de λ es 2.266, porque λ es
                    # multiplicativo y E[a·d] no vale 1. Centrar ahí
                    # metería un sesgo sistemático de −0.11 goles en
                    # cada partido — un error que no tira excepción ni
                    # se ve en pantalla, solo desplaza todo hacia abajo.
                    lh, la = corregir_escala(lh, la, centro_de(slug),
                                             escala_de(slug))
                    # Segundo eje, y el orden importa: la escala se
                    # aplica primero porque trabaja sobre el total, y
                    # esta después porque redistribuye ese total sin
                    # cambiarlo. Al revés el resultado sería el mismo
                    # —las dos son lineales y actúan en ejes
                    # independientes— pero así se lee en el orden en que
                    # se midieron, que es como están documentadas.
                    lh, la = encoger_diferencia(lh, la, diferencia_de(slug))
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
                # Respaldo para una competición sin red de cruces suficiente:
                # promedio simple ponderado por recencia de la muestra propia.
                # Lo usaba Copa Argentina, que salió el 2026-08-25; queda
                # porque cualquier copa nueva vuelve a caer acá.
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
            # Los mismos partidos sirven después para las estadísticas que
            # se muestran. Se anotan acá porque acá se tienen; los números
            # ya quedaron en cache_resumen, así que armarlas es gratis.
            for _tid, _jug in ((loc_id, jug_loc), (vis_id, jug_vis)):
                jugados_equipo.setdefault(str(_tid), _jug)
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
                # El slug, ademas del nombre para mostrar. Hasta el
                # 2026-08-31 la app identificaba la liga por expresion
                # regular sobre `comp` (ver LIGAS_SIN_VALOR en
                # index.html), o sea por el texto que se le muestra al
                # usuario: si manana ESPN escribe "Brasileirao" sin
                # acento, la regla medida deja de aplicarse en silencio.
                # El contrato de ejes lo necesita ademas para buscar el
                # aporte medido por liga. Campo NUEVO: agregar esta
                # permitido, renombrar o cambiar tipos no.
                "liga": slug,
                "date": fecha, "comp": meta["nombre"], "compLogo": comp_logo, "hora": hora,
                "home": loc_nombre, "away": vis_nombre,
                "homeId": loc_id, "awayId": vis_id,
                "homeLogo": escudo(loc["team"]), "awayLogo": escudo(vis["team"]),
                "lh": lh, "la": la, "rho": meta["rho"], "conf": conf,
                "corners": corners, "cornersH": cornersH,
                "fouls": fouls, "cards": cards,
                "note": nota,
                "formH": forma(jug_loc), "formA": forma(jug_vis),
                "formH_general": forma_general(*get_hist_general(loc_id, slug)),
                "formA_general": forma_general(*get_hist_general(vis_id, slug)),
                "h2h": h2h, "tabla": tabla, "grupo": grupo,
                # Copa que cruza divisiones: si alguno de los dos no
                # tiene fuerza calibrada en ninguna liga que sigamos, su
                # lambda sale del promedio de la copa — o sea de nada. La
                # app corta ahi y no publica probabilidad. Campo nuevo,
                # aditivo: si no esta, la app se comporta como antes.
                "sinAncla": bool(
                    str(loc_id) in sin_ancla.get(slug, ())
                    or str(vis_id) in sin_ancla.get(slug, ())),
                "estadio": estadio, "ciudad": ciudad,
                "mercado": mercado,
                "mercadoExtra": mercado_extra or {},
                "preload": {},
            })

            # El plantel con números, para los dos equipos. Un pedido por
            # (equipo, competición), cacheado: los dos partidos de un mismo
            # equipo en la misma corrida no lo pagan dos veces.
            # Un equipo puede jugar dos competiciones en la misma ventana
            # (River: Liga el 23/08, Sudamericana el 26/08). Se anota
            # dónde aparece y el roster se pide después, una vez por
            # (equipo, competición). Ver slugs_de_equipos().
            for tid in (loc_id, vis_id):
                try:
                    slug_liga = liga_domestica(tid, slug, cache_ligas)
                except Exception:
                    slug_liga = None
                apariciones.append((tid, slug, slug_liga))

    # ── planteles ────────────────────────────────────────────────────
    # Un pedido por (equipo, competición). Las estadísticas de /roster son
    # por competición, así que un equipo que juega Liga y copa necesita
    # las dos para que "jugó 5 de 5" signifique algo.
    for tid, slugs in slugs_de_equipos(apariciones).items():
        fuentes = []
        for s in slugs:
            clave = (s, str(tid))
            if clave not in cache_roster:
                try:
                    cache_roster[clave] = roster(s, tid)
                except Exception:
                    cache_roster[clave] = []
            fuentes.append(cache_roster[clave])
        js = solo_los_que_jugaron(fusionar_planteles(*fuentes))
        if not js:
            continue
        peso = peso_goleador(js)
        for j in js:
            j["peso_goles"] = round(peso.get(j["id"], 0.0), 3)
        planteles[tid] = js

    # ── estadísticas de equipo ───────────────────────────────────────
    # Cero pedidos nuevos: los partidos ya están en cache_resumen porque
    # disciplina_equipo() los pidió para calcular los córners del modelo.
    # Esto solo lee lo que quedó guardado y lo promedia — total, y
    # separado por local/visitante y por lo que el equipo hizo vs lo
    # que le concedió el rival en esos mismos partidos.
    # Los parametros salen del cache ENTERO, no de los 8 ultimos de cada
    # equipo: para saber cuanta de la diferencia entre equipos es real
    # hace falta mirar a todos juntos. Se recalculan en cada corrida, sin
    # ninguna constante puesta a mano.
    _muestras = muestras_por_equipo(cache_resumen)
    parametros = parametros_metricas(_muestras)
    for met, dt in dispersion_total(cache_resumen).items():
        if met in parametros:
            parametros[met]["disp_total"] = dt

    # Los mismos parametros, pero calculados DENTRO de cada liga. Ver
    # `parametros_por_liga()` para el por que: el pozo mezclado lee la
    # diferencia entre ligas como si fuera diferencia entre equipos, y
    # eso baja `k` por el motivo equivocado. Medido el 2026-08-25 sobre
    # dos ligas sinteticas de equipos identicos entre si, el pozo daba
    # k=0.1 —"creele todo al promedio del equipo"— cuando la respuesta
    # correcta era el tope.
    #
    # `disp_total` es del partido, no del equipo, asi que se hereda del
    # calculo global: separarla por liga pediria una muestra que ninguna
    # liga tiene todavia.
    parametros_liga = parametros_por_liga(_muestras, cache_ligas)
    # La historia larga, si alguien corrio `historia_equipos.py`. Donde
    # la hay, su `k` y su media de liga le ganan a los del cache: salen
    # de 296 partidos por equipo contra 5. Donde no la hay —arg.1 y
    # bra.1, que la fuente no cubre— no cambia nada.
    historia = leer_historia()
    parametros_liga = params_con_historia(parametros_liga, historia)
    if historia:
        print(f"· historia larga: {', '.join(historia.get('ligas') or {})}"
              f" (de {historia.get('actualizado', '?')})")
    for _lg, _par in parametros_liga.items():
        for met, dt in dispersion_total(cache_resumen).items():
            if met in _par:
                _par[met]["disp_total"] = dt

    estadisticas = {}
    propios_por_equipo = {}
    for tid, jug in jugados_equipo.items():
        filas = filas_partido(jug[:ESTADISTICAS_N], cache_resumen, tid)
        propios = [f["propio"] for f in filas]
        pr = promedios_equipo(propios)
        if not pr:
            continue
        pr["local"] = promedios_equipo([f["propio"] for f in filas if f["local"]])
        pr["visita"] = promedios_equipo([f["propio"] for f in filas if not f["local"]])
        pr["concede"] = promedios_equipo([f["rival"] for f in filas if f["rival"]])
        # Cada equipo se encoge hacia SU liga, no hacia el promedio de
        # las seis competiciones juntas. Si su liga no junto muestra
        # suficiente cae al parametro global, que es peor pero no
        # inventa.
        _lg_eq = cache_ligas.get(str(tid))
        _par_eq = parametros_liga.get(_lg_eq) or parametros
        # El ancla de este equipo: su propia historia, si la tiene. Sin
        # historia, `prior_equipo` devuelve {} y `esperados` vuelve a
        # anclar en el promedio de la liga, que es lo de siempre.
        pr["esperado"] = esperados(propios, _par_eq,
                                   prior_equipo(historia, _lg_eq, tid, _par_eq))
        pr["liga"] = _lg_eq
        estadisticas[tid] = pr
        propios_por_equipo[tid] = propios

    # ── un solo número por métrica ───────────────────────────────────
    # Hasta el 2026-08-24 la app mostraba DOS expectativas para lo mismo
    # en la misma pestaña: el promedio crudo de arriba y el encogido de
    # las líneas. Medido, el encogido acierta más en las tres métricas
    # (ver `esperado_partido`), así que el crudo se reemplaza acá.
    #
    # Tiene que ser DESPUÉS del bucle de partidos: los parámetros de liga
    # salen de `cache_resumen`, que se llena adentro de ese bucle.
    #
    # Y van los parámetros de la liga de los dos equipos, no los
    # globales. Hasta el 2026-08-25 acá entraba `parametros` a secas:
    # el arreglo de §6vicies ter habia llegado a `pr["esperado"]` (las
    # lineas de la pestaña Estadisticas) y no a esta ruta, que es la que
    # alimenta el total de córners que se ve en la tarjeta del partido.
    # O sea que la misma métrica se calculaba con dos varas distintas
    # segun donde se la mirara, y la mas visible usaba la mala.
    for pr_ in partidos:
        _hid, _aid = str(pr_.get("homeId")), str(pr_.get("awayId"))
        _pp = params_de_partido(cache_ligas.get(_hid), cache_ligas.get(_aid),
                                parametros_liga, parametros)
        esp = esperado_partido(propios_por_equipo.get(_hid),
                               propios_por_equipo.get(_aid),
                               _pp,
                               prior_equipo(historia, cache_ligas.get(_hid),
                                            _hid, _pp),
                               prior_equipo(historia, cache_ligas.get(_aid),
                                            _aid, _pp))
        if esp:
            pr_.update(esp)

    # ── serie por jugador ────────────────────────────────────────────
    # El acumulado de temporada que trae el roster no distingue al que
    # remato 1 vez en cada uno de 5 partidos del que hizo 4 en uno solo.
    # La serie si, y sale del mismo /summary que ya se pidio.
    for tid, js in planteles.items():
        serie = serie_jugadores(jugados_equipo.get(tid) or [], cache_resumen, minimo=2)
        for j in js:
            d = serie.get(j["id"])
            if d:
                j["serie"] = d

    # ── el once que cada equipo puso la ultima vez ──────────────────
    # No reemplaza al plantel: lo acompana. La app dibuja este si esta y
    # cae al inferido si no, asi que un equipo sin `rosters` cargados se
    # comporta exactamente como antes de que esto existiera.
    onces = {}
    for tid in planteles:
        uno = ultimo_once(tid, jugados_equipo.get(tid) or [], cache_resumen)
        if uno:
            onces[tid] = uno

    # Los parametros del puesto salen de TODOS los planteles juntos: para
    # saber que es mucho para un delantero hay que mirar a los delanteros,
    # no a los de un equipo. Recien despues se le pone a cada jugador lo
    # que se espera de el, encogido hacia su puesto.
    par_jug = parametros_jugadores(planteles)
    # Y los mismos, por liga. Un 9 ingles no se encoge hacia el promedio
    # de los 9 argentinos: las ligas no rematan igual, y el mercado de
    # jugador solo existe en las europeas.
    par_jug_liga = parametros_jugadores_por_liga(planteles, cache_ligas)
    for tid, equipo in planteles.items():
        _pj = par_jug_liga.get(cache_ligas.get(str(tid))) or par_jug
        for j in equipo:
            if j.get("serie") and j.get("pos") in _pj:
                j["serie"]["esp"] = esperado_jugador(j["serie"], _pj[j["pos"]])

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
        # Una competición que no calibra fuerzas tiene acá su único pedido
        # de resultados de la corrida. Para las demás ya está en cache y
        # no cuesta nada.
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

    # Compacto y no indentado: este archivo no se lee a mano (CLAUDE.md
    # dice "no editar") y el telefono lo baja entero en cada carga. La
    # indentacion eran 138 KB de espacios — mas de lo que ocupa toda la
    # serie por jugador que se acaba de agregar.
    PLANTELES.write_text(json.dumps({
        "actualizado": datetime.datetime.now().isoformat(timespec="minutes"),
        "equipos": planteles,
        "once": onces,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"· planteles: {len(planteles)} equipos, "
          f"{sum(len(v) for v in planteles.values())} jugadores, "
          f"{len(onces)} con el once del ultimo partido")

    ESTADISTICAS.write_text(json.dumps({
        "actualizado": datetime.datetime.now().isoformat(timespec="minutes"),
        "sobre": ESTADISTICAS_N,
        "parametros": parametros,
        "parametros_liga": parametros_liga,
        "jugadores": par_jug,
        "jugadores_liga": par_jug_liga,
        "equipos": estadisticas,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"· estadísticas: {len(estadisticas)} equipos "
          f"(promedio de hasta {ESTADISTICAS_N} partidos, sin pedidos extra)")

    # ── historia de la cuota de mercado ──────────────────────────────
    # Cero pedidos nuevos: la cuota ya viene en el scoreboard que se pidio
    # para armar la grilla. Se acumula porque ESPN la borra cuando el
    # partido termina, y sin la de cierre no hay CLV que medir.
    cuotas_previas = {}
    if CUOTAS.exists():
        try:
            cuotas_previas = json.loads(CUOTAS.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            cuotas_previas = {}
    cuotas = snapshot_cuotas(cuotas_previas, partidos,
                             datetime.datetime.now().isoformat(timespec="minutes"))
    CUOTAS.write_text(json.dumps(cuotas, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
    _fotos = sum(len(v) for v in cuotas.values())
    print(f"· cuotas: {len(cuotas)} partidos, {_fotos} fotos "
          f"(+{_fotos - sum(len(v) for v in cuotas_previas.values())} nuevas)")

    # ── historia de las líneas de jugador (Bet365) ────────────────────
    # Cero pedidos nuevos: mercado_extra_de() ya las trajo más arriba.
    # Se acumula porque para ligas domésticas no hay forma de pedirlas
    # hacia atrás una vez jugado el partido — ver snapshot_props().
    props_previas = {}
    if PROPS_JUGADOR.exists():
        try:
            props_previas = json.loads(PROPS_JUGADOR.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            props_previas = {}
    props = snapshot_props(props_previas, partidos,
                            datetime.datetime.now().isoformat(timespec="minutes"))
    PROPS_JUGADOR.write_text(json.dumps(props, ensure_ascii=False, separators=(",", ":")),
                             encoding="utf-8")
    _fotos_p = sum(len(v) for v in props.values())
    print(f"· props de jugador: {len(props)} líneas, {_fotos_p} fotos "
          f"(+{_fotos_p - sum(len(v) for v in props_previas.values())} nuevas)")

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
