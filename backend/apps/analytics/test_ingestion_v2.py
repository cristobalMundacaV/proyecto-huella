from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (ActividadOperacional, EvidenciaObra, FuenteDatos, Observacion, Organizacion,
                     PlantillaMapeo, ProcesoIngesta, RegistroEmision, UsuarioOrganizacion, VersionEvidencia)


class IngestionV2ApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("ingestion-v2", password="test-pass")
        self.organizacion = Organizacion.objects.create(nombre="Ingesta Uno")
        self.otra = Organizacion.objects.create(nombre="Ingesta Dos")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.organizacion)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.organizacion.organizacion_id}"

    def upload(self, content="viaje_id,km,toneladas\nV-001,132,18\nV-002,98,12\n", name="viajes.csv", fuente_nombre="Planilla logistica"):
        file = SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")
        return self.client.post(f"{self.base}/ingestas/", {"archivo": file, "fuente_nombre": fuente_nombre}, format="multipart")

    def analyze_and_map(self, ingesta_id):
        analysis = self.client.post(f"{self.base}/ingestas/{ingesta_id}/analizar/", {}, format="json")
        self.assertEqual(analysis.status_code, 200)
        mapping = self.client.post(
            f"{self.base}/ingestas/{ingesta_id}/mapeo/", {"mapeos": analysis.data["columnas"], "nombre": "Viajes"}, format="json"
        )
        self.assertEqual(mapping.status_code, 200)
        return analysis, mapping

    def test_carga_crea_evidencia_version_y_proceso(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(EvidenciaObra.objects.count(), 1)
        self.assertEqual(VersionEvidencia.objects.count(), 1)
        self.assertEqual(ProcesoIngesta.objects.count(), 1)
        self.assertEqual(FuenteDatos.objects.count(), 1)

        evidencia = EvidenciaObra.objects.get()
        file = SimpleUploadedFile("viajes_corregidos.csv", b"viaje_id,km\nV-003,20\n", content_type="text/csv")
        second = self.client.post(
            f"{self.base}/ingestas/", {"archivo": file, "fuente_nombre": "Planilla logistica", "evidencia": evidencia.id}, format="multipart"
        )
        self.assertEqual(second.status_code, 201)
        self.assertEqual(evidencia.versiones.count(), 2)
        self.assertEqual(list(evidencia.versiones.order_by("version").values_list("version", flat=True)), [1, 2])

    def test_detecta_aliases_y_deja_columna_desconocida_pendiente(self):
        ingesta = self.upload("viaje_id,KM DIA,misterio\nV-001,132,x\n").data
        analysis = self.client.post(f"{self.base}/ingestas/{ingesta['id']}/analizar/", {}, format="json")
        by_column = {item["columna_normalizada"]: item for item in analysis.data["columnas"]}
        self.assertEqual(by_column["km_dia"]["concepto_normalizado"], "distancia_recorrida_km")
        self.assertFalse(by_column["misterio"]["reconocida"])
        self.assertEqual(analysis.data["estado"], "requiere_mapeo")

    def test_caso_obligatorio_genera_dos_actividades_cuatro_observaciones(self):
        ingesta = self.upload().data
        self.analyze_and_map(ingesta["id"])
        preview = self.client.get(f"{self.base}/ingestas/{ingesta['id']}/preview/")
        self.assertEqual(preview.data["filas_validas"], 2)
        result = self.client.post(f"{self.base}/ingestas/{ingesta['id']}/confirmar/", {}, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["actividades_creadas"], 2)
        self.assertEqual(result.data["observaciones_creadas"], 4)
        self.assertEqual(ActividadOperacional.objects.count(), 2)
        self.assertEqual(Observacion.objects.count(), 4)
        self.assertEqual(RegistroEmision.objects.count(), 0)
        evidencia = EvidenciaObra.objects.get()
        self.assertTrue(all(item.evidencia_id == evidencia.id for item in Observacion.objects.all()))
        version = VersionEvidencia.objects.get()
        self.assertTrue(all(item.version_evidencia_id == version.id for item in Observacion.objects.all()))
        self.assertTrue(all(item.fuente.organizacion == self.organizacion for item in Observacion.objects.all()))

    def test_confirmacion_doble_es_idempotente(self):
        ingesta = self.upload().data
        self.analyze_and_map(ingesta["id"])
        first = self.client.post(f"{self.base}/ingestas/{ingesta['id']}/confirmar/", {}, format="json")
        second = self.client.post(f"{self.base}/ingestas/{ingesta['id']}/confirmar/", {}, format="json")
        self.assertFalse(first.data["idempotente"]); self.assertTrue(second.data["idempotente"])
        self.assertEqual(ActividadOperacional.objects.count(), 2)
        self.assertEqual(Observacion.objects.count(), 4)

    def test_error_parcial_no_bloquea_fila_valida_ni_inventa_actividad(self):
        ingesta = self.upload("viaje_id,km,toneladas\nV-001,132,18\n,98,12\nV-003,mal,\n").data
        self.analyze_and_map(ingesta["id"])
        result = self.client.post(f"{self.base}/ingestas/{ingesta['id']}/confirmar/", {}, format="json")
        self.assertEqual(result.data["actividades_creadas"], 1)
        self.assertEqual(result.data["filas_con_error"], 2)
        self.assertEqual(ProcesoIngesta.objects.get().estado, "completado_con_observaciones")
        self.assertFalse(ActividadOperacional.objects.filter(referencia_externa="").exists())

    def test_cien_filas_una_evidencia_y_plantilla_se_reutiliza(self):
        rows = "\n".join(f"V-{index:03d},{index},10" for index in range(1, 101))
        ingesta = self.upload(f"viaje_id,km,toneladas\n{rows}\n").data
        self.analyze_and_map(ingesta["id"])
        self.client.post(f"{self.base}/ingestas/{ingesta['id']}/confirmar/", {}, format="json")
        self.assertEqual(ActividadOperacional.objects.count(), 100)
        self.assertEqual(EvidenciaObra.objects.count(), 1)
        second = self.upload("viaje_id,km,toneladas\nV-101,1,1\n", "agosto.csv").data
        analysis = self.client.post(f"{self.base}/ingestas/{second['id']}/analizar/", {}, format="json")
        self.assertEqual(analysis.data["estado"], "listo_para_confirmar")
        self.assertTrue(all(item["origen_mapeo"] == "plantilla" for item in analysis.data["columnas"]))
        self.assertEqual(PlantillaMapeo.objects.count(), 1)

    def test_tenant_isolation_y_legacy_intacto(self):
        foreign_file = SimpleUploadedFile("otra.csv", b"viaje_id,km\nX,1\n", content_type="text/csv")
        self.client.logout()
        other_user = User.objects.create_user("other-ingestion", password="test-pass")
        UsuarioOrganizacion.objects.create(user=other_user, organizacion=self.otra)
        self.client.force_login(other_user)
        foreign = self.client.post(f"/api/organizaciones/{self.otra.organizacion_id}/ingestas/", {"archivo": foreign_file}, format="multipart")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f"/api/organizaciones/{self.otra.organizacion_id}/ingestas/{foreign.data['id']}/").status_code, 404)
        legacy = self.client.get(f"{self.base}/registros-emision/")
        self.assertEqual(legacy.status_code, 200)

    def test_dos_versiones_generan_observaciones_distinguibles(self):
        first = self.upload("viaje_id,km\nV-001,10\n", "viajes_julio_v1.csv").data
        self.analyze_and_map(first["id"])
        self.client.post(f"{self.base}/ingestas/{first['id']}/confirmar/", {}, format="json")
        evidencia = ProcesoIngesta.objects.get(id=first["id"]).version_evidencia.evidencia

        file = SimpleUploadedFile("viajes_julio_corregido.csv", b"viaje_id,km\nV-002,12\n", content_type="text/csv")
        second = self.client.post(
            f"{self.base}/ingestas/", {"archivo": file, "fuente_nombre": "Planilla logistica", "evidencia": evidencia.id}, format="multipart"
        ).data
        analysis = self.client.post(f"{self.base}/ingestas/{second['id']}/analizar/", {}, format="json")
        if analysis.data["estado"] != "listo_para_confirmar":
            self.client.post(f"{self.base}/ingestas/{second['id']}/mapeo/", {"mapeos": analysis.data["columnas"], "nombre": "Viajes"}, format="json")
        self.client.post(f"{self.base}/ingestas/{second['id']}/confirmar/", {}, format="json")

        first_observation = Observacion.objects.get(actividad__referencia_externa="V-001")
        second_observation = Observacion.objects.get(actividad__referencia_externa="V-002")
        self.assertEqual(first_observation.evidencia_id, second_observation.evidencia_id)
        self.assertEqual(first_observation.version_evidencia.version, 1)
        self.assertEqual(second_observation.version_evidencia.version, 2)
        self.assertEqual(second_observation.version_evidencia.nombre_original, "viajes_julio_corregido.csv")

    def test_rechaza_version_ajena_y_version_de_otra_evidencia(self):
        first = self.upload("viaje_id,km\nV-001,10\n", "primera.csv").data
        second = self.upload("viaje_id,km\nV-002,12\n", "segunda.csv", fuente_nombre="Otra planilla").data
        process_first = ProcesoIngesta.objects.get(id=first["id"])
        process_second = ProcesoIngesta.objects.get(id=second["id"])
        activity = ActividadOperacional.objects.create(
            organizacion=self.organizacion, codigo="MANUAL-VERSION", nombre="Manual", timestamp_inicio=timezone.now()
        )
        source = process_first.fuente_datos
        path = f"{self.base}/actividades-operacionales/{activity.id}/observaciones/"
        payload = {"fuente": source.id, "concepto": "distancia_recorrida_km", "valor_numerico": "1",
                   "timestamp_observacion": timezone.now().isoformat(), "evidencia": process_first.version_evidencia.evidencia_id,
                   "version_evidencia": process_second.version_evidencia_id}
        self.assertEqual(self.client.post(path, payload, format="json").status_code, 400)

        foreign_evidence = EvidenciaObra.objects.create(
            organizacion=self.otra, nombre="Ajena", archivo=SimpleUploadedFile("ajena.csv", b"x")
        )
        foreign_version = VersionEvidencia.objects.create(
            evidencia=foreign_evidence, organizacion=self.otra, version=1,
            archivo=SimpleUploadedFile("ajena.csv", b"x"), nombre_original="ajena.csv", checksum_sha256="a" * 64,
        )
        payload.update({"evidencia": None, "version_evidencia": foreign_version.id})
        self.assertEqual(self.client.post(path, payload, format="json").status_code, 400)

    def test_observacion_manual_admite_version_nula(self):
        activity = ActividadOperacional.objects.create(
            organizacion=self.organizacion, codigo="MANUAL-SIN-VERSION", nombre="Manual", timestamp_inicio=timezone.now()
        )
        source = FuenteDatos.objects.create(organizacion=self.organizacion, nombre="Declaracion manual")
        response = self.client.post(
            f"{self.base}/actividades-operacionales/{activity.id}/observaciones/",
            {"fuente": source.id, "concepto": "horas_operacion", "valor_numerico": "2", "timestamp_observacion": timezone.now().isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["version_evidencia"])
