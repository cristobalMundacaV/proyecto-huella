"""Deterministic A1-A3 normalization and explicit global human governance."""

from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_EVEN

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.knowledge.connectors.okobaudat_detail import (
    GWP,
    VERSION,
    dataset_url,
    DetailError,
    validate_detail_url,
)
from apps.knowledge.models import (
    EnvironmentalSource,
    ExternalRecord,
    ExternalSnapshot,
    SourceState,
    OekobaudatEnvironmentalProfileFact,
)
from apps.knowledge.okobaudat_detail_sync import snapshot_bytes
from ..models import (
    MaterialEnvironmentalFactorCandidate as Candidate,
    MaterialFactorCandidateReview as Review,
    FactorAmbiental,
    VersionFactorAmbiental,
)
from ..models.material_candidates import material_write
from .unit_conversion import canonicalize_unit, UnitConversionError

INDICATORS = {"EN 15804+A1": "GWP", "EN 15804+A2": "GWP-total"}
RESULT_UNIT_UUID = "1ebf3012-d0db-4de2-aefd-ef30cedb0be1"
RESULT_LABELS = {"kg CO_(2) eq", "kg CO2-Äqv.", "kgCO2e"}


@contextmanager
def governed_write():
    token = material_write.set(True)
    try:
        yield
    finally:
        material_write.reset(token)


def require_global_reviewer(user):
    if (
        not user
        or not user.is_authenticated
        or not user.is_active
        or not user.is_superuser
    ):
        raise PermissionDenied(
            "Sólo un superusuario activo puede gobernar candidatos globales."
        )


def source_current(profile):
    """Current means published catalog identity, not snapshot age or EPD validity."""
    source = EnvironmentalSource.objects.get(pk=profile.snapshot.source_id)
    state = SourceState.objects.filter(source=source).first()
    if (
        not source.activa
        or not state
        or state.estado in {"sincronizando", "parcial", "nunca_sincronizada"}
    ):
        return False
    records = ExternalRecord.objects.filter(
        source=source, kind="okobaudat_process", estado="activo"
    )
    if not records.filter(current_snapshot_id=profile.process.snapshot_id).exists():
        return False
    # Versions are fixed-width ILCD tuples; comparison is within the same datastock.
    return not records.filter(
        current_snapshot__raw_payload__process_uuid=str(profile.process_uuid),
        current_snapshot__raw_payload__datastock_uuid=str(
            profile.process.datastock_uuid
        ),
        current_snapshot__raw_payload__dataset_version__gt=profile.dataset_version,
    ).exists()


def _decimal(value):
    number = Decimal(value)
    if (
        not number.is_finite()
        or abs(number) >= Decimal("1e60")
        or abs(number.adjusted()) > 200
    ):
        raise InvalidOperation
    return number


