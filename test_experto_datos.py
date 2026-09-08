#!/usr/bin/env python3
"""Tests unitarios para experto/datos.py.

Verifica de forma exhaustiva las decisiones matemáticas y de diseño:
1. Detección bidireccional y no dogmática de tensión entre modelo y goles recientes.
2. Normalización de mercados y preservación de props de jugador sin colisión.
3. Cálculo de stake con Kelly fraccional, tope de seguridad y detección de desvalor.
4. Resolución de boletas combinadas de equipos (independientes y del mismo partido).
5. Tratamiento honesto de mercados de jugador en combinadas (sin probabilidades inventadas).
"""

import os
import sys
import unittest
from unittest import mock

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "experto"))

import datos as D


class TestAnalisisGolesRecientes(unittest.TestCase):

    def test_tension_modelo_bajo_vs_goles_recientes(self):
        # Modelo bajo (total 2.1) pero ambos promedian muchos goles
        m = {
            "home": "Equipo A", "away": "Equipo B",
            "formH": [{"marcador": "3-2", "local": True}, {"marcador": "4-1", "local": True}, {"marcador": "2-2", "local": True}],
            "formA": [{"marcador": "2-3", "local": False}, {"marcador": "1-3", "local": False}, {"marcador": "2-2", "local": False}],
            "h2h": [{"s": "4-2"}, {"s": "3-3"}],
        }
        resumen, alertas = D._analisis_goles_recientes(m, 1.2, 0.9)
        self.assertEqual(resumen["local"]["partidos"], 3)
        self.assertEqual(resumen["visitante"]["partidos"], 3)
        self.assertEqual(resumen["h2h_promedio_goles"], 6.0)
        self.assertTrue(len(alertas) >= 1)
        alerta = alertas[0]
        self.assertIn("Tensión metodológica (modelo bajo vs muestra reciente activa)", alerta)
        # Verificar que no sea dogmática
        self.assertNotIn("queda prohibido", alerta.lower())
        self.assertNotIn("descartá el under por completo", alerta.lower())
        self.assertIn("no seguir narrativas", alerta.lower())

    def test_tension_modelo_alto_vs_partidos_cerrados(self):
        # Modelo alto (total 3.4) pero ambos vienen de 0-0 y 1-0
        m = {
            "home": "Equipo X", "away": "Equipo Y",
            "formH": [{"marcador": "1-0", "local": True}, {"marcador": "0-0", "local": True}, {"marcador": "0-1", "local": True}],
            "formA": [{"marcador": "0-1", "local": False}, {"marcador": "1-0", "local": False}, {"marcador": "0-0", "local": False}],
            "h2h": [{"s": "1-0"}, {"s": "0-0"}],
        }
        resumen, alertas = D._analisis_goles_recientes(m, 2.0, 1.4)
        self.assertTrue(len(alertas) >= 1)
        alerta = alertas[0]
        self.assertIn("Tensión metodológica (modelo alto vs muestra reciente cerrada)", alerta)
        self.assertIn("tanteadores bajos", alerta.lower())

    def test_sin_tension_cuando_coinciden(self):
        # Modelo promedio (total 2.7) con partidos normales (2 a 3 goles)
        m = {
            "home": "Equipo 1", "away": "Equipo 2",
            "formH": [{"marcador": "1-1", "local": True}, {"marcador": "2-1", "local": True}, {"marcador": "1-0", "local": True}],
            "formA": [{"marcador": "1-1", "local": False}, {"marcador": "0-2", "local": False}, {"marcador": "2-1", "local": False}],
            "h2h": [{"s": "2-1"}, {"s": "1-1"}],
        }
        resumen, alertas = D._analisis_goles_recientes(m, 1.5, 1.2)
        self.assertEqual(len(alertas), 0)


