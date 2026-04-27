import unittest

from backend.analytics.services.local_advisor import generar_analisis_local


class LocalAdvisorTest(unittest.TestCase):
    def test_genera_analisis_con_recomendacion_contextual(self):
        analisis = generar_analisis_local(
            {
                "total_emisiones": 4500,
                "empresa_critica": "Empresa B",
                "actividad_critica": "diesel",
                "optimizacion": {
                    "reductionPct": 57.2,
                    "dieselReduction": 80,
                    "electricityIncrease": 0,
                },
            }
        )

        self.assertIn("Diagnostico", analisis)
        self.assertIn("Insight estrategico", analisis)
        self.assertIn("Nivel de viabilidad", analisis)
        self.assertIn("Recomendacion principal REALISTA", analisis)
        self.assertIn("Escenario optimo (potencial maximo)", analisis)
        self.assertIn("Escenario recomendado (realista)", analisis)
        self.assertIn("Niveles de accion", analisis)
        self.assertIn("Recomendacion estrategica", analisis)
        self.assertIn("diesel", analisis)
        self.assertIn("57.2", analisis)
        self.assertIn("Siguiente accion concreta", analisis)
        self.assertIn("referencia estrategica", analisis.lower())
        self.assertIn("🟢", analisis)
        self.assertIn("🟡", analisis)
        self.assertIn("🔴", analisis)


if __name__ == "__main__":
    unittest.main()
