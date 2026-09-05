#!/usr/bin/env python3
"""Tests para experto/cierre.py — liquidación, CLV y balance Lucas vs Pronóstic."""

import json
import os
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "experto"))

import cierre as C


class TestCierre(unittest.TestCase):

    def test_norma(self):
        self.assertEqual(C.norma("Matías Fernández"), "matias fernandez")
        self.assertEqual(C.norma("Franco  VÁZQUEZ "), "franco vazquez")
        self.assertEqual(C.norma("O'Higgins"), "o higgins")
        self.assertEqual(C.norma("Álvarez-Balanta"), "alvarez balanta")

    def test_parsear_mercado_jugador(self):
        # 1. Remates
        p1 = C.parsear_mercado_jugador("Matías Fernández más de 2.5 remates")
        self.assertEqual(p1["jugador"], "matias fernandez")
        self.assertEqual(p1["metrica"], "remates")
        self.assertEqual(p1["direccion"], "mas")
        self.assertEqual(p1["linea"], 2.5)

        # 2. Al arco
        p2 = C.parsear_mercado_jugador("Fernández más de 1.5 al arco")
        self.assertEqual(p2["jugador"], "fernandez")
        self.assertEqual(p2["metrica"], "al_arco")
        self.assertEqual(p2["direccion"], "mas")
        self.assertEqual(p2["linea"], 1.5)

        # 3. Faltas con menos de
        p3 = C.parsear_mercado_jugador("Francisco Álvarez menos de 3.5 faltas")
        self.assertEqual(p3["jugador"], "francisco alvarez")
        self.assertEqual(p3["metrica"], "faltas")
        self.assertEqual(p3["direccion"], "menos")
        self.assertEqual(p3["linea"], 3.5)

        # 4. Gol por defecto (linea 0.5)
        p4 = C.parsear_mercado_jugador("Franco Vázquez anota gol")
        self.assertEqual(p4["jugador"], "franco vazquez")
        self.assertEqual(p4["metrica"], "goles")
        self.assertEqual(p4["direccion"], "mas")
        self.assertEqual(p4["linea"], 0.5)

    def test_buscar_jugador_en_plantel(self):
        candidatos = [
            ("101", "Franco Vázquez"),
            ("102", "Francisco Álvarez"),
            ("103", "Sebastián Prieto"),
            ("104", "Lucas Álvarez"),  # Otro Álvarez para probar ambigüedad
        ]
        # Coincidencia exacta de nombre
        pid, nom = C.buscar_jugador_en_plantel("Franco Vázquez", candidatos)
        self.assertEqual(pid, "101")
        self.assertEqual(nom, "Franco Vázquez")

        # Apellido inequívoco
        pid, nom = C.buscar_jugador_en_plantel("Prieto", candidatos)
        self.assertEqual(pid, "103")
        self.assertEqual(nom, "Sebastián Prieto")

        # Apellido ambiguo (hay dos Álvarez) -> no debe adivinar
        pid, nom = C.buscar_jugador_en_plantel("Álvarez", candidatos)
        self.assertIsNone(pid)
        self.assertIsNone(nom)

        # Inexistente
        pid, nom = C.buscar_jugador_en_plantel("Messi", candidatos)
        self.assertIsNone(pid)

    def test_liquidar_marcador(self):
        # 1X2
        self.assertEqual(C.liquidar_marcador("1X2 local", "2-1"), "ganada")
        self.assertEqual(C.liquidar_marcador("1X2 local", "1-1"), "perdida")
        self.assertEqual(C.liquidar_marcador("1X2 local", "0-1"), "perdida")
        self.assertEqual(C.liquidar_marcador("1X2 empate", "1-1"), "ganada")
        self.assertEqual(C.liquidar_marcador("1X2 visitante", "0-2"), "ganada")

        # Doble oportunidad
        self.assertEqual(C.liquidar_marcador("doble oportunidad 1x", "1-1"), "ganada")
        self.assertEqual(C.liquidar_marcador("1x", "2-0"), "ganada")
        self.assertEqual(C.liquidar_marcador("1x", "0-1"), "perdida")
        self.assertEqual(C.liquidar_marcador("x2", "0-1"), "ganada")
        self.assertEqual(C.liquidar_marcador("12", "1-1"), "perdida")

        # DNB
        self.assertEqual(C.liquidar_marcador("dnb local", "2-1"), "ganada")
        self.assertEqual(C.liquidar_marcador("dnb local", "1-1"), "nula")
        self.assertEqual(C.liquidar_marcador("dnb local", "0-1"), "perdida")

        # Goles
        self.assertEqual(C.liquidar_marcador("más de 2.5", "2-1"), "ganada")
        self.assertEqual(C.liquidar_marcador("más de 2.5", "1-1"), "perdida")
        self.assertEqual(C.liquidar_marcador("menos de 2.5", "1-1"), "ganada")
        self.assertEqual(C.liquidar_marcador("ambos marcan", "1-1"), "ganada")
        self.assertEqual(C.liquidar_marcador("ambos marcan", "2-0"), "perdida")

    def test_liquidar_jugador(self):
        cache_disc = {
            "12345": {
                "1": {}, "2": {},
                "_jugadores": {
                    # remates, al_arco, faltas, amarillas, goles, asist, titular
                    "101": [4, 2, 1, 0, 1, 0, 1],
                    "102": [0, 0, 3, 1, 0, 0, 1],
                }
            }
        }
        planteles = {
            "equipos": {
                "1": [{"id": "101", "nombre": "Franco Vázquez"},
                      {"id": "103", "nombre": "Lucas Banco"}],
                "2": [{"id": "102", "nombre": "Francisco Álvarez"}],
            }
        }

        # 1. Jugador que jugó y superó la línea
        ap1 = {
            "id_partido": "espn12345",
            "mercado": "Franco Vázquez más de 2.5 remates",
            "cuota": 2.10, "monto": 1000,
        }
        res1 = C.liquidar_jugador(ap1, cache_disc, planteles)
        self.assertIsNotNone(res1)
        self.assertEqual(res1["resultado"], "ganada")
        self.assertEqual(res1["devolucion"], 1100)
        self.assertIn("4 remates", res1["marcador_final"])

        # 2. Jugador que jugó pero no superó la línea
        ap2 = {
            "id_partido": "espn12345",
            "mercado": "Francisco Álvarez más de 0.5 remates",
            "cuota": 1.80, "monto": 1000,
        }
        res2 = C.liquidar_jugador(ap2, cache_disc, planteles)
        self.assertIsNotNone(res2)
        self.assertEqual(res2["resultado"], "perdida")
        self.assertEqual(res2["devolucion"], -1000)
        self.assertIn("0 remates", res2["marcador_final"])

        # 3. Jugador que NO jugó (no está en _jugadores) -> APUESTA NULA
        ap3 = {
            "id_partido": "espn12345",
            "mercado": "Lucas Banco más de 1.5 remates",
            "cuota": 2.50, "monto": 1000,
        }
        res3 = C.liquidar_jugador(ap3, cache_disc, planteles)
        self.assertIsNotNone(res3)
        self.assertEqual(res3["resultado"], "nula")
        self.assertEqual(res3["devolucion"], 0)
        self.assertIn("no jugó (apuesta nula)", res3["marcador_final"])

    def test_obtener_clv(self):
        # 1X2 CLV
        cuotas = {
            "espn100": [
                {"t": "09:00", "local": 2.10},
                {"t": "14:00", "local": 1.85},
            ]
        }
        # Entró a 2.10, cerró a 1.85 -> CLV positivo
        clv, cierre = C.obtener_clv("espn100", "1X2 local", 2.10, cuotas, {})
        self.assertIsNotNone(clv)
        self.assertAlmostEqual(cierre, 1.85)
        # 1/1.85 - 1/2.10 = 0.5405 - 0.4762 = +6.43 pp
        self.assertAlmostEqual(clv, (1/1.85 - 1/2.10) * 100, places=2)

        # Player prop CLV
        props = {
            "espn100__remates__Franco Vázquez": [
                {"t": "09:00", "lineas": {"2.5": 2.20}},
                {"t": "14:00", "lineas": {"2.5": 1.90}},
            ]
        }
        clv_j, cierre_j = C.obtener_clv("espn100", "Franco Vázquez más de 2.5 remates",
                                       2.20, {}, props)
        self.assertIsNotNone(clv_j)
        self.assertAlmostEqual(cierre_j, 1.90)
        self.assertAlmostEqual(clv_j, (1/1.90 - 1/2.20) * 100, places=2)

    def test_calcular_metricas(self):
        apuestas = [
            {"resultado": "ganada", "monto": 1000, "devolucion": 1100, "clv_pp": 5.0},
            {"resultado": "perdida", "monto": 1000, "devolucion": -1000, "clv_pp": 2.0},
            {"resultado": "ganada", "monto": 1000, "devolucion": 800, "clv_pp": -1.0},
            {"resultado": "nula", "monto": 1000, "devolucion": 0, "clv_pp": None},
        ]
        m = C.calcular_metricas(apuestas)
        self.assertEqual(m["total"], 4)
        self.assertEqual(m["decididas"], 3)
        self.assertEqual(m["ganadas"], 2)
        self.assertEqual(m["perdidas"], 1)
        self.assertEqual(m["nulas"], 1)
        self.assertEqual(m["apostado"], 3000)
        self.assertEqual(m["retorno"], 900)
        # ROI: (1.1 - 1.0 + 0.8) / 3 = 0.9 / 3 = +30.0%
        self.assertAlmostEqual(m["roi_pct"], 30.0, places=1)
        self.assertGreater(m["roi_ee"], 0.0)
        # CLV medio: (5 + 2 - 1) / 3 = 2.0 pp
        self.assertAlmostEqual(m["clv_pp"], 2.0, places=1)
        self.assertGreater(m["clv_ee"], 0.0)

    def test_armar_mensaje(self):
        cerradas_hoy = [
            {
                "partido": "River vs Boca",
                "mercado": "1X2 local",
                "cuota": 2.10,
                "monto": 2000,
                "resultado": "ganada",
                "devolucion": 2200,
                "marcador_final": "2-1",
                "clv_pp": 6.43,
                "cierre": 1.85,
            },
            {
                "partido": "Racing vs Independiente",
                "mercado": "Fernández más de 2.5 remates",
                "cuota": 1.85,
                "monto": 1000,
                "resultado": "perdida",
                "devolucion": -1000,
                "marcador_final": "1 remates (línea 2.5)",
                "clv_pp": -6.43,
                "cierre": 2.10,
            }
        ]
        msg = C.armar_mensaje(cerradas_hoy, balance_semanal=True)
        self.assertIn("CIERRE DE APUESTAS", msg)
        self.assertIn("River vs Boca", msg)
        self.assertIn("Buena entrada", msg)
        self.assertIn("+6.4 pp a favor", msg)
        self.assertIn("Entrada cara", msg)
        self.assertIn("-6.4 pp en contra", msg)
        # "última foto", nunca "cierre": el cron corre 09:00 y 15:00 y los
        # partidos arrancan hasta las 21:00 (`medir_props.py`).
        self.assertIn("última foto", msg)
        self.assertNotIn("cerró a", msg)
        self.assertIn("BALANCE Y CORTE (LUCAS vs PRONÓSTIC)", msg)


if __name__ == "__main__":
    unittest.main()

