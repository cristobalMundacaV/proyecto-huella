import logging

import resend
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Controlled failure while delivering a transactional email."""


def _masked_recipient(email):
    local, separator, domain = str(email).partition("@")
    if not separator:
        return "***"
    domain_name, dot, suffix = domain.partition(".")
    return f"{local[:1]}***@{domain_name[:1]}***{dot}{suffix}"


def _render_button(label, url):
    if not label or not url:
        return ""
    return f"""<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:28px 0 8px"><tr><td bgcolor="#08745b" style="border-radius:10px"><a href="{escape(url)}" style="display:inline-block;min-height:44px;line-height:44px;padding:0 24px;color:#fff;font-size:15px;font-weight:700;text-decoration:none;border-radius:10px">{escape(label)}</a></td></tr></table>"""


def _render_info_box(title, body, items=None):
    if not title and not body:
        return ""
    rows = "".join(f'<li style="margin:0 0 7px;padding-left:2px">{escape(item)}</li>' for item in (items or []))
    item_list = f'<ul style="margin:14px 0 0;padding-left:20px">{rows}</ul>' if rows else ""
    return f"""<div style="margin:24px 0;padding:20px 22px;background:#f2f7f5;border:1px solid #d9e7e2;border-left:4px solid #08745b;border-radius:10px;color:#263b34"><div style="margin:0 0 7px;font-size:16px;font-weight:700;color:#0d2a24">{escape(title)}</div><div style="font-size:14px;line-height:1.65">{escape(body)}</div>{item_list}</div>"""


def _render_layout(title, subtitle, greeting, body, info_title=None, info_body=None, info_items=None, cta_label=None, cta_url=None, security_text=None):
    security = f'<p style="margin:22px 0 0;padding-top:20px;border-top:1px solid #e4e9e7;color:#61706b;font-size:13px;line-height:1.6">{escape(security_text)}</p>' if security_text else ""
    return f"""<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="margin:0;padding:0;background:#f1f4f3;color:#17211d;font-family:Arial,Helvetica,sans-serif"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" bgcolor="#f1f4f3"><tr><td align="center" style="padding:28px 12px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:620px;background:#fff;border:1px solid #dce4e1;border-radius:16px;overflow:hidden"><tr><td bgcolor="#0b2933" style="padding:30px 34px 32px"><div style="display:inline-block;margin-bottom:18px;padding:6px 10px;border:1px solid #4f746f;border-radius:999px;color:#bfe2d6;font-size:11px;font-weight:700;letter-spacing:1.3px">CARBONO ZERO</div><h1 style="margin:0;color:#fff;font-size:30px;line-height:1.2;font-weight:750">{escape(title)}</h1><p style="margin:12px 0 0;color:#d7e4e1;font-size:15px;line-height:1.55">{escape(subtitle)}</p></td></tr><tr><td style="padding:30px 34px 12px"><p style="margin:0 0 18px;font-size:16px;line-height:1.6">{escape(greeting)}</p><p style="margin:0;font-size:15px;line-height:1.7;color:#33463f">{escape(body)}</p>{_render_info_box(info_title, info_body, info_items)}{_render_button(cta_label, cta_url)}{security}</td></tr><tr><td style="padding:22px 34px 28px;color:#66736d;font-size:12px;line-height:1.6"><strong style="color:#08745b;font-size:14px">Carbono Zero</strong><br>Gestión ambiental continua<br>Mundaca’s Solutions<div style="margin-top:10px;color:#82908b">Este es un correo transaccional enviado por Carbono Zero.</div></td></tr></table></td></tr></table></body></html>"""


