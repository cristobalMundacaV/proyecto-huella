from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import LecturaSensor


class LecturaSensorApiTests(TestCase):
    def setUp(self):
        self.client = APIClient(HTTP_HOST="localhost")

    def test_crea_lectura_y_calcula_co2e(self):
        response = self.client.post(
            "/api/iot/lecturas/",
            {
                "empresa": "Maderas Los Robles SpA",
                "unidad_operativa": "Despacho y Transporte",
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
            empresa="Maderas Los Robles SpA",
            unidad_operativa="Despacho y Transporte",
            sensor="SENSOR-ELECTRICIDAD-001",
            tipo=LecturaSensor.Tipo.ELECTRICIDAD_KWH,
            valor=Decimal("10"),
        )

        response = self.client.get("/api/iot/kpis/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_lecturas"], 1)
        self.assertEqual(response.data["sensores_activos"], 1)
        self.assertEqual(response.data["emisiones_totales_kg_co2e"], 3.9)

    def test_kpis_incluye_mayores_emisores_del_dia(self):
        LecturaSensor.objects.create(
            empresa="Maderas Los Robles SpA",
            unidad_operativa="Aserradero Principal",
            sensor="SENSOR-DIESEL-001",
            tipo=LecturaSensor.Tipo.DIESEL_LITROS,
            valor=Decimal("10"),
        )
        LecturaSensor.objects.create(
            empresa="Maderas Los Robles SpA",
            unidad_operativa="Planta de Tratamiento",
            sensor="SENSOR-MAQUINARIA-001",
            tipo=LecturaSensor.Tipo.HORAS_MAQUINARIA,
            valor=Decimal("8"),
        )
        LecturaSensor.objects.create(
            empresa="Maderas Los Robles SpA",
            unidad_operativa="Planta de Tratamiento",
            sensor="SENSOR-ELECTRICIDAD-001",
            tipo=LecturaSensor.Tipo.ELECTRICIDAD_KWH,
            valor=Decimal("20"),
        )

        response = self.client.get("/api/iot/kpis/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["unidad_mayor_emision_hoy"],
            "Planta de Tratamiento",
        )
        self.assertEqual(
            response.data["unidad_mayor_emision_hoy_kg_co2e"],
            51.8,
        )
        self.assertEqual(
            response.data["actividad_mayor_emision_hoy"],
            LecturaSensor.Tipo.HORAS_MAQUINARIA,
        )
        self.assertEqual(
            response.data["actividad_mayor_emision_hoy_kg_co2e"],
            44.0,
        )
