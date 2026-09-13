"""CARBONO-ZERO — organization (portfolio) environmental dashboard.

Aggregates the SAME per-obra motor (`obra_environmental_dashboard.build_obra_dashboard`)
across every obra the requesting user can see in this organization — never a
second calculation path, never a new formula. This module only loops over
already-computed per-obra dashboards, sums/averages/ranks their numbers, and
derives at most 3 portfolio-level insights from them.

RBAC/tenant-safety comes from `filter_works_for_user`, the same scoping used
by the existing `/obras/` list endpoint — a user with `alcance=OBRAS` only
ever sees (and this dashboard only ever aggregates) the obras assigned to
them.
"""
from apps.analytics.models import Obra
from apps.analytics.permissions import filter_works_for_user
from apps.analytics.services.obra_environmental_dashboard import build_obra_dashboard

MAX_INSIGHTS = 3
MAX_PRIORITY_WORKS = 5
MAX_WORKS_AGGREGATED = 30  # portfolio-scale safety cap, documented in the product report


def _obras_for_user(organizacion, user):
    return filter_works_for_user(Obra.objects.all(), user, organizacion).order_by("nombre")[:MAX_WORKS_AGGREGATED]


def _round(value, digits=3):
    if value is None:
        return None
    return round(float(value), digits)


def _average(values):
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 1)


def _priority_score(dashboard):
    risk = dashboard["risk"].get("risk_score") or 0
    findings_penalty = dashboard["resumen_ejecutivo"]["hallazgos_altos"] * 10
    coverage = dashboard["readiness"]["cobertura_registros_pct"]
    readiness_gap = (100 - coverage) * 0.5 if coverage is not None else 25
    return risk + findings_penalty + readiness_gap


def _portfolio_insights(per_obra, huella_total, impacto_por_flujo):
    """At most `MAX_INSIGHTS` insights, each derived directly from numbers
    already present in the per-obra dashboards — no free-form generation."""
    insights = []

    if huella_total and impacto_por_flujo:
        top_flujo, top_value = max(impacto_por_flujo.items(), key=lambda item: item[1])
        share = round(top_value / huella_total * 100) if huella_total else None
        if share is not None and share >= 40:
            insights.append({
                "priority": "alta", "code": "PORTFOLIO_FLOW_CONCENTRATION",
                "title": f"El {share}% de la huella consolidada se concentra en {top_flujo}.",
                "description": (
                    f"El flujo '{top_flujo}' concentra aproximadamente {share}% de la huella total "
                    "del portafolio en el período analizado."
                ),
            })

    zero_evidence = [d for d in per_obra if (d["kpis"]["cobertura_evidencia_pct"] or 0) == 0]
    if zero_evidence:
        obra = zero_evidence[0]
        insights.append({
            "priority": "alta", "code": "PORTFOLIO_ZERO_EVIDENCE",
            "title": f"{obra['obra_nombre']} tiene 0% de cobertura documental.",
            "description": (
                f"No hay evidencia registrada que respalde los datos ambientales de {obra['obra_nombre']} "
                "en el período analizado."
            ),
        })

    riskiest = sorted(per_obra, key=lambda d: d["risk"].get("risk_score") or 0, reverse=True)
    if riskiest and (riskiest[0]["risk"].get("risk_score") or 0) > 0:
        top = riskiest[0]
        insights.append({
            "priority": "media", "code": "PORTFOLIO_TOP_RISK",
            "title": f"{top['obra_nombre']} concentra el mayor riesgo ambiental del portafolio.",
            "description": (
                f"Riesgo {top['risk'].get('nivel')} (score {top['risk'].get('risk_score')}) "
                "en el período analizado."
            ),
        })

    return insights[:MAX_INSIGHTS]


