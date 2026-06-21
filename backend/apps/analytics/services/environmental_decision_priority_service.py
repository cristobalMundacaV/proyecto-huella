from django.utils import timezone

from apps.analytics.models import AlertaCumplimientoAmbiental, DocumentoAmbiental
from apps.analytics.services.environmental_kpi_service import build_environmental_kpis, detect_industry_key, normalize
from apps.analytics.services.environmental_recommendation_engine import build_environmental_recommendations
from apps.analytics.services.environmental_scenario_service import build_environmental_scenarios


PRIORITY_ORDER = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
SEVERITY_POINTS = {"critica": 35, "alta": 25, "media": 15, "baja": 5}
CONFIDENCE_POINTS = {"alta": 15, "media": 8, "baja": 3}
EFFORT_POINTS = {"bajo": 10, "medio": 5, "alto": 0}


def build_environmental_decision_priorities(constructora):
    kpis = build_environmental_kpis(constructora)
    recommendations = build_environmental_recommendations(constructora)
    scenarios = build_environmental_scenarios(constructora)
    industry = detect_industry_key(constructora)
    open_alerts = list(
        AlertaCumplimientoAmbiental.objects.filter(
            constructora=constructora,
            estado__in=[
                AlertaCumplimientoAmbiental.Estado.ABIERTA,
                AlertaCumplimientoAmbiental.Estado.EN_REVISION,
            ],
        )
        .select_related("documento", "variable")
        .order_by("-created_at")
    )
    risky_documents = list(
        DocumentoAmbiental.objects.filter(
            constructora=constructora,
            estado_validacion__in=[
                DocumentoAmbiental.EstadoValidacion.PENDIENTE,
                DocumentoAmbiental.EstadoValidacion.OBSERVADO,
                DocumentoAmbiental.EstadoValidacion.RECHAZADO,
            ],
        ).order_by("-created_at")[:6]
    )

    priorities = []
    scenario_by_id = {item.get("id"): item for item in scenarios.get("scenarios", [])}
    scenario_by_area = build_scenario_area_index(scenarios.get("scenarios", []))

    for recommendation in recommendations.get("recommendations", []):
        scenario = scenario_by_id.get(recommendation.get("related_scenario_id")) or best_scenario_for_area(
            scenario_by_area,
            recommendation.get("area"),
            recommendation.get("id"),
        )
        priorities.append(priority_from_recommendation(recommendation, scenario))

    for scenario in scenarios.get("scenarios", []):
        if scenario.get("status") == "available" and (scenario.get("estimated_reduction_pct") or 0) < 5:
            continue
        priorities.append(priority_from_scenario(scenario))

    for alert in open_alerts[:8]:
        scenario = best_scenario_for_area(scenario_by_area, area_from_alert(alert, industry))
        priorities.append(priority_from_alert(alert, scenario, industry))

    for document in risky_documents:
        priorities.append(priority_from_document(document))

    for card in kpis.get("cards", []):
        if card.get("status") == "missing":
            priorities.append(priority_from_missing_kpi(card, industry))

    for source in kpis.get("top_sources", []):
        if (source.get("share_pct") or 0) >= 25:
            priorities.append(priority_from_kpi_pressure("fuente", source))

    for category in kpis.get("top_categories", []):
        if (category.get("share_pct") or 0) >= 35:
            priorities.append(priority_from_kpi_pressure("categoria", category))

    priorities = dedupe_priorities(priorities)
    for item in priorities:
        item["score"] = score_priority(item)
    priorities = sorted(priorities, key=lambda item: (-item["score"], PRIORITY_ORDER.get(item["priority"], 9), item["id"]))[:12]
    for index, item in enumerate(priorities, start=1):
        item["rank"] = index

    return {
        "constructora_id": constructora.constructora_id,
        "preset": constructora.preset,
        "rubro": constructora.rubro,
        "generated_at": timezone.now().isoformat(),
        "summary": build_summary(priorities),
        "priorities": priorities,
        "data_gaps": build_data_gaps(kpis, scenarios, priorities),
    }


