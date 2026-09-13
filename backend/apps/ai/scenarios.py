"""AI INTELLIGENCE macrofase — what-if scenario simulation.

Operates ONLY on an in-memory hypothetical number — never writes to the
database, never mutates a real `EventoMaterial`/`Observacion`/anything
persisted. The hypothetical value is classified with the exact same pure
rule functions `diagnostics.rules` already uses for real data (they are
pure functions of numbers, so reusing them for a hypothetical number
duplicates nothing and guarantees a scenario is judged by the identical
thresholds a real period would be).
"""
from decimal import Decimal, InvalidOperation

from . import analytics_tools
from .diagnostics import rules as diag_rules
from .periods import resolve_comparison_periods

MAX_PERCENT_CHANGE = 500.0


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def simulate_scenario(organization, user, *, obra, metric=None, categoria=None, material=None,
                       percent_change=None, absolute_value=None, date_from=None, date_to=None,
                       relative_months=None):
    """Hypothetical: "what if this metric's current-period total were
    `percent_change`% different (or exactly `absolute_value`)?" Returns the
    real base value, the hypothetical value, and how that hypothetical
    value would be classified by the SAME deterministic rules diagnostics
    uses — never asserts this happened or will happen."""
    if percent_change is None and absolute_value is None:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere percent_change o absolute_value."}
    if percent_change is not None and abs(float(percent_change)) > MAX_PERCENT_CHANGE:
        return {"ok": False, "error": "invalid_arguments", "reason": f"percent_change fuera de rango (máximo ±{MAX_PERCENT_CHANGE}%)."}

    cur_start, cur_end, prev_start, prev_end = resolve_comparison_periods(
        date_from=date_from, date_to=date_to, relative_months=relative_months,
    )
    current_agg = analytics_tools.operational_aggregate(
        organization, user, obra=obra, material=material, metric=metric, categoria=categoria,
        date_from=cur_start, date_to=cur_end,
    )
    previous_agg = analytics_tools.operational_aggregate(
        organization, user, obra=obra, material=material, metric=metric, categoria=categoria,
        date_from=prev_start, date_to=prev_end,
    )
    if not current_agg["por_unidad"]:
        return {
            "ok": True, "obra_id": obra.id, "obra_nombre": obra.nombre, "metrica": metric or categoria,
            "resultados": {}, "advertencia": "No hay datos base para simular un escenario sobre esta métrica/período.",
        }

    resultados = {}
    for unit, stats in current_agg["por_unidad"].items():
        base_value = stats["total"]
        if percent_change is not None:
            factor = Decimal("1") + (_to_decimal(percent_change) / Decimal("100"))
            hypothetical_value = base_value * factor
        else:
            hypothetical_value = _to_decimal(absolute_value)
            if hypothetical_value is None:
                return {"ok": False, "error": "invalid_arguments", "reason": "absolute_value debe ser numérico."}
        previous_value = (previous_agg["por_unidad"].get(unit) or {}).get("total", Decimal("0"))

        finding = (
            diag_rules.rule_new_activity(
                metric=metric or categoria or "métrica", unit=unit, obra=obra, period_start=cur_start, period_end=cur_end,
                current_value=hypothetical_value, previous_value=previous_value,
            )
            or diag_rules.rule_significant_increase(
                metric=metric or categoria or "métrica", unit=unit, obra=obra, period_start=cur_start, period_end=cur_end,
                current_value=hypothetical_value, previous_value=previous_value,
            )
            or diag_rules.rule_significant_decrease(
                metric=metric or categoria or "métrica", unit=unit, obra=obra, period_start=cur_start, period_end=cur_end,
                current_value=hypothetical_value, previous_value=previous_value,
            )
        )
        resultados[unit] = {
            "valor_base_real": base_value,
            "valor_hipotetico": hypothetical_value,
            "valor_periodo_anterior_real": previous_value,
            "clasificacion_hipotetica": (
                {"code": finding.code, "severity": finding.severity, "reason": finding.reason}
                if finding else {"code": None, "severity": "sin_cambio_relevante", "reason": None}
            ),
        }

    return {
        "ok": True, "obra_id": obra.id, "obra_nombre": obra.nombre, "metrica": metric or categoria,
        "escenario": {"percent_change": percent_change, "absolute_value": absolute_value},
        "period": {"start": cur_start, "end": cur_end},
        "resultados": resultados,
        "nota": "Escenario hipotético: no modifica datos reales ni se persiste ningún cambio.",
    }
