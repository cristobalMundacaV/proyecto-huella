"""SOURCE-WATCH-01G — resilient watch orchestration.

Watches multiple active sources safely, reusing each source's existing
sync command/service — never rewriting a connector into one giant
function. Failure isolation: one source's exception never blocks the
others (`continue_on_error`, default True). Concurrency safety is not
reimplemented here — `services._begin()`'s `select_for_update()` +
`SourceState.SYNCING` guard is still the single authority; a source
already syncing simply reports a graceful per-source failure instead of
blocking the cycle.

No retry loop lives here: bounding/backing off retries is a scheduler-level
concern (re-invoke on the source's own cadence), not something this
orchestrator invents. No stale-SYNCING lease/timeout recovery is
implemented either — there is no evidence yet of a stuck-SYNCING problem in
this codebase, and inventing a recovery contract without a real need would
risk silently un-blocking a genuinely still-running worker (see
ARQ-anti-overengineering: no speculative infrastructure)."""

from django.core.exceptions import ValidationError

from . import bcn_sync, geo_sync, okobaudat_sync, sea_sync, snifa_sync
from .models import EnvironmentalSource
from .services import sanitized_error, sync_environmental_source
from .source_health import source_health

# Bespoke sync functions take no arguments — each hardcodes the exact
# `EnvironmentalSource.codigo` it materializes against (see each module).
# The paired `codigo` here lets the orchestrator verify it is watching the
# same source the bespoke function will actually touch before calling it;
# otherwise it falls back to the safe generic sync.
_BESPOKE_SYNC = {
    "bcn_leychile_sparql": ("bcn-leychile", bcn_sync.sync_bcn_legal_norms),
    "snifa_public": ("snifa", snifa_sync.sync_snifa_regulatory_context),
    "sea_seia_public": ("sea-seia", sea_sync.sync_sea_regulatory_context),
    "simbio_arcgis": ("simbio", geo_sync.sync_simbio_geo_catalog),
    "ide_mma_catalog": ("ide-mma", geo_sync.sync_ide_mma_geo_catalog),
    "okobaudat_soda4lca": ("okobaudat", okobaudat_sync.sync_okobaudat_material_catalog),
}


def _sync_function_for(source):
    entry = _BESPOKE_SYNC.get(source.connector_key)
    if entry is not None and entry[0] == source.codigo:
        return entry[1]
    return lambda: sync_environmental_source(source)


def watch_source(source, *, health_only=False, dry_run=False, open_reviews=True):
    """One source's watch attempt. Never raises for a source-level
    problem — always returns a structured result so the caller can isolate
    failures per source."""

    base = {"source_id": source.pk, "codigo": source.codigo}

    if not source.activa:
        return {**base, "attempted": False, "reason": "inactiva"}
    if not source.permite_poll_automatico and not health_only:
        return {**base, "attempted": False, "reason": "poll_automatico_deshabilitado"}

    if health_only or dry_run:
        return {**base, "attempted": False, "health": source_health(source)}

    sync_fn = _sync_function_for(source)
    try:
        run = sync_fn()
    except ValidationError as exc:
        return {**base, "attempted": True, "success": False, "sync_run_id": None, "error": sanitized_error(exc)}
    except Exception as exc:  # connector-level failures are already sanitized/persisted by services.sync_environmental_source; anything else must still never crash the cycle
        return {**base, "attempted": True, "success": False, "sync_run_id": None, "error": sanitized_error(exc)}

    success = run.estado != "error"
    review_count = 0
    if success and open_reviews:
        from .review_queue import open_items_from_run

        review_count = len(open_items_from_run(run))

    return {
        **base,
        "attempted": True,
        "success": success,
        "sync_run_id": run.pk,
        "change_count": run.created + run.modified + run.disappeared,
        "review_count": review_count,
        "health_after": source_health(source)["health_bucket"],
        "error": run.message if not success else "",
    }


def watch_sources(sources=None, *, health_only=False, dry_run=False, open_reviews=True, continue_on_error=True):
    """`sources=None` means "all active, auto-pollable" sources — never
    every registered source unconditionally."""

    if sources is None:
        sources = EnvironmentalSource.objects.filter(activa=True, permite_poll_automatico=True)

    results = []
    for source in sources:
        try:
            results.append(
                watch_source(source, health_only=health_only, dry_run=dry_run, open_reviews=open_reviews)
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            results.append({
                "source_id": source.pk, "codigo": source.codigo, "attempted": True,
                "success": False, "sync_run_id": None, "error": sanitized_error(exc),
            })
    return results