def priority_from_recommendation(recommendation, scenario=None):
    priority = recommendation.get("severity", "media")
    pct = impact_pct(scenario)
    if pct and pct >= 20 and priority != "critica":
        priority = "alta"
    status = status_from_context(recommendation.get("confidence"), scenario)
    return priority_item(
        item_id=f"decision-{recommendation['id']}",
        title=recommendation.get("title", "Decision ambiental priorizada"),
        priority=priority,
        area=recommendation.get("area") or "cumplimiento",
        decision_type=decision_type_for_area(recommendation.get("area"), status, scenario),
        why_now=recommendation.get("diagnosis") or "Existe evidencia ambiental que requiere decision tecnica.",
        technical_basis=recommendation.get("technical_recommendation") or recommendation.get("expected_impact") or "",
        expected_impact=expected_impact_from_scenario(scenario, priority),
        confidence=recommendation.get("confidence") or "media",
        effort=effort_for_area(recommendation.get("area"), scenario),
        evidence=recommendation.get("evidence", []),
        recommended_decision=recommendation.get("decision_required") or "Definir decision tecnica con responsable y evidencia.",
        next_step=(recommendation.get("suggested_action") or {}).get("title") or "Validar evidencia base y responsable.",
        related_recommendation_id=recommendation.get("id", ""),
        related_scenario_id=(scenario or {}).get("id", ""),
        status=status,
    )


def priority_from_scenario(scenario):
    status = "requires_data" if scenario.get("status") in {"missing", "partial"} else "ready"
    pct = scenario.get("estimated_reduction_pct")
    priority = priority_from_impact_pct(pct)
    confidence = "alta" if scenario.get("status") == "available" and scenario.get("estimated_reduction_kg_co2e") is not None else "baja"
    if scenario.get("status") == "partial" and pct and pct >= 10:
        priority = "media"
        confidence = "media"
    return priority_item(
        item_id=f"scenario-{scenario['id']}",
        title=scenario.get("title", "Simular reduccion ambiental"),
        priority=priority,
        area=scenario.get("area") or "cumplimiento",
        decision_type="reducir_huella" if scenario.get("estimated_reduction_kg_co2e") is not None else "mejorar_dato",
        why_now=scenario.get("reason") or scenario.get("description") or "El escenario permite evaluar una decision ambiental.",
        technical_basis=scenario.get("description") or "Escenario calculado desde datos operacionales disponibles.",
        expected_impact=expected_impact_from_scenario(scenario, priority),
        confidence=confidence,
        effort=effort_for_area(scenario.get("area"), scenario),
        evidence=scenario.get("evidence", []),
        recommended_decision=scenario.get("decision_hint") or "Evaluar la factibilidad tecnica del escenario.",
        next_step="Validar datos base del escenario." if status == "requires_data" else "Comparar alternativa tecnica y costo operacional.",
        related_recommendation_id=scenario.get("related_recommendation_id", ""),
        related_scenario_id=scenario.get("id", ""),
        status=status,
    )


def priority_from_alert(alert, scenario, industry):
    variable = alert.variable
    priority = "critica" if alert.severidad == "rojo" else "media"
    area = area_from_alert(alert, industry)
    norm = alert.normativa or ((variable.metadata or {}).get("normativa", "") if variable else "")
    evidence = [
        alert.descripcion,
        f"Normativa: {norm or 'no informada'}.",
        f"Estado: {alert.estado}.",
    ]
    return priority_item(
        item_id=f"alert-{alert.id}",
        title=alert.titulo,
        priority=priority,
        area=area,
        decision_type="cumplimiento",
        why_now=f"Alerta {alert.severidad} abierta asociada a {variable.nombre if variable else alert.tipo_alerta}.",
        technical_basis=alert.accion_sugerida or "Revisar evidencia, limite aplicable y causa operacional.",
        expected_impact=expected_impact_from_scenario(scenario, priority, risk_reduction="alta" if alert.severidad == "rojo" else "media"),
        confidence="alta" if variable and variable.limite_aplicable is not None else "media",
        effort=effort_for_area(area, scenario),
        evidence=evidence,
        recommended_decision="Cerrar brecha regulatoria antes de optimizar indicadores de huella.",
        next_step="Asignar responsable tecnico y validar dato contra documento fuente.",
        related_recommendation_id="",
        related_scenario_id=(scenario or {}).get("id", ""),
        status="ready",
        risk_signal=alert.severidad,
    )


def priority_from_document(document):
    priority = "alta" if document.estado_validacion == DocumentoAmbiental.EstadoValidacion.RECHAZADO else "media"
    return priority_item(
        item_id=f"document-{document.id}",
        title=f"Resolver respaldo documental: {document.nombre}",
        priority=priority,
        area="documental",
        decision_type="cerrar_brecha",
        why_now=f"Documento ambiental en estado {document.estado_validacion}.",
        technical_basis="La decision ambiental requiere trazabilidad documental valida para sostener variables, limites y reportes.",
        expected_impact={"kg_co2e": None, "tco2e": None, "pct": None, "risk_reduction": "media"},
        confidence="media" if document.estado_validacion != DocumentoAmbiental.EstadoValidacion.PENDIENTE else "baja",
        effort="bajo",
        evidence=[f"Tipo: {document.tipo_documento}.", f"Resumen: {document.resumen or 'sin resumen'}."],
        recommended_decision="Validar, observar o reemplazar el documento antes de usarlo como evidencia.",
        next_step="Revisar campos extraidos, periodo y vinculo con variables ambientales.",
        related_recommendation_id="",
        related_scenario_id="",
        status="requires_data" if document.estado_validacion == DocumentoAmbiental.EstadoValidacion.PENDIENTE else "ready",
        risk_signal="documento_observado",
    )


