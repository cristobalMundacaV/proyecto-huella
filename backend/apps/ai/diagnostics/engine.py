"""AI-INTELLIGENCE-03 — deterministic diagnostic engine.

`run_environmental_diagnostics` is the ONLY entry point. It:
    1. resolves the current/previous comparison periods (`periods.py`);
    2. gathers numbers exclusively via `apps.ai.analytics_tools` (AI-02) —
       never recomputes a total/ranking itself;
    3. runs every rule in `rules.py` over those numbers;
    4. scores and sorts the findings (`scoring.py`);
    5. returns a plain, JSON-serializable dict (`serializers.py`).

RBAC/tenant scoping is inherited entirely from `analytics_tools`/
`rank_operational_entities` (which already intersects against
`filter_works_for_user`) and from the caller having already resolved
`obra` through `apps.ai.tools._resolve_obra` (which enforces
`require_work_access`) — this module never queries the database with a
raw id, only through those already-guarded paths.
"""
from collections import defaultdict
from decimal import Decimal

from apps.analytics.models import MaterialOperacional

from .. import analytics_tools
from ..metrics import resolve_metric_keyword
from ..periods import resolve_comparison_periods
from . import rules, scoring
from .evidence import gather_evidence_stats
from .serializers import serialize_diagnostics

DEFAULT_METRICS = ["agua", "combustible", "energia", "residuos", "materiales"]
# Only "combustible" has real per-asset attribution in this schema
# (`RegistroFlujoAmbiental.activo`) — confirmed by the AI-INTELLIGENCE-02
# audit. Never claim asset-level attribution for a metric that has none.
ASSET_ATTRIBUTABLE_METRICS = {"combustible"}
MAX_FINDINGS_DEFAULT = 20


def _unit_value(agg_result, unit):
    stats = (agg_result.get("por_unidad") or {}).get(unit)
    return stats["total"] if stats else Decimal("0")


def _diagnose_variation_and_drivers(organization, user, *, obra, metric, cur_start, cur_end, prev_start, prev_end):
    findings = []
    current_agg = analytics_tools.operational_aggregate(organization, user, obra=obra, metric=metric, date_from=cur_start, date_to=cur_end)
    previous_agg = analytics_tools.operational_aggregate(organization, user, obra=obra, metric=metric, date_from=prev_start, date_to=prev_end)
    units = set((current_agg.get("por_unidad") or {}).keys()) | set((previous_agg.get("por_unidad") or {}).keys())

    for unit in units:
        current_value = _unit_value(current_agg, unit)
        previous_value = _unit_value(previous_agg, unit)

        new_activity = rules.rule_new_activity(
            metric=metric, unit=unit, obra=obra, period_start=cur_start, period_end=cur_end,
            current_value=current_value, previous_value=previous_value,
        )
        if new_activity:
            findings.append(new_activity)
            continue

        variation_finding = rules.rule_significant_increase(
            metric=metric, unit=unit, obra=obra, period_start=cur_start, period_end=cur_end,
            current_value=current_value, previous_value=previous_value,
        ) or rules.rule_significant_decrease(
            metric=metric, unit=unit, obra=obra, period_start=cur_start, period_end=cur_end,
            current_value=current_value, previous_value=previous_value,
        )
        if not variation_finding:
            continue
        findings.append(variation_finding)

        total_delta = float(current_value) - float(previous_value)
        driver = None
        if metric in ASSET_ATTRIBUTABLE_METRICS:
            driver = _driver_finding(
                organization, user, obra=obra, metric=metric, entity_type="activo",
                cur_start=cur_start, cur_end=cur_end, prev_start=prev_start, prev_end=prev_end, total_delta=total_delta,
            )
        elif metric == "materiales":
            driver = _driver_finding(
                organization, user, obra=obra, metric=metric, entity_type="material",
                cur_start=cur_start, cur_end=cur_end, prev_start=prev_start, prev_end=prev_end, total_delta=total_delta,
            )
        if driver:
            variation_finding.drivers = driver.drivers
            findings.append(driver)

    return findings


def _driver_finding(organization, user, *, obra, metric, entity_type, cur_start, cur_end, prev_start, prev_end, total_delta):
    current = analytics_tools.rank_operational_entities(organization, user, entity_type=entity_type, metric=metric, obra=obra, date_from=cur_start, date_to=cur_end, top_n=25)
    previous = analytics_tools.rank_operational_entities(organization, user, entity_type=entity_type, metric=metric, obra=obra, date_from=prev_start, date_to=prev_end, top_n=25)
    if not current.get("ok") or not previous.get("ok"):
        return None
    rule_fn = rules.rule_change_driver_activo if entity_type == "activo" else rules.rule_change_driver_material
    return rule_fn(
        metric=metric, obra=obra, period_start=cur_start, period_end=cur_end,
        current_ranking=current["ranking"], previous_ranking=previous["ranking"], total_delta=total_delta,
    )


def _diagnose_concentration(organization, user, *, obra, metric, cur_start, cur_end):
    if metric in ASSET_ATTRIBUTABLE_METRICS:
        entity_type = "activo"
    elif metric == "materiales":
        entity_type = "material"
    else:
        return None
    ranking = analytics_tools.rank_operational_entities(organization, user, entity_type=entity_type, metric=metric, obra=obra, date_from=cur_start, date_to=cur_end, top_n=25)
    if not ranking.get("ok") or not ranking["ranking"]:
        return None
    total = sum(float(row["valor"]) for row in ranking["ranking"])
    return rules.rule_consumption_concentration(
        metric=metric, entity_type=entity_type, obra=obra, period_start=cur_start, period_end=cur_end,
        ranking=ranking["ranking"], total=total,
    )


