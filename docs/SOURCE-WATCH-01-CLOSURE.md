# SOURCE-WATCH-01 — Closure

Base: `463c749` (MATERIAL-INTELLIGENCE complete, pushed to `origin/main`).
This macrophase extends `apps.knowledge`'s existing source-registry/sync
infrastructure — it does not replace or duplicate it.

## Purpose

SOURCE-WATCH answers, continuously and deterministically: are our official
sources healthy and fresh, did upstream change, what changed, what
governed Carbono Zero objects may be affected, and does anything require
human review — without ever letting an upstream change silently rewrite
governed downstream truth (a factor, a legal conclusion, a mapping, a
calculation).

```text
official upstream
  -> immutable observation/snapshot        (existing: ExternalSnapshot)
  -> typed facts                            (existing: per-source Fact models)
  -> deterministic change assessment        (new: change_observation.py)
  -> deterministic impact routing           (new: change_classification.py, impact_routing.py)
  -> human review when required             (new: SourceWatchReviewItem)
  -> governed downstream transition          (existing domain services — never invoked by SOURCE-WATCH itself)
```

## Authority map (one authority per concept — audited, no duplication)

| Concept | Authority | Notes |
|---|---|---|
| Source registry | `EnvironmentalSource` (existing, extended) | +`cadencia_horas`, +`permite_poll_automatico`, +`clean()` — no second registry |
| Watch policy / connector capabilities | `watch_policy.py` (new) | Connector capabilities are a code-level lookup, not per-source DB state — they describe what each connector implementation actually does |
| Source state / freshness | `SourceState` (existing) + `services.source_freshness()` (existing, extended with `inactiva`/`sincronizando`) + `source_health.py` (new) | `source_health()` wraps, never replaces, `source_freshness()` |
| Sync history | `SyncRun` (existing, +`snapshot_autoritativo`) | No second sync-run model |
| Immutable external observation | `ExternalSnapshot` (existing, untouched) | No second snapshot store |
| Current external record | `ExternalRecord` (existing, +`missing_since_run`, +`reappeared_via_run`) | No second "current record" table |
| Normalized change | `change_observation.py` (new, pure/derived) | Reconstructed entirely from `SyncRun`+`ExternalSnapshot`+`ExternalRecord`; the two facts that needed new fields (authoritativeness, first-observed-disappearance/reappearance run) were not otherwise reconstructable |
| Source-specific interpretation | `change_classification.py` (new) | Reuses `apps.analytics.services.material_source_impact` for ÖKOBAUDAT — never reimplements MATERIAL-DATA's own version-diff logic |
| Downstream impact | `impact_routing.py` (new) | Only routes through relationships that are actually verified in the repo (ÖKOBAUDAT -> `MaterialFactorMapping`/`FactorAmbiental`/`CalculoAmbiental`); every other domain fails closed to `unknown_impact` rather than inventing a consumer graph |
| Human source-review state | `SourceWatchReviewItem` / `SourceWatchReviewDecision` (new) | No existing tenant-scoped problem/review model fit this global, source-level concern |
| Watch orchestration | `watch_orchestration.py` (new) | Reuses each source's existing bespoke sync function (BCN/SEA/SNIFA/SIMBIO/IDE-MMA/ÖKOBAUDAT catalog) or the generic `sync_environmental_source()` — never rewrites a connector |

## Source registry & watch policy (01A)

`EnvironmentalSource.clean()` fails closed for an unregistered `connector_key`
and rejects non-positive `stale_after_hours`/`cadencia_horas`.
`watch_policy.describe_watch_policy(source)` is the single answer to "how
should this source be watched": it combines the source's own governed
fields with a static, code-level `CONNECTOR_CAPABILITIES` lookup describing
exactly what each of the nine registered connectors' `fetch()` methods
actually does today — none of them currently narrow a request using a
stored cursor (all re-fetch fully and rely on `ExternalSnapshot`'s
content-hash dedup), and this is reported truthfully, not aspirationally.
`safe_to_auto_watch` is `False` whenever the source is inactive, has
`permite_poll_automatico=False`, or its connector is unregistered.

## Health & freshness (01B)

`source_health()` reuses `source_freshness()` for the core state string
(now covering `inactiva` and `sincronizando` too, added as new early-return
branches with all prior states/behavior unchanged) and adds the full
structured envelope: timestamps, sanitized last error, `stale_after_hours`,
computed `age_seconds`/`next_freshness_boundary`, the last finished sync
run's summary, and — critically — `last_known_good_available`, so a source
currently in an error state is never confused with "no usable data" nor
silently reported as healthy.

## Normalized change observation (01C)

