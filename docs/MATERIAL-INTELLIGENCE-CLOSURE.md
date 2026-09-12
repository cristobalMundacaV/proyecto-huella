# MATERIAL-INTELLIGENCE — Closure

Base commit: `362ccdb` (MATERIAL-DATA-01E-01J, closed). This macrophase adds
the MATERIAL-INTELLIGENCE authorities on top of MATERIAL-DATA without
reimplementing any of it: catalog ingestion, factor governance, tenant
mapping, selection, calculation, ledger, coverage, quality, discovery,
source-impact and provenance are all reused exactly as MATERIAL-DATA left
them.

## Core scientific principle (enforced throughout)

`lower kgCO2e/kg ≠ better replacement`. The only valid chain is:

```text
approved application profile → approved requirements → approved technical
property evidence → deterministic suitability → human-approved functional
use → comparable set → deterministic environmental comparison → advisory
scenario/opportunity
```

Environmental comparison is never valid without an established functional
basis first. No code path in this macrophase goes directly from
`material name → similar material → lower GWP → recommendation`.

## Authority map (one authority per responsibility — audited, no duplication)

| Responsibility | Authority | Notes |
|---|---|---|
| Application requirements | `services/material_application_requirements.py` | Typed numeric/categorical/boolean operators only; no eval, no dynamic expressions |
| Functional application profile | `models/material_application_profile.py` + `services/material_application_profile.py` | Governed lifecycle: borrador → aprobado → retirado/rechazado/reemplazado |
| Technical property evidence | `models/material_technical_property.py` + `services/material_technical_property.py` | Reuses `EvidenciaObra`/`VersionEvidencia`/`FuenteDatos` for provenance; no second documentary authority |
| Suitability evaluation | `services/material_suitability.py` | Pure deterministic evaluator + `MaterialApplicationAssessment` immutable snapshot + human decision gate |
| Functional use quantity | `models/material_functional_use.py` (`MaterialFunctionalUse`) + `services/material_functional_use.py` | Governed, evidenced, human-approved; never inferred from density/name |
| Comparability | `services/material_comparable_sets.py` (`eligibility_chain`, `comparable_alternatives`) | Pure/derived; never persisted; never inferred from name/category/embedding |
| Environmental factor | **Reused**: `services/material_factor_mapping.py` / `material_factor_selector.py` (MATERIAL-DATA) | Not reimplemented |
| A1-A3 impact calculation | **Reused**: `services/calculation_v2.py` (MATERIAL-DATA) | Not reimplemented; MI never recomputes GWP itself |
| Deterministic comparison | `services/material_environmental_comparison.py` (`compare_materials`) | Pure/derived; per-functional-unit only |
| Hotspots | `services/material_hotspots.py` | Aggregates the **existing** ledger (`material_ledger.py`/`CalculoAmbiental`) — no second ledger |
| Substitution scenario | `models/material_substitution_scenario.py` + `services/material_substitution_scenario.py` | The one persisted MI derived-result: an immutable, read-only, hypothetical audit snapshot |
| Opportunity detection | `services/material_opportunities.py` | Composes hotspots + comparable sets + comparison; no new ranking authority |
| AI explanation | `services/material_intelligence_copilot.py` + `ContextGateway.material_intelligence()` | Extends the **existing** `ContextGateway` (no second gateway) and reuses `EnvironmentalAgentProvider` (no second provider abstraction) |

Persistence was added only where an audit trail is the actual requirement
(`MaterialApplicationProfile`, `MaterialTechnicalPropertyAssertion`,
`MaterialFunctionalUse`, `MaterialApplicationAssessment`,
`MaterialSubstitutionScenario`). MI-01D (comparability), MI-01E
(comparison) and MI-01H (opportunities) are intentionally pure/on-read —
persisting them would have been a parallel, redundant authority over data
already governed elsewhere.

## Functional equivalence semantics

A material is never compared to another material in the abstract. Every
comparison is *relative to one approved `MaterialApplicationProfile`* — an
explicit statement of function (e.g. "1 m2 of exterior wall") plus typed,
deterministic requirements (numeric eq/gte/lte/range, categorical
equals/one_of, boolean is_true/is_false — no arbitrary Python, no `eval()`).
An approved profile is immutable; a substantive change is a new revision
(`create_revision`), and approving a revision supersedes its predecessor
(`REEMPLAZADO`) atomically.

## Technical property evidence

