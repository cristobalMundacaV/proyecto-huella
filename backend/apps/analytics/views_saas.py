from datetime import timedelta
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DocumentoAmbiental, EventoAuditoriaSaaS, Obra, Observacion, Organizacion, ProblematicaAmbiental, SuscripcionSaaS, UsuarioOrganizacion


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
        "plan": item.plan, "estado": item.estado, "disponibilidad": item.disponibilidad,
        "inicio_plan": item.inicio_plan, "fin_piloto": item.fin_piloto, "proximo_vencimiento": item.proximo_vencimiento,
        "fecha_suspension": item.fecha_suspension, "fecha_cancelacion": item.fecha_cancelacion,
        "responsable_comercial": item.responsable_comercial, "limites": item.limites,
        "uso": {"usuarios": active_users, "obras": active_works, "documentos": documents, "problematicas_abiertas": open_problems},
        "ultima_actividad": activity, "salud": health(organization, item, activity),
    }


def audit(request, organization, action, before, after, detail=""):
    safe_before = json.loads(json.dumps(before, cls=DjangoJSONEncoder))
    safe_after = json.loads(json.dumps(after, cls=DjangoJSONEncoder))
    EventoAuditoriaSaaS.objects.create(organizacion=organization, actor=request.user, accion=action, detalle=detail, estado_anterior=safe_before, estado_nuevo=safe_after)


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


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def saas_organization_detail(request, organizacion_id):
    require_platform_admin(request)
    organization = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    item = subscription(organization)
    if request.method == "GET":
        return Response(serialize_organization(organization))
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
    if action == "iniciar_piloto" and item.estado != SuscripcionSaaS.Estado.CANCELADO:
        item.estado = SuscripcionSaaS.Estado.PILOTO; item.disponibilidad = SuscripcionSaaS.Disponibilidad.OPERATIVO
        item.inicio_plan = today; item.fin_piloto = today + timedelta(days=int(request.data.get("days", 30)))
    elif action == "activar" and item.estado != SuscripcionSaaS.Estado.CANCELADO:
        item.estado = SuscripcionSaaS.Estado.ACTIVO; item.disponibilidad = SuscripcionSaaS.Disponibilidad.OPERATIVO
        item.inicio_plan = item.inicio_plan or today; item.plan = request.data.get("plan") or item.plan
    elif action == "pago_pendiente" and item.estado in {SuscripcionSaaS.Estado.ACTIVO, SuscripcionSaaS.Estado.PILOTO}:
        item.estado = SuscripcionSaaS.Estado.PAGO_PENDIENTE
    elif action == "suspender" and item.estado != SuscripcionSaaS.Estado.CANCELADO:
        item.estado = SuscripcionSaaS.Estado.SUSPENDIDO; item.disponibilidad = SuscripcionSaaS.Disponibilidad.BLOQUEADO; item.fecha_suspension = now
    elif action == "reactivar" and item.estado in {SuscripcionSaaS.Estado.SUSPENDIDO, SuscripcionSaaS.Estado.PAGO_PENDIENTE}:
        item.estado = SuscripcionSaaS.Estado.ACTIVO; item.disponibilidad = SuscripcionSaaS.Disponibilidad.OPERATIVO; item.fecha_suspension = None
    elif action == "cancelar" and item.estado != SuscripcionSaaS.Estado.CANCELADO:
        item.estado = SuscripcionSaaS.Estado.CANCELADO; item.disponibilidad = SuscripcionSaaS.Disponibilidad.BLOQUEADO; item.fecha_cancelacion = now
    else:
        return Response({"detail": "La transición solicitada no es válida para el estado actual."}, status=status.HTTP_409_CONFLICT)
    item.full_clean(); item.save()
    after = serialize_organization(organization)
    audit(request, organization, action, before, after, request.data.get("detail", ""))
    return Response(after)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def saas_audit(request):
    require_platform_admin(request)
    rows = EventoAuditoriaSaaS.objects.select_related("organizacion", "actor")[:200]
    return Response([{"id": row.id, "organizacion": row.organizacion.nombre, "actor": row.actor.username, "accion": row.accion, "detalle": row.detalle, "estado_anterior": row.estado_anterior, "estado_nuevo": row.estado_nuevo, "created_at": row.created_at} for row in rows])
