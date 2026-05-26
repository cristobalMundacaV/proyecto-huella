import unittest

import pandas as pd

from src.cleaning.limpia_datos import limpiar_datos


class LimpiarDatosTest(unittest.TestCase):
    def test_normaliza_columnas_fuente_emision_y_cantidad(self):
        datos = pd.DataFrame(
            {
                " constructora ": [" Constructora Andina ", " Constructora Andina "],
                "fuente_emision": [" Diesel ", " Diesel "],
                "Cantidad": ["120", "120"],
            }
        )

        resultado = limpiar_datos(datos)

        self.assertEqual(list(resultado.columns), ["constructora", "fuente_emision", "cantidad"])
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado.iloc[0]["constructora"], "Constructora Andina")
        self.assertEqual(resultado.iloc[0]["fuente_emision"], "Diesel")
        self.assertEqual(resultado.iloc[0]["cantidad"], 120.0)

    def test_rechaza_columnas_obligatorias_faltantes(self):
        datos = pd.DataFrame({"constructora": ["Constructora Andina"], "cantidad": [120]})

        with self.assertRaises(ValueError):
            limpiar_datos(datos)


if __name__ == "__main__":
    unittest.main()