`MaterialTechnicalPropertyAssertion` distinguishes six provenance types
(manufacturer datasheet, technical spec, certificate, lab result, project
requirement, manual professional assertion) and four states (borrador,
aprobado, rechazado, reemplazado). Only an **approved** assertion feeds
suitability; a draft is invisible to evaluation (`test_draft_property_ignored`).
Unknown stays unknown — it is never inferred from the material's name.
Approving a new assertion for the same `(material, property_key)`
explicitly supersedes the previous approved one (never two simultaneously
approved — enforced by a PostgreSQL partial unique index, not just
application logic).

## Functional quantities

`MaterialFunctionalUse.cantidad_por_unidad_funcional` is the governed,
evidenced, human-approved quantity of a material that fulfills one
functional unit of one approved profile. It is never derived from density
or name. Only one approved functional use exists per `(material, profile)`
at a time (same partial-unique-index pattern).

## Comparability rules (V1)

A material may enter *any* comparison only when, for one approved profile:

1. it has a human-**approved** suitability decision
   (`MaterialApplicationAssessment.decision_humana == aprobado` — not merely
   `resultado == suitable_candidate`, which is the deterministic-only
   signal);
2. it has an approved `MaterialFunctionalUse`;
3. it has a governed, calculable environmental factor (via the existing
   MATERIAL-DATA `select_material_factor`);
4. that factor's environmental data quality is not `insufficient`;
5. that factor's boundary is confirmed `A1-A3` (via the ÖKOBAUDAT-linked
   candidate's frozen normalization);
6. that factor's EN 15804 generation bucket (`A1` or `A2`) is known.

Two materials are comparable only when both pass all six gates **and**
share the same standard bucket. `A1↔A1` and `A2↔A2` are comparable;
`A1↔A2` is an explicit `standard_mismatch`, never silently reconciled.
**Comparability never comes from name, category or embedding similarity** —
`test_name_similarity_never_confers_comparability` and the MI-01J E2E's
lookalike-material test assert this directly.

### Known V1 limitation

Gate 5/6 require an ÖKOBAUDAT-linked factor candidate (the only source of
frozen `boundary`/`standard` metadata in this system). A private,
tenant-only custom factor (no ÖKOBAUDAT origin) therefore never becomes
comparability-eligible in V1 — it always resolves to
`boundary_not_confirmed_a1_a3` / `standard_unknown`. This is a deliberate,
explicit exclusion (never invent a boundary/standard for ungoverned data),
not a bug. Extending comparability to governed custom factors would need
an explicit, human-set boundary/standard annotation on
`MaterialFactorMapping` or `FactorAmbiental` — deferred, no schema change
made speculatively.

## A1/A2 boundary in the deterministic comparison

`impact_per_functional_unit = approved_quantity_per_functional_unit ×
governed_environmental_factor`, entirely in `Decimal`, only after unit
conversion via the existing `unit_conversion.py` (never a density-based
mass↔volume conversion). Percentages: undefined when the baseline impact is
zero (`baseline_zero_percentage_undefined`) or negative
(`baseline_negative_percentage_omitted`) — never a misleading percentage.
Negative GWP is preserved exactly (no `abs()`/clamp); a
`negative_gwp_present_sign_preserved` warning accompanies any comparison
touching a negative value. Quality is reported as metadata for a human
decision, never as a multiplier of impact.

## Hotspot semantics

`material_hotspots()` aggregates the **existing** ledger
(`CalculoAmbiental` via `material_ledger.ledger_entries`), grouped by
`unidad_resultado` (never mixed) and then by material, tracking
`positive_gwp`/`negative_gwp`/`net_gwp` separately. The V1 hotspot-share
denominator is the **total positive contribution only** — a large negative
(carbon-storing) material never dilutes another material's hotspot share,
and never appears as a hotspot itself (`hotspot_share is None` when its own
positive contribution is zero). No AI ranking; the sort key is the raw
positive-contribution Decimal itself.

## Substitution scenario semantics

`evaluate_scenario()` is read-only and hypothetical: it never mutates
`EventoMaterial`, the ledger, a mapping, or approves anything. Its only
side effect is creating one immutable `MaterialSubstitutionScenario` row.
Two bases are supported: a real reception (`functional_units =
normalized_source_quantity / approved_source_quantity_per_functional_unit`)
or an aggregate hypothetical quantity. A non-comparable pair (standard
mismatch, missing governed link, incompatible unit) is persisted with
`resultado=not_comparable` and an explicit `not_comparable_reason` — never
silently dropped, never a fabricated number. The output vocabulary is
strictly "environmental scenario result" — never "safe/approved/recommended
for construction".