class EmailService:
    @staticmethod
    def _send(to, subject, title, greeting, body, cta_label=None, cta_url=None, email_type="transactional", subtitle="Información importante sobre tu cuenta de Carbono Zero.", info_title=None, info_body=None, info_items=None, security_text=None):
        html = _render_layout(title, subtitle, greeting, body, info_title, info_body, info_items, cta_label, cta_url, security_text)
        parts = [greeting, body, info_title, info_body]
        parts.extend(f"- {item}" for item in (info_items or []))
        if cta_label:
            parts.append(f"{cta_label}: {cta_url}")
        parts.extend([security_text, "Carbono Zero\nGestión ambiental continua\nMundaca’s Solutions"])
        plain = "\n\n".join(part for part in parts if part)
        api_key = getattr(settings, "RESEND_API_KEY", "")
        sender = settings.DEFAULT_FROM_EMAIL
        if api_key:
            try:
                resend.api_key = api_key
                return resend.Emails.send({"from": sender, "to": [to], "subject": subject, "html": html, "text": plain})
            except Exception as exc:
                logger.exception("Transactional email delivery failed provider=resend type=%s recipient=%s error_class=%s", email_type, _masked_recipient(to), type(exc).__name__)
                raise EmailDeliveryError("No fue posible entregar el correo transaccional.") from exc
        message = EmailMultiAlternatives(subject, plain, sender, [to])
        message.attach_alternative(html, "text/html")
        return message.send()

    @classmethod
    def send_account_activation(cls, user, organization, url):
        return cls._send(user.email, "Tu organización ya está disponible en Carbono Zero", "Tu espacio ya está disponible", f"Hola {user.first_name or user.username},", f"{organization.nombre} ya tiene habilitado su espacio en Carbono Zero. Has sido registrada como administradora inicial de la organización.", "Activar mi cuenta", url, "account_activation", subtitle="Completa tu acceso para comenzar a configurar la gestión ambiental de tu organización.", info_title="Tu siguiente paso", info_body="Activa tu cuenta, crea tu contraseña y completa la configuración inicial de tu organización.", info_items=["Identidad empresarial", "Estructura operacional", "Flujos ambientales", "Disponibilidad inicial de información", "Diagnóstico preliminar"], security_text="Este enlace es personal y temporal. Si no esperabas recibir este acceso, puedes ignorar este correo.")

    @classmethod
    def send_organization_invitation(cls, user, organization, url):
        return cls._send(user.email, "Tienes acceso a una nueva organización en Carbono Zero", "Nueva organización disponible", f"Hola {user.first_name or user.email},", f"Ahora tienes acceso a {organization.nombre} utilizando tu cuenta actual de Carbono Zero.", "Ir a Carbono Zero", url, "organization_invitation", subtitle="Tu cuenta fue vinculada a un nuevo espacio de trabajo.", info_title="No necesitas crear otra cuenta", info_body="Ingresa con el mismo correo y contraseña que ya utilizas.", security_text="Si no reconoces esta organización, contacta al administrador de tu cuenta.")

    @classmethod
    def send_password_reset(cls, user, url):
        return cls._send(user.email, "Restablece tu contraseña de Carbono Zero", "Restablece tu contraseña", f"Hola {user.first_name or user.username},", "Recibimos una solicitud para crear una nueva contraseña para tu cuenta de Carbono Zero.", "Crear nueva contraseña", url, "password_reset", subtitle="Recupera el acceso a tu cuenta de forma segura.", info_title="Seguridad de tu cuenta", info_body="Este enlace es temporal y solo puede utilizarse una vez.", security_text="Si no realizaste esta solicitud, puedes ignorar este correo.")

    @classmethod
    def send_password_changed(cls, user):
        return cls._send(user.email, "Tu contraseña de Carbono Zero fue actualizada", "Contraseña actualizada", f"Hola {user.first_name or user.username},", "La contraseña de tu cuenta de Carbono Zero fue modificada correctamente.", email_type="password_changed", subtitle="Confirmación de seguridad de tu cuenta.", info_title="¿No reconoces este cambio?", info_body="Contacta inmediatamente al administrador de tu organización o al soporte correspondiente.")