`observe_sync_run(run)` reconstructs, purely on read, exactly what one
completed run observed: `created` (a snapshot with no earlier snapshot for
that external_id), `changed` (a new snapshot for an already-known
external_id), `unchanged` (the record's `last_seen_at` matches the run's
own `finished_at` timestamp with no new snapshot — the same `now` value the
sync engine already shares between both fields), `disappeared`/`reappeared`
(via the two new pointer fields), idempotent by construction (re-running
the same query against the same immutable data yields the same result).
Never marks anything `disappeared` for a non-authoritative run.

## Source-specific classification (01D)

`classify_change(event, source)` dispatches by `connector_key`:
- **ÖKOBAUDAT** (`classify_okobaudat_change`): reuses
  `material_source_impact.assess_candidate_impact`/`assess_all_candidates`
  verbatim — MATERIAL-DATA's own `no_impact`/`review_recommended`/
  `review_required` vocabulary, mapped onto SOURCE-WATCH's bounded severity
  scale.
- **BCN/LeyChile** (`classify_bcn_legal_change`): any legal-norm content
  change is unconditionally `high` severity + `requires_review=True` — this
  domain's governance (draft/validated/active/obsolete lifecycle) already
  requires explicit human review before any legal conclusion is trusted.
- **Every other source** (`classify_generic_change`, the default): never
  assumes `no_impact` for an uninterpreted change — fails closed to
  `changed_unknown_impact` / `requires_review=True`. `created`/`unchanged`
  are the only classifications that are ever low-severity/no-review by
  default; `disappeared` is always `high`/`requires_review=True` even
  generically.

## Downstream impact routing (01E)

`route_impact(classification)` only follows relationships that are
genuinely verified: for ÖKOBAUDAT it surfaces the exact
`FactorAmbiental`/`VersionFactorAmbiental`/`MaterialFactorMapping` ids (and
a historical-calculation count) already computed by
`assess_candidate_impact`. For `legal` and every unmodeled domain it
returns `unknown_impact` with an explicit reason rather than guessing a
norm -> obligation traceability chain that does not yet exist as a
verified query in this repository (see Known limitations). Never mutates
anything it inspects.

## Review queue & human governance (01F)

`SourceWatchReviewItem` (open/acknowledged/resolved/superseded) is the
durable record that a human needs to look at a specific, immutable source
change. `open_review_item()` is idempotent per `(source, external_id,
content_hash)` — a PostgreSQL partial unique index
(`knowledge_review_item_open_dedupe`, `WHERE estado IN ('open',
'acknowledged')`) is the real safety net; the application-level dedup
lookup is the ergonomic fast path. Resolving/acknowledging **only** records
that a human looked at it — it never applies any downstream domain
mutation (verified directly:
`test_resolving_never_mutates_downstream_analytics_objects`,
`test_review_resolution_never_mutates_downstream`). Mutating actions
require `is_superuser` (this app's existing convention — it has no tenant
concept to gate by).

## Resilient watch orchestration (01G)

`watch_source()`/`watch_sources()` never raise for a per-source problem —
every outcome (inactive, poll-disabled, sync failure, success) is a
structured dict, so one bad source never blocks the others. Concurrency
safety is not reimplemented: `services._begin()`'s existing
`select_for_update()` + `SourceState.SYNCING` guard is still the sole
authority; a source already syncing simply reports a graceful per-source
failure. No retry loop and no stale-`SYNCING` lease/timeout recovery were
built — no evidence of a stuck-sync problem exists in this codebase, and
inventing a recovery contract without a real need risks silently
un-blocking a genuinely still-running worker.

## Operational API & observability (01H)

`GET /api/knowledge/source-watch/overview/` (system summary),
`.../sources/<code>/health/`, `.../sources/<code>/sync-runs/<id>/changes/`,
`.../review-items/` (filterable by source/estado/severity/domain/
impact_level/date range, paginated), `.../review-items/<id>/`,
`.../review-items/<id>/acknowledge|resolve/` (superuser only). The existing
`sources/<code>/` detail endpoint now also includes the richer `health`
payload alongside its original `freshness` string (backward compatible,
nothing removed). `review-items/` uses `select_related("source")` +
`Prefetch("decisiones", ...)` so its query count does not scale with row
count (a real N+1 was found and fixed here during this phase — see Bugs
found).

## Continuous watch command / scheduling readiness (01I)

`python manage.py watch_environmental_sources [--source CODE |
--all-active] [--health-only] [--dry-run] [--continue-on-error |
--stop-on-error] [--json]`. Embeds no source-specific business logic — it
only calls `watch_orchestration`. Per-source sync failures are reported in
structured output and never fail the command by itself (that is what
health tracking / the review queue are for); the command only exits
non-zero if `--stop-on-error` was given and an unexpected exception
actually propagated. No scheduler infrastructure existed in this project
before this phase and none was added (no Celery/Redis) — see the
production runbook below for the recommended cron/systemd invocation.