## Opportunity semantics

`detect_opportunities()` composes hotspots (MI-01F) + comparable sets
(MI-01D) + comparison (MI-01E) with no new authority of its own. Ranking
is allowed **only** among alternatives already established as directly
comparable, on the single explicit metric of A1-A3 impact per functional
unit — never a black-box score, never mixed with cost/schedule/logistics
(those authorities do not exist in this system). A hotspot with zero
comparable alternatives is still reported (with an empty `alternatives`
list) rather than silently dropped, and every exclusion carries its
explicit reason. Vocabulary: "opportunity/candidate/requires_review" —
never "approved substitution/best material/recommended for use".

## Copilot boundaries

`MaterialIntelligenceCopilotService` extends the **existing**
`ContextGateway` (new `material_intelligence()` method — no second
gateway) and reuses the **existing** `EnvironmentalAgentProvider` contract
(no second provider abstraction). The AI may only explain already-computed
deterministic findings; it cannot invent an alternative, infer suitability,
change a functional quantity, calculate GWP, or approve an
equivalence/substitution/mapping. Every number in its context comes
literally from MI-01B..01H's own deterministic services. Disabling the
Copilot entirely does not affect any comparison/hotspot/scenario/opportunity
computation — verified directly
(`test_disabling_ai_does_not_affect_deterministic_context`). Tests use only
a stub `EnvironmentalAgentProvider` subclass, never a real LLM call.

## APIs

All new endpoints live under `organizaciones/<organizacion_id>/...` in
`apps/analytics/urls.py`, tenant-scoped (cross-tenant access is a 404,
never a 403 that would leak existence — verified by
`test_material_intelligence_security_audit.py`), and RBAC-gated by new
permissions `MATERIAL_APPLICATION_PROFILE_{VIEW,MANAGE,APPROVE}` and
`MATERIAL_PROPERTY_ASSERTION_{VIEW,MANAGE,APPROVE}` (functional
use/assessment/scenario/hotspot/opportunity/copilot endpoints reuse the
application-profile permissions — no proliferation of near-duplicate
permission constants).

## Commands

No new management commands were added in this macrophase; MI-01A..01I are
exposed purely through the service/API layer described above.

## Migrations

`0070`–`0071` (MI-01A: `MaterialApplicationProfile` +
`MaterialApplicationProfileDecision` + a NULL-safe identity unique index
and a single-approved-per-lineage partial unique index, both PostgreSQL-only
`RunPython`, matching the `0067`/`0068` MATERIAL-DATA pattern). `0072`–`0073`
(MI-01B: `MaterialTechnicalPropertyAssertion` + decision log + a
single-approved-per-property partial unique index). `0074`–`0075` (MI-01C:
`MaterialFunctionalUse` + decision log + `MaterialApplicationAssessment` +
a single-approved-per-(material,profile) partial unique index). `0076`
(MI-01G: `MaterialSubstitutionScenario`, no PostgreSQL-only guard needed —
it has no "single active row" invariant, every evaluation is an independent
immutable row). MI-01D/E/F/H/I introduced **no migrations** — reused/derived
services only.

## Tests

New focused suites (all green on real PostgreSQL,
`test_material01d_focus`/`test_material01d`):

- `test_material_application_profile.py` — requirement-schema validation,
  lifecycle, tenant isolation, RBAC, concurrent revision/retirement races.
- `test_material_technical_property.py` — typed properties, provenance,
  supersession, incompatible-unit rejection, direct-queryset-mutation
  guard, concurrency.
- `test_material_suitability.py` — deterministic evaluation (all
  satisfied/one failed/one unknown/draft ignored/numeric conversion/
  categorical exact match), historical-assessment immutability, human
  decision gate, functional-use lifecycle and concurrency.
- `test_material_comparable_sets.py` — real ÖKOBAUDAT-fixture-backed
  comparable/non-comparable cases (same standard, A1/A2 mismatch, missing
  suitability, missing factor, name-lookalike-never-comparable, tenant
  isolation).
- `test_material_environmental_comparison.py` — equal/different functional
  quantities, tonnes↔kg governed conversion, A1/A2 comparisons, A1/A2
  rejection, negative-baseline percentage handling, the exact ARQ-10 worked
  example (lower-per-kg-factor-still-loses), zero/negative-factor pure math,
  incompatible-unit rejection.
- `test_material_hotspots.py` — dominant material, shared denominator,
  negative material, net impact, positive-only hotspot denominator,
  deterministic recalculation, tenant/work isolation.
