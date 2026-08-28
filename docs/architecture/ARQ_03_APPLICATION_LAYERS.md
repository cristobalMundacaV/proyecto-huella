# ARQ-03 — Application Layers

## Baseline and global audit

ARQ-03 starts from `c8628b1`, after ARQ-02 closed the physical model split. The
inventory was generated from the current tree: 38 API/view files, 64 service files,
13 serializer files and `permissions.py`, containing 889 top-level functions/classes.
This is a responsibility inventory, not evidence that every symbol needs extraction.

Current classification:

| Area | Current responsibilities | Target |
|---|---|---|
| `views*.py` | HTTP, serializers, queries, mutations and some decisions | API; delegate reads/writes/decisions |
| `serializers*.py` | validation, representation and several create/update hooks | Serializer boundary; mutation extraction by slice |
| `services/` | commands, selectors, calculations, AI and compatibility mixed by generation | Commands remain; reads migrate to selectors; decisions to policies |
| `permissions.py` | permission catalogue, membership reads and access decisions | Preserved public compatibility facade; policies extracted incrementally |

The detailed global audit is intentionally sliced. Functions are classified by
observable effects: view functions are **API/MIXED**, functions performing
`save/create/update/delete` are **COMMAND/SERVICE**, queryset/aggregation-only
functions are **QUERY/SELECTOR**, deterministic eligibility/authorization functions
are **POLICY**, and compatibility consumers remain **LEGACY**. No big-bang move is
authorized.

## Layer contracts

- API owns HTTP parsing, serializers, authentication context, responses and status.
- Services orchestrate commands, transactions and writes; they do not receive or
  return DRF `Request`/`Response` objects.
- Selectors perform scoped reads and aggregation only; they never mutate or call a
  service.
- Policies make deterministic, explainable decisions; they do not write, call HTTP,
  AI or hidden fallbacks.

Tenant 404 behavior, RBAC, work/workspace scope and current superuser exceptions are
part of the compatibility contract. URLs, methods, payloads, response shapes,
serializer contracts and status codes remain unchanged.

## Confirmed slice roadmap

Dependency direction in the repository confirms this sequence:

1. **ARQ-03A:** Platform, Operational Context and Foundation boundary.
2. **ARQ-03B:** Operational Data and Assets.
3. **ARQ-03C:** Provenance and Ingestion.
4. **ARQ-03D:** Environmental Flows, Transport and Materials.
5. **ARQ-03E:** Governance, Calculation, Indicators and Quality.
6. **ARQ-03F:** Improvement and Compliance.
7. **ARQ-03G:** Intelligence, Professional and Reporting.
8. **ARQ-03H:** legacy boundary audit.

The order follows Platform → Operations → Ingestion → Environment, with Governance
supporting deterministic calculation/compliance and read-oriented layers last.

## ARQ-03A

### Changes

`selectors/platform.py` now owns tenant-scoped organization lookup.
`selectors/operational_context.py` owns workspace, area and evidence querysets.
`services/platform.py` owns the existing explicit organization-deletion transaction.
`services/operational_context.py` owns area/workspace/evidence creation while retaining
the existing context compatibility facade. `policies/platform.py` owns the named
organization-administration decision.

The affected views retain only HTTP branching, permission invocation, input extraction,
serialization and response selection. Existing helper names in views are preserved where
external tests/consumers may import them.

### Before/after call graph

```text
Before: request → view → queryset / decision / write → Response
After:  request → view → selector (read)
                       → policy (decision)
                       → service (write)
                       → Response
```

Foundation legacy models remain untouched. Existing legacy deletion dependencies
(`RegistroEmision`, `TransporteObra`) were moved with their command, not expanded.

### Architectural enforcement

`test_application_layers.py` verifies that ARQ-03A selectors expose no ORM mutation
calls, policies import neither HTTP/DRF nor AI, and services do not depend on DRF
`Response`. Existing endpoint, tenant, RBAC, Foundation and modularization suites remain
the behavioral gate.

### Validation result

- PostgreSQL runtime: `postgresql`; canonical registry: 94 models / 94 unique labels.
- Architectural modularization + application layers + Operational Context: **91/91**.
- Focused ARQ-03A/RBAC sample: **22/23**; the sole error is the approved baseline
  `DocumentoAmbiental(perfil_ambiental)` failure.
