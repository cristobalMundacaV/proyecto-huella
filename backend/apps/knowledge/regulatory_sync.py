from datetime import date

from django.db import transaction
from django.utils import timezone

from .models import ExternalRecord, SourceState, SyncRun
from .services import sanitized_error, sync_environmental_source


def parsed_date(value):
    return date.fromisoformat(str(value)[:10]) if value else None


def sync_and_materialize(source, materialize):
    previous = dict(source.records.values_list("external_id", "current_snapshot_id"))
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
            for record in ExternalRecord.objects.select_for_update().filter(source=source):
                old = previous.get(record.external_id)
                if old is not None:
                    record.current_snapshot_id = old; record.save(update_fields=["current_snapshot"])
            state = SourceState.objects.select_for_update().get(source=source); metadata = dict(state.metadata or {}); metadata["materialization_status"] = "partial"
            state.estado = SourceState.Status.PARTIAL; state.last_error = message; state.metadata = metadata; state.save(update_fields=["estado", "last_error", "metadata", "updated_at"])
            SyncRun.objects.filter(pk=run.pk).update(estado=SourceState.Status.PARTIAL, errors=1, message=message, finished_at=timezone.now())
        return SyncRun.objects.get(pk=run.pk)
    return run