## Security

- Authentication: every SOURCE-WATCH read endpoint requires
  `IsAuthenticated`; anonymous requests are rejected (403, DRF's default
  for `SessionAuthentication` with no challenge — verified directly).
- RBAC: mutating review actions require `is_superuser`, matching this
  app's pre-existing convention (it has no tenant/organization concept to
  gate reads by — verified during the original architecture audit).
- IDOR: an unknown review-item id or source code is a 404, never a 500 or
  a data leak.
- Error sanitization: every persisted/returned error goes through the
  existing `services.sanitize()`/`sanitized_error()` — verified end to end
  through `watch_source()`'s structured output and `SourceState.last_error`.
- Immutability: every governed SOURCE-WATCH model blocks direct queryset
  `.update()`/`.delete()` (not just instance-level guards) — audited across
  every model this phase added, plus the pre-existing `SyncRun`/
  `ExternalSnapshot` "immutable once finished/created" instance guards
  (unchanged, re-verified).
- Guarded state transitions: a review item cannot be acknowledged/resolved
  twice, a resolved/superseded item is fully immutable afterward.

## PostgreSQL / concurrency

Real-PostgreSQL `TransactionTestCase` coverage: two workers never
conflict-sync the same source (`SourceState.SYNCING` lock), concurrent
duplicate review-item opens leave exactly one row (partial unique index),
concurrent acknowledge/resolve of the same item always converges to
`RESOLVED` regardless of race order. Migrations `0014`-`0018` apply
forward cleanly on real PostgreSQL.

## Tests

New: `test_source_watch_policy.py` (11), `test_source_health.py` (10),
`test_change_observation.py` (8), `test_change_classification.py` (9),
`test_impact_routing.py` (6), `test_review_queue.py` (13),
`test_watch_orchestration.py` (10), `test_source_watch_api.py` (11),
`test_watch_command.py` (8), `test_source_watch_e2e.py` (10),
`test_source_watch_security_audit.py` (9) — **115 tests total, all green
together with the pre-existing `apps/knowledge/tests.py::KnowledgeHubTests`
(11), 100% pass, real PostgreSQL.**

### Global negative tests (automated)

- `test_no_false_disappearance_for_incremental_source` /
  `test_disappearance_safety_authoritative_vs_incremental` — an unseen
  record in a non-authoritative batch is never marked disappeared.
- `test_unknown_change_fails_closed_never_no_impact` /
  `test_malformed_event_kind_still_fails_closed` — an uninterpreted change
  is never `no_impact`.
- `test_missing_detail_is_unknown_impact_not_no_impact` — a missing impact
  assessment is `unknown_impact`, never silently `no_known_impact`.
- `test_resolving_never_mutates_downstream_analytics_objects` /
  `test_review_resolution_never_mutates_downstream` — resolving a review
  item never applies a downstream domain mutation.
- `test_watch_source_error_field_never_carries_secret` /
  `test_error_does_not_leak_secret_via_run_changes` — no secret ever
  reaches a persisted or API-returned error.

## Migrations

`0014_source_watch_policy` (+`cadencia_horas`, +`permite_poll_automatico`
on `EnvironmentalSource`), `0015_change_observation_support`
(+`snapshot_autoritativo` on `SyncRun`, +`missing_since_run` on
`ExternalRecord`), `0016_reappearance_support` (+`reappeared_via_run` on
`ExternalRecord`), `0017_source_watch_review_queue` (new
`SourceWatchReviewItem`/`SourceWatchReviewDecision` models),
`0018_review_queue_dedupe_guard` (PostgreSQL-only partial unique index,
no-op on any other backend, matching the existing `0068`-style pattern
from MATERIAL-INTELLIGENCE).

## Bugs found and fixed during this phase (self-audit)

- **`open_review_item`'s `IntegrityError` handling raised
  `TransactionManagementError`**: the whole function was one
  `@transaction.atomic` block, so catching the partial-unique-index
  violation and then querying again in the `except` clause failed because
  the outer transaction was already marked broken. Fixed by wrapping only
  the risky `.save()` in its own inner `transaction.atomic()` (a real
  savepoint) — the same pattern already used correctly elsewhere in this
  codebase's governed-write services.
- **`JSONField(default=list)` missing `blank=True`** on
  `SourceWatchReviewItem.reasons`/`affected_objects` — the same class of
  bug already found and fixed once in MATERIAL-INTELLIGENCE this session;
  Django's `full_clean()` treats an empty list as blank unless told
  otherwise.
