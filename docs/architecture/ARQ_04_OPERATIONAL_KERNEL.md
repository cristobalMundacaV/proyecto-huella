# ARQ-04 — Operational Kernel Formalization

## Purpose and authority

The Operational Kernel records what happened in an organization's operation, where it
happened, which operational elements participated and which source/evidence supports the
record. It does not calculate environmental impact, decide compliance or delegate truth
to AI.

`Observacion` is the atomic datum. `ActividadOperacional` is its event/context envelope.
Evidence and immutable evidence versions provide documentary provenance. Downstream
domains may interpret this truth but must not redefine it.

## Canonical entities

| Entity | Meaning and ownership | Scope/cardinality | Identity and state |
|---|---|---|---|
| `FuenteDatos` | Named origin/channel of observations; owned by `Organizacion`. | Organization 1:N sources; source 1:N observations. | Unique `(organizacion, nombre)`; type from `Tipo`; `activa` controls availability without deleting history. |
| `ActividadOperacional` | Envelope for one operational occurrence or bounded activity; owned by `Organizacion`. | Optional `Obra`, `UnidadOperacional`, `ProcesoOperacional`; M:N assets; 1:N observations. Every linked context belongs to the same tenant. | Unique `(organizacion, codigo)`; states `borrador`, `registrada`, `incompleta`, `lista_para_evaluacion`, `anulada`; end cannot precede start. |
| `Observacion` | Atomic numeric or textual fact about a concept at a timestamp. | Exactly one source; optional activity, actor, evidence/version and extracted record. All tenant-bearing relations share the observation tenant. | Exactly one of numeric/text value; states `pendiente`, `validada`, `rechazada`; capture method and nature preserve how the fact was obtained. |
| `ActivoOperacional` | Physical or logical element used by the operation; owned by `Organizacion`. | Optional unit/process; M:N activities; specializations remain `Vehiculo`/`Maquinaria`. | Unique `(organizacion, codigo)`; states `operativo`, `requiere_revision`, `fuera_servicio`, `retirado`. |
| `UnidadOperacional` | Stable operational location/unit such as plant, installation or site; owned by `Organizacion`. | Organization 1:N units; unit 1:N processes/assets/activities. | Model identity; type catalogue plus active flag. No schema-level natural-key uniqueness exists. |
| `ProcesoOperacional` | Activity pattern performed by the organization, optionally inside a unit. | Organization 1:N processes; optional unit; process 1:N activities/assets. Unit must share tenant. | Model identity; states `activo`, `inactivo`, `en_diseno`. No schema-level natural-key uniqueness exists. |
| `Obra` | Tenant-owned work/project context and operational boundary. | Organization 1:N works; work scopes activities, evidence and workspaces where present. | Global generated `codigo_obra`; operational and environmental states remain separate existing contracts. |
| `AreaOperacional` | Organizational responsibility that generates/administers information. | Organization 1:N areas; area 1:N workspaces/evidence origins. | Unique `(organizacion, nombre)`; typed and active/inactive. It is not a process or environmental flow. |
| `EspacioTrabajoOperacional` (Workspace) | User membership + area + optional work access context. | One membership and one area; optional work. All belong to the membership tenant and work-scoped memberships require explicit access. | Unique `(usuario_organizacion, area, obra)` under the current database contract; active/inactive. |
| `EvidenciaObra` | Documentary or file-backed support, optionally scoped to work/area/actor. | Owned by organization; optional work, area, user and stage; 1:N versions; observations may reference it. | Documentary type/state; file and extraction metadata. It is support/provenance, not an operational fact by itself. |
| `VersionEvidencia` | Immutable-addressable uploaded version of evidence. | Exactly one evidence and organization; organization must equal the evidence tenant. | Unique `(evidencia, version)`, SHA-256 checksum and processing state `recibida`, `analizando`, `lista`, `procesada`, `error`. |

## Facts and non-facts

- An `Observacion` is operational truth only as the captured assertion represented by
  its value, concept, time, source and state. `pendiente` is not equivalent to verified.
- An activity, asset, process, area, work or workspace provides identity/context; none is
  a measurement by itself.
- Evidence proves provenance but its presence alone does not validate an observation.
- Extracted suggestions, AI output, metadata and ingestion previews are not canonical
  facts until the existing confirmation flow persists observations.
