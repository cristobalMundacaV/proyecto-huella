import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from apps.analytics.services.local_advisor import generar_analisis_local


class LocalAdvisorTest(unittest.TestCase):
    def test_genera_analisis_con_recomendacion_contextual(self):
        analisis = generar_analisis_local(
            {
                "total_emisiones": 4500,
                "categoria_critica": "Maquinaria",
                "fuente_critica": "Diesel maquinaria",
                "etapa_critica": "Obra gruesa",
            }
        )

        self.assertIn("Diagnostico", analisis)
        self.assertIn("Insight estrategico", analisis)
        self.assertIn("Nivel de viabilidad", analisis)
        self.assertIn("Recomendacion principal realista", analisis)
        self.assertIn("Escenario optimo", analisis)
        self.assertIn("Niveles de accion", analisis)
        self.assertIn("Recomendacion estrategica", analisis)
        self.assertIn("diesel", analisis.lower())
        self.assertIn("Siguiente accion concreta", analisis)


if __name__ == "__main__":
    unittest.main()
