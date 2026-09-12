"""SOURCE-WATCH-01C — normalized change observation.

Reconstructs, purely on read, exactly what one completed `SyncRun`
observed — no second snapshot store, no new mutable "change" model.
`ExternalSnapshot` already IS the durable, content-addressed evidence of
"created" vs "changed" vs "unchanged" (a new snapshot row for an
already-known `external_id` is a change; the absence of one is
"unchanged"; a first-ever snapshot is "created"). The only two facts that
were not durably reconstructable from the pre-existing schema — whether a
run's own batch was an authoritative full observation, and which run
specifically first observed each disappearance — are now carried by two
minimal fields (`SyncRun.snapshot_autoritativo`, `ExternalRecord.missing_since_run`)
rather than a parallel change-event ledger.

Never marks a record `disappeared` for a non-authoritative run: an
incremental/partial batch not mentioning a record proves nothing about
that record's continued existence upstream.
"""

from .models import ExternalRecord, ExternalSnapshot, SyncRun

CREATED = "created"
CHANGED = "changed"
UNCHANGED = "unchanged"
DISAPPEARED = "disappeared"
REAPPEARED = "reappeared"
UNKNOWN = "unknown"


def _was_created(snapshot):
    """A snapshot is a "created" event when no earlier snapshot exists for
    the same (source, external_id) — never guessed, always a real query
    against the immutable snapshot history."""
    return not ExternalSnapshot.objects.filter(
        source_id=snapshot.source_id, external_id=snapshot.external_id,
    ).exclude(pk=snapshot.pk).filter(retrieved_at__lt=snapshot.retrieved_at).exists()


def observe_sync_run(run):
    """Idempotent: re-analyzing the same finished run always reconstructs
    the identical event list from the same immutable evidence — nothing is
    created or mutated by calling this."""

    if run.finished_at is None:
        return {
            "run_id": run.pk, "source_id": run.source_id, "authoritative": None,
            "events": [], "reason": "run_not_finished",
        }

    new_snapshots = ExternalSnapshot.objects.filter(sync_run=run).order_by("external_id")
    events = []
    changed_or_created_ids = set()

    for snapshot in new_snapshots:
        changed_or_created_ids.add(snapshot.external_id)
        classification = CREATED if _was_created(snapshot) else CHANGED
        events.append({
            "external_id": snapshot.external_id,
            "classification": classification,
            "snapshot_id": snapshot.pk,
            "content_hash": snapshot.content_hash,
            "retrieved_at": snapshot.retrieved_at,
        })

    # Unchanged: seen in this exact run (same `now` timestamp persisted as
    # both the run's finish time and the record's last_seen_at) but with no
    # new snapshot — i.e. the content hash matched an existing one.
    unchanged_records = ExternalRecord.objects.filter(
        source=run.source, last_seen_at=run.finished_at,
    ).exclude(external_id__in=changed_or_created_ids)
    for record in unchanged_records:
        events.append({
            "external_id": record.external_id,
            "classification": UNCHANGED,
            "snapshot_id": record.current_snapshot_id,
            "content_hash": record.current_snapshot.content_hash,
            "retrieved_at": record.last_seen_at,
        })

    if run.snapshot_autoritativo:
        for record in ExternalRecord.objects.filter(missing_since_run=run):
            events.append({
                "external_id": record.external_id,
                "classification": DISAPPEARED,
                "snapshot_id": record.current_snapshot_id,
                "content_hash": None,
                "retrieved_at": run.finished_at,
            })

    # Reappearance: `reappeared_via_run` is set (services.sync_environmental_source)
    # exactly when a record's estado flips from MISSING back to ACTIVE —
    # durable, unambiguous, no inference needed.
    for record in ExternalRecord.objects.filter(source=run.source, reappeared_via_run=run):
        events.append({
            "external_id": record.external_id,
            "classification": REAPPEARED,
            "snapshot_id": record.current_snapshot_id,
            "content_hash": record.current_snapshot.content_hash,
            "retrieved_at": record.last_seen_at,
        })

    previous_run = (
        SyncRun.objects.filter(source_id=run.source_id, finished_at__isnull=False, pk__lt=run.pk)
        .order_by("-pk")
        .first()
    )
    source_metadata_changed = bool(
        previous_run and run.upstream_version and previous_run.upstream_version != run.upstream_version
    )

    return {
        "run_id": run.pk,
        "source_id": run.source_id,
        "authoritative": run.snapshot_autoritativo,
        "events": events,
        "source_metadata_changed": source_metadata_changed,
        "reason": None,
    }
