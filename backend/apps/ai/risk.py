"""AI INTELLIGENCE macrofase — deterministic environmental-operational risk
scoring.

Built EXCLUSIVELY from `apps.ai.diagnostics` findings — never from the
LLM's own judgment, and never a second, independent assessment of the raw
data. If a finding didn't fire in diagnostics, it contributes nothing to
risk; if diagnostics changes (a new rule, a different threshold), risk
changes with it automatically, with zero duplicated logic.
"""
from .diagnostics import run_environmental_diagnostics

RISK_WEIGHTS = {"critical": 40, "high": 25, "medium": 12, "low": 5, "info": 0}
MAX_RISK_SCORE = 100
RISK_TIERS = [("critico", 85), ("alto", 60), ("medio", 30), ("bajo", 0)]

CATEGORY_BY_CODE = {
    "CONSUMPTION_INCREASE": "consumo", "CONSUMPTION_DECREASE": "consumo", "NEW_ACTIVITY": "consumo",
    "IMPACT_CONCENTRATION": "concentracion", "CONSUMPTION_CONCENTRATION": "concentracion",
    "CHANGE_DRIVER_ACTIVO": "concentracion", "CHANGE_DRIVER_MATERIAL": "concentracion",
    "HIGH_VARIABILITY": "consumo", "INCOMPLETE_COVERAGE": "cobertura",
    "MISSING_EVIDENCE": "evidencia", "UNMAPPED_FACTOR": "factor", "LOW_DATA_QUALITY": "calidad",
    "UNSUPPORTED_DATA": "calidad",
}


def _tier(score):
    for name, floor in RISK_TIERS:
        if score >= floor:
            return name
    return "bajo"


def score_environmental_risk(organization, user, *, obra, date_from=None, date_to=None,
                              relative_months=None, metrics=None):
    """Risk score in [0, 100] plus a category breakdown, derived
    deterministically from a real diagnostics run. Same findings -> same
    score, always — `RISK_WEIGHTS`/`RISK_TIERS` are the only knobs."""
    diagnostics_result = run_environmental_diagnostics(
        organization, user, obra=obra, date_from=date_from, date_to=date_to,
        relative_months=relative_months, metrics=metrics, max_findings=50,
    )
    findings = diagnostics_result["findings"]

    raw_score = sum(RISK_WEIGHTS.get(finding["severity"], 0) for finding in findings)
    risk_score = min(raw_score, MAX_RISK_SCORE)

    by_category = {}
    for finding in findings:
        category = CATEGORY_BY_CODE.get(finding["code"], "otro")
        bucket = by_category.setdefault(category, {"findings": 0, "score": 0})
        bucket["findings"] += 1
        bucket["score"] += RISK_WEIGHTS.get(finding["severity"], 0)
    for bucket in by_category.values():
        bucket["score"] = min(bucket["score"], MAX_RISK_SCORE)

    top_findings = sorted(findings, key=lambda finding: finding["priority_score"], reverse=True)[:5]

    return {
        "ok": True,
        "obra_id": obra.id, "obra_nombre": obra.nombre,
        "period": diagnostics_result["period"], "previous_period": diagnostics_result["previous_period"],
        "risk_score": risk_score, "nivel": _tier(risk_score),
        "basado_en_findings": len(findings),
        "por_categoria": by_category,
        "principales_findings": [
            {"code": finding["code"], "severity": finding["severity"], "priority_score": finding["priority_score"], "title": finding["title"]}
            for finding in top_findings
        ],
        "reason": {"rule": "sum(weight(severity)) capped at 100", "weights": RISK_WEIGHTS},
        "ruleset_version": diagnostics_result["ruleset_version"],
    }
