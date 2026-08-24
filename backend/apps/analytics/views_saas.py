from datetime import timedelta
import json

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ActividadOperacional, DocumentoAmbiental, EvidenciaObra, EventoAuditoriaSaaS, Obra, Observacion, Organizacion, ProblematicaAmbiental, ProcesoIngesta, RegistroEmision, SuscripcionSaaS, UsuarioOrganizacion
from .services.email_service import EmailService
from .services.identity import normalize_email_identity, provision_user_membership


def require_platform_admin(request):
    if not request.user.is_superuser:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Esta operación requiere administración global de plataforma.")


def subscription(organization):
    item, _ = SuscripcionSaaS.objects.get_or_create(
        organizacion=organization,
        defaults={"estado": SuscripcionSaaS.Estado.ACTIVO, "disponibilidad": SuscripcionSaaS.Disponibilidad.OPERATIVO},
    )
    return item


def latest_activity(organization):
    dates = [organization.updated_at]
    observation = Observacion.objects.filter(organizacion=organization).aggregate(value=Max("timestamp_observacion"))["value"]
    document = DocumentoAmbiental.objects.filter(organizacion=organization).aggregate(value=Max("created_at"))["value"]
    work = Obra.objects.filter(organizacion=organization).aggregate(value=Max("updated_at"))["value"]
    return max(value for value in [*dates, observation, document, work] if value)


def health(organization, item, activity):
    inactive_days = max(0, (timezone.now() - activity).days)
    if item.disponibilidad == SuscripcionSaaS.Disponibilidad.BLOQUEADO or item.estado in {SuscripcionSaaS.Estado.SUSPENDIDO, SuscripcionSaaS.Estado.CANCELADO}:
        return {"key": "critico", "label": "Crítico", "reason": "El acceso operativo está bloqueado."}
    if item.estado == SuscripcionSaaS.Estado.PAGO_PENDIENTE:
        return {"key": "riesgo", "label": "En riesgo", "reason": "La organización tiene un pago pendiente."}
    if inactive_days > 30:
        return {"key": "riesgo", "label": "En riesgo", "reason": f"Sin actividad observable hace {inactive_days} días."}
    if item.estado == SuscripcionSaaS.Estado.PILOTO and item.fin_piloto:
        remaining = (item.fin_piloto - timezone.localdate()).days
        if remaining <= 7:
            return {"key": "observacion", "label": "En observación", "reason": f"El piloto vence en {remaining} días." if remaining >= 0 else "El piloto está vencido."}
    if inactive_days > 14:
        return {"key": "observacion", "label": "En observación", "reason": f"Actividad reducida: {inactive_days} días sin cambios."}
    return {"key": "saludable", "label": "Saludable", "reason": "Uso reciente y acceso operativo normal."}


def deletion_status(organization):
    checks = {
        "obras": organization.obras.count(),
        "registros ambientales": RegistroEmision.objects.filter(organizacion=organization).count(),
        "observaciones": Observacion.objects.filter(organizacion=organization).count(),
        "actividades operacionales": ActividadOperacional.objects.filter(organizacion=organization).count(),
        "evidencias": EvidenciaObra.objects.filter(organizacion=organization).count(),
        "documentos": DocumentoAmbiental.objects.filter(organizacion=organization).count(),
        "importaciones": ProcesoIngesta.objects.filter(organizacion=organization).count(),
        "problemáticas": ProblematicaAmbiental.objects.filter(organizacion=organization).count(),
    }
    blockers = [{"tipo": label, "cantidad": count} for label, count in checks.items() if count]
    return {"permitida": not blockers, "bloqueos": blockers}


def serialize_admins(organization):
    return [{"membership_id": membership.id, "user_id": membership.user_id, "nombre": membership.user.get_full_name().strip() or membership.user.username, "email": membership.user.email, "cargo": membership.cargo, "activo": membership.activo and membership.user.is_active, "cuenta_activada": membership.user.is_active and membership.user.has_usable_password(), "ultimo_acceso": membership.user.last_login} for membership in organization.usuarios.filter(rol=UsuarioOrganizacion.Rol.ADMIN).select_related("user")]


