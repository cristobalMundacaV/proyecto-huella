# SOURCE-WATCH-01 — COMPLETE AUTONOMOUS MISSION

## Carbono Zero — final environmental macrophase

This file is an executable engineering mission for Claude Code.

The goal is to implement and close the complete **SOURCE-WATCH-01** macrophase after `MATERIAL-INTELLIGENCE` is fully complete.

Do not execute this mission before `docs/MATERIAL-INTELLIGENCE-HANDOFF.md` says `STATUS: COMPLETE`.

---

# 0. EXECUTION CONTRACT

Work as an autonomous sequential engineering loop:

```text
AUDIT CURRENT STATE
  ↓
IMPLEMENT PHASE
  ↓
FOCUSED TESTS
  ↓
POSTGRESQL / SECURITY / CONCURRENCY
  ↓
REGRESSION
  ↓
FAIL?
  ├─ YES → ROOT CAUSE → FIX → RE-RUN THE SAME FAILED GATE
  └─ NO
  ↓
DOCUMENT CHECKPOINT
  ↓
NEXT PHASE
```

Do not ask the user for approval between phases.

Do not stop after a subphase.

Only stop in one of two cases:

1. `SOURCE-WATCH-01` is fully COMPLETE and all final gates have passed.
2. A real token/context/usage/tool/infrastructure limit makes further work impossible.

If a real limit is reached, leave the repository consistent and update:

`docs/SOURCE-WATCH-01-HANDOFF.md`

with:

- completed phases;
- current phase;
- last verified gate;
- changed files;
- migrations;
- tests passed;
- tests pending;
- exact blocker;
- next exact task;
- next exact command;
- architectural decisions already made.

Never describe a partial state as COMPLETE.

---

# 1. STARTING BASELINE

Before changing code, read:

- `CLAUDE.md`
- `docs/MATERIAL-DATA-CLOSURE.md`
- `docs/MATERIAL-INTELLIGENCE-CLOSURE.md`
- `docs/MATERIAL-INTELLIGENCE-HANDOFF.md`
- all relevant files under `docs/architecture/`

Audit the current repository and `git status` before assuming anything.

The environmental source foundation already contains, at minimum:

```text
EnvironmentalSource
SourceState
SyncRun
ExternalSnapshot
ExternalRecord
ExternalFileArtifact
```

Existing source infrastructure already tracks concepts such as:

```text
source identity
connector key
access type
base/documentation URL
authority
suggested cadence
stale_after_hours
active/inactive state
last attempt
last successful sync
upstream version
cursor
etag
last-modified
checksum
last error
sync-run counts
immutable external snapshots
current external records
```

There are existing connectors/sync/materialization flows for sources including, where currently implemented:

- HuellaChile;
- RETC;
- BCN / LeyChile;
- SNIFA;
- SEA;
- SIMBIO;
- IDE MMA;
- ÖKOBAUDAT.

Do not replace this architecture.

Do not create a parallel source registry.

Do not create a parallel snapshot system.

Do not create a second sync history if `SyncRun` is already authoritative.

Reuse existing source-specific sync/materialization services and commands.

---

# 2. PURPOSE OF SOURCE-WATCH

SOURCE-WATCH exists to answer continuously and deterministically:

```text
Are our official sources healthy?
Are they fresh?
Did upstream change?
What changed?
What governed Carbono Zero objects may be affected?
Does anything require human review?
Can the last trusted version still be used?
```

The system must distinguish:

```text
source synchronization
source observation
change detection
impact assessment
review requirement
```

These are not the same operation.

A source changing upstream must NEVER automatically rewrite governed truth downstream.

The canonical direction remains:

```text
official upstream
→ immutable observation/snapshot
→ typed facts
→ deterministic change assessment
→ deterministic impact routing
→ human review when required
→ governed downstream transition through existing domain services
```

Never:

```text
upstream changed
→ silently replace active factor / law / mapping / calculation / professional conclusion
```

---

# 3. SCIENTIFIC AND GOVERNANCE BOUNDARY

SOURCE-WATCH may:

- observe official sources;
- synchronize through existing trusted connectors;
- detect new/changed/disappeared records;
- classify freshness and source health;
- produce deterministic change events/assessments when persistence is justified;
- identify downstream objects that may require review;
- expose review queues;
- explain why a source is stale/unhealthy/changed;
- provide operational commands and APIs.

