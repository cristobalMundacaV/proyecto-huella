"""AI INTELLIGENCE macrofase — multi-turn conversation context.

Nothing here is inferred by the LLM: the conversation's own append-only
message history (already persisted, immutable) is the only source of
"what obra/period/metric were we just discussing". Same transcript ->
same inferred context, regardless of which model is reading it.

Two deterministic mechanisms, deliberately conservative:
1. `apply_conversation_defaults` fills `obra_id` from `conversation.obra`
   ONLY when the tool call didn't specify an obra at all — it never
   overrides an argument the model actually provided.
2. `infer_conversation_context` scans past tool results for the most
   recent obra/metric/period actually used, so the model (or a human
   debugging a transcript) can explicitly recall it via the
   `get_conversation_context` tool instead of silently re-guessing.
"""
TOOLS_WITH_OBRA_ARG = {
    "get_project_summary", "get_environmental_indicators", "get_emissions_summary",
    "get_material_summary", "get_material_hotspots", "get_evidence_quality", "get_open_alerts",
    "get_operational_timeseries", "get_operational_aggregate", "rank_operational_entities",
    "diagnose_environmental_performance", "forecast_environmental_metric", "detect_environmental_anomalies",
    "score_environmental_risk", "simulate_environmental_scenario",
}
_OBRA_ARG_NAMES = ("obra_id", "obra", "query")
_METRIC_ARG_NAMES = ("metric", "categoria")
_PERIOD_ARG_NAMES = ("date_from", "date_to", "relative_months")


def apply_conversation_defaults(conversation, tool_name, arguments):
    """Returns a NEW arguments dict — never mutates the caller's dict.
    Only fills `obra_id` when: the tool accepts one, the conversation has
    a fixed obra, and the call supplied none of obra_id/obra/query."""
    arguments = dict(arguments or {})
    if tool_name not in TOOLS_WITH_OBRA_ARG:
        return arguments
    if not getattr(conversation, "obra_id", None):
        return arguments
    if any(arguments.get(name) for name in _OBRA_ARG_NAMES):
        return arguments
    arguments["obra_id"] = conversation.obra_id
    return arguments


def build_context_note(conversation):
    """A short factual system-visible note so the model learns
    `Conversation.obra` (set once, at conversation creation, never
    changed) WITHOUT needing to call a tool first. Returns `None` when the
    conversation has no fixed obra — nothing is ever asserted that isn't
    already true of the conversation record itself."""
    obra = getattr(conversation, "obra", None)
    if obra is None:
        return None
    return (
        f"Esta conversación está fijada a la obra \"{obra.nombre}\" (obra_id={obra.id}). "
        "No le pidas al usuario el nombre de la obra — usa este id directamente en las herramientas "
        "que lo acepten, salvo que el usuario mencione explícitamente una obra distinta."
    )


def infer_conversation_context(conversation):
    """Walks the conversation's TOOL messages, most recent first, and
    returns the last obra/metric/period seen in a successful call's
    arguments or result — never a guess, only what was already used."""
    context = {"obra_id": getattr(conversation, "obra_id", None), "obra_nombre": None, "metric": None, "period": None}
    messages = conversation.messages.filter(role="tool").order_by("-created_at")[:50]
    for message in messages:
        result = message.tool_result or {}
        if not result.get("ok"):
            continue
        data = result.get("data") or {}
        if context["obra_id"] is None:
            obra_id = data.get("obra_id")
            if obra_id is not None:
                context["obra_id"] = obra_id
                context["obra_nombre"] = data.get("obra_nombre")
        if context["metric"] is None:
            metric = data.get("metrica") or data.get("metric")
            if metric:
                context["metric"] = metric
        if context["period"] is None:
            period = data.get("period") or data.get("periodo")
            if period:
                context["period"] = period
        if all(context[key] is not None for key in ("obra_id", "metric", "period")):
            break
    return context
