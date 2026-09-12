"""Read-only projections from frozen factor evidence, including historical results."""


def _en15804_generation(compliance):
    # Never invented: only an explicit "EN 15804+A1"/"EN 15804+A2" entry
    # already present in the EPD's own declared compliance list counts —
    # matches the same "standard" vocabulary ÖKOBAUDAT factors already use,
    # so `material_comparable_sets._standard_bucket` treats both sources
    # identically without knowing which one it is looking at.
    for entry in compliance or []:
        name = (entry or {}).get("short_name") if isinstance(entry, dict) else None
        if name and ("A1" in name or "A2" in name):
            return name
    return None


def factor_quality(factor):
    context = factor.contexto or {}
    source = context.get("knowledge_source", {})
    normalization = context.get("normalization", {})
    metadata = source.get("quality", {})
    known = {"source": source.get("source"), "external_id": source.get("external_id"),
             "dataset_version": source.get("upstream_version"), "declared_unit": source.get("declared_unit"),
             "boundary": normalization.get("lifecycle_scope"), "indicator": normalization.get("indicator"),
             "standard": _en15804_generation(metadata.get("compliance")),
             "lcia_method": normalization.get("lcia_method"), "gwp_available": normalization.get("version_value") is not None,
             "compliance": metadata.get("compliance"), "verification": metadata.get("third_party_verifier"),
             "owner_manufacturer": metadata.get("manufacturer"),
             "geography": metadata.get("applicable_in"), "review_id": context.get("review_id")}
    unknown = [key for key, value in known.items() if value is None]
    # This projection describes data quality, never suitability of a future alternative.
    return {"estado": "requires_review" if unknown else "sufficient", "known": known,
            "unknown": unknown, "reasons": [], "warnings": ["technical_comparability_not_assessed"],
            "assessment_basis": "frozen_ec3_review", "source_current": "evaluate_separately"}


def ledger_source(calculation):
    context = (calculation.snapshot_tecnico or {}).get("factor_contexto", {})
    if context.get("provider") != "EC3":
        return {}
    return {"external_source": context.get("knowledge_source"),
            "ec3_candidate_id": context.get("ec3_candidate_id"),
            "ec3_review_id": context.get("review_id")}
