from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models.material_application_profile import MaterialApplicationProfile
from .permissions import Permission, require_tenant_permission
from .selectors.environmental_flows import organization_available_to_user, work_for_organization
from .services.material_application_profile import (
    approve_profile,
    create_profile,
    create_revision,
    reject_profile,
    retire_profile,
    update_draft,
)


def _organization(request, value):
    return organization_available_to_user(request.user, value)


def _validation_response(exc):
    if hasattr(exc, "message_dict"):
        return Response(exc.message_dict, status=400)
    return Response({"detail": exc.messages}, status=400)


def _profile_data(profile):
    return {
        "id": profile.id,
        "organizacion_id": profile.organizacion_id,
        "obra_id": profile.obra_id,
        "codigo": profile.codigo,
        "nombre": profile.nombre,
        "descripcion": profile.descripcion,
        "cantidad_unidad_funcional": profile.cantidad_unidad_funcional,
        "unidad_funcional": profile.unidad_funcional,
        "requisitos": profile.requisitos,
        "estado": profile.estado,
        "version": profile.version,
        "reemplaza_a_id": profile.reemplaza_a_id,
        "created_by_id": profile.created_by_id,
        "reviewed_by_id": profile.reviewed_by_id,
        "reviewed_at": profile.reviewed_at,
        "retired_by_id": profile.retired_by_id,
        "retired_at": profile.retired_at,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "decisiones": [
            {
                "id": item.id,
                "decision": item.decision,
                "actor_id": item.actor_id,
                "timestamp": item.timestamp,
                "nota": item.nota,
                "contexto": item.contexto,
            }
            for item in profile.decisiones.order_by("pk")
        ],
    }


def _profile_or_404(organization, profile_id):
    return get_object_or_404(
        MaterialApplicationProfile.objects.select_related("obra"),
        pk=profile_id,
        organizacion=organization,
    )


@api_view(["GET", "POST"])
def material_application_profiles(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    if request.method == "GET":
        require_tenant_permission(
            request.user, organization, Permission.MATERIAL_APPLICATION_PROFILE_VIEW
        )
        rows = MaterialApplicationProfile.objects.filter(organizacion=organization)
        params = request.query_params
        if params.get("codigo"):
            rows = rows.filter(codigo=params["codigo"])
        if params.get("estado"):
            rows = rows.filter(estado=params["estado"])
        if params.get("obra"):
            rows = rows.filter(obra_id=params["obra"])
        return Response([_profile_data(item) for item in rows.order_by("pk")])

    obra = None
    if request.data.get("obra"):
        obra = get_object_or_404(
            work_for_organization(organization, request.data["obra"])
        )
    try:
        profile = create_profile(
            organization,
            request.user,
            request.data.get("codigo"),
            request.data.get("nombre"),
            request.data.get("cantidad_unidad_funcional"),
            request.data.get("unidad_funcional"),
            descripcion=request.data.get("descripcion", ""),
            requisitos=request.data.get("requisitos"),
            obra=obra,
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_profile_data(profile), status=201)


@api_view(["GET", "PATCH"])
def material_application_profile_detail(request, organizacion_id, profile_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    if request.method == "GET":
        require_tenant_permission(
            request.user, organization, Permission.MATERIAL_APPLICATION_PROFILE_VIEW
        )
        return Response(_profile_data(_profile_or_404(organization, profile_id)))

    _profile_or_404(organization, profile_id)
    try:
        profile = update_draft(
            profile_id,
            organization,
            request.user,
            nombre=request.data.get("nombre"),
            descripcion=request.data.get("descripcion"),
            cantidad_unidad_funcional=request.data.get("cantidad_unidad_funcional"),
            unidad_funcional=request.data.get("unidad_funcional"),
            requisitos=request.data.get("requisitos"),
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_profile_data(profile))


@api_view(["POST"])
def material_application_profile_approve(request, organizacion_id, profile_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    _profile_or_404(organization, profile_id)
    try:
        profile = approve_profile(profile_id, organization, request.user, request.data.get("nota", ""))
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_profile_data(profile))


@api_view(["POST"])
def material_application_profile_reject(request, organizacion_id, profile_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    _profile_or_404(organization, profile_id)
    try:
        profile = reject_profile(profile_id, organization, request.user, request.data.get("nota", ""))
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_profile_data(profile))


@api_view(["POST"])
def material_application_profile_retire(request, organizacion_id, profile_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    _profile_or_404(organization, profile_id)
    try:
        profile = retire_profile(profile_id, organization, request.user, request.data.get("nota", ""))
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_profile_data(profile))


@api_view(["POST"])
def material_application_profile_revise(request, organizacion_id, profile_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    _profile_or_404(organization, profile_id)
    try:
        revision = create_revision(profile_id, organization, request.user)
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_profile_data(revision), status=201)
