from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.models import Organizacion, UsuarioOrganizacion
from apps.ai.greeting import GREETING_TEXT, ensure_greeting
from apps.ai.models import Conversation, Message

User = get_user_model()


class GreetingTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="AI greeting org")
        self.user = User.objects.create_user("ai-greeting-user", "ai-greeting-user@example.com", "pw")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)
        self.conversation = Conversation.objects.create(organizacion=self.org, usuario=self.user)

    def test_greeting_created_for_new_conversation_without_any_provider_call(self):
        message = ensure_greeting(self.conversation)
        self.assertEqual(message.role, Message.Role.ASSISTANT)
        self.assertEqual(message.content, GREETING_TEXT)
        self.assertEqual(message.model, "")
        self.assertIsNone(message.tokens_input)
        self.assertIsNone(message.tokens_output)

    def test_greeting_mentions_carbono_zero_and_asks_how_to_help(self):
        self.assertIn("Carbono Zero", GREETING_TEXT)
        self.assertIn("?", GREETING_TEXT)

    def test_greeting_is_idempotent(self):
        first = ensure_greeting(self.conversation)
        second = ensure_greeting(self.conversation)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(self.conversation.messages.count(), 1)

    def test_greeting_not_reissued_once_real_conversation_started(self):
        Message.objects.create(conversation=self.conversation, role=Message.Role.USER, content="hola")
        result = ensure_greeting(self.conversation)
        self.assertEqual(result.role, Message.Role.USER)
        self.assertEqual(self.conversation.messages.count(), 1)
