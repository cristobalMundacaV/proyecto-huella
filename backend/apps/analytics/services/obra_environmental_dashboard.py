"""CARBONO-ZERO-V1 — unified obra environmental dashboard & period readiness.

Single consolidation point for "how is this obra doing environmentally"
questions. Deliberately reuses the SAME already-built, already-tested
engines rather than recomputing anything:

* `apps.analytics.services.material_ledger.material_ledger_totals` — GEI
  impact (kgCO2e) totals and per-category breakdown (used here for the
  Alcance 1/2/3 split, via a fixed GHG-Protocol convention table — see
  `SCOPE_BY_CATEGORY` below; this is a standard classification applied to
  categories the system already models, never an invented number).
* `apps.ai.analytics_tools` (AI-INTELLIGENCE-02) — physical consumption
  per flow (agua/combustible/energía/residuos/materiales).
* `apps.ai.diagnostics` (AI-INTELLIGENCE-03) — findings (what changed,
  what's concentrated, what evidence/quality/factor gaps exist).
* `apps.ai.risk` (AI INTELLIGENCE macrofase) — the single risk score/tier
  this dashboard's "estado ejecutivo" is classified from.

This guarantees the dashboard, the AI copiloto, and any future report all
read the exact same number for the exact same obra/period — there is only
one motor, this module (and the report/export builders that reuse it) are
presentation layers on top of it, never a second calculation path.
"""
from decimal import Decimal

from django.db.models import Q

from apps.analytics.models import MaterialOperacional
from apps.analytics.models.professional import RevisionProfesionalAmbiental
from apps.analytics.services.material_ledger import material_ledger_totals

FLOW_METRICS = ["agua", "combustible", "energia", "residuos", "materiales"]

# GHG Protocol convention applied to the categories this system already
# models (`MaterialOperacional.categoria`) — not an invented split: fuel
# combustion on-site is Alcance 1, purchased electricity is Alcance 2,
# everything else accounted here (materials, waste, water) is Alcance 3.
SCOPE_BY_CATEGORY = {
    "combustible": 1,
    "energia": 2,
    "materiales": 3,
    "residuos": 3,
    "agua": 3,
}

READINESS_THRESHOLDS = {
    "cobertura_registros_pct": 90.0,
    "evidencia_pct": 90.0,
    "factores_pct": 100.0,
    "validacion_profesional_pct": 90.0,
}

ESTADO_LABELS = {
    "estable": "Estable",
    "atencion": "Atención",
    "critica": "Crítica",
    "periodo_incompleto": "Período incompleto",
    "lista_para_reporte": "Lista para reporte",
}


def _round(value, digits=2):
    if value is None:
        return None
    return round(float(value), digits)


def _impact_and_scopes(organizacion, obra, start, end):
    totals = material_ledger_totals(organizacion, work=obra, start=start, end=end, group_by="categoria")
    total_kg = totals["totales_por_unidad"].get("kgCO2e", {}).get("total", Decimal("0"))
    scope_totals = {1: Decimal("0"), 2: Decimal("0"), 3: Decimal("0")}
    for categoria, por_unidad in (totals.get("por_grupo") or {}).items():
        kg = por_unidad.get("kgCO2e", {}).get("total", Decimal("0"))
        scope_totals[SCOPE_BY_CATEGORY.get(categoria, 3)] += kg
    return total_kg, scope_totals, totals["entradas_totales"]


def _flow_kpis(organizacion, user, obra, start, end):
    from apps.ai import analytics_tools

    kpis = {}
    for metric in FLOW_METRICS:
        aggregate = analytics_tools.operational_aggregate(
            organizacion, user, obra=obra, metric=metric, date_from=start, date_to=end,
        )
        kpis[metric] = aggregate.get("por_unidad") or {}
    return kpis


