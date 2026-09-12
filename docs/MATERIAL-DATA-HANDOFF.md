# MATERIAL-DATA — Handoff / Checkpoint

STATUS: COMPLETE
NEXT MACROPHASE: MATERIAL-INTELLIGENCE

```
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
```

Final full regression: 1097/1125 PASS (apps.knowledge 163/163, apps.analytics 934/962).
The 28 remaining failures are confirmed pre-existing, unrelated to MATERIAL-DATA (see
`docs/MATERIAL-DATA-CLOSURE.md` → "Segundo hallazgo preexistente"). Every
`test_material_*.py` file and the E2E suite: 100% PASS.

Base commit for this loop: `c783750` (MATERIAL-DATA-01D, already committed/pushed to `main`
in a prior turn at the user's explicit request; this loop's own work is uncommitted per its
git policy — no commit, no push until the user gates it).

## 01E — Material Environmental Inventory & Coverage — PASS

Read-only reporting layer, no new models, no new authority. Delegates the terminal
calculable/no_calculable verdict to `material_factor_selector.select_material_factor`
(01D); only adds the granular, structured "why" breakdown for reporting.

**Files:**
- `backend/apps/analytics/services/material_inventory.py` — `reception_coverage(event)`,
  `material_environmental_coverage(organization, ...)`, `material_coverage_detail(...)`.
- `backend/apps/analytics/views_material_inventory.py` — 3 endpoints.
- `backend/apps/analytics/urls.py` — wired under `organizaciones/<id>/materiales-operacionales/...`
  and `.../eventos-materiales/<id>/cobertura-ambiental/`.
- `backend/apps/analytics/test_material_inventory.py` — 22 tests.

**Reason codes implemented:** `observacion_faltante`, `sin_mapping`, `mapping_no_aprobado`,
`mapping_fuera_vigencia`, `sin_version_factor_activa`, `factor_fuera_vigencia`,
`unidad_incompatible`, `dato_calidad_insuficiente` (reused `quality_v2.evaluate_observation_quality`
with `persist=False`, same INSUFFICIENT states `eligibility_v2.py` already blocks on).

**Quantity aggregation:** grouped by physical dimension (masa/volumen/energia) using ONLY
governed `unit_conversion.convert_value` (kg↔t, L↔m3, kWh↔MWh); units outside those
dimensions (e.g. "unidad" piece counts) get their own exact-unit bucket, never merged.
Unrecognized units are counted and excluded, never silently summed.

**Migrations:** none (pure read layer).

**Tests:** 22/22 PASS (PostgreSQL, `test_material01d` @ 127.0.0.1:55441). `manage.py check`
clean. `makemigrations --check --dry-run`: no changes detected.

## 01F — Environmental Data Quality & Suitability — PASS

