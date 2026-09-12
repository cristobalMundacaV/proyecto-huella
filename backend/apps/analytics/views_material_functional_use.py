from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import EvidenciaObra
from .models.material_application_profile import MaterialApplicationProfile
from .models.material_functional_use import MaterialApplicationAssessment, MaterialFunctionalUse
from .permissions import Permission, require_tenant_permission
from .selectors.environmental_flows import organization_available_to_user
from .selectors.materials import material_for_organization
from .services.material_functional_use import approve_functional_use, create_functional_use, reject_functional_use
from .services.material_suitability import decide_human_approval, record_assessment


def _organization(request, value):
    return organization_available_to_user(request.user, value)


def _validation_response(exc):
    if hasattr(exc, "message_dict"):
        return Response(exc.message_dict, status=400)
    return Response({"detail": exc.messages}, status=400)


def _functional_use_data(item):
    return {
        "id": item.id,
        "organizacion_id": item.organizacion_id,
        "material_id": item.material_id,
        "profile_id": item.profile_id,
        "cantidad_por_unidad_funcional": item.cantidad_por_unidad_funcional,
        "unidad": item.unidad,
        "rationale": item.rationale,
        "evidencia_id": item.evidencia_id,
        "estado": item.estado,
        "created_by_id": item.created_by_id,
        "reviewed_by_id": item.reviewed_by_id,
        "reviewed_at": item.reviewed_at,
    }


def _assessment_data(item):
    return {
        "id": item.id,
        "organizacion_id": item.organizacion_id,
        "material_id": item.material_id,
        "profile_id": item.profile_id,
        "resultado": item.resultado,
        "requirement_results": item.requirement_results,
        "missing_properties": item.missing_properties,
        "failed_requirements": item.failed_requirements,
        "warnings": item.warnings,
        "profile_version": item.profile_version,
        "assertion_ids_used": item.assertion_ids_used,
        "decision_humana": item.decision_humana,
        "decidido_por_id": item.decidido_por_id,
        "decidido_en": item.decidido_en,
        "evaluated_by_id": item.evaluated_by_id,
        "created_at": item.created_at,
    }


@api_view(["GET", "POST"])
def material_functional_uses(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    if request.method == "GET":
        require_tenant_permission(request.user, organization, Permission.MATERIAL_APPLICATION_PROFILE_VIEW)
        rows = MaterialFunctionalUse.objects.filter(organizacion=organization)
        if request.query_params.get("material"):
            rows = rows.filter(material_id=request.query_params["material"])
        if request.query_params.get("profile"):
            rows = rows.filter(profile_id=request.query_params["profile"])
        return Response([_functional_use_data(item) for item in rows.order_by("pk")])

    material = get_object_or_404(material_for_organization(organization, request.data.get("material")))
    profile = get_object_or_404(MaterialApplicationProfile, pk=request.data.get("profile"), organizacion=organization)
    evidencia = None
    if request.data.get("evidencia"):
        evidencia = get_object_or_404(EvidenciaObra, pk=request.data["evidencia"], organizacion=organization)
    try:
        functional_use = create_functional_use(
            organization, request.user, material, profile,
            request.data.get("cantidad_por_unidad_funcional"),
            request.data.get("unidad"),
            request.data.get("rationale", ""),
            evidencia=evidencia,
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_functional_use_data(functional_use), status=201)


@api_view(["POST"])
def material_functional_use_approve(request, organizacion_id, functional_use_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    get_object_or_404(MaterialFunctionalUse, pk=functional_use_id, organizacion=organization)
    try:
        item = approve_functional_use(functional_use_id, organization, request.user, request.data.get("nota", ""))
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_functional_use_data(item))


@api_view(["POST"])
def material_functional_use_reject(request, organizacion_id, functional_use_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    get_object_or_404(MaterialFunctionalUse, pk=functional_use_id, organizacion=organization)
    try:
        item = reject_functional_use(functional_use_id, organization, request.user, request.data.get("nota", ""))
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_functional_use_data(item))


@api_view(["POST"])
def material_application_assessments(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    material = get_object_or_404(material_for_organization(organization, request.data.get("material")))
    profile = get_object_or_404(MaterialApplicationProfile, pk=request.data.get("profile"), organizacion=organization)
    try:
        assessment = record_assessment(organization, request.user, material, profile)
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_assessment_data(assessment), status=201)


@api_view(["GET"])
def material_application_assessment_detail(request, organizacion_id, assessment_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    require_tenant_permission(request.user, organization, Permission.MATERIAL_APPLICATION_PROFILE_VIEW)
    item = get_object_or_404(MaterialApplicationAssessment, pk=assessment_id, organizacion=organization)
    return Response(_assessment_data(item))


@api_view(["POST"])
def material_application_assessment_decide(request, organizacion_id, assessment_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    get_object_or_404(MaterialApplicationAssessment, pk=assessment_id, organizacion=organization)
    try:
        item = decide_human_approval(
            assessment_id, organization, request.user,
            approved=bool(request.data.get("approved")),
            note=request.data.get("nota", ""),
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_assessment_data(item))