def priority_from_missing_kpi(card, industry):
    area = area_from_text(f"{card.get('id')} {card.get('label')}", industry)
    return priority_item(
        item_id=f"kpi-gap-{card['id']}",
        title=f"Completar dato para {card['label']}",
        priority="media" if card.get("priority") == "high" else "baja",
        area=area,
        decision_type="mejorar_dato",
        why_now=card.get("reason") or "Falta un dato clave para calcular KPI ambiental.",
        technical_basis=f"Fuente esperada: {card.get('source') or 'dato operacional'}.",
        expected_impact={"kg_co2e": None, "tco2e": None, "pct": None, "risk_reduction": None},
        confidence="baja",
        effort="bajo",
        evidence=[card.get("reason", ""), f"Unidad esperada: {card.get('unit', '')}."],
        recommended_decision="Definir fuente oficial del dato y periodicidad de carga.",
        next_step="Cargar o vincular documento/variable base.",
        related_recommendation_id="",
        related_scenario_id="",
        status="requires_data",
    )


def priority_from_kpi_pressure(kind, item):
    share = item.get("share_pct") or 0
    area = area_from_text(item.get("label"), "")
    priority = "alta" if (kind == "fuente" and share >= 25) or (kind == "categoria" and share >= 35) else "media"
    return priority_item(
        item_id=f"{kind}-pressure-{slug(item.get('label'))}",
        title=f"Priorizar {item.get('label')}",
        priority=priority,
        area=area,
        decision_type="reducir_huella",
        why_now=f"{item.get('label')} concentra {share:.1f}% de la huella medida.",
        technical_basis=f"Base real: {item.get('value')} {item.get('unit', 'kgCO2e')} en registros de emision.",
        expected_impact={"kg_co2e": None, "tco2e": None, "pct": share, "risk_reduction": None},
        confidence="media",
        effort="medio",
        evidence=[f"Participacion: {share:.1f}%.", f"Valor: {item.get('value')} {item.get('unit', 'kgCO2e')}."],
        recommended_decision="Evaluar alternativa tecnica, proveedor, eficiencia o cambio operacional sobre esta presion.",
        next_step="Revisar registros que explican la presion y seleccionar escenario aplicable.",
        related_recommendation_id="",
        related_scenario_id="",
        status="ready",
    )


def priority_item(
    item_id,
    title,
    priority,
    area,
    decision_type,
    why_now,
    technical_basis,
    expected_impact,
    confidence,
    effort,
    evidence,
    recommended_decision,
    next_step,
    related_recommendation_id,
    related_scenario_id,
    status,
    risk_signal="",
):
    return {
        "id": item_id,
        "rank": None,
        "title": title,
        "priority": priority,
        "area": area or "cumplimiento",
        "decision_type": decision_type,
        "why_now": why_now,
        "technical_basis": technical_basis,
        "expected_impact": expected_impact,
        "confidence": confidence,
        "effort": effort,
        "score": 0,
        "evidence": [item for item in evidence if item],
        "recommended_decision": recommended_decision,
        "next_step": next_step,
        "related_recommendation_id": related_recommendation_id,
        "related_scenario_id": related_scenario_id,
        "status": status,
        "_risk_signal": risk_signal,
    }


def score_priority(item):
    score = SEVERITY_POINTS.get(item.get("priority"), 0)
    pct = (item.get("expected_impact") or {}).get("pct")
    if pct is not None:
        if pct > 20:
            score += 30
        elif pct >= 10:
            score += 22
        elif pct >= 5:
            score += 14
        else:
            score += 6
    risk_signal = item.pop("_risk_signal", "")
    if risk_signal == "rojo" or item.get("decision_type") == "cumplimiento" and item.get("priority") == "critica":
        score += 25
    elif risk_signal == "amarillo":
        score += 15
    elif risk_signal == "documento_observado":
        score += 10
    score += CONFIDENCE_POINTS.get(item.get("confidence"), 0)
    score += EFFORT_POINTS.get(item.get("effort"), 0)
    return min(100, score)