def serialize_organization(organization):
    item = subscription(organization)
    activity = latest_activity(organization)
    active_works = organization.obras.filter(estado=Obra.Estado.EN_EJECUCION).count()
    active_users = organization.usuarios.filter(activo=True, user__is_active=True).count()
    documents = DocumentoAmbiental.objects.filter(organizacion=organization).count()
    open_problems = ProblematicaAmbiental.objects.filter(organizacion=organization).exclude(estado__in=["cerrada", "resuelta"]).count()
    return {
        "id": organization.id, "organizacion_id": organization.organizacion_id, "nombre": organization.nombre,
        "rut": organization.rut, "rubro": organization.rubro, "preset": organization.preset,
        "email": organization.email, "telefono": organization.telefono, "direccion": organization.direccion,
        "region": organization.region, "comuna": organization.comuna, "contacto": organization.contacto,
        "onboarding_step": organization.onboarding_step, "onboarding_completado": organization.onboarding_completado,
        "plan": item.plan, "estado": item.estado, "disponibilidad": item.disponibilidad,
        "inicio_plan": item.inicio_plan, "fin_piloto": item.fin_piloto, "proximo_vencimiento": item.proximo_vencimiento,
        "fecha_suspension": item.fecha_suspension, "fecha_cancelacion": item.fecha_cancelacion,
        "responsable_comercial": item.responsable_comercial, "limites": item.limites,
        "uso": {"usuarios": active_users, "obras": active_works, "documentos": documents, "problematicas_abiertas": open_problems},
        "administradores": serialize_admins(organization), "eliminacion": deletion_status(organization),
        "ultima_actividad": activity, "salud": health(organization, item, activity),
    }


