"""Deterministic environmental comparison over one functional unit (MI-01E).

Never compares raw factor/kg between alternatives — only
impact_per_functional_unit = approved_quantity_per_functional_unit ×
governed_environmental_factor, using Decimal throughout. Comparability
itself is never decided here: it is delegated to MI-01D's
eligibility_chain/comparable_alternatives, so a standard mismatch (A1 vs A2)
or a missing governed link always surfaces as `comparable: False` with an
explicit reason rather than a fabricated number.
"""

from datetime import date as date_cls
from decimal import Decimal

from ..models.governance import VersionFactorAmbiental
from .material_comparable_sets import eligibility_chain
from .material_functional_use import approved_functional_use
from .unit_conversion import UnitConversionError, convert_value

# Matches the persisted scenario/comparison DecimalField precision
# (max_digits=24, decimal_places=10). Multiplying/dividing Decimals never
# auto-rounds in Python, so every value that may end up persisted must be
# quantized explicitly here rather than relying on the DB to truncate it —
# unlike CalculoAmbiental, this model calls full_clean() and would reject an
# over-precise value outright instead of rounding it.
IMPACT_QUANTUM = Decimal("0.0000000001")


def material_impact_per_functional_unit(functional_use, factor_version):
    factor = factor_version.factor
    try:
        normalized = convert_value(
            functional_use.cantidad_por_unidad_funcional, functional_use.unidad, factor.unidad_entrada
        )
    except UnitConversionError as exc:
        return None, str(exc)
    impact = (normalized["valor_normalizado"] * factor_version.valor).quantize(IMPACT_QUANTUM)
    return impact, None


def compare_materials(organization, baseline_material, alternative_material, profile, effective_date=None):
    """Deterministic A1-A3 comparison of two materials for the same
    approved application profile, expressed per functional unit."""

    effective_date = effective_date or date_cls.today()

    baseline_chain, baseline_reasons = eligibility_chain(organization, baseline_material, profile, effective_date)
    if baseline_chain is None:
        return {"comparable": False, "reason": "baseline_not_eligible", "details": baseline_reasons}

    alt_chain, alt_reasons = eligibility_chain(organization, alternative_material, profile, effective_date)
    if alt_chain is None:
        return {"comparable": False, "reason": "alternative_not_eligible", "details": alt_reasons}

    if baseline_chain["standard"] != alt_chain["standard"]:
        return {
            "comparable": False,
            "reason": "standard_mismatch",
            "details": [f"{baseline_chain['standard']} vs {alt_chain['standard']}"],
        }

    baseline_use = approved_functional_use(organization, baseline_material, profile)
    alt_use = approved_functional_use(organization, alternative_material, profile)
    baseline_version = VersionFactorAmbiental.objects.get(pk=baseline_chain["factor_version_id"])
    alt_version = VersionFactorAmbiental.objects.get(pk=alt_chain["factor_version_id"])

    baseline_impact, baseline_error = material_impact_per_functional_unit(baseline_use, baseline_version)
    if baseline_impact is None:
        return {"comparable": False, "reason": "baseline_unit_incompatible", "details": [baseline_error]}

    alt_impact, alt_error = material_impact_per_functional_unit(alt_use, alt_version)
    if alt_impact is None:
        return {"comparable": False, "reason": "alternative_unit_incompatible", "details": [alt_error]}

    absolute_delta = (alt_impact - baseline_impact).quantize(IMPACT_QUANTUM)
    relative_delta = None
    warnings = []
    if baseline_impact == 0:
        warnings.append("baseline_zero_percentage_undefined")
    elif baseline_impact < 0:
        warnings.append("baseline_negative_percentage_omitted")
    else:
        relative_delta = (absolute_delta / baseline_impact).quantize(IMPACT_QUANTUM)

    if baseline_impact < 0 or alt_impact < 0:
        warnings.append("negative_gwp_present_sign_preserved")

    return {
        "comparable": True,
        "profile_id": profile.pk,
        "functional_unit": profile.unidad_funcional,
        "baseline": {
            "material_id": baseline_material.pk,
            "quantity_per_functional_unit": baseline_use.cantidad_por_unidad_funcional,
            "quantity_unit": baseline_use.unidad,
            "factor_version_id": baseline_version.pk,
            "factor_value": baseline_version.valor,
            "impact_a1a3_per_functional_unit": baseline_impact,
        },
        "alternative": {
            "material_id": alternative_material.pk,
            "quantity_per_functional_unit": alt_use.cantidad_por_unidad_funcional,
            "quantity_unit": alt_use.unidad,
            "factor_version_id": alt_version.pk,
            "factor_value": alt_version.valor,
            "impact_a1a3_per_functional_unit": alt_impact,
        },
        "absolute_delta": absolute_delta,
        "relative_delta": relative_delta,
        "warnings": warnings,
    }
