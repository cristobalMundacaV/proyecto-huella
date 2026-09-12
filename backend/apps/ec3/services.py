from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.analytics.models import FactorAmbiental, MaterialOperacional, VersionFactorAmbiental
from apps.analytics.permissions import Permission, require_tenant_permission
from apps.analytics.services.material_factor_mapping import propose_material_mapping
from apps.knowledge.models import EnvironmentalSource, ExternalRecord, ExternalSnapshot, SourceState, SyncRun

from .client import Ec3Client, UpstreamError
from .conf import ATTRIBUTION, BASE_URL, enabled, require_storage, storage_allowed
from .models import Candidate, EpdVersion, Review
from .rate_limit import RateLimited
from .schemas import checksum, external_id, normalize, timestamp


def require_reviewer(user):
    enabled()
    if not user or not user.is_active or not user.is_superuser:
        raise PermissionDenied("La gobernanza de evidencia EC3 requiere superusuario activo.")


def source_registry():
    # Explicit registration only on ingestion, never during application startup.
    source, _ = EnvironmentalSource.objects.get_or_create(codigo="ec3-openepd", defaults={
        "nombre": "EC3 / openEPD", "organismo": "Building Transparency", "connector_key": "ec3_openepd",
        "tipo_acceso": "REST", "base_url": BASE_URL, "nivel_autoridad": "fuente_externa_autoritativa",
        "documentation_url": "https://docs.open-epd-forum.org/en/rest-api/",
        "licencia_nombre": "Acuerdo EC3 Pilot; derechos configurados por operador",
        "licencia_url": "https://www.buildingtransparency.org/api-access-pricing/",
        "atribucion_requerida": True, "permite_poll_automatico": False,
        "cadencia_sugerida": "dirigida_por_id", "stale_after_hours": 168,
    })
    if source.connector_key != "ec3_openepd" or source.base_url != BASE_URL or not source.activa:
        raise ValidationError("Registro de fuente EC3 incompatible o deshabilitado.")
    SourceState.objects.get_or_create(source=source)
    return source


