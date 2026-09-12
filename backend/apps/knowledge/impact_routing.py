"""SOURCE-WATCH-01E — downstream impact routing.

Identifies which governed downstream objects an upstream change MAY affect
— read-only, never mutates them. Only routes through relationships that
actually exist and are already verified in this repository; it never
invents a consumer graph. Today that means exactly one concrete, fully
traceable route (ÖKOBAUDAT → `MaterialEnvironmentalFactorCandidate` →
`MaterialFactorMapping`/`FactorAmbiental`/`CalculoAmbiental`, reusing
`apps.analytics.services.material_source_impact`). Every other domain
fails closed to `unknown_impact` rather than guessing at a relationship
this layer cannot yet safely traverse — this is a documented, honest
limitation, not a placeholder pretending to be complete.
"""

NO_KNOWN_IMPACT = "no_known_impact"
REVIEW_RECOMMENDED = "review_recommended"
REVIEW_REQUIRED = "review_required"
BLOCKED = "blocked"
UNKNOWN_IMPACT = "unknown_impact"

_OKOBAUDAT_LEVELS = {
    "no_impact": NO_KNOWN_IMPACT,
    "review_recommended": REVIEW_RECOMMENDED,
    "review_required": REVIEW_REQUIRED,
}


def route_impact(classification):
    """Given one `change_classification.classify_change()` result, return
    the deterministic downstream impact envelope. Never mutates anything."""

    domain = classification["domain"]
    reasons = list(classification["reasons"])

    if domain == "okobaudat":
        detail = classification.get("detail") or {}
        affected = detail.get("affected")
        impact = detail.get("impact")
        if affected is None or impact is None:
            return _envelope(classification, UNKNOWN_IMPACT, [], reasons + ["sin_evaluacion_de_impacto_disponible"])
        level = _OKOBAUDAT_LEVELS.get(impact, UNKNOWN_IMPACT)
        affected_objects = []
        if affected.get("promoted_factor_id"):
            affected_objects.append({"type": "FactorAmbiental", "id": affected["promoted_factor_id"]})
        if affected.get("promoted_version_id"):
            affected_objects.append({"type": "VersionFactorAmbiental", "id": affected["promoted_version_id"]})
        for mapping_id in affected.get("mapping_ids", []) or []:
            affected_objects.append({"type": "MaterialFactorMapping", "id": mapping_id})
        if affected.get("calculation_count"):
            affected_objects.append({
                "type": "CalculoAmbiental", "id": None,
                "count": affected["calculation_count"],
                "note": "referencias_historicas_no_recalculadas",
            })
        return _envelope(classification, level, affected_objects, reasons)

    if domain == "legal":
        # Requires review unconditionally at classification time already;
        # a deterministic norm -> LegalObligationVersion traceability
        # query does not yet exist in this routing layer (the real chain
        # is norm -> text document -> parsed article -> extraction run ->
        # candidate -> obligation version, and asserting it here without a
        # verified join would risk inventing a relationship). Honestly
        # fails closed instead of guessing.
        return _envelope(
            classification, UNKNOWN_IMPACT, [],
            reasons + ["trazabilidad_norma_a_obligacion_no_implementada_en_este_enrutador"],
        )

    # Generic/unmodeled domains: no consumer relationship established.
    return _envelope(classification, UNKNOWN_IMPACT, [], reasons + ["sin_relacion_de_consumo_conocida_para_el_dominio"])


def _envelope(classification, impact_level, affected_objects, reasons):
    return {
        "source_id": classification["source_id"],
        "source_codigo": classification["source_codigo"],
        "external_id": classification["external_id"],
        "domain": classification["domain"],
        "classification": classification["classification"],
        "severity": classification.get("severity", ""),
        "impact_level": impact_level,
        "affected_objects": affected_objects,
        "reasons": reasons,
        "provenance": classification["provenance"],
    }


def route_run_impact(run):
    from .change_classification import classify_run

    result = classify_run(run)
    return {
        "run_id": result["run_id"],
        "source_id": result["source_id"],
        "impacts": [route_impact(c) for c in result["classifications"]],
    }