- **`impact_routing._envelope()` silently dropped `severity`** when
  translating a classification into an impact envelope, which meant
  `SourceWatchReviewItem.severity` (a required `CharField`) would have
  been persisted as an empty string in real (non-test) usage — caught by a
  test that supplied `severity` explicitly in its stub, then traced back
  to the real gap once the underlying `open_review_item()` call from
  `open_items_from_run()` used only what `route_impact()` actually
  returns.
- **A real N+1** in `review_items` API view: `item.decisiones.order_by("pk")`
  bypasses Django's prefetch cache (any `.filter()`/`.order_by()` call on a
  prefetched related manager triggers a fresh query). Fixed with
  `Prefetch("decisiones", queryset=...order_by("pk"))` plus
  `item.decisiones.all()` at read time — verified with a query-count test
  that compares 1-row vs. many-row responses rather than asserting a guessed
  literal count.
- **Two of this session's own tests made live outbound HTTP calls**:
  `watch_sources()`'s default "all active" selection unintentionally
  included the bootstrap-seeded real sources (RETC, HuellaChile, BCN,
  SNIFA, SEA, SIMBIO, IDE-MMA, ÖKOBAUDAT), whose real connectors would then
  hit real external endpoints during a unit test run. Fixed by explicitly
  setting `permite_poll_automatico=False` on every non-fake-connector
  source in the affected tests' `setUp()`.
- **Migration reversal friction (pre-existing pattern, not newly
  introduced)**: reversing `0014` fails because `apps.knowledge`'s
  pre-existing `post_migrate` signal (`ensure_source_registry_after_migrate`,
  present in `apps.py` before this session) re-seeds the source registry
  using the *current* `models.py`, which still declares the now-dropped
  columns. This is the same class of "post_migrate auto-seed vs. migration
  reversal" friction already documented for a different app in
  `MATERIAL-DATA-CLOSURE.md`. Forward migration and normal operation are
  fully unaffected; only an isolated `migrate knowledge <earlier>` while the
  code is unchanged hits this, and it self-resolves immediately on
  migrating forward again (verified).

## Known limitations (V1, explicit)

- **Legal (BCN) downstream impact routing is `unknown_impact` by
  design**, not yet a resolved norm -> `LegalObligationVersion`
  traceability query. The real chain is norm -> version -> legal text
  document -> parsed article -> extraction run -> obligation candidate ->
  promoted obligation version, and asserting a shortcut through it without
  a verified join risked inventing a relationship. Classification already
  forces `requires_review=True` unconditionally for any legal change, so no
  legal change is ever silently treated as safe — only the *specific
  affected objects* are not yet enumerated automatically.
- **Generic-domain downstream impact routing is `unknown_impact`** for
  every source family without a verified consumer relationship
  (RETC/HuellaChile/SNIFA/SEA/SIMBIO/IDE-MMA) — there is no established
  FK graph from these facts to any other governed authority in this
  repository yet.
- **No stale-`SYNCING` lease/timeout recovery** — deferred; no evidence of
  a real stuck-sync problem exists yet (anti-overengineering).
- **No bounded-retry policy in the orchestrator** — a single sync attempt
  per `watch_source()` call; retry cadence is a scheduler-level concern
  (re-invoke per the source's own `cadencia_horas`), not reinvented here.
- **This macrophase's git history includes an unrelated, concurrent
  change**: `apps/ec3/` (a separate "EC3" integration) and matching
  `settings.py`/`urls.py`/`INSTALLED_APPS` entries appeared mid-session
  from a different, concurrent process writing to this same working
  directory — not created by this session, and never modified by it. It
  had stabilized (its own migrations applied cleanly) before this
  session's final regression gate ran.

## Production runbook (for the human gate — NOT executed by this session)

1. `python manage.py check` and `python manage.py makemigrations --check
   --dry-run` in the target environment.
2. `python manage.py migrate knowledge` — applies `0014`–`0018`.
   `0018` installs a PostgreSQL-only partial unique index (no-op on any
   other backend). Verify forward migration on a PostgreSQL target.
3. No production source, sync, review, or downstream domain data was
   touched by this session.
4. Schedule `python manage.py watch_environmental_sources --all-active
   --continue-on-error --json` via cron or a systemd timer — a suggested
   starting cadence is hourly for `--health-only` checks and per-source
   `cadencia_horas`/`stale_after_hours` for full watch cycles; do not poll
   every source at the same arbitrary interval. No Celery/Redis is
   required or was added.
5. The first time a human wants to act on an open `SourceWatchReviewItem`,
   they acknowledge/resolve it via the API (superuser only) — this never
   auto-applies anything; any real factor/legal/mapping change still goes
   through that domain's own existing governed service, separately.

STATUS: see `docs/SOURCE-WATCH-01-HANDOFF.md` for the final gate results
and STATUS line.