def evaluate_material_profile(profile):
    reasons = []
    current = source_current(profile)
    if not current:
        reasons.append("historical_source")
    process, snapshot = profile.process, profile.snapshot
    if (
        not profile.process_uuid
        or not VERSION.fullmatch(profile.dataset_version)
        or profile.process_uuid != process.process_uuid
        or profile.dataset_version != process.dataset_version
    ):
        reasons.append("invalid_identity")
    code = INDICATORS.get(profile.standard)
    if not code or process.compliance_standard_raw != profile.standard:
        reasons.append("unknown_or_conflicting_standard")
    rows = sorted(profile.indicators.all(), key=lambda row: row.pk)
    matches = [row for row in rows if row.code == code]
    indicator = matches[0] if len(matches) == 1 else None
    if not indicator:
        reasons.append("missing_gwp")
    elif (
        GWP.get(str(indicator.upstream_uuid)) != (profile.standard, code)
        or indicator.standard != profile.standard
        or indicator.module != "A1-A3"
        or indicator.snapshot_id != snapshot.pk
        or indicator.process_uuid != profile.process_uuid
        or indicator.dataset_version != profile.dataset_version
    ):
        reasons.append("invalid_indicator_identity")
    if any(row.module != "A1-A3" for row in rows):
        reasons.append("incomplete_a1a3")
    amount = value = normalized = None
    try:
        amount = _decimal(profile.declared_amount)
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError, TypeError):
        reasons.append("invalid_declared_quantity")
        amount = None
    try:
        input_unit = canonicalize_unit(profile.declared_unit)
    except UnitConversionError:
        input_unit = None
        reasons.append("unsupported_unit")
    if indicator:
        if (
            str(indicator.unit_uuid) != RESULT_UNIT_UUID
            or indicator.unit not in RESULT_LABELS
        ):
            reasons.append("unsupported_unit")
        try:
            value = _decimal(indicator.value)
        except (InvalidOperation, TypeError, ValueError):
            reasons.append("invalid_gwp")
    profile_provenance = (
        profile.provenance if isinstance(profile.provenance, dict) else {}
    )
    snapshot_metadata = snapshot.metadata if isinstance(snapshot.metadata, dict) else {}
    provenance = {
        "provider": "ÖKOBAUDAT",
        "profile_id": profile.pk,
        "process_fact_id": process.pk,
        "snapshot_id": snapshot.pk,
        "content_hash": snapshot.content_hash,
        "source_url": snapshot.source_url,
        "retrieved_at": snapshot.retrieved_at.isoformat(),
        "catalog_snapshot_id": process.snapshot_id,
        "process_uuid": str(profile.process_uuid),
        "dataset_version": profile.dataset_version,
        "parser_version": profile.parser_version,
        "references": profile_provenance.get("references", []),
        "reference_metadata": profile.reference_metadata,
        "source_terms": snapshot_metadata.get("source_terms", {}),
        "gwp_components": [
            {
                "id": r.pk,
                "code": r.code,
                "uuid": str(r.upstream_uuid),
                "value": r.value,
                "unit": r.unit,
            }
            for r in rows
            if r.code in {"GWP-fossil", "GWP-biogenic", "GWP-luluc"}
        ],
    }
    try:
        if (
            snapshot.source.codigo != "okobaudat"
            or snapshot.source_id != process.snapshot.source_id
            or snapshot.record_kind != "okobaudat_process_detail"
            or snapshot.source_url
            != dataset_url(
                "processes", str(profile.process_uuid), profile.dataset_version
            )
            or not profile.reference_metadata
            or not provenance["source_terms"]
            or len(provenance["references"]) < 3
        ):
            raise DetailError("Incomplete provenance")
        snapshot_bytes(snapshot)
        for ref in provenance["references"]:
            dependency = ExternalSnapshot.objects.get(
                pk=ref["snapshot_id"],
                source_id=snapshot.source_id,
                record_kind="okobaudat_detail_reference",
            )
            validate_detail_url(ref["source_url"])
            if (
                dependency.content_hash != ref["content_hash"]
                or dependency.source_url != ref["source_url"]
                or not ref["uuid"]
                or not ref["dataset_version"]
                or dependency.retrieved_at.isoformat() != ref["retrieved_at"]
            ):
                raise DetailError("Incomplete reference")
            snapshot_bytes(dependency)
    except (
        DetailError,
        KeyError,
        TypeError,
        ValueError,
        ExternalSnapshot.DoesNotExist,
    ):
        reasons.append("incomplete_provenance")
    if (
        amount is not None
        and value is not None
        and input_unit
        and "unsupported_unit" not in reasons
    ):
        with localcontext() as ctx:
            ctx.prec = 80
            normalized = value / amount
            try:
                stored = normalized.quantize(
                    Decimal("0.0000000001"), rounding=ROUND_HALF_EVEN
                )
                if abs(stored) >= Decimal("1e10") or (normalized != 0 and stored == 0):
                    reasons.append("factor_storage_out_of_range")
            except InvalidOperation:
                reasons.append("factor_storage_out_of_range")
                stored = None
    else:
        stored = None
    normalization = {
        "raw_gwp_value": indicator.value if indicator else None,
        "raw_gwp_unit": indicator.unit if indicator else None,
        "raw_gwp_unit_uuid": str(indicator.unit_uuid) if indicator else None,
        "raw_gwp_unit_version": indicator.unit_version if indicator else None,
        "declared_quantity": profile.declared_amount,
        "declared_unit": profile.declared_unit,
        "normalized_factor_value": str(normalized) if normalized is not None else None,
        "normalized_input_unit": input_unit,
        "normalized_result_unit": "kgCO2e" if normalized is not None else None,
        "standard": profile.standard,
        "boundary": "A1-A3",
        "indicator": code,
        "indicator_id": indicator.pk if indicator else None,
        "indicator_uuid": str(indicator.upstream_uuid) if indicator else None,
        "indicator_version": indicator.upstream_version if indicator else None,
        "version_value": str(stored) if stored is not None else None,
        "division_precision": 80,
        "version_rounding": "ROUND_HALF_EVEN; 10 decimal places",
    }
    functional = {
        "classification": process.classification,
        "dataset_type": process.dataset_type_raw or "unknown",
        "location": process.location_raw or "unknown",
        "owner_manufacturer": process.owner_raw or "unknown",
        "description": process.name,
        "declared_unit": profile.declared_unit,
        "standard": profile.standard,
        "compliance": {
            "standard": process.compliance_standard_raw,
            "source_uuid": process.compliance_source_uuid,
        },
        "intended_use": "unknown",
        "technical_properties": "unknown",
        "functional_equivalence": "unknown",
        "comparison_status": "requires_review",
    }
    return {
        "compatible": not reasons,
        "source_current": current,
        "reasons": list(dict.fromkeys(reasons)),
        "normalization": normalization,
        "provenance": provenance,
        "functional_context": functional,
    }


