# SOURCE-WATCH-01 — Handoff (complete)

STATUS: COMPLETE

Base: `463c749` (MATERIAL-INTELLIGENCE complete, pushed to origin/main).

## Phase status

- 01A — Source Registry & Watch Policy Audit: PASS
- 01B — Source Health & Freshness Authority: PASS
- 01C — Normalized Change Observation: PASS
- 01D — Source-Specific Change Classification: PASS
- 01E — Downstream Impact Routing: PASS
- 01F — Review Queue & Human Governance: PASS
- 01G — Resilient Watch Orchestration: PASS
- 01H — Operational API & Observability: PASS
- 01I — Continuous Watch Command / Scheduling Readiness: PASS
- 01J — Closure & Environmental Platform Readiness: PASS

## Final regression (closure gate)

Full suite across `apps.analytics apps.knowledge apps.iot` on real PostgreSQL
(deliberately excluding the unrelated, separately-owned `apps.ec3` app):

```
Ran 1395 tests in 2467.494s
FAILED (errors=27)
System check identified no issues (0 silenced).
```

All 27 errors are the pre-existing, documented baseline, unchanged in name
or count from before this macrophase started: 20 in
`apps.analytics.test_professional_v2.ProfessionalV2Tests` and 7 in
`apps.analytics.test_generated_emissions_indicator.GeneratedEmissionsIndicatorTests`
(both pre-existing methodology/indicator issues unrelated to SOURCE-WATCH,
knowledge, or iot). Zero new failures, zero new modules affected. The
115 SOURCE-WATCH-specific tests plus the 11 pre-existing
`KnowledgeHubTests` all pass (126/126, confirmed separately during
development in run `b62idkb1e`). `manage.py check` and
`makemigrations --check --dry-run` are clean.

## Important note: concurrent unrelated work in this working directory

During 01I, `backend/apps/ec3/` (a new, unrelated "EC3" integration app) and
matching `backend/config/settings.py`/`backend/config/urls.py` changes
appeared mid-session from what was evidently a different, concurrent
process writing to this same working directory — not created by this
session. This transiently broke `manage.py check` (`ModuleNotFoundError:
No module named 'apps.ec3.urls'`) for a few minutes before that other
process finished and added its own `urls.py`/migrations. This session
never touched `apps/ec3/` and waited for it to stabilize rather than
working around or reverting it. `manage.py check` and
`makemigrations --check --dry-run` are confirmed clean again as of this
checkpoint. Two of this session's own tests were fixed to stop relying on
`watch_sources()`'s default source selection including bootstrap-seeded
real sources (which would otherwise make live outbound HTTP calls to real
government/international endpoints during unit tests) — a real test-hygiene
bug this session introduced and caught itself before it became a habit.

## Files/changes so far

- `apps/knowledge/models.py`: `EnvironmentalSource` +2 fields
  (`cadencia_horas`, `permite_poll_automatico`) + `clean()`; `SyncRun` +1
  field (`snapshot_autoritativo`); `ExternalRecord` +2 fields
  (`missing_since_run`, `reappeared_via_run`).
- `apps/knowledge/services.py`: `source_freshness()` extended with
  `inactiva`/`sincronizando` states (existing states unchanged);
  `sync_environmental_source()` now sets `missing_since_run`/
  `reappeared_via_run`/`snapshot_autoritativo` at their exact existing
  write points — no new write transaction, no behavior change to existing
  counters/return values.
- New: `apps/knowledge/watch_policy.py` (01A), `apps/knowledge/source_health.py` (01B),
  `apps/knowledge/change_observation.py` (01C).
- Migrations: `0014_source_watch_policy`, `0015_change_observation_support`,
  `0016_reappearance_support`.
- Tests: `test_source_watch_policy.py` (11), `test_source_health.py` (10),
  `test_change_observation.py` (8) — all green together with the existing
  `apps/knowledge/tests.py::KnowledgeHubTests` (11) — 40/40 on real
  PostgreSQL, zero regression.

## Architectural decisions

- No new source registry, no new snapshot/sync-run model, no new
  freshness vocabulary — extended `EnvironmentalSource`/`SyncRun`/
  `ExternalRecord` minimally and extended `services.source_freshness()`
  rather than replacing it.
- Connector capabilities (authoritative-full-snapshot, cursor support,
  conditional-HTTP-metadata capture) are static per-connector-implementation
  facts, not per-source instance data — represented as a code-level lookup
  (`watch_policy.CONNECTOR_CAPABILITIES`) keyed by `connector_key`, fails
  closed (`None`) for any unregistered connector.
- Per-record change observation (01C) is reconstructed entirely on read
  from `SyncRun` + `ExternalSnapshot` + `ExternalRecord`, using the same
  `now` timestamp already shared between a run's `finished_at` and every
  record's `last_seen_at` in that run to attribute "unchanged" precisely.
  Two facts were NOT safely reconstructable from the pre-existing schema
  and got minimal new fields instead of a parallel change-event ledger:
  whether a run's own batch was authoritative (`SyncRun.snapshot_autoritativo`)
  and which run first observed a given disappearance/reappearance
  (`ExternalRecord.missing_since_run` / `reappeared_via_run`).
- A record can carry more than one classification in the same run's
  observation (e.g. `unchanged` + `reappeared` when identical content
  returns after an absence) — this is two independent true facts about the
  same external_id, not a bug.

## Closure

All ten phases (01A–01J) are implemented, tested, and green together with
every pre-existing test in the affected apps. See
`docs/SOURCE-WATCH-01-CLOSURE.md` for the full phase-by-phase closure
report (files, architectural decisions, known limitations). This macrophase
is committed and pushed to `origin/main`; see the commit referenced there.

Known non-blocking limitation (documented, not fixed, out of scope): reversing
a migration that alters `EnvironmentalSource` (e.g. `0014`) hits a
pre-existing `post_migrate` re-seed signal in `apps.knowledge.apps` that
seeds using current `models.py` regardless of migration direction — forward
migration and normal operation are fully unaffected.

ENVIRONMENTAL ROADMAP: COMPLETE
NEXT: BUILD-INTELLIGENCE / BUILD-ARCH-00 (not started this macrophase)
