"""EC3-01 — candidate-level potential opportunity preview (capability 8).

This does NOT duplicate MI-01H's `apps.analytics.services.material_opportunities
.detect_opportunities`: once an EC3-sourced factor is promoted, mapped and
approved (its `VersionFactorAmbiental` reaches `activo`), the material it is
mapped to already participates fully in that existing, source-agnostic
hotspot/comparable-set/opportunity engine — through the `factor_block_reason`
governance hook already wired into `material_factor_selector`. Nothing here
re-implements hotspots, comparable sets or the deterministic comparison;
this module only covers the distinct PRE-decisional case: a human has
already proposed one or more EC3 candidates for a material
(`services.propose_candidate`) that are not yet operationally applied, and
wants to preview — before spending real review effort — whether pursuing
that review would plausibly lower the material's A1-A3 impact.

Every result is explicitly a *potential* figure: `requires_human_review` is
always True, nothing is ever marked adopted/approved/recommended, and a
candidate that fails scientific eligibility or unit comparability is
reported with its exact reasons rather than silently dropped or guessed.
"""

from datetime import date as date_cls
from decimal import Decimal

from apps.analytics.services.material_factor_selector import select_material_factor
from apps.analytics.services.unit_conversion import UnitConversionError, convert_value

from .comparability import compare_epd_versions
from .models import Candidate
from .services import evaluate_version

IMPACT_QUANTUM = Decimal("0.0000000001")


def _is_operationally_applied(candidate):
    return bool(
        candidate.mapping_id
        and candidate.mapping.estado == "aprobado"
        and candidate.promoted_version_id
        and candidate.promoted_version.estado == "activo"
    )


def _baseline(organization, material, effective_date):
    selection = select_material_factor(organization, material, material.unidad_base, effective_date)
    if selection["status"] != "calculable":
        return None
    factor_version = selection["factor_version"]
    return {
        "factor_version_id": factor_version.pk,
        "value": factor_version.valor,
        "unit": factor_version.factor.unidad_entrada,
    }


def _candidate_preview(candidate, method, baseline):
    evaluation = evaluate_version(candidate.epd_version, method)
    entry = {
        "candidate_id": candidate.pk, "epd_version_id": candidate.epd_version_id,
        "eligible": evaluation["compatible"], "eligibility_reasons": evaluation["reasons"],
        "candidate_value_per_declared_unit": None, "candidate_unit": None,
        "potential_reduction_per_baseline_unit": None, "comparison_reasons": [],
        "requires_human_review": True, "status": "candidate_not_yet_applied",
    }
    if not evaluation["compatible"]:
        return entry

    entry["candidate_value_per_declared_unit"] = evaluation["version_value"]
    entry["candidate_unit"] = evaluation["input_unit"]

    if baseline is None:
        entry["comparison_reasons"] = ["no_active_baseline_factor"]
        return entry

    try:
        converted = convert_value(Decimal(evaluation["version_value"]), evaluation["input_unit"], baseline["unit"])
    except UnitConversionError as exc:
        entry["comparison_reasons"] = ["baseline_unit_incompatible: " + str(exc)]
        return entry

    candidate_value = converted["valor_normalizado"]
    delta = (baseline["value"] - candidate_value).quantize(IMPACT_QUANTUM)
    entry["potential_reduction_per_baseline_unit"] = str(delta) if delta > 0 else "0"
    entry["direction"] = "lower" if delta > 0 else ("higher" if delta < 0 else "equal")
    return entry


def material_candidate_opportunities(organization, material, method, *, effective_date=None):
    """Preview, per already-proposed EC3 candidate on `material`, whether
    pursuing human review would plausibly lower its A1-A3 impact versus the
    material's current active factor (if any). Never searches EC3 or
    proposes candidates itself — only reports on what a human already
    proposed via `services.propose_candidate`."""

    if material.organizacion_id != organization.id:
        return {"material_id": material.pk, "candidates": [], "reason": "different_organization"}

    effective_date = effective_date or date_cls.today()
    baseline = _baseline(organization, material, effective_date)
    candidates = (
        Candidate.objects.filter(material=material)
        .select_related("epd_version", "mapping", "promoted_version")
        .order_by("pk")
    )

    return {
        "material_id": material.pk,
        "baseline_factor_version_id": baseline["factor_version_id"] if baseline else None,
        "baseline_value_per_unit": str(baseline["value"]) if baseline else None,
        "baseline_unit": baseline["unit"] if baseline else None,
        "candidates": [
            _candidate_preview(candidate, method, baseline)
            for candidate in candidates if not _is_operationally_applied(candidate)
        ],
    }


def compare_candidates(candidate_a, candidate_b, method):
    """Explicit two-alternative comparison between two already-proposed EC3
    candidates (capability 7 exposed at the candidate level): comparability
    first (`comparability.compare_epd_versions`), and only when at least
    PARTIALLY_COMPARABLE, the environmental difference between their
    normalized declared-unit values. Never ranks purchase viability."""

    comparability = compare_epd_versions(candidate_a.epd_version, candidate_b.epd_version, method)
    result = {
        "candidate_a_id": candidate_a.pk, "candidate_b_id": candidate_b.pk,
        "comparability": comparability["result"], "reasons": comparability["reasons"],
        "potential_difference": None, "requires_human_review": True,
    }
    if comparability["result"] not in ("COMPARABLE", "PARTIALLY_COMPARABLE"):
        return result

    value_a = Decimal(comparability["eligibility"]["a"]["version_value"])
    value_b = Decimal(comparability["eligibility"]["b"]["version_value"])
    result["potential_difference"] = str((value_b - value_a).quantize(IMPACT_QUANTUM))
    return result
