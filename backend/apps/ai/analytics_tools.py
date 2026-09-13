"""AI-INTELLIGENCE-02 — deterministic analytical capability layer.

Root cause this module fixes: AI-INTELLIGENCE-01's tool layer only exposed
*point-lookup* tools (one entity, one current-state snapshot). It had no
tool for a time series, a statistical aggregate, a cross-entity ranking, or
a natural-language entity reference — so the model either had to compute a
comparison itself (forbidden by the system prompt) or ask the user for an
internal id it had no way to look up.

Every function below is read-only and does all of the arithmetic itself —
sum, average, min/max, variation, sorting, month-bucketing. The LLM is only
ever handed the finished numbers; it never receives a raw queryset and
never computes a figure on its own. Two domains, kept deliberately separate
because they are backed by different data:

* **Physical consumption** (agua, combustible, energía, residuos,
  materiales) — `material_ledger.material_physical_totals` (real m3/L/kWh/
  kg, from `EventoMaterial`/`Observacion`) and, for total environmental
  *impact* in kgCO2e across all materials, `material_ledger_totals`.
* **Per-asset/machinery attribution** — `sector_flows_v1.sector_summary`,
  the only place with reliable per-asset data (`RegistroFlujoAmbiental
  .activo`); used only for `rank_operational_entities(entity_type="activo")`.

`metrics.py` decides which domain a free-text metric belongs to. Nothing
here is hardcoded to any tenant's seed data (no fixed obra name, id, or
material) — obra/material/activo names are always resolved live.
"""
from collections import defaultdict
from decimal import Decimal

from apps.analytics.models import MaterialOperacional, Obra
from apps.analytics.models.assets import ActivoOperacional
from apps.analytics.permissions import filter_works_for_user
from apps.analytics.services.material_ledger import material_ledger_totals, material_physical_totals
from apps.analytics.services.sector_flows_v1 import sector_summary

from .metrics import month_bounds, resolve_asset_flow_metric, resolve_metric_keyword
from .periods import resolve_period

MAX_ENTITIES = 25


def _decimal(value):
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))


def _effective_categoria(metric, categoria):
    """A recognized metric keyword (agua/combustible/...) wins over a raw
    `categoria` argument only when both somehow disagree; otherwise either
    one alone is enough to select the physical-consumption domain."""
    match = resolve_metric_keyword(metric)
    if match:
        return match["key"], match["categoria"]
    if categoria:
        return categoria, categoria
    return None, None


def _stats(values):
    values = [_decimal(value) for value in values]
    non_zero_periods = [value for value in values if value != 0]
    if not values:
        return {"total": Decimal("0"), "promedio": None, "maximo": None, "minimo": None, "variacion": None, "periodos_con_datos": 0}
    total = sum(values, Decimal("0"))
    promedio = total / len(values)
    maximo = max(values)
    minimo = min(values)
    variacion = None
    if minimo not in (None, Decimal("0")):
        variacion = (maximo - minimo) / minimo
    return {
        "total": total, "promedio": promedio, "maximo": maximo, "minimo": minimo,
        "variacion": variacion, "periodos_con_datos": len(non_zero_periods),
    }


def operational_timeseries(organization, user, *, obra=None, material=None, metric=None, categoria=None,
                            date_from=None, date_to=None, relative_months=None):
    """Per-period (monthly) physical-consumption series for a metric
    (agua/combustible/energía/residuos/materiales) or a specific material.
    Every number here is a real backend sum, never computed by the LLM.

    Every month actually requested (not just the months that happen to
    have data) gets its own row, marked `con_datos: False` when empty — a
    gap must be visible to the model as "no data this month", never
    silently skipped as if the series simply started later."""
    period_start, period_end = resolve_period(date_from=date_from, date_to=date_to, relative_months=relative_months)
    metric_key, effective_categoria = _effective_categoria(metric, categoria)
    totals = material_physical_totals(
        organization, work=obra, material=material, categoria=effective_categoria if material is None else None,
        start=period_start, end=period_end, group_by="periodo",
    )
    por_grupo = totals.get("por_grupo") or {}
    if period_start and period_end:
        labels = [label for _, _, label in month_bounds(period_start, period_end)]
    else:
        labels = sorted(por_grupo.keys(), key=lambda value: value or "")
    serie = []
    for label in labels:
        por_unidad = por_grupo.get(label)
        if por_unidad:
            serie.append({"periodo": label, "con_datos": True, **{unit: dict(values) for unit, values in por_unidad.items()}})
        else:
            serie.append({"periodo": label, "con_datos": False})
    return {
        "ok": True, "tipo_metrica": "consumo_fisico",
        "metrica": metric_key or metric or (material.nombre if material else None),
        "serie": serie,
        "cobertura": {
            "periodos_totales": len(serie),
            "periodos_con_datos": sum(1 for row in serie if row["con_datos"]),
            "entradas_totales": totals["entradas_totales"],
        },
    }


def operational_aggregate(organization, user, *, obra=None, material=None, metric=None, categoria=None,
                           date_from=None, date_to=None, relative_months=None):
    """Total/promedio/máximo/mínimo/variación/entradas/cobertura for one
    metric over one period — computed entirely here, backend-side, per
    unit (never mixing units in one number)."""
    series_result = operational_timeseries(
        organization, user, obra=obra, material=material, metric=metric, categoria=categoria,
        date_from=date_from, date_to=date_to, relative_months=relative_months,
    )
    per_unit = defaultdict(list)
    for row in series_result["serie"]:
        if not row["con_datos"]:
            continue
        for unit, values in row.items():
            if unit in ("periodo", "con_datos"):
                continue
            per_unit[unit].append(values["total"])
    resultado_por_unidad = {unit: _stats(values) for unit, values in per_unit.items()}
    return {
        "ok": True, "tipo_metrica": "consumo_fisico", "metrica": series_result["metrica"],
        "por_unidad": resultado_por_unidad, "cobertura": series_result["cobertura"],
    }


def _obra_name_map(organization, ids):
    ids = [value for value in ids if value is not None]
    if not ids:
        return {}
    return dict(Obra.objects.filter(organizacion=organization, id__in=ids).values_list("id", "nombre"))


def _material_name_map(organization, ids):
    ids = [value for value in ids if value is not None]
    if not ids:
        return {}
    return dict(MaterialOperacional.objects.filter(organizacion=organization, id__in=ids).values_list("id", "nombre"))


def _activo_name_map(organization, ids):
    ids = [value for value in ids if value is not None]
    if not ids:
        return {}
    return dict(ActivoOperacional.objects.filter(organizacion=organization, id__in=ids).values_list("id", "nombre"))


def _flow_by_asset(organization, *, flujos, concepto, obra=None, start=None, end=None):
    """Per-`activo_id` totals for a flow-based metric, via
    `RegistroFlujoAmbiental` — the only path with real per-asset
    attribution. Used exclusively for machinery/asset ranking."""
    buckets = defaultdict(lambda: {"total": Decimal("0"), "mediciones": 0, "unidad": None})
    for flujo in flujos:
        summary = sector_summary(organization, flow=flujo, work=obra.id if obra else None, start=start, end=end)
        for row in summary["totales_compatibles"]:
            if row["concepto"] != concepto:
                continue
            activo_id = row["alcance"].get("activo_id")
            if activo_id is None:
                continue
            bucket = buckets[activo_id]
            bucket["total"] += row["total"]
            bucket["mediciones"] += row["mediciones"]
            bucket["unidad"] = bucket["unidad"] or row["unidad"]
    return buckets


