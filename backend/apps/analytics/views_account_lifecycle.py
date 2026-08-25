from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import AreaOperacional, UsuarioOrganizacion
from .services.email_service import EmailService
from .services.onboarding import AREA_FLOW_SUGGESTIONS, FLOW_CATALOG, apply_onboarding_step, area_catalog_for


def _token_user(uid):
    try: return User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError): return None


@api_view(["POST"])
@permission_classes([AllowAny])
@transaction.atomic
def activate_account(request, uid, token):
    user = _token_user(uid)
    if not user or user.is_active or not default_token_generator.check_token(user, token): return Response({"detail": "El enlace ya no es válido. Solicita uno nuevo al administrador."}, status=status.HTTP_400_BAD_REQUEST)
    password = request.data.get("password", ""); confirmation = request.data.get("confirmation", "")
    if password != confirmation: return Response({"confirmation": ["Las contraseñas no coinciden."]}, status=status.HTTP_400_BAD_REQUEST)
    try: validate_password(password, user)
    except DjangoValidationError as error: return Response({"password": list(error.messages)}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(password); user.is_active = True; user.save(update_fields=["password", "is_active"])
    return Response({"detail": "Cuenta activada correctamente."})


@api_view(["POST"])
@permission_classes([AllowAny])
def request_password_reset(request):
    email = str(request.data.get("email", "")).strip().lower(); user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk)); token = default_token_generator.make_token(user)
        try: EmailService.send_password_reset(user, f"{settings.FRONTEND_URL.rstrip('/')}/restablecer-contrasena/{uid}/{token}")
        except Exception: pass
    return Response({"detail": "Si existe una cuenta asociada a ese correo, recibirás instrucciones para restablecer tu contraseña."})


@api_view(["POST"])
@permission_classes([AllowAny])
@transaction.atomic
def confirm_password_reset(request, uid, token):
    user = _token_user(uid)
    if not user or not default_token_generator.check_token(user, token): return Response({"detail": "El enlace ya no es válido."}, status=status.HTTP_400_BAD_REQUEST)
    password = request.data.get("password", ""); confirmation = request.data.get("confirmation", "")
    if password != confirmation: return Response({"confirmation": ["Las contraseñas no coinciden."]}, status=status.HTTP_400_BAD_REQUEST)
    try: validate_password(password, user)
    except DjangoValidationError as error: return Response({"password": list(error.messages)}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(password); user.save(update_fields=["password"]); EmailService.send_password_changed(user)
    return Response({"detail": "Contraseña actualizada correctamente."})


@api_view(["POST"])
@transaction.atomic
def change_password(request):
    user = request.user
    if not user.check_password(request.data.get("current_password", "")):
        return Response({"current_password": ["La contraseña actual no es correcta."]}, status=status.HTTP_400_BAD_REQUEST)
    password = request.data.get("password", ""); confirmation = request.data.get("confirmation", "")
    if password != confirmation: return Response({"confirmation": ["Las contraseñas no coinciden."]}, status=status.HTTP_400_BAD_REQUEST)
    try: validate_password(password, user)
    except DjangoValidationError as error: return Response({"password": list(error.messages)}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(password); user.save(update_fields=["password"]); update_session_auth_hash(request, user); EmailService.send_password_changed(user)
    return Response({"detail": "Contraseña actualizada correctamente."})


def _onboarding_membership(request):
    organization_id = request.headers.get("X-Organization-ID") or request.data.get("organizacion_id") or request.query_params.get("organizacion_id")
    queryset = UsuarioOrganizacion.objects.select_related("organizacion").filter(user=request.user, activo=True, rol=UsuarioOrganizacion.Rol.ADMIN)
    return get_object_or_404(queryset, organizacion__organizacion_id=organization_id) if organization_id else get_object_or_404(queryset, organizacion__onboarding_completado=False)


def _payload(organization):
    areas = [{"id": row.id, "tipo": row.tipo, "nombre": row.nombre, "activa": row.activa} for row in organization.areas_operacionales.all()]
    flows = [{"clave": row.capacidad.clave, "nombre": row.capacidad.nombre, "estado": row.estado, "disponibilidad": row.disponibilidad_inicial} for row in organization.capacidades_ambientales.select_related("capacidad").exclude(estado="no_aplica")]
    identity = {field: getattr(organization, field) for field in ("nombre", "nombre_comercial", "rut", "rubro", "pais", "region", "comuna", "direccion", "email", "telefono", "contacto")}; identity["sector"] = organization.preset; identity["id"] = organization.organizacion_id
    relations = {area.tipo: list(area.flujos_asociados.values_list("capacidad_organizacion__capacidad__clave", flat=True)) for area in organization.areas_operacionales.filter(activa=True)}
    return {"organizacion": identity, "step": organization.onboarding_step, "completado": organization.onboarding_completado, "data": organization.onboarding_data, "areas": areas, "flujos": flows, "relaciones": relations, "catalogos": {"areas": area_catalog_for(organization.preset), "flujos": [{"clave": key, "nombre": value[0], "descripcion": value[1]} for key, value in FLOW_CATALOG.items()], "sugerencias": AREA_FLOW_SUGGESTIONS}}


@api_view(["GET", "PATCH"])
def onboarding(request):
    membership = _onboarding_membership(request); organization = membership.organizacion
    if request.method == "GET": return Response(_payload(organization))
    step = int(request.data.get("step", organization.onboarding_step)); payload = request.data.get("data", {})
    if step > organization.onboarding_step: return Response({"detail": "Completa la etapa actual antes de continuar."}, status=status.HTTP_409_CONFLICT)
    try: apply_onboarding_step(organization, request.user, step, payload)
    except (ValueError, DjangoValidationError) as error: return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(_payload(organization))
