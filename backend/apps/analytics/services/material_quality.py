"""MATERIAL-DATA-01F — deterministic material environmental data quality &
suitability assessment. No AI, no opaque score.

The assessment is a pure function of already-frozen, immutable evidence:
``MaterialEnvironmentalFactorCandidate.initial_eligibility`` (01C's own
eligibility verdict, frozen at build time) and ``functional_context`` /
``normalization`` (also frozen). This makes the assessment itself
deterministic and reconstructible for free: the same candidate always
yields the same verdict, forever, without re-touching upstream.

The hard-fail axis (``insufficient``) is never invented here: it is exactly
01C's own ``compatible`` flag and ``reasons``, reused rather than duplicated.
This module only adds the softer metadata-richness axis on top
(``requires_review`` warnings) that 01C's binary eligibility does not need.
"""

SUFFICIENT = "sufficient"
REQUIRES_REVIEW = "requires_review"
INSUFFICIENT = "insufficient"


def _warning(reasons, condition, code):
    if condition:
        reasons.append(code)


def assess_material_data_quality(candidate):
    """Deterministic quality/suitability verdict for one material candidate.

    Reuses the candidate's own frozen eligibility (01C) for the hard-fail
    axis; only adds metadata-richness warnings on top.
    """
    eligibility = candidate.initial_eligibility or {}
    normalization = candidate.normalization or {}
    functional = candidate.functional_context or {}
    compliance = functional.get("compliance") or {}

    known = {
        "standard": normalization.get("standard"),
        "boundary": normalization.get("boundary"),
        "dataset_version": candidate.provenance.get("dataset_version") if candidate.provenance else None,
        "declared_unit": normalization.get("declared_unit"),
        "indicator": normalization.get("indicator"),
        "gwp_available": normalization.get("normalized_factor_value") is not None,
        "location": functional.get("location"),
        "owner_manufacturer": functional.get("owner_manufacturer"),
        "classification": functional.get("classification"),
        "dataset_type": functional.get("dataset_type"),
        "compliance_standard": compliance.get("standard"),
        "current": eligibility.get("source_current"),
    }

    if not eligibility.get("compatible", False):
        return {
            "estado": INSUFFICIENT,
            "reasons": list(eligibility.get("reasons") or ["eligibilidad_no_evaluada"]),
            "warnings": [],
            "known": known,
            "unknown": [],
        }

    reasons = []
    warnings = []
    unknown = []

    _warning(warnings, eligibility.get("source_current") is False, "historical_source")
    _warning(warnings, functional.get("location") in (None, "", "unknown"), "unknown_geography")
    if functional.get("location") in (None, "", "unknown"):
        unknown.append("location")
    _warning(warnings, functional.get("owner_manufacturer") in (None, "", "unknown"), "unknown_owner")
    if functional.get("owner_manufacturer") in (None, "", "unknown"):
        unknown.append("owner_manufacturer")
    dataset_type = functional.get("dataset_type") or ""
    _warning(warnings, dataset_type in ("", "unknown"), "unknown_dataset_type")
    if dataset_type in ("", "unknown"):
        unknown.append("dataset_type")
    elif "generic" in dataset_type.casefold():
        warnings.append("generic_dataset")
    compliance_standard = compliance.get("standard")
    compliance_unknown = compliance_standard in (None, "", "unknown")
    _warning(warnings, compliance_unknown, "missing_compliance_metadata")
    if compliance_unknown:
        unknown.append("compliance_standard")
    _warning(warnings, normalization.get("standard") == "EN 15804+A1", "legacy_a1_standard")

    warnings = list(dict.fromkeys(warnings))
    unknown = list(dict.fromkeys(unknown))
    estado = REQUIRES_REVIEW if warnings else SUFFICIENT
    return {
        "estado": estado,
        "reasons": reasons,
        "warnings": warnings,
        "known": known,
        "unknown": unknown,
    }


def assess_factor_data_quality(factor):
    """Resolve a FactorAmbiental/VersionFactorAmbiental back to its origin
    candidate (01C) and assess it. Factors with no ÖKOBAUDAT-governed origin
    (e.g. a private tenant factor) have no upstream metadata to assess: this
    is reported explicitly, never guessed."""
    candidate = getattr(factor, "material_source_candidate", None)
    if candidate is None:
        return {
            "estado": REQUIRES_REVIEW,
            "reasons": [],
            "warnings": ["sin_origen_okobaudat"],
            "known": {},
            "unknown": ["origen_catalogo"],
        }
    return assess_material_data_quality(candidate)
