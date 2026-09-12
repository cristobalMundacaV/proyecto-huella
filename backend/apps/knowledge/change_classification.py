"""SOURCE-WATCH-01D — source-specific change classification.

Routes each normalized event from `change_observation.observe_sync_run()`
through a deterministic, rule-based classifier. Severity/requires_review
are never set by an LLM. Domain-specific classifiers are dispatched by
`connector_key`; any source without a specific classifier falls back to
`classify_generic_change`, which never assumes `no impact` for a change or
a disappearance it cannot interpret — it fails closed into
`changed_unknown_impact` / `requires_review=True`.

For ÖKOBAUDAT this reuses (never reimplements) MATERIAL-DATA's own
`apps.analytics.services.material_source_impact` module.
"""

from .change_observation import CHANGED, CREATED, DISAPPEARED, REAPPEARED, UNCHANGED

# Bounded severity vocabulary — deterministic, rule-based only.
LOW = "low"
MEDIUM = "medium"
HIGH = "high"

UNKNOWN_IMPACT = "changed_unknown_impact"


def _envelope(event, source, *, classification, severity, requires_review, reasons, domain, detail=None):
    return {
        "source_id": source.pk,
        "source_codigo": source.codigo,
        "external_id": event["external_id"],
        "event_classification": event["classification"],
        "classification": classification,
        "severity": severity,
        "requires_review": requires_review,
        "reasons": reasons,
        "domain": domain,
        "provenance": {
            "snapshot_id": event.get("snapshot_id"),
            "content_hash": event.get("content_hash"),
            "retrieved_at": event.get("retrieved_at"),
        },
        "detail": detail or {},
    }


def classify_generic_change(event, source):
    """Fail-closed default: never assume `no impact` for anything but a
    genuinely unremarkable classification (unchanged, or a brand new
    record with nothing pre-existing to affect)."""

    kind = event["classification"]
    if kind == UNCHANGED:
        return _envelope(
            event, source, classification="unchanged", severity=LOW,
            requires_review=False, reasons=["sin_cambio_de_contenido"], domain="generic",
        )
    if kind == CREATED:
        return _envelope(
            event, source, classification="new_record", severity=LOW,
            requires_review=False, reasons=["registro_nuevo_sin_impacto_previo"], domain="generic",
        )
    if kind == DISAPPEARED:
        return _envelope(
            event, source, classification="disappeared_unknown_impact", severity=HIGH,
            requires_review=True, reasons=["registro_ausente_en_observacion_autoritativa"], domain="generic",
        )
    if kind == REAPPEARED:
        return _envelope(
            event, source, classification="reappeared_unknown_impact", severity=MEDIUM,
            requires_review=True, reasons=["registro_reaparecido_tras_ausencia"], domain="generic",
        )
    # CHANGED, and any future/unknown event kind: never assume no impact.
    return _envelope(
        event, source, classification=UNKNOWN_IMPACT, severity=MEDIUM,
        requires_review=True, reasons=["sin_regla_de_dominio_para_interpretar_el_cambio"], domain="generic",
    )


def classify_okobaudat_change(event, source):
    """Reuses MATERIAL-DATA's own ÖKOBAUDAT impact assessment — never a
    second version-diff authority. Only escalates beyond the generic
    default when a governed `MaterialEnvironmentalFactorCandidate` actually
    references the affected process; otherwise falls back to the generic
    classifier (still fail-closed, never `no_impact` for an uninterpreted
    change)."""

    from apps.analytics.models import MaterialEnvironmentalFactorCandidate
    from apps.analytics.services.material_source_impact import assess_candidate_impact

    if event["classification"] not in (CHANGED, DISAPPEARED):
        return classify_generic_change(event, source)

    candidates = MaterialEnvironmentalFactorCandidate.objects.filter(
        source_profile__process__snapshot__source_id=source.pk,
    )
    if not candidates.exists():
        return classify_generic_change(event, source)

    worst = None
    reasons = []
    for candidate in candidates:
        result = assess_candidate_impact(candidate)
        reasons.extend(result["reasons"])
        rank = {"no_impact": 0, "review_recommended": 1, "review_required": 2}[result["impact"]]
        if worst is None or rank > worst[0]:
            worst = (rank, result)

    impact = worst[1]["impact"] if worst else "review_required"
    severity = {"no_impact": LOW, "review_recommended": MEDIUM, "review_required": HIGH}[impact]
    return _envelope(
        event, source, classification=f"okobaudat_{impact}", severity=severity,
        requires_review=impact != "no_impact", reasons=sorted(set(reasons)) or ["sin_razon_especifica"],
        domain="okobaudat", detail=worst[1] if worst else {},
    )


def classify_bcn_legal_change(event, source):
    """Legal-norm content changes are always significant: BCN/LeyChile
    governance requires explicit human review before any legal conclusion
    is trusted (see the legal obligation lifecycle in this same app) —
    never silently downgraded to low severity."""

    if event["classification"] == UNCHANGED:
        return classify_generic_change(event, source)
    return _envelope(
        event, source, classification="legal_norm_changed", severity=HIGH,
        requires_review=True, reasons=["cambio_en_fuente_legal_requiere_revision_humana"],
        domain="legal",
    )


CHANGE_CLASSIFIERS = {
    "okobaudat_soda4lca": classify_okobaudat_change,
    "bcn_leychile_sparql": classify_bcn_legal_change,
}


def classify_change(event, source):
    classifier = CHANGE_CLASSIFIERS.get(source.connector_key, classify_generic_change)
    return classifier(event, source)


def classify_run(run):
    from .change_observation import observe_sync_run

    observation = observe_sync_run(run)
    return {
        "run_id": run.pk,
        "source_id": run.source_id,
        "authoritative": observation["authoritative"],
        "source_metadata_changed": observation.get("source_metadata_changed", False),
        "classifications": [classify_change(event, run.source) for event in observation["events"]],
    }
