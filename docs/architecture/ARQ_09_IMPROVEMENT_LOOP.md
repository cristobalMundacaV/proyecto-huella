# ARQ-09 — Problem → Recommendation → Action → Verification

## Canonical improvement cycle

```text
ProblematicaAmbiental
→ Recommendation
→ AccionMejoraAmbiental selected by a human
→ MedicionSeguimientoAmbiental / governed indicator values
→ SnapshotIntervencion BASE (frozen at implementation)
→ SnapshotIntervencion RESULTADO (frozen at evaluation)
→ ResultadoIntervencion
→ CicloReevaluacionProblematica closed
→ resolution or a new cycle / professional escalation
```

Improvement consumes operational and environmental truth; it does not replace it. A
calendar interval by itself is never evidence of improvement.

## Authority by stage

- **Problem:** records the deviation, scope, risk and target under review.
- **AI recommendation:** may propose an intervention. It cannot create operational truth,
  select itself, start implementation, evaluate or close a problem.
- **Human confirmation:** converts a prepared Copilot command into an action and explicitly
  selects it. Direct actions also require the selection command before implementation.
- **Action:** records the intervention selected and applied by people.
- **Measurement / indicator value:** supplies an independently persisted observation or
  result. It is not inferred from dates.
- **BASE snapshot:** freezes scope, indicators and values before implementation.
- **RESULTADO snapshot:** freezes the comparable values used after implementation.
- **ResultadoIntervencion:** is the deterministic authority for the intervention outcome;
  its metrics explicitly say that temporal association alone does not imply causality.
- **CicloReevaluacionProblematica:** binds action, both snapshots and result into an
  auditable cycle. A positive result resolves the problem; other results keep it
  unresolved and allow another cycle or the existing professional escalation.
- **Professional review:** retains its existing authority and audited correction paths.

## Closure invariant

The generic problem PATCH is an editing boundary, not a transition command. Requests to
persist `cerrada` or `resuelta` through it return HTTP 400 with an explicit explanation.
The service enforces the same policy even when invoked without HTTP, removing the former
internal bypass.

Modern deterministic resolution additionally verifies that:

- an action was explicitly selected;
- BASE and RESULTADO snapshots exist and are frozen;
- `ResultadoIntervencion` belongs to the same problem, action, cycle and snapshots;
- the reevaluation cycle has a close date.

Only after those invariants pass can a positive result persist `resuelta`. Existing
legacy evaluation remains available through its dedicated measurement/evaluation command;
it is not broadened or silently rewritten by ARQ-09.

## Read contract and traceability

`verified_cycles_for_problem()` returns only complete reevaluation chains and joins the
selected action, frozen inputs and deterministic result for audit consumers. Existing
history records retain actor, event, state and object identifiers. Recommendation command
confirmation continues recording the human decision in `HitoDecisionIA` and
`MemoriaOrganizacion`.

## External behavior

URLs, serializers, state vocabulary and successful non-state PATCH updates are preserved.
The intentional correction is that terminal state requests through generic PATCH are no
longer silently ignored or persistable: they are rejected with HTTP 400. No schema,
migration, prompt, scientific calculation or frontend change is introduced.

## Legacy boundary

Legacy `AccionAmbiental` closure remains a compatibility workflow and is not promoted to
the canonical modern reevaluation authority. ARQ-09 introduces no new legacy dependency
and does not remove existing compatibility endpoints.

## Known debt

- Legacy measurement-based resolution does not persist modern BASE/RESULTADO snapshots;
  migrating that external contract requires a dedicated compatibility program.
- Recommendation and action remain separate models only for the modern Copilot path;
  manually created proposals are represented directly as `AccionMejoraAmbiental` in
  proposed state.
- Professional escalation is capped at the existing three automatic cycles.

No schema change is required.

## Validation gate

`test_intervention_v2.py` covers generic PATCH/service closure rejection and proves that a
positive resolution has a selected action, frozen snapshots, deterministic result and a
closed verified cycle. Existing problem, action, closure, Copilot, professional,
tenant/RBAC and architecture suites remain the regression gate.

- Focused problem and intervention gate: **27/27** on PostgreSQL.
- Integrated Improvement, Copilot, Professional, Compliance contract, tenant/RBAC and
  architecture gate: **101/102**; its only error is the previously documented
  `DocumentoAmbiental(perfil_ambiental)` serializer baseline failure.
- Critical baseline: **25/30**, preserving exactly its five documented failures (three
  obsolete onboarding area-catalog expectations, the same evidence serializer error and
  the missing Construction V1 ingestion activity). No new failure or changed signature
  appeared.
- Django check, migration dry-run, Black, compileall and diff checks pass.

ARQ-09 — IMPROVEMENT LOOP: **CLOSED**.

ARQ-09 stops here; ARQ-10 is not started.