SOURCE-WATCH may NOT automatically:

- activate an environmental factor;
- replace an active environmental factor;
- change a material mapping;
- approve a material substitution;
- recalculate historical environmental accounting;
- rewrite a legal obligation;
- change legal applicability conclusions without the existing governed process;
- close a professional review;
- fabricate missing source data;
- use AI to decide scientific or legal truth.

AI is not required for SOURCE-WATCH.

If AI is reused for explanation, it must obey `ARQ_10_INTELLIGENCE_BOUNDARIES.md` and remain advisory only.

---

# 4. MACROPHASE PLAN

Implement and close ten sequential subphases:

```text
SOURCE-WATCH-01A  Source Registry & Watch Policy Audit
SOURCE-WATCH-01B  Source Health & Freshness Authority
SOURCE-WATCH-01C  Normalized Change Observation
SOURCE-WATCH-01D  Source-Specific Change Classification
SOURCE-WATCH-01E  Downstream Impact Routing
SOURCE-WATCH-01F  Review Queue & Human Governance
SOURCE-WATCH-01G  Resilient Watch Orchestration
SOURCE-WATCH-01H  Operational API & Observability
SOURCE-WATCH-01I  Continuous Watch Command / Scheduling Readiness
SOURCE-WATCH-01J  Closure & Environmental Platform Readiness
```

Do not begin another macrophase after 01J.

---

# SOURCE-WATCH-01A — SOURCE REGISTRY & WATCH POLICY AUDIT

## Objective

Turn the existing `EnvironmentalSource` registry into the explicit authority for watch policy without duplicating it.

Audit every currently registered official source and the connector actually used by the repository.

For each source Carbono Zero must be able to determine, from governed configuration or deterministic defaults:

```text
source code
source authority
active/inactive
connector
access type
freshness threshold
suggested cadence
whether full snapshots are authoritative
whether disappearance can be interpreted safely
whether incremental cursors are supported
whether conditional HTTP metadata is supported
whether automatic polling is permitted/safe
```

Do not invent upstream capabilities.

If the source contract does not support reliable disappearance detection, represent that as unknown/unsupported rather than assuming deletion.

## Watch policy

If the existing source model lacks a few necessary watch-policy fields, extend it minimally.

Before adding fields/models, answer internally:

1. What authority does this represent?
2. What invariant does it protect?
3. Why can existing fields/metadata not represent it safely?

Prefer existing structured fields over dumping core policy into arbitrary JSON.

## Validation

Prevent nonsensical combinations where reasonably possible.

Examples:

- inactive source should not be automatically watched;
- cadence/threshold values must be positive;
- connector key must resolve through the existing connector registry;
- unsupported watch behavior must fail closed.

## Tests

Cover source registry validity, inactive sources, unsupported connector, freshness/cadence boundaries and existing source regression.

## DoD 01A

For every official source, Carbono Zero can answer:

> How should this source be watched, how stale may it become, and what source capabilities are actually supported?

---

# SOURCE-WATCH-01B — SOURCE HEALTH & FRESHNESS AUTHORITY

## Objective

Establish one deterministic source-health projection based on existing `EnvironmentalSource`, `SourceState` and `SyncRun` data.

Do not create a second truth for freshness if `source_freshness()` already provides the core semantics.

Audit and extend/restructure only if necessary.

## Health contract

A source-health result should distinguish at minimum:

```text
healthy
near_stale
stale
syncing
partial_with_last_version
partial_without_version
error_with_last_version
error_without_version
never_synced
inactive
```

Use the repository's established Spanish/internal status values where appropriate; do not rename public contracts gratuitously.

Return structured reasons and timestamps, not only prose.

Include when available:

```text
last_attempt_at
last_successful_sync_at
retrieved_at
upstream_updated_at
upstream_version
last_error (sanitized)
stale_after_hours
age
next freshness boundary
last successful run summary
```

Never leak credentials/tokens/cookies in error responses.

Reuse existing error sanitization.

## Last-known-good semantics

When a source fails but an earlier trusted version exists, distinguish:

```text
source currently unhealthy
last trusted version still available
```

Do not silently label the source healthy.

Do not destroy last-known-good data after a sync failure.

## Tests

Cover all health states, time boundaries, sanitized errors, timezone correctness and inactive source behavior.

