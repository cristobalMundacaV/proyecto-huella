"""AI-INTELLIGENCE-03 — plain-dict serialization of diagnostic findings.

The LLM (and any other consumer) only ever sees the output of
`serialize_diagnostics` — a JSON-serializable dict, never a
`DiagnosticFinding` dataclass instance or an ORM object.
"""
from dataclasses import asdict

from .rules import DIAGNOSTIC_RULESET_VERSION, RECOMMENDATIONS

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def _serialize_finding(finding):
    payload = asdict(finding)
    payload["recommendations"] = RECOMMENDATIONS.get(finding.code, [])
    return payload


def serialize_diagnostics(*, obra, period_start, period_end, previous_period, findings, metrics_analyzed):
    summary = {"findings": len(findings)}
    for severity in SEVERITY_ORDER:
        summary[severity] = sum(1 for finding in findings if finding.severity == severity)
    return {
        "obra_id": obra.id,
        "obra_nombre": obra.nombre,
        "period": {"start": period_start, "end": period_end},
        "previous_period": {"start": previous_period[0], "end": previous_period[1]},
        "metrics_analyzed": metrics_analyzed,
        "ruleset_version": DIAGNOSTIC_RULESET_VERSION,
        "summary": summary,
        "findings": [_serialize_finding(finding) for finding in findings],
    }