def build_summary(priorities):
    main = priorities[0] if priorities else {}
    return {
        "total_priorities": len(priorities),
        "critical": sum(1 for item in priorities if item["priority"] == "critica"),
        "high": sum(1 for item in priorities if item["priority"] == "alta"),
        "medium": sum(1 for item in priorities if item["priority"] == "media"),
        "low": sum(1 for item in priorities if item["priority"] == "baja"),
        "main_decision": main.get("title", "Sin decision prioritaria identificada"),
        "main_reason": main.get("why_now", "No hay evidencia suficiente para priorizar."),
    }


def build_data_gaps(kpis, scenarios, priorities):
    gaps = []
    gaps.extend(kpis.get("data_gaps", []))
    gaps.extend(scenarios.get("data_gaps", []))
    gaps.extend(item["why_now"] for item in priorities if item.get("status") == "requires_data")
    unique = []
    for gap in gaps:
        if gap and gap not in unique:
            unique.append(gap)
    return unique[:10]


def expected_impact_from_scenario(scenario, priority, risk_reduction=None):
    if not scenario:
        return {"kg_co2e": None, "tco2e": None, "pct": None, "risk_reduction": risk_reduction}
    return {
        "kg_co2e": scenario.get("estimated_reduction_kg_co2e"),
        "tco2e": scenario.get("estimated_reduction_tco2e"),
        "pct": scenario.get("estimated_reduction_pct"),
        "risk_reduction": risk_reduction or ("alta" if priority in {"critica", "alta"} else "media" if priority == "media" else "baja"),
    }


def build_scenario_area_index(scenarios):
    result = {}
    for scenario in scenarios:
        result.setdefault(scenario.get("area") or "cumplimiento", []).append(scenario)
    for area, items in result.items():
        result[area] = sorted(items, key=lambda item: (item.get("status") != "available", -(item.get("estimated_reduction_pct") or 0)))
    return result


def best_scenario_for_area(scenario_by_area, area, recommendation_id=""):
    for scenario in scenario_by_area.get(area or "cumplimiento", []):
        if recommendation_id and scenario.get("related_recommendation_id") == recommendation_id:
            return scenario
    return (scenario_by_area.get(area or "cumplimiento") or [None])[0]


def priority_from_impact_pct(pct):
    if pct is None:
        return "baja"
    if pct > 20:
        return "alta"
    if pct >= 10:
        return "media"
    return "baja"


def impact_pct(scenario):
    return (scenario or {}).get("estimated_reduction_pct")


def status_from_context(confidence, scenario):
    pct = impact_pct(scenario)
    if confidence == "baja" and pct and pct >= 10:
        return "requires_data"
    if scenario and scenario.get("status") in {"missing", "partial"}:
        return "requires_data"
    return "ready"


def decision_type_for_area(area, status, scenario):
    if status == "requires_data":
        return "mejorar_dato"
    if area in {"documental", "cumplimiento", "riles", "aire", "ruido"}:
        return "cumplimiento"
    if scenario:
        return "reducir_huella"
    return "optimizar_operacion"


def effort_for_area(area, scenario):
    if scenario and scenario.get("status") == "missing":
        return "bajo"
    if area in {"documental", "cumplimiento"}:
        return "bajo"
    if area in {"materiales", "energia", "combustible", "transporte"}:
        return "medio"
    return "alto"


def area_from_alert(alert, industry):
    variable = alert.variable
    if not variable:
        return "cumplimiento"
    return area_from_text(f"{variable.variable_id} {variable.nombre} {variable.categoria}", industry)


def area_from_text(text, industry):
    text = normalize(text)
    if any(term in text for term in ["diesel", "combustible"]):
        return "combustible"
    if any(term in text for term in ["resid", "rcd", "respel", "rep", "relave"]):
        return "residuos"
    if any(term in text for term in ["agua", "water"]):
        return "agua"
    if any(term in text for term in ["energia", "kwh", "biomasa", "caldera"]):
        return "energia"
    if any(term in text for term in ["ph", "dbo", "dqo", "sst", "riles"]):
        return "riles"
    if any(term in text for term in ["mp10", "mp2", "so2", "nox", "opacidad", "opacity", "cems"]):
        return "aire"
    if any(term in text for term in ["ruido", "noise"]):
        return "ruido"
    if any(term in text for term in ["km", "ruta", "transporte"]):
        return "transporte"
    if any(term in text for term in ["hormigon", "acero", "cemento", "arido", "asfalto", "material"]):
        return "materiales"
    if "forestal" in industry or any(term in text for term in ["madera", "wood", "produccion"]):
        return "produccion"
    return "cumplimiento"


def dedupe_priorities(priorities):
    seen = set()
    result = []
    for item in priorities:
        key = (item["area"], item["decision_type"], slug(item["title"]))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def slug(value):
    return normalize(value).replace(" ", "-").replace("/", "-")[:80] or "sin-id"