## DoD 01B

Carbono Zero has one explainable answer to:

> Is this official source healthy and fresh right now, and what is the last trustworthy version we have?

---

# SOURCE-WATCH-01C — NORMALIZED CHANGE OBSERVATION

## Objective

Create a source-agnostic way to describe what a completed sync actually observed.

First audit whether `SyncRun + ExternalSnapshot + ExternalRecord` already reconstruct enough information.

Only create a new immutable change-event model if durable per-record change identity cannot be reconstructed safely from existing authorities.

Avoid duplicating snapshots.

## Change vocabulary

At minimum support deterministic classifications conceptually equivalent to:

```text
created
changed
unchanged
disappeared
reappeared
source_metadata_changed
unknown
```

Only call something `disappeared` when the connector/run was an authoritative full observation capable of proving absence.

Incremental APIs must not mark unseen records as disappeared simply because they were not in the current page/batch.

## Evidence

Any durable change assessment must point back to:

```text
source
sync run
external identity
old snapshot when applicable
new snapshot when applicable
retrieval time
content hash/version
```

No mutable raw copy of the same source payload.

## Idempotence

Re-analyzing the same sync run must not create duplicate change events.

## Tests

Cover created, changed, unchanged, disappearance with authoritative full snapshot, no false disappearance for incremental source, reappearance, concurrent assessment, idempotence.

## DoD 01C

Given any completed sync run, Carbono Zero can explain exactly what the source observation changed without guessing.

---

# SOURCE-WATCH-01D — SOURCE-SPECIFIC CHANGE CLASSIFICATION

## Objective

Route normalized observations through source-specific deterministic classifiers where domain semantics differ.

Do not force every source into one fake universal semantic model.

Audit existing source-specific logic first.

Examples of existing/likely domain-specific behavior:

- ÖKOBAUDAT version impact assessment from MATERIAL-DATA;
- BCN legal norm/version changes;
- HuellaChile factor file/version changes;
- SEA/RCA project/reference changes;
- SNIFA regulatory references;
- geospatial source dataset/layer changes;
- RETC resource/file versions.

Reuse existing assessment services.

Do not reimplement MATERIAL-DATA source-impact logic.

## Classifier output

Use a bounded common envelope such as:

```text
source
external identity/change
classification
severity
requires_review
reasons[]
domain
provenance
```

but keep domain-specific details under explicit typed/structured payloads.

Severity must be deterministic and rule-based.

Do not use an LLM to set severity.

## Unknown semantics

If a source changed but Carbono Zero does not have enough domain rules to interpret the significance:

```text
classification = changed_unknown_impact
requires_review = true
```

Never assume `no impact`.

## Tests

At least one meaningful change classifier per implemented source family, unknown-change behavior, malformed/incomplete facts, idempotence.

## DoD 01D

Carbono Zero can distinguish:

> The source changed

from:

> This specific domain change may affect governed Carbono Zero behavior.

---

# SOURCE-WATCH-01E — DOWNSTREAM IMPACT ROUTING

## Objective

Identify what governed downstream objects may be affected by an upstream change without mutating those objects.

Create deterministic impact routing using existing relationships/provenance.

Potential impacted domains include only those actually represented in the repo, for example:

```text
FactorAmbiental / VersionFactorAmbiental
MaterialEnvironmentalFactorCandidate
MaterialFactorMapping
material calculations / historical ledger
legal obligation/version structures
legal applicability/evidence requirements
RCA/regulatory context
geospatial context
professional/reporting consumers
```

Do not invent relationships that do not exist.

## Impact levels

Use deterministic states conceptually like:

```text
no_known_impact
review_recommended
review_required
blocked
unknown_impact
```

with reasons.

`unknown_impact` is not `no_known_impact`.

## Historical protection

A source update must NEVER rewrite historical calculations or prior professional conclusions.

Historical objects remain tied to their original snapshots/versions.

## Provenance graph

Impact results must make the chain traversable:

```text
upstream observation
→ snapshot/version change
→ typed fact/domain object
→ governed downstream object
→ reason for potential impact
```

## Tests

Cover direct impact, no impact, historical-only references, unknown relation, cross-tenant isolation when tenant-scoped downstream objects are involved, and no mutation assertions.

## DoD 01E

For any meaningful upstream change, Carbono Zero can answer:

