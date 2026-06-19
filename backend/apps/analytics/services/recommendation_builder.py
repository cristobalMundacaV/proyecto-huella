CATEGORY_STRATEGIES = {
    "Materiales": {
        "foco": "Materiales de alto impacto",
        "problema": "La mayor presion ambiental esta en partidas de carbono incorporado como acero, hormigon, cemento o aridos.",
        "accion": "Comparar proveedores, revisar especificaciones tecnicas y priorizar alternativas con menor factor de emision antes de nuevas compras.",
        "kpi": "kg CO2e por partida material",
    },
    "Transporte": {
        "foco": "Logistica y viajes de obra",
        "problema": "Las emisiones se concentran en traslados, despachos o movimientos asociados a materiales, maquinaria o residuos.",
        "accion": "Consolidar viajes, priorizar proveedores cercanos, revisar rutas y evitar kilometros sin carga util.",
        "kpi": "kg CO2e por viaje o ruta",
    },
    "Maquinaria": {
        "foco": "Uso operacional de maquinaria",
        "problema": "El impacto puede venir de combustible, horas maquina, ralenti, baja mantencion o uso fuera de horario.",
        "accion": "Medir litros y horas por equipo, controlar ralenti, revisar mantencion preventiva y planificar uso por jornada.",
        "kpi": "kg CO2e por equipo o jornada",
    },
    "Energia": {
        "foco": "Consumo energetico y generadores",
        "problema": "El consumo electrico y los generadores pueden generar emisiones evitables si no se controlan por etapa o turno.",
        "accion": "Reducir uso de generadores, ordenar horarios de consumo, separar kWh por etapa y detectar consumos atipicos.",
        "kpi": "kg CO2e por kWh o punto de consumo",
    },
    "Agua": {
        "foco": "Consumo de agua en faena",
        "problema": "El consumo de agua requiere seguimiento operacional para detectar desviaciones tempranas.",
        "accion": "Monitorear litros por etapa, revisar fugas y comparar consumo diario contra avance de obra.",
        "kpi": "litros por etapa o jornada",
    },
    "Residuos": {
        "foco": "Gestion y valorizacion de residuos",
        "problema": "La disposicion final sin segregacion reduce trazabilidad y oportunidades de valorizacion.",
        "accion": "Separar residuos valorizables, registrar retiros y priorizar reciclaje o valorizacion antes de disposicion final.",
        "kpi": "kg CO2e por retiro o tipo de residuo",
    },
    "Procesos externos": {
        "foco": "Procesos tercerizados",
        "problema": "Parte del impacto puede estar fuera de la obra directa, en proveedores, subcontratos o servicios externos.",
        "accion": "Revisar contratos, solicitar respaldos ambientales y priorizar proveedores con datos trazables.",
        "kpi": "kg CO2e por proveedor o servicio",
    },
}

DEFAULT_STRATEGY = {
    "foco": "Gestion ambiental operacional",
    "problema": "La informacion ambiental requiere mejor clasificacion para priorizar con precision.",
    "accion": "Ordenar registros por categoria, obra, etapa y fuente para convertir la huella en decisiones de gestion.",
    "kpi": "kg CO2e por categoria",
}

MODULE_SCOPES = {
    "dashboard": "Resumen ejecutivo para direccion y toma de decisiones.",
    "obra": "Recomendaciones aplicables a una obra especifica.",
    "etapas": "Priorizacion por etapa de obra.",
    "materiales": "Control de materiales, compras y proveedores.",
    "maquinaria": "Control de combustible, horas maquina y equipos.",
    "transporte": "Logistica, rutas, viajes y proveedores cercanos.",
    "energia": "Consumo electrico, generadores y kWh por etapa.",
    "iot": "Lecturas de sensores, telemetria y alertas operacionales.",
    "evidencias": "Trazabilidad documental como respaldo de decisiones.",
}


def number(value, decimals=1):
    try:
        return round(float(value or 0), decimals)
    except (TypeError, ValueError):
        return 0


def percent(part, total):
    total = float(total or 0)
    if total <= 0:
        return 0
    return round((float(part or 0) / total) * 100, 1)


def get_strategy(category):
    return CATEGORY_STRATEGIES.get(category or "", DEFAULT_STRATEGY)


