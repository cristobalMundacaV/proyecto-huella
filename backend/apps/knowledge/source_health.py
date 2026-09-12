"""SOURCE-WATCH-01B — source health & freshness authority.

Reuses `services.source_freshness()` for the core state string (never a
second truth for freshness) and adds the structured envelope the mission
requires: timestamps, sanitized last error, and — critically — an explicit
`last_known_good_available` flag so a source that is currently unhealthy
never gets silently reported as if it had no usable data, and never gets
silently reported as healthy either.
"""

from datetime import timedelta

from django.utils import timezone

from .models import ExternalRecord, SourceState, SyncRun
from .services import source_freshness

# The mission's required vocabulary, mapped onto this repo's existing
# Spanish state strings (never renamed — see `source_freshness()`).
HEALTHY = {"actualizada", "sin_cambios", "actualizado"}
NEAR_STALE = {"proximo_a_vencer"}
STALE = {"desactualizado"}
SYNCING = {"sincronizando"}
PARTIAL_WITH_VERSION = {"parcial_con_ultima_version_disponible"}
PARTIAL_WITHOUT_VERSION = {"parcial_sin_version_publicada"}
ERROR_WITH_VERSION = {"error_con_ultima_version_disponible"}
ERROR_WITHOUT_VERSION = {"error_sin_version_disponible"}
NEVER_SYNCED = {"nunca_sincronizado"}
INACTIVE = {"inactiva"}


def _bucket(freshness):
    for bucket, values in (
        ("healthy", HEALTHY), ("near_stale", NEAR_STALE), ("stale", STALE),
        ("syncing", SYNCING), ("partial_with_last_version", PARTIAL_WITH_VERSION),
        ("partial_without_version", PARTIAL_WITHOUT_VERSION),
        ("error_with_last_version", ERROR_WITH_VERSION),
        ("error_without_version", ERROR_WITHOUT_VERSION),
        ("never_synced", NEVER_SYNCED), ("inactive", INACTIVE),
    ):
        if freshness in values:
            return bucket
    return "unknown"


def source_health(source, now=None):
    """The single explainable answer to "is this source healthy and
    fresh right now, and what is the last trustworthy version we have?"."""

    now = now or timezone.now()
    state = SourceState.objects.get(source=source)
    freshness = source_freshness(source, now=now)
    bucket = _bucket(freshness)

    last_known_good_available = ExternalRecord.objects.filter(source=source).exists()

    age_seconds = None
    next_boundary = None
    if state.last_successful_sync_at:
        age_seconds = (now - state.last_successful_sync_at).total_seconds()
        limit = timedelta(hours=source.stale_after_hours)
        next_boundary = state.last_successful_sync_at + limit

    last_run = (
        SyncRun.objects.filter(source=source, finished_at__isnull=False)
        .order_by("-finished_at")
        .first()
    )

    return {
        "source_id": source.pk,
        "codigo": source.codigo,
        "activa": source.activa,
        "freshness": freshness,
        "health_bucket": bucket,
        "last_attempt_at": state.last_attempt_at,
        "last_successful_sync_at": state.last_successful_sync_at,
        "retrieved_at": state.retrieved_at,
        "upstream_updated_at": state.upstream_updated_at,
        "upstream_version": state.upstream_version,
        "last_error": state.last_error,
        "stale_after_hours": source.stale_after_hours,
        "age_seconds": age_seconds,
        "next_freshness_boundary": next_boundary,
        "last_known_good_available": last_known_good_available,
        "last_run_summary": (
            {
                "id": last_run.pk,
                "trigger": last_run.trigger,
                "estado": last_run.estado,
                "started_at": last_run.started_at,
                "finished_at": last_run.finished_at,
                "received": last_run.received,
                "created": last_run.created,
                "modified": last_run.modified,
                "unchanged": last_run.unchanged,
                "disappeared": last_run.disappeared,
                "errors": last_run.errors,
            }
            if last_run
            else None
        ),
    }