> What existing governed objects might require review, and why?

without modifying them.

---

# SOURCE-WATCH-01F — REVIEW QUEUE & HUMAN GOVERNANCE

## Objective

Provide a durable, auditable review workflow for source changes that require human attention.

Before adding a model, audit whether an existing generic professional/review/problem workflow can safely represent this authority.

Do not overload an environmental problem model if its semantics are different.

If a dedicated authority is required, create the minimum domain needed conceptually equivalent to:

```text
SourceWatchReviewItem
SourceWatchReviewDecision
```

## Lifecycle

Conceptually:

```text
open
acknowledged
resolved
superseded
```

or repository-consistent equivalents.

Human actions must record:

```text
actor
timestamp
decision/note
source/change reference
impact assessment reference
```

Review resolution does NOT automatically apply downstream domain changes.

It only records that the source-watch item was reviewed.

Any actual factor/legal/mapping/etc transition must use that domain's existing governed service.

## Deduplication

Repeated watch executions must not generate duplicate open review items for the same immutable source change + affected authority.

## Security

Global source review requires appropriate global/admin permission.

Tenant-specific impact views must respect tenant boundaries.

No IDOR.

## Tests

Lifecycle, immutability/history, duplicate prevention, permissions, concurrent acknowledgement/resolution, downstream non-mutation.

## DoD 01F

A meaningful official-source change can become a durable human review task without silently changing system truth.

---

# SOURCE-WATCH-01G — RESILIENT WATCH ORCHESTRATION

## Objective

Create an orchestration service that can watch multiple active sources safely using existing source-specific sync commands/services.

Do not rewrite each connector into one giant function.

## Execution rules

A watch cycle should support:

```text
all active sources
one source
source subsets
health-only / no-fetch mode when useful
dry-run assessment where meaningful
```

Respect existing connector rate limits and source behavior.

Do not bypass upstream politeness controls.

## Failure isolation

One failed source must not prevent independent sources from being assessed.

Result must report per source:

```text
attempted
success/failure
sync run
change count
review count
health after run
error (sanitized)
```

## Concurrency

Existing `SourceState.SYNCING` / row locks must remain authoritative when appropriate.

Two workers must not perform conflicting syncs for the same source.

If stale `SYNCING` recovery is needed, implement only with a safe explicit lease/timeout contract; never blindly reset a live worker.

## Retry

Do not create infinite retries.

Bound retries when supported.

Respect `Retry-After`/connector-specific semantics if existing connector layers expose them.

Permanent validation/security errors should not be retried blindly.

## Tests

One-source success, one failure among many, same-source concurrency, bounded retry, partial completion, idempotent re-run, sanitized errors.

## DoD 01G

Carbono Zero can run a complete source-watch cycle without one bad upstream source corrupting or blocking unrelated source truth.

---

# SOURCE-WATCH-01H — OPERATIONAL API & OBSERVABILITY

## Objective

Expose source-watch status to authenticated authorized users/operators.

Provide read APIs sufficient for an environmental/admin operations view.

At minimum consider:

```text
sources overview
source detail
health/freshness
recent sync runs
recent changes
impact assessments
open review items
review history
```

Do not expose raw secret-bearing upstream responses.

Do not expose arbitrary full raw snapshots through convenience endpoints if existing controlled detail APIs already govern them.

## Filtering

Useful filters may include:

```text
source
health
freshness
change classification
severity
requires_review
review status
date range
```

## Performance

Avoid N+1 across source/run/review lists.

Paginate potentially large change/review histories.

Add query-count tests where valuable.

## Operational summary

A system-level summary should be able to answer:

```text
sources total
healthy
near stale
stale
errors
never synced
currently syncing
changes since X
open reviews
review-required impacts
```

## Tests

Authentication, permissions, filters, pagination, query count, error redaction and tenant/global boundaries.

## DoD 01H

An operator can understand environmental-source health and pending source-change review work without database access.

---

# SOURCE-WATCH-01I — CONTINUOUS WATCH COMMAND / SCHEDULING READINESS

## Objective

Make SOURCE-WATCH operable repeatedly without depending on a developer manually invoking individual connector commands.

Implement a management command conceptually equivalent to:

```text
watch_environmental_sources
```

Adapt naming to repository conventions.

## Command requirements

Support safe options such as:

```text
--source <code>
--all-active
--health-only
--dry-run where semantically valid
--continue-on-error
```

Do not invent flags with unsafe semantics.

Return machine-readable summary option if useful for operations.

Exit non-zero when policy says the watch cycle itself failed; distinguish upstream source failures in structured output.

## Scheduling

Audit whether the project already has a scheduler/worker infrastructure.

If it does:

- integrate minimally and safely;
- do not create a second scheduler.

If it does NOT:

- do NOT add Celery/Redis merely for this ticket;
- document cron/systemd timer invocation as production-ready operational options;
- keep command idempotent and concurrency safe.

Suggested cadence must come from source policy; do not schedule every source at the same arbitrary interval.

## Dry production runbook

Document exact commands but DO NOT run production syncs/deploy from this mission's implementation work unless explicitly authorized separately.

## Tests

Command selection, inactive source skip, failure codes, continue-on-error, repeat execution, concurrent invocation safeguards.

## DoD 01I

SOURCE-WATCH can be scheduled by ordinary infrastructure without embedding business logic in cron/systemd itself.

---

# SOURCE-WATCH-01J — CLOSURE & ENVIRONMENTAL PLATFORM READINESS

This phase adds no new product features.

It closes the environmental roadmap.

## 1. Authority audit

Review SOURCE-WATCH 01A–01I plus the source infrastructure built before it.

Confirm one authority for each concept:

```text
source registry
source state/freshness
sync history
immutable external observation
current external record
normalized change
source-specific interpretation
downstream impact
human source-review state
watch orchestration
```

Remove real duplicate authority.

Do not perform giant cosmetic refactors.

## 2. Multi-source E2E

Build an isolated E2E that exercises at least:

```text
healthy unchanged source
changed source
source failure with last-known-good data
source requiring human review
```

Use existing connector fixtures/fakes and official captured fixtures where available.

No production mutations.

The E2E should demonstrate:

```text
watch cycle
→ sync/observation
→ change detection
→ source classifier
→ impact routing
→ review queue
→ operator API
```

## 3. Source-specific E2E

At minimum include meaningful paths across representative domains that actually exist in the repository, ideally including:

- ÖKOBAUDAT/material source change;
- legal/regulatory source change;
- another data/geospatial/regulatory source.

Do not fabricate domain behavior absent from the repo.

## 4. Last-known-good E2E

Demonstrate:

```text
source previously synchronized successfully
→ new watch fails
→ SourceState reports error
→ freshness/health reflects failure
→ previous immutable data remains available
→ no governed downstream truth is rewritten
```

## 5. Disappearance safety

Demonstrate:

```text
authoritative full snapshot
→ missing record may be marked missing
```

and:

```text
incremental/non-authoritative observation
→ unseen record is NOT falsely marked disappeared
```

## 6. Historical reconstruction

A review/impact item must remain explainable from persisted source/run/snapshot information without refetching upstream.

## 7. Security audit

Verify:

- authentication;
- RBAC;
- global-source permissions;
- tenant isolation for tenant impacts;
- IDOR protection;
- error sanitization;
- URL/connector validation;
- no secret persistence in source errors/metadata;
- immutable snapshot/history protections;
- guarded state transitions.

## 8. PostgreSQL/concurrency audit

Use real PostgreSQL for:

- same-source concurrent watch attempts;
- review deduplication;
- review transition concurrency;
- immutable history constraints/triggers if added;
- migrations forward/reverse where contractually supported.

## 9. Regression policy

Run all SOURCE-WATCH tests.

Run knowledge/source connector tests.

Run MATERIAL-DATA regression.

Run MATERIAL-INTELLIGENCE regression.

Run the broad backend regression required by the project.

Use the documented pre-existing regression baseline from the current closure docs.

Do not fix unrelated domains merely to manufacture a perfect global count.

But any NEW failure caused by SOURCE-WATCH must be fixed.

If a broad regression fails and you modify code to fix it, re-run the same broad regression completely.

Final report must clearly state:

```text
SOURCE-WATCH tests: X/X PASS
new failures: 0
known pre-existing failures: <documented count/set>
```

## 10. Schema/check gates

