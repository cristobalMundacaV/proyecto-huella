from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .selectors.environmental_flows import organization_available_to_user
from .selectors.materials import event_for_organization, material_for_organization, work_for_organization
from .services.material_inventory import material_coverage_detail, material_environmental_coverage, reception_coverage


def _organization(request, value):
    return organization_available_to_user(request.user, value)


def _filters(request, organization):
    params = request.query_params
    work = None
    if params.get("obra"):
        work = get_object_or_404(work_for_organization(organization, params["obra"]))
    return {
        "work": work,
        "start": parse_date(params["desde"]) if params.get("desde") else None,
        "end": parse_date(params["hasta"]) if params.get("hasta") else None,
        "categoria": params.get("categoria") or None,
    }


@api_view(["GET"])
def coverage_summary(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    filters = _filters(request, organization)
    material = None
    if request.query_params.get("material"):
        material = get_object_or_404(
            material_for_organization(organization, request.query_params["material"])
        )
    return Response(
        material_environmental_coverage(organization, material=material, **filters)
    )


@api_view(["GET"])
def material_coverage(request, organizacion_id, material_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    material = get_object_or_404(material_for_organization(organization, material_id))
    filters = _filters(request, organization)
    filters.pop("categoria", None)
    return Response(material_coverage_detail(organization, material, **filters))


@api_view(["GET"])
def reception_coverage_detail(request, organizacion_id, event_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    event = get_object_or_404(event_for_organization(organization, event_id))
    if event.tipo != event.Tipo.RECEPCION:
        return Response(
            {"detail": "La cobertura ambiental sólo aplica a eventos de recepción."},
            status=400,
        )
    return Response(reception_coverage(event))
