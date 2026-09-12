"""EC3-01 — pairwise EPD comparability (capability 7 of the EC3 mission).

Deterministic, fully explainable comparability between two already-ingested
EC3 `EpdVersion` rows — never a similarity/embedding score. Two EPDs are
only ever COMPARABLE when: both are individually scientifically eligible
(`services.evaluate_version`), share the same EC3 product category, the
same declared-unit type, an overlapping declared geography, the same
lifecycle scope and the same LCIA method basis. A shared category/unit/
geography/scope but a differing PCR is PARTIALLY_COMPARABLE (explained).
Anything else is NOT_COMPARABLE, with every disqualifying reason listed.
Ineligible input on either side is REVIEW_REQUIRED, not a guess.

This module intentionally does not decide whether either EPD is a valid
substitute in practice — it only answers "can these two be compared at
all," which capability 8 (`opportunity.py`) then builds on.
"""

from .services import evaluate_version


def _geography(evidence):
    values = evidence.get("applicable_in")
    return set(values) if isinstance(values, list) else set()


def compare_epd_versions(version_a, version_b, method):
    eval_a = evaluate_version(version_a, method)
    eval_b = evaluate_version(version_b, method)

    ineligible = []
    if not eval_a["compatible"]:
        ineligible.append("epd_a_not_eligible")
    if not eval_b["compatible"]:
        ineligible.append("epd_b_not_eligible")
    if ineligible:
        return {"result": "REVIEW_REQUIRED", "reasons": ineligible,
                "eligibility": {"a": eval_a, "b": eval_b}}

    evidence_a, evidence_b = version_a.evidence, version_b.evidence
    reasons = []

    category_a = (evidence_a.get("ec3") or {}).get("category")
    category_b = (evidence_b.get("ec3") or {}).get("category")
    if not category_a or not category_b:
        reasons.append("missing_category")
    elif category_a != category_b:
        reasons.append("category_mismatch")

    if eval_a["input_unit"] != eval_b["input_unit"]:
        reasons.append("declared_unit_type_mismatch")

    geography_a, geography_b = _geography(evidence_a), _geography(evidence_b)
    if not geography_a or not geography_b:
        reasons.append("missing_geography")
    elif not (geography_a & geography_b):
        reasons.append("geography_disjoint")

    if eval_a["lifecycle_scope"] != eval_b["lifecycle_scope"]:
        reasons.append("lifecycle_scope_mismatch")

    if eval_a["lcia_method"] != eval_b["lcia_method"]:
        reasons.append("lcia_method_mismatch")

    if reasons:
        return {"result": "NOT_COMPARABLE", "reasons": reasons,
                "eligibility": {"a": eval_a, "b": eval_b}}

    pcr_a = (evidence_a.get("pcr") or {}).get("id")
    pcr_b = (evidence_b.get("pcr") or {}).get("id")
    if pcr_a and pcr_b and pcr_a != pcr_b:
        return {"result": "PARTIALLY_COMPARABLE", "reasons": ["pcr_mismatch"],
                "eligibility": {"a": eval_a, "b": eval_b}}

    return {"result": "COMPARABLE", "reasons": [], "eligibility": {"a": eval_a, "b": eval_b}}
