from django.db import transaction
from django.utils import timezone

from .models import ExternalRecord, SourceState, SyncRun
from .services import sanitized_error, sync_environmental_source


RECORD_PUBLICATION_FIELDS = (
    "current_snapshot_id", "kind", "canonical_key", "title", "source_url",
    "published_at", "upstream_updated_at", "estado", "metadata", "last_seen_at",
)


def _published_records(source):
    return {
        row["external_id"]: row
        for row in source.records.values("external_id", *RECORD_PUBLICATION_FIELDS)
    }


def sync_and_materialize(source, materialize):
    previous = _published_records(source)
    run = sync_environmental_source(source)
    if run.estado == "error": return run
    try:
        with transaction.atomic():
            records = source.records.filter(estado="activo").select_related("current_snapshot")
            for record in records: materialize(record.current_snapshot)
            state = SourceState.objects.select_for_update().get(source=source)
            metadata = dict(state.metadata or {}); metadata.update({"last_materialized_success_at": timezone.now().isoformat(), "materialization_status": "success"})
            state.metadata = metadata; state.save(update_fields=["metadata", "updated_at"])
    except Exception as exc:
        message = sanitized_error(exc)
        with transaction.atomic():
            records = list(ExternalRecord.objects.select_for_update().filter(source=source))
            for record in records:
                old = previous.get(record.external_id)
                if old is None:
                    # The observed snapshot belongs to the immutable sync history,
                    # but a first failed materialization is not published as current.
                    record.delete()
                    continue
                for field in RECORD_PUBLICATION_FIELDS:
                    setattr(record, field, old[field])
                record.save(update_fields=list(RECORD_PUBLICATION_FIELDS))
            state = SourceState.objects.select_for_update().get(source=source); metadata = dict(state.metadata or {}); metadata["materialization_status"] = "partial"
            state.estado = SourceState.Status.PARTIAL; state.last_error = message; state.metadata = metadata; state.save(update_fields=["estado", "last_error", "metadata", "updated_at"])
            SyncRun.objects.filter(pk=run.pk).update(estado=SourceState.Status.PARTIAL, errors=1, message=message, finished_at=timezone.now())
        return SyncRun.objects.get(pk=run.pk)
    return run
