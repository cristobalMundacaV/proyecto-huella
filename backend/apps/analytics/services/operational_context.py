from dataclasses import dataclass

from django.http import Http404
from rest_framework.exceptions import ValidationError

from ..models import EspacioTrabajoOperacional
from ..permissions import ROLE_PERMISSIONS, require_tenant_permission, require_work_access


@dataclass(frozen=True)
class ContextoOperativo:
    usuario: object
    organizacion: object
    membresia: object
    rol: str
    obra: object
    area: object
    permisos: frozenset
    espacio: object


def workspaces_for_user(user):
    if not user or not user.is_authenticated:
        return EspacioTrabajoOperacional.objects.none()
    return EspacioTrabajoOperacional.objects.select_related(
        "usuario_organizacion__organizacion", "area", "obra"
    ).filter(
        usuario_organizacion__user=user,
        usuario_organizacion__activo=True,
        area__activa=True,
        activo=True,
    )


def serialize_workspace(workspace):
    membership = workspace.usuario_organizacion
    organization = membership.organizacion
    return {
        "id": workspace.id,
        "nombre": workspace.nombre or workspace.area.nombre,
        "area": {"id": workspace.area_id, "nombre": workspace.area.nombre, "tipo": workspace.area.tipo},
        "organizacion": {"id": organization.organizacion_id, "nombre": organization.nombre},
        "obra": ({"id": workspace.obra_id, "codigo": workspace.obra.codigo_obra, "nombre": workspace.obra.nombre} if workspace.obra_id else None),
        "rol": membership.rol,
        "permisos": sorted(ROLE_PERMISSIONS.get(membership.rol, ())),
    }


def requested_workspace_id(request):
    value = request.headers.get("X-Workspace-ID") or request.query_params.get("workspace_id")
    if not value and hasattr(request, "data"):
        value = request.data.get("workspace_id")
    return value


def resolve_operational_context(request, permission=None, allow_automatic=True):
    queryset = workspaces_for_user(request.user)
    workspace_id = requested_workspace_id(request)
    if workspace_id:
        workspace = queryset.filter(pk=workspace_id).first()
        if not workspace:
            raise Http404("Espacio de trabajo no encontrado.")
    elif allow_automatic and queryset.count() == 1:
        workspace = queryset.first()
    else:
        raise ValidationError({"workspace_id": "Selecciona el espacio de trabajo en el que deseas continuar."})

    membership = workspace.usuario_organizacion
    organization = membership.organizacion
    require_work_access(request.user, organization, workspace.obra)
    if permission:
        require_tenant_permission(request.user, organization, permission)
    return ContextoOperativo(
        usuario=request.user,
        organizacion=organization,
        membresia=membership,
        rol=membership.rol,
        obra=workspace.obra,
        area=workspace.area,
        permisos=frozenset(ROLE_PERMISSIONS.get(membership.rol, ())),
        espacio=workspace,
    )
