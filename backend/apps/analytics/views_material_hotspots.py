from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .permissions import Permission, require_tenant_permission
from .selectors.environmental_flows import organization_available_to_user, work_for_organization
from .services.material_hotspots import material_hotspots


def _organization(request, value):
    return organization_available_to_user(request.user, value)


@api_view(["GET"])
def material_hotspots_view(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    require_tenant_permission(request.user, organization, Permission.MATERIAL_MAPPING_VIEW)
    params = request.query_params
    work = None
    if params.get("obra"):
        from django.shortcuts import get_object_or_404

        work = get_object_or_404(work_for_organization(organization, params["obra"]))
    start = parse_date(params["desde"]) if params.get("desde") else None
    end = parse_date(params["hasta"]) if params.get("hasta") else None
    result = material_hotspots(
        organization, work=work, start=start, end=end,
        categoria=params.get("categoria"), standard=params.get("standard"),
        group_by=params.get("agrupar_por"),
    )
    return Response(result)
