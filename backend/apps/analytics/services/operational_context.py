from dataclasses import dataclass

from django.http import Http404
from django.db import transaction
from rest_framework.exceptions import ValidationError

from ..models import (
    AreaOperacional,
    EspacioTrabajoOperacional,
    EvidenciaObra,
    UsuarioAreaOperacional,
)
from ..permissions import (
    ROLE_PERMISSIONS,
    require_tenant_permission,
    require_work_access,
)
from ..selectors.operational_context import workspaces_for_user


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


def serialize_workspace(workspace):
    membership = workspace.usuario_organizacion
    organization = membership.organizacion
    return {
        "id": workspace.id,
        "nombre": workspace.nombre or workspace.area.nombre,
        "area": {
            "id": workspace.area_id,
            "nombre": workspace.area.nombre,
            "tipo": workspace.area.tipo,
        },
        "organizacion": {
            "id": organization.organizacion_id,
            "nombre": organization.nombre,
        },
        "obra": (
            {
                "id": workspace.obra_id,
                "codigo": workspace.obra.codigo_obra,
                "nombre": workspace.obra.nombre,
            }
            if workspace.obra_id
            else None
        ),
        "rol": membership.rol,
        "permisos": sorted(ROLE_PERMISSIONS.get(membership.rol, ())),
    }


def requested_workspace_id(request):
    value = request.headers.get("X-Workspace-ID") or request.query_params.get(
        "workspace_id"
    )
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
        raise ValidationError(
            {
                "workspace_id": "Selecciona el espacio de trabajo en el que deseas continuar."
            }
        )

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


def create_operational_area(*, organization, name, area_type, description):
    area = AreaOperacional(
        organizacion=organization,
        nombre=name.strip(),
        tipo=area_type,
        descripcion=description.strip(),
    )
    area.full_clean()
    area.save()
    return area


def create_membership_workspace(*, membership, area, work_id, name):
    workspace = EspacioTrabajoOperacional(
        usuario_organizacion=membership,
        area=area,
        obra_id=work_id or None,
        nombre=name.strip(),
    )
    workspace.full_clean()
    workspace.save()
    return workspace


def create_operational_evidence(*, context, uploaded_file, name):
    return EvidenciaObra.objects.create(
        organizacion=context.organizacion,
        obra=context.obra,
        area_origen=context.area,
        usuario_origen=context.usuario,
        metodo_captura="documento",
        archivo=uploaded_file,
        nombre=(name or uploaded_file.name)[:240],
        tipo_evidencia=EvidenciaObra.TipoEvidencia.OTRO,
        metadata_extraccion={
            "workspace_id": context.espacio.id,
            "origen_operacional": True,
        },
    )


@transaction.atomic
def assign_user_to_operational_area(
    *,
    membership,
    area,
    cargo="",
    is_primary=False,
):
    # Serializa las asignaciones de una misma membresía para preservar una sola
    # área principal incluso ante solicitudes concurrentes.
    membership.__class__.objects.select_for_update().get(pk=membership.pk)

    if is_primary:
        UsuarioAreaOperacional.objects.filter(
            usuario_organizacion=membership,
            es_principal=True,
            activo=True,
        ).update(
            es_principal=False,
        )

    assignment, created = (
        UsuarioAreaOperacional.objects.get_or_create(
            usuario_organizacion=membership,
            area=area,
            defaults={
                "cargo": cargo.strip(),
                "es_principal": is_primary,
                "activo": True,
            },
        )
    )

    if not created:
        assignment.cargo = cargo.strip()
        assignment.es_principal = is_primary
        assignment.activo = True

    assignment.full_clean()
    assignment.save()

    return assignment
