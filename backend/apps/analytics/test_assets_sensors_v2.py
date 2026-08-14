from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.iot.models import CalibracionSensor, DispositivoSensor, InstalacionSensor, LecturaSensorV2, RegistroSensor

from .models import (ActividadOperacional, ActivoOperacional, EvidenciaObra, FuenteDatos,
                     Observacion, Organizacion, ProcesoOperacional, RegistroEmision,
                     UnidadOperacional, UsuarioOrganizacion)


class AssetsSensorsV2Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("assets-v2", password="test-pass")
        self.org = Organizacion.objects.create(nombre="Activos Uno")
        self.other = Organizacion.objects.create(nombre="Activos Dos")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.unit = UnidadOperacional.objects.create(organizacion=self.org, nombre="Faena")
        self.process = ProcesoOperacional.objects.create(organizacion=self.org, unidad=self.unit, nombre="Transporte")

    def create_asset(self):
        response = self.client.post(f"{self.base}/activos/", {
            "codigo": "CAM-01", "nombre": "Camion 01", "tipo": "vehiculo", "estado": "operativo",
            "unidad_operacional": self.unit.id, "proceso_operacional": self.process.id,
            "vehiculo": {"patente": "ABCD-12", "combustible": "diesel"},
        }, format="json")
        self.assertEqual(response.status_code, 201)
        return response.data

    def create_sensor(self, asset_id):
        response = self.client.post(f"{self.base}/sensores/", {
            "dispositivo_id": "GPS-CAM-01", "nombre": "GPS Camion 01", "tipo_sensor": "gps",
            "activo_operacional": asset_id, "unidad_operacional": self.unit.id, "proceso_operacional": self.process.id,
            "estado": "operativo",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        return response.data

    def test_crear_activo_y_rechazar_contexto_cross_tenant(self):
        asset = self.create_asset()
        self.assertEqual(asset["vehiculo"]["patente"], "ABCD-12")
        foreign_unit = UnidadOperacional.objects.create(organizacion=self.other, nombre="Ajena")
        response = self.client.post(f"{self.base}/activos/", {"codigo": "BAD", "nombre": "Bad", "unidad_operacional": foreign_unit.id}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_mantenimiento_y_condicion(self):
        asset = self.create_asset()
        maintenance = self.client.post(f"{self.base}/activos/{asset['id']}/mantenimientos/", {
            "tipo": "Preventivo", "fecha_programada": timezone.localdate().isoformat(), "estado": "programado"
        }, format="json")
        condition = self.client.post(f"{self.base}/activos/{asset['id']}/condiciones/", {
            "timestamp_inicio": timezone.now().isoformat(), "estado": "ralenti"
        }, format="json")
        self.assertEqual(maintenance.status_code, 201); self.assertEqual(condition.status_code, 201)

    def test_sensor_instalaciones_preservan_historial(self):
        asset = self.create_asset(); sensor = self.create_sensor(asset["id"])
        path = f"{self.base}/sensores/{sensor['id']}/instalaciones/"
        for offset, state in [(2, "retirada"), (1, "activa")]:
            response = self.client.post(path, {"activo": asset["id"], "fecha_instalacion": (timezone.localdate()-timedelta(days=offset)).isoformat(), "estado": state}, format="json")
            self.assertEqual(response.status_code, 201)
        self.assertEqual(InstalacionSensor.objects.filter(sensor_id=sensor["id"]).count(), 2)

    def test_calibracion_vencida_y_evidencia_cross_tenant(self):
        asset = self.create_asset(); sensor = self.create_sensor(asset["id"])
        response = self.client.post(f"{self.base}/sensores/{sensor['id']}/calibraciones/", {
            "fecha": (timezone.localdate()-timedelta(days=30)).isoformat(), "tipo": "Verificacion",
            "resultado": "aprobada", "fecha_proxima_calibracion": (timezone.localdate()-timedelta(days=1)).isoformat(),
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(DispositivoSensor.objects.get(id=sensor["id"]).estado, "calibracion_vencida")
        foreign = EvidenciaObra.objects.create(organizacion=self.other, nombre="Ajena", archivo=SimpleUploadedFile("a.txt", b"a"))
        rejected = self.client.post(f"{self.base}/sensores/{sensor['id']}/calibraciones/", {
            "fecha": timezone.localdate().isoformat(), "tipo": "Prueba", "resultado": "aprobada", "evidencia": foreign.id
        }, format="json")
        self.assertEqual(rejected.status_code, 400)

    def test_caso_obligatorio_lectura_observacion_sin_emision(self):
        asset = self.create_asset(); sensor = self.create_sensor(asset["id"])
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, codigo="V-001", nombre="Viaje V-001", tipo="transporte", timestamp_inicio=timezone.now()
        )
        activity.activos.add(asset["id"])
        response = self.client.post(f"{self.base}/sensores/{sensor['id']}/lecturas/", {
            "actividad": activity.id, "concepto": "distancia_recorrida_km", "valor_numerico": "132", "unidad": "km",
            "timestamp": timezone.now().isoformat(),
        }, format="json")
        self.assertEqual(response.status_code, 201)
        lectura = LecturaSensorV2.objects.get(); observacion = Observacion.objects.get()
        self.assertEqual(lectura.observacion, observacion)
        self.assertEqual(observacion.actividad, activity)
        self.assertEqual(observacion.fuente.tipo, FuenteDatos.Tipo.SENSOR)
        self.assertEqual(observacion.metodo_captura, Observacion.MetodoCaptura.INSTRUMENTAL)
        self.assertEqual(RegistroEmision.objects.count(), 0)
        self.assertFalse(hasattr(lectura, "co2e_estimado"))

    def test_lectura_sin_actividad_y_sensor_fuera_servicio_se_conserva(self):
        asset = self.create_asset(); sensor = self.create_sensor(asset["id"])
        DispositivoSensor.objects.filter(id=sensor["id"]).update(estado="fuera_servicio")
        response = self.client.post(f"{self.base}/sensores/{sensor['id']}/lecturas/", {
            "concepto": "horas_ralenti", "valor_numerico": "1.5", "unidad": "h"
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["calidad_tecnica"], "requiere_revision")
        self.assertIsNone(Observacion.objects.get().actividad)
        self.assertEqual(RegistroEmision.objects.count(), 0)

    def test_sensor_y_actividad_cross_tenant_rechazados(self):
        asset = self.create_asset()
        foreign_asset = ActivoOperacional.objects.create(organizacion=self.other, codigo="OTHER", nombre="Otro")
        self.assertEqual(self.client.post(f"{self.base}/sensores/", {"dispositivo_id": "BAD", "nombre": "Bad", "activo_operacional": foreign_asset.id}, format="json").status_code, 400)
        sensor = self.create_sensor(asset["id"])
        foreign_activity = ActividadOperacional.objects.create(organizacion=self.other, codigo="OTHER-A", nombre="Otra", timestamp_inicio=timezone.now())
        reading = self.client.post(f"{self.base}/sensores/{sensor['id']}/lecturas/", {
            "actividad": foreign_activity.id, "concepto": "distancia_recorrida_km", "valor_numerico": "1", "unidad": "km"
        }, format="json")
        self.assertEqual(reading.status_code, 400)

    def test_iot_legacy_models_siguen_disponibles(self):
        self.assertTrue(hasattr(RegistroSensor, "co2e_estimado"))
        self.assertEqual(self.client.get("/api/iot/registros/").status_code, 200)

    def test_eliminar_actividad_preserva_observacion_instrumental_y_lectura(self):
        asset = self.create_asset(); sensor_data = self.create_sensor(asset["id"])
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, codigo="V-PERSISTE", nombre="Viaje persistente",
            tipo="transporte", timestamp_inicio=timezone.now(),
        )
        response = self.client.post(f"{self.base}/sensores/{sensor_data['id']}/lecturas/", {
            "actividad": activity.id, "concepto": "distancia_recorrida_km",
            "valor_numerico": "132", "unidad": "km",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        lectura = LecturaSensorV2.objects.select_related("observacion", "sensor").get()
        observacion_id = lectura.observacion_id
        fuente_id = lectura.observacion.fuente_id
        sensor_id = lectura.sensor_id

        activity.delete()

        lectura.refresh_from_db(); lectura.observacion.refresh_from_db()
        self.assertEqual(lectura.observacion_id, observacion_id)
        self.assertIsNone(lectura.observacion.actividad_id)
        self.assertEqual(lectura.observacion.fuente_id, fuente_id)
        self.assertEqual(lectura.sensor_id, sensor_id)
        self.assertTrue(Observacion.objects.filter(id=observacion_id).exists())
        self.assertTrue(FuenteDatos.objects.filter(id=fuente_id).exists())
        self.assertTrue(DispositivoSensor.objects.filter(id=sensor_id).exists())

    def test_eliminar_actividad_preserva_observacion_manual(self):
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, codigo="MANUAL-PERSISTE", nombre="Actividad manual",
            timestamp_inicio=timezone.now(),
        )
        source = FuenteDatos.objects.create(organizacion=self.org, nombre="Fuente manual persistente")
        observation = Observacion.objects.create(
            organizacion=self.org, actividad=activity, fuente=source,
            concepto="horas_operacion", valor_numerico="2", unidad="h",
            timestamp_observacion=timezone.now(), metodo_captura="manual",
        )

        activity.delete()

        observation.refresh_from_db()
        self.assertIsNone(observation.actividad_id)
        self.assertEqual(observation.fuente, source)