def first_or_empty(items):
    return items[0] if items else {}


def build_focus_card(context):
    total = number(context.get("total_emisiones"), 1)
    category = context.get("categoria_critica") or "Sin datos"
    source = context.get("fuente_critica") or "Sin fuente critica"
    strategy = get_strategy(category)
    top_sources = context.get("top_fuentes_criticas") or []
    top_source = first_or_empty(top_sources)
    impact = number(top_source.get("emisiones_kg_co2e") or 0, 1)

    return {
        "id": "foco_principal",
        "title": "Foco principal de reduccion",
        "priority": "alta" if total > 0 else "media",
        "area": category,
        "source": source,
        "impact_kg_co2e": impact,
        "impact_share_pct": percent(impact, total),
        "diagnosis": f"El foco principal esta en {category}, especialmente en {source}.",
        "why_it_matters": strategy["problema"],
        "recommended_action": strategy["accion"],
        "tracking_kpi": strategy["kpi"],
    }


def build_stage_card(context):
    top_stage = first_or_empty(context.get("top_etapas_criticas") or [])
    total = number(context.get("total_emisiones"), 1)
    stage_name = top_stage.get("etapa_nombre") or "Sin etapa prioritaria detectada"
    stage_impact = number(top_stage.get("emisiones_kg_co2e") or 0, 1)

    if stage_impact <= 0:
        return {
            "id": "etapa_prioritaria",
            "title": "Etapa prioritaria",
            "priority": "media",
            "stage": stage_name,
            "impact_kg_co2e": 0,
            "impact_share_pct": 0,
            "diagnosis": "Aun no hay suficientes emisiones asociadas a etapas para priorizar una fase de obra.",
            "recommended_action": "Vincular registros ambientales a etapas para que la inteligencia detecte donde intervenir primero.",
            "tracking_kpi": "kg CO2e por etapa",
        }

    return {
        "id": "etapa_prioritaria",
        "title": "Etapa prioritaria",
        "priority": "alta",
        "stage": stage_name,
        "impact_kg_co2e": stage_impact,
        "impact_share_pct": percent(stage_impact, total),
        "diagnosis": f"La etapa {stage_name} concentra el mayor impacto ambiental registrado.",
        "recommended_action": "Revisar las fuentes criticas de esta etapa, validar responsables operacionales y definir una accion de reduccion medible antes del siguiente ciclo de control.",
        "tracking_kpi": "kg CO2e por etapa y fuente",
    }


def build_scenario_card(context):
    intensity = context.get("intensidad_carbono")
    coverage = context.get("evidencia_respaldada")
    iot_count = int(context.get("registros_iot") or 0)
    has_iot = iot_count > 0

    return {
        "id": "escenario_recomendado",
        "title": "Escenario recomendado",
        "priority": "estrategica",
        "target_state": "Obra controlada con foco en reduccion operacional, no solo en reporte de huella.",
        "current_state": {
            "intensidad_carbono": intensity,
            "evidencia_respaldada_pct": coverage if isinstance(coverage, (int, float)) else None,
            "iot_activo": has_iot,
        },
        "how_to_reach_it": [
            "Priorizar las fuentes que concentran mayor kg CO2e.",
            "Separar emisiones por obra, etapa y categoria para detectar desviaciones.",
            "Usar sensores para controlar combustible, energia, horas encendido, agua o GPS.",
            "Vincular evidencias a los registros criticos como respaldo, no como fin principal.",
            "Revisar avances semanalmente y cerrar acciones con responsables.",
        ],
        "success_metric": "Menor intensidad kg CO2e/m2 y menor concentracion de emisiones en fuentes criticas recurrentes.",
    }


