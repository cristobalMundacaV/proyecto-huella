from unittest.mock import patch
from types import SimpleNamespace

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


@override_settings(
    RESEND_API_KEY="",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notificaciones@example.com",
)
class TransactionalEmailContentTests(TestCase):
    def setUp(self):
        self.user = SimpleNamespace(
            email="marcela@example.com", first_name="Marcela", username="marcela"
        )
        self.organization = SimpleNamespace(nombre="Constructora Andina del Biobío SpA")

    def html(self):
        return mail.outbox[-1].alternatives[0].content

    def test_activation_contains_brand_organization_cta_and_url(self):
        url = "https://frontend.test/activar/uid/token"
        EmailService.send_account_activation(self.user, self.organization, url)

        html = self.html()
        self.assertIn("CARBONO ZERO", html)
        self.assertIn(self.organization.nombre, html)
        self.assertIn("Activar mi cuenta", html)
        self.assertIn(url, html)
        self.assertIn(url, mail.outbox[-1].body)

    def test_invitation_explains_that_the_existing_account_is_reused(self):
        EmailService.send_organization_invitation(
            self.user, self.organization, "https://frontend.test"
        )

        html = self.html()
        self.assertIn(self.organization.nombre, html)
        self.assertIn("No necesitas crear otra cuenta", html)
        self.assertIn("mismo correo y contraseña", html)

    def test_password_reset_contains_cta_and_url(self):
        url = "https://frontend.test/restablecer/uid/token"
        EmailService.send_password_reset(self.user, url)

        self.assertIn("Crear nueva contraseña", self.html())
        self.assertIn(url, self.html())
        self.assertIn(url, mail.outbox[-1].body)

    def test_password_changed_contains_security_message_without_cta(self):
        EmailService.send_password_changed(self.user)

        html = self.html()
        self.assertIn("¿No reconoces este cambio?", html)
        self.assertIn("Contacta inmediatamente", html)
        self.assertNotIn("<a href=", html)
