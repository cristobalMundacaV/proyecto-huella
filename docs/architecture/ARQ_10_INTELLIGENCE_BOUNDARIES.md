# ARQ-10 — Intelligence Boundaries

## Authority matrix

| Capability | AI authority | System authority |
| --- | --- | --- |
| Read tenant-scoped context | Allowed | `ContextGateway` and selectors define the projection |
| Read derived Knowledge | Allowed | Only verified persisted cases are exposed |
| Suggest recommendation | Allowed | Structured-output policy validates the proposal |
| Prepare a command | Allowed | Preparation has no operational effect |
| Apply an action | Forbidden | Authenticated human confirmation command |
| Calculate environmental truth | Forbidden | Deterministic Calculation services |
| Decide Compliance | Forbidden | Deterministic requirement evaluation |
| Verify improvement | Forbidden | `ResultadoIntervencion` and reevaluation cycle |
| Close a problem | Forbidden | Verified Improvement transition |

The executable matrix lives in `policies/intelligence.py`. Provider-facing services may
read approved projections and persist proposals/audit milestones, but cannot import the
services that calculate, decide compliance, verify interventions or close actions.

## Read contract and provenance

`ContextGateway` is the only general context boundary for Copilot. It verifies tenant
ownership and returns bounded projections for problems, works, assets, maintenance,
sensors, indicators, evidence, activities, intervention history and organization memory.

The problem projection identifies organization, problem and work; provides only linked
scope, existing KPI values/comparisons, prior cycles/actions, active restrictions,
evidence summary and compact verified Knowledge. Evidence context exposes identifiers,
version numbers and checksums but excludes file contents, extracted text and extraction
metadata. Collection sizes are bounded.

Each proposal records provider/model, context categories, a context-size summary, facts,
assumptions and limitations. `HitoDecisionIA` records context consultation, proposal,
feedback and the later human decision. These references explain what context was offered;
they are not environmental measurements.

## Suggestion and output contract

Copilot output is a proposal with required structured fields:

```text
titulo, descripcion, justificacion, kpis_afectados,
requisitos, riesgos, prioridad, hechos_utilizados,
limitaciones, supuestos
```

Lists, priority and KPI scope are validated deterministically. A proposal may cite only
numeric facts already present in context. It remains a `RecomendacionAgenteAmbiental` and
does not create `AccionMejoraAmbiental`, snapshots, calculations or compliance results.

## Human confirmation gate

Accepting a proposal only prepares `ComandoCopiloto`; it returns
`requiere_confirmacion=true` and has no operational effect. Execution requires all of:

- explicit `confirmed=True` at the application-service boundary;
- an authenticated user;
- command state `preparado`;
- organization/problem/proposal context consistency.

The API and service enforce the same gate. A direct internal call that omits confirmation
is rejected before creating an action, restriction, reevaluation cycle or escalation.
Confirmed execution remains audited with `confirmado_por`, `confirmed_at`,
`HitoDecisionIA(tipo=decision_humana)` and organization memory where applicable.

## Deterministic authorities

- Calculation owns formulas, factors, conversions and numerical environmental truth.
- Compliance compares independently produced results with governed requirements.
- Improvement owns measurements, frozen BASE/RESULTADO snapshots,
  `ResultadoIntervencion`, reevaluation and resolution.
- Professional review retains its existing correction/review authority.
- Knowledge derives reusable cases from persisted intervention results; observed prior
  outcomes never guarantee a future result.

AI output cannot call or replace any of those authorities.

## Fallback and errors

- Provider connection/failure returns the existing 503 response while the environmental
  domain remains operational.
- Invalid structured output is rejected and creates no proposal/action.
- Reevaluation drafts explicitly report that no cycle was started.
- During refutation, user feedback/restriction is preserved if generation of the adjusted
  alternative fails, matching the existing recovery contract.
- No fallback fabricates a recommendation, result, calculation or compliance state.

## Legacy boundary

The intelligence policy, proposal service and command gate introduce no legacy imports or
writes. Existing legacy consumers outside this boundary are unchanged.

## Known debt

- Context audit stores reference categories and size, not an immutable checksum of the
  complete model input; adding one requires a persistence decision.
- The older `EnvironmentalAgentService` and Copilot V2 have overlapping proposal
  contracts; consolidation should preserve their current endpoints and prompts.
- Provider-side prompt enforcement remains defense in depth; deterministic application
  policies are the actual authority boundary.

No schema, model/provider, prompt or external API change is required.

## Validation gate

`test_intelligence_boundaries.py` enforces the executable authority matrix and prevents
provider-facing services from importing deterministic authority services.
`test_copilot_v2.py` verifies that direct command execution without explicit confirmation
does not create an action. Existing Knowledge, Improvement, Compliance, Calculation,
tenant/RBAC and architecture suites remain the regression gate.

- Focused Copilot, Knowledge and authority-boundary gate: **27/27** on PostgreSQL.
- Integrated Intelligence, Knowledge, Improvement, Professional, Compliance, Calculation,
  tenant/RBAC and architecture gate: **136/137**; its only error is the previously
  documented `DocumentoAmbiental(perfil_ambiental)` serializer baseline failure.
- Critical baseline: **25/30**, preserving exactly its five documented failures (three
  obsolete onboarding area-catalog expectations, the same evidence serializer error and
  the missing Construction V1 ingestion activity). No new failure or changed signature
  appeared.
- Django check, migration dry-run, Black, compileall and diff checks pass.

ARQ-10 — INTELLIGENCE BOUNDARIES: **CLOSED**.

ARQ-10 stops here; ARQ-11 is not started.