def audit(request, organization, action, before, after, detail=""):
    safe_before = json.loads(json.dumps(before, cls=DjangoJSONEncoder))
    safe_after = json.loads(json.dumps(after, cls=DjangoJSONEncoder))
    EventoAuditoriaSaaS.objects.create(organizacion=organization, actor=request.user, accion=action, detalle=detail, estado_anterior=safe_before, estado_nuevo=safe_after)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def saas_provision_organization(request):
    require_platform_admin(request)
    required = ["nombre", "sector", "plan", "estado", "admin_nombre", "admin_apellido", "admin_email"]
    missing = [field for field in required if not str(request.data.get(field, "")).strip()]
    if missing:
        return Response({field: ["Este dato es necesario."] for field in missing}, status=status.HTTP_400_BAD_REQUEST)
    email = normalize_email_identity(request.data["admin_email"])
    if request.data["sector"] not in Organizacion.Preset.values: return Response({"sector": ["Selecciona un sector disponible."]}, status=status.HTTP_400_BAD_REQUEST)
    if request.data["plan"] not in SuscripcionSaaS.Plan.values: return Response({"plan": ["Selecciona un plan disponible."]}, status=status.HTTP_400_BAD_REQUEST)
    if request.data["estado"] not in {SuscripcionSaaS.Estado.PILOTO, SuscripcionSaaS.Estado.ACTIVO}: return Response({"estado": ["El estado inicial debe ser Piloto o Activo."]}, status=status.HTTP_400_BAD_REQUEST)
    organization = Organizacion.objects.create(nombre=request.data["nombre"].strip(), preset=request.data["sector"], onboarding_step=1)
    subscription_item = SuscripcionSaaS.objects.create(organizacion=organization, plan=request.data["plan"], estado=request.data["estado"], disponibilidad=SuscripcionSaaS.Disponibilidad.OPERATIVO)
    admin_user, _, identity = provision_user_membership(organization=organization, email=email, role=UsuarioOrganizacion.Rol.ADMIN, first_name=request.data["admin_nombre"], last_name=request.data["admin_apellido"], cargo=request.data.get("admin_cargo", ""))
    audit(request, organization, "alta_saas", {}, {"plan": subscription_item.plan, "estado": subscription_item.estado, "administrador": email}, "Tenant y administrador inicial provisionados.")
    return Response({"organizacion_id": organization.organizacion_id, "nombre": organization.nombre, "plan": subscription_item.plan, "estado": subscription_item.estado, "administrador": email, "identidad_nueva": identity["identity_created"], "mensaje_enviado": identity["message_kind"]}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def saas_dashboard(request):
    require_platform_admin(request)
    rows = [serialize_organization(item) for item in Organizacion.objects.all()]
    attention = [row for row in rows if row["salud"]["key"] != "saludable"]
    return Response({
        "organizations": rows,
        "kpis": {"total": len(rows), "operativas": sum(row["disponibilidad"] == "operativo" for row in rows), "pilotos": sum(row["estado"] == "piloto" for row in rows), "requieren_gestion": len(attention), "usuarios_activos": sum(row["uso"]["usuarios"] for row in rows), "obras_activas": sum(row["uso"]["obras"] for row in rows)},
        "attention": sorted(attention, key=lambda row: ({"critico": 0, "riesgo": 1, "observacion": 2}.get(row["salud"]["key"], 3), row["nombre"])),
    })


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def saas_organization_detail(request, organizacion_id):
    require_platform_admin(request)
    organization = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    item = subscription(organization)
    if request.method == "GET":
        return Response(serialize_organization(organization))
    if request.method == "DELETE":
        deletion = deletion_status(organization)
        if not deletion["permitida"]:
            summary = ", ".join(f"{row['cantidad']} {row['tipo']}" for row in deletion["bloqueos"])
            return Response({"detail": f"No puedes eliminar esta organización porque contiene datos operacionales: {summary}.", "bloqueos": deletion["bloqueos"]}, status=status.HTTP_409_CONFLICT)
        orphan_ids = list(organization.usuarios.values_list("user_id", flat=True))
        name = organization.nombre
        organization.delete()
        User.objects.filter(id__in=orphan_ids, organizaciones_perfil__isnull=True, is_active=False).delete()
        return Response({"detail": f"La organización {name} fue eliminada definitivamente."})
    before = serialize_organization(organization)
    allowed_org = {"nombre", "rut", "rubro", "preset", "email", "telefono", "direccion", "region", "comuna", "contacto"}
    allowed_subscription = {"plan", "inicio_plan", "fin_piloto", "proximo_vencimiento", "responsable_comercial", "limites"}
    for field in allowed_org.intersection(request.data):
        setattr(organization, field, request.data[field])
    for field in allowed_subscription.intersection(request.data):
        setattr(item, field, request.data[field])
    organization.full_clean(); item.full_clean(); organization.save(); item.save()
    after = serialize_organization(organization)
    audit(request, organization, "actualizacion_comercial", before, after, "Se actualizó la configuración SaaS.")
    return Response(after)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def saas_organization_action(request, organizacion_id):
    require_platform_admin(request)
    organization = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    item = subscription(organization)
    action = request.data.get("action")
    before = serialize_organization(organization)
    now = timezone.now(); today = timezone.localdate()
    if action == "iniciar_piloto":
        item.estado = SuscripcionSaaS.Estado.PILOTO; item.disponibilidad = SuscripcionSaaS.Disponibilidad.OPERATIVO
        item.inicio_plan = today; item.fin_piloto = today + timedelta(days=int(request.data.get("days", 30)))
    elif action == "activar":
        item.estado = SuscripcionSaaS.Estado.ACTIVO; item.disponibilidad = SuscripcionSaaS.Disponibilidad.OPERATIVO
        item.inicio_plan = item.inicio_plan or today; item.plan = request.data.get("plan") or item.plan
    elif action == "pago_pendiente" and item.estado in {SuscripcionSaaS.Estado.ACTIVO, SuscripcionSaaS.Estado.PILOTO}:
        item.estado = SuscripcionSaaS.Estado.PAGO_PENDIENTE
    elif action == "suspender" and item.estado != SuscripcionSaaS.Estado.CANCELADO:
        item.estado = SuscripcionSaaS.Estado.SUSPENDIDO; item.disponibilidad = SuscripcionSaaS.Disponibilidad.BLOQUEADO; item.fecha_suspension = now
    elif action == "reactivar" and item.estado in {SuscripcionSaaS.Estado.SUSPENDIDO, SuscripcionSaaS.Estado.PAGO_PENDIENTE, SuscripcionSaaS.Estado.CANCELADO}:
        item.estado = SuscripcionSaaS.Estado.ACTIVO; item.disponibilidad = SuscripcionSaaS.Disponibilidad.OPERATIVO; item.fecha_suspension = None
        item.fecha_cancelacion = None
    elif action == "cancelar" and item.estado != SuscripcionSaaS.Estado.CANCELADO:
        item.estado = SuscripcionSaaS.Estado.CANCELADO; item.disponibilidad = SuscripcionSaaS.Disponibilidad.BLOQUEADO; item.fecha_cancelacion = now
    else:
        return Response({"detail": "La transición solicitada no es válida para el estado actual."}, status=status.HTTP_409_CONFLICT)
    item.full_clean(); item.save()
    after = serialize_organization(organization)
    audit(request, organization, action, before, after, request.data.get("detail", ""))
    return Response(after)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def saas_organization_admins(request, organizacion_id):
    require_platform_admin(request)
    organization = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    email = str(request.data.get("email", "")).strip().lower()
    first_name = str(request.data.get("nombre", "")).strip(); last_name = str(request.data.get("apellido", "")).strip()
    if not email or "@" not in email: return Response({"email": ["Ingresa un correo electrónico válido."]}, status=status.HTTP_400_BAD_REQUEST)
    user, membership, identity = provision_user_membership(organization=organization, email=email, role=UsuarioOrganizacion.Rol.ADMIN, first_name=first_name, last_name=last_name, cargo=request.data.get("cargo", ""))
    audit(request, organization, "administrador_asignado", {}, {"email": email, "usuario_existente": not identity["identity_created"]}, "Se asignó o recuperó un administrador para el tenant.")
    return Response({"detail": "Administrador asignado correctamente. Se envió la comunicación correspondiente.", "administradores": serialize_admins(organization), "mensaje_enviado": identity["message_kind"]}, status=status.HTTP_201_CREATED if identity["membership_created"] else status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def saas_audit(request):
    require_platform_admin(request)
    rows = EventoAuditoriaSaaS.objects.select_related("organizacion", "actor")[:200]
    return Response([{"id": row.id, "organizacion": row.organizacion.nombre, "actor": row.actor.username, "accion": row.accion, "detalle": row.detalle, "estado_anterior": row.estado_anterior, "estado_nuevo": row.estado_nuevo, "created_at": row.created_at} for row in rows])
