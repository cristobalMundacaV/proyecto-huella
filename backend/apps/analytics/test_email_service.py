from unittest.mock import patch

import resend
from django.core import mail
from django.test import TestCase, override_settings

from .services.email_service import EmailDeliveryError, EmailService


class EmailServiceTests(TestCase):
    @override_settings(
        RESEND_API_KEY="re_test_private_key",
        DEFAULT_FROM_EMAIL="Carbono Zero <notificaciones@example.com>",
    )
    @patch("apps.analytics.services.email_service.resend.Emails.send")
    def test_resend_sdk_receives_the_transactional_payload(self, send):
        send.return_value = {"id": "email_123"}

        result = EmailService._send(
            "persona@example.com",
            "Asunto",
            "Título",
            "Hola Persona,",
            "Contenido del mensaje.",
            "Continuar",
            "https://frontend.test/activar",
            "account_activation",
        )

        self.assertEqual(result, {"id": "email_123"})
        self.assertEqual(resend.api_key, "re_test_private_key")
        payload = send.call_args.args[0]
        self.assertEqual(payload["from"], "Carbono Zero <notificaciones@example.com>")
        self.assertEqual(payload["to"], ["persona@example.com"])
        self.assertEqual(payload["subject"], "Asunto")
        self.assertIn("https://frontend.test/activar", payload["html"])

    @override_settings(
        RESEND_API_KEY="",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="notificaciones@example.com",
    )
    @patch("apps.analytics.services.email_service.resend.Emails.send")
    def test_django_email_backend_is_used_without_resend_key(self, send):
        EmailService._send(
            "persona@example.com", "Asunto", "Título", "Hola,", "Contenido"
        )

        send.assert_not_called()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["persona@example.com"])
        self.assertEqual(mail.outbox[0].alternatives[0].mimetype, "text/html")

    @override_settings(RESEND_API_KEY="re_test_private_key")
    @patch("apps.analytics.services.email_service.resend.Emails.send")
    def test_sdk_failure_is_logged_safely_and_raises_controlled_error(self, send):
        send.side_effect = RuntimeError("provider unavailable")

        with self.assertLogs("apps.analytics.services.email_service", level="ERROR") as logs:
            with self.assertRaises(EmailDeliveryError):
                EmailService._send(
                    "persona@example.com",
                    "Asunto",
                    "Título",
                    "Hola,",
                    "Contenido confidencial",
                    email_type="organization_invitation",
                )

        output = "\n".join(logs.output)
        self.assertIn("provider=resend", output)
        self.assertIn("type=organization_invitation", output)
        self.assertIn("p***@e***.com", output)
        self.assertNotIn("persona@example.com", output)
        self.assertNotIn("re_test_private_key", output)
        self.assertNotIn("Contenido confidencial", output)
