"""AI INTELLIGENCE macrofase — forecasting, anomaly detection, risk
scoring, what-if scenarios, prioritization, provenance, knowledge
grounding, multi-turn context, and their tool wrappers.

Every module here is deterministic and reuses AI-INTELLIGENCE-02/03
services — these tests verify: no LLM-free-form computation is needed,
RBAC/tenant isolation hold for every new tool, scenarios never write to
the database, and same-input determinism (model-independence) holds.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from apps.ai import (
    anomalies, context, forecasting, prioritization, provenance as provenance_module, risk, scenarios, tools,
)
from apps.ai.diagnostics import rules as diag_rules
from apps.ai.knowledge_grounding import classify_provenance_entry
from apps.ai.models import Conversation, Message
from apps.ai.tests.test_analytical_tools import _make_reception
from apps.analytics.models import EventoMaterial, FuenteDatos, MaterialOperacional, Obra, Organizacion, UsuarioOrganizacion

User = get_user_model()


@dataclass
class _FakeObra:
    id: int = 1
    nombre: str = "Obra de prueba"


OBRA = _FakeObra()


class ForecastingUnitTests(SimpleTestCase):
    def test_linear_regression_perfect_line(self):
        xs, ys = [0, 1, 2, 3], [10, 20, 30, 40]
        slope, intercept = forecasting._linear_regression(xs, ys)
        self.assertAlmostEqual(slope, 10.0)
        self.assertAlmostEqual(intercept, 10.0)

    def test_r_squared_is_one_for_a_perfect_fit(self):
        xs, ys = [0, 1, 2, 3], [10, 20, 30, 40]
        slope, intercept = forecasting._linear_regression(xs, ys)
        self.assertAlmostEqual(forecasting._r_squared(xs, ys, slope, intercept), 1.0)

    def test_flat_series_has_zero_slope_and_stable_direction(self):
        xs, ys = [0, 1, 2, 3], [50, 50, 50, 50]
        slope, intercept = forecasting._linear_regression(xs, ys)
        self.assertEqual(slope, 0.0)
        self.assertEqual(forecasting._direction(slope, 50), "estable")

    def test_confidence_low_with_few_points(self):
        self.assertEqual(forecasting._confidence(2, 0.99), "low")

    def test_confidence_high_with_many_points_and_good_fit(self):
        self.assertEqual(forecasting._confidence(6, 0.9), "high")

    def test_next_period_label_rolls_over_year(self):
        self.assertEqual(forecasting._next_period_label("2026-12", 1), "2027-01")
        self.assertEqual(forecasting._next_period_label("2026-06", 3), "2026-09")

    def test_forecast_unit_insufficient_points_reports_insuficiente(self):
        result = forecasting._forecast_unit([("2026-08", Decimal("100"))], "m3", 3)
        self.assertEqual(result["confidence"]["nivel"], "insuficiente")
        self.assertEqual(result["proyeccion"], [])

    def test_forecast_unit_never_projects_a_negative_value(self):
        labeled = [("2026-06", Decimal("100")), ("2026-07", Decimal("50")), ("2026-08", Decimal("0"))]
        result = forecasting._forecast_unit(labeled, "m3", 2)
        for row in result["proyeccion"]:
            self.assertGreaterEqual(row["valor_proyectado"], 0.0)


class AnomaliesUnitTests(SimpleTestCase):
    def test_detect_flags_a_real_outlier_with_method_and_threshold(self):
        # With population z-score, |z| is mathematically bounded by
        # sqrt(n-1) — at least 6 points are needed for a single outlier to
        # clear a threshold of 2.0 (the outlier inflates its own std dev).
        labeled = [
            ("2026-03", 100.0), ("2026-04", 102.0), ("2026-05", 98.0),
            ("2026-06", 101.0), ("2026-07", 99.0), ("2026-08", 500.0),
        ]
        result = anomalies._detect_unit(labeled, "m3", 2.0)
        self.assertEqual(result["metodo"], "z_score")
        self.assertEqual(result["threshold"], 2.0)
        self.assertEqual(len(result["anomalias"]), 1)
        anomaly = result["anomalias"][0]
        self.assertEqual(anomaly["periodo"], "2026-08")
        self.assertIn("z_score", anomaly)
        self.assertIn("desviacion_estandar", anomaly)

    def test_detect_no_anomaly_in_a_stable_series(self):
        labeled = [("2026-05", 100.0), ("2026-06", 101.0), ("2026-07", 99.0), ("2026-08", 100.0)]
        result = anomalies._detect_unit(labeled, "m3", 2.0)
        self.assertEqual(result["anomalias"], [])

    def test_detect_insufficient_points_reports_a_warning(self):
        result = anomalies._detect_unit([("2026-08", 100.0)], "m3", 2.0)
        self.assertIn("advertencia", result)
        self.assertEqual(result["anomalias"], [])

    def test_zero_variance_series_never_divides_by_zero(self):
        labeled = [("2026-05", 100.0), ("2026-06", 100.0), ("2026-07", 100.0), ("2026-08", 100.0)]
        result = anomalies._detect_unit(labeled, "m3", 2.0)
        self.assertEqual(result["desviacion_estandar"], 0.0)
        self.assertEqual(result["anomalias"], [])


class RiskUnitTests(SimpleTestCase):
    def test_tier_boundaries(self):
        self.assertEqual(risk._tier(0), "bajo")
        self.assertEqual(risk._tier(29), "bajo")
        self.assertEqual(risk._tier(30), "medio")
        self.assertEqual(risk._tier(60), "alto")
        self.assertEqual(risk._tier(85), "critico")
        self.assertEqual(risk._tier(100), "critico")

    def test_every_diagnostic_code_has_a_risk_category(self):
        # Risk must never silently ignore a finding code — every code the
        # rules module can produce must map to a risk category.
        for code in diag_rules.RECOMMENDATIONS:
            with self.subTest(code=code):
                self.assertIn(code, risk.CATEGORY_BY_CODE)


class KnowledgeGroundingTests(SimpleTestCase):
    def test_classification_keeps_four_categories_distinct(self):
        entry = {
            "evento_recepcion_id": 1, "actividad_id": 2, "resultado": Decimal("100"),
            "unidad_resultado": "kgCO2e", "fecha_calculo": date(2026, 8, 1),
            "factor_id": 5, "version_factor_id": 6, "standard": "EN 15804+A2",
            "boundary": "A1-A3", "dataset_version": "v1", "quality": {"estado": "sufficient"},
        }
        grounding = classify_provenance_entry(entry)
        self.assertEqual(set(grounding.keys()), {"dato_operacional", "factor_cientifico", "fuente_normativa", "interpretacion"})
        self.assertIsNone(grounding["fuente_normativa"])
        self.assertIsNone(grounding["interpretacion"])
        self.assertEqual(grounding["dato_operacional"]["resultado"], Decimal("100"))
        self.assertEqual(grounding["factor_cientifico"]["factor_id"], 5)
        # Never leaks an operational field into the scientific-factor bucket.
        self.assertNotIn("resultado", grounding["factor_cientifico"])


class ConversationDefaultsUnitTests(SimpleTestCase):
    def test_fills_obra_id_when_conversation_has_one_and_call_omits_it(self):
        conversation = _FakeObra(id=None, nombre=None)
        conversation.obra_id = 42
        result = context.apply_conversation_defaults(conversation, "diagnose_environmental_performance", {"metric": "agua"})
        self.assertEqual(result["obra_id"], 42)

    def test_never_overrides_an_explicit_obra_id(self):
        conversation = _FakeObra(id=None, nombre=None)
        conversation.obra_id = 42
        result = context.apply_conversation_defaults(conversation, "diagnose_environmental_performance", {"obra_id": 99})
        self.assertEqual(result["obra_id"], 99)

    def test_never_fills_for_a_tool_with_no_obra_argument(self):
        conversation = _FakeObra(id=None, nombre=None)
        conversation.obra_id = 42
        result = context.apply_conversation_defaults(conversation, "search_environmental_knowledge", {"query": "agua"})
        self.assertNotIn("obra_id", result)

    def test_never_mutates_the_caller_arguments_dict(self):
        conversation = _FakeObra(id=None, nombre=None)
        conversation.obra_id = 42
        original = {"metric": "agua"}
        context.apply_conversation_defaults(conversation, "diagnose_environmental_performance", original)
        self.assertEqual(original, {"metric": "agua"})

    def test_build_context_note_mentions_the_fixed_obra(self):
        conversation = _FakeObra(id=None, nombre=None)
        conversation.obra = OBRA
        note = context.build_context_note(conversation)
        self.assertIn(OBRA.nombre, note)
        self.assertIn(str(OBRA.id), note)

    def test_build_context_note_is_none_without_a_fixed_obra(self):
        conversation = _FakeObra(id=None, nombre=None)
        conversation.obra = None
        self.assertIsNone(context.build_context_note(conversation))


class MacroToolsDemoTenantTests(TestCase):
    """Engine-level tests for every new macrofase tool, against the real
    synthetic demo tenant (same tenant AI-01/02/03 already use)."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_ai_demo_tenant")
        cls.org = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
        membership = UsuarioOrganizacion.objects.filter(organizacion=cls.org).select_related("user").first()
        cls.admin = membership.user
        cls.obra_norte = Obra.objects.get(organizacion=cls.org, nombre="Edificio Horizonte Norte")

    def test_forecast_tool_returns_confidence_metadata(self):
        result = tools.forecast_environmental_metric(self.org, self.admin, obra_id=self.obra_norte.id, metric="agua", periods_back=4, periods_ahead=2)
        self.assertTrue(result["ok"])
        unit_result = result["por_unidad"]["m3"]
        self.assertIn("confidence", unit_result)
        self.assertIn("nivel", unit_result["confidence"])
        self.assertEqual(len(unit_result["proyeccion"]), 2)

    def test_forecast_resolves_obra_by_name(self):
        result = tools.forecast_environmental_metric(self.org, self.admin, obra="Horizonte Norte", metric="agua")
        self.assertTrue(result["ok"])

    def test_forecast_requires_a_metric_or_material(self):
        result = tools.forecast_environmental_metric(self.org, self.admin, obra_id=self.obra_norte.id)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_argument")

    def test_anomaly_tool_reports_method_and_threshold(self):
        result = tools.detect_environmental_anomalies(self.org, self.admin, obra_id=self.obra_norte.id, metric="combustible", periods_back=4)
        self.assertTrue(result["ok"])
        unit_result = next(iter(result["por_unidad"].values()))
        self.assertEqual(unit_result["metodo"], "z_score")
        self.assertIn("threshold", unit_result)

    def test_anomaly_tool_custom_threshold_is_echoed_back(self):
        result = tools.detect_environmental_anomalies(self.org, self.admin, obra_id=self.obra_norte.id, metric="combustible", periods_back=4, threshold=3.5)
        unit_result = next(iter(result["por_unidad"].values()))
        self.assertEqual(unit_result["threshold"], 3.5)

    def test_risk_tool_is_built_from_real_diagnostics_findings(self):
        from apps.ai.diagnostics import run_environmental_diagnostics

        risk_result = tools.score_environmental_risk(self.org, self.admin, obra_id=self.obra_norte.id, relative_months=3)
        diagnostics_result = run_environmental_diagnostics(self.org, self.admin, obra=self.obra_norte, relative_months=3)
        self.assertTrue(risk_result["ok"])
        self.assertEqual(risk_result["basado_en_findings"], len(diagnostics_result["findings"]))
        expected_score = min(sum(risk.RISK_WEIGHTS.get(f["severity"], 0) for f in diagnostics_result["findings"]), 100)
        self.assertEqual(risk_result["risk_score"], expected_score)

    def test_risk_score_is_between_zero_and_hundred(self):
        result = tools.score_environmental_risk(self.org, self.admin, obra_id=self.obra_norte.id, relative_months=3)
        self.assertGreaterEqual(result["risk_score"], 0)
        self.assertLessEqual(result["risk_score"], 100)

    def test_prioritization_actions_come_from_recommendations_catalog(self):
        result = tools.prioritize_environmental_actions(self.org, self.admin, obra_id=self.obra_norte.id, relative_months=3, max_actions=5)
        self.assertTrue(result["ok"])
        self.assertLessEqual(len(result["acciones"]), 5)
        all_recommendation_texts = {text for texts in diag_rules.RECOMMENDATIONS.values() for text in texts}
        for action in result["acciones"]:
            self.assertIn(action["accion"], all_recommendation_texts)

    def test_prioritization_actions_are_sorted_by_priority_descending(self):
        result = tools.prioritize_environmental_actions(self.org, self.admin, obra_id=self.obra_norte.id, relative_months=3, max_actions=20)
        scores = [action["priority_score"] for action in result["acciones"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_scenario_never_writes_to_the_database(self):
        before = EventoMaterial.objects.count()
        result = tools.simulate_environmental_scenario(
            self.org, self.admin, obra_id=self.obra_norte.id, metric="agua", percent_change=25, relative_months=3,
        )
        after = EventoMaterial.objects.count()
        self.assertTrue(result["ok"])
        self.assertEqual(before, after)
        self.assertIn("hipotético", result["nota"])

    def test_scenario_hypothetical_value_matches_the_math(self):
        result = tools.simulate_environmental_scenario(
            self.org, self.admin, obra_id=self.obra_norte.id, metric="agua", percent_change=50, relative_months=3,
        )
        unit_result = result["resultados"]["m3"]
        base = unit_result["valor_base_real"]
        hypothetical = unit_result["valor_hipotetico"]
        self.assertEqual(hypothetical, base * Decimal("1.5"))

    def test_scenario_requires_obra(self):
        result = tools.simulate_environmental_scenario(self.org, self.admin, metric="agua", percent_change=10)
        self.assertFalse(result["ok"])

    def test_scenario_requires_percent_or_absolute(self):
        result = tools.simulate_environmental_scenario(self.org, self.admin, obra_id=self.obra_norte.id, metric="agua")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_argument")

    def test_scenario_rejects_extreme_percent_change(self):
        result = tools.simulate_environmental_scenario(
            self.org, self.admin, obra_id=self.obra_norte.id, metric="agua", percent_change=99999,
        )
        self.assertFalse(result["ok"])

    def test_provenance_tool_returns_full_chain_with_grounding(self):
        material = MaterialOperacional.objects.get(organizacion=self.org, codigo="HORIZONTE-HORMIGON")
        result = tools.trace_metric_provenance(self.org, self.admin, material_id=material.id, obra_id=self.obra_norte.id, limit=3)
        self.assertTrue(result["ok"])
        self.assertGreater(result["entradas"], 0)
        for entry in result["cadena"]:
            self.assertIn("grounding", entry)
            self.assertIn("dato_operacional", entry["grounding"])
            self.assertIn("factor_cientifico", entry["grounding"])

    def test_provenance_tool_resolves_material_by_name(self):
        result = tools.trace_metric_provenance(self.org, self.admin, material="hormigón", obra_id=self.obra_norte.id)
        self.assertTrue(result["ok"])

    def test_provenance_tool_requires_material(self):
        result = tools.trace_metric_provenance(self.org, self.admin, obra_id=self.obra_norte.id)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_argument")

    def test_conversation_context_tool_without_conversation(self):
        result = tools.get_conversation_context(self.org, self.admin)
        self.assertTrue(result["ok"])
        self.assertIsNone(result["data"]["obra_id"])

    def test_conversation_context_infers_obra_from_history(self):
        conversation = Conversation.objects.create(organizacion=self.org, usuario=self.admin)
        tool_result = tools.diagnose_environmental_performance(self.org, self.admin, obra_id=self.obra_norte.id, relative_months=3)
        Message.objects.create(conversation=conversation, role=Message.Role.TOOL, tool_name="diagnose_environmental_performance", tool_result=tool_result)
        inferred = context.infer_conversation_context(conversation)
        self.assertEqual(inferred["obra_id"], self.obra_norte.id)


class MacroToolsRbacAndTenantTests(TestCase):
    """RBAC and cross-tenant isolation for every new macrofase tool."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_ai_demo_tenant")
        cls.org = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
        membership = UsuarioOrganizacion.objects.filter(organizacion=cls.org).select_related("user").first()
        cls.admin = membership.user
        cls.obra_norte = Obra.objects.get(organizacion=cls.org, nombre="Edificio Horizonte Norte")
        cls.stranger = User.objects.create_user("macro-stranger", "macro-stranger@example.com", "pw")
        cls.other_org = Organizacion.objects.create(nombre="Macro org B")
        cls.foreign_obra = Obra.objects.create(organizacion=cls.other_org, nombre="Obra ajena macro", fecha_inicio=date(2026, 1, 1))

    def test_all_new_tools_deny_without_permission(self):
        calls = [
            ("forecast_environmental_metric", {"obra_id": self.obra_norte.id, "metric": "agua"}),
            ("detect_environmental_anomalies", {"obra_id": self.obra_norte.id, "metric": "agua"}),
            ("score_environmental_risk", {"obra_id": self.obra_norte.id}),
            ("prioritize_environmental_actions", {"obra_id": self.obra_norte.id}),
            ("simulate_environmental_scenario", {"obra_id": self.obra_norte.id, "metric": "agua", "percent_change": 10}),
            ("trace_metric_provenance", {"material": "hormigón", "obra_id": self.obra_norte.id}),
        ]
        for tool_name, arguments in calls:
            with self.subTest(tool=tool_name):
                result = tools.execute_tool(tool_name, organization=self.org, user=self.stranger, arguments=arguments)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "permission_denied")

    def test_all_new_tools_reject_a_foreign_tenants_obra(self):
        calls = [
            ("forecast_environmental_metric", {"obra_id": self.foreign_obra.id, "metric": "agua"}),
            ("detect_environmental_anomalies", {"obra_id": self.foreign_obra.id, "metric": "agua"}),
            ("score_environmental_risk", {"obra_id": self.foreign_obra.id}),
            ("prioritize_environmental_actions", {"obra_id": self.foreign_obra.id}),
            ("simulate_environmental_scenario", {"obra_id": self.foreign_obra.id, "metric": "agua", "percent_change": 10}),
            ("trace_metric_provenance", {"material": "hormigón", "obra_id": self.foreign_obra.id}),
        ]
        for tool_name, arguments in calls:
            with self.subTest(tool=tool_name):
                result = tools.execute_tool(tool_name, organization=self.org, user=self.admin, arguments=arguments)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "not_found")

    def test_all_new_tools_registered_with_valid_schemas(self):
        for tool_name in (
            "forecast_environmental_metric", "detect_environmental_anomalies", "score_environmental_risk",
            "prioritize_environmental_actions", "simulate_environmental_scenario", "trace_metric_provenance",
            "get_conversation_context",
        ):
            with self.subTest(tool=tool_name):
                self.assertIn(tool_name, tools.TOOLS)
        schemas = tools.openai_tool_schemas()
        self.assertEqual(len(schemas), len(tools.TOOLS))


class OrchestratorMultiTurnTests(TestCase):
    """Multi-turn context: a conversation scoped to an obra should never
    need the user to repeat the obra name in a follow-up turn."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_ai_demo_tenant")
        cls.org = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
        membership = UsuarioOrganizacion.objects.filter(organizacion=cls.org).select_related("user").first()
        cls.admin = membership.user
        cls.obra_norte = Obra.objects.get(organizacion=cls.org, nombre="Edificio Horizonte Norte")

    def test_conversation_obra_is_injected_when_the_model_omits_it(self):
        from apps.ai.orchestrator import run_turn
        from apps.ai.providers import AIChatResult, ToolCallRequest

        class FakeProviderOmittingObra:
            name = "fake"
            model = "fake/model"
            available = True

            def __init__(self):
                self._step = 0

            def chat(self, *, messages, tools=None):
                self._step += 1
                if self._step == 1:
                    return AIChatResult(
                        content=None,
                        tool_calls=[ToolCallRequest(id="call_1", name="score_environmental_risk", arguments={})],
                        model=self.model,
                    )
                return AIChatResult(content="Listo.", tool_calls=[], model=self.model)

        conversation = Conversation.objects.create(organizacion=self.org, usuario=self.admin, obra=self.obra_norte)
        run_turn(
            conversation=conversation, organization=self.org, user=self.admin,
            user_message="¿Qué tan riesgosa está esta obra?", provider=FakeProviderOmittingObra(),
        )
        tool_message = conversation.messages.get(role="tool")
        self.assertTrue(tool_message.tool_result["ok"])
        self.assertEqual(tool_message.tool_result["obra_id"], self.obra_norte.id)

    def test_conversation_scoped_obra_is_visible_to_the_model_before_any_tool_call(self):
        # The real bug this fixes: without a context note, a conversation
        # created with `obra` already set still made the model ask "which
        # obra?" because nothing in its own message history said so until
        # AFTER it happened to call a tool. Verified here at the mechanical
        # level: the obra's name/id must appear in what the provider sees
        # on the very first call, before any tool has run.
        from apps.ai.orchestrator import run_turn
        from apps.ai.providers import AIChatResult

        seen_messages = []

        class RecordingProvider:
            name = "fake"
            model = "fake/model"
            available = True

            def chat(self, *, messages, tools=None):
                seen_messages.append(messages)
                return AIChatResult(content="Ok.", tool_calls=[], model=self.model)

        conversation = Conversation.objects.create(organizacion=self.org, usuario=self.admin, obra=self.obra_norte)
        run_turn(conversation=conversation, organization=self.org, user=self.admin, user_message="hola", provider=RecordingProvider())
        first_call_messages = seen_messages[0]
        system_texts = " ".join(m["content"] for m in first_call_messages if m["role"] == "system")
        self.assertIn(self.obra_norte.nombre, system_texts)
        self.assertIn(str(self.obra_norte.id), system_texts)
