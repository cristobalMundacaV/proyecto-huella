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

ARQ-03A stops here; ARQ-03B is not started.