- Expanded critical sample: **25/30**, reproducing exactly the five approved PostgreSQL
  failures (three legacy area-catalog assertions, `DocumentoAmbiental` serializer and
  Construction V1 missing activity); no additional or changed failure.
- `manage.py check`, `makemigrations --check --dry-run`, Black check, `compileall` and
  `git diff --check`: clean. No migration or schema change.
- API routes, methods, payloads, serializer use, response shapes/status selection and
  tenant/RBAC calls are preserved in the affected views.

## Known debt

- `resolve_operational_context` still adapts DRF request metadata for compatibility;
  a later Operational Context slice may split extraction from domain resolution.
- Foundation and SaaS views remain mixed and require smaller follow-up extractions.
- `permissions.py` combines membership selectors and policies; its public API remains
  stable until all consumers are mapped.
- The organization deletion command intentionally retains legacy persistence writes.

## Dependency rule

New features must not introduce dependencies on legacy models. An exception requires
explicit justification, a compatibility test and a migration/removal path.

ARQ-03A — PLATFORM / OPERATIONAL CONTEXT APPLICATION LAYERS: **CLOSED**.

ARQ-03A closed at that gate; the subsequent authorized ARQ-03B slice begins below.

## ARQ-03B — Operational Data / Assets

### Audit and ownership changes

The scoped audit found read/filter ownership in both views, mutations and tenant
validation in both serializers, `detalle_actividad` incorrectly living in a service,
and Vehículo/Maquinaria specialization embedded in `ActivoOperacionalSerializer`.

Operational Data now uses:

- `selectors/activity_core.py` for organization/source/activity/observation lookup,
  activity filters, observation filters and the prefetched activity detail;
- `services/activity_core.py` for activity create/update including the `activos` M2M,
  and observation create/update including actor and activity assignment;
- `policies/activity_core.py` for deterministic tenant/context and observation-value
  validation.

Assets now uses:

- `selectors/assets.py` for organization, assets, maintenance and condition reads;
- `services/assets.py` for asset, maintenance and condition mutations and transactional
  Vehículo/Maquinaria specialization;
- `policies/assets.py` for tenant validation of unit, process and source relations.

Serializers retain DRF field contracts and translate policy results to the same
`ValidationError` payloads. Views retain request parsing, serializers, HTTP response and
status selection. Selectors contain no writes; policies import neither DRF nor AI;
services return domain objects rather than `Response`.

### Preserved behavior

- `full_clean()` remains part of every extracted mutation.
- Organization-scoped querysets preserve cross-tenant 404 behavior.
- Invalid payload relations preserve serializer 400 behavior and messages.
- URLs, methods, payloads, ordering, response representations and status codes are
  unchanged.
- `registros_emision_legacy_count` remains a prefetched, read-only compatibility field.
- Vehículo and Maquinaria keep the existing `update_or_create` semantics.
- `PuntoAmbientalOperacional` and sector-flows endpoints were not touched.

### Validation

- Activity Core + Assets: **18/18** on PostgreSQL.
- ARQ-02 modularization + application-layer contracts + ARQ-03A + Activity/Assets:
  **109/109** on PostgreSQL.
- Tenant/RBAC: **10/11**; the only error is the approved historical
  `DocumentoAmbiental(perfil_ambiental)` failure outside ARQ-03B.
- The critical PostgreSQL baseline retains exactly its five documented failures; no
  new or changed failure was observed.
- Django check and migration dry-run pass with no schema changes; Black, compileall and
  diff checks pass.

### Remaining debt

The generic `crear_entidad`/`actualizar_entidad` helpers remain for `FuenteDatos`, whose
mutation has no richer orchestration. Sensor-specific reads remain representation logic
in the observation serializer. Broader permission-module decomposition belongs to later
slices. No legacy dependency was added.

ARQ-03B — OPERATIONAL DATA / ASSETS APPLICATION LAYERS: **CLOSED**.

ARQ-03B closed at that gate; the subsequent authorized ARQ-03C slice begins below.

## ARQ-03C — Ingestion / Provenance

### Audit and ownership changes

The audit confirmed that the ingestion pipeline already lived mainly in
`services/ingestion_v2.py`, but HTTP views still owned scoped process/template queries
and failure persistence, while the service mixed evidence/source/template lookups and
deterministic contract/context decisions with command orchestration.

ARQ-03C introduces:

- `selectors/ingestion.py`: organization/process scoping, user-visible process lists,
  templates, sources, extracted records and mapping reads;
- `selectors/provenance.py`: tenant-scoped evidence lookup and evidence-version sequence;
- `policies/ingestion.py`: context parsing, work-scope access, ingestion contracts,
  structured-payload shape, context/reference/applicability checks and confirmed-state
  immutability;
- the existing ingestion service remains command authority for receive, evidence/version
  creation, checksum persistence, analysis, mapping, preview mutations, confirmation and
  failure-state mutation.

The serializers remain representation-only. Technical parsing, normalization,
classification helpers and destination handlers remain in their established modules;
they were not wrapped or moved for cosmetic reasons.

### Preserved behavior

- The sequence received → analyze → map → preview → confirm is unchanged.
- Confirmed ingestion remains immutable and confirmation remains idempotent.
- Tenant/work 404 behavior and permission-specific hidden-resource responses remain.
- Evidence/version provenance, version numbering, files and SHA-256 checksums remain
  inside the original atomic transaction.
- Suggested versus confirmed classification and confirmed/suggested context remain
  separate.
- Preview and confirmation retain existing response shapes, row errors and states.
- Documentary extraction continues to report the current structured-extraction
  limitation; no data is invented.
- Ingestion still delegates persistence handlers and does not calculate environmental
  impact.
- No dependency on a legacy model was introduced.

### Validation

- Ingestion V2 + multisource: **28/28** on PostgreSQL.
- Provenance/manual atomicity + modularization/application architecture: **99/99**.
- ARQ-03A/B + tenant/RBAC sample: **28/29**; the only error is the approved historical
  `DocumentoAmbiental(perfil_ambiental)` failure outside ARQ-03C.
- The critical baseline retains exactly the five documented PostgreSQL failures and no
  new or changed failure.
- Django check and migration dry-run pass; Black, compileall and diff checks pass.

### Remaining debt

Preview is intentionally a mutating command despite its historical name because it
persists normalized rows and review states. Context policies perform scoped database
reads but no writes. Pandas parsing and destination handlers remain coupled to the
ingestion service and should only be revisited with dedicated compatibility tests.

ARQ-03C — INGESTION / PROVENANCE APPLICATION LAYERS: **CLOSED**.

ARQ-03C stops here; ARQ-03D is not started.

## ARQ-03D — Environmental Flows / Transport / Materials

### Application-layer ownership

- `selectors/environmental_flows.py`, `selectors/transport.py` and
  `selectors/materials.py` own tenant-scoped lists, details, filters and analytical
  querysets. Selectors are read-only.
- `policies/environmental_flows.py`, `policies/transport.py` and
  `policies/materials.py` own deterministic tenant, work and relationship validation.
  They return domain error mappings and have no DRF or mutation dependency.
- The existing domain services own point/record, route/journey and
  material/lot/event mutations, observation creation and analytical orchestration.
  Atomic commands retain `full_clean()` before persistence.
- Views coordinate authentication, HTTP serialization and status codes; serializers
  delegate deterministic validation and mutations to policies and services.

### Compatibility boundaries

Manual sector recording preserves the atomic Evidence → Operational Activity →
Environmental Flow Record chain, current fuel classification and stored-file cleanup.
Transport preserves journeys, routes and derived metrics. Materials preserves lots,
events, lineage and balance. Tenant/workspace/RBAC scoping, cross-tenant 404s, invalid
relationship 400s, URLs, ordering, payloads and response codes remain unchanged.
Modern flows do not write `RegistroEmision` legacy and no environmental calculation was
moved into these domains.

### Validation and remaining debt

The focused Environmental Flows, Transport, Materials and manual-atomicity suite passes
83/83 on PostgreSQL. Application architecture, modularization and tenant/RBAC gates pass
103/103. The critical baseline reproduces only its five previously documented failures.
Django check, migration dry-run, Black, compileall and diff checks pass.

The manual multipart endpoint still assembles serializer input at the HTTP boundary;
the atomic mutation itself remains intentionally cohesive to preserve file rollback and
the public validation contract. Legacy flow aliases remain compatibility-only.

ARQ-03D — ENVIRONMENTAL FLOWS / TRANSPORT / MATERIALS APPLICATION LAYERS: **CLOSED**.

ARQ-03D stops here; ARQ-03E is not started.

## ARQ-03E — Governance / Calculation / Indicators / Quality