Run:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```

All must be clean.

## 11. Documentation

Create/update:

```text
docs/SOURCE-WATCH-01-CLOSURE.md
docs/SOURCE-WATCH-01-HANDOFF.md
```

Closure documentation must include:

- architecture;
- authorities;
- source registry/policies;
- health/freshness semantics;
- change semantics;
- domain classifiers;
- downstream impact routing;
- human review workflow;
- orchestration;
- APIs;
- management commands;
- scheduling runbook;
- concurrency;
- security;
- tests;
- migrations;
- known limitations;
- production gate commands.

Final handoff must say:

```text
STATUS: COMPLETE
ENVIRONMENTAL ROADMAP: COMPLETE
NEXT MACROPHASE: BUILD-INTELLIGENCE / BUILD-ARCH-00
```

Do not begin BUILD-INTELLIGENCE.

---

# 5. GLOBAL DEFINITION OF DONE

Do not declare SOURCE-WATCH complete until Carbono Zero can answer deterministically and audibly:

1. What official sources are registered?
2. Which are active?
3. What connector governs each?
4. What authority/publisher does each represent?
5. What watch cadence/freshness policy applies?
6. When was the last attempt?
7. When was the last successful observation?
8. Is the source healthy now?
9. Is it fresh, near stale, stale, partial, error, syncing or never synchronized?
10. Does a last-known-good version exist?
11. What upstream version/checksum/HTTP metadata do we know?
12. What did the latest completed sync observe?
13. Which records were created?
14. Which records changed?
15. Which were unchanged?
16. Which can safely be considered disappeared?
17. Was the observation authoritative enough to infer disappearance?
18. What immutable snapshot proves a change?
19. What was the previous snapshot when applicable?
20. What source-specific meaning does the change have?
21. Is its impact known or unknown?
22. What deterministic severity/review requirement was assigned?
23. What governed downstream objects may be affected?
24. Why may each object be affected?
25. Were any downstream objects automatically modified? The answer must be NO unless an existing explicitly governed domain command was separately invoked by a human.
26. Is there an open human review item?
27. What immutable source change created it?
28. Has it been acknowledged/resolved?
29. Who performed the review action?
30. Did resolving the watch item silently mutate factor/legal/mapping/calculation truth? The answer must be NO.
31. Can repeated watch execution run idempotently?
32. Can one source fail without blocking independent sources?
33. Can two workers safely avoid conflicting synchronization of one source?
34. Are errors sanitized?
35. Are source secrets absent from persisted/displayed errors?
36. Can an operator inspect source health through an authenticated API?
37. Can change/review lists be filtered and paginated?
38. Can the whole watch cycle be launched from one management command?
39. Can ordinary cron/systemd/scheduler infrastructure invoke it safely?
40. Does the command avoid embedding arbitrary source-specific business truth?
41. Can a prior review/impact be reconstructed without calling upstream again?
42. Are historical snapshots immutable?
43. Does an upstream outage preserve the previous trusted data?
44. Does an incremental source avoid false disappearance events?
45. Can an unknown source-domain change fail closed into human review?
46. Are MATERIAL-DATA and MATERIAL-INTELLIGENCE authorities unchanged?
47. Does SOURCE-WATCH introduce any new scientific truth authority? It must not.
48. Does SOURCE-WATCH introduce any new legal truth authority outside existing governance? It must not.
49. Are all new SOURCE-WATCH tests green?
50. Are there zero new broad-regression failures attributable to SOURCE-WATCH?

If any answer relies on guessing, mutable history, hidden fallback or AI-generated truth, SOURCE-WATCH is not complete.

---

# 6. GLOBAL NEGATIVE TESTS

Automated evidence must prove these do NOT happen:

```text
upstream request failed
→ delete last trusted data
```

```text
record absent from an incremental page
→ mark record disappeared
```

```text
official factor changed
→ silently replace active factor
```

```text
law/source changed
→ silently rewrite governed legal conclusion
```

```text
source changed
→ AI decides impact severity as authority
```

```text
review item resolved
→ downstream mutation automatically applied
```

Correct pattern:

```text
official source observation
→ immutable evidence
→ deterministic change interpretation
→ deterministic impact routing
→ explicit human review where required
→ existing governed domain command if a human later chooses an action
```

---

# 7. ANTI-OVERENGINEERING

Do not add infrastructure because it is fashionable.

Specifically:

- no Kafka;
- no event bus unless one already exists and is clearly required;
- no Celery/Redis only for SOURCE-WATCH if the project has no scheduler infrastructure;
- no Elasticsearch;
- no Neo4j;
- no vector DB;
- no second source registry;
- no second snapshot store;
- no second sync-run model;
- no generic workflow engine unless an existing one can be reused safely;
- no AI dependency for core watch behavior.

Prefer boring, deterministic PostgreSQL + Django services + existing connector architecture.

---

# 8. PRODUCTION SAFETY

During implementation/testing:

- do not SSH to production;
- do not deploy;
- do not run production migrations;
- do not run mass production source syncs;
- do not modify real production mappings/factors/legal state.

Use local/isolated PostgreSQL and fixtures.

Document exact production commands in the closure runbook.

---

# 9. GIT POLICY FOR THIS MISSION

During implementation:

- do not create intermediate commits merely to checkpoint subphases;
- do not push partial SOURCE-WATCH work;
- do not force-push;
- do not reset/delete legitimate user work.

When and ONLY when the entire SOURCE-WATCH-01 macrophase is COMPLETE and all final gates are satisfied:

1. update closure and handoff docs with `STATUS: COMPLETE`;
2. inspect `git status` and `git diff`;
3. stage only legitimate SOURCE-WATCH changes and necessary blocker fixes documented by the mission;
4. create one final macrophase commit with a clear message such as:

   `SOURCE-WATCH-01 complete`

5. run `git fetch origin main`;
6. if `origin/main` advanced, integrate it safely using a normal non-destructive rebase/merge as appropriate;
7. never use force push;
8. after conflict resolution, re-run any gates affected by code conflicts;
9. push directly to:

   `origin main`

10. confirm the remote `main` points to the completed SOURCE-WATCH commit and the working tree is clean.

If SOURCE-WATCH is incomplete because of a real usage/token/tool limit:

- do NOT commit/push an incomplete macrophase merely to claim completion;
- write the handoff and stop.

---

# 10. CHECKPOINT POLICY

After every completed subphase update silently:

`docs/SOURCE-WATCH-01-HANDOFF.md`

Example:

```text
01A PASS
01B PASS
01C PASS
01D IN PROGRESS
01E PENDING
01F PENDING
01G PENDING
01H PENDING
01I PENDING
01J PENDING
```

Continue automatically.

---

# 11. FINAL RESPONSE — COMPLETE

Only after final commit + successful direct push to `origin/main`, respond once with:

```text
SOURCE-WATCH-01 — COMPLETE

