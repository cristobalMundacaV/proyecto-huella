"""AI INTELLIGENCE macrofase — deterministic anomaly detection.

Point-level complement to `diagnostics.rules.rule_high_variability` (which
only says "this whole window is noisy"): this flags WHICH specific
period(s) are statistical outliers, using a named, fixed method — the
population z-score over the same monthly series `operational_timeseries`
already computes. Every reported anomaly carries `method`, `threshold`
and the observed deviation — nothing here is "this looks weird" without a
number backing it.
"""
from . import analytics_tools

DEFAULT_Z_THRESHOLD = 2.0
MIN_POINTS_FOR_DETECTION = 4


def _stats(values):
    n = len(values)
    mean = sum(values) / n
    variance = sum((value - mean) ** 2 for value in values) / n
    std_dev = variance ** 0.5
    return mean, std_dev


def _detect_unit(labeled_values, unit, threshold):
    values = [float(value) for _, value in labeled_values]
    n_points = len(values)
    if n_points < MIN_POINTS_FOR_DETECTION:
        return {
            "unidad": unit, "metodo": "z_score", "threshold": threshold, "n_points": n_points,
            "anomalias": [], "advertencia": "Puntos insuficientes para una detección estadísticamente significativa.",
        }
    mean, std_dev = _stats(values)
    anomalias = []
    if std_dev > 0:
        for (periodo, value), numeric in zip(labeled_values, values):
            z = (numeric - mean) / std_dev
            if abs(z) >= threshold:
                anomalias.append({
                    "periodo": periodo, "valor": numeric, "media": round(mean, 4),
                    "desviacion_estandar": round(std_dev, 4), "z_score": round(z, 3),
                    "direccion": "sobre_lo_esperado" if z > 0 else "bajo_lo_esperado",
                })
    return {
        "unidad": unit, "metodo": "z_score", "threshold": threshold, "n_points": n_points,
        "media": round(mean, 4), "desviacion_estandar": round(std_dev, 4), "anomalias": anomalias,
    }


def detect_anomalies(organization, user, *, obra=None, material=None, metric=None, categoria=None,
                      periods_back=6, threshold=None):
    """Deterministic outlier detection per unit, over the requested window.
    Reuses `operational_timeseries` — no independent query, no new data
    source. `threshold` defaults to `DEFAULT_Z_THRESHOLD` and is always
    echoed back so the model can never claim a different one."""
    threshold = float(threshold) if threshold else DEFAULT_Z_THRESHOLD
    periods_back = max(MIN_POINTS_FOR_DETECTION, min(int(periods_back or 6), 24))

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

    por_unidad = {unit: _detect_unit(labeled_values, unit, threshold) for unit, labeled_values in values_by_unit.items()}
    return {
        "ok": True, "metrica": series_result["metrica"], "cobertura": series_result["cobertura"],
        "por_unidad": por_unidad,
    }