def build_iot_card(context):
    iot_count = int(context.get("registros_iot") or 0)
    iot_emissions = number(context.get("emisiones_iot_kg_co2e"), 1)
    top_device = first_or_empty(context.get("top_dispositivos_iot") or [])
    device_id = top_device.get("dispositivo_id")

    if iot_count <= 0:
        return {
            "id": "alerta_iot",
            "title": "Lectura operacional IoT",
            "priority": "media",
            "diagnosis": "No hay telemetria reciente en la ventana analizada.",
            "recommended_action": "Activar sensores prioritarios en combustible, energia, horas encendido o agua para pasar de declaracion manual a gestion continua.",
            "metrics": {
                "registros_iot": 0,
                "emisiones_iot_kg_co2e": 0,
            },
        }

    return {
        "id": "alerta_iot",
        "title": "Lectura operacional IoT",
        "priority": "alta" if iot_emissions > 0 else "media",
        "diagnosis": f"La ventana actual contiene {iot_count} lecturas IoT y {iot_emissions} kg CO2e estimados por telemetria.",
        "critical_device": device_id,
        "recommended_action": "Cruzar consumo del dispositivo critico con jornada, equipo, operador y avance de obra para detectar ralenti, uso fuera de horario o bajo rendimiento.",
        "metrics": {
            "registros_iot": iot_count,
            "emisiones_iot_kg_co2e": iot_emissions,
            "emisiones_iot_por_tipo": context.get("emisiones_iot_por_tipo") or {},
        },
    }


def build_evidence_card(context):
    coverage = context.get("evidencia_respaldada")
    coverage_number = coverage if isinstance(coverage, (int, float)) else None
    priority = "alta" if coverage_number is not None and coverage_number < 50 else "media"

    return {
        "id": "trazabilidad_soporte",
        "title": "Trazabilidad como respaldo",
        "priority": priority,
        "diagnosis": "La evidencia documental debe respaldar las decisiones sobre fuentes criticas, no reemplazar la recomendacion operacional.",
        "coverage_pct": coverage_number,
        "recommended_action": "Vincular primero evidencias a las partidas y dispositivos con mayor impacto para sostener decisiones ante mandantes, auditorias o licitaciones.",
        "tracking_kpi": "porcentaje de registros criticos respaldados",
    }


def build_action_plan(context):
    focus = build_focus_card(context)
    stage = build_stage_card(context)
    iot = build_iot_card(context)

    return [
        {
            "id": "accion_1",
            "horizon": "24-48h",
            "title": "Revisar top 5 fuentes de emision",
            "detail": "Validar cantidades, factores, proveedor y responsable operacional de las fuentes con mayor kg CO2e.",
            "area": focus["area"],
        },
        {
            "id": "accion_2",
            "horizon": "esta_semana",
            "title": "Definir accion sobre foco principal",
            "detail": focus["recommended_action"],
            "area": focus["area"],
        },
        {
            "id": "accion_3",
            "horizon": "esta_semana",
            "title": "Intervenir etapa prioritaria",
            "detail": stage["recommended_action"],
            "area": "etapas",
        },
        {
            "id": "accion_4",
            "horizon": "continuo",
            "title": "Usar telemetria para detectar desviaciones",
            "detail": iot["recommended_action"],
            "area": "iot",
        },
    ]


def build_module_recommendations(context):
    focus = build_focus_card(context)
    stage = build_stage_card(context)
    scenario = build_scenario_card(context)
    iot = build_iot_card(context)
    evidence = build_evidence_card(context)

    return {
        "dashboard": [focus, scenario, iot],
        "obra": [focus, stage, scenario],
        "etapas": [stage, focus],
        "materiales": [focus] if focus.get("area") == "Materiales" else [focus],
        "maquinaria": [iot, focus],
        "transporte": [focus],
        "energia": [iot, focus],
        "iot": [iot, focus],
        "evidencias": [evidence, focus],
    }


def build_structured_recommendations(context, scope="dashboard"):
    scope = scope or "dashboard"
    if scope not in MODULE_SCOPES:
        scope = "dashboard"

    focus = build_focus_card(context)
    stage = build_stage_card(context)
    scenario = build_scenario_card(context)
    iot = build_iot_card(context)
    evidence = build_evidence_card(context)
    action_plan = build_action_plan(context)
    modules = build_module_recommendations(context)

    return {
        "version": "2.0",
        "scope": scope,
        "scope_description": MODULE_SCOPES[scope],
        "headline": "No solo medir la huella: priorizar donde actuar y como reducir impacto operacional.",
        "cards": [focus, stage, scenario, iot, evidence],
        "actions": action_plan,
        "modules": modules,
        "active_cards": modules.get(scope, modules["dashboard"]),
        "engine_contract": {
            "ai_ready": True,
            "local_fallback": True,
            "expected_output": "structured_json_plus_executive_text",
        },
    }
