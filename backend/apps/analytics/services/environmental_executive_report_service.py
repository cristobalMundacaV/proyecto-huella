from django.utils import timezone

from apps.analytics.models import AlertaCumplimientoAmbiental, DocumentoAmbiental, EvidenciaObra
from apps.analytics.models_acciones import AccionAmbiental
from apps.analytics.services.environmental_decision_priority_service import build_environmental_decision_priorities
from apps.analytics.services.environmental_kpi_service import build_environmental_kpis
from apps.analytics.services.environmental_recommendation_engine import build_environmental_recommendations
from apps.analytics.services.environmental_scenario_service import build_environmental_scenarios
from apps.analytics.views_acciones import serialize_action

ACTIVE_ACTION_STATUSES = {"pendiente", "en_progreso", "validacion"}


def build_environmental_executive_report(organizacion):
    warnings = []
    kpis = safe_call("KPIs ambientales", lambda: build_environmental_kpis(organizacion), {}, warnings)
    recommendations = safe_call("recomendaciones tecnicas", lambda: build_environmental_recommendations(organizacion), {"recommendations": []}, warnings)
    scenarios = safe_call("escenarios de impacto", lambda: build_environmental_scenarios(organizacion), {"scenarios": []}, warnings)
    decisions = safe_call("decisiones priorizadas", lambda: build_environmental_decision_priorities(organizacion), {"priorities": []}, warnings)

    actions = list(
        AccionAmbiental.objects.filter(organizacion=organizacion)
        .select_related("obra", "lote_forestal", "registro_emision", "evidencia")
        .order_by("-updated_at", "-id")
    )
    documents = DocumentoAmbiental.objects.filter(organizacion=organizacion)
    evidence_total = EvidenciaObra.objects.filter(organizacion=organizacion).count()
    open_alerts = AlertaCumplimientoAmbiental.objects.filter(
        organizacion=organizacion,
        estado__in=[AlertaCumplimientoAmbiental.Estado.ABIERTA, AlertaCumplimientoAmbiental.Estado.EN_REVISION],
    )

    kpi_summary = kpis.get("summary", {}) if isinstance(kpis, dict) else {}
    top_recommendations = sorted(recommendations.get("recommendations", []), key=lambda item: severity_order(item.get("severity")))[:5]
    top_scenarios = sorted(scenarios.get("scenarios", []), key=scenario_order)[:5]
    top_priorities = sorted(decisions.get("priorities", []), key=lambda item: (item.get("rank") or 999, -(item.get("score") or 0)))[:5]
    action_summary = build_action_summary(actions)
    traceability = build_traceability_summary(documents, evidence_total, open_alerts)
    readiness = build_readiness(kpi_summary, top_recommendations, top_scenarios, top_priorities, action_summary, traceability)
    executive_summary = build_summary(organizacion, kpi_summary, top_priorities, action_summary, traceability, readiness)

    return {
        "organizacion_id": organizacion.organizacion_id,
        "empresa": organizacion.nombre,
        "preset": organizacion.preset,
        "rubro": organizacion.rubro,
        "generated_at": timezone.now().isoformat(),
        "title": "Informe ejecutivo ambiental",
        "period": "Periodo disponible",
        "executive_summary": executive_summary,
        "baseline": {
            "huella_total_kg_co2e": as_number(kpi_summary.get("huella_total_kg_co2e")),
            "huella_total_tco2e": as_number(kpi_summary.get("huella_total_tco2e")),
            "total_registros": as_number(kpi_summary.get("total_registros")),
            "total_documentos": as_number(kpi_summary.get("total_documentos")),
            "alertas_abiertas": as_number(kpi_summary.get("alertas_abiertas")),
        },
        "critical_findings": [normalize_recommendation(item) for item in top_recommendations],
        "impact_scenarios": [normalize_scenario(item) for item in top_scenarios],
        "decision_agenda": [normalize_priority(item) for item in top_priorities],
        "action_summary": action_summary,
        "document_traceability": traceability,
        "readiness": readiness,
        "management_plan": build_management_plan(top_priorities, action_summary, traceability),
        "data_gaps": collect_gaps(kpis, scenarios, decisions, action_summary, traceability),
        "warnings": warnings,
    }


def safe_call(label, builder, default, warnings):
    try:
        return builder()
    except Exception as exc:
        warnings.append(f"No se pudo cargar {label}: {exc}")
        return default


def severity_order(value):
    return {"critica": 0, "alta": 1, "media": 2, "baja": 3}.get(value, 9)


