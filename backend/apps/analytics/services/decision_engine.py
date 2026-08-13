from .emission_semantics import (
    is_diesel_emission,
    is_electricity_emission,
    is_transport_emission,
)


def normalize_source(value):
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
    selected_organizacion="Todas",
):
    simulated_rows = []

    for row in rows:
        organizacion = row.get("organizacion")
        should_apply_organizacion = selected_organizacion in (None, "", "Todas", organizacion)
        cantidad = to_float(row.get("cantidad"))
        factor = to_float(row.get("factor_emision"))

        if should_apply_organizacion and is_diesel_emission(row) and not is_transport_emission(row):
            cantidad *= 1 - to_float(diesel_reduction) / 100

        if should_apply_organizacion and is_electricity_emission(row):
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
    by_organizacion = {}
    by_source = {}

    for row in rows:
        organizacion = row.get("organizacion", "Sin organizacion")
        fuente = row.get("fuente_emision", "Sin fuente")
        emisiones = to_float(row.get("emisiones"))
        by_organizacion[organizacion] = by_organizacion.get(organizacion, 0) + emisiones
        by_source[fuente] = by_source.get(fuente, 0) + emisiones

    return {
        "total_emisiones": total,
        "emisiones_por_organizacion": dict(
            sorted(by_organizacion.items(), key=lambda item: item[1], reverse=True)
        ),
        "emisiones_por_fuente": dict(
            sorted(by_source.items(), key=lambda item: item[1], reverse=True)
        ),
        "datos": rows,
    }


def optimize_rows(rows):
    best_scenario = None
    evaluated_scenarios = 0
    current_total = sum(to_float(row.get("emisiones")) for row in rows)
    has_diesel = any(
        is_diesel_emission(row) and not is_transport_emission(row) for row in rows
    )
    has_electricity = any(is_electricity_emission(row) for row in rows)

    if not has_diesel and not has_electricity:
        return {
            "dieselReduction": 0,
            "electricityIncrease": 0,
            "currentTotal": current_total,
            "evaluatedScenarios": 0,
            "simulatedTotal": current_total,
            "reductionPct": 0,
            "rows": rows,
            "message": "No hay fuentes optimizables detectadas.",
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
    by_source = summary.get("emisiones_por_fuente") or {}
    by_stage = summary.get("emisiones_por_etapa") or {}
    rows = summary.get("datos") or []

    max_source = max(by_source.values(), default=0)
    max_stage = max(by_stage.values(), default=0)
    source_concentration = (max_source / total) * 100 if total > 0 else 0
    stage_concentration = (max_stage / total) * 100 if total > 0 else 0
    diesel_present = any(is_diesel_emission(row) for row in rows)
    potential_reduction = (
        max(to_float(optimized_scenario.get("reductionPct")), 0)
        if optimized_scenario
        else 0
    )

    total_component = min(total / 5000, 1) * 100
    diesel_component = 100 if diesel_present else 0

    score = round(
        total_component * 0.3
        + source_concentration * 0.25
        + stage_concentration * 0.2
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
            "sourceConcentration": source_concentration,
            "stageConcentration": stage_concentration,
            "dieselPresent": diesel_present,
            "potentialReduction": potential_reduction,
        },
    }
