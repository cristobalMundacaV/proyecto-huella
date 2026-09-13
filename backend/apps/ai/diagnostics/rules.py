"""AI-INTELLIGENCE-03 — deterministic diagnostic rules.

Every function here is a pure classifier: it receives already-computed
structured numbers (never a queryset, never raw model instances) and
returns one `DiagnosticFinding` or `None`. No rule queries the database and
no rule calls an LLM — `engine.py` gathers the numbers (by calling
`apps.ai.analytics_tools`, never recomputing anything itself), these
functions only classify them against a fixed threshold.

`DIAGNOSTIC_RULESET_VERSION` lets a stored/returned finding be traced back
to the exact threshold set that produced it — bump it whenever a threshold
below changes.
"""
from dataclasses import dataclass, field

DIAGNOSTIC_RULESET_VERSION = "1.0"

# Centralized, configurable thresholds — never inline "magic numbers" in a
# rule function below.
VARIATION_THRESHOLDS = {"medium": 20.0, "high": 40.0, "critical": 75.0}
CONCENTRATION_THRESHOLDS = {"medium": 50.0, "high": 65.0, "critical": 80.0}
EVIDENCE_COVERAGE_THRESHOLD = 80.0  # below this % of events with evidence -> finding
FACTOR_COVERAGE_THRESHOLD = 100.0  # any unmapped material -> finding (no partial tolerance)
DATA_QUALITY_POOR_STATES = {"incompleto", "requiere_revision", "no_confiable", "no_calculable"}
DATA_QUALITY_POOR_SHARE_THRESHOLD = 20.0  # % of evaluated observations in a poor state
VARIABILITY_CV_THRESHOLD = 0.5
MIN_ENTITIES_FOR_CONCENTRATION = 2  # a single-source category is not "concentration"


@dataclass
class DiagnosticFinding:
    code: str
    severity: str  # info | low | medium | high | critical
    title: str
    description: str
    period_start: object
    period_end: object
    metric: str | None = None
    entity_type: str | None = None
    entity_id: object = None
    entity_name: str | None = None
    reason: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    drivers: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    priority_score: int = 0


def _classify(value, thresholds):
    """Highest tier whose threshold `value` meets, or None."""
    tier = None
    for level in ("medium", "high", "critical"):
        if value >= thresholds[level]:
            tier = level
    return tier


def _variation_percent(current, previous):
    return float((current - previous) / previous * 100)


def rule_new_activity(*, metric, unit, obra, period_start, period_end, current_value, previous_value):
    """DIAG-01/02 special case: `previous == 0` is not a variation percent
    (division by zero) — it is a distinct, informational fact: activity
    that did not exist in the comparison period."""
    if previous_value not in (0, None) or not current_value:
        return None
    return DiagnosticFinding(
        code="NEW_ACTIVITY", severity="info",
        title=f"Actividad nueva de {metric}",
        description=f"Se registró consumo de {metric} en el período analizado sin actividad comparable en el período anterior.",
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type="obra", entity_id=getattr(obra, "id", None), entity_name=getattr(obra, "nombre", None),
        reason={"rule": "previous_value == 0", "observed": float(current_value), "threshold": 0},
        evidence={"obra_id": getattr(obra, "id", None), "current_value": float(current_value), "unit": unit},
        metadata={"variation_percent": None},
    )


def rule_significant_increase(*, metric, unit, obra, period_start, period_end, current_value, previous_value):
    """DIAG-01 — significant increase vs the immediately preceding,
    equal-length period."""
    if not previous_value:
        return None
    variation = _variation_percent(current_value, previous_value)
    if variation <= 0:
        return None
    tier = _classify(variation, VARIATION_THRESHOLDS)
    if tier is None:
        return None
    return DiagnosticFinding(
        code="CONSUMPTION_INCREASE", severity=tier,
        title=f"Aumento relevante de {metric}",
        description=(
            f"El consumo de {metric} aumentó {variation:.1f}% respecto del período anterior "
            f"({float(previous_value):.2f} -> {float(current_value):.2f} {unit})."
        ),
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type="obra", entity_id=getattr(obra, "id", None), entity_name=getattr(obra, "nombre", None),
        reason={"rule": f"variation_percent >= {VARIATION_THRESHOLDS['medium']}", "observed": round(variation, 2), "threshold": VARIATION_THRESHOLDS["medium"]},
        evidence={"obra_id": getattr(obra, "id", None), "current_value": float(current_value), "previous_value": float(previous_value), "unit": unit},
        metadata={"variation_percent": variation},
    )


