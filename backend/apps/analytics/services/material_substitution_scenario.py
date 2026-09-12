"""Substitution scenario engine (MI-01G): a hypothetical, read-only
evaluation of "what if this material were replaced by this approved
comparable alternative." Never writes EventoMaterial, the ledger, a
mapping, or any approval — evaluating a scenario is the only action, and it
only ever produces an immutable audit snapshot. Output never claims
"safe/approved/recommended for construction" — only an environmental
scenario result.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models.material_substitution_scenario import MaterialSubstitutionScenario
from ..permissions import Permission, require_tenant_permission
from .material_environmental_comparison import compare_materials
from .material_functional_use import approved_functional_use
from .unit_conversion import UnitConversionError, convert_value

Resultado = MaterialSubstitutionScenario.Resultado
Basis = MaterialSubstitutionScenario.Basis
# Matches functional_units/alternative_quantity_equivalent's DecimalField
# precision (decimal_places=6) — Decimal division/multiplication never
# auto-rounds, so this must be quantized explicitly before persistence.
QUANTITY_QUANTUM = Decimal("0.000001")


def _not_comparable(base_fields, reason):
    return MaterialSubstitutionScenario.objects.create(
        **base_fields, resultado=Resultado.NOT_COMPARABLE, not_comparable_reason=reason,
    )


@transaction.atomic
def evaluate_scenario(
    organization, user, profile, baseline_material, alternative_material, *,
    basis, reception=None, aggregate_quantity=None, aggregate_unit=None,
):
    require_tenant_permission(user, organization, Permission.MATERIAL_APPLICATION_PROFILE_VIEW)

    if basis == Basis.RECEPTION:
        if reception is None or reception.organizacion_id != organization.id:
            raise ValidationError({"reception": "La recepción debe pertenecer a la misma organizacion."})
        if reception.material_id != baseline_material.id:
            raise ValidationError({"reception": "La recepción no corresponde al material base."})
        source_quantity_input = reception.observacion_cantidad.valor_numerico
        source_quantity_unit = reception.observacion_cantidad.unidad
    elif basis == Basis.AGGREGATE_QUANTITY:
        if aggregate_quantity is None or not aggregate_unit:
            raise ValidationError("Se requiere cantidad y unidad para basis=aggregate_quantity.")
        source_quantity_input = Decimal(str(aggregate_quantity))
        source_quantity_unit = aggregate_unit
    else:
        raise ValidationError({"basis": "Basis inválido."})

    base_fields = dict(
        organizacion=organization,
        profile=profile,
        profile_version=profile.version,
        baseline_material=baseline_material,
        alternative_material=alternative_material,
        basis=basis,
        reception=reception if basis == Basis.RECEPTION else None,
        source_quantity_input=source_quantity_input,
        source_quantity_unit=source_quantity_unit,
        created_by=user,
    )

    comparison = compare_materials(
        organization, baseline_material, alternative_material, profile, effective_date=timezone.now().date(),
    )
    if not comparison["comparable"]:
        return _not_comparable(base_fields, comparison["reason"])

    baseline_use = approved_functional_use(organization, baseline_material, profile)
    alt_use = approved_functional_use(organization, alternative_material, profile)

    try:
        normalized_source = convert_value(
            source_quantity_input, source_quantity_unit, baseline_use.unidad
        )["valor_normalizado"]
    except UnitConversionError:
        return _not_comparable(base_fields, "source_unit_incompatible")

    functional_units = (
        normalized_source / baseline_use.cantidad_por_unidad_funcional
    ).quantize(QUANTITY_QUANTUM)
    alternative_quantity_equivalent = (
        functional_units * alt_use.cantidad_por_unidad_funcional
    ).quantize(QUANTITY_QUANTUM)

    absolute_delta = comparison["absolute_delta"]
    if absolute_delta < 0:
        resultado = Resultado.LOWER_IMPACT
    elif absolute_delta > 0:
        resultado = Resultado.HIGHER_IMPACT
    else:
        resultado = Resultado.EQUAL_IMPACT

    return MaterialSubstitutionScenario.objects.create(
        **base_fields,
        functional_units=functional_units,
        baseline_functional_use_id=baseline_use.pk,
        alternative_functional_use_id=alt_use.pk,
        baseline_factor_version_id=comparison["baseline"]["factor_version_id"],
        alternative_factor_version_id=comparison["alternative"]["factor_version_id"],
        baseline_quantity_per_functional_unit=comparison["baseline"]["quantity_per_functional_unit"],
        alternative_quantity_per_functional_unit=comparison["alternative"]["quantity_per_functional_unit"],
        alternative_quantity_equivalent=alternative_quantity_equivalent,
        baseline_impact_per_functional_unit=comparison["baseline"]["impact_a1a3_per_functional_unit"],
        alternative_impact_per_functional_unit=comparison["alternative"]["impact_a1a3_per_functional_unit"],
        absolute_delta=absolute_delta,
        relative_delta=comparison["relative_delta"],
        resultado=resultado,
        warnings=comparison["warnings"],
    )
