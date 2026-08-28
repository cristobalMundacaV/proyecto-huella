# ARQ-08 — Requirements / Compliance

## Contract and authority

Compliance is a deterministic comparison boundary, not a source of measurements:

```text
Operational Kernel facts
→ Environment interpretation
→ Calculation / indicator result when applicable
→ Requirement comparison
→ explainable compliance result
```

A requirement is an immutable condition against which an independently obtained result
is evaluated. It is never itself a measurement. Missing observations/results remain
`sin_dato`; the evaluator neither infers a value nor performs unit conversion. AI has no
authority to decide applicability or compliance.

`RequirementContract` makes the common fields explicit: class, stable identity, scope,
variable/indicator, comparator and threshold, unit, validity interval,
source/authority, evaluation method and metadata. `ComplianceResult` adds the evaluated
value, evidence/result references, state and a deterministic explanation.

## Requirement classes

### NORMATIVE LIMIT

An externally authoritative limit already configured and professionally validated for
the tenant. Applicability also respects industry, region, installation type and validity.
Persistence remains the existing `LimiteNormativoAmbiental` compatibility model; the new
contract consumes it through the established Compliance selector and does not expand
legacy writes.

### OPERATIONAL RESTRICTION

An active, time-bounded constraint on how the operation may occur. Existing
`RestriccionContextual(tipo="restriccion_operacional")` records are adapted only when
their content explicitly supplies variable, condition/threshold and unit. Conditions
that are absent or not deterministically evaluable return `requiere_revision`.

### INTERNAL TARGET

A tenant-authorized performance objective. ARQ-08 accepts an explicitly governed target
as an immutable contract and may compare it with an existing indicator/result. It does
not treat `IndicadorProblematica.valor_objetivo` as the canonical Compliance authority,
because that field belongs to Improvement and doing so would violate the domain boundary.

## Evaluation states

- `cumple`: the supplied result satisfies the explicit condition.
- `incumple`: the supplied result does not satisfy it.
- `sin_dato`: no independently produced value exists.
- `no_aplica`: the requirement is outside its validity interval.
- `requiere_revision`: units or conditions do not support a deterministic comparison.

The explanation states why the result reached its state. Evidence and result identifiers
are preserved as references; evaluation never creates or rewrites Operational Kernel,
Environment, Calculation, indicator, evidence, alert or Improvement records.

## Scope and provenance

Selectors enforce organization scope before adapting records. Requirement scope may add
work, area/workspace, industry, region, installation or problem context. Evidence and
calculation/indicator result references belong to the evaluation trace, keeping the
authority chain inspectable without confusing a document with a measured value.

## Existing behavior preserved

Current Compliance endpoints, serializers, persisted states, alerts and the legacy
`VariableAmbientalExtraida.calculate_compliance()` behavior are unchanged. Existing
scientific calculations, factors, conversions, environmental classification and
Improvement transitions are untouched. The ARQ-08 facade is an internal contract for
progressive adoption; it introduces no API or schema change.

## Legacy boundary

The normative store is an inherited **REQUIRED/WRITE COMPATIBILITY** boundary of current
Compliance. ARQ-08 introduces no direct import from `models/legacy.py`: its selector
reuses `selectors/compliance.py`, and adapters are duck-typed. No modern domain writes
`RegistroEmision`, `FactorEmision`, `TransporteObra` or `AccionAmbiental`.

## Known debt

- There is no canonical, standalone Governance persistence model for internal targets.
  Adding one would require schema and is intentionally deferred.
- Normative limits, extracted variables and compliance alerts still persist in legacy
  compatibility models; migrating them requires a separate data/API program.
- Presence, mandatory and non-numeric operational conditions need their existing domain
  evaluator or human review; ARQ-08 does not invent semantics for them.
- Existing alert thresholds (`alerta` bands) remain in the legacy model and were not
  redefined by this architecture slice.

No schema or external behavior change is required.

## Validation gate

`test_requirements_compliance_contract.py` covers all three classes, tenant scoping,
validity, evidence/result trace, missing-data preservation and unit mismatch. Existing
Compliance, Environment, Calculation, tenant/RBAC and architecture suites remain the
regression gate.

- ARQ-08 contract tests: **6/6** on PostgreSQL.
- Integrated Governance, Environment, Calculation, Quality, tenant/RBAC and architecture
  gate: **136/137**; its only error is the previously documented
  `DocumentoAmbiental(perfil_ambiental)` serializer baseline failure.
- Critical baseline: **25/30**, preserving exactly its five documented failures (three
  obsolete onboarding area-catalog expectations, the same evidence serializer error and
  the missing Construction V1 ingestion activity). No new failure or changed signature
  appeared.
- Django check, migration dry-run, Black, compileall and diff checks pass.

ARQ-08 — REQUIREMENTS / COMPLIANCE: **CLOSED**.

ARQ-08 stops here; ARQ-09 is not started.