def build_organization_dashboard(organizacion, user, *, date_from=None, date_to=None, relative_months=None):
    obras = list(_obras_for_user(organizacion, user))
    per_obra = []
    omitted = []
    for obra in obras:
        try:
            per_obra.append(
                build_obra_dashboard(
                    organizacion, user, obra, date_from=date_from, date_to=date_to, relative_months=relative_months,
                )
            )
        except Exception:  # pragma: no cover - one obra's failure must not break the whole portfolio view
            omitted.append(obra.id)

    huella_total = sum((d["kpis"]["huella_total_tco2e"] or 0) for d in per_obra)
    alcance_1 = sum((d["kpis"]["alcance_1_tco2e"] or 0) for d in per_obra)
    alcance_2 = sum((d["kpis"]["alcance_2_tco2e"] or 0) for d in per_obra)
    alcance_3 = sum((d["kpis"]["alcance_3_tco2e"] or 0) for d in per_obra)

    impacto_por_flujo = {}
    for dashboard in per_obra:
        for categoria, value in (dashboard["kpis"].get("impacto_por_flujo_tco2e") or {}).items():
            impacto_por_flujo[categoria] = impacto_por_flujo.get(categoria, 0) + (value or 0)

    emisiones_por_obra = [
        {
            "obra_id": d["obra_id"], "obra_nombre": d["obra_nombre"],
            "huella_total_tco2e": d["kpis"]["huella_total_tco2e"],
        }
        for d in per_obra
    ]
    readiness_por_obra = [
        {
            "obra_id": d["obra_id"], "obra_nombre": d["obra_nombre"],
            "listo_para_reporte": d["readiness"]["listo_para_reporte"],
            "cobertura_registros_pct": d["readiness"]["cobertura_registros_pct"],
        }
        for d in per_obra
    ]
    riesgo_por_obra = [
        {
            "obra_id": d["obra_id"], "obra_nombre": d["obra_nombre"],
            "risk_score": d["risk"].get("risk_score"), "nivel": d["risk"].get("nivel"),
        }
        for d in per_obra
    ]

    risk_scores = [d["risk"]["risk_score"] for d in per_obra if d["risk"].get("risk_score") is not None]
    niveles = [d["risk"].get("nivel") for d in per_obra]
    nivel_global = (
        "critico" if "critico" in niveles else
        "alto" if "alto" in niveles else
        "medio" if "medio" in niveles else
        ("bajo" if per_obra else None)
    )

    top_obras = sorted(per_obra, key=_priority_score, reverse=True)[:MAX_PRIORITY_WORKS]
    top_obras_prioritarias = [
        {
            "obra_id": d["obra_id"], "obra_nombre": d["obra_nombre"],
            "huella_total_tco2e": d["kpis"]["huella_total_tco2e"],
            "estado_ejecutivo": d["estado_ejecutivo"], "risk": d["risk"],
            "readiness_pct": d["readiness"]["cobertura_registros_pct"],
            "cobertura_evidencia_pct": d["kpis"]["cobertura_evidencia_pct"],
            "hallazgos_altos": d["resumen_ejecutivo"]["hallazgos_altos"],
        }
        for d in top_obras
    ]

    return {
        "organizacion_id": organizacion.organizacion_id, "organizacion_nombre": organizacion.nombre,
        "obras_activas": len(per_obra),
        "obras_con_atencion": sum(1 for d in per_obra if d["estado_ejecutivo"]["codigo"] in ("atencion", "critica")),
        "obras_omitidas_error": omitted,
        "kpis": {
            "huella_total_tco2e": _round(huella_total), "alcance_1_tco2e": _round(alcance_1),
            "alcance_2_tco2e": _round(alcance_2), "alcance_3_tco2e": _round(alcance_3),
            "impacto_por_flujo_tco2e": {categoria: _round(value) for categoria, value in impacto_por_flujo.items()},
            "readiness_promedio_pct": _average([d["readiness"]["cobertura_registros_pct"] for d in per_obra]),
            "cobertura_evidencia_promedio_pct": _average([d["kpis"]["cobertura_evidencia_pct"] for d in per_obra]),
            "hallazgos_criticos": sum(d["resumen_ejecutivo"]["hallazgos_altos"] for d in per_obra),
        },
        "riesgo_global": {"score": max(risk_scores) if risk_scores else None, "nivel": nivel_global},
        "emisiones_por_obra": emisiones_por_obra,
        "readiness_por_obra": readiness_por_obra,
        "riesgo_por_obra": riesgo_por_obra,
        "top_obras_prioritarias": top_obras_prioritarias,
        "prioridades": _portfolio_insights(per_obra, huella_total, impacto_por_flujo),
    }
