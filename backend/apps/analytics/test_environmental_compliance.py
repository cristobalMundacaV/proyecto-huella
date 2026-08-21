from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import (
    DocumentoAmbiental,
    Obra,
    Organizacion,
    UsuarioOrganizacion,
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