class TestNormalizarMercado(unittest.TestCase):

    def test_1x2_y_doble_oportunidad(self):
        self.assertEqual(D._normalizar_mercado("gana local"), "1X2 local")
        self.assertEqual(D._normalizar_mercado("1X"), "Doble oportunidad 1X")
        self.assertEqual(D._normalizar_mercado("local o empate"), "Doble oportunidad 1X")
        self.assertEqual(D._normalizar_mercado("X2"), "Doble oportunidad X2")
        self.assertEqual(D._normalizar_mercado("12"), "Doble oportunidad 12")

    def test_goles_y_btts(self):
        self.assertEqual(D._normalizar_mercado("Menos de 2.5"), "Menos de 2.5")
        self.assertEqual(D._normalizar_mercado("under 3.5"), "Menos de 3.5")
        self.assertEqual(D._normalizar_mercado("Más de 1.5 goles"), "Más de 1.5")
        self.assertEqual(D._normalizar_mercado("ambos marcan"), "Ambos marcan")
        self.assertEqual(D._normalizar_mercado("btts"), "Ambos marcan")
        self.assertEqual(D._normalizar_mercado("no marcan los dos"), "No marcan los dos")

    def test_proteccion_mercados_jugador(self):
        # No debe colisionar con "Más de 3.5" de goles del partido
        txt = "Matko Miljevic más de 3.5 remates"
        self.assertEqual(D._normalizar_mercado(txt), txt)
        txt2 = "Fernández más de 1.5 tiros"
        self.assertEqual(D._normalizar_mercado(txt2), txt2)


class TestStakeKelly(unittest.TestCase):

    def test_stake_cero_con_desventaja(self):
        # Si pagamos 1.50 pero nuestra probabilidad es 50%, EV es negativo -> stake 0%
        res = D.stake(50, 1.50, banca=100000)
        self.assertEqual(res["de_cada_cien_pesos_de_banca"], 0.0)
        self.assertEqual(res["plata"], 0)
        self.assertIn("A ese precio no da para apostar", res["por_que"])

    def test_stake_positivo_con_tope(self):
        # Gran ventaja (80% a cuota 2.0) -> Kelly fraccional topado a 4.0%
        res = D.stake(80, 2.0, banca=100000)
        self.assertEqual(res["de_cada_cien_pesos_de_banca"], 4.0)
        self.assertEqual(res["plata"], 4000)

    def test_stake_autodetecta_banca(self):
        # Si banca es None, debe tomar la banca de memoria
        res = D.stake(65, 2.0)
        self.assertGreater(res["de_cada_cien_pesos_de_banca"], 0)
        if res.get("plata") is not None:
            self.assertGreater(res["plata"], 0)


class TestRevisarBoleta(unittest.TestCase):

    def test_boleta_equipos_independientes(self):
        # 2 patas de partidos distintos activos
        partidos = D.partidos_del_dia()["partidos"]
        p1, p2 = partidos[0]["id"], partidos[1]["id"]
        patas = [
            {"id_partido": p1, "mercado": "Menos de 3.5", "cuota": 1.30},
            {"id_partido": p2, "mercado": "Menos de 3.5", "cuota": 1.444},
        ]
        res = D.revisar_boleta(patas)
        self.assertTrue(res["probabilidad_conjunta_calculable"])
        self.assertIsNotNone(res["sale_de_cada_cien_veces"])
        self.assertIsNotNone(res["cuota_justa"])
        self.assertGreater(res["margen_estimado_de_la_casa"], 0)
        self.assertIn("la_pata_que_la_hunde", res)

    def test_boleta_mismo_partido_resuelve_matriz(self):
        # 2 patas del mismo partido (1X2 local y Menos de 3.5)
        partidos = D.partidos_del_dia()["partidos"]
        p = partidos[0]["id"]
        patas = [
            {"id_partido": p, "mercado": "1X2 local", "cuota": 1.71},
            {"id_partido": p, "mercado": "Menos de 3.5", "cuota": 1.30},
        ]
        res = D.revisar_boleta(patas)
        self.assertIn("patas_del_mismo_partido", res)
        mismo = res["patas_del_mismo_partido"][0]
        self.assertIn("juntas_de_cada_cien", mismo)
        self.assertIn("multiplicando_daria", mismo)

    def test_boleta_con_jugador_sin_falsa_precision(self):
        # Pata de jugador + pata de equipo
        partidos = D.partidos_del_dia()["partidos"]
        p = partidos[0]["id"]
        patas = [
            {"id_partido": p, "mercado": "Matias Fernandez mas de 2.5 remates", "cuota": 2.10},
            {"id_partido": p, "mercado": "1X2 local", "cuota": 1.71},
        ]
        with mock.patch("datos.jugadores_partido") as mock_jp:
            mock_jp.return_value = {
                "jugadores": [{
                    "nombre": "Matias Fernandez",
                    "equipo": "Independiente",
                    "serie_de_remates": [2, 3, 1, 4],
                    "cuotas_por_linea": {"2.5": 2.10}
                }]
            }
            res = D.revisar_boleta(patas)
        # REGLA CLAVE: no inventar probabilidad conjunta calibrada para jugadores
        self.assertFalse(res["probabilidad_conjunta_calculable"])
        self.assertIsNone(res["sale_de_cada_cien_veces"])
        self.assertIsNone(res["cuota_justa"])
        # Pero sí calcular margen compuesto de la casa y avisar
        self.assertGreater(res["margen_estimado_de_la_casa"], 0)
        self.assertIn("aviso_jugador", res)
        self.assertIn("VALOR no calcula probabilidad conjunta para combinadas con actuaciones individuales", res["aviso_jugador"])
        # La pata de equipo sí tiene su número
        self.assertIsNotNone(res["probabilidad_patas_equipo_de_cada_cien"])


class TestCartera(unittest.TestCase):

    def test_clasificacion_conservadora_factores(self):
        # 1. Unders / baja anotación
        f_under = D._clasificar_factor_apuesta({"mercado": "Menos de 2.5", "cuota": 1.60, "monto": 2000})
        self.assertEqual(f_under["direccion_goles"], "baja_anotacion")
        self.assertFalse(f_under["es_jugador"])

        # 2. Overs / alta anotación
        f_over = D._clasificar_factor_apuesta({"mercado": "Más de 2.5", "cuota": 2.20, "monto": 1500})
        self.assertEqual(f_over["direccion_goles"], "alta_anotacion")
        self.assertFalse(f_over["es_jugador"])

        # 3. 1X2 / neutro a goles
        f_1x2 = D._clasificar_factor_apuesta({"mercado": "1X2 local", "cuota": 3.10, "monto": 1000})
        self.assertEqual(f_1x2["direccion_goles"], "otro")
        self.assertFalse(f_1x2["es_jugador"])

        # 4. Prop de jugador
        f_prop = D._clasificar_factor_apuesta({"mercado": "Borja más de 2.5 remates", "cuota": 1.95, "monto": 1000})
        self.assertTrue(f_prop["es_jugador"])

    @mock.patch("datos._memoria")
    def test_cartera_separacion_real_y_simulada(self, mock_mem):
        mock_mem.return_value = {
            "banca": 100000,
            "apuestas": [
                {"id_partido": "r1", "partido": "Central Córdoba vs Independiente", "mercado": "Doble oportunidad 1X", "cuota": 1.57, "monto": 1000, "resultado": None},
                {"id_partido": "r2", "partido": "Fluminense vs Vasco da Gama", "mercado": "1X2 local", "cuota": 2.3, "monto": 4000, "resultado": None},
            ]
        }
        sims = [
            {"id_partido": "sim1", "partido": "Boca vs Racing", "mercado": "1X2 empate", "cuota": 3.0, "monto": 2000}
        ]
        res = D.cartera(apuestas_simuladas=sims)
        rb = res["resumen_banca"]
        # En memoria simulada hay 2 apuestas reales por $5.000
        self.assertEqual(rb["expuesto_real"]["monto"], 5000.0)
        self.assertEqual(rb["expuesto_real"]["cantidad_apuestas"], 2)
        # La simulada agrega $2.000
        self.assertEqual(rb["expuesto_simulado"]["monto"], 2000)
        self.assertEqual(rb["expuesto_simulado"]["cantidad_apuestas"], 1)
        # El total proyectado es $7.000 (7% de banca)
        self.assertEqual(rb["expuesto_total_proyectado"]["monto"], 7000.0)
        self.assertEqual(rb["expuesto_total_proyectado"]["cantidad_apuestas"], 3)
        self.assertEqual(rb["expuesto_total_proyectado"]["pct_banca"], 7.0)

    @mock.patch("datos._memoria")
    def test_cartera_concentracion_mismo_partido(self, mock_mem):
        mock_mem.return_value = {
            "banca": 100000,
            "apuestas": [
                {"id_partido": "espn401841542", "partido": "Central Córdoba vs Independiente", "mercado": "Doble oportunidad 1X", "cuota": 1.57, "monto": 1000, "resultado": None},
            ]
        }
        # Sumar una simulada en el mismo partido que ya tiene una real (Central Córdoba espn401841542)
        sims = [
            {"id_partido": "espn401841542", "mercado": "Menos de 2.5", "cuota": 1.65, "monto": 2500}
        ]
        res = D.cartera(apuestas_simuladas=sims)
        conc = [p for p in res["concentracion_por_partido"] if p["id_partido"] == "espn401841542"][0]
        self.assertTrue(conc["concentracion_evento"])
        self.assertEqual(conc["cantidad_apuestas"], 2)
        self.assertEqual(conc["monto_total"], 3500) # 1000 real + 2500 simulada
        # Debe haber generado advertencia de concentración en el mismo partido
        advs = " ".join(res["advertencias"])
        self.assertIn("Concentración en un mismo partido", advs)
        self.assertIn("Central Córdoba", advs)

    @mock.patch("datos._memoria")
    def test_cartera_sesgo_macro_goles_y_escenario_hipotetico(self, mock_mem):
        mock_mem.return_value = {"banca": 100000, "apuestas": []}
        # 2 apuestas simuladas en Unders
        sims = [
            {"id_partido": "p1", "partido": "Equipo A vs Equipo B", "mercado": "Menos de 2.5", "cuota": 1.70, "monto": 3000},
            {"id_partido": "p2", "partido": "Equipo C vs Equipo D", "mercado": "Menos de 3.5", "cuota": 1.40, "monto": 3000},
        ]
        res = D.cartera(apuestas_simuladas=sims)
        dg = res["direccion_goles"]
        self.assertEqual(dg["baja_anotacion"]["pct_goles"], 100.0)
        self.assertIsNotNone(dg["alerta_sesgo"])
        self.assertIn("Fuerte sesgo hacia baja anotación", dg["alerta_sesgo"])
        # Debe existir el escenario hipotético de fecha con muchos goles
        estres_nombres = [e["escenario"] for e in res["escenarios_hipoteticos"]]
        self.assertIn("Hipotético: fecha con muchos goles", estres_nombres)

    @mock.patch("datos._memoria")
    def test_cartera_sin_falsas_alarmas_por_cuotas_bajas(self, mock_mem):
        mock_mem.return_value = {
            "banca": 100000,
            "apuestas": [
                {"id_partido": "r1", "partido": "Real Madrid vs Alavés", "mercado": "1X2 local", "cuota": 1.40, "monto": 2500, "resultado": None},
                {"id_partido": "r2", "partido": "PSG vs Rennes", "mercado": "1X2 local", "cuota": 1.45, "monto": 2500, "resultado": None},
            ]
        }
        # Apuestas a cuotas bajas pero en partidos independientes NO deben generar alertas de correlación
        sims = [
            {"id_partido": "p3", "partido": "Arsenal vs Chelsea", "mercado": "1X2 local", "cuota": 1.40, "monto": 2000},
            {"id_partido": "p4", "partido": "Bayern vs Mainz", "mercado": "1X2 local", "cuota": 1.45, "monto": 2000},
        ]
        res = D.cartera(apuestas_simuladas=sims)
        # No debe haber alerta de favoritos ni sesgo inventado
        advs = res["advertencias"]
        self.assertEqual(len(advs), 0)
        # La exposición agregada ($9.000 sobre $100.000 = 9%) es normal
        self.assertEqual(res["resumen_banca"]["nivel_exposicion"], "normal (exposición acotada, margen holgado de maniobra)")

    @mock.patch("datos._memoria")
    def test_cartera_alerta_sobreexposicion_banca(self, mock_mem):
        mock_mem.return_value = {
            "banca": 100000,
            "apuestas": [
                {"id_partido": "r1", "partido": "Otro partido", "mercado": "1X2 local", "cuota": 1.50, "monto": 5000, "resultado": None},
            ]
        }
        # Si el total proyectado excede el 20% de la banca ($25.000)
        sims = [
            {"id_partido": "p1", "partido": "River vs Platense", "mercado": "1X2 local", "cuota": 1.50, "monto": 20000}
        ]
        res = D.cartera(apuestas_simuladas=sims)
        # 5000 real + 20000 simulada = 25000 (25% de la banca de 100000)
        self.assertEqual(res["resumen_banca"]["expuesto_total_proyectado"]["pct_banca"], 25.0)
        advs = " ".join(res["advertencias"])
        self.assertIn("Exposición agregada elevada", advs)

    def test_cartera_resistencia_entradas_raras(self):
        # Entradas vacías, None, tipos raros
        res1 = D.cartera([])
        self.assertIn("resumen_banca", res1)
        res2 = D.cartera([{"id_partido": None, "mercado": None, "cuota": "invalida", "monto": None}])
        self.assertIn("resumen_banca", res2)


if __name__ == "__main__":
    unittest.main()

