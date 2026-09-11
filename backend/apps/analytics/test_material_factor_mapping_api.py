from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import (FactorAmbiental, MaterialOperacional, Organizacion,
                     UsuarioOrganizacion, VersionFactorAmbiental)


class MaterialFactorMappingApiTests(APITestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="API mapeo material")
        self.other_org = Organizacion.objects.create(nombre="API otro tenant mapeo")
        self.proposer = User.objects.create_user("api-proponente", password="test-pass")
        UsuarioOrganizacion.objects.create(
            user=self.proposer, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ANALISTA,
        )
        self.approver = User.objects.create_user("api-aprobador", password="test-pass")
        UsuarioOrganizacion.objects.create(
            user=self.approver, organizacion=self.org, rol=UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL,
        )
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-API", nombre="Ladrillo", categoria="ladrillo", unidad_base="kg",
        )
        self.factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-api-ladrillo", nombre="Ladrillo",
            categoria="materiales", unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        self.version = VersionFactorAmbiental.objects.create(
            factor=self.factor, version=1, valor="0.3", fuente="Fixture", estado="activo",
            vigencia_desde=date(2026, 1, 1),
        )
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.other_material = MaterialOperacional.objects.create(
            organizacion=self.other_org, codigo="MAT-OTHER", nombre="Otro", categoria="otro", unidad_base="kg",
        )

    def propose(self, actor):
        self.client.force_login(actor)
        response = self.client.post(
            f"{self.base}/mapeos-material-factor/",
            {
                "material": self.material.id,
                "factor": self.factor.id,
                "vigencia_desde": "2026-01-01",
            },
            format="json",
        )
        return response

    def test_propose_and_approve_flow(self):
        response = self.propose(self.proposer)
        self.assertEqual(response.status_code, 201, response.content)
        mapping_id = response.json()["id"]
        self.assertEqual(response.json()["estado"], "propuesto")

        self.client.force_login(self.approver)
        approve = self.client.post(
            f"{self.base}/mapeos-material-factor/{mapping_id}/aprobar/", {}, format="json"
        )
        self.assertEqual(approve.status_code, 200, approve.content)
        self.assertEqual(approve.json()["estado"], "aprobado")

    def test_analista_cannot_approve(self):
        response = self.propose(self.proposer)
        mapping_id = response.json()["id"]
        self.client.force_login(self.proposer)
        approve = self.client.post(
            f"{self.base}/mapeos-material-factor/{mapping_id}/aprobar/", {}, format="json"
        )
        self.assertEqual(approve.status_code, 403)

    def test_cross_tenant_mapping_detail_is_404(self):
        response = self.propose(self.proposer)
        mapping_id = response.json()["id"]
        other_user = User.objects.create_user("api-otro-usuario", password="test-pass")
        UsuarioOrganizacion.objects.create(user=other_user, organizacion=self.other_org)
        self.client.force_login(other_user)
        other_base = f"/api/organizaciones/{self.other_org.organizacion_id}"
        detail = self.client.get(f"{other_base}/mapeos-material-factor/{mapping_id}/")
        self.assertEqual(detail.status_code, 404)

    def test_eligibility_endpoint_reports_calculable_after_approval(self):
        response = self.propose(self.proposer)
        mapping_id = response.json()["id"]
        self.client.force_login(self.approver)
        self.client.post(f"{self.base}/mapeos-material-factor/{mapping_id}/aprobar/", {}, format="json")

        eligibility = self.client.get(
            f"{self.base}/materiales-operacionales/{self.material.id}/elegibilidad-calculo/?fecha=2026-06-01"
        )
        self.assertEqual(eligibility.status_code, 200, eligibility.content)
        payload = eligibility.json()
        self.assertTrue(payload["calculable"])
        self.assertEqual(payload["estado"], "calculable")

    def test_eligibility_endpoint_no_mapping_is_not_calculable(self):
        self.client.force_login(self.proposer)
        eligibility = self.client.get(
            f"{self.base}/materiales-operacionales/{self.material.id}/elegibilidad-calculo/"
        )
        self.assertEqual(eligibility.status_code, 200)
        self.assertFalse(eligibility.json()["calculable"])

    def test_material_detail_exposes_mapping_status(self):
        response = self.propose(self.proposer)
        mapping_id = response.json()["id"]
        self.client.force_login(self.approver)
        self.client.post(f"{self.base}/mapeos-material-factor/{mapping_id}/aprobar/", {}, format="json")
        self.client.force_login(self.proposer)
        detail = self.client.get(f"{self.base}/materiales-operacionales/{self.material.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["factor_mapping_status"], "aprobado")
        self.assertEqual(detail.json()["calculation_eligibility"]["estado"], "calculable")