@transaction.atomic
def build_material_candidate(profile_id):
    profile = OekobaudatEnvironmentalProfileFact.objects.select_for_update().get(
        pk=profile_id
    )
    evaluation = evaluate_material_profile(profile)
    with governed_write():
        candidate, created = Candidate.objects.get_or_create(
            source_profile=profile,
            defaults={
                "source_indicator_id": evaluation["normalization"]["indicator_id"],
                "status": (
                    Candidate.Status.REVIEW
                    if evaluation["compatible"]
                    else Candidate.Status.DETECTED
                ),
                "normalization": evaluation["normalization"],
                "provenance": evaluation["provenance"],
                "functional_context": evaluation["functional_context"],
                "initial_eligibility": {
                    k: evaluation[k]
                    for k in ("compatible", "source_current", "reasons")
                },
            },
        )
    return candidate, created, evaluation


def build_material_candidates(**filters):
    summary = dict.fromkeys(
        [
            "profiles_seen",
            "eligible",
            "ineligible",
            "created",
            "existing",
            "a1",
            "a2",
            "missing_gwp",
            "unsupported_unit",
            "requires_review",
        ],
        0,
    )
    for pk in (
        OekobaudatEnvironmentalProfileFact.objects.filter(**filters)
        .order_by("pk")
        .values_list("pk", flat=True)
        .iterator()
    ):
        candidate, created, result = build_material_candidate(pk)
        summary["profiles_seen"] += 1
        summary["created" if created else "existing"] += 1
        summary["eligible" if result["compatible"] else "ineligible"] += 1
        for label in ("a1", "a2"):
            summary[label] += (
                result["normalization"]["standard"] == "EN 15804+" + label.upper()
            )
        for reason in ("missing_gwp", "unsupported_unit"):
            summary[reason] += reason in result["reasons"]
        summary["requires_review"] += candidate.status == Candidate.Status.REVIEW
    return summary


def _lock_source(candidate):
    # Synchronization enters SYNCING under this same lock before publication.
    source_id = candidate.source_profile.snapshot.source_id
    EnvironmentalSource.objects.select_for_update().get(pk=source_id)
    SourceState.objects.select_for_update().get(source_id=source_id)


