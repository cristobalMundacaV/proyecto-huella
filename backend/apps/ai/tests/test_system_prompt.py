from django.test import SimpleTestCase

from apps.ai.system_prompt import SYSTEM_PROMPT, SYSTEM_PROMPT_VERSION, build_messages


class SystemPromptTests(SimpleTestCase):
    def test_version_is_set_and_stable_format(self):
        self.assertTrue(SYSTEM_PROMPT_VERSION)
        self.assertIn("/", SYSTEM_PROMPT_VERSION)

    def test_required_guardrail_phrases_are_present(self):
        required_fragments = [
            "Carbono Zero", "no inventes", "aprobado", "oportunidad potencial",
            "cumplimiento normativo", "no tengo esa información", "hechos", "inferencias", "recomendaciones",
            "provenance" if "provenance" in SYSTEM_PROMPT.lower() else "fuente",
            "intervención humana",
        ]
        lowered = SYSTEM_PROMPT.lower()
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment.lower(), lowered)

    def test_never_query_database_directly_is_stated(self):
        self.assertIn("nunca accedes a la base de datos directamente", SYSTEM_PROMPT.lower())

    def test_ai_intelligence_02_guardrails_are_present(self):
        required_fragments = [
            "resolve_entity", "rank_operational_entities", "compare_projects",
            "nunca calcules tú mismo", "dame el id", "ambiguous",
            "no hay evidencia o factor ambiental",
        ]
        lowered = SYSTEM_PROMPT.lower()
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment.lower(), lowered)

    def test_ai_intelligence_03_diagnostics_guardrails_are_present(self):
        required_fragments = [
            "diagnose_environmental_performance", "priority_score", "reason",
            "nunca reclasifiques la severidad", "nunca llames \"anomalía\"",
            "nunca se presenta como una mejora ambiental",
        ]
        lowered = SYSTEM_PROMPT.lower()
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment.lower(), lowered)

    def test_ai_intelligence_macro_guardrails_are_present(self):
        required_fragments = [
            "forecast_environmental_metric", "confidence.nivel", "detect_environmental_anomalies",
            "z-score", "score_environmental_risk", "simulate_environmental_scenario",
            "puramente hipotético", "prioritize_environmental_actions", "trace_metric_provenance",
            "dato operacional", "factor científico", "fuente normativa", "get_conversation_context",
        ]
        lowered = SYSTEM_PROMPT.lower()
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment.lower(), lowered)

    def test_build_messages_prepends_system_and_never_mutates_history(self):
        history = [{"role": "user", "content": "hola"}]
        messages = build_messages(history=history)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], SYSTEM_PROMPT)
        self.assertEqual(messages[1:], history)
        self.assertEqual(len(history), 1)

    def test_build_messages_appends_an_optional_context_note(self):
        history = [{"role": "user", "content": "hola"}]
        messages = build_messages(history=history, context_note="Nota de contexto de prueba.")
        self.assertEqual(messages[1], {"role": "system", "content": "Nota de contexto de prueba."})
        self.assertEqual(messages[2:], history)

    def test_build_messages_without_context_note_has_only_one_system_message(self):
        messages = build_messages(history=[], context_note=None)
        self.assertEqual(len(messages), 1)
