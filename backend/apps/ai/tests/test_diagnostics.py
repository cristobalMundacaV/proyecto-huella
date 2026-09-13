"""AI-INTELLIGENCE-03 — deterministic environmental diagnostics.

Two layers of tests, matching the two layers of the feature:
- Pure rule/scoring unit tests (no DB): every threshold boundary, every
  "None means nothing to report" branch — the same as the mission's
  explicit acceptance list (aumento>umbral, aumento<umbral, previous=0,
  caída, concentración, evidencia, factor, calidad, cobertura, variabilidad).
- Engine/tool tests (real DB, real demo tenant): RBAC, tenant isolation,
  obra resolution by name, ordering by priority, and same-input ->
  same-output determinism.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from apps.ai import tools
from apps.ai.diagnostics import rules, scoring
from apps.ai.diagnostics.engine import run_environmental_diagnostics
from apps.analytics.models import Obra, Organizacion, UsuarioOrganizacion

User = get_user_model()


@dataclass
class _FakeObra:
    id: int = 1
    nombre: str = "Obra de prueba"


OBRA = _FakeObra()
D1 = date(2026, 8, 1)
D2 = date(2026, 8, 31)


class VariationRuleTests(SimpleTestCase):
    def test_increase_below_threshold_returns_none(self):
        finding = rules.rule_significant_increase(
            metric="agua", unit="m3", obra=OBRA, period_start=D1, period_end=D2,
            current_value=Decimal("105"), previous_value=Decimal("100"),
        )
        self.assertIsNone(finding)

    def test_increase_at_medium_threshold_fires_medium(self):
        finding = rules.rule_significant_increase(
            metric="agua", unit="m3", obra=OBRA, period_start=D1, period_end=D2,
            current_value=Decimal("120"), previous_value=Decimal("100"),
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.severity, "medium")
        self.assertEqual(finding.code, "CONSUMPTION_INCREASE")

    def test_increase_above_critical_threshold_fires_critical(self):
        finding = rules.rule_significant_increase(
            metric="combustible", unit="L", obra=OBRA, period_start=D1, period_end=D2,
            current_value=Decimal("1340"), previous_value=Decimal("700"),
        )
        self.assertEqual(finding.severity, "critical")
        self.assertAlmostEqual(finding.metadata["variation_percent"], 91.43, places=1)

    def test_increase_reason_carries_rule_observed_threshold(self):
        finding = rules.rule_significant_increase(
            metric="agua", unit="m3", obra=OBRA, period_start=D1, period_end=D2,
            current_value=Decimal("134"), previous_value=Decimal("100"),
        )
        self.assertIn("rule", finding.reason)
        self.assertIn("observed", finding.reason)
        self.assertIn("threshold", finding.reason)

    def test_decrease_is_always_info_severity_never_labeled_improvement(self):
        finding = rules.rule_significant_decrease(
            metric="energia", unit="kWh", obra=OBRA, period_start=D1, period_end=D2,
            current_value=Decimal("72"), previous_value=Decimal("100"),
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.severity, "info")
        self.assertNotIn("mejor", finding.description.lower())
        self.assertNotIn("eficien", finding.description.lower())

    def test_decrease_below_threshold_returns_none(self):
        finding = rules.rule_significant_decrease(
            metric="energia", unit="kWh", obra=OBRA, period_start=D1, period_end=D2,
            current_value=Decimal("95"), previous_value=Decimal("100"),
        )
        self.assertIsNone(finding)

    def test_increase_rule_never_fires_on_a_decrease(self):
        finding = rules.rule_significant_increase(
            metric="agua", unit="m3", obra=OBRA, period_start=D1, period_end=D2,
            current_value=Decimal("50"), previous_value=Decimal("100"),
        )
        self.assertIsNone(finding)

    def test_new_activity_when_previous_is_zero(self):
        finding = rules.rule_new_activity(
            metric="residuos", unit="kg", obra=OBRA, period_start=D1, period_end=D2,
            current_value=Decimal("40"), previous_value=Decimal("0"),
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.code, "NEW_ACTIVITY")
        self.assertEqual(finding.severity, "info")

    def test_new_activity_none_when_current_also_zero(self):
        finding = rules.rule_new_activity(
            metric="residuos", unit="kg", obra=OBRA, period_start=D1, period_end=D2,
            current_value=Decimal("0"), previous_value=Decimal("0"),
        )
        self.assertIsNone(finding)

    def test_increase_rule_never_fires_when_previous_is_zero(self):
        # previous == 0 is NEW_ACTIVITY's job, never a division in the
        # increase rule (would be a ZeroDivisionError if not guarded).
        finding = rules.rule_significant_increase(
            metric="residuos", unit="kg", obra=OBRA, period_start=D1, period_end=D2,
            current_value=Decimal("40"), previous_value=Decimal("0"),
        )
        self.assertIsNone(finding)


class ConcentrationRuleTests(SimpleTestCase):
    def test_concentration_fires_above_threshold(self):
        ranking = [
            {"activo_id": 1, "nombre": "Excavadora", "valor": Decimal("1280"), "unidad": "L"},
            {"activo_id": 2, "nombre": "Camión", "valor": Decimal("600"), "unidad": "L"},
        ]
        finding = rules.rule_consumption_concentration(
            metric="combustible", entity_type="activo", obra=OBRA, period_start=D1, period_end=D2,
            ranking=ranking, total=Decimal("1880"),
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.code, "CONSUMPTION_CONCENTRATION")
        self.assertEqual(finding.drivers[0]["name"], "Excavadora")

    def test_concentration_requires_at_least_two_entities(self):
        ranking = [{"activo_id": 1, "nombre": "Único activo", "valor": Decimal("500"), "unidad": "L"}]
        finding = rules.rule_consumption_concentration(
            metric="combustible", entity_type="activo", obra=OBRA, period_start=D1, period_end=D2,
            ranking=ranking, total=Decimal("500"),
        )
        self.assertIsNone(finding)

    def test_concentration_below_threshold_returns_none(self):
        # Real callers always pass a descending-sorted ranking (see
        # analytics_tools.rank_operational_entities) — ranking[0] is the
        # top entity, and even it stays under the 50% threshold here.
        ranking = [
            {"activo_id": 1, "nombre": "A", "valor": Decimal("40"), "unidad": "L"},
            {"activo_id": 2, "nombre": "B", "valor": Decimal("35"), "unidad": "L"},
            {"activo_id": 3, "nombre": "C", "valor": Decimal("25"), "unidad": "L"},
        ]
        finding = rules.rule_consumption_concentration(
            metric="combustible", entity_type="activo", obra=OBRA, period_start=D1, period_end=D2,
            ranking=ranking, total=Decimal("100"),
        )
        self.assertIsNone(finding)

    def test_impact_concentration_never_mixes_physical_and_impact_units(self):
        ranking = [
            {"clave": 1, "nombre": "Hormigón", "valor": Decimal("460800"), "unidad": "kgCO2e"},
            {"clave": 2, "nombre": "Acero", "valor": Decimal("9891"), "unidad": "kgCO2e"},
        ]
        finding = rules.rule_impact_concentration(obra=OBRA, period_start=D1, period_end=D2, ranking=ranking, total=Decimal("470691"))
        self.assertEqual(finding.code, "IMPACT_CONCENTRATION")
        self.assertEqual(finding.metadata["kind"], "impact")


class ChangeDriverRuleTests(SimpleTestCase):
    def test_change_driver_attributes_the_correct_entity(self):
        current = [
            {"activo_id": 1, "nombre": "Excavadora", "valor": Decimal("1280"), "unidad": "L"},
            {"activo_id": 2, "nombre": "Camión", "valor": Decimal("600"), "unidad": "L"},
        ]
        previous = [
            {"activo_id": 1, "nombre": "Excavadora", "valor": Decimal("700"), "unidad": "L"},
            {"activo_id": 2, "nombre": "Camión", "valor": Decimal("590"), "unidad": "L"},
        ]
        finding = rules.rule_change_driver_activo(
            metric="combustible", obra=OBRA, period_start=D1, period_end=D2,
            current_ranking=current, previous_ranking=previous, total_delta=590.0,
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.entity_name, "Excavadora")
        self.assertGreater(finding.metadata["contribution_percent"], 50)

    def test_change_driver_below_threshold_returns_none(self):
        # The change is evenly spread across three assets — no single one
        # explains a majority of the total delta (each ~33%).
        current = [
            {"activo_id": 1, "nombre": "A", "valor": Decimal("110"), "unidad": "L"},
            {"activo_id": 2, "nombre": "B", "valor": Decimal("110"), "unidad": "L"},
            {"activo_id": 3, "nombre": "C", "valor": Decimal("110"), "unidad": "L"},
        ]
        previous = [
            {"activo_id": 1, "nombre": "A", "valor": Decimal("100"), "unidad": "L"},
            {"activo_id": 2, "nombre": "B", "valor": Decimal("100"), "unidad": "L"},
            {"activo_id": 3, "nombre": "C", "valor": Decimal("100"), "unidad": "L"},
        ]
        finding = rules.rule_change_driver_activo(
            metric="combustible", obra=OBRA, period_start=D1, period_end=D2,
            current_ranking=current, previous_ranking=previous, total_delta=30.0,
        )
        self.assertIsNone(finding)

    def test_change_driver_zero_total_delta_returns_none(self):
        finding = rules.rule_change_driver_material(
            metric="materiales", obra=OBRA, period_start=D1, period_end=D2,
            current_ranking=[], previous_ranking=[], total_delta=0.0,
        )
        self.assertIsNone(finding)


class VariabilityAndCoverageRuleTests(SimpleTestCase):
    def test_high_variability_above_threshold(self):
        finding = rules.rule_high_variability(
            metric="agua", unit="m3", obra=OBRA, period_start=D1, period_end=D2,
            values=[10, 100, 15, 90],
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.code, "HIGH_VARIABILITY")
        self.assertNotIn("anomal", finding.description.lower())

    def test_low_variability_returns_none(self):
        finding = rules.rule_high_variability(
            metric="agua", unit="m3", obra=OBRA, period_start=D1, period_end=D2,
            values=[100, 102, 98, 101],
        )
        self.assertIsNone(finding)

    def test_variability_needs_at_least_two_data_points(self):
        finding = rules.rule_high_variability(
            metric="agua", unit="m3", obra=OBRA, period_start=D1, period_end=D2, values=[100],
        )
        self.assertIsNone(finding)

    def test_incomplete_coverage_fires_when_a_period_is_missing(self):
        finding = rules.rule_incomplete_coverage(
            metric="agua", obra=OBRA, period_start=D1, period_end=D2,
            periodos_totales=4, periodos_con_datos=3,
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.code, "INCOMPLETE_COVERAGE")

    def test_incomplete_coverage_none_when_period_is_full(self):
        finding = rules.rule_incomplete_coverage(
            metric="agua", obra=OBRA, period_start=D1, period_end=D2,
            periodos_totales=4, periodos_con_datos=4,
        )
        self.assertIsNone(finding)


class EvidenceFactorQualityRuleTests(SimpleTestCase):
    def test_missing_evidence_fires_below_threshold(self):
        finding = rules.rule_missing_evidence(
            metric="combustible", obra=OBRA, period_start=D1, period_end=D2,
            total_eventos=10, con_evidencia=2,
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.code, "MISSING_EVIDENCE")

    def test_missing_evidence_none_when_full_coverage(self):
        finding = rules.rule_missing_evidence(
            metric="combustible", obra=OBRA, period_start=D1, period_end=D2,
            total_eventos=10, con_evidencia=9,
        )
        self.assertIsNone(finding)

    def test_missing_evidence_none_when_no_records_at_all(self):
        finding = rules.rule_missing_evidence(
            metric="combustible", obra=OBRA, period_start=D1, period_end=D2,
            total_eventos=0, con_evidencia=0,
        )
        self.assertIsNone(finding)

    def test_unmapped_factor_fires_with_affected_materials(self):
        finding = rules.rule_unmapped_factor(
            metric="materiales", obra=OBRA, period_start=D1, period_end=D2,
            unmapped_materials=[{"material_id": 1, "nombre": "Hormigón", "eventos": 14, "razon": "sin_mapeo"}],
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.code, "UNMAPPED_FACTOR")
        self.assertEqual(finding.severity, "high")

    def test_unmapped_factor_none_when_all_mapped(self):
        finding = rules.rule_unmapped_factor(
            metric="materiales", obra=OBRA, period_start=D1, period_end=D2, unmapped_materials=[],
        )
        self.assertIsNone(finding)

    def test_low_data_quality_fires_above_poor_share(self):
        finding = rules.rule_low_data_quality(
            metric="agua", obra=OBRA, period_start=D1, period_end=D2,
            evaluated_count=10, poor_count=3,
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.code, "LOW_DATA_QUALITY")

    def test_low_data_quality_none_below_threshold(self):
        finding = rules.rule_low_data_quality(
            metric="agua", obra=OBRA, period_start=D1, period_end=D2,
            evaluated_count=10, poor_count=1,
        )
        self.assertIsNone(finding)

    def test_unsupported_data_fires_and_can_be_critical(self):
        finding = rules.rule_unsupported_data(
            metric="combustible", obra=OBRA, period_start=D1, period_end=D2,
            unsupported_count=8, total_eventos=10,
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.severity, "critical")

    def test_unsupported_data_none_when_zero(self):
        finding = rules.rule_unsupported_data(
            metric="combustible", obra=OBRA, period_start=D1, period_end=D2,
            unsupported_count=0, total_eventos=10,
        )
        self.assertIsNone(finding)

    def test_evidence_and_factor_findings_are_never_the_same_code(self):
        # Requirement 7's fix (AI-INTELLIGENCE-02), enforced structurally
        # here: evidence absence and factor absence must stay two codes.
        evidence_finding = rules.rule_missing_evidence(
            metric="materiales", obra=OBRA, period_start=D1, period_end=D2, total_eventos=10, con_evidencia=0,
        )
        factor_finding = rules.rule_unmapped_factor(
            metric="materiales", obra=OBRA, period_start=D1, period_end=D2,
            unmapped_materials=[{"material_id": 1, "nombre": "X", "eventos": 10, "razon": "r"}],
        )
        self.assertNotEqual(evidence_finding.code, factor_finding.code)


class ScoringTests(SimpleTestCase):
    def _finding(self, **overrides):
        base = dict(
            code="CONSUMPTION_INCREASE", severity="medium", title="t", description="d",
            period_start=D1, period_end=D2, metadata={},
        )
        base.update(overrides)
        return rules.DiagnosticFinding(**base)

    def test_base_score_by_severity(self):
        self.assertEqual(scoring.compute_priority(self._finding(severity="critical")), 100)
        self.assertEqual(scoring.compute_priority(self._finding(severity="high")), 75)
        self.assertEqual(scoring.compute_priority(self._finding(severity="info")), 10)

    def test_unmapped_factor_modifier_applied(self):
        score = scoring.compute_priority(self._finding(code="UNMAPPED_FACTOR", severity="high"))
        self.assertEqual(score, 95)

    def test_missing_evidence_modifier_applied(self):
        score = scoring.compute_priority(self._finding(code="MISSING_EVIDENCE", severity="medium"))
        self.assertEqual(score, 65)

    def test_variation_and_share_modifiers_are_additive_and_capped(self):
        finding = self._finding(severity="critical", metadata={"variation_percent": 90, "share_percent": 70})
        self.assertEqual(scoring.compute_priority(finding), 100)  # capped, not 135

    def test_many_records_modifier(self):
        finding = self._finding(severity="low", metadata={"affected_count": 20})
        self.assertEqual(scoring.compute_priority(finding), 35)


class DiagnosticsEngineDemoTenantTests(TestCase):
    """Engine-level tests against the real synthetic demo tenant — the
    same tenant AI-INTELLIGENCE-01/02 already use."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_ai_demo_tenant")
        cls.org = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
        membership = UsuarioOrganizacion.objects.filter(organizacion=cls.org).select_related("user").first()
        cls.admin = membership.user
        cls.obra_norte = Obra.objects.get(organizacion=cls.org, nombre="Edificio Horizonte Norte")

    def test_diagnose_via_tool_resolves_obra_by_name(self):
        result = tools.diagnose_environmental_performance(self.org, self.admin, obra="Horizonte Norte", relative_months=3)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["obra_id"], self.obra_norte.id)

    def test_diagnose_via_tool_missing_obra_argument(self):
        result = tools.diagnose_environmental_performance(self.org, self.admin)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_argument")

    def test_obra_inexistente_is_not_found(self):
        result = tools.diagnose_environmental_performance(self.org, self.admin, obra="Obra que no existe XYZ")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["status"], "not_found")

    def test_rbac_denied_without_data_view_permission(self):
        stranger = User.objects.create_user("diag-stranger", "diag-stranger@example.com", "pw")
        result = tools.diagnose_environmental_performance(self.org, stranger, obra_id=self.obra_norte.id)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "permission_denied")

    def test_obra_scoped_user_denied_for_unauthorized_obra(self):
        other_obra = Obra.objects.create(organizacion=self.org, nombre="Obra restringida diag", fecha_inicio=date(2026, 1, 1))
        scoped_user = User.objects.create_user("diag-scoped", "diag-scoped@example.com", "pw")
        UsuarioOrganizacion.objects.create(
            user=scoped_user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ANALISTA,
            alcance=UsuarioOrganizacion.Alcance.OBRAS,
        )
        result = tools.diagnose_environmental_performance(self.org, scoped_user, obra_id=other_obra.id)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "not_found")

    def test_cross_tenant_obra_never_diagnosed(self):
        other_org = Organizacion.objects.create(nombre="Diagnostics org B")
        foreign_obra = Obra.objects.create(organizacion=other_org, nombre="Obra ajena diag", fecha_inicio=date(2026, 1, 1))
        result = tools.diagnose_environmental_performance(self.org, self.admin, obra_id=foreign_obra.id)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "not_found")

    def test_period_sin_datos_returns_ok_with_no_variation_findings(self):
        # A period with zero data anywhere legitimately still fires
        # INCOMPLETE_COVERAGE (there really is no data for any of its
        # months) — but never a variation/concentration/new-activity
        # finding, since there is nothing to compare or attribute.
        data = run_environmental_diagnostics(
            self.org, self.admin, obra=self.obra_norte,
            date_from="2020-01-01", date_to="2020-03-31", metrics=["agua"],
        )
        codes = {finding["code"] for finding in data["findings"]}
        self.assertEqual(codes - {"INCOMPLETE_COVERAGE"}, set())

    def test_findings_are_ordered_by_priority_descending(self):
        data = run_environmental_diagnostics(self.org, self.admin, obra=self.obra_norte, relative_months=3)
        scores = [finding["priority_score"] for finding in data["findings"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_every_finding_has_period_entity_and_deterministic_reason(self):
        data = run_environmental_diagnostics(self.org, self.admin, obra=self.obra_norte, relative_months=3)
        self.assertGreater(len(data["findings"]), 0)
        for finding in data["findings"]:
            self.assertIn("period_start", finding)
            self.assertIn("period_end", finding)
            self.assertIsNotNone(finding.get("entity_type"))
            self.assertIn("rule", finding["reason"])
            self.assertIn("observed", finding["reason"])
            self.assertIn("threshold", finding["reason"])

    def test_ranking_driver_matches_real_analytics_ranking(self):
        # The mission's hard requirement: drivers must come from real
        # analytics, never an LLM inference. Cross-check the reported
        # top consumer directly against rank_operational_entities.
        from apps.ai import analytics_tools

        data = run_environmental_diagnostics(self.org, self.admin, obra=self.obra_norte, relative_months=1)
        concentration = next((f for f in data["findings"] if f["code"] == "CONSUMPTION_CONCENTRATION" and f["metric"] == "combustible"), None)
        if concentration is None:
            self.skipTest("No concentration finding fired for this window — nothing to cross-check.")
        ranking = analytics_tools.rank_operational_entities(
            self.org, self.admin, entity_type="activo", metric="combustible", obra=self.obra_norte,
            date_from=data["period"]["start"], date_to=data["period"]["end"],
        )
        self.assertEqual(concentration["entity_id"], ranking["ranking"][0]["activo_id"])

    def test_same_input_produces_the_same_output_deterministically(self):
        first = run_environmental_diagnostics(
            self.org, self.admin, obra=self.obra_norte, date_from="2026-06-01", date_to="2026-08-31",
        )
        second = run_environmental_diagnostics(
            self.org, self.admin, obra=self.obra_norte, date_from="2026-06-01", date_to="2026-08-31",
        )
        self.assertEqual(first, second)

    def test_no_computation_is_left_for_the_llm_every_value_is_pre_derived(self):
        data = run_environmental_diagnostics(self.org, self.admin, obra=self.obra_norte, relative_months=3)
        for finding in data["findings"]:
            # Every classification field the LLM would otherwise have to
            # infer is already present and numeric/boolean, not free text.
            self.assertIn(finding["severity"], {"info", "low", "medium", "high", "critical"})
            self.assertIsInstance(finding["priority_score"], int)

    def test_recommendations_come_from_the_controlled_catalog(self):
        from apps.ai.diagnostics.rules import RECOMMENDATIONS

        data = run_environmental_diagnostics(self.org, self.admin, obra=self.obra_norte, relative_months=3)
        for finding in data["findings"]:
            self.assertEqual(finding["recommendations"], RECOMMENDATIONS.get(finding["code"], []))

    def test_ruleset_version_is_present(self):
        data = run_environmental_diagnostics(self.org, self.admin, obra=self.obra_norte, relative_months=3)
        self.assertEqual(data["ruleset_version"], "1.0")

    def test_diagnose_tool_schema_is_registered(self):
        self.assertIn("diagnose_environmental_performance", tools.TOOLS)
        schemas = tools.openai_tool_schemas()
        names = [schema["function"]["name"] for schema in schemas]
        self.assertIn("diagnose_environmental_performance", names)
