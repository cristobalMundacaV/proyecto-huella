from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .permissions import Permission, require_tenant_permission
from .selectors.environmental_flows import organization_available_to_user, work_for_organization
from .selectors.materials import material_for_organization
from .services.environmental_agent import OpenAIEnvironmentalProvider
from .services.material_intelligence_copilot import MaterialIntelligenceCopilotService


def _organization(request, value):
    return organization_available_to_user(request.user, value)


@api_view(["POST"])
def material_intelligence_explain(request, organizacion_id, material_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    require_tenant_permission(request.user, organization, Permission.MATERIAL_APPLICATION_PROFILE_VIEW)
    material = get_object_or_404(material_for_organization(organization, material_id))
    work = None
    if request.data.get("obra"):
        work = get_object_or_404(work_for_organization(organization, request.data["obra"]))
    service = MaterialIntelligenceCopilotService(OpenAIEnvironmentalProvider())
    try:
        result = service.explain_material(
            material, organization, question=request.data.get("pregunta", ""), work=work,
        )
    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            return Response(exc.message_dict, status=400)
        return Response({"detail": exc.messages}, status=400)
    return Response(result)
