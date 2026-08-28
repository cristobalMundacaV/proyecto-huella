# ARQ-12 — Legacy Retirement

## Decision rule

Legacy is retired only when the repository has a canonical replacement with equivalent
tenant scope, payload/response semantics, persistence, historical-data coverage and an
identified consumer cutover. A model or endpoint is not dead merely because the current
SPA does not call it: public compatibility APIs and persisted historical rows remain
contracts until an explicit migration proves otherwise.

## Final inventory

| Legacy piece | Classification | Active consumers / reason |
| --- | --- | --- |
| `FactorEmision` | KEEP COMPATIBILITY / READ-ONLY frontend | Factor catalogue UI and legacy factor API still read it; imports and public endpoints retain write compatibility. `FactorAmbiental`/`VersionFactorAmbiental` do not provide a demonstrated drop-in API/data migration. |
| `RegistroEmision` | KEEP COMPATIBILITY / BLOCKED | Emission APIs, aserradero capture, evidence compatibility modal, historical reporting/intelligence/governance and forestal services still read or write it. Modern capture, Environmental Engine and Calculation do not write it. Retirement requires historical data and API migration. |
| `TransporteObra` | KEEP COMPATIBILITY / BLOCKED | Public obra transport endpoint and historical model contract remain. Its `save()` synchronizes a `RegistroEmision` with fixed legacy science, so removal requires a data/API cutover to `ViajeOperacional` and Calculation. |
| `TransporteLoteForestal` | KEEP COMPATIBILITY | Aserradero lot UI and forestal endpoints actively read/write it. There is no proven one-to-one replacement preserving lote lineage and current responses. |
| `AccionAmbiental` | BLOCKED | Unmanaged (`managed=False`) external compatibility table with active decision, closure, priority and reporting consumers. `AccionMejoraAmbiental` is canonical for the modern Improvement loop but is not a data-compatible replacement. |
| `DocumentoAmbiental` | BLOCKED | Compliance, executive reporting, contextual services and public document endpoints actively consume it. `EvidenciaObra`/`VersionEvidencia` preserve provenance but do not yet replace compliance variables/status contracts. |
| Legacy Compliance (`LimiteNormativoAmbiental`, `VariableAmbientalExtraida`, `AlertaCumplimientoAmbiental`) | KEEP COMPATIBILITY / BLOCKED | Current Compliance persists and evaluates these records. ARQ-08 contracts them without changing persistence. Replacement requires schema/data/API work. |
| Diagnostics/capabilities (`DiagnosticoAmbientalInicial`, `ElementoDiagnosticoAmbiental`, `CapacidadAmbiental`, `CapacidadOrganizacion`, `AreaCapacidadAmbiental`, `AplicabilidadCapacidadObra`) | KEEP COMPATIBILITY | Onboarding, work applicability, navigation and Foundation services remain active consumers. They currently hold product configuration truth despite their legacy module location. |
| Forestry/material compatibility (`LoteForestal`, `EspecieMadera`, `MaterialConstruccion`, `DatoACV`) | KEEP COMPATIBILITY | Aserradero, lifecycle, scenario and forestal carbon consumers remain active. Materials V2 has not migrated their historical rows or external contracts. |
| `ConfiguracionOrganizacion`, historical/context helpers | READ-ONLY or KEEP COMPATIBILITY | Existing reports, environmental context and configuration endpoints still depend on them. No safe removal was demonstrated. |

No audited runtime item is classified `SAFE TO REMOVE` at model/table/backend-endpoint
level. Removing any blocked persistence item requires a separately approved data/schema
migration, so ARQ-12 does not execute one.

## Consumers migrated or retired

The repository contained frontend API exports with no static consumer anywhere under
`frontend/src`. They were removed without changing backend endpoints:

- obsolete obra-detail aggregator that performed parallel legacy emission/evidence/
  transport reads;
- unused `TransporteObra` write client;
- unused `FactorEmision` create/update clients;
- unused legacy apply-factor client;
- unused direct `RegistroEmision` preview/confirm import clients, including organization
  variants;
- unused re-exports from the obra feature service.

The active readers/writers were intentionally not migrated:

- `ImportarEvidenciaObraModal` → `createRegistroEmision`;
- aserradero manual record → organization `RegistroEmision` compatibility API;
- aserradero lote transport → `TransporteLoteForestal`;
- factor catalogue → legacy factor read endpoint.

Replacing these paths would alter persistence or response semantics without demonstrated
parity. The new frontend architecture test freezes the three remaining visible legacy
write consumers and proves the removed symbols have no consumer. Existing backend
application-layer tests continue guarding modern selectors/policies/services from new
legacy dependencies.

## Dual reads and writes

- Modern Unified Capture, sector flows, Calculation and Environmental Engine V2 do not
  create `RegistroEmision`.
- Legacy emissions/import/environmental-record services retain isolated writes.
- `TransporteObra.save()` and `TransporteLoteForestal.save()` retain their historical
  synchronization to `RegistroEmision`; this is an explicit blocked dual-write boundary.
- Reporting, intelligence and compliance still contain legacy reads for historical
  compatibility. They were not silently redirected to incomplete modern datasets.
- `AccionAmbiental` and `AccionMejoraAmbiental` remain separate workflows; no dual write
  or inferred conversion was introduced.

## Validation

PostgreSQL 16 (`connection.vendor == postgresql`):

- broad architecture/modern-flow matrix: 350 tests, 347 passed and 3 pre-existing
  baseline errors;
- focused legacy/ingestion/quality/intelligence matrix: 123 tests, 122 passed and the
  same pre-existing `DocumentoAmbiental` error;
- known errors: Construction V1 ingestion does not create the expected
  `ActividadOperacional`; `DocumentoAmbientalSerializer` passes the nonexistent
  `perfil_ambiental` field (Compliance and RBAC manifestations);
- no new ARQ-12 backend regression was observed.

Other gates:

- frontend tests: 41 passed, 0 failed;
- frontend ESLint: passed;
- frontend production build: passed; existing large-chunk advisory remains;
- `manage.py check`: passed against PostgreSQL;
- `makemigrations --check --dry-run`: no changes detected;
- `compileall`: passed;
- `git diff --check`: passed;
- repository-wide Black check: existing baseline is not clean (131 pre-existing files
  would be reformatted); ARQ-12 changed no Python file and did not perform a bulk rewrite.

## Migrations and remaining debt

ARQ-12 requires **no migration for the changes implemented here**.

Future retirement of `RegistroEmision`, transport, `DocumentoAmbiental`, compliance
persistence or unmanaged `AccionAmbiental` does require a controlled data/schema/API
migration and consumer cutover. The two known PostgreSQL failures and the repository-wide
Black baseline must be handled independently rather than hidden by this phase.

## Closure

**ARQ-12 CLOSED.** Safe dead frontend compatibility clients were removed and protected
by tests. Every remaining legacy dependency has an active consumer or a demonstrated
data/schema/API blocker; no historical data, scientific result, endpoint or backend
contract was changed.
