from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import (
    AlertaCumplimientoAmbiental,
    DocumentoAmbiental,
    Obra,
    Organizacion,
    UsuarioOrganizacion,
    VariableAmbientalExtraida,
)


class EnvironmentalComplianceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "compliance-user",
            password="test-pass",
        )

        self.org = Organizacion.objects.create(
            nombre="Compliance Org",
        )

        UsuarioOrganizacion.objects.create(
            user=self.user,
            organizacion=self.org,
            rol="analista",
        )

        self.work_a = Obra.objects.create(
            organizacion=self.org,
            nombre="Obra A",
            fecha_inicio=date(
                2026,
                1,
                1,
            ),
        )

        self.work_b = Obra.objects.create(
            organizacion=self.org,
            nombre="Obra B",
            fecha_inicio=date(
                2026,
                1,
                1,
            ),
        )

        self.document_a = DocumentoAmbiental.objects.create(
            organizacion=self.org,
            obra=self.work_a,
            tipo_documento="permiso",
            nombre="Documento A",
            fecha_documento=date(
                2026,
                1,
                10,
            ),
        )

        self.document_b = DocumentoAmbiental.objects.create(
            organizacion=self.org,
            obra=self.work_b,
            tipo_documento="permiso",
            nombre="Documento B",
            fecha_documento=date(
                2026,
                1,
                11,
            ),
        )

        self.client.force_login(self.user)

        self.base = f"/api/organizaciones/" f"{self.org.organizacion_id}"

    def create_alert(self, document, title):
        variable = VariableAmbientalExtraida.objects.create(
            organizacion=document.organizacion,
            documento=document,
            variable_id=f"variable-{document.id}",
            nombre="Variable ambiental",
        )
        return AlertaCumplimientoAmbiental.objects.create(
            organizacion=document.organizacion,
            documento=document,
            variable=variable,
            severidad=AlertaCumplimientoAmbiental.Severidad.AMARILLO,
            tipo_alerta="revision_documental",
            titulo=title,
        )

    def test_documentos_filtran_por_obra(
        self,
    ):
        response = self.client.get(
            f"{self.base}/" f"documentos-ambientales/" f"?obra={self.work_a.id}"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = {item["id"] for item in response.data}

        self.assertIn(
            self.document_a.id,
            ids,
        )

        self.assertNotIn(
            self.document_b.id,
            ids,
        )

    def test_cumplimiento_requiere_membresia_tenant(
        self,
    ):
        foreign_user = User.objects.create_user(
            "compliance-foreign",
            password="test-pass",
        )

        self.client.force_login(foreign_user)

        response = self.client.get(f"{self.base}/" f"documentos-ambientales/")

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_alertas_filtran_por_obra_y_serializan(self):
        alert_a = self.create_alert(self.document_a, "Alerta A")
        alert_b = self.create_alert(self.document_b, "Alerta B")

        response = self.client.get(
            f"{self.base}/alertas-cumplimiento/?obra={self.work_a.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [alert_a.id])
        self.assertNotIn(alert_b.id, [item["id"] for item in response.data])

    def test_resumen_filtra_por_obra(self):
        self.document_a.estado_validacion = DocumentoAmbiental.EstadoValidacion.VALIDO
        self.document_a.save(update_fields=["estado_validacion"])
        self.create_alert(self.document_a, "Alerta A")
        self.create_alert(self.document_b, "Alerta B")

        response = self.client.get(
            f"{self.base}/cumplimiento-ambiental/resumen/?obra={self.work_a.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["obra_id"], self.work_a.id)
        self.assertEqual(response.data["total_documentos"], 1)
        self.assertEqual(response.data["documentos_validados"], 1)
        self.assertEqual(response.data["alertas_abiertas"], 1)
        self.assertEqual(response.data["compliance_pct"], 0.0)

    def test_resumen_obra_sin_datos_no_fabrica_porcentaje(self):
        empty_work = Obra.objects.create(
            organizacion=self.org,
            nombre="Obra sin antecedentes",
            fecha_inicio=date(2026, 1, 1),
        )

        response = self.client.get(
            f"{self.base}/cumplimiento-ambiental/resumen/?obra={empty_work.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_documentos"], 0)
        self.assertEqual(response.data["documentos_validados"], 0)
        self.assertEqual(response.data["alertas_abiertas"], 0)
        self.assertIsNone(response.data["compliance_pct"])

    def test_obra_de_otro_tenant_no_es_accesible(self):
        other_org = Organizacion.objects.create(nombre="Otra organizacion")
        other_work = Obra.objects.create(
            organizacion=other_org,
            nombre="Obra externa",
            fecha_inicio=date(2026, 1, 1),
        )

        for endpoint in [
            "documentos-ambientales/",
            "alertas-cumplimiento/",
            "cumplimiento-ambiental/resumen/",
        ]:
            response = self.client.get(
                f"{self.base}/{endpoint}?obra={other_work.id}"
            )
            self.assertEqual(response.status_code, 404)

    def test_post_work_scoped_impone_obra(
        self,
    ):
        response = self.client.post(
            f"{self.base}/" f"documentos-ambientales/" f"?obra={self.work_a.id}",
            {
                "tipo_documento": "resolucion",
                "nombre": "Documento scoped",
                "fecha_documento": "2026-02-01",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        document = DocumentoAmbiental.objects.get(pk=response.data["id"])

        self.assertEqual(
            document.obra_id,
            self.work_a.id,
        )

    def test_post_work_scoped_rechaza_otra_obra(
        self,
    ):
        response = self.client.post(
            f"{self.base}/" f"documentos-ambientales/" f"?obra={self.work_a.id}",
            {
                "tipo_documento": "resolucion",
                "nombre": "Documento incorrecto",
                "fecha_documento": "2026-02-01",
                "obra": self.work_b.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )
