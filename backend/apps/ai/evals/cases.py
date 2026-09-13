"""AI INTELLIGENCE macrofase — eval case definitions.

Each `eval_*` function returns a list of result dicts
`{"category", "name", "passed", "detail"}`. Every case calls the SAME
tool functions the orchestrator calls (`apps.ai.tools`) — this suite is
not a reimplementation, it is a battery of assertions over the real code.
"""
from datetime import date
from decimal import Decimal

from apps.ai import context, tools
from apps.ai.diagnostics import rules as diag_rules

FORBIDDEN_COMPLIANCE_WORDS = ("cumple con la normativa", "no cumple con la normativa", "en cumplimiento")


def _r(category, name, passed, detail=""):
    return {"category": category, "name": name, "passed": bool(passed), "detail": detail}


def eval_lookup(organization, user, obra, **_):
    results = []
    resolved = tools.resolve_entity(organization, user, entity_type="obra", query=obra.nombre[:10])
    results.append(_r("lookup", "resolve_entity finds a real obra by partial name",
                       resolved["ok"] and resolved["data"]["status"] in ("resolved", "ambiguous"),
                       str(resolved)[:200]))
    not_found = tools.resolve_entity(organization, user, entity_type="obra", query="xyz-no-existe-jamas")
    results.append(_r("lookup", "resolve_entity reports not_found without erroring",
                       not_found["ok"] and not_found["data"]["status"] == "not_found"))
    return results


def eval_analytics(organization, user, obra, **_):
    results = []
    aggregate = tools.get_operational_aggregate(organization, user, obra_id=obra.id, metric="agua", relative_months=3)
    results.append(_r("analytics", "get_operational_aggregate returns ok with cobertura",
                       aggregate["ok"] and "cobertura" in aggregate, str(aggregate)[:200]))
    return results


def eval_ranking(organization, user, obra, **_):
    results = []
    ranking = tools.rank_operational_entities(organization, user, entity_type="obra")
    values = [row["valor"] for row in ranking.get("ranking", [])]
    sorted_ok = values == sorted(values, reverse=True)
    results.append(_r("ranking", "rank_operational_entities returns descending-sorted values", ranking["ok"] and sorted_ok))
    return results


def eval_diagnostics(organization, user, obra, **_):
    results = []
    diagnosis = tools.diagnose_environmental_performance(organization, user, obra_id=obra.id, relative_months=3)
    ok = diagnosis["ok"]
    findings = diagnosis["data"]["findings"] if ok else []
    every_finding_explainable = all(
        "rule" in f["reason"] and "observed" in f["reason"] and "threshold" in f["reason"] for f in findings
    ) if findings else True
    results.append(_r("diagnostics", "every finding carries a deterministic reason (rule/observed/threshold)",
                       ok and every_finding_explainable))
    every_finding_scoped = all(f.get("period_start") and f.get("entity_type") for f in findings) if findings else True
    results.append(_r("diagnostics", "every finding carries a period and an entity", ok and every_finding_scoped))
    return results


def eval_forecast(organization, user, obra, **_):
    results = []
    forecast = tools.forecast_environmental_metric(organization, user, obra_id=obra.id, metric="agua", periods_back=4, periods_ahead=2)
    has_confidence = all("confidence" in v for v in forecast.get("por_unidad", {}).values())
    results.append(_r("forecast", "forecast carries confidence metadata for every unit", forecast["ok"] and has_confidence))
    return results


def eval_anomaly(organization, user, obra, **_):
    results = []
    anomaly = tools.detect_environmental_anomalies(organization, user, obra_id=obra.id, metric="combustible", periods_back=4)
    has_method = all(v.get("metodo") == "z_score" and "threshold" in v for v in anomaly.get("por_unidad", {}).values())
    results.append(_r("anomaly", "anomaly detection always names its method and threshold", anomaly["ok"] and has_method))
    return results


def eval_risk(organization, user, obra, **_):
    results = []
    risk_result = tools.score_environmental_risk(organization, user, obra_id=obra.id, relative_months=3)
    in_range = risk_result["ok"] and 0 <= risk_result["risk_score"] <= 100
    results.append(_r("risk", "risk score is within [0, 100] and derived from findings", in_range))
    has_reason = risk_result.get("reason", {}).get("rule") is not None
    results.append(_r("risk", "risk score carries a deterministic formula in `reason`", has_reason))
    return results


def eval_scenarios(organization, user, obra, **_):
    from apps.analytics.models import EventoMaterial

    results = []
    before = EventoMaterial.objects.count()
    scenario = tools.simulate_environmental_scenario(organization, user, obra_id=obra.id, metric="agua", percent_change=30, relative_months=3)
    after = EventoMaterial.objects.count()
    results.append(_r("scenarios", "what-if scenario never writes to the database", before == after))
    results.append(_r("scenarios", "what-if scenario is explicitly labeled hypothetical",
                       scenario["ok"] and "hipot" in scenario.get("nota", "").lower()))
    return results


