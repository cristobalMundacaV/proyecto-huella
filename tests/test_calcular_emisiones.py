import unittest
from pathlib import Path

import pandas as pd

from src.emissions.calculadora import calcular_emisiones

FACTORES_PATH = Path(__file__).parent / "fixtures" / "factores_emision_test.csv"


class CalcularEmisionesTest(unittest.TestCase):
    def test_calcula_emisiones_con_factor(self):
        datos = pd.DataFrame(
            {
                "empresa": ["EcoRetail"],
                "actividad": ["diesel"],
                "cantidad": [100],
            }
        )

        resultado = calcular_emisiones(datos, str(FACTORES_PATH))

        self.assertEqual(resultado.iloc[0]["emisiones"], 268)

    def test_rechaza_actividad_sin_factor(self):
        datos = pd.DataFrame(
            {
                "empresa": ["EcoRetail"],
                "actividad": ["gas"],
                "cantidad": [100],
            }
        )

        with self.assertRaises(ValueError):
            calcular_emisiones(datos, str(FACTORES_PATH))


if __name__ == "__main__":
    unittest.main()
