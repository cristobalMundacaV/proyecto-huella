"""AI-INTELLIGENCE-01 — orchestration loop: tool execution, no-hallucination
fallback, provenance, conversation history, cost/token accounting. The LLM
is always a small fake here, never a real network call."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.analytics.models import Organizacion, UsuarioOrganizacion
from apps.ai.models import Conversation, Message
from apps.ai.orchestrator import OrchestratorError, run_turn
from apps.ai.providers import AIChatResult, AIProviderError, ToolCallRequest

User = get_user_model()


class FakeProvider:
    name = "fake"
    model = "fake/model"

    def __init__(self, results=None, *, available=True):
        self._results = list(results or [])
        self._available = available
        self.calls = []

    @property
    def available(self):
        return self._available

    def chat(self, *, messages, tools=None):
        self.calls.append({"messages": messages, "tools": tools})
        if not self._results:
            raise AssertionError("FakeProvider ran out of scripted results")
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@override_settings(AI_MAX_TOOL_ITERATIONS=4, AI_MAX_MESSAGES_PER_CONVERSATION=200, AI_MAX_REQUESTS_PER_ORG_PER_HOUR=60)
class OrchestratorTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="AI orchestrator org")
        self.user = User.objects.create_user("ai-orch-user", "ai-orch-user@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.conversation = Conversation.objects.create(organizacion=self.org, usuario=self.user)

    def test_plain_text_reply_persists_user_and_assistant_messages(self):
        provider = FakeProvider([AIChatResult(content="La organización activa es de prueba.", tool_calls=[],
                                              model="fake/model", tokens_input=12, tokens_output=8)])
        reply = run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                         user_message="¿Cuál es mi organización?", provider=provider)
        self.assertEqual(reply.role, Message.Role.ASSISTANT)
        self.assertEqual(reply.content, "La organización activa es de prueba.")
        self.assertEqual(reply.tokens_input, 12)
        self.assertEqual(reply.tokens_output, 8)
        roles = list(self.conversation.messages.values_list("role", flat=True))
        self.assertEqual(roles, [Message.Role.USER, Message.Role.ASSISTANT])

    def test_tool_call_then_final_answer_persists_tool_round_trip_and_provenance(self):
        provider = FakeProvider([
            AIChatResult(content=None, tool_calls=[ToolCallRequest(id="call_1", name="get_current_organization", arguments={})],
                        model="fake/model", tokens_input=20, tokens_output=4),
            AIChatResult(content="Tu organización es la de prueba.", tool_calls=[], model="fake/model",
                        tokens_input=30, tokens_output=10),
        ])
        reply = run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                         user_message="¿Cuál es mi organización?", provider=provider)
        self.assertEqual(reply.content, "Tu organización es la de prueba.")
        self.assertEqual(reply.tokens_input, 50)
        self.assertEqual(reply.tokens_output, 14)
        self.assertEqual(len(reply.provenance), 1)
        self.assertEqual(reply.provenance[0]["tool"], "get_current_organization")

        tool_message = self.conversation.messages.get(role=Message.Role.TOOL)
        self.assertEqual(tool_message.tool_name, "get_current_organization")
        self.assertTrue(tool_message.tool_result["ok"])
        self.assertEqual(tool_message.tool_result["data"]["organizacion_id"], self.org.organizacion_id)

    def test_tool_failure_is_reported_to_model_not_hidden_or_faked(self):
        provider = FakeProvider([
            AIChatResult(content=None, tool_calls=[ToolCallRequest(id="call_1", name="get_material_summary", arguments={})],
                        model="fake/model"),
            AIChatResult(content="No encontré ese material.", tool_calls=[], model="fake/model"),
        ])
        run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                user_message="Resume el material 999", provider=provider)
        tool_message = self.conversation.messages.get(role=Message.Role.TOOL)
        self.assertFalse(tool_message.tool_result["ok"])
        self.assertEqual(tool_message.tool_result["error"], "missing_argument")
        # A failed tool result must never be counted as a used source.
        final = self.conversation.messages.filter(role=Message.Role.ASSISTANT).last()
        self.assertEqual(final.provenance, [])

    def test_exhausting_tool_iterations_stops_with_explicit_message_never_infinite_loop(self):
        always_calls_tool = [
            AIChatResult(content=None, tool_calls=[ToolCallRequest(id=f"call_{i}", name="get_current_organization", arguments={})],
                        model="fake/model")
            for i in range(10)
        ]
        with override_settings(AI_MAX_TOOL_ITERATIONS=2):
            provider = FakeProvider(always_calls_tool)
            reply = run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                            user_message="pregunta", provider=provider)
        self.assertIn("no pude completar", reply.content.lower())
        self.assertEqual(len(provider.calls), 2)

    def test_provider_disabled_never_calls_chat(self):
        provider = FakeProvider([], available=False)
        reply = run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                         user_message="hola", provider=provider)
        self.assertEqual(provider.calls, [])
        self.assertIn("no está habilitado", reply.content.lower())

    def test_provider_error_becomes_a_safe_message_never_raises(self):
        provider = FakeProvider([AIProviderError("network_error")])
        reply = run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                         user_message="hola", provider=provider)
        self.assertIn("no se pudo conectar", reply.content.lower())

    def test_tool_result_with_decimal_and_date_values_is_persisted_without_crashing(self):
        # Found by the real OpenRouter smoke test: a genuine tool result
        # (e.g. get_material_hotspots) carries real Decimal/date values,
        # which the plain JSON encoder cannot serialize. Message.tool_result
        # must use DjangoJSONEncoder — this locks that in with a fake tool
        # result shaped the same way, no real provider/network involved.
        from decimal import Decimal
        from datetime import date

        provider = FakeProvider([
            AIChatResult(content=None, tool_calls=[ToolCallRequest(id="call_1", name="get_current_organization", arguments={})],
                        model="fake/model"),
            AIChatResult(content="Listo.", tool_calls=[], model="fake/model"),
        ])
        from unittest.mock import patch
        fake_result = {"ok": True, "data": {"total": Decimal("460800.0000000000"), "fecha": date(2026, 9, 12)}}
        with patch("apps.ai.orchestrator.execute_tool", return_value=fake_result):
            reply = run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                            user_message="pregunta", provider=provider)
        self.assertEqual(reply.content, "Listo.")
        tool_message = self.conversation.messages.get(role=Message.Role.TOOL)
        self.assertEqual(tool_message.tool_result["data"]["total"], "460800.0000000000")

    def test_conversation_history_is_replayed_to_the_model(self):
        provider = FakeProvider([
            AIChatResult(content="Respuesta 1", tool_calls=[], model="fake/model"),
        ])
        run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                user_message="Primera pregunta", provider=provider)
        provider2 = FakeProvider([AIChatResult(content="Respuesta 2", tool_calls=[], model="fake/model")])
        run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                user_message="Segunda pregunta", provider=provider2)
        sent_messages = provider2.calls[0]["messages"]
        contents = [m["content"] for m in sent_messages if m["role"] == "user"]
        self.assertIn("Primera pregunta", contents)
        self.assertIn("Segunda pregunta", contents)

    def test_conversation_message_limit_is_enforced(self):
        with override_settings(AI_MAX_MESSAGES_PER_CONVERSATION=1):
            Message.objects.create(conversation=self.conversation, role=Message.Role.ASSISTANT, content="saludo")
            provider = FakeProvider([AIChatResult(content="no debería llegar aquí", tool_calls=[], model="fake/model")])
            with self.assertRaises(OrchestratorError) as ctx:
                run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                        user_message="hola", provider=provider)
            self.assertEqual(ctx.exception.code, "conversation_limit_reached")
        self.assertEqual(provider.calls, [])

    def test_org_hourly_request_limit_is_enforced(self):
        with override_settings(AI_MAX_REQUESTS_PER_ORG_PER_HOUR=1):
            Message.objects.create(conversation=self.conversation, role=Message.Role.ASSISTANT, content="respuesta previa")
            provider = FakeProvider([AIChatResult(content="no debería llegar aquí", tool_calls=[], model="fake/model")])
            with self.assertRaises(OrchestratorError) as ctx:
                run_turn(conversation=self.conversation, organization=self.org, user=self.user,
                        user_message="hola", provider=provider)
            self.assertEqual(ctx.exception.code, "rate_limit_reached")
        self.assertEqual(provider.calls, [])