def rule_significant_decrease(*, metric, unit, obra, period_start, period_end, current_value, previous_value):
    """DIAG-02 — significant decrease. Always `info` severity and never
    phrased as an improvement: a raw decrease is not normalized against
    activity/production, so "better" cannot be concluded from this alone."""
    if not previous_value:
        return None
    variation = _variation_percent(current_value, previous_value)
    if variation >= 0:
        return None
    magnitude = abs(variation)
    tier = _classify(magnitude, VARIATION_THRESHOLDS)
    if tier is None:
        return None
    return DiagnosticFinding(
        code="CONSUMPTION_DECREASE", severity="info",
        title=f"Disminución relevante de {metric}",
        description=(
            f"El consumo de {metric} disminuyó {magnitude:.1f}% respecto del período anterior "
            f"({float(previous_value):.2f} -> {float(current_value):.2f} {unit})."
        ),
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type="obra", entity_id=getattr(obra, "id", None), entity_name=getattr(obra, "nombre", None),
        reason={"rule": f"variation_percent <= -{VARIATION_THRESHOLDS['medium']}", "observed": round(variation, 2), "threshold": -VARIATION_THRESHOLDS["medium"]},
        evidence={"obra_id": getattr(obra, "id", None), "current_value": float(current_value), "previous_value": float(previous_value), "unit": unit},
        metadata={"variation_percent": variation, "classification": "positive_signal_not_confirmed"},
    )


def _concentration(*, code, title_prefix, kind, metric, obra, period_start, period_end, ranking, total, entity_type):
    if not ranking or len(ranking) < MIN_ENTITIES_FOR_CONCENTRATION or not total:
        return None
    top = ranking[0]
    share = float(top["valor"]) / float(total) * 100
    tier = _classify(share, CONCENTRATION_THRESHOLDS)
    if tier is None:
        return None
    name = top.get("nombre") or str(top.get("clave") or top.get(f"{entity_type}_id"))
    return DiagnosticFinding(
        code=code, severity=tier,
        title=f"{title_prefix}: {name}",
        description=f"\"{name}\" concentra el {share:.1f}% del {'impacto' if kind == 'impact' else 'consumo'} de {metric} en el período.",
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type=entity_type, entity_id=top.get(f"{entity_type}_id") or top.get("clave"), entity_name=name,
        reason={"rule": f"share_percent >= {CONCENTRATION_THRESHOLDS['medium']}", "observed": round(share, 2), "threshold": CONCENTRATION_THRESHOLDS["medium"]},
        evidence={"obra_id": getattr(obra, "id", None), "total": float(total), "entity_value": float(top["valor"]), "unidad": top.get("unidad")},
        drivers=[{"entity_type": entity_type, "entity_id": top.get(f"{entity_type}_id") or top.get("clave"), "name": name, "contribution_percent": round(share, 2)}],
        metadata={"share_percent": share, "kind": kind},
    )


def rule_impact_concentration(*, obra, period_start, period_end, ranking, total):
    """DIAG-03 — one material dominating the obra's total kgCO2e impact."""
    return _concentration(
        code="IMPACT_CONCENTRATION", title_prefix="Concentración de impacto ambiental", kind="impact",
        metric="impacto_ambiental_total", obra=obra, period_start=period_start, period_end=period_end,
        ranking=ranking, total=total, entity_type="material",
    )