def _waste_valorization_rate(organizacion, obra, start, end):
    """Tasa de valorización = cantidad valorizada / cantidad total generada,
    usando el mismo dato físico de residuos ya agregado (nunca un cálculo
    paralelo) — sólo se distingue por `RegistroFlujoAmbiental.destino_operacional`
    cuando existe granularidad suficiente para ello; si no hay esa
    granularidad, se reporta `None` en vez de inventar una tasa."""
    from apps.analytics.models import RegistroFlujoAmbiental
    from apps.analytics.selectors.environmental_flows import environmental_records_for_organization

    valorizables = {
        RegistroFlujoAmbiental.DestinoOperacional.REUTILIZACION,
        RegistroFlujoAmbiental.DestinoOperacional.RECICLAJE,
        RegistroFlujoAmbiental.DestinoOperacional.VALORIZACION,
        RegistroFlujoAmbiental.DestinoOperacional.SUBPRODUCTO_REUTILIZADO,
    }
    records = environmental_records_for_organization(
        organizacion, flow=RegistroFlujoAmbiental.Flujo.RESIDUO, work=obra.id if obra else None, start=start, end=end,
    )
    total = Decimal("0")
    valorizado = Decimal("0")
    found = False
    for record in records:
        for observation in record.actividad.observaciones.all():
            if observation.concepto != "cantidad_residuo" or observation.valor_numerico is None:
                continue
            found = True
            total += observation.valor_numerico
            if record.destino_operacional in valorizables:
                valorizado += observation.valor_numerico
    if not found or total == 0:
        return None
    return _round((valorizado / total) * Decimal("100"), 1)


def build_period_readiness(organizacion, user, obra, *, date_from=None, date_to=None, relative_months=None):
    """Deterministic "¿está listo este período para reportarse?" check —
    every percentage here is computed from real rows, never estimated."""
    from apps.ai import analytics_tools
    from apps.ai.diagnostics.evidence import gather_evidence_stats
    from apps.ai.periods import resolve_period

    start, end = resolve_period(date_from=date_from, date_to=date_to, relative_months=relative_months)

    coverage_ratios = []
    for metric in FLOW_METRICS:
        timeseries = analytics_tools.operational_timeseries(organizacion, user, obra=obra, metric=metric, date_from=start, date_to=end)
        cobertura = timeseries["cobertura"]
        if cobertura["periodos_totales"]:
            coverage_ratios.append(cobertura["periodos_con_datos"] / cobertura["periodos_totales"])
    cobertura_pct = _round(sum(coverage_ratios) / len(coverage_ratios) * 100, 1) if coverage_ratios else None

    material_filter = Q(eventos__obra=obra) if obra else Q()
    materials_in_scope = list(
        MaterialOperacional.objects.filter(organizacion=organizacion).filter(material_filter).distinct()
    )
    evidence_stats = (
        gather_evidence_stats(organizacion, materials=materials_in_scope, obra=obra, start=start, end=end)
        if materials_in_scope else None
    )
    evidencia_pct = (
        _round(evidence_stats["con_evidencia"] / evidence_stats["total_eventos"] * 100, 1)
        if evidence_stats and evidence_stats["total_eventos"] else None
    )
    unmapped_materials = evidence_stats["unmapped_materials"] if evidence_stats else []
    factores_pct = (
        _round((len(materials_in_scope) - len(unmapped_materials)) / len(materials_in_scope) * 100, 1)
        if materials_in_scope else None
    )

    review_filter = Q(observacion__actividad__obra=obra) | Q(calculo__actividad__obra=obra)
    reviews = RevisionProfesionalAmbiental.objects.filter(organizacion=organizacion).filter(review_filter)
    if start:
        reviews = reviews.filter(created_at__date__gte=start)
    if end:
        reviews = reviews.filter(created_at__date__lte=end)
    total_reviews = reviews.count()
    validated_reviews = reviews.filter(
        estado__in=[RevisionProfesionalAmbiental.Estado.VALIDADA, RevisionProfesionalAmbiental.Estado.VALIDADA_OBSERVACIONES],
    ).count()
    pending_reviews = reviews.filter(estado=RevisionProfesionalAmbiental.Estado.PENDIENTE).count()
    validacion_pct = _round(validated_reviews / total_reviews * 100, 1) if total_reviews else None

    pendientes = []
    if evidence_stats:
        faltantes = evidence_stats["total_eventos"] - evidence_stats["con_evidencia"]
        if faltantes:
            pendientes.append(f"{faltantes} registro(s) sin evidencia documental")
    if unmapped_materials:
        pendientes.append(f"{len(unmapped_materials)} material(es) sin factor ambiental asignado")
    if pending_reviews:
        pendientes.append(f"{pending_reviews} revisión(es) profesional(es) pendiente(s)")
    if evidence_stats and evidence_stats["poor_count"]:
        pendientes.append(f"{evidence_stats['poor_count']} observación(es) con calidad insuficiente")

    checks = {
        "cobertura_registros_pct": cobertura_pct, "evidencia_pct": evidencia_pct,
        "factores_pct": factores_pct, "validacion_profesional_pct": validacion_pct,
    }
    listo = not pendientes and all(
        value is not None and value >= READINESS_THRESHOLDS[key] for key, value in checks.items()
    )

    return {
        "periodo": {"start": start, "end": end},
        **checks,
        "pendientes": pendientes,
        "listo_para_reporte": listo,
    }