01A PASS
01B PASS
01C PASS
01D PASS
01E PASS
01F PASS
01G PASS
01H PASS
01I PASS
01J PASS

SOURCE-WATCH tests: X/X PASS
Knowledge/source regression: PASS
MATERIAL-DATA regression: PASS
MATERIAL-INTELLIGENCE regression: PASS

Broad regression:
passed: X
known pre-existing failures: Y
new failures: 0

PostgreSQL: PASS
Security/RBAC: PASS
Source health/freshness: PASS
Change detection: PASS
Impact routing: PASS
Human review governance: PASS
Watch orchestration: PASS
Scheduling readiness: PASS
Migrations/schema: PASS
Historical reconstruction: PASS

Commit: <sha>
Push: origin/main PASS
Production deploy: NOT EXECUTED

ENVIRONMENTAL ROADMAP: COMPLETE
NEXT: BUILD-INTELLIGENCE / BUILD-ARCH-00
```

Then provide a concise implementation report and exact human production-gate commands.

STOP.

Do not start BUILD-INTELLIGENCE.

---

# 12. FINAL RESPONSE — LIMIT/HANDOFF

Only if a real execution limit prevents continuation:

```text
SOURCE-WATCH-01 — HANDOFF REQUIRED

Completed:
...

Current:
...

Last verified gate:
...

Remaining:
...

Repository state:
...

Handoff:
docs/SOURCE-WATCH-01-HANDOFF.md

Resume exactly with:
...
```

Do not claim COMPLETE.

---

# 13. START CONDITION

Before starting this mission, verify:

```text
docs/MATERIAL-INTELLIGENCE-HANDOFF.md
STATUS: COMPLETE
```

If Material Intelligence is still in progress, do not start SOURCE-WATCH yet.

Once that condition is true, begin immediately at `SOURCE-WATCH-01A` and continue autonomously through `SOURCE-WATCH-01J` without asking the user between phases.
