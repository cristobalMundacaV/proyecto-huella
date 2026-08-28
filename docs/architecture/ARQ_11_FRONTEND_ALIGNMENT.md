# ARQ-11 — Frontend Alignment

## Scope audited

The audit covered the frontend entry points and consumers for capture/imports/evidence,
Construction V1 operation domains, calculation eligibility, Improvement, Compliance,
Copilot, provenance, errors and compatibility APIs. No backend contract, route, payload,
permission or persistence rule was changed.

## Unified capture entry

`/datos/importaciones` remains the existing common entry for operational files and the
navigation bridge to document evidence. User-facing primary actions now call this
capability **Subir información** consistently from the data overview, import history and
evidence views. The existing role-scoped simplified uploader remains unchanged because it
is already a bounded capture adapter, not a second domain contract.

Capture continues to converge through the current backend APIs. The frontend does not
create missing observations, infer classifications or confirm document extraction.

## Canonical presentation states

Frontend presentation now maps backend-owned states to five stable user concepts:

| UI state | Meaning | Authority |
| --- | --- | --- |
| Capturado | Information exists and retains an origin | Capture/provenance response |
| Incompleto | Required information is still missing | Backend workflow/eligibility response |
| Listo para evaluación | A methodology is applicable, including non-blocking warnings | Eligibility response |
| No elegible | No applicable and calculable methodology exists | Eligibility response |
| Requiere revisión | A human decision or review is required | Backend workflow response |

The mapping is presentation-only. The frontend neither recomputes scientific eligibility
nor replaces workflow codes used for API filters and mutations. Detailed import pages
continue to expose the underlying workflow, errors and row results.

## Provenance and traceability

The existing traceability surfaces were preserved:

- import detail identifies source, destination, evidence version and result;
- evidence detail exposes version/checksum and related context;
- operation and Improvement retain traceability links;
- calculation keeps methodology/version information and now presents eligibility in
  human language while retaining the backend explanation.

No absence of data is presented as a zero environmental result.

## Improvement and AI authority

The Improvement detail was verified to guide users through BASE snapshot, selected human
action, measurement, RESULTADO snapshot and deterministic evaluation. There is no direct
frontend close action to remove. Invalid transitions continue to be rejected by the
backend and are now presented with a common human-readable API error policy.

Copilot keeps the existing prepare-then-confirm interaction. Its page explicitly states
that it may analyse context and propose alternatives, but cannot calculate environmental
truth, decide Compliance, verify improvement or close a problem. Human confirmation
remains required to create a formal action.

## Error contract

Action errors use a shared presentation helper:

- `403`: the user is informed that the action is not permitted;
- `404`: the resource is described as unavailable/not found;
- `400`: deterministic domain detail and field validation are retained;
- transport/unknown failures: a contextual retry message is shown.

This changes only wording. Status handling and backend rules remain authoritative.

## Visible compatibility consumers

The following legacy consumers remain intentionally unchanged:

- `shared/services/api.js`: obra detail aggregates `registros-emision` and `transportes`,
  and exports legacy emission/transport helpers;
- `shared/components/ImportarEvidenciaObraModal.jsx`: creates `RegistroEmision` through
  the existing compatibility endpoint;
- `features/obras/services/obrasApi.js` and obra compatibility tabs consume those helpers;
- `OperationalWorkspaceContext.jsx` retains its explicit legacy fallback.

They are compatibility debt, not new dependencies introduced by ARQ-11. Removing them
requires a separate contract migration and is outside this phase.

## Validation

- Frontend unit tests: 39 passed, 0 failed.
- ESLint: passed.
- Production build: passed (existing chunk-size advisory only).
- HTTP 400/403/404 presentation: covered by unit tests.
- Canonical state mapping: covered by unit tests.
- No backend files, schema, migrations or endpoints changed.

## Remaining debt

- Replace the documented legacy emission/transport consumers only after their modern API
  replacements have parity and a separately approved migration plan.
- Add browser-level integration coverage for the complete upload, Improvement and Copilot
  journeys; the repository currently validates these frontend changes through unit tests,
  lint and production build.
- Address Vite's existing large-chunk advisory independently; it is unrelated to the
  canonical contract alignment.

## Closure

**ARQ-11 CLOSED.** The audited frontend now presents the canonical capture, eligibility,
traceability and authority contracts without changing backend or functional behaviour.
