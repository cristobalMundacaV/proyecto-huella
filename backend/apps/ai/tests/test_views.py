"""AI-INTELLIGENCE-01 — API: auth, tenant isolation, RBAC, greeting, history."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.analytics.models import Organizacion, UsuarioOrganizacion
from apps.ai.models import Conversation
from apps.ai.providers import AIChatResult

User = get_user_model()


class FakeProvider:
    name = "fake"
    model = "fake/model"
    available = True

    def __init__(self, content="Respuesta de prueba"):
        self._content = content

    def chat(self, *, messages, tools=None):
        return AIChatResult(content=self._content, tool_calls=[], model=self.model, tokens_input=5, tokens_output=5)


class AiChatApiTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="AI views org")
        self.other_org = Organizacion.objects.create(nombre="AI views other org")
        self.user = User.objects.create_user("ai-views-user", "ai-views-user@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.stranger = User.objects.create_user("ai-views-stranger", "ai-views-stranger@example.com", "pw")
        self.client_api = APIClient()

    def _conversations_url(self, org=None):
        org = org or self.org
        return f"/api/ai/{org.organizacion_id}/conversations/"

    def test_anonymous_request_is_rejected(self):
        # OrganizacionTenantMiddleware intercepts before DRF's own
        # IsAuthenticated check runs, so an unauthenticated request to any
        # URL carrying organizacion_id gets a 401 here (not DRF's 403).
        response = self.client_api.post(self._conversations_url(), {}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_user_without_membership_cannot_access_organization(self):
        self.client_api.force_login(self.stranger)
        response = self.client_api.post(self._conversations_url(), {}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_creating_conversation_returns_automatic_greeting_without_provider_call(self):
        self.client_api.force_login(self.user)
        with patch("apps.ai.views.default_provider") as mocked_provider:
            response = self.client_api.post(self._conversations_url(), {}, format="json")
            mocked_provider.assert_not_called()
        self.assertEqual(response.status_code, 201)
        messages = response.data["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "assistant")
        self.assertIn("Carbono Zero", messages[0]["content"])

    def test_conversation_cannot_be_read_through_another_organization(self):
        self.client_api.force_login(self.user)
        created = self.client_api.post(self._conversations_url(), {}, format="json").data
        conversation_id = created["id"]

        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.other_org, rol=UsuarioOrganizacion.Rol.ADMIN)
        response = self.client_api.get(
            f"/api/ai/{self.other_org.organizacion_id}/conversations/{conversation_id}/",
        )
        self.assertEqual(response.status_code, 404)

    def test_send_message_persists_and_returns_assistant_reply(self):
        self.client_api.force_login(self.user)
        conversation_id = self.client_api.post(self._conversations_url(), {}, format="json").data["id"]
        with patch("apps.ai.views.default_provider", return_value=FakeProvider("Hola, esta es una respuesta real.")):
            response = self.client_api.post(
                f"/api/ai/{self.org.organizacion_id}/conversations/{conversation_id}/messages/",
                {"content": "¿Cómo estamos ambientalmente?"}, format="json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["content"], "Hola, esta es una respuesta real.")
        conversation = Conversation.objects.get(pk=conversation_id)
        self.assertEqual(conversation.messages.count(), 3)  # greeting + user + assistant

    def test_send_message_requires_non_empty_content(self):
        self.client_api.force_login(self.user)
        conversation_id = self.client_api.post(self._conversations_url(), {}, format="json").data["id"]
        response = self.client_api.post(
            f"/api/ai/{self.org.organizacion_id}/conversations/{conversation_id}/messages/",
            {"content": ""}, format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_list_conversations_only_returns_the_requesting_users_own(self):
        self.client_api.force_login(self.user)
        self.client_api.post(self._conversations_url(), {}, format="json")
        other_user = User.objects.create_user("ai-views-user2", "ai-views-user2@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=other_user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.client_api.force_login(other_user)
        response = self.client_api.get(self._conversations_url())
        self.assertEqual(response.data["conversaciones"], [])
