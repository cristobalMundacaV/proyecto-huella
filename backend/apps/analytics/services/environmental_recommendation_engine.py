from django.utils import timezone

from apps.analytics.models import (
    AlertaCumplimientoAmbiental,
    DocumentoAmbiental,
    RegistroEmision,
    VariableAmbientalExtraida,
)
from apps.analytics.services.environmental_kpi_service import (
    build_environmental_kpis,
    detect_industry_key,
    normalize,
)


SEVERITY_ORDER = {"critica": 0, "alta": 1, "media": 2, "baja": 3}


def build_environmental_recommendations(constructora):
    kpis = build_environmental_kpis(constructora)
    industry = detect_industry_key(constructora)
    variables = list(
        VariableAmbientalExtraida.objects.filter(constructora=constructora)
        .select_related("documento")
        .order_by("-fecha_medicion", "-created_at")
    )
    documents = list(DocumentoAmbiental.objects.filter(constructora=constructora).order_by("-created_at"))
    alerts = list(
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
    registros = list(RegistroEmision.objects.filter(constructora=constructora).order_by("-emisiones_kg_co2e"))

    recommendations = []
    recommendations.extend(recommend_from_alerts(alerts, industry))
    recommendations.extend(recommend_from_missing_kpis(kpis, industry))
    recommendations.extend(recommend_from_top_sources(kpis, registros, industry))
    recommendations.extend(recommend_from_top_categories(kpis, industry))
    recommendations.extend(recommend_from_documents(documents, variables, industry))

    recommendations = dedupe_recommendations(recommendations)
    recommendations = sorted(recommendations, key=lambda item: (SEVERITY_ORDER.get(item["severity"], 9), item["id"]))[:12]
    summary = build_summary(recommendations, kpis)

    return {
        "constructora_id": constructora.constructora_id,
        "preset": constructora.preset,
        "rubro": constructora.rubro,
        "generated_at": timezone.now().isoformat(),
        "summary": summary,
        "recommendations": recommendations,
        "data_gaps": kpis.get("data_gaps", []),
        "debug_context": {
            "industry_key": industry,
            "top_sources": kpis.get("top_sources", [])[:3],
            "top_categories": kpis.get("top_categories", [])[:3],
        },
    }


def build_summary(recommendations, kpis):
    counts = {
        "total_recommendations": len(recommendations),
        "critical": sum(1 for item in recommendations if item["severity"] == "critica"),
        "high": sum(1 for item in recommendations if item["severity"] == "alta"),
        "medium": sum(1 for item in recommendations if item["severity"] == "media"),
        "low": sum(1 for item in recommendations if item["severity"] == "baja"),
        "main_environmental_pressure": "",
        "main_data_gap": "",
    }
    top_category = (kpis.get("top_categories") or [{}])[0]
    top_source = (kpis.get("top_sources") or [{}])[0]
    counts["main_environmental_pressure"] = top_category.get("label") or top_source.get("label") or "Sin presion principal identificada"
    counts["main_data_gap"] = (kpis.get("data_gaps") or ["Sin brecha principal identificada"])[0]
    return counts


def recommend_from_alerts(alerts, industry):
    recommendations = []
    for alert in alerts[:6]:
        variable = alert.variable
        severity = "critica" if alert.severidad == "rojo" else "media"
        if alert.severidad == "rojo" and variable and variable.estado_cumplimiento == "alerta":
            severity = "alta"
        area = area_from_variable(variable, industry)
        value_text = variable_value_text(variable)
        norm = alert.normativa
        if not norm and variable:
            norm = (variable.metadata or {}).get("normativa", "")
        recommendations.append(
            recommendation(
                rec_id=f"alerta-{alert.id}",
                severity=severity,
                area=area,
                title=alert.titulo,
                diagnosis=f"{variable.nombre if variable else 'Una variable ambiental'} presenta estado {alert.tipo_alerta}.",
                evidence=[
                    value_text,
                    f"Normativa asociada: {norm or 'no informada'}.",
                    f"Documento: {alert.documento.nombre if alert.documento else 'sin documento vinculado'}.",
                ],
                probable_cause=probable_cause_for_area(area, industry),
                technical_recommendation=recommendation_for_area(area, industry),
                expected_impact="Reducir riesgo de incumplimiento y mejorar trazabilidad para reporte regulatorio.",
                decision_required="Definir responsable tecnico, validar el dato y decidir si corresponde accion correctiva operacional.",
                confidence="alta" if variable and variable.limite_aplicable is not None else "media",
                source={"type": "alerta", "id": str(alert.id), "label": alert.titulo},
                suggested_action={
                    "title": f"Revisar {variable.nombre if variable else alert.titulo}",
                    "responsible_role": responsible_for_area(area),
                    "required_evidence": evidence_for_area(area),
                    "suggested_due_days": 7 if severity in {"critica", "alta"} else 15,
                },
            )
        )
    return recommendations


def recommend_from_missing_kpis(kpis, industry):
    recommendations = []
    for card in kpis.get("cards", []):
        if card.get("status") != "missing":
            continue
        area = area_from_kpi(card["id"], industry)
        recommendations.append(
            recommendation(
                rec_id=f"brecha-{card['id']}",
                severity="baja" if card.get("priority") != "high" else "media",
                area=area,
                title=f"Completar dato base para {card['label']}",
                diagnosis=f"No es posible calcular {card['label']} porque falta un dato de base.",
                evidence=[card.get("reason", "Dato requerido no disponible."), f"Fuente esperada: {format_source(card.get('source'))}."],
                probable_cause="El proceso de captura aun no registra el denominador o variable operacional necesaria.",
                technical_recommendation=specific_missing_recommendation(card["id"], industry),
                expected_impact="Habilitar intensidad ambiental real y comparabilidad entre periodos o unidades operativas.",
                decision_required="Definir fuente oficial del dato y periodicidad de carga.",
                confidence="baja",
                source={"type": "brecha", "id": card["id"], "label": card["label"]},
                suggested_action={
                    "title": f"Capturar dato para {card['label']}",
                    "responsible_role": responsible_for_area(area),
                    "required_evidence": required_evidence_for_kpi(card["id"]),
                    "suggested_due_days": 20,
                },
            )
        )
    return recommendations[:4]


def recommend_from_top_sources(kpis, registros, industry):
    recommendations = []
    for source in kpis.get("top_sources", []):
        share = source.get("share_pct") or 0
        if share < 25:
            continue
        registros_fuente = [item for item in registros if item.fuente_emision == source["label"]]
        proveedor = next((item.proveedor for item in registros_fuente if item.proveedor), "")
        area = area_from_text(source["label"], industry)
        evidence = [
            f"{source['label']} concentra aproximadamente {share:.1f}% de la huella.",
            f"Emisiones asociadas: {source.get('value')} {source.get('unit', 'kgCO2e')}.",
        ]
        if proveedor:
            evidence.append(f"Proveedor asociado frecuente: {proveedor}.")
        recommendations.append(
            recommendation(
                rec_id=f"fuente-{slug(source['label'])}",
                severity="alta" if share >= 40 else "media",
                area=area,
                title=f"Revisar fuente critica: {source['label']}",
                diagnosis=f"{source['label']} concentra una parte relevante de la huella operacional.",
                evidence=evidence,
                probable_cause=probable_cause_for_area(area, industry),
                technical_recommendation=source_recommendation(source["label"], area, industry, proveedor),
                expected_impact="Reducir la principal presion ambiental medible del periodo.",
                decision_required="Evaluar alternativa tecnica, ajuste operacional o validacion con proveedor antes de ejecutar cambios.",
                confidence="media",
                source={"type": "emision", "id": slug(source["label"]), "label": source["label"]},
                suggested_action={
                    "title": f"Analizar reduccion de {source['label']}",
                    "responsible_role": responsible_for_area(area),
                    "required_evidence": "Registros de consumo, factor de emision y respaldo de proveedor.",
                    "suggested_due_days": 30,
                },
            )
        )
    return recommendations[:3]


def recommend_from_top_categories(kpis, industry):
    recommendations = []
    for category in kpis.get("top_categories", []):
        share = category.get("share_pct") or 0
        if share < 35:
            continue
        area = area_from_text(category["label"], industry)
        recommendations.append(
            recommendation(
                rec_id=f"categoria-{slug(category['label'])}",
                severity="alta" if share >= 50 else "media",
                area=area,
                title=f"Priorizar categoria {category['label']}",
                diagnosis=f"La categoria {category['label']} representa cerca de {share:.1f}% de la huella total.",
                evidence=[f"Emisiones: {category.get('value')} {category.get('unit', 'kgCO2e')}.", f"Participacion estimada: {share:.1f}%."],
                probable_cause=probable_cause_for_area(area, industry),
                technical_recommendation=recommendation_for_area(area, industry),
                expected_impact="Enfocar recursos en la categoria que explica la mayor presion ambiental.",
                decision_required="Definir si se abordara mediante eficiencia operacional, sustitucion tecnica o mejora documental.",
                confidence="media",
                source={"type": "kpi", "id": slug(category["label"]), "label": category["label"]},
                suggested_action={
                    "title": f"Plan tecnico para {category['label']}",
                    "responsible_role": responsible_for_area(area),
                    "required_evidence": "Detalle de registros, factores y documentos asociados a la categoria.",
                    "suggested_due_days": 30,
                },
            )
        )
    return recommendations[:2]


def recommend_from_documents(documents, variables, industry):
    recommendations = []
    risky_docs = [doc for doc in documents if doc.estado_validacion in {"pendiente", "observado", "rechazado"}]
    variable_doc_ids = {var.documento_id for var in variables if var.estado_cumplimiento in {"alerta", "incumple"}}
    risky_docs = sorted(risky_docs, key=lambda doc: (doc.id not in variable_doc_ids, doc.created_at), reverse=False)
    for doc in risky_docs[:3]:
        recommendations.append(
            recommendation(
                rec_id=f"documento-{doc.id}",
                severity="media" if doc.id in variable_doc_ids else "baja",
                area="documental",
                title=f"Validar documento: {doc.nombre}",
                diagnosis=f"El documento {doc.tipo_documento} esta en estado {doc.estado_validacion}.",
                evidence=[f"Documento: {doc.nombre}.", f"Estado: {doc.estado_validacion}.", f"Sirve para respaldar: {doc.resumen or 'variables y cumplimiento ambiental'}."],
                probable_cause="Falta revision documental, respaldo complementario o validacion tecnica del dato.",
                technical_recommendation="Validar fuente, periodo, responsable, dato extraido y vinculo con variables o limites antes de usarlo en reportes.",
                expected_impact="Mejorar trazabilidad y reducir riesgo de observaciones regulatorias.",
                decision_required="Aceptar, observar o rechazar el documento y definir evidencia complementaria si corresponde.",
                confidence="media" if doc.id in variable_doc_ids else "baja",
                source={"type": "documento", "id": str(doc.id), "label": doc.nombre},
                suggested_action={
                    "title": f"Revisar respaldo {doc.tipo_documento}",
                    "responsible_role": "Encargado documental ambiental",
                    "required_evidence": doc.tipo_documento,
                    "suggested_due_days": 10,
                },
            )
        )
    return recommendations


def recommendation(rec_id, severity, area, title, diagnosis, evidence, probable_cause, technical_recommendation, expected_impact, decision_required, confidence, source, suggested_action):
    return {
        "id": rec_id,
        "type": "technical_recommendation",
        "severity": severity,
        "area": area,
        "title": title,
        "diagnosis": diagnosis,
        "evidence": [item for item in evidence if item],
        "probable_cause": probable_cause,
        "technical_recommendation": technical_recommendation,
        "expected_impact": expected_impact,
        "decision_required": decision_required,
        "confidence": confidence,
        "source": source,
        "suggested_action": suggested_action,
        "can_be_converted_to_action": True,
    }


def dedupe_recommendations(recommendations):
    seen = set()
    result = []
    for item in recommendations:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        result.append(item)
    return result


def variable_value_text(variable):
    if not variable:
        return "Variable no disponible."
    limit = f" Limite: {variable.limite_aplicable} {variable.unidad_limite}." if variable.limite_aplicable is not None else ""
    return f"Valor registrado: {variable.valor} {variable.unidad}.{limit}"


def area_from_variable(variable, industry):
    if not variable:
        return "cumplimiento"
    return area_from_text(f"{variable.variable_id} {variable.nombre} {variable.categoria}", industry)


def area_from_kpi(kpi_id, industry):
    return area_from_text(kpi_id, industry)


def area_from_text(text, industry):
    text = normalize(text)
    if any(term in text for term in ["diesel", "combustible"]):
        return "combustible"
    if any(term in text for term in ["rcd", "resid", "rep", "neumatic", "respel", "relave", "aserrin"]):
        return "residuos"
    if any(term in text for term in ["agua", "water"]):
        return "agua"
    if any(term in text for term in ["kwh", "energia", "biomasa", "caldera"]):
        return "energia"
    if any(term in text for term in ["ph", "dbo", "dqo", "sst", "riles"]):
        return "riles"
    if any(term in text for term in ["mp10", "mp2", "so2", "nox", "opacidad", "opacity", "cems"]):
        return "aire"
    if any(term in text for term in ["ruido", "noise"]):
        return "ruido"
    if any(term in text for term in ["km", "ruta", "transporte"]):
        return "transporte"
    if any(term in text for term in ["hormigon", "acero", "cemento", "arido", "asfalto"]):
        return "materiales"
    if "forestal" in industry or any(term in text for term in ["madera", "wood"]):
        return "produccion"
    return "cumplimiento"


def probable_cause_for_area(area, industry):
    causes = {
        "materiales": "Alta intensidad de materiales, factor de emision elevado o falta de alternativa con declaracion ambiental.",
        "combustible": "Consumo elevado, baja eficiencia de equipos, ralentizacion operacional o mantencion insuficiente.",
        "residuos": "Segregacion insuficiente, baja valorizacion o trazabilidad incompleta de destino autorizado.",
        "agua": "Captacion o consumo por sobre patron operacional, baja recirculacion o medicion incompleta.",
        "energia": "Proceso energetico intensivo, baja eficiencia de equipos o programacion operacional suboptima.",
        "riles": "Carga organica o solidos sobre lo esperado, tratamiento insuficiente o muestreo fuera de condicion normal.",
        "aire": "Condicion operacional, combustion, control de polvo o calibracion de monitoreo fuera de rango.",
        "ruido": "Operacion de equipos, horarios, barreras acusticas insuficientes o actividad cercana al receptor.",
        "transporte": "Rutas extensas, bajo rendimiento, viajes vacios o falta de optimizacion logistica.",
        "documental": "Validacion documental incompleta o evidencia sin vinculo operacional.",
    }
    if industry == "mineria" and area == "aire":
        return "Transito de camiones, viento, tronadura o humectacion insuficiente pueden explicar la desviacion."
    return causes.get(area, "Brecha de control operacional o documental sobre una obligacion ambiental.")


def recommendation_for_area(area, industry):
    recommendations = {
        "materiales": "Comparar alternativas tecnicas con menor factor de emision, EPD o ajuste de diseno antes de nuevas compras.",
        "combustible": "Revisar mantencion, consumo especifico, horas de operacion y habitos de uso para reducir diesel.",
        "residuos": "Validar gestor autorizado, aumentar segregacion y cerrar trazabilidad de destino final o valorizacion.",
        "agua": "Revisar balance hidrico, recirculacion, lectura de medidores y respaldo de captacion o consumo.",
        "energia": "Identificar proceso critico, revisar eficiencia de equipos y programacion operacional.",
        "riles": "Revisar tratamiento, carga organica del proceso y frecuencia de muestreo antes del reporte.",
        "aire": "Revisar condicion operacional, calibracion de monitoreo, combustion y controles de abatimiento.",
        "ruido": "Revisar fuente emisora, horario, barreras acusticas y medicion de seguimiento.",
        "transporte": "Optimizar rutas, registrar km reales, revisar mantencion y controlar viajes vacios.",
        "documental": "Completar validacion documental con periodo, fuente, responsable y variable asociada.",
    }
    if industry == "energia" and area == "aire":
        return "Revisar combustion, calibracion CEMS y condicion operacional de la unidad generadora."
    if industry == "forestal_aserradero" and area == "energia":
        return "Revisar proceso de secado, humedad inicial/final y programacion de camaras."
    return recommendations.get(area, "Revisar evidencia, causa operacional y control tecnico antes de decidir acciones.")


def source_recommendation(label, area, industry, proveedor):
    base = recommendation_for_area(area, industry)
    if proveedor:
        return f"{base} Comparar el desempeno tecnico/comercial de {proveedor} contra alternativas solo si los datos respaldan menor huella o menor distancia logistica."
    return base


def specific_missing_recommendation(kpi_id, industry):
    mapping = {
        "huella_m2": "Completar superficie m2 de cada obra para calcular kgCO2e/m2.",
        "emisiones_por_km": "Cargar rutas, GPS o km por viaje para calcular kgCO2e/km.",
        "rendimiento_km_l": "Registrar km recorridos y litros diesel por periodo o vehiculo.",
        "huella_m3_madera": "Cargar volumen m3 de madera producida o lote forestal.",
        "energia_m3": "Vincular consumo energetico kWh con volumen m3 producido.",
        "agua_captada": "Registrar lectura o respaldo de agua captada.",
        "cems_status": "Cargar variables CEMS con limites y continuidad de medicion.",
    }
    return mapping.get(kpi_id, "Capturar el dato base faltante desde documento, variable o registro operacional verificable.")


def responsible_for_area(area):
    return {
        "materiales": "Jefe de compras tecnicas",
        "combustible": "Jefe de operaciones",
        "residuos": "Encargado de residuos",
        "agua": "Encargado ambiental",
        "energia": "Jefe de energia o mantencion",
        "riles": "Encargado de planta de tratamiento",
        "aire": "Encargado de monitoreo ambiental",
        "ruido": "Prevencion y medio ambiente",
        "transporte": "Jefe de logistica",
        "documental": "Encargado documental ambiental",
    }.get(area, "Encargado ambiental")


def evidence_for_area(area):
    return {
        "materiales": "Factura, guia de despacho, EPD o ficha tecnica.",
        "combustible": "Factura combustible, bitacora de equipo o telemetria.",
        "residuos": "Certificado de gestor, manifiesto, ticket de pesaje o SINADER/SIDREP.",
        "agua": "Lectura de medidor, balance hidrico o factura.",
        "energia": "Factura electrica, bitacora de equipo o medicion operacional.",
        "riles": "Informe de laboratorio y cadena de custodia.",
        "aire": "Reporte de monitoreo, CEMS o calibracion.",
        "ruido": "Informe de medicion acustica.",
        "transporte": "GPS, hoja de ruta, km recorridos y consumo.",
    }.get(area, "Documento ambiental validado.")


def required_evidence_for_kpi(kpi_id):
    if "km" in kpi_id or "rendimiento" in kpi_id:
        return "Rutas, GPS o registro de km por viaje."
    if "m2" in kpi_id:
        return "Ficha de obra con superficie m2."
    if "m3" in kpi_id or "madera" in kpi_id:
        return "Registro de produccion o lote forestal en m3."
    if "agua" in kpi_id:
        return "Lectura de medidor, balance hidrico o factura."
    return "Documento o variable operacional validada."


def format_source(source):
    return str(source or "calculado").replace("_", " ")


def slug(value):
    return normalize(value).replace(" ", "-").replace("/", "-")[:80] or "sin-id"