def ingest_epd(epd_id, user, *, client=None):
    require_reviewer(user)
    require_storage()
    epd_id = external_id(epd_id)
    source = source_registry()
    run = SyncRun.objects.create(source=source, trigger="manual", started_at=timezone.now(),
                                 snapshot_autoritativo=False, metadata={"integration": "EC3-01", "external_id": epd_id, "actor_id": user.pk})
    owned = client is None
    client = client or Ec3Client()
    try:
        # Always revalidate ingestion against upstream, never make a cached search authoritative.
        result = client.detail(epd_id, refresh=True)
        with transaction.atomic():
            source = EnvironmentalSource.objects.select_for_update().get(pk=source.pk)
            if not source.activa:
                raise ValidationError("Fuente EC3 deshabilitada durante ingestión.")
            require_storage()
            evidence = result["data"]
            retrieved = timestamp(result["retrieved_at"])
            snapshot, _ = ExternalSnapshot.objects.get_or_create(
                source=source, external_id=epd_id, content_hash=result["payload_checksum"],
                defaults={"sync_run": run, "record_kind": "ec3_epd", "source_url": result["source_url"],
                          "retrieved_at": retrieved, "raw_payload": None,
                          "content_type": "application/json", "metadata": {
                              "projection_checksum": checksum(evidence), "upstream_version": evidence["version"],
                              "checksum_algorithm": result["checksum_algorithm"], "storage": "minimal_projection_only"}},
            )
            record, new_record = ExternalRecord.objects.get_or_create(source=source, external_id=epd_id, defaults={
                "kind": "ec3_epd", "title": evidence["product_name"], "source_url": result["source_url"],
                "current_snapshot": snapshot, "first_seen_at": retrieved, "last_seen_at": retrieved})
            previous = record.ec3_versions.order_by("-local_version").first()
            current = record.ec3_versions.filter(pk=record.metadata.get("ec3_current_version_id")).first()
            new_version = not (current and current.snapshot_id == snapshot.pk)
            if current and current.snapshot_id == snapshot.pk:
                epd_version = current
            else:
                # A -> B -> A is a NEW local observation, never resurrection of A's approval.
                epd_version = EpdVersion.objects.create(snapshot=snapshot,
                    record=record, upstream_version=evidence["version"],
                    local_version=previous.local_version + 1 if previous else 1,
                    evidence=evidence, evidence_checksum=checksum(evidence), retrieved_at=retrieved,
                    rights_reference=settings.EC3_RIGHTS_REFERENCE)
            # Two overlapping HTTP calls must not publish an older observation last.
            if retrieved >= record.last_seen_at:
                record.current_snapshot = snapshot
                record.last_seen_at = retrieved
                record.title = evidence["product_name"]
                record.estado = ExternalRecord.Status.ACTIVE
                record.metadata = {**record.metadata, "ec3_current_version_id": epd_version.pk, "ec3_validation_failed": False}
                record.save(update_fields=["current_snapshot", "last_seen_at", "title", "estado", "metadata"])
            run.estado = "actualizada" if new_version else "sin_cambios"
            run.received = 1
            run.created = int(new_record)
            run.modified = int(new_version and not new_record)
            run.unchanged = int(not new_version)
            run.finished_at = timezone.now()
            run.save()
            state = SourceState.objects.select_for_update().get(source=source)
            if not state.retrieved_at or retrieved >= state.retrieved_at:
                state.estado = run.estado
                state.last_attempt_at = run.started_at
                state.last_successful_sync_at = run.finished_at
                state.retrieved_at = retrieved
                state.last_checksum = result["payload_checksum"]
                state.upstream_version = str(evidence["version"]) if evidence["version"] is not None else ""
                state.last_error = ""
                state.metadata = {"sync_scope": "targeted_epd", "external_id": epd_id, "sync_run_id": run.pk,
                                  "authoritative_full_snapshot": False}
                state.save()
        return epd_version
    except Exception as exc:
        # A failed subset request is not evidence of withdrawal or catalog disappearance.
        run.refresh_from_db()
        if run.finished_at is None:
            run.estado = "error"
            run.errors = 1
            run.message = (exc.code if isinstance(exc, UpstreamError)
                          else "ec3_rate_limited" if isinstance(exc, RateLimited) else "ec3_ingestion_failed")
            run.finished_at = timezone.now()
            run.save()
            with transaction.atomic():
                EnvironmentalSource.objects.select_for_update().get(pk=source.pk)
                state = SourceState.objects.select_for_update().get(source=source)
                if not state.last_attempt_at or run.started_at >= state.last_attempt_at:
                    state.estado = "error"
                    state.last_attempt_at = run.started_at
                    state.last_error = run.message
                    state.save(update_fields=["estado", "last_attempt_at", "last_error"])
                if isinstance(exc, UpstreamError):
                    record = ExternalRecord.objects.filter(source=source, external_id=epd_id).first()
                    if record and record.last_seen_at <= run.started_at:
                        record.metadata = {**record.metadata, "ec3_validation_failed": True}
                        record.save(update_fields=["metadata"])
        raise
    finally:
        if owned:
            client.close()


def provenance(version):
    return {"source": "EC3 / Building Transparency", "external_id": version.snapshot.external_id,
            "epd": version.evidence.get("declaration_url"), "source_url": version.snapshot.source_url,
            "upstream_version": version.upstream_version, "local_version": version.local_version,
            "retrieved_at": version.retrieved_at.isoformat(),
            "checksum": version.snapshot.content_hash, "checksum_algorithm": "sha256/http-decoded-body",
            "projection_checksum": version.evidence_checksum, "snapshot_id": version.snapshot_id,
            "epd_version_id": version.pk, "declared_unit": version.evidence.get("declared_unit"),
            "lifecycle_scope": "A1-A3" if any(v.get("gwp", {}).get("A1A2A3") for v in version.evidence.get("impacts", {}).values()) else None,
            "quality": {key: version.evidence.get(key) for key in (
                "product_name", "manufacturer", "compliance", "program_operator", "program_operator_doc_id",
                "program_operator_version", "openepd_version", "pcr", "third_party_verifier",
                "third_party_verification_url", "ec3", "applicable_in", "date_of_issue", "valid_until",
                "product_usage_description")},
            "attribution": ATTRIBUTION}


