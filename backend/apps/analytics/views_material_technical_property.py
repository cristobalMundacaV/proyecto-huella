from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import EvidenciaObra, FuenteDatos, VersionEvidencia
from .models.material_technical_property import MaterialTechnicalPropertyAssertion
from .permissions import Permission, require_tenant_permission
from .selectors.environmental_flows import organization_available_to_user
from .selectors.materials import material_for_organization
from .services.material_technical_property import approve_assertion, create_assertion, reject_assertion


def _organization(request, value):
    return organization_available_to_user(request.user, value)


def _validation_response(exc):
    if hasattr(exc, "message_dict"):
        return Response(exc.message_dict, status=400)
    return Response({"detail": exc.messages}, status=400)


def _assertion_data(assertion):
    return {
        "id": assertion.id,
        "organizacion_id": assertion.organizacion_id,
        "material_id": assertion.material_id,
        "property_key": assertion.property_key,
        "property_type": assertion.property_type,
        "value_numeric": assertion.value_numeric,
        "value_text": assertion.value_text,
        "value_boolean": assertion.value_boolean,
        "unit": assertion.unit,
        "provenance_type": assertion.provenance_type,
        "evidencia_id": assertion.evidencia_id,
        "version_evidencia_id": assertion.version_evidencia_id,
        "fuente_id": assertion.fuente_id,
        "rationale": assertion.rationale,
        "effective_date": assertion.effective_date,
        "estado": assertion.estado,
        "asserted_by_id": assertion.asserted_by_id,
        "reviewed_by_id": assertion.reviewed_by_id,
        "reviewed_at": assertion.reviewed_at,
        "created_at": assertion.created_at,
        "updated_at": assertion.updated_at,
    }


def _assertion_or_404(organization, assertion_id):
    return get_object_or_404(
        MaterialTechnicalPropertyAssertion, pk=assertion_id, organizacion=organization
    )


@api_view(["GET", "POST"])
def material_property_assertions(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    if request.method == "GET":
        require_tenant_permission(
            request.user, organization, Permission.MATERIAL_PROPERTY_ASSERTION_VIEW
        )
        rows = MaterialTechnicalPropertyAssertion.objects.filter(organizacion=organization)
        params = request.query_params
        if params.get("material"):
            rows = rows.filter(material_id=params["material"])
        if params.get("property_key"):
            rows = rows.filter(property_key=params["property_key"])
        if params.get("estado"):
            rows = rows.filter(estado=params["estado"])
        return Response([_assertion_data(item) for item in rows.order_by("pk")])

    material = get_object_or_404(
        material_for_organization(organization, request.data.get("material"))
    )
    evidencia = None
    if request.data.get("evidencia"):
        evidencia = get_object_or_404(
            EvidenciaObra, pk=request.data["evidencia"], organizacion=organization
        )
    version_evidencia = None
    if request.data.get("version_evidencia"):
        version_evidencia = get_object_or_404(
            VersionEvidencia, pk=request.data["version_evidencia"], organizacion=organization
        )
    fuente = None
    if request.data.get("fuente"):
        fuente = get_object_or_404(
            FuenteDatos, pk=request.data["fuente"], organizacion=organization
        )
    try:
        assertion = create_assertion(
            organization,
            request.user,
            material,
            request.data.get("property_key"),
            request.data.get("property_type"),
            request.data.get("provenance_type"),
            request.data.get("effective_date"),
            value_numeric=request.data.get("value_numeric"),
            value_text=request.data.get("value_text", ""),
            value_boolean=request.data.get("value_boolean"),
            unit=request.data.get("unit", ""),
            evidencia=evidencia,
            version_evidencia=version_evidencia,
            fuente=fuente,
            rationale=request.data.get("rationale", ""),
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_assertion_data(assertion), status=201)


@api_view(["GET"])
def material_property_assertion_detail(request, organizacion_id, assertion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    require_tenant_permission(
        request.user, organization, Permission.MATERIAL_PROPERTY_ASSERTION_VIEW
    )
    return Response(_assertion_data(_assertion_or_404(organization, assertion_id)))


@api_view(["POST"])
def material_property_assertion_approve(request, organizacion_id, assertion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    _assertion_or_404(organization, assertion_id)
    try:
        assertion = approve_assertion(assertion_id, organization, request.user, request.data.get("nota", ""))
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_assertion_data(assertion))


@api_view(["POST"])
def material_property_assertion_reject(request, organizacion_id, assertion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    _assertion_or_404(organization, assertion_id)
    try:
        assertion = reject_assertion(assertion_id, organization, request.user, request.data.get("nota", ""))
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_assertion_data(assertion))