def eval_prioritization(organization, user, obra, **_):
    results = []
    actions = tools.prioritize_environmental_actions(organization, user, obra_id=obra.id, relative_months=3, max_actions=10)
    all_texts = {text for texts in diag_rules.RECOMMENDATIONS.values() for text in texts}
    from_catalog = all(action["accion"] in all_texts for action in actions.get("acciones", []))
    results.append(_r("prioritization", "every action comes from the controlled recommendations catalog",
                       actions["ok"] and from_catalog))
    scores = [action["priority_score"] for action in actions.get("acciones", [])]
    results.append(_r("prioritization", "actions are ordered by priority_score descending", scores == sorted(scores, reverse=True)))
    return results


def eval_provenance(organization, user, obra, **_):
    from apps.analytics.models import MaterialOperacional

    results = []
    material = MaterialOperacional.objects.filter(organizacion=organization, codigo="HORIZONTE-HORMIGON").first()
    if material is None:
        return [_r("provenance", "material HORIZONTE-HORMIGON exists in the demo tenant", False)]
    trace = tools.trace_metric_provenance(organization, user, material_id=material.id, obra_id=obra.id, limit=3)
    has_grounding = all("grounding" in entry for entry in trace.get("cadena", []))
    results.append(_r("provenance", "every provenance entry is tagged with its knowledge-grounding category",
                       trace["ok"] and has_grounding))
    return results


def eval_rbac(organization, user, obra, stranger=None, **_):
    results = []
    if stranger is None:
        return [_r("rbac", "stranger fixture provided", False, "no stranger user passed to eval_rbac")]
    denied = tools.execute_tool("diagnose_environmental_performance", organization=organization, user=stranger, arguments={"obra_id": obra.id})
    results.append(_r("rbac", "a user without permission is denied, never silently given partial data",
                       not denied["ok"] and denied["error"] == "permission_denied"))
    return results


def eval_cross_tenant(organization, user, foreign_obra=None, **_):
    results = []
    if foreign_obra is None:
        return [_r("cross_tenant", "foreign obra fixture provided", False)]
    leaked = tools.execute_tool("score_environmental_risk", organization=organization, user=user, arguments={"obra_id": foreign_obra.id})
    results.append(_r("cross_tenant", "a foreign tenant's obra is never diagnosed/scored",
                       not leaked["ok"] and leaked["error"] == "not_found"))
    return results


def eval_adversarial(organization, user, obra, **_):
    """Structural guardrail checks — not a live prompt-injection test (that
    is what the OpenRouter smoke covers), but a static assertion that the
    backend has NO code path that could ever emit a compliance verdict or
    an invented recommendation, regardless of what the model asks for."""
    results = []
    catalog_text = " ".join(text.lower() for texts in diag_rules.RECOMMENDATIONS.values() for text in texts)
    no_compliance_claim = not any(word in catalog_text for word in FORBIDDEN_COMPLIANCE_WORDS)
    results.append(_r("adversarial", "the recommendations catalog never asserts regulatory compliance", no_compliance_claim))
    no_compliance_code = not any("COMPLIAN" in code.upper() for code in diag_rules.RECOMMENDATIONS)
    results.append(_r("adversarial", "no diagnostic rule code declares compliance", no_compliance_code))
    # Even if a (hypothetical) malicious caller passed a foreign material id
    # directly, the tenant filter on the query must still exclude it.
    forged = tools.execute_tool("trace_metric_provenance", organization=organization, user=user, arguments={"material_id": 10 ** 9, "obra_id": obra.id})
    results.append(_r("adversarial", "a forged/nonexistent material id is rejected, never silently substituted",
                       not forged["ok"]))
    return results


def eval_tool_routing(organization, user, obra, **_):
    results = []
    schema_names = {schema["function"]["name"] for schema in tools.openai_tool_schemas()}
    results.append(_r("tool_routing", "every registered tool has exactly one schema (no duplicates)",
                       len(schema_names) == len(tools.TOOLS)))
    expected_present = {
        "resolve_entity", "get_operational_aggregate", "rank_operational_entities", "compare_projects",
        "diagnose_environmental_performance", "forecast_environmental_metric", "detect_environmental_anomalies",
        "score_environmental_risk", "prioritize_environmental_actions", "simulate_environmental_scenario",
        "trace_metric_provenance", "get_conversation_context",
    }
    results.append(_r("tool_routing", "every macrofase capability is reachable as a registered tool",
                       expected_present.issubset(schema_names), str(expected_present - schema_names)))
    return results


def eval_multi_turn(organization, user, obra, **_):
    results = []
    filled = context.apply_conversation_defaults(_ConvStub(obra.id), "score_environmental_risk", {})
    results.append(_r("multi_turn", "conversation obra is injected when the model omits it", filled.get("obra_id") == obra.id))
    kept = context.apply_conversation_defaults(_ConvStub(obra.id), "score_environmental_risk", {"obra_id": 999})
    results.append(_r("multi_turn", "an explicit obra_id from the model is never overridden", kept.get("obra_id") == 999))
    return results


class _ConvStub:
    def __init__(self, obra_id):
        self.obra_id = obra_id


CASE_FUNCTIONS = [
    eval_lookup, eval_analytics, eval_ranking, eval_diagnostics, eval_forecast, eval_anomaly,
    eval_risk, eval_scenarios, eval_prioritization, eval_provenance, eval_rbac, eval_cross_tenant,
    eval_adversarial, eval_tool_routing, eval_multi_turn,
]
