from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.analytics.models import (
    ActividadOperacional, FuenteDatos, Observacion, Organizacion, EtapaObra,
    Obra, RegistroEmision, UsuarioOrganizacion,
)

from .models import DispositivoSensor, LecturaSensor, LecturaSensorV2, RegistroSensor


class LecturaSensorApiTests(TestCase):
    def setUp(self):
        self.client = APIClient(HTTP_HOST="localhost")
        self.organizacion = Organizacion.objects.create(organizacion_id="ANDINA", nombre="Organizacion Andina SpA")
        self.user = User.objects.create_user("iot-reader", password="test")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.organizacion)
        self.client.force_login(self.user)

    def test_lectura_legacy_conserva_valor_sin_inventar_co2e(self):
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
        self.assertIsNone(lectura.co2e_estimado)

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
        self.assertEqual(response.data["valor_promedio"], 10.0)
        self.assertNotIn("emisiones_totales_kg_co2e", response.data)

    def test_kpis_y_ultimas_lecturas_respetan_organizacion(self):
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
        self.assertEqual(kpis_response.data["etapa_mas_lecturas_hoy"], "Obra gruesa")
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
        self.sensor_key = "sensor-test-key"
        self.dispositivo.set_api_key(self.sensor_key)
        self.dispositivo.save(update_fields=["api_key_hash"])
        self.actividad = ActividadOperacional.objects.create(
            organizacion=self.organizacion,
            obra=self.obra,
            codigo="ACT-IOT-001",
            nombre="Consumo instrumentado",
            tipo="energia",
            timestamp_inicio=timezone.now(),
        )

    def payload(self, **overrides):
        data = {
            "device_id": "SENSOR-DIESEL-001",
            "external_id": "msg-001",
            "type": "diesel_litros",
            "value": "10.5",
            "timestamp": timezone.now().isoformat(),
            "actividad_id": self.actividad.id,
            "api_key": self.sensor_key,
        }
        data.update(overrides)
        return data

    def test_ingesta_crea_hecho_operacional_trazable_sin_emision(self):
        response = self.client.post(
            "/api/iot/ingesta/",
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        registro_sensor = RegistroSensor.objects.get()
        self.assertEqual(registro_sensor.estado_procesamiento, RegistroSensor.EstadoProcesamiento.HECHO_OPERACIONAL)
        self.assertIsNone(registro_sensor.co2e_estimado)
        self.assertIsNone(registro_sensor.factor_emision_usado)
        self.assertEqual(RegistroEmision.objects.count(), 0)
        lectura = LecturaSensorV2.objects.select_related("observacion__fuente", "sensor").get()
        self.assertEqual(registro_sensor.lectura_v2, lectura)
        self.assertEqual(lectura.sensor, self.dispositivo)
        self.assertEqual(lectura.actividad, self.actividad)
        self.assertEqual(lectura.observacion.organizacion, self.organizacion)
        self.assertEqual(lectura.observacion.actividad, self.actividad)
        self.assertEqual(lectura.observacion.fuente.tipo, FuenteDatos.Tipo.SENSOR)
        self.assertEqual(lectura.observacion.metodo_captura, Observacion.MetodoCaptura.INSTRUMENTAL)
        self.assertEqual(lectura.observacion.naturaleza, Observacion.Naturaleza.INSTRUMENTAL)
        self.assertEqual(lectura.metadata_tecnica["registro_sensor_id"], registro_sensor.id)
        self.assertEqual(registro_sensor.obra, self.obra)

    def test_ingesta_es_idempotente_por_external_id(self):
        payload = self.payload(external_id="msg-duplicado", value="3")
        first = self.client.post("/api/iot/ingesta/", payload, format="json")
        second = self.client.post("/api/iot/ingesta/", payload, format="json")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(RegistroSensor.objects.count(), 1)
        self.assertEqual(RegistroEmision.objects.count(), 0)
        self.assertEqual(Observacion.objects.count(), 1)

    def test_telemetria_ambiental_no_crea_emision(self):
        response = self.client.post(
            "/api/iot/ingesta/",
            self.payload(external_id="msg-temp", type="temperatura", value="21.4"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RegistroSensor.objects.get().estado_procesamiento, RegistroSensor.EstadoProcesamiento.HECHO_OPERACIONAL)
        self.assertEqual(RegistroEmision.objects.count(), 0)
        self.assertEqual(Observacion.objects.get().valor_numerico, Decimal("21.4"))

    def test_combustible_y_electricidad_no_inventan_emision(self):
        for external_id, tipo, valor, unidad in [
            ("fuel-1", "diesel_litros", "42", "litros"),
            ("power-1", "electricidad_kwh", "100", "kWh"),
        ]:
            response = self.client.post(
                "/api/iot/ingesta/",
                self.payload(external_id=external_id, type=tipo, value=valor),
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            row = RegistroSensor.objects.get(external_id=external_id)
            self.assertEqual(row.unidad, unidad)
            self.assertIsNone(row.co2e_estimado)
        self.assertEqual(RegistroEmision.objects.count(), 0)

    def test_api_key_es_obligatoria(self):
        response = self.client.post(
            "/api/iot/ingesta/", self.payload(api_key=None), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(RegistroSensor.objects.count(), 0)

    def test_calidad_sensor_se_propaga_a_observacion(self):
        self.dispositivo.estado = DispositivoSensor.Estado.REQUIERE_REVISION
        self.dispositivo.save(update_fields=["estado"])
        response = self.client.post(
            "/api/iot/ingesta/", self.payload(external_id="quality-1"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lectura = LecturaSensorV2.objects.get()
        self.assertEqual(lectura.calidad_tecnica, LecturaSensorV2.CalidadTecnica.REQUIERE_REVISION)
        self.assertEqual(lectura.observacion.estado, Observacion.Estado.PENDIENTE)

    def test_actividad_de_otro_tenant_es_rechazada(self):
        other = Organizacion.objects.create(nombre="Otra organizacion")
        activity = ActividadOperacional.objects.create(
            organizacion=other, codigo="OTHER", nombre="Ajena", timestamp_inicio=timezone.now()
        )
        response = self.client.post(
            "/api/iot/ingesta/", self.payload(actividad_id=activity.id), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Observacion.objects.count(), 0)
