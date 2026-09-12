"""MI-01J — consolidated security audit for MATERIAL-INTELLIGENCE.

Cross-cutting checks not already exercised per-phase: every governed model
blocks direct queryset mutation (not just save()/delete() on an instance),
every new API endpoint enforces tenant isolation (cross-tenant access is a
404, never a 403 leaking existence), and RBAC is enforced for governed
write actions at the API boundary, not only in the service layer.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase

from .models import MaterialOperacional, Organizacion, UsuarioOrganizacion
from .models.material_application_profile import MaterialApplicationProfile, MaterialApplicationProfileDecision
from .models.material_functional_use import (
    MaterialApplicationAssessment,
    MaterialFunctionalUse,
    MaterialFunctionalUseDecision,
)
from .models.material_substitution_scenario import MaterialSubstitutionScenario
from .models.material_technical_property import (
    MaterialTechnicalPropertyAssertion,
    MaterialTechnicalPropertyAssertionDecision,
)
from .services.material_application_profile import approve_profile, create_profile
from .services.material_functional_use import approve_functional_use, create_functional_use
from .services.material_substitution_scenario import evaluate_scenario
from .services.material_technical_property import approve_assertion, create_assertion

User = get_user_model()

GOVERNED_MODELS = [
    MaterialApplicationProfile,
    MaterialApplicationProfileDecision,
    MaterialTechnicalPropertyAssertion,
    MaterialTechnicalPropertyAssertionDecision,
    MaterialFunctionalUse,
    MaterialFunctionalUseDecision,
    MaterialApplicationAssessment,
    MaterialSubstitutionScenario,
]


class DirectQuerysetMutationBlockedTests(TestCase):
    """Every governed MI model must refuse bulk .update()/.delete()/
    .bulk_create() regardless of whether any row exists — the guard is on
    the manager/queryset, not conditional on matching rows."""

    def test_update_blocked_for_every_governed_model(self):
        for model in GOVERNED_MODELS:
            with self.assertRaises(ValidationError, msg=model.__name__):
                model.objects.all().update(id=999999)

    def test_delete_blocked_for_every_governed_model(self):
        for model in GOVERNED_MODELS:
            with self.assertRaises(ValidationError, msg=model.__name__):
                model.objects.all().delete()

    def test_bulk_create_blocked_for_every_governed_model(self):
        for model in GOVERNED_MODELS:
            with self.assertRaises(ValidationError, msg=model.__name__):
                model.objects.bulk_create([model()])


class ApiTenantIsolationAndRbacTests(APITestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Audit org")
        self.other_org = Organizacion.objects.create(nombre="Audit otro tenant")
        self.admin = User.objects.create_user("audit-admin", "audit-admin@example.com", "password")
        UsuarioOrganizacion.objects.create(user=self.admin, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.reader = User.objects.create_user("audit-reader", "audit-reader@example.com", "password")
        UsuarioOrganizacion.objects.create(user=self.reader, organizacion=self.org, rol=UsuarioOrganizacion.Rol.LECTOR)
        self.outsider = User.objects.create_user("audit-outsider", "audit-outsider@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.outsider, organizacion=self.other_org, rol=UsuarioOrganizacion.Rol.ADMIN,
        )

        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-AUDIT", nombre="Material audit",
            categoria="materiales", unidad_base="kg",
        )
        profile = create_profile(self.org, self.admin, "PERFIL-AUDIT", "Perfil", Decimal("1"), "m2")
        self.profile = approve_profile(profile.pk, self.org, self.admin)

    def _login(self, user):
        client = APIClient()
        client.force_login(user)
        return client

    def test_profile_detail_hidden_across_tenants(self):
        client = self._login(self.outsider)
        response = client.get(
            f"/api/organizaciones/{self.org.organizacion_id}/perfiles-aplicacion-material/{self.profile.pk}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_profile_list_requires_membership(self):
        client = self._login(self.outsider)
        response = client.get(f"/api/organizaciones/{self.org.organizacion_id}/perfiles-aplicacion-material/")
        self.assertEqual(response.status_code, 404)

    def test_reader_cannot_create_profile(self):
        client = self._login(self.reader)
        response = client.post(
            f"/api/organizaciones/{self.org.organizacion_id}/perfiles-aplicacion-material/",
            {
                "codigo": "PERFIL-DENIED", "nombre": "Denegado",
                "cantidad_unidad_funcional": "1", "unidad_funcional": "m2",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_reader_cannot_approve_profile(self):
        draft = create_profile(self.org, self.admin, "PERFIL-AUDIT-DRAFT", "Draft", Decimal("1"), "m2")
        client = self._login(self.reader)
        response = client.post(
            f"/api/organizaciones/{self.org.organizacion_id}/perfiles-aplicacion-material/{draft.pk}/aprobar/",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_and_approve_profile(self):
        client = self._login(self.admin)
        response = client.post(
            f"/api/organizaciones/{self.org.organizacion_id}/perfiles-aplicacion-material/",
            {
                "codigo": "PERFIL-AUDIT-OK", "nombre": "OK",
                "cantidad_unidad_funcional": "1", "unidad_funcional": "m2",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        profile_id = response.json()["id"]
        approve_response = client.post(
            f"/api/organizaciones/{self.org.organizacion_id}/perfiles-aplicacion-material/{profile_id}/aprobar/",
        )
        self.assertEqual(approve_response.status_code, 200)

    def test_material_property_assertion_hidden_across_tenants(self):
        assertion = create_assertion(
            self.org, self.admin, self.material, "cumple_norma", "boolean",
            "manual_professional_assertion", date(2026, 1, 1), value_boolean=True,
        )
        client = self._login(self.outsider)
        response = client.get(
            f"/api/organizaciones/{self.org.organizacion_id}/aserciones-propiedad-material/{assertion.pk}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_comparable_alternatives_endpoint_hidden_across_tenants(self):
        client = self._login(self.outsider)
        response = client.get(
            f"/api/organizaciones/{self.org.organizacion_id}/materiales-operacionales/"
            f"{self.material.pk}/alternativas-comparables/?profile={self.profile.pk}"
        )
        self.assertEqual(response.status_code, 404)

    def test_hotspots_endpoint_hidden_across_tenants(self):
        client = self._login(self.outsider)
        response = client.get(
            f"/api/organizaciones/{self.org.organizacion_id}/materiales-operacionales/hotspots-a1a3/"
        )
        self.assertEqual(response.status_code, 404)

    def test_copilot_endpoint_hidden_across_tenants(self):
        client = self._login(self.outsider)
        response = client.post(
            f"/api/organizaciones/{self.org.organizacion_id}/materiales-operacionales/"
            f"{self.material.pk}/copiloto-inteligencia/",
        )
        self.assertEqual(response.status_code, 404)

    def test_scenario_endpoint_idor_on_scenario_id(self):
        assertion = create_assertion(
            self.org, self.admin, self.material, "cumple_norma", "boolean",
            "manual_professional_assertion", date(2026, 1, 1), value_boolean=True,
        )
        approve_assertion(assertion.pk, self.org, self.admin)
        functional_use = create_functional_use(
            self.org, self.admin, self.material, self.profile, Decimal("1"), "kg", "Justificación",
        )
        approve_functional_use(functional_use.pk, self.org, self.admin)
        other_material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-AUDIT-2", nombre="Material 2",
            categoria="materiales", unidad_base="kg",
        )
        scenario = evaluate_scenario(
            self.org, self.admin, self.profile, self.material, other_material,
            basis=MaterialSubstitutionScenario.Basis.AGGREGATE_QUANTITY,
            aggregate_quantity="1", aggregate_unit="kg",
        )
        client = self._login(self.outsider)
        response = client.get(
            f"/api/organizaciones/{self.org.organizacion_id}/escenarios-sustitucion-material/{scenario.pk}/"
        )
        self.assertEqual(response.status_code, 404)