def rule_consumption_concentration(*, metric, entity_type, obra, period_start, period_end, ranking, total):
    """DIAG-04 — one entity (activo/material) dominating the PHYSICAL
    consumption of one metric. Never mixed with impact (kgCO2e) — `metric`
    here is always the physical-consumption category, `ranking`/`total`
    always come from the physical path (see `engine.py`)."""
    return _concentration(
        code="CONSUMPTION_CONCENTRATION", title_prefix="Concentración de consumo", kind="physical",
        metric=metric, obra=obra, period_start=period_start, period_end=period_end,
        ranking=ranking, total=total, entity_type=entity_type,
    )


def _change_driver(*, code, entity_type, metric, obra, period_start, period_end, current_ranking, previous_ranking, total_delta):
    if not total_delta:
        return None
    previous_by_id = {row.get(f"{entity_type}_id") or row.get("clave"): float(row["valor"]) for row in previous_ranking}
    deltas = []
    for row in current_ranking:
        key = row.get(f"{entity_type}_id") or row.get("clave")
        delta = float(row["valor"]) - previous_by_id.get(key, 0.0)
        deltas.append((key, row.get("nombre") or str(key), delta, row.get("unidad")))
    if not deltas:
        return None
    key, name, delta, unit = max(deltas, key=lambda item: abs(item[2]))
    contribution = (delta / total_delta) * 100
    if abs(contribution) < CONCENTRATION_THRESHOLDS["medium"]:
        return None
    return DiagnosticFinding(
        code=code, severity="medium" if abs(contribution) < CONCENTRATION_THRESHOLDS["high"] else "high",
        title=f"Cambio concentrado en {name}",
        description=f"El cambio de {metric} se concentra principalmente en \"{name}\", que explica el {contribution:.1f}% de la variación total.",
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type=entity_type, entity_id=key, entity_name=name,
        reason={"rule": f"abs(contribution_percent) >= {CONCENTRATION_THRESHOLDS['medium']}", "observed": round(contribution, 2), "threshold": CONCENTRATION_THRESHOLDS["medium"]},
        evidence={"obra_id": getattr(obra, "id", None), "entity_delta": delta, "total_delta": total_delta, "unidad": unit},
        drivers=[{"entity_type": entity_type, "entity_id": key, "name": name, "contribution_percent": round(contribution, 2)}],
        metadata={"contribution_percent": contribution},
    )


def rule_change_driver_activo(*, metric, obra, period_start, period_end, current_ranking, previous_ranking, total_delta):
    """DIAG-09 — mathematically attribute a metric's change to one asset."""
    return _change_driver(
        code="CHANGE_DRIVER_ACTIVO", entity_type="activo", metric=metric, obra=obra,
        period_start=period_start, period_end=period_end,
        current_ranking=current_ranking, previous_ranking=previous_ranking, total_delta=total_delta,
    )


def rule_change_driver_material(*, metric, obra, period_start, period_end, current_ranking, previous_ranking, total_delta):
    """DIAG-10 — same attribution, for materials instead of assets."""
    return _change_driver(
        code="CHANGE_DRIVER_MATERIAL", entity_type="material", metric=metric, obra=obra,
        period_start=period_start, period_end=period_end,
        current_ranking=current_ranking, previous_ranking=previous_ranking, total_delta=total_delta,
    )


def rule_high_variability(*, metric, unit, obra, period_start, period_end, values):
    """DIAG-11 — coefficient of variation across the available monthly
    buckets. Never labeled an "anomaly" — only "variabilidad"."""
    if len(values) < 2:
        return None
    values = [float(value) for value in values]
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std_dev = variance ** 0.5
    cv = std_dev / mean
    if cv < VARIABILITY_CV_THRESHOLD:
        return None
    return DiagnosticFinding(
        code="HIGH_VARIABILITY", severity="medium" if cv < 1.0 else "high",
        title=f"Variabilidad alta de {metric}",
        description=f"El consumo de {metric} presenta alta variabilidad durante el período analizado (CV={cv:.2f}).",
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type="obra", entity_id=getattr(obra, "id", None), entity_name=getattr(obra, "nombre", None),
        reason={"rule": f"coefficient_of_variation >= {VARIABILITY_CV_THRESHOLD}", "observed": round(cv, 3), "threshold": VARIABILITY_CV_THRESHOLD},
        evidence={"obra_id": getattr(obra, "id", None), "values": values, "unidad": unit},
        metadata={"cv": cv},
    )


