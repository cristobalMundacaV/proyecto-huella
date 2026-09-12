from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import MaterialOperacional
from .models.material_application_profile import MaterialApplicationProfile
from .permissions import Permission, require_tenant_permission
from .selectors.environmental_flows import organization_available_to_user
from .selectors.materials import material_for_organization
from .services.material_comparable_sets import comparable_alternatives


def _organization(request, value):
    return organization_available_to_user(request.user, value)


@api_view(["GET"])
def material_comparable_alternatives(request, organizacion_id, material_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    require_tenant_permission(request.user, organization, Permission.MATERIAL_APPLICATION_PROFILE_VIEW)
    material = get_object_or_404(material_for_organization(organization, material_id))
    profile = get_object_or_404(
        MaterialApplicationProfile, pk=request.query_params.get("profile"), organizacion=organization
    )
    candidates = MaterialOperacional.objects.filter(organizacion=organization).exclude(pk=material.pk)
    result = comparable_alternatives(organization, material, profile, list(candidates))
    return Response(result)
