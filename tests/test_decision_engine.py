import unittest

from backend.analytics.services.decision_engine import (
    calculate_risk_profile,
    optimize_rows,
    simulate_rows,
    summarize_rows,
)


class DecisionEngineTest(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "empresa": "Empresa A",
                "actividad": "diesel",
                "cantidad": 100,
                "factor_emision": 2.68,
                "emisiones": 268,
            },
            {
                "empresa": "Empresa B",
                "actividad": "electricidad",
                "cantidad": 200,
                "factor_emision": 0.4,
                "emisiones": 80,
            },
        ]

    def test_simula_reduccion_de_diesel(self):
        resultado = simulate_rows(self.rows, diesel_reduction=50)

        self.assertEqual(resultado[0]["cantidad"], 50)
        self.assertEqual(resultado[0]["emisiones"], 134)

    def test_optimiza_y_reporta_escenarios_evaluados(self):
        resultado = optimize_rows(self.rows)

        self.assertEqual(resultado["dieselReduction"], 80)
        self.assertEqual(resultado["evaluatedScenarios"], 209)
        self.assertGreater(resultado["reductionPct"], 0)

    def test_score_de_riesgo_devuelve_factores_defendibles(self):
        summary = summarize_rows(self.rows)
        optimized = optimize_rows(self.rows)
        riesgo = calculate_risk_profile(summary, optimized)

        self.assertIn("score", riesgo)
        self.assertIn("activityConcentration", riesgo["factors"])
        self.assertTrue(riesgo["factors"]["dieselPresent"])


if __name__ == "__main__":
    unittest.main()
