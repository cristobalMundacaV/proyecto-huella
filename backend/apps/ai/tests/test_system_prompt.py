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

    def test_build_messages_prepends_system_and_never_mutates_history(self):
        history = [{"role": "user", "content": "hola"}]
        messages = build_messages(history=history)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], SYSTEM_PROMPT)
        self.assertEqual(messages[1:], history)
        self.assertEqual(len(history), 1)
