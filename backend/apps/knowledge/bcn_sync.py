from datetime import date

from django.db import transaction
from django.utils import timezone

from .models import (
    BcnLegalNormFact,
    BcnLegalNormRelationFact,
    BcnLegalNormVersionFact,
    EnvironmentalSource,
    ExternalRecord,
    SourceState,
    SyncRun,
)
from .services import sanitized_error, sync_environmental_source


def _date(value):
    return date.fromisoformat(value[:10]) if value else None


def sync_bcn_legal_norms():
    source = EnvironmentalSource.objects.get(codigo="bcn-leychile")
    previous_current = dict(
        source.records.values_list("external_id", "current_snapshot_id")
    )
    run = sync_environmental_source(source)
    if run.estado == "error":
        return run
    try:
        with transaction.atomic():
            for record in source.records.filter(estado="activo").select_related(
                "current_snapshot"
            ):
                snapshot = record.current_snapshot
                if BcnLegalNormFact.objects.filter(snapshot=snapshot).exists():
                    continue
                p = snapshot.raw_payload
                versions = p.get("versions") or []
                if sum(bool(v.get("is_latest")) for v in versions) != 1:
                    raise ValueError(f"{record.external_id}: latest version inválida.")
                fact = BcnLegalNormFact.objects.create(
                    snapshot=snapshot,
                    norm_uri=p["norm_uri"],
                    identifier=p.get("identifier", ""),
                    number=p["number"],
                    title=p["title"],
                    norm_type_uri=p["norm_type_uri"],
                    norm_type_name=p["norm_type_name"],
                    issuer_uri=p.get("issuer_uri", ""),
                    issuer_name=p.get("issuer_name", ""),
                    publish_date=_date(p.get("publish_date")),
                    promulgation_date=_date(p.get("promulgation_date")),
                    latest_version_uri=p["latest_version_uri"],
                    latest_version_date=_date(p.get("latest_version_date")),
                    scope_tags=p.get("scope_tags", []),
                )
                BcnLegalNormVersionFact.objects.bulk_create(
                    [
                        BcnLegalNormVersionFact(
                            norm_fact=fact,
                            version_uri=v["version_uri"],
                            version_date=_date(v.get("version_date")),
                            is_latest=bool(v.get("is_latest")),
                            xml_document_url=v.get("xml_document_url", ""),
                            html_document_url=v.get("html_document_url", ""),
                        )
                        for v in versions
                    ]
                )
                unique = {
                    (r["relation_type"], r["target_uri"]): r
                    for r in p.get("relations", [])
                }
                BcnLegalNormRelationFact.objects.bulk_create(
                    [
                        BcnLegalNormRelationFact(
                            norm_fact=fact,
                            relation_type=r["relation_type"],
                            target_uri=r["target_uri"],
                            target_number=r.get("target_number", ""),
                            target_title=r.get("target_title", ""),
                        )
                        for r in unique.values()
                    ]
                )
            state = SourceState.objects.select_for_update().get(source=source)
            metadata = dict(state.metadata or {})
            metadata.update(
                {
                    "last_materialized_success_at": timezone.now().isoformat(),
                    "materialization_status": "success",
                }
            )
            state.metadata = metadata
            state.save(update_fields=["metadata", "updated_at"])
    except Exception as exc:
        message = sanitized_error(exc)
        now = timezone.now()
        with transaction.atomic():
            records = ExternalRecord.objects.select_for_update().filter(source=source)
            for record in records:
                previous_id = previous_current.get(record.external_id)
                if previous_id is not None:
                    record.current_snapshot_id = previous_id
                    record.save(update_fields=["current_snapshot"])
            state = SourceState.objects.select_for_update().get(source=source)
            metadata = dict(state.metadata or {})
            metadata["materialization_status"] = "partial"
            state.estado = SourceState.Status.PARTIAL
            state.last_error = message
            state.metadata = metadata
            state.save(update_fields=["estado", "last_error", "metadata", "updated_at"])
            SyncRun.objects.filter(pk=run.pk).update(
                estado=SourceState.Status.PARTIAL,
                errors=1,
                message=message,
                finished_at=now,
            )
        return SyncRun.objects.get(pk=run.pk)
    return run