def rule_incomplete_coverage(*, metric, obra, period_start, period_end, periodos_totales, periodos_con_datos):
    """DIAG-12 — missing months inside the analyzed window make a temporal
    comparison potentially unrepresentative; this must be surfaced
    explicitly rather than silently computing over fewer periods."""
    if periodos_totales <= 0 or periodos_con_datos >= periodos_totales:
        return None
    return DiagnosticFinding(
        code="INCOMPLETE_COVERAGE", severity="medium",
        title=f"Cobertura incompleta de {metric}",
        description=(
            f"Existen {periodos_totales - periodos_con_datos} de {periodos_totales} períodos sin registros de "
            f"{metric}, por lo que la comparación temporal puede no ser representativa."
        ),
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type="obra", entity_id=getattr(obra, "id", None), entity_name=getattr(obra, "nombre", None),
        reason={"rule": "periodos_con_datos < periodos_totales", "observed": periodos_con_datos, "threshold": periodos_totales},
        evidence={"obra_id": getattr(obra, "id", None), "periodos_totales": periodos_totales, "periodos_con_datos": periodos_con_datos},
        metadata={"affected_count": periodos_totales - periodos_con_datos},
    )


def rule_missing_evidence(*, metric, obra, period_start, period_end, total_eventos, con_evidencia):
    """DIAG-05 — evidence coverage below threshold."""
    if not total_eventos:
        return None
    coverage = con_evidencia / total_eventos * 100
    if coverage >= EVIDENCE_COVERAGE_THRESHOLD:
        return None
    missing = total_eventos - con_evidencia
    return DiagnosticFinding(
        code="MISSING_EVIDENCE", severity="high" if coverage < 50 else "medium",
        title=f"Evidencia incompleta de {metric}",
        description=f"{missing} de {total_eventos} registros de {metric} del período no tienen evidencia documental asociada ({coverage:.1f}% de cobertura).",
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type="obra", entity_id=getattr(obra, "id", None), entity_name=getattr(obra, "nombre", None),
        reason={"rule": f"evidence_coverage_percent < {EVIDENCE_COVERAGE_THRESHOLD}", "observed": round(coverage, 2), "threshold": EVIDENCE_COVERAGE_THRESHOLD},
        evidence={"obra_id": getattr(obra, "id", None), "total_eventos": total_eventos, "eventos_sin_evidencia": missing},
        metadata={"affected_count": missing, "coverage_percent": coverage},
    )


def rule_unmapped_factor(*, metric, obra, period_start, period_end, unmapped_materials):
    """DIAG-06 — a material with no governed environmental factor mapped
    blocks trustworthy emissions calculation for its records. The model
    never picks a factor itself — this only flags the gap for human review."""
    if not unmapped_materials:
        return None
    total_records = sum(item["eventos"] for item in unmapped_materials)
    names = ", ".join(item["nombre"] for item in unmapped_materials)
    return DiagnosticFinding(
        code="UNMAPPED_FACTOR", severity="high",
        title=f"Factor ambiental no mapeado en {metric}",
        description=f"{total_records} registros de {metric} corresponden a material(es) sin factor ambiental mapeado ({names}).",
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type="obra", entity_id=getattr(obra, "id", None), entity_name=getattr(obra, "nombre", None),
        reason={"rule": "material.factor_mapeado == False", "observed": len(unmapped_materials), "threshold": 0},
        evidence={"obra_id": getattr(obra, "id", None), "materiales": unmapped_materials},
        metadata={"affected_count": total_records},
    )