`services/material_quality.py`: `assess_material_data_quality(candidate)` (pure function
of frozen `initial_eligibility`/`normalization`/`functional_context`) + `assess_factor_data_quality(factor)`
(resolves to origin candidate via `material_source_candidate`, or reports `sin_origen_okobaudat`
for private tenant factors). States: `sufficient`/`requires_review`/`insufficient` (insufficient
reuses 01C's own `compatible`/`reasons` verbatim — no invented hard-fail axis). Endpoint:
`GET /api/environmental-governance/material-factor-candidates/<id>/calidad/` (superuser, same
as sibling candidate endpoints). No migration. Tests: `test_material_quality.py`, 9/9 PASS,
using real A1/A2 upstream fixtures via `test_material_candidates.material_fixture`.

## 01G — Material A1-A3 Accounting Ledger — PASS

No new ledger model — `CalculoAmbiental` (already immutable/append-only) is the ledger.
`services/material_ledger.py`: `current_calculations_queryset`/`current_calculation_for_activity`
(current = the row nothing else's `recalculo_de` points at), `ledger_entries`, `material_ledger_totals`
(Decimal sums grouped by `unidad_resultado`, optional group_by obra/material/categoria/standard/periodo),
`ledger_entry_provenance` (full walk incl. `assess_factor_data_quality`).
**Real pre-existing bug fixed**: `CalculoAmbiental.recalculo_de` had no uniqueness — two concurrent
`recalculate()` calls on the same base calculation could both succeed, leaving two "current" leaves.
Fixed with `UniqueConstraint(fields=["recalculo_de"])` (migration `0069_calculo_recalculo_de_unique`)
+ `IntegrityError`→`ValidationError` translation in `calculation_v2.recalculate()`. Verified with a
real two-thread PostgreSQL concurrency test (`MaterialLedgerConcurrencyTests`) — exactly one wins.
APIs under `organizaciones/<id>/materiales-operacionales/ledger-a1a3/...` (totals/entries/detail).
Tests: `test_material_ledger.py`, 14/14 PASS (incl. concurrency, negative sign, recalculation,
superseded-history, tenant isolation). `test_calculation_v2.py` re-run clean (22/22) after the fix.

## 01H — Human Material Catalog Discovery — PASS

No new search authority — reuses 01C's `Candidate` queryset and exact/classification filters,
but as a NEW read-only surface any authenticated user can hit (`IsAuthenticated`, not superuser),
since the existing `views_material_candidates.py` list is superuser-only and tenant analysts need
to browse before proposing a mapping. `views_material_catalog_discovery.py`:
`GET /api/catalogo-material/` (search: q/status/standard/uuid/dataset_version/location/owner/
dataset_type/input_unit/classification/current/calidad, paginated) and
`GET /api/catalogo-material/<id>/` (walks process → profile → indicators → candidate →
promoted factor → mappings, mappings scoped to the requester's own orgs unless superuser).
No ranking/scoring fields ever present (tested explicitly). **Real N+1 found and fixed**: reusing
`CandidateSerializer.get_eligibility()` in a list context re-runs 01C's expensive live
`evaluate_material_profile` (source_current + snapshot-hash + reference checks) per row — 26
queries for 2 candidates. Fixed by projecting list rows from already-fetched
`select_related`/JSON fields only (frozen `initial_eligibility`, not live re-eval); the single-object
detail endpoint still shows the richer `CandidateSerializer` view since that's one row, not N.
Query-count regression test pins this (`assertNumQueries`). Tests: `test_material_catalog_discovery.py`,
11/11 PASS.

## 01I — Source Refresh & Version Impact Governance — PASS

No new persisted model — impact assessment is a pure read-only diff, so idempotence and
concurrency safety are free (nothing to race on). `services/material_source_impact.py`:
`assess_candidate_impact(candidate)` compares a candidate's frozen provenance against
whatever the *existing* 01A/01B sync has already hydrated locally (fetches nothing new
itself): `no_impact`/`review_recommended`/`review_required` with structured reasons
(`proceso_no_activo`, `nueva_version_disponible`, `nueva_version_no_hidratada_localmente`,
`nueva_version_no_evaluada_como_candidato`, `gwp_modificado`, `unidad_declarada_modificada`,
`standard_modificado`, `republicacion_detectada_mismo_dataset_version`,
`version_local_mas_reciente_que_activa`). `assess_all_candidates()` for the bulk report.
Management command `assess_okobaudat_material_updates` (idempotent, read-only, prints JSON).
Superuser API: `GET /api/environmental-governance/material-factor-candidates/<id>/impacto-fuente/`.
Verified explicitly that assessment never mutates the candidate/factor/version/mapping/
calculation it inspects, and that a historical calculation reconstructs identically after a
simulated upstream GWP change. Tests: `test_material_source_impact.py`, 12/12 PASS, including
a real two-thread PostgreSQL concurrency test confirming identical, non-contradictory results.

## Architectural decisions carried into remaining phases

- **01F** will reuse `material_candidates.py`'s already-frozen `initial_eligibility`/
  `normalization`/`functional_context` (immutable per `GovernedMaterialModel`) as the sole
  input to a deterministic quality verdict — no new persisted model; reconstructibility is
  free because the inputs are already immutable.
- **01G** will reuse `CalculoAmbiental` (already append-only/immutable with `recalculo_de`
  lineage) as the ledger — no new ledger model. "Current" representation = the row with the
  max `version_interna` per `actividad`, equivalently the row nobody's `recalculo_de` points
  away from. A real pre-existing concurrency gap was found (`recalculate()` has no
  protection against two concurrent recalculations of the same base calculation producing
  two divergent "current" rows) — minimal fix planned: `UniqueConstraint` on
  `CalculoAmbiental.recalculo_de` + catch `IntegrityError` in `recalculate()`.
- **01H** will reuse `apps.knowledge.views.okobaudat_processes/_detail` (already has
  search/filter/pagination over the catalog) and 01C's `views_material_candidates.py`
  (already superuser-scoped candidate search) rather than rebuilding catalog search. New
  work is scoped to a read-only, non-superuser discovery surface (any authenticated user)
  over candidates + profile + indicators + promoted factor, since the existing candidate
  API is superuser-only and tenant analysts need to browse before proposing a mapping.
  Mapping visibility in the provenance walk stays tenant-scoped to the requester.
- **01I** needs no new persisted model either: impact assessment is a pure read-only diff
  between what a candidate was built from (frozen `provenance`) and what's already been
  locally hydrated by the *existing* 01A/01B sync commands (no new network fetches by this
  phase). Idempotence/concurrency is free because nothing is written.

## 01J — Closure & Production Readiness — PASS

Architecture audit across 01A-01I: no authority duplication, no dead code, tenant isolation
consistent with sibling read views, RBAC gates present on every mutation endpoint. Complete
local E2E for both A1 (`-647.4201396839651 kgCO2e/m3`, sign preserved) and A2
(`0.847351015163189 kgCO2e/kg`) paths with full historical-reconstruction assertions
(`test_material_data_e2e.py`, 2/2 PASS). Migration forward/reverse verified on 0067-0069
(unapply to 0066, reapply — clean both directions on real PostgreSQL).

**Two real pre-existing bugs found, root-caused, and handled per the failure policy:**

1. **Fixed (blocked a clean full regression)**: 7 of 8 pre-existing `TransactionTestCase`
   `_fixture_teardown` overrides (`test_legal_applicability.py`, `test_geospatial_context.py`,
   `test_legal_evidence_mapping.py`, `apps/knowledge/test_geo_sources.py`,
   `apps/knowledge/test_legal_evidence.py`, `apps/knowledge/test_okobaudat.py`,
   `apps/knowledge/test_regulatory_context.py`) truncated `django_migrations` itself instead
   of excluding it like the one correct pre-existing pattern
   (`test_okobaudat_detail.DetailPostgresTests`). Fixed all 7 to match that correct pattern.
   Confirmed by re-running the full regression: failures dropped from 29 to 28 (exactly the
   `EnvironmentalSource... does not exist` failure disappeared) and the
   `django_content_type already exists` corruption on subsequent `--keepdb` runs stopped
   recurring.
2. **Documented, not fixed (confirmed out of scope)**: `test_professional_v2.py` (20),
   `test_generated_emissions_indicator.py` (7), `test_requirements_compliance_contract.py`
   (1) fail even run completely alone on a freshly-migrated DB with zero MATERIAL-DATA
   files involved. Root cause: `apps/analytics/apps.py`'s `post_migrate` signal
   auto-seeds global fuel/energy methodologies after every migration; those global rows,
   evaluated by `methodology_selector.select_methodology()`, land in the broader
   "applicable_candidates" set (not filtered out by their own `aplicabilidad`) for
   `transporte`-type activities and tie in priority with each test's own tenant methodology,
   triggering the ambiguity branch. Confirmed 100% pre-existing and unrelated: `git diff`
   is empty on `apps.py`, `signals.py`, `methodology_selector.py`,
   `system_environmental_catalog.py`, and all three test files. Fixing it means changing
   transport/fuel methodology semantics — outside MATERIAL-DATA's boundary — so it is
   documented in `docs/MATERIAL-DATA-CLOSURE.md` and left alone.

**Full regression final: 1097/1125 PASS** (`apps.knowledge` 163/163 + `apps.analytics`
934/962; the 28 remaining failures are the confirmed pre-existing item #2 above). Every
`test_material_*.py` file and the E2E suite: 100% PASS. `manage.py check`,
`makemigrations --check --dry-run`, `git diff --check`: all clean.

`docs/MATERIAL-DATA-CLOSURE.md` finalized with architecture, authorities, APIs, commands,
runbook, both findings above, and remaining technical debt.

## MATERIAL-DATA is complete. Nothing pending. Not committed, not pushed, not deployed —
production gate is the user's.

## Command to re-verify this closure locally

```powershell
$env:DATABASE_ENGINE = 'django.db.backends.postgresql'
$env:DATABASE_HOST = '127.0.0.1'; $env:DATABASE_PORT = '55441'
$env:DATABASE_USER = 'material01d'; $env:DATABASE_PASSWORD = 'local-trust'
$env:DATABASE_NAME = 'material01d'
../venv/Scripts/python.exe manage.py test apps.knowledge apps.analytics --noinput
```