def rank_operational_entities(organization, user, *, entity_type, metric=None, obra=None,
                               categoria=None, date_from=None, date_to=None,
                               relative_months=None, top_n=10):
    """Ranks obras / materiales / categorías / activos / períodos by total
    consumption or impact for one metric. Every value returned is
    comparable (same unit, same period) — sorting is done here, never by
    the LLM."""
    top_n = max(1, min(int(top_n or 10), MAX_ENTITIES))
    period_start, period_end = resolve_period(date_from=date_from, date_to=date_to, relative_months=relative_months)
    metric_key, effective_categoria = _effective_categoria(metric, categoria)

    if entity_type == "activo":
        asset_metric = resolve_asset_flow_metric(metric)
        if not asset_metric:
            return {"ok": False, "error": "unsupported_metric", "reason": "El ranking por activo/maquinaria requiere una métrica de flujo operacional (agua, energía, combustible, residuo)."}
        buckets = _flow_by_asset(organization, flujos=asset_metric["flujos"], concepto=asset_metric["concepto"], obra=obra, start=period_start, end=period_end)
        names = _activo_name_map(organization, buckets.keys())
        rows = [
            {"activo_id": activo_id, "nombre": names.get(activo_id), "valor": data["total"], "unidad": data["unidad"], "mediciones": data["mediciones"]}
            for activo_id, data in buckets.items()
        ]
        rows.sort(key=lambda row: row["valor"], reverse=True)
        return {"ok": True, "tipo_entidad": "activo", "metrica": asset_metric["key"], "ranking": rows[:top_n], "total_entidades": len(rows)}

    if entity_type == "obra":
        allowed_ids = set(filter_works_for_user(Obra.objects.filter(organizacion=organization), user, organization).values_list("id", flat=True))
        if metric_key or effective_categoria:
            totals = material_physical_totals(organization, categoria=effective_categoria, start=period_start, end=period_end, group_by="obra")
        else:
            totals = material_ledger_totals(organization, start=period_start, end=period_end, group_by="obra")
        rows = []
        for obra_id, por_unidad in (totals.get("por_grupo") or {}).items():
            # RBAC fix: neither ledger helper is per-user obra-scoped —
            # never surface an obra this user cannot access.
            if obra_id not in allowed_ids:
                continue
            for unit, values in por_unidad.items():
                rows.append({"obra_id": obra_id, "valor": values["total"], "unidad": unit, "entradas": values["entradas"]})
        names = _obra_name_map(organization, [row["obra_id"] for row in rows])
        for row in rows:
            row["nombre"] = names.get(row["obra_id"])
        rows.sort(key=lambda row: row["valor"], reverse=True)
        return {"ok": True, "tipo_entidad": "obra", "metrica": metric_key or metric or "impacto_ambiental_total", "ranking": rows[:top_n], "total_entidades": len(rows)}

    if entity_type in ("material", "categoria", "standard"):
        if metric_key or effective_categoria:
            totals = material_physical_totals(organization, work=obra, categoria=effective_categoria, start=period_start, end=period_end, group_by=entity_type if entity_type != "standard" else "categoria")
        else:
            totals = material_ledger_totals(organization, work=obra, start=period_start, end=period_end, group_by=entity_type)
        rows = []
        for key, por_unidad in (totals.get("por_grupo") or {}).items():
            for unit, values in por_unidad.items():
                rows.append({"clave": key, "valor": values["total"], "unidad": unit, "entradas": values["entradas"]})
        if entity_type == "material":
            names = _material_name_map(organization, [row["clave"] for row in rows])
            for row in rows:
                row["nombre"] = names.get(row["clave"])
        rows.sort(key=lambda row: row["valor"], reverse=True)
        return {"ok": True, "tipo_entidad": entity_type, "metrica": metric_key or metric or "impacto_ambiental_total", "ranking": rows[:top_n], "total_entidades": len(rows)}

    if entity_type == "periodo":
        series_result = operational_timeseries(organization, user, obra=obra, metric=metric, categoria=categoria, date_from=date_from, date_to=date_to, relative_months=relative_months)
        rows = []
        for row in series_result["serie"]:
            if not row["con_datos"]:
                continue
            for unit, values in row.items():
                if unit in ("periodo", "con_datos"):
                    continue
                rows.append({"periodo": row["periodo"], "valor": values["total"], "unidad": unit})
        rows.sort(key=lambda row: row["valor"], reverse=True)
        return {"ok": True, "tipo_entidad": "periodo", "metrica": series_result["metrica"], "ranking": rows[:top_n], "total_entidades": len(rows)}

    return {"ok": False, "error": "unsupported_entity", "reason": f"Tipo de entidad '{entity_type}' no soportado para ranking."}


def compare_projects(organization, user, *, metric=None, categoria=None, date_from=None,
                      date_to=None, relative_months=None, top_n=5):
    """Auto-resolves every obra the user can see in this tenant and ranks
    them by impact (default) or by one physical-consumption metric — the
    user never has to supply an obra id or an obra list for this to work."""
    ranking = rank_operational_entities(
        organization, user, entity_type="obra", metric=metric, categoria=categoria,
        date_from=date_from, date_to=date_to, relative_months=relative_months, top_n=top_n,
    )
    if not ranking["ok"]:
        return ranking
    rows = ranking["ranking"]
    if not rows:
        return {"ok": True, "comparacion": [], "obra_con_mayor_valor": None, "por_que": None, "metrica": ranking["metrica"], "reason": "No hay datos suficientes para comparar obras en este período."}
    top = rows[0]
    contexto = None
    if top.get("obra_id") and not resolve_metric_keyword(metric):
        from apps.analytics.services.material_hotspots import material_hotspots

        obra = Obra.objects.filter(organizacion=organization, id=top["obra_id"]).first()
        if obra is not None:
            hotspots = material_hotspots(organization, work=obra, categoria=categoria or None)
            for payload in hotspots.values():
                if payload.get("materiales"):
                    contexto = {"principal_contribuyente": payload["materiales"][0]}
                    break
    return {"ok": True, "comparacion": rows, "obra_con_mayor_valor": top, "por_que": contexto, "metrica": ranking["metrica"]}
