"""AI-INTELLIGENCE-03 — deterministic finding prioritization.

`compute_priority` is a pure function of a `DiagnosticFinding`'s already-set
fields — same finding in, same score out, regardless of which LLM (or no
LLM at all) is presenting it afterwards.
"""
SEVERITY_BASE_SCORE = {"critical": 100, "high": 75, "medium": 50, "low": 25, "info": 10}

MANY_RECORDS_THRESHOLD = 10


def compute_priority(finding):
    score = SEVERITY_BASE_SCORE.get(finding.severity, 0)
    if finding.code == "UNMAPPED_FACTOR":
        score += 20
    if finding.code in ("MISSING_EVIDENCE", "UNSUPPORTED_DATA"):
        score += 15
    variation_percent = finding.metadata.get("variation_percent")
    if variation_percent is not None and abs(variation_percent) >= 75:
        score += 20
    share_percent = finding.metadata.get("share_percent")
    if share_percent is not None and share_percent > 60:
        score += 15
    affected_count = finding.metadata.get("affected_count")
    if affected_count is not None and affected_count > MANY_RECORDS_THRESHOLD:
        score += 10
    return min(score, 100)
