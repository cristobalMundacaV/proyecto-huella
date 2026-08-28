# ARQ-07 — Generic Environmental Engine

## Authority and contract

The generic environmental engine is a read-oriented interpretation boundary:

```text
Operational Kernel
→ environmental interpretation
→ RegistroFlujoAmbiental / confirmed domain context
→ scientific eligibility
→ Calculation command
```

Environment explains what a fact represents. Calculation remains the only authority
that applies formulae/factors and persists numerical environmental results.

The engine consumes an existing `ActividadOperacional` and its `Observacion` records. It
returns a traceable projection containing capture completeness, classification,
environmental context, provenance and scientific eligibility. `calculation` is always
`None`; requesting a projection never creates `CalculoAmbiental` or `ImpactoAmbiental`.

## Generic components

- `EnvironmentalClassification`: immutable deterministic classification decision.
- `classify_environmental_context()`: prioritizes governed fuel classification, then an
  explicit `RegistroFlujoAmbiental`, then an injected domain contract. With none, it
  returns `sin_clasificar`; it never guesses.
- `environmental_activity_for_organization()`: tenant/work-scoped activity selector.
- `activity_environmental_record()` and `activity_provenance()`: read-only context and
  provenance selectors.
- `project_environmental_activity()`: orchestration facade. It joins interpretation with
  the existing methodology selector but performs no mutation or calculation.
- `project_construction_activity()`: Construction V1 adapter. Construction contracts are
  injected into the generic engine instead of hardcoded into its policy.

Other industries can provide their own immutable domain contract and adapter without
changing the generic classification core.

## Interpretation flow

1. Resolve the activity inside organization/work scope.
2. Read its observations, sources, actor, evidence/version and extracted-record links.
3. Evaluate capture completeness independently of scientific eligibility.
4. Classify fuel through the existing deterministic fuel policy. Ambiguous machinery,
   equipment or unknown use remains `requiere_clasificacion`.
5. Otherwise use the explicitly validated environmental-flow record or injected domain
   contract. Absence remains `sin_clasificar`.
6. Ask the existing methodology selector for eligibility. The projection records its
   reasons, discarded candidates, selected methodology/formula/factor version and exact
   input observation IDs.
7. Stop. A separate authorized Calculation command may calculate later.

## Seven Construction V1 flows

The adapter respects the ARQ-06 contracts for fuels, machinery, transport, materials,
energy, water and waste. Missing observations and rejected facts remain missing. Material
lifecycle remains optional. Work isolation follows the activity/domain invariants and a
different work cannot satisfy completeness or eligibility.

Capture completeness means the operational contract has its minimum context/facts.
Scientific eligibility additionally requires the existing active methodology, compatible
factor, required formula inputs, governed normalization and any professional-review
conditions. The two states are deliberately reported separately.

## Provenance

Every projected input exposes, when present:

- observation ID and state;
- source and actor IDs;
- evidence and exact evidence-version IDs;
- extracted-record ID;
- capture method and nature.

Eligibility trace adds methodology version, formula, factor version and exact input
observation IDs. No values or missing fields are synthesized into that trace.

## Legacy boundary

`services/environmental_engine.py` remains the named legacy metrics/LCA consumer of
`RegistroEmision`, `ConfiguracionOrganizacion` and `DatoACV`. Its endpoints and consumers
are unchanged. The new generic engine neither imports nor writes those models. Modern
environmental flows continue to use `RegistroFlujoAmbiental` and the Operational Kernel.

## Scientific preservation

`eligibility_v2`, `methodology_selector`, unit conversion, governed factor selection and
`calculation_v2` are reused unchanged. No formula, factor, priority, conversion, numeric
result or calculation snapshot contract is modified. AI has no authority in the engine.

## Known debt

- The legacy `environmental_engine.py` name overlaps conceptually with this modern
  interpretation facade. Renaming/removing it requires endpoint and consumer migration.
- Generic capture completeness without a supplied domain contract can only assert that a
  usable observation exists; richer completeness belongs to industry adapters.
- Environmental classification for non-fuel domain contracts is contextual, not a
  scientific methodology classification.
- The existing Construction V1 ingestion baseline failure remains outside this slice.

No schema or external behavior change is required.

## Validation gate

`test_generic_environmental_engine.py` verifies traceable interpretation, missing-data
preservation, ambiguous fuel classification, tenant/work isolation and absence of
legacy/calculation writes. Existing classification, eligibility, factor and Calculation
suites remain the scientific regression gate.

- Seven flows, classification, governed factors, units, eligibility, Calculation,
  tenant/RBAC and architecture: **282/282** on PostgreSQL.
- The critical baseline retains exactly its five documented failures: three obsolete
  onboarding area-catalog expectations, the `DocumentoAmbiental(perfil_ambiental)`
  serializer error and the missing Construction V1 ingestion activity. No new failure
  or changed signature appeared.
- Django check, migration dry-run, compileall and diff checks pass.

ARQ-07 — GENERIC ENVIRONMENTAL ENGINE: **CLOSED**.

ARQ-07 stops here; ARQ-08 is not started.
