# ARQ-13 — Contracts / Tests / Docs

## Final contract chain

```text
Operational Kernel
  FuenteDatos → ActividadOperacional → Observacion
  EvidenciaObra → VersionEvidencia (provenance)
        ↓
Unified Capture
  manual / ingestion / documents / API / IoT / sector adapters
        ↓
Environment
  deterministic interpretation → RegistroFlujoAmbiental + explanation
        ↓
Calculation
  governed methodology/factor/version → immutable technical snapshot + impacts
        ↓
Compliance
  deterministic comparison of results/facts against governed requirements
        ↓
Improvement
  problem → human-selected action → measurement → BASE/RESULT snapshots → result/cycle
        ↓
Intelligence
  bounded context and proposals only; confirmation is human and authority remains deterministic
        ↓
Reporting / Professional
  read derived truth, preserve snapshots/audit, and never rewrite Operational Kernel truth implicitly
        ↓
Frontend
  presents backend-owned capture, eligibility, provenance and authority states without recomputing them
```

### Authority at each boundary

| Boundary | Owns | Must not own |
| --- | --- | --- |
| Operational Kernel | tenant-scoped operational facts and their atomic observations | impact, compliance or AI decisions |
| Unified Capture | channel convergence, actor/source/context and provenance | invented missing values or environmental calculation |
| Environment | explainable classification and scientific-eligibility input | formulas, factors or numerical result authority |
| Calculation | deterministic formulas, units, factors, snapshots and impacts | operational capture or compliance decisions |
| Compliance | requirement classification and deterministic evaluation | measurements, invented limits or AI judgement |
| Improvement | verified action/measurement/reevaluation lifecycle | closure by generic PATCH, dates alone or AI |
| Intelligence | bounded reads, structured proposals and prepared commands | calculation, compliance, verification, closure or unconfirmed mutation |
| Reporting/Professional | immutable presentation/audit and authorized existing correction workflows | silent mutation of operational truth |
| Frontend | navigation, human-readable state and explicit confirmation | duplicated domain rules or scientific inference |

Tenant, work and workspace ownership is enforced before each domain transition. A
cross-tenant relation remains a 404 when locating an inaccessible resource and a 400
when the submitted payload contains an invalid in-scope relation, according to the
existing endpoint contract.

## Documentation index

| Phase | Canonical document | Contract frozen |
| --- | --- | --- |
| ARQ-02 | `ARQ_02_MODEL_MODULARIZATION.md` | physical model ownership and legacy isolation |
| ARQ-03 | `ARQ_03_APPLICATION_LAYERS.md` | API/selectors/services/policies |
| ARQ-04 | `ARQ_04_OPERATIONAL_KERNEL.md` | operational entities, scope and invariants |
| ARQ-05 | `ARQ_05_UNIFIED_CAPTURE.md` | capture envelope and channel convergence |
| ARQ-06 | `ARQ_06_CONSTRUCTION_V1_FLOWS.md` | seven construction flow contracts |
| ARQ-07 | `ARQ_07_GENERIC_ENVIRONMENTAL_ENGINE.md` | interpretation and eligibility boundary |
| ARQ-08 | `ARQ_08_REQUIREMENTS_COMPLIANCE.md` | requirements and deterministic compliance |
| ARQ-09 | `ARQ_09_IMPROVEMENT_LOOP.md` | verified improvement authority |
| ARQ-10 | `ARQ_10_INTELLIGENCE_BOUNDARIES.md` | AI authority matrix and human confirmation |
| ARQ-11 | `ARQ_11_FRONTEND_ALIGNMENT.md` | canonical frontend state and provenance presentation |
| ARQ-12 | `ARQ_12_LEGACY_RETIREMENT.md` | final legacy inventory and safe retirement boundary |

The documents above are normative architecture contracts. Historical test counts inside
them describe their individual closure points; the consolidated baseline below is the
official pre-E2E reference.

## Gates

Existing gates protect model module/table identity, selector immutability, policy purity,
service/DRF separation, tenant/RBAC isolation, legacy import allowlists, Operational
Kernel invariants, capture convergence, seven-flow contracts, environmental
classification, deterministic requirements, Improvement closure and AI authority.

ARQ-13 adds `test_architecture_contracts_final.py`, which verifies:

1. every closed phase ARQ-02..12 has a versioned document with an explicit closure;
2. the official test runner accepts PostgreSQL only and validates the runtime vendor;
3. every critical suite exists and has no explicit SQLite/configuration override;
4. this final contract contains every domain boundary and a debt register.

The frontend legacy-boundary gate introduced by ARQ-12 remains part of `npm test` and
prevents expansion of visible legacy writers.

## Official PostgreSQL baseline

The only certifying command is:

```powershell
python backend/scripts/run_tests_postgres.py [test labels]
```

The runner rejects non-PostgreSQL engines, non-loopback hosts and database names that do
not end in `_test`; it also verifies `connection.vendor == "postgresql"` before invoking
Django. Direct `manage.py test` with default settings is not an architectural gate because
the development fallback remains SQLite for historical convenience.

Baseline consolidated immediately before E2E:

| Matrix | Result | Interpretation |
| --- | --- | --- |
| Complete backend suite | 584 run; 583 pass; 1 known error | official pre-E2E baseline |
| Architecture-only gate | 94/94 pass | includes the four final ARQ-13 contract gates |
| Repaired Foundation/Onboarding/Compliance/RBAC contracts | 47/47 pass | confirms the six historical failures are closed |
| Frontend unit/contract tests | 41/41 pass | includes canonical state, errors and legacy boundary |
| Frontend ESLint/build | pass/pass | build retains the known chunk-size advisory |
| Django check/migrations | pass / no changes | executed with PostgreSQL environment |
| Compileall/diff-check | pass/pass | source integrity clean |
| Black repository-wide | baseline not green | 131 pre-existing Python files would be reformatted; no ARQ-13 runtime Python was changed |

## Known historical failures

One failure predates ARQ-13 and reproduces without a scientific or contract change:

1. `ConstructionV1IntegrationTests.test_ingestion_resolves_work_into_activity` expects
   `ActividadOperacional(codigo=ING-...)`, but the fixture does not produce it.

ARQ-13 closed six historical failures while consolidating their contracts:

- `ObraSerializer` now owns the already-defined project-type → environmental-profile
  derivation that had been physically misplaced in `DocumentoAmbientalSerializer`;
- Compliance and RBAC document creation no longer receive the invalid
  `perfil_ambiental` model argument;
- the Foundation fixture now uses valid Unicode for `Edificación habitacional`;
- three onboarding tests now use the current area/flow catalogue, the four-step review
  contract, and the explicit rule that onboarding does not create declarative diagnostic
  rows or automatic area-flow relations.

No test in the critical matrix imports SQLite or overrides `DATABASES`. The PostgreSQL
runner, rather than test-local database assumptions, owns database selection.

## Debt register

| ID | Debt | Owner | Required later phase | Exit condition |
| --- | --- | --- | --- | --- |
| D-01 | Construction ingestion fixture/activity mismatch | Operational Kernel + Ingestion | pre-E2E defect stabilization | expected canonical activity is produced or expectation is contractually corrected |
| D-04 | `RegistroEmision`, transports and document/compliance persistence remain active legacy | Legacy migration program | separately approved data/API migration | historical rows and consumers migrated with parity and rollback |
| D-05 | unmanaged `AccionAmbiental` compatibility workflow | Improvement + platform data owner | external-table migration program | ownership, data migration and endpoint cutover approved |
| D-06 | legacy factor catalogue frontend/read API | Governance + Frontend | factor consumer migration | V2 catalogue proves payload, scope and historical parity |
| D-07 | 131 Python files outside Black baseline | Developer Experience | formatting-only maintenance window | repository-wide Black check passes without mixing domain changes |
| D-08 | large frontend production chunks | Frontend platform | performance maintenance | agreed bundle budget and code-splitting gate pass |
| D-09 | browser-level end-to-end coverage pending | QA/E2E | next explicitly authorized E2E phase | tenant/capture/calculation/compliance/improvement/AI journeys pass in browser |

No debt is silently assigned to an unspecified future architecture phase. Schema/data
migrations require explicit authorization and are not part of ARQ-13.

## Closure

**ARQ-13 CLOSED.** The cross-domain contracts, PostgreSQL-only certification path,
critical test matrix, historical failures and owned debt are consolidated before E2E.
No schema, scientific rule or API contract changed. The only runtime repair restores the
existing obra-profile serializer contract and removes an invalid field from legacy
document creation.