def _classify_estado_ejecutivo(risk_result, readiness):
    if readiness["listo_para_reporte"]:
        return "lista_para_reporte"
    coverage = readiness.get("cobertura_registros_pct")
    if coverage is not None and coverage < 70.0:
        return "periodo_incompleto"
    nivel = risk_result.get("nivel")
    if nivel == "critico":
        return "critica"
    if nivel in ("alto", "medio"):
        return "atencion"
    return "estable"


def build_obra_dashboard(organizacion, user, obra, *, date_from=None, date_to=None, relative_months=None):
    """The single consolidated payload the obra dashboard (and, later, the
    Informe Ambiental de Obra) is built from. `obra` must already be an
    RBAC-checked `Obra` instance (see `views_obra_dashboard.py`) — this
    function performs no permission check of its own, exactly like
    `apps.ai.diagnostics.engine.run_environmental_diagnostics`."""
    from apps.ai import analytics_tools
    from apps.ai.diagnostics import run_environmental_diagnostics
    from apps.ai.periods import resolve_comparison_periods
    from apps.ai.risk import score_environmental_risk

    cur_start, cur_end, prev_start, prev_end = resolve_comparison_periods(
        date_from=date_from, date_to=date_to, relative_months=relative_months,
    )

    total_kg, scope_totals, entradas_impacto = _impact_and_scopes(organizacion, obra, cur_start, cur_end)
    flow_kpis = _flow_kpis(organizacion, user, obra, cur_start, cur_end)
    valorizacion_pct = _waste_valorization_rate(organizacion, obra, cur_start, cur_end)

    diagnostics_result = run_environmental_diagnostics(
        organizacion, user, obra=obra, date_from=cur_start, date_to=cur_end,
    )
    risk_result = score_environmental_risk(
        organizacion, user, obra=obra, date_from=cur_start, date_to=cur_end,
    )
    readiness = build_period_readiness(
        organizacion, user, obra, date_from=cur_start, date_to=cur_end,
    )
    estado = _classify_estado_ejecutivo(risk_result, readiness)

    findings = diagnostics_result["findings"]
    findings_altos = sum(1 for finding in findings if finding["severity"] in ("high", "critical"))
    evidencia_faltante = sum(1 for finding in findings if finding["code"] == "MISSING_EVIDENCE")
    factores_pendientes = sum(1 for finding in findings if finding["code"] == "UNMAPPED_FACTOR")

    return {
        "obra_id": obra.id, "obra_nombre": obra.nombre, "organizacion_id": organizacion.organizacion_id,
        "organizacion_nombre": organizacion.nombre,
        "period": {"start": cur_start, "end": cur_end}, "previous_period": {"start": prev_start, "end": prev_end},
        "estado_ejecutivo": {"codigo": estado, "label": ESTADO_LABELS[estado]},
        "kpis": {
            "huella_total_tco2e": _round(total_kg / Decimal("1000"), 3),
            "alcance_1_tco2e": _round(scope_totals[1] / Decimal("1000"), 3),
            "alcance_2_tco2e": _round(scope_totals[2] / Decimal("1000"), 3),
            "alcance_3_tco2e": _round(scope_totals[3] / Decimal("1000"), 3),
            "energia": flow_kpis.get("energia", {}),
            "combustible": flow_kpis.get("combustible", {}),
            "agua": flow_kpis.get("agua", {}),
            "residuos": flow_kpis.get("residuos", {}),
            "materiales": flow_kpis.get("materiales", {}),
            "tasa_valorizacion_pct": valorizacion_pct,
            "calidad_datos_pct": readiness["evidencia_pct"],
            "cobertura_evidencia_pct": readiness["evidencia_pct"],
        },
        "resumen_ejecutivo": {
            "hallazgos_altos": findings_altos, "evidencias_faltantes": evidencia_faltante,
            "factores_pendientes": factores_pendientes,
            "cobertura_periodo_pct": readiness["cobertura_registros_pct"],
        },
        "risk": risk_result,
        "readiness": readiness,
        "diagnostics_summary": diagnostics_result["summary"],
        "top_findings": findings[:10],
        "ruleset_version": diagnostics_result["ruleset_version"],
    }