- Environmental flow records, calculations, impacts, indicators, compliance decisions
  and reports are downstream interpretations/results, not members of the kernel.

## Invariants and deduplication

1. `organizacion` is the primary isolation boundary. Any referenced work, unit, process,
   asset, source, evidence or evidence version must belong to the same tenant.
2. Work/area/workspace scope narrows access; it never grants membership or cross-tenant
   visibility. Cross-tenant resources remain hidden as 404 at API boundaries and invalid
   payload relations remain 400.
3. Activity assets are validated before their M2M assignment. Activity and observation
   commands call `full_clean()` before persistence.
4. An evidence version must belong to its evidence and tenant. An observation that
   names both evidence and version requires the version to belong to that evidence.
5. Canonical database deduplication keys are source name per tenant, activity code per
   tenant, asset code per tenant, area name per tenant and version number per evidence.
   Ingestion additionally uses existing external references, checksums and confirmed
   record semantics. No undocumented fuzzy merge is authoritative.
6. Unit, process and work currently retain model/generated identity rather than a new
   natural-key uniqueness rule. ARQ-04 does not invent one.
7. Operational records never write `RegistroEmision`, choose a factor, compute an
   impact, declare compliance or accept AI output as truth.

## Dependency graph

```text
Organizacion
├── AreaOperacional ── EspacioTrabajoOperacional ── UsuarioOrganizacion
├── Obra ───────────── EspacioTrabajoOperacional
├── UnidadOperacional ── ProcesoOperacional
├── ActivoOperacional ──┬─ ActividadOperacional
├── FuenteDatos ────────┤          │
└── EvidenciaObra ── VersionEvidencia
             └──────────────┬──────┘
                            ▼
                       Observacion
                            │
                            ▼
       Environment / Calculation / Quality / Reporting
```

Dependency direction is one-way: Platform/Operational Context → Operational Kernel →
Ingestion and environmental consumers → deterministic Calculation/Quality → Reporting.
Ingestion may create kernel facts after confirmation. Environment classifies/relates
them. Calculation consumes eligible facts and governed factors. Reporting consumes
persisted results and provenance; it does not mutate Operational Truth.

## Application boundaries

- Selectors own tenant-scoped reads for sources, activities, observations, assets,
  workspaces and evidence.
- Policies validate deterministic relation/scope/value rules without DRF, mutation, AI
  or scientific decisions.
- Services own atomic creation/update, call `full_clean()` where the current contract
  requires it and perform M2M assignment after the parent is valid.
- Views/serializers retain HTTP and representation responsibilities; public URLs,
  payloads, responses, ordering and status codes are unchanged.

No new legacy dependency is introduced. `registros_emision_legacy_count` remains an
explicit read-only compatibility projection and is not part of kernel authority.

## Known debt and schema boundary

- `EvidenciaObra` itself does not currently implement a complete cross-tenant `clean()`
  for work/area/stage. Authorized creation paths derive those fields from validated
  context. Moving this invariant into the model could reject previously accepted direct
  writes and is therefore deferred rather than changed silently.
- `UnidadOperacional` and `ProcesoOperacional` have no tenant-scoped natural-key unique
  constraints. Adding them requires a duplication/data audit and migration.
- Workspace uniqueness with nullable `obra` follows current PostgreSQL null semantics;
  organization-wide duplicate workspaces require a future schema/product decision.
- Evidence retains documented legacy relations for compatibility. They do not make
  legacy emission records canonical Operational Kernel facts.

No schema change is required to formalize the current kernel. Any strengthening of the
three constraints above requires a separately authorized migration and behavior review.

## ARQ-04 validation gate

`test_operational_kernel_contract.py` freezes dependency direction, canonical identity
constraints, cross-tenant activity/asset context, atomic observation values,
evidence-version consistency and workspace isolation.

- Operational Data, Assets, Operational Context, Provenance, Ingestion, tenant/RBAC and
  architecture: **160/160** on PostgreSQL.
- The critical baseline retains exactly its five documented failures: three obsolete
  onboarding area-catalog expectations, the `DocumentoAmbiental(perfil_ambiental)`
  serializer error and the missing Construction V1 ingestion activity. No new failure
  or changed signature appeared.
- Django check, migration dry-run, compileall and diff checks pass.

ARQ-04 — OPERATIONAL KERNEL FORMALIZATION: **CLOSED**.

ARQ-04 stops here; ARQ-05 is not started.