- `test_material_substitution_scenario.py` — real reception vs aggregate
  basis, different quantities, lower/higher impact, negative factor,
  zero-source-quantity edge case, non-comparable persistence, immutability,
  never-mutates-ledger/mapping, historical freeze against later changes,
  tenant isolation, concurrent evaluation.
- `test_material_opportunities.py` — lower-impact alternative, no
  alternatives still reported, higher-impact alternative not hidden,
  deterministic ordering, negative-GWP material excluded as a hotspot,
  tenant isolation.
- `test_material_intelligence_copilot.py` — bounded/tenant-scoped context,
  deterministic numbers not AI-generated, provider-unavailable and
  malformed-output handling, prompt-injection containment, provenance
  separated from explanation, AI-disabled-does-not-break-determinism —
  stub provider only, never a real LLM.
- `test_material_intelligence_e2e.py` — full comparable chain (≥2
  materials, real fixtures) end to end through Copilot explanation; the two
  explicit non-comparable cases (lookalike-without-suitability, A1-vs-A2);
  historical reconstruction surviving later changes.
- `test_material_intelligence_security_audit.py` — direct-queryset-mutation
  block for every governed model, API-level tenant isolation (404, not
  403) and RBAC enforcement.
- `test_material_intelligence_performance.py` — comparable-sets/hotspots
  sanity at moderate scale (dozens of materials) with no error/timeout; no
  speculative optimization added without evidence of a real bottleneck.

### Global negative test (automated, not merely asserted)

- `test_name_similarity_never_confers_comparability` — near-identical
  names/codes never produce `comparable=true`.
- `test_a1_a2_rejected_as_not_comparable` /
  `test_a1_vs_a2_not_directly_comparable_v1` — a lower-kgCO2e/kg
  alternative across an A1/A2 standard mismatch never produces a winner;
  the system returns `standard_mismatch`, never a recommendation.
- No test anywhere asserts or exercises a code path producing
  `recommended=true`, `approved_substitution`, or `best_material` — those
  strings do not appear as valid output values anywhere in MI-01A..01I.

## Regression discipline

Baseline preserved from MATERIAL-DATA: 28 pre-existing failures (1 FAIL +
27 ERROR in `test_professional_v2.py`, `test_generated_emissions_indicator.py`,
`test_requirements_compliance_contract.py` — a documented, out-of-scope
transport/fuel methodology-priority ambiguity from global auto-seeding).
Confirmed via two full-suite checkpoints during this macrophase:

1. A fresh, isolated run before any MATERIAL-INTELLIGENCE file existed:
   1135 tests (`apps` = analytics + knowledge + iot), 28 failures — exact
   baseline signature.
2. A mid-point checkpoint (`apps.analytics apps.knowledge`, with MI-01A..01D
   migrations/tests already present): 1207 tests, 32 errors — 27 of the
   documented baseline (`test_professional_v2`, 20;
   `test_generated_emissions_indicator`, 7) plus 5 *stale* failures in this
   macrophase's own `test_material_suitability.py`, from a bug (JSONField
   `blank=True` missing on empty-list result fields) already found and
   fixed earlier in the same session — confirmed fixed by every later
   focused run. Zero genuinely new regressions.

**FINAL FULL REGRESSION** (`manage.py test apps` — analytics + knowledge +
iot, real PostgreSQL, `--keepdb`): **passed: 1265 / known baseline
failures: 27 / new failures: 0**. Ran 1292 tests in 1431.4s. The 27
failures are exactly `test_generated_emissions_indicator.py` (7) and
`test_professional_v2.py` (20) — the same two files, same test names, as
every prior checkpoint in this macrophase and as documented in
`MATERIAL-DATA-CLOSURE.md`. The third documented baseline file
(`test_requirements_compliance_contract.py`, contributing the historical
"1 FAIL") did not reproduce its failure in this run — already observed as
run-dependent in an earlier isolated checkpoint this session, consistent
with its documented root cause (global fuel/energy methodology auto-seeding
order), and not something this macrophase touched. Every
`test_material_*` and `test_material_intelligence_*` file: **100% PASS**.
Migration forward → reverse (to `0069`) → forward again: clean on real
PostgreSQL (`0070`–`0076`, all 3 `RunPython` guards uninstall/reinstall
without error). `manage.py check`: clean. `makemigrations --check
--dry-run`: no pending changes. `git diff --check`: clean (only the
pre-existing, benign Windows LF→CRLF warnings on 4 files, no real
conflicts or trailing-whitespace errors).

