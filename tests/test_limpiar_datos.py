import unittest

import pandas as pd

from src.cleaning.limpia_datos import limpiar_datos


class LimpiarDatosTest(unittest.TestCase):
    def test_normaliza_columnas_actividad_y_cantidad(self):
        datos = pd.DataFrame(
            {
                " Empresa ": [" EcoRetail ", " EcoRetail "],
                "Actividad": [" Diesel ", " Diesel "],
                "Cantidad": ["120", "120"],
            }
        )

        resultado = limpiar_datos(datos)

        self.assertEqual(list(resultado.columns), ["empresa", "actividad", "cantidad"])
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado.iloc[0]["empresa"], "EcoRetail")
        self.assertEqual(resultado.iloc[0]["actividad"], "diesel")
        self.assertEqual(resultado.iloc[0]["cantidad"], 120.0)

    def test_rechaza_columnas_obligatorias_faltantes(self):
        datos = pd.DataFrame({"empresa": ["EcoRetail"], "cantidad": [120]})

        with self.assertRaises(ValueError):
            limpiar_datos(datos)


if __name__ == "__main__":
    unittest.main()
