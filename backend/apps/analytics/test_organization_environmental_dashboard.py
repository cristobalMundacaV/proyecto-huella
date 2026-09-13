"""CARBONO-ZERO — organization (portfolio) environmental dashboard.

Verifies the aggregation-only guarantee (totals must equal the sum of the
per-obra dashboards, never a second calculation path), tenant isolation,
RBAC (`alcance=OBRAS`), the max-3-insights cap, and the HTTP layer.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.analytics.models import Obra, Organizacion, UsuarioObraAcceso, UsuarioOrganizacion
from apps.analytics.services.obra_environmental_dashboard import build_obra_dashboard
from apps.analytics.services.organization_environmental_dashboard import (
    MAX_INSIGHTS, MAX_PRIORITY_WORKS, build_organization_dashboard,
)

User = get_user_model()


class OrganizationDashboardDemoTenantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_ai_demo_tenant")
        cls.org = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
        membership = UsuarioOrganizacion.objects.filter(organizacion=cls.org).select_related("user").first()
        cls.admin = membership.user
        cls.obras = list(Obra.objects.filter(organizacion=cls.org))

    def test_totals_match_the_sum_of_each_obras_own_dashboard(self):
        portfolio = build_organization_dashboard(self.org, self.admin, date_from="2020-01-01", date_to="2035-12-31")
        expected_total = sum(
            build_obra_dashboard(self.org, self.admin, obra, date_from="2020-01-01", date_to="2035-12-31")["kpis"]["huella_total_tco2e"] or 0
            for obra in self.obras
        )
        self.assertAlmostEqual(portfolio["kpis"]["huella_total_tco2e"], round(expected_total, 3), places=2)

    def test_obras_activas_matches_obras_visible_to_the_user(self):
        portfolio = build_organization_dashboard(self.org, self.admin, relative_months=3)
        self.assertEqual(portfolio["obras_activas"], len(self.obras))

    def test_never_returns_more_than_three_insights(self):
        portfolio = build_organization_dashboard(self.org, self.admin, date_from="2020-01-01", date_to="2035-12-31")
        self.assertLessEqual(len(portfolio["prioridades"]), MAX_INSIGHTS)

    def test_never_returns_more_priority_works_than_the_cap(self):
        portfolio = build_organization_dashboard(self.org, self.admin, relative_months=3)
        self.assertLessEqual(len(portfolio["top_obras_prioritarias"]), MAX_PRIORITY_WORKS)

    def test_is_fully_deterministic_for_the_same_input(self):
        first = build_organization_dashboard(self.org, self.admin, date_from="2026-06-01", date_to="2026-08-31")
        second = build_organization_dashboard(self.org, self.admin, date_from="2026-06-01", date_to="2026-08-31")
        self.assertEqual(first, second)

    def test_an_org_with_no_obras_returns_zeros_not_an_error(self):
        empty_org = Organizacion.objects.create(nombre="Portafolio vacío")
        UsuarioOrganizacion.objects.create(user=self.admin, organizacion=empty_org, rol=UsuarioOrganizacion.Rol.ADMIN)
        portfolio = build_organization_dashboard(empty_org, self.admin, relative_months=3)
        self.assertEqual(portfolio["obras_activas"], 0)
        self.assertEqual(portfolio["kpis"]["huella_total_tco2e"], 0)
        self.assertEqual(portfolio["prioridades"], [])
        self.assertEqual(portfolio["top_obras_prioritarias"], [])


class OrganizationDashboardRbacTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organizacion.objects.create(nombre="Portafolio RBAC", preset="construccion")
        cls.admin = User.objects.create_user("portfolio-admin", "portfolio-admin@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=cls.admin, organizacion=cls.org, rol=UsuarioOrganizacion.Rol.ADMIN)
        cls.work_a = Obra.objects.create(organizacion=cls.org, nombre="Obra A", fecha_inicio=date(2026, 1, 1))
        cls.work_b = Obra.objects.create(organizacion=cls.org, nombre="Obra B", fecha_inicio=date(2026, 1, 1))
        cls.url = f"/api/organizaciones/{cls.org.organizacion_id}/dashboard-portafolio/"

    def test_obras_scoped_user_only_aggregates_their_assigned_obra(self):
        scoped_user = User.objects.create_user("portfolio-scoped", "portfolio-scoped@example.com", "pw")
        membership = UsuarioOrganizacion.objects.create(
            user=scoped_user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.OPERADOR,
            alcance=UsuarioOrganizacion.Alcance.OBRAS,
        )
        UsuarioObraAcceso.objects.create(usuario_organizacion=membership, obra=self.work_a)
        portfolio = build_organization_dashboard(self.org, scoped_user, relative_months=3)
        self.assertEqual(portfolio["obras_activas"], 1)
        self.assertEqual(portfolio["emisiones_por_obra"][0]["obra_id"], self.work_a.id)

    def test_endpoint_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_endpoint_denies_a_user_with_no_membership(self):
        stranger = User.objects.create_user("portfolio-stranger", "portfolio-stranger@example.com", "pw")
        self.client.force_login(stranger)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_endpoint_never_leaks_a_foreign_tenants_obra(self):
        other_org = Organizacion.objects.create(nombre="Portafolio org B")
        Obra.objects.create(organizacion=other_org, nombre="Obra ajena portafolio", fecha_inicio=date(2026, 1, 1))
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        names = [row["obra_nombre"] for row in response.data["emisiones_por_obra"]]
        self.assertNotIn("Obra ajena portafolio", names)

    def test_endpoint_returns_expected_shape_for_an_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {"relative_months": 3})
        self.assertEqual(response.status_code, 200)
        for key in ("kpis", "riesgo_global", "emisiones_por_obra", "readiness_por_obra", "top_obras_prioritarias", "prioridades"):
            self.assertIn(key, response.data)
        self.assertEqual(response.data["obras_activas"], 2)
