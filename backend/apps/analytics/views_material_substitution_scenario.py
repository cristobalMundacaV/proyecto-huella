from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import EventoMaterial
from .models.material_application_profile import MaterialApplicationProfile
from .models.material_substitution_scenario import MaterialSubstitutionScenario
from .permissions import Permission, require_tenant_permission
from .selectors.environmental_flows import organization_available_to_user
from .selectors.materials import material_for_organization
from .services.material_substitution_scenario import evaluate_scenario


def _organization(request, value):
    return organization_available_to_user(request.user, value)


def _scenario_data(item):
    return {
        "id": item.id,
        "organizacion_id": item.organizacion_id,
        "profile_id": item.profile_id,
        "profile_version": item.profile_version,
        "baseline_material_id": item.baseline_material_id,
        "alternative_material_id": item.alternative_material_id,
        "basis": item.basis,
        "reception_id": item.reception_id,
        "source_quantity_input": item.source_quantity_input,
        "source_quantity_unit": item.source_quantity_unit,
        "functional_units": item.functional_units,
        "baseline_quantity_per_functional_unit": item.baseline_quantity_per_functional_unit,
        "alternative_quantity_per_functional_unit": item.alternative_quantity_per_functional_unit,
        "alternative_quantity_equivalent": item.alternative_quantity_equivalent,
        "baseline_impact_per_functional_unit": item.baseline_impact_per_functional_unit,
        "alternative_impact_per_functional_unit": item.alternative_impact_per_functional_unit,
        "absolute_delta": item.absolute_delta,
        "relative_delta": item.relative_delta,
        "resultado": item.resultado,
        "not_comparable_reason": item.not_comparable_reason,
        "warnings": item.warnings,
        "created_by_id": item.created_by_id,
        "created_at": item.created_at,
    }


@api_view(["GET", "POST"])
def material_substitution_scenarios(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    if request.method == "GET":
        require_tenant_permission(request.user, organization, Permission.MATERIAL_APPLICATION_PROFILE_VIEW)
        rows = MaterialSubstitutionScenario.objects.filter(organizacion=organization)
        return Response([_scenario_data(item) for item in rows.order_by("-pk")])

    profile = get_object_or_404(
        MaterialApplicationProfile, pk=request.data.get("profile"), organizacion=organization
    )
    baseline = get_object_or_404(material_for_organization(organization, request.data.get("baseline_material")))
    alternative = get_object_or_404(
        material_for_organization(organization, request.data.get("alternative_material"))
    )
    reception = None
    if request.data.get("reception"):
        reception = get_object_or_404(
            EventoMaterial, pk=request.data["reception"], organizacion=organization
        )
    try:
        scenario = evaluate_scenario(
            organization, request.user, profile, baseline, alternative,
            basis=request.data.get("basis"),
            reception=reception,
            aggregate_quantity=request.data.get("aggregate_quantity"),
            aggregate_unit=request.data.get("aggregate_unit"),
        )
    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            return Response(exc.message_dict, status=400)
        return Response({"detail": exc.messages}, status=400)
    return Response(_scenario_data(scenario), status=201)


@api_view(["GET"])
def material_substitution_scenario_detail(request, organizacion_id, scenario_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    require_tenant_permission(request.user, organization, Permission.MATERIAL_APPLICATION_PROFILE_VIEW)
    item = get_object_or_404(MaterialSubstitutionScenario, pk=scenario_id, organizacion=organization)
    return Response(_scenario_data(item))