def evaluate_version(version, method, *, now=None):
    now = now or timezone.now()
    result = normalize(version.evidence, method)
    reasons = list(result["reasons"])
    record = ExternalRecord.objects.select_related("source").get(pk=version.record_id)
    evidence = version.evidence
    if not getattr(settings, "EC3_ENABLED", False):
        reasons.append("ec3_disabled")
    if not storage_allowed():
        reasons.append("ec3_data_rights_not_current")
    if not record.source.activa or record.estado != ExternalRecord.Status.ACTIVE:
        reasons.append("source_unavailable")
    if record.metadata.get("ec3_validation_failed"):
        reasons.append("source_revalidation_failed")
    if record.current_snapshot_id != version.snapshot_id or record.metadata.get("ec3_current_version_id") != version.pk:
        reasons.append("source_version_changed")
    maximum_age = min(max(1, settings.EC3_EVIDENCE_MAX_AGE_HOURS), record.source.stale_after_hours)
    if record.last_seen_at < now - timedelta(hours=maximum_age):
        reasons.append("source_stale")
    if checksum(evidence) != version.evidence_checksum or version.snapshot.metadata.get("projection_checksum") != version.evidence_checksum:
        reasons.append("evidence_integrity_failure")
    if version.upstream_version is None:
        reasons.append("missing_upstream_version")
    if evidence.get("private") is not False or evidence.get("doctype") != "OpenEPD":
        reasons.append("publication_not_explicit")
    for field in ("declaration_url", "date_of_issue", "valid_until", "program_operator", "pcr", "compliance", "third_party_verifier"):
        if not evidence.get(field):
            reasons.append("missing_" + field)
    if evidence.get("date_of_issue") and timestamp(evidence["date_of_issue"]) > now:
        reasons.append("epd_not_yet_valid")
    if evidence.get("valid_until") and timestamp(evidence["valid_until"]) < now:
        reasons.append("epd_expired")
    return {**result, "compatible": not reasons, "reasons": reasons, "human_applicability_required": True}


@transaction.atomic
def propose_candidate(material, version, user):
    require_reviewer(user)
    require_storage()
    require_tenant_permission(user, material.organizacion, Permission.MATERIAL_MAPPING_PROPOSE)
    material = MaterialOperacional.objects.select_for_update().get(pk=material.pk)
    return Candidate.objects.get_or_create(material=material, epd_version=version, defaults={"created_by": user})[0]


@transaction.atomic
def review_candidate(candidate_id, user, decision, method, context):
    require_reviewer(user)
    require_storage()
    if decision not in {"approved", "rejected"} or not isinstance(method, str) or len(method) > 80:
        raise ValidationError("Revisión EC3 inválida.")
    fields = {"technical_basis", "geographic_basis", "temporal_basis", "standard_basis", "verification_basis", "note"}
    if not isinstance(context, dict) or set(context) != fields or any(not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in context.values()):
        raise ValidationError("La revisión humana requiere technical_basis, geographic_basis, temporal_basis, standard_basis, verification_basis y note.")
    candidate = Candidate.objects.select_for_update().select_related("epd_version", "material__organizacion").get(pk=candidate_id)
    require_tenant_permission(user, candidate.material.organizacion, Permission.MATERIAL_MAPPING_APPROVE)
    if candidate.promoted_version_id:
        raise ValidationError("Candidato promovido congelado; revoque el mapping existente para retirar su aplicación.")
    EnvironmentalSource.objects.select_for_update().get(pk=candidate.epd_version.snapshot.source_id)
    evaluation = evaluate_version(candidate.epd_version, method)
    if decision == "approved" and not evaluation["compatible"]:
        raise ValidationError({"eligibility": evaluation["reasons"]})
    Review.objects.create(candidate=candidate, actor=user, decision=decision, lcia_method=method,
                          context=context, evaluation=evaluation)
    return candidate


@transaction.atomic
def promote_candidate(candidate_id, user):
    require_reviewer(user)
    require_storage()
    candidate = Candidate.objects.select_for_update().select_related("epd_version", "material__organizacion").get(pk=candidate_id)
    if candidate.promoted_version_id:
        raise ValidationError("El candidato ya fue promovido.")
    EnvironmentalSource.objects.select_for_update().get(pk=candidate.epd_version.snapshot.source_id)
    review = candidate.reviews.order_by("-pk").first()
    if not review or review.decision != "approved":
        raise ValidationError("Se requiere revisión humana aprobada.")
    evaluation = evaluate_version(candidate.epd_version, review.lcia_method)
    if not evaluation["compatible"]:
        raise ValidationError({"eligibility": evaluation["reasons"]})
    context = {"provider": "EC3", "ec3_candidate_id": candidate.pk, "review_id": review.pk,
               "knowledge_source": provenance(candidate.epd_version), "normalization": evaluation,
               "human_context": review.context, "alcance_ciclo_vida": "A1-A3", "fuente_tipo": "epd"}
    factor = FactorAmbiental.objects.create(organizacion=candidate.material.organizacion,
        codigo=f"ec3-material-{candidate.pk}", nombre=f"EC3 · {candidate.epd_version.evidence['product_name']}"[:200],
        categoria="materiales_a1a3", sustancia_impacto="CO2e", unidad_entrada=evaluation["input_unit"],
        unidad_resultado="kgCO2e", contexto=context)
    evidence = candidate.epd_version.evidence
    version = VersionFactorAmbiental.objects.create(factor=factor, version=1,
        valor=Decimal(evaluation["version_value"]), fuente="EC3 / Building Transparency",
        referencia=candidate.epd_version.snapshot.source_url, contexto=context,
        vigencia_desde=timestamp(evidence["date_of_issue"]).date(), vigencia_hasta=timestamp(evidence["valid_until"]).date(),
        estado=VersionFactorAmbiental.Estado.BORRADOR)
    candidate.promoted_version = version
    candidate.save(update_fields=["promoted_version"])
    return candidate


