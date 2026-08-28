# ARQ-05 — Unified Capture

## Purpose

Every modern capture channel converges on the Operational Kernel:

```text
FuenteDatos → ActividadOperacional → Observacion
                         ↑                ↑
              operational context   EvidenciaObra → VersionEvidencia
```

Capture records facts and provenance. It does not interpret environmental impact,
select factors, calculate results, decide compliance or let AI confirm truth.

## Audited channels

| Channel | Current adapter | Canonical result | Provenance authority |
|---|---|---|---|
| Manual activity API | `activity_core.create_observation` | Existing activity + atomic observation | Authenticated actor when available, manual source and optional evidence/version. |
| Structured/manual ingestion | `ingestion_handlers` | Confirmed row → activity + observations | Confirmed ingestion context, `RegistroExtraido`, source and optional evidence version. |
| Tabular import | `ingestion_handlers` | One activity envelope per confirmed row + observations | Extracted record, import source, checksum-backed evidence version when uploaded. |
| Document ingestion | `ingestion_v2` + `ingestion_handlers` | Only confirmed extraction becomes observations | Evidence/version and extracted record; suggested classification remains non-authoritative until confirmation. |
| API ingestion | `ingestion_handlers` | Confirmed payload row → activity + observations | API source and extracted record. Missing values are not invented. |
| Sensor/IoT | `iot.services_v2` | Sensor reading + canonical observation | Technical source, device reading and instrumental capture nature. |
| Environmental sector manual record | `sector_flows_v1` | Sector record linked to an activity and canonical observation | Actor, source and optional evidence/version inside the existing atomic transaction. |
| Transport manual record | `transport_v2` | Journey observations attached to its activity | Manual source and optional evidence/version. |
| Material event | `materials_v2` | Quantity observation attached to activity/event | Manual source, actor and optional evidence/version. |

Legacy endpoints remain available but are not promoted into the unified modern capture
contract. No modern adapter writes `RegistroEmision`.

## Common capture contract

`CaptureProvenance` is an immutable value object describing channel, capture method,
nature and initial state. `capture_observation()` is the single command used by modern
adapters to persist an atomic fact.

Required common fields:

- channel/origin;
- organization and source;
- concept and observation timestamp;
- exactly one numeric or textual value.

Context and provenance fields when applicable:

- work through the activity envelope;
- activity, actor and source;
- capture method, nature and state;
- evidence and exact evidence version;
- extracted-record reference for ingestion;
- unit and existing technical context stored by the channel's activity, reading,
  ingestion record or evidence metadata.

No generic JSON metadata was added to `Observacion`: technical metadata stays in the
existing authoritative record (`ActividadOperacional.metadata`, `RegistroExtraido`,
sensor reading, evidence/version or sector entity). Copying it into observations would
create competing provenance.

## Deterministic provenance rules

- Manual capture defaults to `manual` + `declarativo` + `pendiente`; authenticated
  adapters pass their actor. Older transport compatibility paths retain source-based
  provenance where no actor field existed.
- Document/import/API capture requires either the confirmed extracted record or an exact
  evidence version. Extraction and classification suggestions never become facts merely
  by existing.
- Sensor capture requires a sensor, telemetry or GPS `FuenteDatos`; its quality adapter
  preserves whether the observation starts validated or pending review.
- Evidence version, evidence, activity and source must share the capture tenant. If both
  evidence and version are supplied, that version must belong to that evidence.
- Model `full_clean()` remains the final atomic-value and cross-tenant invariant gate.
  The command executes transactionally, so a rejected fact leaves no observation.

## Application boundary and dependencies

```text
HTTP / file / device payload
        ↓
channel parser + existing confirmation/RBAC
        ↓
channel adapter
        ↓
CaptureProvenance policy/value object
        ↓
capture_observation command
        ↓
Operational Kernel
        ↓
Environment / Calculation / Reporting consumers
```

The common policy is deterministic and has no DRF, AI, mutation or legacy dependency.
The service mutates only `Observacion`; adapters retain ownership of activity envelopes,
evidence versions, ingestion records, sensor readings and sector entities.

## Preserved behavior

- Public endpoints, payloads, response shapes, status codes and UX are unchanged.
- Document extraction still requires human confirmation.
- Suggested and confirmed classifications remain distinct.
- Existing checksums, file versions, tenant/workspace/RBAC and transactional boundaries
  are unchanged.
- Manual and imported information persist in the same `ActividadOperacional` /
  `Observacion` kernel.
- Parsing does not synthesize missing values; existing invalid-row errors are preserved.

## Known debt

- Legacy emissions/import endpoints continue writing their compatibility models and are
  outside this modern capture boundary.
- Transport's historical manual adapter has no actor parameter; adding one would change
  its service/API contract and is deferred.
- IoT provenance links the observation to its reading from the reading side because
  `Observacion` has no generic sensor FK. The relation remains auditable and unchanged.
- Technical metadata remains distributed among authoritative channel records. A generic
  observation metadata field would require schema work and was not introduced.

No schema or external behavior change is required for unified capture.

## Validation gate

`test_unified_capture.py` verifies channel convergence, documentary provenance,
technical-source requirements, tenant isolation, transaction rollback and dependency
direction. Existing channel suites remain the end-to-end behavioral gate.

- Manual capture, ingestion, evidence/provenance, IoT, sector flows, transport,
  materials, atomicity, tenant/RBAC, Operational Kernel and architecture: **258/258**
  on PostgreSQL.
- The critical baseline retains exactly its five documented failures: three obsolete
  onboarding area-catalog expectations, the `DocumentoAmbiental(perfil_ambiental)`
  serializer error and the missing Construction V1 ingestion activity. No new failure
  or changed signature appeared.
- Django check, migration dry-run, compileall and diff checks pass.

ARQ-05 — UNIFIED CAPTURE: **CLOSED**.

ARQ-05 stops here; ARQ-06 is not started.