## Bugs found and fixed during this macrophase (self-audit, not user-reported)

- **Approve-transition ordering vs. partial unique index**: promoting a new
  row into an `estado='aprobado'` slot while its predecessor was still
  `aprobado` violated the PostgreSQL partial unique index immediately
  (Postgres checks non-deferred unique constraints at statement time, not
  only at commit). Fixed by demoting the predecessor *before* promoting the
  new row, in `material_application_profile.py` and
  `material_technical_property.py`.
- **JSONField `blank=True` missing** on `MaterialApplicationAssessment`'s
  empty-list result fields — Django's `full_clean()` treats an empty list
  as "blank" and rejects it unless `blank=True` is set, even though `[]` is
  the correct value when nothing is missing/failed/warned.
- **Decimal precision exceeding the persisted field's `decimal_places`**:
  unlike `CalculoAmbiental` (which never calls `full_clean()` and lets
  PostgreSQL's `NUMERIC` column silently round), `MaterialSubstitutionScenario`
  and the comparison it persists **do** call `full_clean()`, which strictly
  rejects a Decimal with more fractional digits than the field declares.
  Decimal multiplication/division never auto-rounds in Python, so a
  6-decimal-place quantity times a 10-decimal-place factor produces up to
  16 decimal places. Fixed by explicit `.quantize()` at the exact points
  where these values are computed (`material_environmental_comparison.py`,
  `material_substitution_scenario.py`), matching each field's declared
  precision.
- **Missing `MATERIAL_APPLICATION_PROFILE_VIEW` check** on the Copilot
  explain endpoint (defense-in-depth fix; not independently exploitable,
  since `organization_available_to_user` already gates on tenant
  membership before the view body runs).
- **`record_assessment` used a VIEW-level permission** for what is actually
  a write action (persisting a new immutable row); tightened to
  `MATERIAL_APPLICATION_PROFILE_MANAGE`, consistent with the
  propose/approve separation-of-duties pattern used everywhere else in
  this macrophase.
- Several test-only bugs (missing `fecha_inicio` on `Obra` fixtures, a
  test helper reusing a tenant-scoped `FuenteDatos` across organizations,
  a profile/property mismatch in one E2E scenario, an
  over-strict concurrency-test assertion that assumed a race always
  rejects rather than sometimes gracefully superseding) — documented for
  completeness, none reflect a production code defect.

## Known limitations (V1, explicit, not silently deferred)

- Comparability requires an ÖKOBAUDAT-linked factor (see "Known V1
  limitation" above) — private/custom tenant factors are excluded from
  automated comparability until a governed boundary/standard annotation
  exists for them.
- No command-preparation/human-confirmation machinery was built for the
  Copilot (spec listed this as conditional/optional: "si se permite
  preparación de acciones"); MI-01I is explanation-only in this closure.
  Adding action-preparation later should reuse the existing
  `ComandoCopiloto`/`HitoDecisionIA` confirmation infrastructure (ARQ-10),
  not a new one.
- Hotspot/opportunity/comparable-set aggregation was validated at a
  moderate scale (dozens of materials); no index or query-batching change
  was made speculatively. If a tenant's catalog grows into the thousands,
  `material_comparable_sets.eligibility_chain()` (one factor-selection +
  quality-assessment pass per candidate) is the first place to profile
  with real production evidence before optimizing.

## Production runbook (for the human gate — NOT executed by this session)

1. `python manage.py check` and `python manage.py makemigrations --check
   --dry-run` in the target environment.
2. `python manage.py migrate analytics` — applies `0070`–`0076`. `0071`,
   `0073` and `0075` install PostgreSQL-only partial unique indexes
   (no-op on any other backend, matching the existing `0068` pattern); verify
   forward migration succeeds on a PostgreSQL target.
3. No production data was touched by this session: no profiles, no
   property assertions, no functional uses, no scenarios.
4. The first time a tenant wants to use MATERIAL-INTELLIGENCE for a
   material, someone with `MATERIAL_APPLICATION_PROFILE_MANAGE` must create
   and someone with `MATERIAL_APPLICATION_PROFILE_APPROVE` must approve: an
   application profile, technical property assertions, and a functional
   use — in that order — before any comparison/scenario/opportunity
   involving that material becomes possible. There is no automatic
   shortcut, by design.

STATUS: see `docs/MATERIAL-INTELLIGENCE-HANDOFF.md` for the final
completion gate results and STATUS line.
