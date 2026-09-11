from datetime import date

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import FactorAmbiental
from .models.material_factor_mapping import MaterialFactorMapping
from .permissions import Permission, require_tenant_permission
from .selectors.environmental_flows import organization_available_to_user
from .selectors.materials import material_for_organization
from .services.material_factor_mapping import (
    approve_material_mapping,
    propose_material_mapping,
    reject_material_mapping,
    revoke_material_mapping,
)
from .services.material_factor_selector import select_material_factor


def _organization(request, value):
    return organization_available_to_user(request.user, value)


def _validation_response(exc):
    if hasattr(exc, "message_dict"):
        return Response(exc.message_dict, status=400)
    return Response({"detail": exc.messages}, status=400)


def _mapping_data(mapping):
    return {
        "id": mapping.id,
        "organizacion_id": mapping.organizacion_id,
        "material_id": mapping.material_id,
        "material_codigo": mapping.material.codigo,
        "material_nombre": mapping.material.nombre,
        "factor_id": mapping.factor_id,
        "factor_codigo": mapping.factor.codigo,
        "factor_organizacion_id": mapping.factor.organizacion_id,
        "estado": mapping.estado,
        "vigencia_desde": mapping.vigencia_desde,
        "vigencia_hasta": mapping.vigencia_hasta,
        "contexto": mapping.contexto,
        "propuesto_por_id": mapping.propuesto_por_id,
        "revocado_por_id": mapping.revocado_por_id,
        "revocado_en": mapping.revocado_en,
        "reemplazado_por_id": mapping.reemplazado_por_id,
        "created_at": mapping.created_at,
        "updated_at": mapping.updated_at,
        "decisiones": [
            {
                "id": item.id,
                "decision": item.decision,
                "actor_id": item.actor_id,
                "timestamp": item.timestamp,
                "nota": item.nota,
                "contexto": item.contexto,
            }
            for item in mapping.decisiones.order_by("pk")
        ],
    }


def _mapping_or_404(organization, mapping_id):
    return get_object_or_404(
        MaterialFactorMapping.objects.select_related("material", "factor"),
        pk=mapping_id,
        organizacion=organization,
    )


@api_view(["GET", "POST"])
def material_factor_mappings(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    if request.method == "GET":
        require_tenant_permission(
            request.user, organization, Permission.MATERIAL_MAPPING_VIEW
        )
        rows = MaterialFactorMapping.objects.filter(
            organizacion=organization
        ).select_related("material", "factor")
        params = request.query_params
        if params.get("material"):
            rows = rows.filter(material_id=params["material"])
        if params.get("estado"):
            rows = rows.filter(estado=params["estado"])
        if params.get("factor"):
            rows = rows.filter(factor_id=params["factor"])
        if params.get("fecha"):
            fecha = parse_date(params["fecha"])
            if fecha:
                rows = rows.filter(vigencia_desde__lte=fecha).filter(
                    Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=fecha)
                )
        return Response([_mapping_data(item) for item in rows.order_by("pk")])

    material = get_object_or_404(
        material_for_organization(organization, request.data.get("material"))
    )
    factor = get_object_or_404(FactorAmbiental, pk=request.data.get("factor"))
    vigencia_desde = request.data.get("vigencia_desde")
    vigencia_hasta = request.data.get("vigencia_hasta") or None
    try:
        mapping = propose_material_mapping(
            organization,
            material,
            factor,
            vigencia_desde,
            vigencia_hasta,
            request.user,
            request.data.get("contexto"),
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_mapping_data(mapping), status=201)


@api_view(["GET"])
def material_factor_mapping_detail(request, organizacion_id, mapping_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    require_tenant_permission(
        request.user, organization, Permission.MATERIAL_MAPPING_VIEW
    )
    return Response(_mapping_data(_mapping_or_404(organization, mapping_id)))


@api_view(["POST"])
def material_factor_mapping_approve(request, organizacion_id, mapping_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    _mapping_or_404(organization, mapping_id)
    try:
        mapping = approve_material_mapping(
            mapping_id, organization, request.user, request.data.get("nota", "")
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_mapping_data(mapping))


@api_view(["POST"])
def material_factor_mapping_reject(request, organizacion_id, mapping_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    _mapping_or_404(organization, mapping_id)
    try:
        mapping = reject_material_mapping(
            mapping_id, organization, request.user, request.data.get("nota", "")
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_mapping_data(mapping))


@api_view(["POST"])
def material_factor_mapping_revoke(request, organizacion_id, mapping_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    _mapping_or_404(organization, mapping_id)
    replacement = None
    if request.data.get("reemplazado_por"):
        replacement = get_object_or_404(
            MaterialFactorMapping,
            pk=request.data["reemplazado_por"],
            organizacion=organization,
        )
    try:
        mapping = revoke_material_mapping(
            mapping_id,
            organization,
            request.user,
            request.data.get("nota", ""),
            replacement=replacement,
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_mapping_data(mapping))


@api_view(["GET"])
def material_calculation_eligibility(request, organizacion_id, material_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    require_tenant_permission(
        request.user, organization, Permission.MATERIAL_MAPPING_VIEW
    )
    material = get_object_or_404(
        material_for_organization(organization, material_id)
    )
    fecha = parse_date(request.query_params.get("fecha", "")) or date.today()
    input_unit = request.query_params.get("unidad") or material.unidad_base
    selection = select_material_factor(organization, material, input_unit, fecha)
    mapping = selection["mapping"]
    factor_version = selection["factor_version"]
    return Response(
        {
            "material": {
                "id": material.id,
                "codigo": material.codigo,
                "nombre": material.nombre,
            },
            "fecha_efectiva": fecha,
            "unidad_entrada": input_unit,
            "mapping_status": mapping.estado if mapping else None,
            "mapping": (
                {
                    "id": mapping.id,
                    "factor_id": mapping.factor_id,
                    "vigencia_desde": mapping.vigencia_desde,
                    "vigencia_hasta": mapping.vigencia_hasta,
                }
                if mapping
                else None
            ),
            "factor": (
                {"id": factor_version.factor_id, "codigo": factor_version.factor.codigo}
                if factor_version
                else None
            ),
            "version_factor": (
                {
                    "id": factor_version.id,
                    "version": factor_version.version,
                    "estado": factor_version.estado,
                    "valor": factor_version.valor,
                }
                if factor_version
                else None
            ),
            "unidad_resultado": (
                factor_version.factor.unidad_resultado if factor_version else None
            ),
            "calculable": selection["status"] == "calculable",
            "estado": selection["status"],
            "motivos": [selection["reason"]] if selection["reason"] else [],
            "provenance": (
                factor_version.factor.contexto if factor_version else None
            ),
        }
    )
