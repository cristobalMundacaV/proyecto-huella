# MATERIAL-INTELLIGENCE — Handoff

STATUS: COMPLETE

Base commit: `362ccdb` (MATERIAL-DATA-01E-01J, closed). This macrophase is
committed on top of it as a single macrophase commit (see git log). NO
production deploy, NO SSH production, NO production mutation was performed
by this session.

## Phase status — all CLOSED

- 01A — Functional Application Profiles: PASS
- 01B — Governed Technical Property Evidence: PASS
- 01C — Suitability & Functional Use Governance: PASS
- 01D — Comparable Alternative Sets: PASS
- 01E — Deterministic Environmental Comparison: PASS
- 01F — Material Hotspot Intelligence: PASS
- 01G — Substitution Scenario Engine: PASS
- 01H — Environmental Opportunity Detection: PASS
- 01I — Material Intelligence Copilot: PASS
- 01J — Closure & Production Readiness: PASS

## Final gate results

- **Focused suites** (every `test_material_*` + `test_material_intelligence_*`
  file, real PostgreSQL, run together): 157 + 19 = **176 tests, 0 failures**
  across the two combined runs that included every MI file.
- **FINAL FULL REGRESSION** (`manage.py test apps`, real PostgreSQL):
  **passed: 1265 / known baseline failures: 27 / new failures: 0** (1292
  tests total, 27 errors, all in `test_generated_emissions_indicator.py`
  and `test_professional_v2.py` — the documented, out-of-scope
  methodology-priority baseline; the historical "1 FAIL" in
  `test_requirements_compliance_contract.py` did not reproduce in this run,
  confirmed run-dependent and pre-existing, not caused by this macrophase).
- `python manage.py check`: clean.
- `python manage.py makemigrations --check --dry-run`: no pending changes.
- `git diff --check`: clean (only pre-existing benign LF→CRLF warnings).
- Migration `0070`–`0076` forward → reverse (to `0069`) → forward again:
  clean on real PostgreSQL.
- `docs/MATERIAL-INTELLIGENCE-CLOSURE.md`: complete.

## Files (all new unless marked "modified")

Models: `material_application_profile.py`, `material_technical_property.py`,
`material_functional_use.py` (also `MaterialApplicationAssessment`),
`material_substitution_scenario.py`, `material_intelligence_governed.py`.

Services: `material_application_requirements.py`, `material_application_profile.py`,
`material_technical_property.py`, `material_suitability.py`,
`material_functional_use.py`, `material_comparable_sets.py`,
`material_environmental_comparison.py`, `material_hotspots.py`,
`material_substitution_scenario.py`, `material_opportunities.py`,
`material_intelligence_copilot.py`. Modified: `services/context_gateway.py`
(added `material_intelligence()` method only).

Views: `views_material_application_profile.py`,
`views_material_technical_property.py`, `views_material_functional_use.py`,
`views_material_comparable_sets.py`, `views_material_environmental_comparison.py`,
`views_material_hotspots.py`, `views_material_substitution_scenario.py`,
`views_material_opportunities.py`, `views_material_intelligence_copilot.py`.
Modified: `urls.py` (new routes appended), `permissions.py` (new
`MATERIAL_APPLICATION_PROFILE_*` / `MATERIAL_PROPERTY_ASSERTION_*`
constants and role grants appended), `models/__init__.py` (new model
imports appended).

Migrations: `0070`–`0076` (see `MATERIAL-INTELLIGENCE-CLOSURE.md` for the
per-migration breakdown).

Tests: `test_material_application_profile.py`, `test_material_technical_property.py`,
`test_material_suitability.py`, `test_material_comparable_sets.py`,
`test_material_environmental_comparison.py`, `test_material_hotspots.py`,
`test_material_substitution_scenario.py`, `test_material_opportunities.py`,
`test_material_intelligence_copilot.py`, `test_material_intelligence_e2e.py`,
`test_material_intelligence_security_audit.py`,
`test_material_intelligence_performance.py`.

Docs: `MATERIAL-INTELLIGENCE-CLOSURE.md` (this macrophase's architecture,
authority map, semantics, known limitations, production runbook), this
file.

## Architectural decisions (see CLOSURE.md for full detail)

- MI-01D/E/H are pure/on-read — no new persisted model. Only MI-01A/B/C
  (governance authorities) and MI-01G (audit-trail scenario snapshot)
  needed real models.
- Comparability requires an ÖKOBAUDAT-linked factor candidate (frozen
  boundary/standard); private/custom tenant factors are excluded from V1
  automated comparability — documented as a known limitation, not a bug.
- "Approved suitability" for comparability = human `decision_humana ==
  aprobado`, not merely the deterministic `resultado == suitable_candidate`.
- Governed single-active-row invariants use a PostgreSQL partial unique
  index (`WHERE estado = 'aprobado'`) as the real safety net, plus an
  application-level "supersede current approved" convenience — the
  approve-transition order matters (demote predecessor before promoting;
  found and fixed a real ordering bug here during 01A/01B).
- MI-01I's Copilot reuses the existing `EnvironmentalAgentProvider` and
  extends the existing `ContextGateway` — no second gateway, no second
  provider abstraction.
- Decimal fields that persist a computed product/quotient (impact,
  delta, functional units) must be explicitly `.quantize()`d to their
  field's `decimal_places` before assignment, because (unlike
  `CalculoAmbiental`, which never calls `full_clean()`) these governed
  models do call `full_clean()`, which strictly rejects over-precise
  Decimals rather than letting PostgreSQL round them.

## Bugs found and fixed this session (see CLOSURE.md for full list)

Approve-transition ordering vs. partial unique index; missing
`blank=True` on empty-list JSONFields; Decimal precision exceeding
persisted field precision; a defense-in-depth RBAC check missing on the
Copilot endpoint; `record_assessment` using a view-level rather than
manage-level permission; several test-only fixture bugs (documented, no
production code defect).

## Next macrophase

Per explicit user instruction received during this session (overriding
the standing no-commit/no-push rule at this exact completion boundary):
this macrophase is committed and pushed to `origin/main`, then this
session proceeds directly to `docs/SOURCE-WATCH-01-MISSION.md` (fetched
from `origin/main`) as the next engineering mission — SOURCE-WATCH-01A
through 01J — without further human confirmation, per that same
instruction. See the session transcript for the exact instruction text.
