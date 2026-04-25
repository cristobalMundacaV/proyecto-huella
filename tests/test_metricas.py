import unittest

import pandas as pd

from src.analysis.metrics import calcular_metricas


class CalcularMetricasTest(unittest.TestCase):
    def test_total_y_agrupaciones_salen_ordenadas(self):
        datos = pd.DataFrame(
            {
                "empresa": ["A", "B", "B"],
                "actividad": ["diesel", "diesel", "electricidad"],
                "emisiones": [100, 300, 50],
            }
        )

        metricas = calcular_metricas(datos)

        self.assertEqual(metricas["total_emisiones"], 450)
        self.assertEqual(metricas["emisiones_por_empresa"].index[0], "B")
        self.assertEqual(metricas["emisiones_por_actividad"].index[0], "diesel")


if __name__ == "__main__":
    unittest.main()