@transaction.atomic
def propose_mapping(candidate_id, user, start, end=None):
    require_reviewer(user)
    candidate = Candidate.objects.select_for_update(of=("self",)).select_related("material__organizacion", "promoted_version__factor", "epd_version").get(pk=candidate_id)
    if not candidate.promoted_version_id or candidate.mapping_id:
        raise ValidationError("Requiere factor promovido y sin mapping previo.")
    EnvironmentalSource.objects.select_for_update().get(pk=candidate.epd_version.snapshot.source_id)
    review = candidate.reviews.order_by("-pk").first()
    evaluation = evaluate_version(candidate.epd_version, review.lcia_method)
    if not evaluation["compatible"]:
        raise ValidationError({"eligibility": evaluation["reasons"]})
    candidate.mapping = propose_material_mapping(candidate.material.organizacion, candidate.material,
        candidate.promoted_version.factor, start, end, user,
        contexto={"technical_basis": review.context["technical_basis"], "review_note": f"EC3 review {review.pk}"})
    candidate.save(update_fields=["mapping"])
    return candidate


def candidate_data(candidate):
    review = candidate.reviews.order_by("-pk").first()
    evaluation = evaluate_version(candidate.epd_version, review.lcia_method if review else "")
    status = "CANDIDATES_FOUND"
    if review:
        status = "REJECTED" if review.decision == "rejected" else "REVIEW_REQUIRED"
    stale_reasons = {"source_version_changed", "source_stale", "epd_expired", "source_unavailable", "source_revalidation_failed", "ec3_data_rights_not_current", "ec3_disabled"}
    if stale_reasons.intersection(evaluation["reasons"]):
        status = "STALE"
    elif candidate.mapping_id:
        state = candidate.mapping.estado
        if state in {"rechazado", "revocado", "reemplazado"}:
            status = "REJECTED"
        elif state == "aprobado" and candidate.promoted_version.estado == "activo" and evaluation["compatible"]:
            status = "MAPPED"
    return {"id": candidate.pk, "material_id": candidate.material_id,
            "organization_id": candidate.material.organizacion_id, "status": status,
            "provenance": provenance(candidate.epd_version), "eligibility": evaluation,
            "factor_version_id": candidate.promoted_version_id, "mapping_id": candidate.mapping_id,
            "reviews": [{"id": r.pk, "actor_id": r.actor_id, "decision": r.decision, "lcia_method": r.lcia_method,
                         "context": r.context, "evaluation": r.evaluation, "created_at": r.created_at} for r in candidate.reviews.order_by("pk")],
            "recommendation_contract": {"version": "EC3-01/v1", "material_id": candidate.material_id,
                "candidate_id": candidate.pk, "epd_version_id": candidate.epd_version_id,
                "hotspot": None, "technical_comparability": "requires_separate_assessment",
                "potential_reduction": None, "ai_may_confirm": False}}


def factor_block_reason(version, mapping):
    """Called by the existing selector: source data never chooses its own application."""
    candidate = Candidate.objects.filter(promoted_version=version).select_related("epd_version", "material").first()
    if not candidate or candidate.material_id != mapping.material_id or candidate.mapping_id != mapping.pk:
        return "Factor EC3 sin candidato/mapping trazable."
    review = candidate.reviews.order_by("-pk").first()
    if not review or review.decision != "approved":
        return "Factor EC3 sin revisión humana aprobada."
    evaluation = evaluate_version(candidate.epd_version, review.lcia_method)
    if not evaluation["compatible"]:
        return "EC3: " + ", ".join(evaluation["reasons"])
    if (version.valor != Decimal(evaluation["version_value"])
            or version.factor.unidad_entrada != evaluation["input_unit"]
            or version.factor.unidad_resultado != "kgCO2e"
            or version.contexto.get("knowledge_source") != provenance(candidate.epd_version)
            or version.contexto.get("review_id") != review.pk):
        return "Integridad de factor/provenance EC3 inválida."
    return None
