"""CARBONO-ZERO-V1 — obra environmental dashboard & period readiness.

Verifies the single-motor guarantee explicitly: the dashboard's GEI total
must equal the sum of `material_ledger_totals`, its risk score must equal
`apps.ai.risk.score_environmental_risk`'s own output for the same
obra/period — never a second, independently-computed number. Also covers
RBAC (obra-scoped `alcance=OBRAS`), tenant isolation, and the HTTP layer.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.analytics.models import Obra, Organizacion, UsuarioOrganizacion
from apps.analytics.services.material_ledger import material_ledger_totals
from apps.analytics.services.obra_environmental_dashboard import (
    ESTADO_LABELS, _classify_estado_ejecutivo, build_obra_dashboard, build_period_readiness,
)

User = get_user_model()


class ClassificationUnitTests(TestCase):
    def test_ready_for_report_wins_over_everything_else(self):
        readiness = {"listo_para_reporte": True, "cobertura_registros_pct": 40.0}
        risk_result = {"nivel": "critico"}
        self.assertEqual(_classify_estado_ejecutivo(risk_result, readiness), "lista_para_reporte")

    def test_low_coverage_is_periodo_incompleto_even_with_low_risk(self):
        readiness = {"listo_para_reporte": False, "cobertura_registros_pct": 50.0}
        risk_result = {"nivel": "bajo"}
        self.assertEqual(_classify_estado_ejecutivo(risk_result, readiness), "periodo_incompleto")

    def test_critical_risk_with_good_coverage_is_critica(self):
        readiness = {"listo_para_reporte": False, "cobertura_registros_pct": 95.0}
        risk_result = {"nivel": "critico"}
        self.assertEqual(_classify_estado_ejecutivo(risk_result, readiness), "critica")

    def test_medium_or_high_risk_is_atencion(self):
        readiness = {"listo_para_reporte": False, "cobertura_registros_pct": 95.0}
        for nivel in ("alto", "medio"):
            with self.subTest(nivel=nivel):
                self.assertEqual(_classify_estado_ejecutivo({"nivel": nivel}, readiness), "atencion")

    def test_low_risk_and_good_coverage_is_estable(self):
        readiness = {"listo_para_reporte": False, "cobertura_registros_pct": 95.0}
        self.assertEqual(_classify_estado_ejecutivo({"nivel": "bajo"}, readiness), "estable")

    def test_every_status_code_has_a_label(self):
        for code in ("estable", "atencion", "critica", "periodo_incompleto", "lista_para_reporte"):
            self.assertIn(code, ESTADO_LABELS)


class ObraDashboardDemoTenantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_ai_demo_tenant")
        cls.org = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
        membership = UsuarioOrganizacion.objects.filter(organizacion=cls.org).select_related("user").first()
        cls.admin = membership.user
        cls.obra_norte = Obra.objects.get(organizacion=cls.org, nombre="Edificio Horizonte Norte")

    def test_dashboard_gei_total_matches_material_ledger_directly(self):
        # Explicit dates (not `relative_months`, which is wall-clock-relative
        # and would drift against this fixed demo tenant over a long-lived
        # --keepdb test database) so the window reliably covers real data.
        dashboard = build_obra_dashboard(self.org, self.admin, self.obra_norte, date_from="2020-01-01", date_to="2035-12-31")
        ledger = material_ledger_totals(self.org, work=self.obra_norte, start=dashboard["period"]["start"], end=dashboard["period"]["end"])
        kg_total = ledger["totales_por_unidad"].get("kgCO2e", {}).get("total", Decimal("0"))
        expected_tco2e = float(kg_total / Decimal("1000"))
        self.assertGreater(expected_tco2e, 0, "the demo tenant should have real impact data across this wide a window")
        self.assertAlmostEqual(dashboard["kpis"]["huella_total_tco2e"], expected_tco2e, places=3)

    def test_dashboard_risk_matches_the_ai_risk_tool_directly(self):
        from apps.ai.risk import score_environmental_risk

        dashboard = build_obra_dashboard(self.org, self.admin, self.obra_norte, relative_months=3)
        risk_result = score_environmental_risk(
            self.org, self.admin, obra=self.obra_norte,
            date_from=dashboard["period"]["start"], date_to=dashboard["period"]["end"],
        )
        self.assertEqual(dashboard["risk"]["risk_score"], risk_result["risk_score"])
        self.assertEqual(dashboard["risk"]["nivel"], risk_result["nivel"])

    def test_scope_split_sums_back_to_the_total(self):
        dashboard = build_obra_dashboard(self.org, self.admin, self.obra_norte, relative_months=3)
        kpis = dashboard["kpis"]
        scope_sum = kpis["alcance_1_tco2e"] + kpis["alcance_2_tco2e"] + kpis["alcance_3_tco2e"]
        self.assertAlmostEqual(scope_sum, kpis["huella_total_tco2e"], places=2)

    def test_readiness_pendientes_explain_a_not_ready_period(self):
        readiness = build_period_readiness(self.org, self.admin, self.obra_norte, relative_months=3)
        if not readiness["listo_para_reporte"]:
            self.assertGreater(len(readiness["pendientes"]), 0)

    def test_readiness_percentages_are_within_0_100(self):
        readiness = build_period_readiness(self.org, self.admin, self.obra_norte, relative_months=3)
        for key in ("cobertura_registros_pct", "evidencia_pct", "factores_pct", "validacion_profesional_pct"):
            value = readiness[key]
            if value is not None:
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 100.0)

    def test_same_input_is_fully_deterministic(self):
        first = build_obra_dashboard(self.org, self.admin, self.obra_norte, date_from="2026-06-01", date_to="2026-08-31")
        second = build_obra_dashboard(self.org, self.admin, self.obra_norte, date_from="2026-06-01", date_to="2026-08-31")
        self.assertEqual(first, second)

    def test_period_with_no_data_is_never_marked_ready(self):
        dashboard = build_obra_dashboard(self.org, self.admin, self.obra_norte, date_from="2020-01-01", date_to="2020-03-31")
        self.assertFalse(dashboard["readiness"]["listo_para_reporte"])


class ObraDashboardApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_ai_demo_tenant")
        cls.org = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
        membership = UsuarioOrganizacion.objects.filter(organizacion=cls.org).select_related("user").first()
        cls.admin = membership.user
        cls.obra_norte = Obra.objects.get(organizacion=cls.org, nombre="Edificio Horizonte Norte")
        cls.dashboard_url = f"/api/organizaciones/{cls.org.organizacion_id}/obras/{cls.obra_norte.id}/dashboard-ambiental/"
        cls.readiness_url = f"/api/organizaciones/{cls.org.organizacion_id}/obras/{cls.obra_norte.id}/readiness-periodo/"

    def test_dashboard_endpoint_returns_real_data_for_a_member(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.dashboard_url, {"relative_months": 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["obra_id"], self.obra_norte.id)
        self.assertIn("estado_ejecutivo", response.data)

    def test_readiness_endpoint_returns_real_data(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.readiness_url, {"relative_months": 3})
        self.assertEqual(response.status_code, 200)
        self.assertIn("listo_para_reporte", response.data)

    def test_dashboard_endpoint_requires_authentication(self):
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 401)

    def test_dashboard_endpoint_denies_a_user_with_no_membership(self):
        stranger = User.objects.create_user("dash-stranger", "dash-stranger@example.com", "pw")
        self.client.force_login(stranger)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 404)

    def test_dashboard_endpoint_denies_an_obra_scoped_user_for_an_unauthorized_obra(self):
        other_obra = Obra.objects.create(organizacion=self.org, nombre="Obra restringida dashboard", fecha_inicio=date(2026, 1, 1))
        scoped_user = User.objects.create_user("dash-scoped", "dash-scoped@example.com", "pw")
        UsuarioOrganizacion.objects.create(
            user=scoped_user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ANALISTA,
            alcance=UsuarioOrganizacion.Alcance.OBRAS,
        )
        self.client.force_login(scoped_user)
        url = f"/api/organizaciones/{self.org.organizacion_id}/obras/{other_obra.id}/dashboard-ambiental/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_dashboard_endpoint_never_leaks_a_foreign_tenants_obra(self):
        other_org = Organizacion.objects.create(nombre="Dashboard org B")
        foreign_obra = Obra.objects.create(organizacion=other_org, nombre="Obra ajena dashboard", fecha_inicio=date(2026, 1, 1))
        self.client.force_login(self.admin)
        url = f"/api/organizaciones/{self.org.organizacion_id}/obras/{foreign_obra.id}/dashboard-ambiental/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