def rule_low_data_quality(*, metric, obra, period_start, period_end, evaluated_count, poor_count):
    """DIAG-07 — reuses the system's own `EvaluacionCalidadDato` states
    (never a new quality scale invented for diagnostics)."""
    if not evaluated_count:
        return None
    share = poor_count / evaluated_count * 100
    if share < DATA_QUALITY_POOR_SHARE_THRESHOLD:
        return None
    return DiagnosticFinding(
        code="LOW_DATA_QUALITY", severity="medium" if share < 50 else "high",
        title=f"Calidad de datos baja en {metric}",
        description=f"{poor_count} de {evaluated_count} observaciones evaluadas de {metric} tienen calidad insuficiente ({share:.1f}%).",
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type="obra", entity_id=getattr(obra, "id", None), entity_name=getattr(obra, "nombre", None),
        reason={"rule": f"poor_quality_share_percent >= {DATA_QUALITY_POOR_SHARE_THRESHOLD}", "observed": round(share, 2), "threshold": DATA_QUALITY_POOR_SHARE_THRESHOLD},
        evidence={"obra_id": getattr(obra, "id", None), "evaluated_count": evaluated_count, "poor_count": poor_count},
        metadata={"affected_count": poor_count},
    )


def rule_unsupported_data(*, metric, obra, period_start, period_end, unsupported_count, total_eventos):
    """DIAG-08 — a record that is BOTH missing evidence AND of poor quality
    is a stronger signal than either alone; reported with elevated
    severity but as its own distinct finding (never merged into DIAG-05/07's
    counts)."""
    if not unsupported_count:
        return None
    return DiagnosticFinding(
        code="UNSUPPORTED_DATA", severity="critical" if unsupported_count > total_eventos / 2 else "high",
        title=f"Datos sin respaldo suficiente en {metric}",
        description=(
            f"{unsupported_count} registros de {metric} no tienen evidencia documental Y tienen calidad "
            f"insuficiente — no deberían usarse todavía para calcular emisiones."
        ),
        period_start=period_start, period_end=period_end, metric=metric,
        entity_type="obra", entity_id=getattr(obra, "id", None), entity_name=getattr(obra, "nombre", None),
        reason={"rule": "sin_evidencia AND calidad_pobre", "observed": unsupported_count, "threshold": 0},
        evidence={"obra_id": getattr(obra, "id", None), "unsupported_count": unsupported_count, "total_eventos": total_eventos},
        metadata={"affected_count": unsupported_count},
    )


RECOMMENDATIONS = {
    "CONSUMPTION_INCREASE": [
        "Revisar el detalle operacional del período para confirmar la causa del aumento.",
        "Priorizar la revisión de los activos/materiales que más contribuyeron (ver 'drivers').",
    ],
    "CHANGE_DRIVER_ACTIVO": [
        "Revisar los registros del activo señalado antes de reportar el período.",
    ],
    "CHANGE_DRIVER_MATERIAL": [
        "Revisar los registros del material señalado antes de reportar el período.",
    ],
    "IMPACT_CONCENTRATION": [
        "Priorizar acciones de reducción sobre la entidad que concentra el impacto.",
    ],
    "CONSUMPTION_CONCENTRATION": [
        "Priorizar la revisión operacional de la entidad que concentra el consumo.",
    ],
    "MISSING_EVIDENCE": [
        "Revisar los registros sin respaldo documental.",
        "Solicitar o adjuntar evidencia antes del cierre del período.",
    ],
    "UNMAPPED_FACTOR": [
        "Revisar la clasificación del dato.",
        "Asignar un factor de emisión gobernado antes del cálculo final.",
    ],
    "LOW_DATA_QUALITY": [
        "Revisar y corregir las observaciones marcadas con calidad insuficiente.",
    ],
    "UNSUPPORTED_DATA": [
        "No utilizar estos registros en cálculos de huella hasta regularizar evidencia y calidad.",
        "Priorizar su revisión antes que cualquier otro hallazgo de este período.",
    ],
    "HIGH_VARIABILITY": [
        "Revisar si la variabilidad corresponde a un patrón operacional esperado o a un registro irregular.",
    ],
    "INCOMPLETE_COVERAGE": [
        "Completar los registros del período faltante antes de interpretar la tendencia.",
    ],
    "NEW_ACTIVITY": [
        "Confirmar que la actividad nueva está correctamente registrada y clasificada.",
    ],
    "CONSUMPTION_DECREASE": [
        "Confirmar si la disminución corresponde a menor actividad o a un registro incompleto del período.",
    ],
}
