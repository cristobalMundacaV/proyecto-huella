from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from django.shortcuts import get_object_or_404

from .models import AreaOperacional, EspacioTrabajoOperacional, EvidenciaObra, Organizacion, UsuarioOrganizacion
from .permissions import Permission
from .services.operational_context import resolve_operational_context, serialize_workspace, workspaces_for_user


@api_view(["GET"])
def operational_workspaces(request):
    workspaces = list(workspaces_for_user(request.user))
    return Response({
        "workspaces": [serialize_workspace(item) for item in workspaces],
        "automatico": len(workspaces) == 1,
        "legacy": len(workspaces) == 0,
    })


@api_view(["GET"])
def operational_context(request):
    context = resolve_operational_context(request)
    return Response(serialize_workspace(context.espacio))


@api_view(["GET", "POST"])
def organization_operational_areas(request, organizacion_id):
    organization = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    from .permissions import require_tenant_permission
    require_tenant_permission(request.user, organization, Permission.SETTINGS_MANAGE if request.method == "POST" else Permission.SETTINGS_VIEW)
    if request.method == "GET":
        return Response([{"id": area.id, "nombre": area.nombre, "tipo": area.tipo, "descripcion": area.descripcion, "activa": area.activa} for area in organization.areas_operacionales.all()])
    area = AreaOperacional(organizacion=organization, nombre=request.data.get("nombre", "").strip(), tipo=request.data.get("tipo", AreaOperacional.Tipo.OTRO), descripcion=request.data.get("descripcion", "").strip())
    area.full_clean()
    area.save()
    return Response({"id": area.id, "nombre": area.nombre, "tipo": area.tipo, "descripcion": area.descripcion, "activa": area.activa}, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def membership_operational_workspaces(request, organizacion_id, user_id):
    organization = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    from .permissions import require_tenant_permission
    require_tenant_permission(request.user, organization, Permission.TEAM_MANAGE if request.method == "POST" else Permission.TEAM_VIEW)
    membership = get_object_or_404(UsuarioOrganizacion, organizacion=organization, user_id=user_id)
    if request.method == "GET":
        return Response([serialize_workspace(item) for item in membership.espacios_trabajo.select_related("area", "obra", "usuario_organizacion__organizacion")])
    area = get_object_or_404(AreaOperacional, pk=request.data.get("area_id"), organizacion=organization, activa=True)
    obra_id = request.data.get("obra_id") or None
    workspace = EspacioTrabajoOperacional(usuario_organizacion=membership, area=area, obra_id=obra_id, nombre=request.data.get("nombre", "").strip())
    workspace.full_clean()
    workspace.save()
    return Response(serialize_workspace(workspace), status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_operational_information(request):
    permission = Permission.EVIDENCE_CREATE if request.method == "POST" else Permission.EVIDENCE_VIEW
    context = resolve_operational_context(request, permission)
    if request.method == "GET":
        evidence = EvidenciaObra.objects.filter(
            organizacion=context.organizacion, obra=context.obra, area_origen=context.area, usuario_origen=request.user
        ).order_by("-created_at")[:20]
        state_labels = {
            EvidenciaObra.EstadoDocumental.PENDIENTE: "En revisión",
            EvidenciaObra.EstadoDocumental.VALIDADA: "Procesado",
            EvidenciaObra.EstadoDocumental.OBSERVADA: "Necesita información",
            EvidenciaObra.EstadoDocumental.RECHAZADA: "Rechazado",
            EvidenciaObra.EstadoDocumental.SIN_VINCULO: "Recibido",
            EvidenciaObra.EstadoDocumental.VINCULADA: "Procesado",
        }
        return Response([{"id": item.id, "nombre": item.nombre, "estado": state_labels.get(item.estado_documental, "Recibido"), "fecha": item.created_at} for item in evidence])
    uploaded = request.FILES.get("archivo")
    if not uploaded:
        return Response({"archivo": ["Selecciona un archivo para continuar."]}, status=status.HTTP_400_BAD_REQUEST)
    evidence = EvidenciaObra.objects.create(
        organizacion=context.organizacion,
        obra=context.obra,
        area_origen=context.area,
        usuario_origen=context.usuario,
        metodo_captura="documento",
        archivo=uploaded,
        nombre=(request.data.get("nombre") or uploaded.name)[:240],
        tipo_evidencia=EvidenciaObra.TipoEvidencia.OTRO,
        metadata_extraccion={"workspace_id": context.espacio.id, "origen_operacional": True},
    )
    return Response({
        "id": evidence.id,
        "nombre": evidence.nombre,
        "estado": "recibido",
        "mensaje": "Archivo recibido correctamente.",
        "contexto": serialize_workspace(context.espacio),
    }, status=status.HTTP_201_CREATED)
