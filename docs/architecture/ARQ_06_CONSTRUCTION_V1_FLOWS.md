# ARQ-06 — Construction V1 Flow Contracts

## Boundary

Construction V1 formalizes seven capture contracts over the Operational Kernel. A
contract describes when captured operational context is structurally complete. It does
not select a methodology/factor or declare a record scientifically calculable.

All observations converge through Unified Capture. Domain records provide context; they
do not create a second operational truth.

## Flow contracts

### Combustibles

- Activity: `consumo_combustible` or `consumo_combustible_estacionario`.
- Minimum observation: `combustible_consumido` or historical transport-compatible
  `combustible_consumido_l`; numeric value remains required by the observation model.
- Accepted capture units: L, m³, kg or t. Formula compatibility and conversion remain
  governed by Calculation.
- Context: `RegistroFlujoAmbiental`; asset/vehicle/generator may refine destination.
- Provenance: source required; actor for authenticated manual capture; extracted record
  or evidence version for imported/document capture.
- Typical evidence: fuel invoice or source document.
- Complete: activity type + environmental-flow context + one non-rejected consumption
  observation. Eligible: only after mobile/stationary classification, compatible active
  factor, required formula inputs and unit conversion pass existing Calculation rules.

### Maquinaria

- Activity: `operacion_maquinaria`.
- Minimum observation: `horas_operacion`.
- Optional: fuel consumption and performance.
- Units: h for operation; L/m³ where fuel is captured.
- Context: at least one `ActivoOperacional`, normally `Maquinaria` specialization.
- Typical evidence: machinery log and fuel invoice.
- Complete: typed activity + asset + non-rejected hours observation. Eligibility remains
  formula/factor-specific; capture never infers fuel from hours.

### Transporte

- Activity: `transporte`.
- Minimum observation: `distancia_recorrida_km`.
- Optional: `masa_transportada_t`, `combustible_consumido_l`.
- Units: km, t/kg and L.
- Context: `ViajeOperacional`, vehicle and optional route; journey/model invariants
  enforce tenant, selected concepts and non-negative values.
- Typical evidence: transport document or dispatch guide.
- Complete: typed activity + journey + distance. A completed journey without calculation
  inputs remains operationally stored but contract-incomplete. Calculation eligibility
  depends on the selected transport formula, vehicle and factor.

### Materiales

- Activity: `movimiento_material`.
- Optional observation: `cantidad_material`, using `MaterialOperacional.unidad_base` or
  the explicitly captured event unit.
- Context: `EventoMaterial`; material required, lot and lineage optional.
- Typical evidence: material invoice, dispatch guide or technical sheet.
- Complete: typed activity + material event. Quantity improves traceability but is not
  invented. Lifecycle, lot, lineage and balance remain optional.
- Environmental interpretation/calculation consumes confirmed material events later; the
  event itself is not an impact.

### Energía

- Activity: `consumo_energia` or `generacion_energia`.
- Minimum observation: `consumo_energia` or `energia_generada`, matching the activity.
- Optional: self-consumed/exported energy.
- Units currently captured: kWh or MWh; exact compatibility remains formula-governed.
- Context: environmental-flow record, optionally scoped to work, point or asset.
- Typical evidence: electricity bill or production/generation record.
- Complete: context + one non-rejected primary energy observation.

### Agua

- Activity: `consumo_agua`.
- Minimum observation: `consumo_agua`.
- Optional: flow rate or meter reading.
- Units: L or m³.
- Context: environmental-flow record, commonly work or measurement point.
- Typical evidence: source document, meter or production record.
- Complete: context + non-rejected consumption. A missing reading remains missing.

### Residuos

- Activity: `gestion_residuo`.
- Minimum observation: `cantidad_residuo`.
- Optional: waste type and dangerous/non-dangerous classification metadata.
- Units: kg, t or m³.
- Context: environmental-flow record; optional material event, manager/provider and
  operational destination. Dangerous and non-dangerous data remain distinguishable.
- Typical evidence: waste-removal record or weighing ticket.
- Complete: context + non-rejected quantity. Treatment, factor and compliance are
  downstream decisions and are never inferred at capture.

## Shared invariants

1. Activity, observation, source, work, asset, point, event and journey remain in one
   tenant. Existing model/policy validation rejects cross-tenant payloads.
2. Work scope comes from the activity/domain context. A contract reads only observations
   attached to that activity, so another work cannot fill a missing value.
3. Rejected observations do not satisfy capture completeness. Missing, blank or
   unconfirmed information is never defaulted into a fact.
4. Unified Capture owns observation persistence and provenance rules. Domain adapters
   own their contextual entity and atomic transaction.
5. Capture completeness is not Calculation eligibility. `capture_completeness()` returns
   eligibility as `delegada`; `eligibility_v2` remains the only scientific gate.
6. No contract writes `RegistroEmision` or any other legacy model.

## Executable contract catalogue

`ConstructionFlowContract` is an immutable value object containing activity types,
minimum/optional concepts, accepted capture units, required domain context, typical
evidence and lifecycle optionality. `CONSTRUCTION_V1_FLOW_CONTRACTS` contains exactly the
seven authorized flows.

`capture_completeness()` is read-only. It reports explicit missing elements and never
creates observations, supplies values, converts units, selects factors or calculates an
impact.

## Inconsistencies preserved as debt

- Construction V1's older ingestion integration baseline still expects an activity that
  its current fixture does not produce. ARQ-06 does not patch that unrelated behavior.
- Machinery is an operational activity/asset domain, not a `RegistroFlujoAmbiental.Flujo`
  enum value. Its contract intentionally uses the canonical activity + asset relation.
- Materials accept business-specific base units; imposing a global closed unit catalogue
  would require data normalization and behavior change.
- Energy unit conversion is not expanded by ARQ-06. Only existing formula compatibility
  may authorize calculation.
- Residue dangerous/non-dangerous separation is carried by confirmed operational
  classification/context; no new schema field is introduced.

No schema or external behavior change is required.

## Validation gate

`test_construction_flow_contracts_v1.py` verifies the seven-flow catalogue, missing-value
preservation, Unified Capture convergence, rejected facts, optional material lifecycle,
work isolation and capture/calculation separation.

- Seven flow domains, atomic manual capture, Unified Capture, Operational Kernel,
  tenant/RBAC and architecture: **214/214** on PostgreSQL.
- The critical baseline retains exactly its five documented failures: three obsolete
  onboarding area-catalog expectations, the `DocumentoAmbiental(perfil_ambiental)`
  serializer error and the missing Construction V1 ingestion activity. No new failure
  or changed signature appeared.
- Django check, migration dry-run, compileall and diff checks pass.

ARQ-06 — CONSTRUCTION V1 FLOW CONTRACTS: **CLOSED**.

ARQ-06 stops here; ARQ-07 is not started.
