"""Comparable alternative sets (MI-01D): which materials may enter an
environmental comparison for one approved application profile, and why.

Comparability is never derived from name/category/embedding similarity —
only from an explicit governed chain: approved profile, human-approved
suitability, approved functional use, a governed environmental factor
(reusing the existing MATERIAL-DATA-01D selector, never re-implemented),
usable environmental data quality, a confirmed A1-A3 boundary and a matching
EN 15804 generation (A1<->A1, A2<->A2; A1<->A2 is a standard mismatch, never
silently reconciled). No new persisted model: this is a pure, on-read
derivation over already-governed authorities.
"""

from datetime import date as date_cls

from ..models.material_application_profile import MaterialApplicationProfile
from ..models.material_functional_use import MaterialApplicationAssessment, MaterialFunctionalUse
from .material_factor_selector import select_material_factor
from .material_quality import INSUFFICIENT, assess_factor_data_quality


def _standard_bucket(standard):
    if not standard:
        return None
    if "A1" in standard:
        return "A1"
    if "A2" in standard:
        return "A2"
    return None


def _latest_assessment(organization, material, profile):
    return (
        MaterialApplicationAssessment.objects.filter(
            organizacion=organization, material=material, profile=profile,
        )
        .order_by("-created_at", "-id")
        .first()
    )


def eligibility_chain(organization, material, profile, effective_date=None):
    """Whether `material` may enter ANY comparison for `profile`.

    Returns (chain, None) when eligible, or (None, reasons) when not, where
    `reasons` is a list of explicit, machine-checkable codes — never a
    similarity heuristic and never invented from the material's name.
    """
    effective_date = effective_date or date_cls.today()
    reasons = []

    if material.organizacion_id != organization.id or profile.organizacion_id != organization.id:
        return None, ["different_organization"]
    if profile.estado != MaterialApplicationProfile.Estado.APROBADO:
        return None, ["profile_not_approved"]

    assessment = _latest_assessment(organization, material, profile)
    if (
        assessment is None
        or assessment.decision_humana != MaterialApplicationAssessment.DecisionHumana.APROBADO
    ):
        reasons.append("suitability_not_approved")

    functional_use = MaterialFunctionalUse.objects.filter(
        organizacion=organization, material=material, profile=profile,
        estado=MaterialFunctionalUse.Estado.APROBADO,
    ).first()
    if functional_use is None:
        reasons.append("functional_use_not_approved")

    quality = None
    standard_bucket = None
    selection = select_material_factor(organization, material, material.unidad_base, effective_date)
    if selection["status"] != "calculable":
        reasons.append("environmental_factor_not_available")
    else:
        factor = selection["factor_version"].factor
        quality = assess_factor_data_quality(factor)
        if quality["estado"] == INSUFFICIENT:
            reasons.append("environmental_data_insufficient")
        if quality["known"].get("boundary") != "A1-A3":
            reasons.append("boundary_not_confirmed_a1_a3")
        standard_bucket = _standard_bucket(quality["known"].get("standard"))
        if standard_bucket is None:
            reasons.append("standard_unknown")

    if reasons:
        return None, reasons

    return {
        "material_id": material.pk,
        "assessment_id": assessment.pk,
        "functional_use_id": functional_use.pk,
        "factor_version_id": selection["factor_version"].pk,
        "quality_estado": quality["estado"],
        "standard": standard_bucket,
    }, None


def comparable_alternatives(organization, source_material, profile, candidate_materials, effective_date=None):
    """Per source material: which of `candidate_materials` are directly
    comparable to it for `profile`, with an explicit reason for every
    exclusion. Never ranks, scores or recommends — that is MI-01H/MI-01I."""

    source_chain, source_reasons = eligibility_chain(organization, source_material, profile, effective_date)
    if source_chain is None:
        return {
            "source_material_id": source_material.pk,
            "source_eligible": False,
            "source_exclusion_reasons": source_reasons,
            "comparable_candidates": [],
            "excluded_candidates": [],
        }

    comparable = []
    excluded = []
    for candidate in candidate_materials:
        if candidate.pk == source_material.pk:
            continue
        chain, reasons = eligibility_chain(organization, candidate, profile, effective_date)
        if chain is None:
            excluded.append({"material_id": candidate.pk, "reasons": reasons})
            continue
        if chain["standard"] != source_chain["standard"]:
            excluded.append({"material_id": candidate.pk, "reasons": ["standard_mismatch"]})
            continue
        comparable.append({"material_id": candidate.pk, "chain": chain})

    return {
        "source_material_id": source_material.pk,
        "source_eligible": True,
        "source_chain": source_chain,
        "comparable_candidates": comparable,
        "excluded_candidates": excluded,
    }
