from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.analytics.models import Organizacion, EtapaObra, Obra, RegistroEmision

from .models import DispositivoSensor, LecturaSensor, RegistroSensor


class LecturaSensorApiTests(TestCase):
    def setUp(self):
        self.client = APIClient(HTTP_HOST="localhost")

    def test_crea_lectura_y_calcula_co2e(self):
        response = self.client.post(
            "/api/iot/lecturas/",
            {
                "organizacion": "Organizacion Andina SpA",
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
            organizacion="Organizacion Andina SpA",
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

    def test_kpis_y_ultimas_lecturas_respetan_organizacion(self):
        Organizacion.objects.create(organizacion_id="ANDINA", nombre="Organizacion Andina SpA")
        Organizacion.objects.create(organizacion_id="PACIFICO", nombre="Organizacion Pacifico SpA")
        LecturaSensor.objects.create(
            organizacion="Organizacion Andina SpA",
            etapa_obra="Obra gruesa",
            sensor="SENSOR-DIESEL-001",
            tipo=LecturaSensor.Tipo.DIESEL_LITROS,
            valor=Decimal("10"),
        )
        LecturaSensor.objects.create(
            organizacion="Organizacion Pacifico SpA",
            etapa_obra="Fundaciones",
            sensor="SENSOR-MAQUINARIA-001",
            tipo=LecturaSensor.Tipo.HORAS_MAQUINARIA,
            valor=Decimal("8"),
        )

        kpis_response = self.client.get("/api/iot/kpis/?organizacion_id=ANDINA")
        lecturas_response = self.client.get("/api/iot/lecturas/ultimas/?organizacion_id=ANDINA")

        self.assertEqual(kpis_response.status_code, status.HTTP_200_OK)
        self.assertEqual(kpis_response.data["total_lecturas"], 1)
        self.assertEqual(kpis_response.data["etapa_mayor_emision_hoy"], "Obra gruesa")
        self.assertEqual(lecturas_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(lecturas_response.data), 1)
        self.assertEqual(lecturas_response.data[0]["organizacion"], "Organizacion Andina SpA")


class SensorIngestionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient(HTTP_HOST="localhost")
        self.organizacion = Organizacion.objects.create(
            organizacion_id="ANDINA",
            nombre="Organizacion Andina SpA",
        )
        self.etapa = EtapaObra.objects.create(
            organizacion=self.organizacion,
            nombre="Obra gruesa",
            tipo=EtapaObra.Tipo.OBRA_GRUESA,
        )
        self.obra = Obra.objects.create(
            organizacion=self.organizacion,
            etapa_principal=self.etapa,
            nombre="Edificio Sensorizado",
            tipo_proyecto=Obra.TipoProyecto.EDIFICIO,
            fecha_inicio=timezone.localdate(),
            superficie_m2=Decimal("1200"),
        )
        self.dispositivo = DispositivoSensor.objects.create(
            dispositivo_id="SENSOR-DIESEL-001",
            nombre="Sensor estanque diesel",
            organizacion=self.organizacion,
            obra=self.obra,
            etapa=self.etapa,
            tipo_sensor=DispositivoSensor.TipoSensor.COMBUSTIBLE,
        )

    def test_ingesta_crea_registro_sensor_y_registro_emision(self):
        response = self.client.post(
            "/api/iot/ingesta/",
            {
                "device_id": "SENSOR-DIESEL-001",
                "external_id": "msg-001",
                "type": "diesel_litros",
                "value": "10.5",
                "timestamp": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        registro_sensor = RegistroSensor.objects.get()
        self.assertEqual(registro_sensor.estado_procesamiento, RegistroSensor.EstadoProcesamiento.CONSOLIDADO)
        self.assertEqual(registro_sensor.co2e_estimado, Decimal("28.140"))
        self.assertEqual(RegistroEmision.objects.count(), 1)
        self.assertEqual(RegistroEmision.objects.get().metadata["origen"], "iot_sensor")

    def test_ingesta_es_idempotente_por_external_id(self):
        payload = {
            "device_id": "SENSOR-DIESEL-001",
            "external_id": "msg-duplicado",
            "type": "diesel_litros",
            "value": "3",
        }
        first = self.client.post("/api/iot/ingesta/", payload, format="json")
        second = self.client.post("/api/iot/ingesta/", payload, format="json")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(RegistroSensor.objects.count(), 1)
        self.assertEqual(RegistroEmision.objects.count(), 1)

    def test_telemetria_ambiental_no_crea_emision(self):
        response = self.client.post(
            "/api/iot/ingesta/",
            {
                "device_id": "SENSOR-DIESEL-001",
                "external_id": "msg-temp",
                "type": "temperatura",
                "value": "21.4",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RegistroSensor.objects.get().estado_procesamiento, RegistroSensor.EstadoProcesamiento.SOLO_TELEMETRIA)
        self.assertEqual(RegistroEmision.objects.count(), 0)
