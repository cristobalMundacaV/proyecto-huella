import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from ..models import UsuarioOrganizacion
from .email_service import EmailService


def normalize_email_identity(email):
    return User.objects.normalize_email(str(email or "").strip()).casefold()


def find_user_by_email(email):
    normalized = normalize_email_identity(email)
    matches = User.objects.filter(email__iexact=normalized)
    if matches.count() > 1:
        raise ValidationError("Existen varias identidades con este correo. Contacta a soporte antes de continuar.")
    return matches.first()


def _internal_username():
    while True:
        value = f"usr_{uuid.uuid4().hex}"
        if not User.objects.filter(username=value).exists():
            return value


@transaction.atomic
def provision_user_membership(*, organization, email, role, first_name="", last_name="", cargo="", scope="organizacion", active=True, send_email=True):
    normalized = normalize_email_identity(email)
    validate_email(normalized)
    user = find_user_by_email(normalized)
    identity_created = user is None
    if identity_created:
        user = User(username=_internal_username(), email=normalized, first_name=first_name.strip(), last_name=last_name.strip(), is_active=False)
        user.set_unusable_password(); user.save()
    membership, membership_created = UsuarioOrganizacion.objects.get_or_create(user=user, organizacion=organization, defaults={"rol": role, "cargo": cargo.strip(), "alcance": scope, "activo": active})
    if not membership_created:
        membership.rol = role; membership.cargo = cargo.strip() or membership.cargo; membership.alcance = scope; membership.activo = active; membership.save()
    message_kind = "none"
    if send_email and not user.is_active:
        uid = urlsafe_base64_encode(force_bytes(user.pk)); token = default_token_generator.make_token(user)
        EmailService.send_account_activation(user, organization, f"{settings.FRONTEND_URL.rstrip('/')}/activar-cuenta/{uid}/{token}")
        message_kind = "activation"
    elif send_email and membership_created:
        EmailService.send_organization_invitation(user, organization, settings.FRONTEND_URL.rstrip("/"))
        message_kind = "invitation"
    return user, membership, {"identity_created": identity_created, "membership_created": membership_created, "message_kind": message_kind}