def scenario_order(item):
    status_order = {"available": 0, "partial": 1, "missing": 2}
    return (status_order.get(item.get("status"), 9), -(item.get("estimated_reduction_kg_co2e") or 0), -(item.get("estimated_reduction_pct") or 0))


def build_action_summary(actions):
    today = timezone.localdate()
    total = len(actions)
    completed = [item for item in actions if item.status == AccionAmbiental.Estado.COMPLETADA]
    active = [item for item in actions if item.status in ACTIVE_ACTION_STATUSES]
    overdue = [item for item in active if item.due_date and item.due_date < today]
    with_support = [item for item in actions if action_has_support(item)]
    closed_with_warning = [item for item in completed if (item.metadata or {}).get("closure", {}).get("close_with_warning")]
    return {
        "total": total,
        "active": len(active),
        "completed": len(completed),
        "overdue": len(overdue),
        "with_evidence": len(with_support),
        "without_evidence": max(total - len(with_support), 0),
        "closed_with_warning": len(closed_with_warning),
        "closure_pct": round((len(completed) / total) * 100, 1) if total else 0,
        "traceability_pct": round((len(with_support) / total) * 100, 1) if total else 0,
        "latest_actions": [serialize_action(item) for item in actions[:6]],
        "actions_requiring_evidence": [serialize_action(item) for item in active if not action_has_support(item)][:6],
    }


def action_has_support(action):
    metadata = action.metadata if isinstance(action.metadata, dict) else {}
    return bool(action.evidencia_id or metadata.get("linked_evidence") or metadata.get("linked_documents") or metadata.get("closure_notes") or metadata.get("closure_references") or metadata.get("evidence_summary"))


def build_traceability_summary(documents, evidence_total, open_alerts):
    total_documents = documents.count()
    validated = documents.filter(estado_validacion=DocumentoAmbiental.EstadoValidacion.VALIDO).count()
    pending = documents.filter(estado_validacion=DocumentoAmbiental.EstadoValidacion.PENDIENTE).count()
    observed = documents.filter(estado_validacion__in=[DocumentoAmbiental.EstadoValidacion.OBSERVADO, DocumentoAmbiental.EstadoValidacion.RECHAZADO]).count()
    red_alerts = open_alerts.filter(severidad="rojo").count()
    yellow_alerts = open_alerts.filter(severidad="amarillo").count()
    return {
        "documents_total": total_documents,
        "documents_validated": validated,
        "documents_pending": pending,
        "documents_observed": observed,
        "evidence_total": evidence_total,
        "open_alerts": open_alerts.count(),
        "red_alerts": red_alerts,
        "yellow_alerts": yellow_alerts,
        "validation_pct": round((validated / total_documents) * 100, 1) if total_documents else 0,
    }


def build_readiness(kpi_summary, recommendations, scenarios, priorities, action_summary, traceability):
    checks = [
        check("Datos ambientales cargados", (kpi_summary.get("total_registros") or 0) > 0, f"{kpi_summary.get('total_registros') or 0} registros disponibles."),
        check("Huella calculada", (kpi_summary.get("huella_total_kg_co2e") or 0) > 0, f"Huella total: {fmt(kpi_summary.get('huella_total_tco2e'))} tCO2e."),
        check("Recomendaciones tecnicas", len(recommendations) > 0, f"{len(recommendations)} hallazgos principales."),
        check("Escenarios disponibles", any(item.get("status") == "available" for item in scenarios), f"{len(scenarios)} escenarios revisados."),
        check("Decisiones priorizadas", len(priorities) > 0, f"{len(priorities)} decisiones ejecutivas."),
        check("Acciones ambientales", action_summary["total"] > 0, f"{action_summary['total']} acciones registradas."),
        check("Evidencia de gestion", action_summary["with_evidence"] > 0 or traceability["evidence_total"] > 0, f"{action_summary['with_evidence']} acciones con evidencia y {traceability['evidence_total']} evidencias de obra."),
        check("Sin alertas rojas abiertas", traceability["red_alerts"] == 0, f"{traceability['red_alerts']} alertas rojas abiertas."),
    ]
    passed = sum(1 for item in checks if item["passed"])
    score = round((passed / len(checks)) * 100) if checks else 0
    status = "Listo para presentar" if score >= 85 else "Presentable con observaciones" if score >= 65 else "Requiere completar gestion"
    return {"score": score, "status": status, "passed": passed, "total": len(checks), "checks": checks}


