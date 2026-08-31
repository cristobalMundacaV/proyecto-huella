from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import (
    AreaOperacional,
    EvidenciaObra,
    Organizacion,
    UsuarioAreaOperacional,
    UsuarioOrganizacion,
)
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
    assign_user_to_operational_area,
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


@api_view(["GET", "PATCH", "DELETE"])
def organization_operational_area_detail(
    request,
    organizacion_id,
    area_id,
):
    organization = get_object_or_404(
        Organizacion,
        organizacion_id=organizacion_id,
    )

    permission = (
        Permission.SETTINGS_VIEW
        if request.method == "GET"
        else Permission.SETTINGS_MANAGE
    )

    require_tenant_permission(
        request.user,
        organization,
        permission,
    )

    area = get_object_or_404(
        AreaOperacional,
        pk=area_id,
        organizacion=organization,
    )

    if request.method == "GET":
        return Response(
            {
                "id": area.id,
                "nombre": area.nombre,
                "tipo": area.tipo,
                "descripcion": area.descripcion,
                "activa": area.activa,
            }
        )

    if request.method == "PATCH":
        if "nombre" in request.data:
            area.nombre = request.data["nombre"].strip()

        if "tipo" in request.data:
            area.tipo = request.data["tipo"]

        if "descripcion" in request.data:
            area.descripcion = request.data["descripcion"].strip()

        if "activa" in request.data:
            area.activa = bool(request.data["activa"])

        area.full_clean()
        area.save()

        return Response(
            {
                "id": area.id,
                "nombre": area.nombre,
                "tipo": area.tipo,
                "descripcion": area.descripcion,
                "activa": area.activa,
            }
        )

    tiene_historial = area.usuarios_asignados.exists() or area.espacios_trabajo.exists()

    if tiene_historial:
        area.activa = False
        area.save(
            update_fields=[
                "activa",
                "updated_at",
            ]
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    area.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
def operational_area_users(
    request,
    organizacion_id,
    area_id,
):
    organization = get_object_or_404(
        Organizacion,
        organizacion_id=organizacion_id,
    )

    require_tenant_permission(
        request.user,
        organization,
        (Permission.TEAM_MANAGE if request.method == "POST" else Permission.TEAM_VIEW),
    )

    area = get_object_or_404(
        AreaOperacional,
        pk=area_id,
        organizacion=organization,
        activa=True,
    )

    if request.method == "GET":
        rows = UsuarioAreaOperacional.objects.filter(
            area=area,
            activo=True,
        ).select_related(
            "usuario_organizacion__user",
        )

        return Response(
            [
                {
                    "id": row.id,
                    "user_id": row.usuario_organizacion.user_id,
                    "nombre": row.usuario_organizacion.user.get_full_name()
                    or row.usuario_organizacion.user.username,
                    "email": row.usuario_organizacion.user.email,
                    "cargo": row.cargo,
                    "es_principal": row.es_principal,
                }
                for row in rows
            ]
        )

    user_id = request.data.get("user_id")

    membership = get_object_or_404(
        UsuarioOrganizacion,
        organizacion=organization,
        user_id=user_id,
    )

    assignment = assign_user_to_operational_area(
        membership=membership,
        area=area,
        cargo=request.data.get(
            "cargo",
            "",
        ),
        is_primary=bool(
            request.data.get(
                "es_principal",
                False,
            )
        ),
    )

    user = membership.user

    return Response(
        {
            "id": assignment.id,
            "user_id": user.id,
            "nombre": user.get_full_name() or user.username,
            "email": user.email,
            "cargo": assignment.cargo,
            "es_principal": assignment.es_principal,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
@transaction.atomic
def operational_area_user_detail(
    request,
    organizacion_id,
    area_id,
    assignment_id,
):
    organization = get_object_or_404(
        Organizacion,
        organizacion_id=organizacion_id,
    )

    require_tenant_permission(
        request.user,
        organization,
        Permission.TEAM_MANAGE,
    )

    assignment = get_object_or_404(
        UsuarioAreaOperacional.objects.select_for_update(),
        pk=assignment_id,
        area_id=area_id,
        area__organizacion=organization,
    )

    if request.method == "PATCH":
        if "cargo" in request.data:
            assignment.cargo = request.data["cargo"].strip()

        if "es_principal" in request.data:
            is_primary = bool(request.data["es_principal"])

            if is_primary:
                assignment.usuario_organizacion.__class__.objects.select_for_update().get(
                    pk=assignment.usuario_organizacion_id,
                )
                UsuarioAreaOperacional.objects.filter(
                    usuario_organizacion=assignment.usuario_organizacion,
                    es_principal=True,
                    activo=True,
                ).exclude(
                    pk=assignment.pk,
                ).update(
                    es_principal=False,
                )

            assignment.es_principal = is_primary

        assignment.full_clean()
        assignment.save()

        return Response(
            {
                "id": assignment.id,
                "cargo": assignment.cargo,
                "es_principal": assignment.es_principal,
            }
        )

    assignment.activo = False
    assignment.es_principal = False
    assignment.save(
        update_fields=[
            "activo",
            "es_principal",
            "updated_at",
        ]
    )

    return Response(status=status.HTTP_204_NO_CONTENT)


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
        from .services.evidence_documents import (
            current_document_result,
            current_evidence_version,
        )

        evidence = recent_evidence_for_context(context, request.user)
        state_labels = {
            "verificada": "Verificada",
            "compatible_incompleta": "Necesita información",
            "contradiccion": "Contradicción",
            "no_pertinente": "No pertinente",
            "indeterminada": "Indeterminada",
        }
        return Response(
            [
                {
                    "id": item.id,
                    "nombre": item.nombre,
                    "estado": (
                        "Procesando"
                        if getattr(
                            current_evidence_version(item),
                            "estado_procesamiento",
                            None,
                        )
                        in {"recibida", "analizando"}
                        else state_labels.get(
                            current_document_result(item).get("veredicto"),
                            "Indeterminada",
                        )
                    ),
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
