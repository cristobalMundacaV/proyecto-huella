import json
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


class EmailService:
    @staticmethod
    def _send(to, subject, title, greeting, body, cta_label=None, cta_url=None):
        html = f"""<div style='font-family:Arial,sans-serif;max-width:620px;margin:auto;color:#17211d'>
        <div style='font-weight:800;color:#08745b;font-size:20px'>Carbono Zero</div><h1>{title}</h1>
        <p>{greeting}</p><p style='line-height:1.6'>{body}</p>
        {f"<p><a href='{cta_url}' style='display:inline-block;background:#08745b;color:white;padding:13px 20px;border-radius:10px;text-decoration:none;font-weight:bold'>{cta_label}</a></p>" if cta_url else ""}
        <p style='margin-top:32px;color:#66736d;font-size:13px'>Carbono Zero<br>Mundaca’s Solutions</p></div>"""
        api_key = getattr(settings, "RESEND_API_KEY", "")
        sender = settings.DEFAULT_FROM_EMAIL
        if api_key:
            request = Request("https://api.resend.com/emails", data=json.dumps({"from": sender, "to": [to], "subject": subject, "html": html}).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode())
        message = EmailMultiAlternatives(subject, f"{greeting}\n\n{body}\n\n{cta_url or ''}", sender, [to])
        message.attach_alternative(html, "text/html")
        return message.send()

    @classmethod
    def send_account_activation(cls, user, organization, url):
        return cls._send(user.email, "Tu organización ya está disponible en Carbono Zero", "Tu organización ya está disponible", f"Hola {user.first_name or user.username},", f"{organization.nombre} ya tiene habilitado su espacio en Carbono Zero. Has sido registrada como administradora inicial. Completa tu acceso y configura la estructura ambiental inicial de tu organización.", "Activar mi cuenta", url)

    @classmethod
    def send_password_reset(cls, user, url):
        return cls._send(user.email, "Restablece tu contraseña de Carbono Zero", "Restablece tu contraseña", f"Hola {user.first_name or user.username},", "Recibimos una solicitud para crear una nueva contraseña. Si no fuiste tú, puedes ignorar este mensaje.", "Crear nueva contraseña", url)

    @classmethod
    def send_password_changed(cls, user):
        return cls._send(user.email, "Tu contraseña de Carbono Zero fue actualizada", "Contraseña actualizada", f"Hola {user.first_name or user.username},", "Tu contraseña fue modificada correctamente. Si no reconoces este cambio, contacta al administrador de tu organización.")
