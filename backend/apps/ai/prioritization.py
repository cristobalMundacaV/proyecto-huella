"""AI INTELLIGENCE macrofase — deterministic action prioritization.

Reuses `diagnostics` findings entirely — this module adds no new scoring
logic, only turns an already-sorted findings list into a deduplicated,
action-oriented list (one row per distinct recommendation, from the
controlled catalog) with an explicit "next action" pointer. Every action
still carries the exact `reason`/`priority_score` of the finding it came
from — fully traceable back to a deterministic rule.
"""
from .diagnostics import run_environmental_diagnostics


def prioritize_actions(organization, user, *, obra, date_from=None, date_to=None,
                        relative_months=None, metrics=None, max_actions=10):
    diagnostics_result = run_environmental_diagnostics(
        organization, user, obra=obra, date_from=date_from, date_to=date_to,
        relative_months=relative_months, metrics=metrics, max_findings=50,
    )
    findings = diagnostics_result["findings"]

    actions = []
    seen = set()
    for finding in findings:
        for recommendation in finding.get("recommendations") or []:
            key = (finding["code"], recommendation)
            if key in seen:
                continue
            seen.add(key)
            actions.append({
                "priority_score": finding["priority_score"], "severity": finding["severity"],
                "source_finding_code": finding["code"], "metric": finding.get("metric"),
                "entity_type": finding.get("entity_type"), "entity_name": finding.get("entity_name"),
                "accion": recommendation, "reason": finding["reason"],
            })
            if len(actions) >= max_actions:
                break
        if len(actions) >= max_actions:
            break

    return {
        "ok": True, "obra_id": obra.id, "obra_nombre": obra.nombre,
        "period": diagnostics_result["period"], "previous_period": diagnostics_result["previous_period"],
        "total_acciones": len(actions), "acciones": actions,
        "accion_prioritaria": actions[0] if actions else None,
        "ruleset_version": diagnostics_result["ruleset_version"],
    }
