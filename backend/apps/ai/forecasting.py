"""AI INTELLIGENCE macrofase — deterministic environmental forecasting.

A forecast is a plain linear trend (ordinary least squares) fitted over
the SAME monthly series `analytics_tools.operational_timeseries` already
computes — never a new data source, never an external ML library. Same
history in, same trend/projection out, regardless of which LLM (or none)
reads the result.

Every result carries `confidence` (`nivel` + `r_squared` + `n_points`) so
the model can never present a projection as certain — a forecast built
from 2 noisy points must read very differently from one built from 12
clean ones, and that judgment is made here, deterministically, not by the
model's tone.
"""
from datetime import date as date_cls
from decimal import Decimal

from . import analytics_tools

MAX_PERIODS_BACK = 24
MAX_PERIODS_AHEAD = 6
MIN_POINTS_FOR_TREND = 2


def _next_period_label(label, offset):
    year, month = int(label[:4]), int(label[5:7])
    index = (year * 12 + (month - 1)) + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _linear_regression(xs, ys):
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return 0.0, mean_y
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _r_squared(xs, ys, slope, intercept):
    mean_y = sum(ys) / len(ys)
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    if ss_tot == 0:
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
        return 1.0 if ss_res == 0 else 0.0
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    return 1 - ss_res / ss_tot


def _confidence(n_points, r_squared):
    if n_points < 3:
        return "low"
    if r_squared >= 0.7 and n_points >= 4:
        return "high"
    if r_squared >= 0.4:
        return "medium"
    return "low"


def _direction(slope, mean_y):
    if mean_y == 0:
        return "estable"
    relative_slope = slope / abs(mean_y) if mean_y else 0
    if relative_slope > 0.02:
        return "creciente"
    if relative_slope < -0.02:
        return "decreciente"
    return "estable"


def _forecast_unit(labeled_values, unit, periods_ahead):
    points = [(index, float(value)) for index, (_, value) in enumerate(labeled_values)]
    n_points = len(points)
    if n_points < MIN_POINTS_FOR_TREND:
        return {
            "unidad": unit, "n_points": n_points, "metodo": "regresion_lineal_min_cuadrados",
            "confidence": {"nivel": "insuficiente", "r_squared": None, "n_points": n_points},
            "tendencia": None, "proyeccion": [],
        }
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    slope, intercept = _linear_regression(xs, ys)
    r_squared = _r_squared(xs, ys, slope, intercept)
    mean_y = sum(ys) / len(ys)
    last_label = labeled_values[-1][0]
    projection = []
    for step in range(1, periods_ahead + 1):
        x = xs[-1] + step
        projected_value = slope * x + intercept
        projection.append({
            "periodo": _next_period_label(last_label, step),
            "valor_proyectado": round(max(projected_value, 0.0), 4),
        })
    return {
        "unidad": unit, "n_points": n_points, "metodo": "regresion_lineal_min_cuadrados",
        "tendencia": {"pendiente": round(slope, 6), "direccion": _direction(slope, mean_y)},
        "proyeccion": projection,
        "confidence": {"nivel": _confidence(n_points, r_squared), "r_squared": round(r_squared, 4), "n_points": n_points},
    }


def forecast_metric(organization, user, *, obra=None, material=None, metric=None, categoria=None,
                     periods_back=6, periods_ahead=3):
    """Deterministic trend + projection for one metric/material, per unit
    (never mixed). Reuses `operational_timeseries` — no independent query."""
    periods_back = max(MIN_POINTS_FOR_TREND, min(int(periods_back or 6), MAX_PERIODS_BACK))
    periods_ahead = max(1, min(int(periods_ahead or 3), MAX_PERIODS_AHEAD))

    series_result = analytics_tools.operational_timeseries(
        organization, user, obra=obra, material=material, metric=metric, categoria=categoria,
        relative_months=periods_back,
    )
    values_by_unit = {}
    for row in series_result["serie"]:
        if not row["con_datos"]:
            continue
        for key, value in row.items():
            if key in ("periodo", "con_datos"):
                continue
            values_by_unit.setdefault(key, []).append((row["periodo"], value["total"]))

    if not values_by_unit:
        return {
            "ok": True, "metrica": series_result["metrica"], "cobertura": series_result["cobertura"],
            "por_unidad": {}, "advertencia": "No hay datos históricos suficientes para proyectar esta métrica.",
        }

    por_unidad = {
        unit: _forecast_unit(labeled_values, unit, periods_ahead)
        for unit, labeled_values in values_by_unit.items()
    }
    return {
        "ok": True, "metrica": series_result["metrica"], "cobertura": series_result["cobertura"],
        "por_unidad": por_unidad,
    }
