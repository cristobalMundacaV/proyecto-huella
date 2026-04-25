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
        self.assertIn("diesel", analisis)
        self.assertIn("57.2", analisis)
        self.assertIn("Siguiente accion concreta", analisis)


if __name__ == "__main__":
    unittest.main()
