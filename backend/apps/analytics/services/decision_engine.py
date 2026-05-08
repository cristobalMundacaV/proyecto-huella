from .activity_semantics import (
    is_diesel_activity,
    is_electricity_activity,
    is_transport_activity,
)


def normalize_activity(value):
    return str(value or "").strip().lower()


def to_float(value, fallback=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def simulate_rows(
    rows,
    diesel_reduction=0,
    electricity_increase=0,
    selected_company="Todas",
):
    simulated_rows = []

    for row in rows:
        empresa = row.get("empresa")
        should_apply_company = selected_company in (None, "", "Todas", empresa)
        cantidad = to_float(row.get("cantidad"))
        factor = to_float(row.get("factor_emision"))

        if should_apply_company and is_diesel_activity(row) and not is_transport_activity(row):
            cantidad *= 1 - to_float(diesel_reduction) / 100

        if should_apply_company and is_electricity_activity(row):
            cantidad *= 1 + to_float(electricity_increase) / 100

        simulated_rows.append(
            {
                **row,
                "cantidad": cantidad,
                "emisiones": cantidad * factor,
            }
        )

    return simulated_rows


def summarize_rows(rows):
    total = sum(to_float(row.get("emisiones")) for row in rows)
    by_company = {}
    by_activity = {}

    for row in rows:
        empresa = row.get("empresa", "Sin empresa")
        actividad = row.get("actividad", "Sin actividad")
        emisiones = to_float(row.get("emisiones"))
        by_company[empresa] = by_company.get(empresa, 0) + emisiones
        by_activity[actividad] = by_activity.get(actividad, 0) + emisiones

    return {
        "total_emisiones": total,
        "emisiones_por_empresa": dict(
            sorted(by_company.items(), key=lambda item: item[1], reverse=True)
        ),
        "emisiones_por_actividad": dict(
            sorted(by_activity.items(), key=lambda item: item[1], reverse=True)
        ),
        "datos": rows,
    }


def optimize_rows(rows):
    best_scenario = None
    evaluated_scenarios = 0
    current_total = sum(to_float(row.get("emisiones")) for row in rows)
    has_diesel = any(
        is_diesel_activity(row) and not is_transport_activity(row) for row in rows
    )
    has_electricity = any(is_electricity_activity(row) for row in rows)

    if not has_diesel and not has_electricity:
        return {
            "dieselReduction": 0,
            "electricityIncrease": 0,
            "currentTotal": current_total,
            "evaluatedScenarios": 0,
            "simulatedTotal": current_total,
            "reductionPct": 0,
            "rows": rows,
            "message": "No hay actividades optimizables detectadas.",
        }

    diesel_range = range(0, 81, 5) if has_diesel else range(0, 1, 5)
    electricity_range = range(0, 61, 5) if has_electricity else range(0, 1, 5)

    for diesel_reduction in diesel_range:
        for electricity_increase in electricity_range:
            evaluated_scenarios += 1
            simulated_rows = simulate_rows(
                rows,
                diesel_reduction=diesel_reduction,
                electricity_increase=electricity_increase,
            )
            simulated_total = sum(
                to_float(row.get("emisiones")) for row in simulated_rows
            )
            reduction_pct = (
                ((current_total - simulated_total) / current_total) * 100
                if current_total > 0
                else 0
            )

            if (
                best_scenario is None
                or reduction_pct > best_scenario["reductionPct"]
            ):
                best_scenario = {
                    "dieselReduction": diesel_reduction,
                    "electricityIncrease": electricity_increase,
                    "currentTotal": current_total,
                    "evaluatedScenarios": evaluated_scenarios,
                    "simulatedTotal": simulated_total,
                    "reductionPct": reduction_pct,
                    "rows": simulated_rows,
                }

    return best_scenario


def calculate_risk_profile(summary, optimized_scenario=None):
    total = to_float(summary.get("total_emisiones"))
    by_activity = summary.get("emisiones_por_actividad") or {}
    by_unit = summary.get("emisiones_por_unidad_operativa") or {}
    rows = summary.get("datos") or []

    max_activity = max(by_activity.values(), default=0)
    max_unit = max(by_unit.values(), default=0)
    activity_concentration = (max_activity / total) * 100 if total > 0 else 0
    unit_concentration = (max_unit / total) * 100 if total > 0 else 0
    diesel_present = any(is_diesel_activity(row) for row in rows)
    potential_reduction = (
        max(to_float(optimized_scenario.get("reductionPct")), 0)
        if optimized_scenario
        else 0
    )

    total_component = min(total / 5000, 1) * 100
    diesel_component = 100 if diesel_present else 0

    score = round(
        total_component * 0.3
        + activity_concentration * 0.25
        + unit_concentration * 0.2
        + diesel_component * 0.15
        + potential_reduction * 0.1
    )

    if score > 70:
        label = "Alto"
    elif score > 30:
        label = "Medio"
    else:
        label = "Bajo"

    return {
        "score": min(score, 100),
        "label": label,
        "factors": {
            "totalEmissions": total,
            "activityConcentration": activity_concentration,
            "companyConcentration": unit_concentration,
            "unitConcentration": unit_concentration,
            "dieselPresent": diesel_present,
            "potentialReduction": potential_reduction,
        },
    }
