from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from django.shortcuts import get_object_or_404

from .models import AreaOperacional, EvidenciaObra, Organizacion, UsuarioOrganizacion
from .permissions import Permission, require_tenant_permission
from .selectors.operational_context import (
    areas_for_organization,
    recent_evidence_for_context,
    workspaces_for_membership,
    workspaces_for_user,
)
from .services.operational_context import (
    create_membership_workspace,
    create_operational_area,
    create_operational_evidence,
    resolve_operational_context,
    serialize_workspace,
)


@api_view(["GET"])
def operational_workspaces(request):
    workspaces = list(workspaces_for_user(request.user))
    return Response(
        {
            "workspaces": [serialize_workspace(item) for item in workspaces],
            "automatico": len(workspaces) == 1,
            "legacy": len(workspaces) == 0,
        }
    )


@api_view(["GET"])
def operational_context(request):
    context = resolve_operational_context(request)
    return Response(serialize_workspace(context.espacio))


@api_view(["GET", "POST"])
def organization_operational_areas(request, organizacion_id):
    organization = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    require_tenant_permission(
        request.user,
        organization,
        (
            Permission.SETTINGS_MANAGE
            if request.method == "POST"
            else Permission.SETTINGS_VIEW
        ),
    )
    if request.method == "GET":
        return Response(
            [
                {
                    "id": area.id,
                    "nombre": area.nombre,
                    "tipo": area.tipo,
                    "descripcion": area.descripcion,
                    "activa": area.activa,
                }
                for area in areas_for_organization(organization)
            ]
        )
    area = create_operational_area(
        organization=organization,
        name=request.data.get("nombre", ""),
        area_type=request.data.get("tipo", AreaOperacional.Tipo.OTRO),
        description=request.data.get("descripcion", ""),
    )
    return Response(
        {
            "id": area.id,
            "nombre": area.nombre,
            "tipo": area.tipo,
            "descripcion": area.descripcion,
            "activa": area.activa,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "POST"])
def membership_operational_workspaces(request, organizacion_id, user_id):
    organization = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    require_tenant_permission(
        request.user,
        organization,
        Permission.TEAM_MANAGE if request.method == "POST" else Permission.TEAM_VIEW,
    )
    membership = get_object_or_404(
        UsuarioOrganizacion, organizacion=organization, user_id=user_id
    )
    if request.method == "GET":
        return Response(
            [
                serialize_workspace(item)
                for item in workspaces_for_membership(membership)
            ]
        )
    area = get_object_or_404(
        AreaOperacional,
        pk=request.data.get("area_id"),
        organizacion=organization,
        activa=True,
    )
    obra_id = request.data.get("obra_id") or None
    workspace = create_membership_workspace(
        membership=membership,
        area=area,
        work_id=obra_id,
        name=request.data.get("nombre", ""),
    )
    return Response(serialize_workspace(workspace), status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_operational_information(request):
    permission = (
        Permission.EVIDENCE_CREATE
        if request.method == "POST"
        else Permission.EVIDENCE_VIEW
    )
    context = resolve_operational_context(request, permission)
    if request.method == "GET":
        evidence = recent_evidence_for_context(context, request.user)
        state_labels = {
            EvidenciaObra.EstadoDocumental.PENDIENTE: "En revisión",
            EvidenciaObra.EstadoDocumental.VALIDADA: "Procesado",
            EvidenciaObra.EstadoDocumental.OBSERVADA: "Necesita información",
            EvidenciaObra.EstadoDocumental.RECHAZADA: "Rechazado",
            EvidenciaObra.EstadoDocumental.SIN_VINCULO: "Recibido",
            EvidenciaObra.EstadoDocumental.VINCULADA: "Procesado",
        }
        return Response(
            [
                {
                    "id": item.id,
                    "nombre": item.nombre,
                    "estado": state_labels.get(item.estado_documental, "Recibido"),
                    "fecha": item.created_at,
                }
                for item in evidence
            ]
        )
    uploaded = request.FILES.get("archivo")
    if not uploaded:
        return Response(
            {"archivo": ["Selecciona un archivo para continuar."]},
            status=status.HTTP_400_BAD_REQUEST,
        )
    evidence = create_operational_evidence(
        context=context,
        uploaded_file=uploaded,
        name=request.data.get("nombre"),
    )
    return Response(
        {
            "id": evidence.id,
            "nombre": evidence.nombre,
            "estado": "recibido",
            "mensaje": "Archivo recibido correctamente.",
            "contexto": serialize_workspace(context.espacio),
        },
        status=status.HTTP_201_CREATED,
    )