def _eligible(candidate):
    result = evaluate_material_profile(candidate.source_profile)
    if not result["compatible"]:
        raise ValidationError({"eligibility": result["reasons"]})
    if candidate.source_indicator_id != result["normalization"]["indicator_id"]:
        raise ValidationError("El indicador del candidato no corresponde al perfil.")
    if any(
        getattr(candidate, key) != result[key]
        for key in ("normalization", "provenance", "functional_context")
    ):
        raise ValidationError(
            "La evidencia del candidato cambió; requiere investigación."
        )
    return result


@transaction.atomic
def review_material_candidate(candidate_id, user, decision, note="", context=None):
    require_global_reviewer(user)
    context = {} if context is None else context
    if (
        decision not in {"approved", "rejected"}
        or not isinstance(note, str)
        or not isinstance(context, dict)
    ):
        raise ValidationError("Revisión inválida.")
    if set(context) - {"intended_use", "mapping_note"} or any(
        not isinstance(v, str) or len(v) > 2000 for v in context.values()
    ):
        raise ValidationError(
            "Contexto permitido: intended_use y mapping_note textuales; no equivalencia funcional."
        )
    candidate = Candidate.objects.select_for_update().get(pk=candidate_id)
    if candidate.status == Candidate.Status.PROMOTED:
        raise ValidationError("El candidato promovido es inmutable.")
    _lock_source(candidate)
    result = (
        _eligible(candidate)
        if decision == "approved"
        else evaluate_material_profile(candidate.source_profile)
    )
    with governed_write():
        Review.objects.create(
            candidate=candidate,
            decision=decision,
            reviewer=user,
            note=note,
            context=context,
            eligibility=result,
        )
        candidate.status = (
            Candidate.Status.READY
            if decision == "approved"
            else Candidate.Status.REJECTED
        )
        candidate.save(update_fields=["status"])
    return candidate


@transaction.atomic
def promote_material_candidate(candidate_id, user):
    require_global_reviewer(user)
    candidate = Candidate.objects.select_for_update().get(pk=candidate_id)
    if candidate.status == Candidate.Status.PROMOTED:
        raise ValidationError("El candidato ya fue promovido.")
    _lock_source(candidate)
    result = _eligible(candidate)
    review = candidate.reviews.order_by("-pk").first()
    if (
        candidate.status != Candidate.Status.READY
        or not review
        or review.decision != "approved"
    ):
        raise ValidationError("Se requiere aprobación humana explícita.")
    normalized = result["normalization"]
    context = {
        "provider": "ÖKOBAUDAT",
        "domain": "materials",
        "source_candidate_id": candidate.pk,
        **normalized,
        "process_uuid": candidate.provenance["process_uuid"],
        "dataset_version": candidate.provenance["dataset_version"],
        "location": candidate.functional_context["location"],
        "classification": candidate.functional_context["classification"],
        "functional_context": candidate.functional_context,
        "human_context": review.context,
        "review_id": review.pk,
        "knowledge_source": candidate.provenance,
    }
    factor = FactorAmbiental.objects.create(
        organizacion=None,
        codigo=f"obd-material-{candidate.pk}",
        nombre=f"ÖKOBAUDAT · {candidate.source_profile.process.name}"[:200],
        categoria="materiales_a1a3",
        sustancia_impacto="CO2e",
        unidad_entrada=normalized["normalized_input_unit"],
        unidad_resultado="kgCO2e",
        contexto=context,
    )
    version = VersionFactorAmbiental.objects.create(
        factor=factor,
        version=1,
        valor=Decimal(normalized["version_value"]),
        fuente="ÖKOBAUDAT",
        referencia=candidate.provenance["source_url"],
        region=context["location"][:100],
        contexto=context,
        estado=VersionFactorAmbiental.Estado.BORRADOR,
    )
    with governed_write():
        candidate.status = Candidate.Status.PROMOTED
        candidate.promoted_factor = factor
        candidate.promoted_version = version
        candidate.promoted_by = user
        candidate.promoted_at = timezone.now()
        candidate.save()
    return factor, version