### Application-layer ownership

- `selectors/governance.py` owns tenant/global methodology, version, factor and
  professional-review reads.
- `selectors/calculation.py` owns calculation details, activity calculation series and
  user-visible environmental impacts.
- `selectors/quality.py` owns observations/evaluations, discrepancies, confidence
  policies, indicators, comparable periods, baselines and indicator input querysets.
- `policies/governance.py` owns deterministic applicability, structural eligibility,
  transition and professional-review decisions.
- `policies/quality.py` owns source-health, confidence/quality decisions and discrepancy
  relation/resolution validation.
- Existing calculation, methodology, indicator and quality services remain the command
  boundary for calculations, recalculations, version transitions, methodology/formula
  mutations, quality persistence, indicator generation and baseline construction.

### Scientific and compatibility boundaries

No formula, factor, unit conversion, factor selector, methodology rule or calculation
strategy changed. Calculation remains deterministic and AI has no decision path. Formula,
methodology and factor versions, technical snapshots, calculation inputs, environmental
impacts, immutability and recalculation provenance preserve their existing contracts.
Indicator periods, comparable periods, baselines, quality evaluations, discrepancies and
confidence policies preserve their previous behavior. Tenant/RBAC scoping, URLs,
payloads, responses and status codes remain unchanged.

### Remaining debt

Scientific selection helpers retain their established internal query access where moving
it would split a tested scientific decision across layers. Serializer method fields remain
representation-only. Compatibility with historical environmental records is unchanged;
no new dependency on legacy was introduced.

### Validation

- Calculation, methodology/governance, factors and quality: **91/91** on PostgreSQL.
- Focused post-selector calculation, methodology and quality gate: **58/58**.
- Application layers, architecture, modularization and tenant/RBAC: **103/103**.
- The critical baseline retains exactly its five documented failures; no numeric result
  or failure signature changed.
- Django check, migration dry-run, Black, compileall and diff checks pass.

ARQ-03E — GOVERNANCE / CALCULATION / INDICATORS / QUALITY APPLICATION LAYERS:
**CLOSED**.

ARQ-03E stops here; ARQ-03F is not started.

## ARQ-03F — Improvement / Compliance

### Application-layer ownership

- `selectors/improvement.py` owns problem, action, measurement, history, scope,
  indicator, snapshot and reevaluation-cycle reads.
- `selectors/compliance.py` owns document, extracted-variable, normative-limit, alert,
  work-scope and compliance-summary querysets.
- `policies/improvement.py` owns deterministic problem transitions, action selection,
  measurement chronology, evaluation prerequisites and cycle-start rules.
- `policies/compliance.py` owns minimum closure evidence and scoped-work payload rules.
- Improvement services own problem/action/measurement/history mutations and the complete
  Action → BASE Snapshot → RESULT Snapshot → Result → Cycle orchestration.
- Compliance services own mutable compliance entities; the established document
  serializer path remains intact for multipart/M2M compatibility.

### Preserved behavior

Problem → Action → Measurement → Snapshot → Result → Cycle remains unchanged. Modern
closure still depends on deterministic reevaluation, frozen snapshots and results. AI may
propose but cannot verify, transition or close. Existing legacy behavior, requirement
classes, tenant/work RBAC, hidden-resource 404s, invalid-payload 400s, URLs, response
shapes and status codes are preserved. No operational truth or scientific calculation was
moved into Improvement.

### Known debt

The generic problem PATCH can still persist `cerrada` when exposed as serializer-writable
state. This behavior is intentionally preserved by ARQ-03F and is assigned to ARQ-09.
`DocumentoAmbientalSerializer` continues to inject the historical unsupported
`perfil_ambiental` argument; its existing PostgreSQL failure is outside this slice and was
not corrected.

### Validation

- Problems, intervention, reevaluation/snapshots/results and compliance: **39/40** on
  PostgreSQL; the only error is the documented `DocumentoAmbiental(perfil_ambiental)`
  failure outside ARQ-03F.
- Application layers, architecture, modularization and tenant/RBAC: **103/103**.
- The critical baseline retains exactly its five documented failures; no new or changed
  failure was observed.
- Django check, migration dry-run, Black, compileall and diff checks pass.

ARQ-03F — IMPROVEMENT / COMPLIANCE APPLICATION LAYERS: **CLOSED**.

ARQ-03F stops here; ARQ-03G is not started.