def _diagnose_impact_concentration(organization, user, *, obra, cur_start, cur_end):
    ranking = analytics_tools.rank_operational_entities(organization, user, entity_type="material", obra=obra, date_from=cur_start, date_to=cur_end, top_n=25)
    if not ranking.get("ok") or not ranking["ranking"]:
        return None
    total = sum(float(row["valor"]) for row in ranking["ranking"])
    return rules.rule_impact_concentration(obra=obra, period_start=cur_start, period_end=cur_end, ranking=ranking["ranking"], total=total)


def _diagnose_variability_and_coverage(organization, user, *, obra, metric, prev_start, cur_end):
    timeseries = analytics_tools.operational_timeseries(organization, user, obra=obra, metric=metric, date_from=prev_start, date_to=cur_end)
    if not timeseries.get("ok"):
        return []
    findings = []
    values_by_unit = defaultdict(list)
    for row in timeseries["serie"]:
        if not row["con_datos"]:
            continue
        for key, value in row.items():
            if key in ("periodo", "con_datos"):
                continue
            values_by_unit[key].append(value["total"])
    for unit, values in values_by_unit.items():
        variability = rules.rule_high_variability(
            metric=metric, unit=unit, obra=obra, period_start=prev_start, period_end=cur_end, values=values,
        )
        if variability:
            findings.append(variability)
    coverage = rules.rule_incomplete_coverage(
        metric=metric, obra=obra, period_start=prev_start, period_end=cur_end,
        periodos_totales=timeseries["cobertura"]["periodos_totales"],
        periodos_con_datos=timeseries["cobertura"]["periodos_con_datos"],
    )
    if coverage:
        findings.append(coverage)
    return findings


def _diagnose_evidence(organization, user, *, obra, metric, cur_start, cur_end):
    match = resolve_metric_keyword(metric)
    categoria = match["categoria"] if match else metric
    materials = list(MaterialOperacional.objects.filter(organizacion=organization, categoria=categoria))
    if not materials:
        return []
    stats = gather_evidence_stats(organization, materials=materials, obra=obra, start=cur_start, end=cur_end)
    findings = []
    missing_evidence = rules.rule_missing_evidence(
        metric=metric, obra=obra, period_start=cur_start, period_end=cur_end,
        total_eventos=stats["total_eventos"], con_evidencia=stats["con_evidencia"],
    )
    if missing_evidence:
        findings.append(missing_evidence)
    unmapped_factor = rules.rule_unmapped_factor(
        metric=metric, obra=obra, period_start=cur_start, period_end=cur_end,
        unmapped_materials=stats["unmapped_materials"],
    )
    if unmapped_factor:
        findings.append(unmapped_factor)
    low_quality = rules.rule_low_data_quality(
        metric=metric, obra=obra, period_start=cur_start, period_end=cur_end,
        evaluated_count=stats["evaluated_count"], poor_count=stats["poor_count"],
    )
    if low_quality:
        findings.append(low_quality)
    unsupported = rules.rule_unsupported_data(
        metric=metric, obra=obra, period_start=cur_start, period_end=cur_end,
        unsupported_count=stats["unsupported_count"], total_eventos=stats["total_eventos"],
    )
    if unsupported:
        findings.append(unsupported)
    return findings


def run_environmental_diagnostics(organization, user, *, obra, date_from=None, date_to=None,
                                   relative_months=None, metrics=None, max_findings=MAX_FINDINGS_DEFAULT):
    """`obra` must already be a resolved, access-checked `Obra` instance
    (see `apps.ai.tools.diagnose_environmental_performance`) — this
    function performs no id resolution and no permission check of its own,
    by design: it only ever consumes already-guarded data sources."""
    cur_start, cur_end, prev_start, prev_end = resolve_comparison_periods(
        date_from=date_from, date_to=date_to, relative_months=relative_months,
    )
    metrics = list(metrics) if metrics else list(DEFAULT_METRICS)
    max_findings = max(1, min(int(max_findings or MAX_FINDINGS_DEFAULT), 50))

    findings = []
    for metric in metrics:
        findings.extend(_diagnose_variation_and_drivers(
            organization, user, obra=obra, metric=metric, cur_start=cur_start, cur_end=cur_end,
            prev_start=prev_start, prev_end=prev_end,
        ))
        concentration = _diagnose_concentration(organization, user, obra=obra, metric=metric, cur_start=cur_start, cur_end=cur_end)
        if concentration:
            findings.append(concentration)
        findings.extend(_diagnose_variability_and_coverage(
            organization, user, obra=obra, metric=metric, prev_start=prev_start, cur_end=cur_end,
        ))
        findings.extend(_diagnose_evidence(organization, user, obra=obra, metric=metric, cur_start=cur_start, cur_end=cur_end))

    impact_concentration = _diagnose_impact_concentration(organization, user, obra=obra, cur_start=cur_start, cur_end=cur_end)
    if impact_concentration:
        findings.append(impact_concentration)

    for finding in findings:
        finding.priority_score = scoring.compute_priority(finding)
    findings.sort(key=lambda finding: (finding.priority_score, finding.code), reverse=True)
    findings = findings[:max_findings]

    return serialize_diagnostics(
        obra=obra, period_start=cur_start, period_end=cur_end, previous_period=(prev_start, prev_end),
        findings=findings, metrics_analyzed=metrics,
    )