def check(label, passed, detail):
    return {"label": label, "passed": bool(passed), "detail": detail}


def build_summary(organizacion, kpi_summary, priorities, action_summary, traceability, readiness):
    empresa = organizacion.nombre or organizacion.organizacion_id
    top_priority = priorities[0] if priorities else None
    headline = f"{empresa} presenta un estado ambiental {readiness['status'].lower()} con {readiness['score']}% de preparacion ejecutiva."
    footprint = kpi_summary.get("huella_total_tco2e")
    main_message = f"La huella total disponible es {fmt(footprint)} tCO2e y ya existen prioridades tecnicas para decidir donde actuar primero." if footprint else "La empresa debe completar datos base para consolidar huella, impacto esperado y trazabilidad ejecutiva."
    next_step = top_priority.get("next_step") if top_priority else "Cargar registros, documentos y evidencias faltantes."
    return {
        "headline": headline,
        "main_message": main_message,
        "main_decision": top_priority.get("title") if top_priority else "Completar base de datos y evidencias antes del reporte final.",
        "next_step": next_step,
        "management_message": f"Hay {action_summary['total']} acciones ambientales, {action_summary['completed']} cerradas y {action_summary['with_evidence']} con evidencia vinculada.",
        "risk_message": f"Alertas abiertas: {traceability['open_alerts']} ({traceability['red_alerts']} rojas, {traceability['yellow_alerts']} amarillas).",
    }


def normalize_recommendation(item):
    return {"id": item.get("id"), "severity": item.get("severity"), "area": item.get("area"), "title": item.get("title"), "diagnosis": item.get("diagnosis"), "evidence": item.get("evidence", [])[:3], "technical_recommendation": item.get("technical_recommendation"), "decision_required": item.get("decision_required"), "confidence": item.get("confidence")}


def normalize_scenario(item):
    return {"id": item.get("id"), "title": item.get("title"), "type": item.get("type"), "area": item.get("area"), "status": item.get("status"), "estimated_reduction_kg_co2e": as_number(item.get("estimated_reduction_kg_co2e")), "estimated_reduction_tco2e": as_number(item.get("estimated_reduction_tco2e")), "estimated_reduction_pct": as_number(item.get("estimated_reduction_pct")), "decision_hint": item.get("decision_hint"), "reason": item.get("reason")}


def normalize_priority(item):
    return {"id": item.get("id"), "rank": item.get("rank"), "title": item.get("title"), "priority": item.get("priority"), "area": item.get("area"), "score": item.get("score"), "why_now": item.get("why_now"), "expected_impact": item.get("expected_impact"), "confidence": item.get("confidence"), "effort": item.get("effort"), "recommended_decision": item.get("recommended_decision"), "next_step": item.get("next_step"), "status": item.get("status"), "action_created": item.get("action_created", False), "action_id": item.get("action_id")}


def build_management_plan(priorities, action_summary, traceability):
    plan = [{"title": item.get("title"), "priority": item.get("priority"), "step": item.get("next_step") or item.get("recommended_decision"), "status": "accion_creada" if item.get("action_created") else item.get("status", "ready")} for item in priorities[:4]]
    if action_summary["actions_requiring_evidence"]:
        plan.append({"title": "Cerrar evidencia de acciones abiertas", "priority": "alta" if action_summary["overdue"] else "media", "step": "Vincular documento, evidencia o nota de cierre antes del reporte final.", "status": "requires_data"})
    if traceability["red_alerts"]:
        plan.append({"title": "Resolver alertas rojas antes de presentar", "priority": "critica", "step": "Validar variable, documento fuente y accion correctiva asociada.", "status": "ready"})
    return plan[:6]


def collect_gaps(kpis, scenarios, decisions, action_summary, traceability):
    gaps = []
    for source in [kpis, scenarios, decisions]:
        if isinstance(source, dict):
            for item in source.get("data_gaps", []):
                gaps.append(item if isinstance(item, dict) else {"label": str(item), "source": "motor ambiental"})
    if action_summary["without_evidence"]:
        gaps.append({"label": f"{action_summary['without_evidence']} acciones sin evidencia vinculada.", "source": "acciones"})
    if traceability["documents_pending"]:
        gaps.append({"label": f"{traceability['documents_pending']} documentos pendientes de validacion.", "source": "documentos"})
    return gaps[:10]


def as_number(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt(value):
    number = as_number(value)
    if number is None:
        return "sin dato"
    return f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
