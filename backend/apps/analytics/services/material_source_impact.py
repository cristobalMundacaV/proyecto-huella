"""MATERIAL-DATA-01I — source refresh & version impact governance.

Pure read-only diff between what a candidate/promoted factor was built
from (frozen provenance) and what has *already* been locally hydrated by
the existing 01A/01B sync commands. This module fetches nothing from
upstream itself and writes nothing: idempotent and concurrency-safe by
construction. It never overwrites a fact, activates a factor, revokes a
mapping, or recalculates a reception — it only classifies.
"""

from apps.knowledge.models import ExternalRecord, OekobaudatEnvironmentalProfileFact

from ..models.material_factor_mapping import MaterialFactorMapping
from .material_candidates import evaluate_material_profile

NO_IMPACT = "no_impact"
REVIEW_RECOMMENDED = "review_recommended"
REVIEW_REQUIRED = "review_required"


def _active_identity_record(profile):
    process = profile.process
    return (
        ExternalRecord.objects.filter(
            source_id=profile.snapshot.source_id,
            kind="okobaudat_process",
            estado="activo",
            current_snapshot__raw_payload__process_uuid=str(profile.process_uuid),
            current_snapshot__raw_payload__datastock_uuid=str(process.datastock_uuid),
        )
        .select_related("current_snapshot")
        .order_by("-current_snapshot__raw_payload__dataset_version")
        .first()
    )


def _affected_objects(candidate):
    affected = {
        "candidate_id": candidate.pk,
        "promoted_factor_id": candidate.promoted_factor_id,
        "promoted_version_id": candidate.promoted_version_id,
        "mapping_ids": [],
        "calculation_count": 0,
    }
    if candidate.promoted_factor_id:
        affected["mapping_ids"] = list(
            MaterialFactorMapping.objects.filter(
                factor_id=candidate.promoted_factor_id
            ).values_list("id", flat=True)
        )
        from ..models import CalculoAmbiental

        affected["calculation_count"] = CalculoAmbiental.objects.filter(
            version_factor__factor_id=candidate.promoted_factor_id
        ).count()
    return affected


def assess_candidate_impact(candidate):
    """Deterministic, read-only impact classification for one candidate
    against whatever has already been locally hydrated. Never mutates
    anything; safe to call concurrently any number of times."""
    profile = candidate.source_profile
    reasons = []
    impact = NO_IMPACT

    record = _active_identity_record(profile)
    if record is None:
        reasons.append("proceso_no_activo")
        impact = REVIEW_REQUIRED
        return {
            "candidate_id": candidate.pk,
            "impact": impact,
            "reasons": reasons,
            "local_dataset_version": profile.dataset_version,
            "upstream_dataset_version": None,
            "affected": _affected_objects(candidate),
        }

    upstream_version = record.current_snapshot.raw_payload.get("dataset_version")
    upstream_version_str = str(upstream_version) if upstream_version is not None else None

    if record.current_snapshot_id == profile.process.snapshot_id:
        return {
            "candidate_id": candidate.pk,
            "impact": NO_IMPACT,
            "reasons": [],
            "local_dataset_version": profile.dataset_version,
            "upstream_dataset_version": upstream_version_str,
            "affected": _affected_objects(candidate),
        }

    if upstream_version_str and upstream_version_str > profile.dataset_version:
        reasons.append("nueva_version_disponible")
        impact = REVIEW_RECOMMENDED
        newer_profile = (
            OekobaudatEnvironmentalProfileFact.objects.filter(
                process__process_uuid=profile.process_uuid,
                dataset_version=upstream_version_str,
            )
            .order_by("-pk")
            .first()
        )
        if newer_profile is None:
            reasons.append("nueva_version_no_hidratada_localmente")
        else:
            newer_candidate = getattr(newer_profile, "material_factor_candidate", None)
            if newer_candidate is None:
                reasons.append("nueva_version_no_evaluada_como_candidato")
            else:
                new_eval = evaluate_material_profile(newer_profile)
                old_norm = candidate.normalization or {}
                new_norm = new_eval["normalization"]
                if new_norm.get("normalized_factor_value") != old_norm.get(
                    "normalized_factor_value"
                ):
                    reasons.append("gwp_modificado")
                    impact = REVIEW_REQUIRED
                if new_norm.get("declared_unit") != old_norm.get("declared_unit"):
                    reasons.append("unidad_declarada_modificada")
                    impact = REVIEW_REQUIRED
                if new_norm.get("standard") != old_norm.get("standard"):
                    reasons.append("standard_modificado")
                    impact = REVIEW_REQUIRED
    elif upstream_version_str == profile.dataset_version:
        # Same declared version, different snapshot identity: a silent
        # republish upstream, never treated as equivalent.
        reasons.append("republicacion_detectada_mismo_dataset_version")
        impact = REVIEW_REQUIRED
    else:
        reasons.append("version_local_mas_reciente_que_activa")
        impact = NO_IMPACT

    return {
        "candidate_id": candidate.pk,
        "impact": impact,
        "reasons": list(dict.fromkeys(reasons)),
        "local_dataset_version": profile.dataset_version,
        "upstream_dataset_version": upstream_version_str,
        "affected": _affected_objects(candidate),
    }


def assess_all_candidates(**filters):
    """Idempotent, read-only report over every candidate matching
    ``filters`` (e.g. status='promoted_to_draft'). Concurrency-safe: no
    writes anywhere, so two simultaneous runs cannot contradict each
    other — they simply compute the same deterministic answer twice."""
    from ..models import MaterialEnvironmentalFactorCandidate as Candidate

    candidates = Candidate.objects.filter(**filters).select_related(
        "source_profile__process", "source_profile__snapshot"
    ).order_by("pk")
    results = [assess_candidate_impact(candidate) for candidate in candidates]
    summary = {
        NO_IMPACT: sum(1 for r in results if r["impact"] == NO_IMPACT),
        REVIEW_RECOMMENDED: sum(1 for r in results if r["impact"] == REVIEW_RECOMMENDED),
        REVIEW_REQUIRED: sum(1 for r in results if r["impact"] == REVIEW_REQUIRED),
    }
    return {"total": len(results), "resumen": summary, "resultados": results}
