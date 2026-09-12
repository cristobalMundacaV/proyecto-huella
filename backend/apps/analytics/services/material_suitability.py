"""Deterministic suitability evaluation of a MaterialOperacional against one
approved MaterialApplicationProfile (MI-01C). Every requirement result is
exactly one of satisfied/failed/unknown; unknown never equals satisfied, and
a missing critical property forces requires_review rather than inventing a
value. Comparability/ranking/recommendation are explicitly out of scope
here — this module only answers "does this material meet this function's
explicit requirements," never "which material is better."
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models.material_application_profile import MaterialApplicationProfile
from ..models.material_functional_use import MaterialApplicationAssessment, functional_use_write
from ..models.material_technical_property import MaterialTechnicalPropertyAssertion
from ..permissions import Permission, require_tenant_permission
from .unit_conversion import UnitConversionError, convert_value

Estado = MaterialApplicationAssessment.Resultado


def _approved_assertions_by_key(organization, material):
    rows = MaterialTechnicalPropertyAssertion.objects.filter(
        organizacion=organization,
        material=material,
        estado=MaterialTechnicalPropertyAssertion.Estado.APROBADO,
    )
    return {row.property_key: row for row in rows}


def _numeric_with_unit(assertion, requirement_unit):
    value = assertion.value_numeric
    if requirement_unit and assertion.unit and requirement_unit != assertion.unit:
        try:
            converted = convert_value(value, assertion.unit, requirement_unit)
        except UnitConversionError:
            return None, True
        return converted["valor_normalizado"], False
    return value, False


def evaluate_requirement(requirement, assertion):
    key = requirement["key"]
    req_type = requirement["type"]
    critical = requirement.get("critical", True)

    if assertion is None:
        return {"key": key, "status": "unknown", "critical": critical, "detail": "Sin aserción aprobada."}

    if req_type == "numeric":
        if assertion.property_type != "numeric" or assertion.value_numeric is None:
            return {"key": key, "status": "unknown", "critical": critical, "detail": "Valor numérico no disponible."}
        operator = requirement["operator"]
        if operator == "range":
            value, incompatible = _numeric_with_unit(assertion, requirement.get("min_unit"))
            if incompatible:
                return {
                    "key": key, "status": "unknown", "critical": critical,
                    "detail": "Unidad incompatible entre la aserción y el requisito.",
                }
            min_value = Decimal(requirement["min"])
            max_value = Decimal(requirement["max"])
            satisfied = min_value <= value <= max_value
        else:
            value, incompatible = _numeric_with_unit(assertion, requirement.get("unit"))
            if incompatible:
                return {
                    "key": key, "status": "unknown", "critical": critical,
                    "detail": "Unidad incompatible entre la aserción y el requisito.",
                }
            threshold = Decimal(requirement["value"])
            if operator == "eq":
                satisfied = value == threshold
            elif operator == "gte":
                satisfied = value >= threshold
            else:  # lte
                satisfied = value <= threshold
        return {
            "key": key,
            "status": "satisfied" if satisfied else "failed",
            "critical": critical,
            "detail": f"Valor evaluado: {value}.",
        }

    if req_type == "categorical":
        if assertion.property_type != "categorical" or not assertion.value_text:
            return {"key": key, "status": "unknown", "critical": critical, "detail": "Valor categórico no disponible."}
        if requirement["operator"] == "equals":
            satisfied = assertion.value_text == requirement["value"]
        else:  # one_of
            satisfied = assertion.value_text in requirement["values"]
        return {
            "key": key,
            "status": "satisfied" if satisfied else "failed",
            "critical": critical,
            "detail": f"Valor evaluado: {assertion.value_text}.",
        }

    # boolean
    if assertion.property_type != "boolean" or assertion.value_boolean is None:
        return {"key": key, "status": "unknown", "critical": critical, "detail": "Valor booleano no disponible."}
    expected = requirement["operator"] == "is_true"
    satisfied = assertion.value_boolean == expected
    return {
        "key": key,
        "status": "satisfied" if satisfied else "failed",
        "critical": critical,
        "detail": f"Valor evaluado: {assertion.value_boolean}.",
    }


def evaluate_application(organization, material, profile):
    """Pure, on-read deterministic evaluation; does not persist anything."""

    if profile.estado != MaterialApplicationProfile.Estado.APROBADO:
        raise ValidationError("Sólo un perfil aprobado puede evaluarse.")
    if profile.organizacion_id != organization.id or material.organizacion_id != organization.id:
        raise ValidationError("El material y el perfil deben pertenecer a la misma organizacion.")

    assertions_by_key = _approved_assertions_by_key(organization, material)
    requirement_results = []
    missing_properties = []
    failed_requirements = []
    warnings = []
    assertion_ids_used = []

    for requirement in profile.requisitos:
        assertion = assertions_by_key.get(requirement["key"])
        outcome = evaluate_requirement(requirement, assertion)
        requirement_results.append(outcome)
        if outcome["status"] == "unknown":
            missing_properties.append(requirement["key"])
            if not outcome["critical"]:
                warnings.append(
                    f"Propiedad no crítica desconocida: {requirement['key']}."
                )
        elif outcome["status"] == "failed":
            failed_requirements.append(requirement["key"])
        if assertion is not None:
            assertion_ids_used.append(assertion.pk)

    if failed_requirements:
        result = Estado.NOT_SUITABLE
    elif any(
        item["status"] == "unknown" and item["critical"] for item in requirement_results
    ):
        result = Estado.REQUIRES_REVIEW
    else:
        result = Estado.SUITABLE_CANDIDATE

    return {
        "resultado": result,
        "requirement_results": requirement_results,
        "missing_properties": missing_properties,
        "failed_requirements": failed_requirements,
        "warnings": warnings,
        "assertion_ids_used": sorted(set(assertion_ids_used)),
    }


@transaction.atomic
def record_assessment(organization, user, material, profile):
    """Persist an immutable snapshot of evaluate_application()'s outcome so
    later property/profile changes never rewrite this historical result."""

    require_tenant_permission(user, organization, Permission.MATERIAL_APPLICATION_PROFILE_MANAGE)
    outcome = evaluate_application(organization, material, profile)
    token = functional_use_write.set(True)
    try:
        assessment = MaterialApplicationAssessment(
            organizacion=organization,
            material=material,
            profile=profile,
            resultado=outcome["resultado"],
            requirement_results=outcome["requirement_results"],
            missing_properties=outcome["missing_properties"],
            failed_requirements=outcome["failed_requirements"],
            warnings=outcome["warnings"],
            profile_version=profile.version,
            assertion_ids_used=outcome["assertion_ids_used"],
            evaluated_by=user,
        )
        assessment.save()
    finally:
        functional_use_write.reset(token)
    return assessment


@transaction.atomic
def decide_human_approval(assessment_id, organization, user, approved, note=""):
    """Human confirmation that a suitable_candidate result is approved for
    the application. Never allowed to override not_suitable/requires_review
    — those require new evidence or a profile revision, not an override."""

    require_tenant_permission(user, organization, Permission.MATERIAL_APPLICATION_PROFILE_APPROVE)
    assessment = MaterialApplicationAssessment.objects.select_for_update().get(
        pk=assessment_id, organizacion=organization
    )
    if assessment.resultado != Estado.SUITABLE_CANDIDATE:
        raise ValidationError(
            "Sólo un resultado suitable_candidate puede recibir una decisión humana."
        )
    if assessment.decision_humana != MaterialApplicationAssessment.DecisionHumana.PENDIENTE:
        raise ValidationError("Esta evaluación ya tiene una decisión humana registrada.")
    token = functional_use_write.set(True)
    try:
        assessment.decision_humana = (
            MaterialApplicationAssessment.DecisionHumana.APROBADO
            if approved
            else MaterialApplicationAssessment.DecisionHumana.RECHAZADO
        )
        assessment.decidido_por = user
        assessment.decidido_en = timezone.now()
        assessment.save()
    finally:
        functional_use_write.reset(token)
    return assessment
