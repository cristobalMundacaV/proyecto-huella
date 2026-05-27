from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.analytics.models import Constructora

from .models import LecturaSensor


class LecturaSensorApiTests(TestCase):
    def setUp(self):
        self.client = APIClient(HTTP_HOST="localhost")

    def test_crea_lectura_y_calcula_co2e(self):
        response = self.client.post(
            "/api/iot/lecturas/",
            {
                "constructora": "Constructora Andina SpA",
                "etapa_obra": "Obra gruesa",
                "sensor": "SENSOR-DIESEL-001",
                "tipo": "diesel_litros",
                "valor": "12.8",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lectura = LecturaSensor.objects.get()
        self.assertEqual(lectura.unidad, "litros")
        self.assertEqual(lectura.co2e_estimado, Decimal("34.304"))

    def test_kpis_ultimas_24_horas(self):
        LecturaSensor.objects.create(
            constructora="Constructora Andina SpA",
            etapa_obra="Faena electrica",
            sensor="SENSOR-ELECTRICIDAD-001",
            tipo=LecturaSensor.Tipo.ELECTRICIDAD_KWH,
            valor=Decimal("10"),
        )

        response = self.client.get("/api/iot/kpis/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_lecturas"], 1)
        self.assertEqual(response.data["sensores_activos"], 1)
        self.assertEqual(response.data["emisiones_totales_kg_co2e"], 3.9)

    def test_kpis_y_ultimas_lecturas_respetan_constructora(self):
        Constructora.objects.create(constructora_id="ANDINA", nombre="Constructora Andina SpA")
        Constructora.objects.create(constructora_id="PACIFICO", nombre="Constructora Pacifico SpA")
        LecturaSensor.objects.create(
            constructora="Constructora Andina SpA",
            etapa_obra="Obra gruesa",
            sensor="SENSOR-DIESEL-001",
            tipo=LecturaSensor.Tipo.DIESEL_LITROS,
            valor=Decimal("10"),
        )
        LecturaSensor.objects.create(
            constructora="Constructora Pacifico SpA",
            etapa_obra="Fundaciones",
            sensor="SENSOR-MAQUINARIA-001",
            tipo=LecturaSensor.Tipo.HORAS_MAQUINARIA,
            valor=Decimal("8"),
        )

        kpis_response = self.client.get("/api/iot/kpis/?constructora_id=ANDINA")
        lecturas_response = self.client.get("/api/iot/lecturas/ultimas/?constructora_id=ANDINA")

        self.assertEqual(kpis_response.status_code, status.HTTP_200_OK)
        self.assertEqual(kpis_response.data["total_lecturas"], 1)
        self.assertEqual(kpis_response.data["etapa_mayor_emision_hoy"], "Obra gruesa")
        self.assertEqual(lecturas_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(lecturas_response.data), 1)
        self.assertEqual(lecturas_response.data[0]["constructora"], "Constructora Andina SpA")
