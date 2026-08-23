from django.urls import path

from .views import (
    ai_advisor,
    auth_bootstrap,
    auth_csrf_token,
    auth_login,
    auth_logout,
    auth_me,
    calcular_distancia_ruta,
    organizacion_configuracion,
    organizacion_dashboard,
    organizacion_estado,
    organizacion_evidencias,
    organizacion_evidencia_extraer,
    organizacion_obras,
    organizacion_registro_aplicar_factor,
    organizacion_registros_emision,
    organizacion_reportes,
    organizacion_usuarios,
    organizacion_usuario_detail,
    organizaciones,
    dashboard_data,
    factores_catalogo,
    factores_emision,
    factores_emision_detail,
    materiales_construccion,
    obra_detail,
    obra_evidencias,
    obra_registros_emision,
    obra_transportes,
    obras,
    sistema_estado,
    verificar_obra,
)
from .views_acciones import (
    organizacion_accion_ambiental_detail,
    organizacion_acciones_ambientales,
    organizacion_acciones_ambientales_resumen,
)
from .views_organizaciones import organizacion_detail_safe
from .views_emisiones import organizacion_emisiones
from .views_etapas import organizacion_etapas
from .views_environmental_compliance import (
    alerta_cumplimiento_detail,
    alertas_cumplimiento,
    cumplimiento_ambiental_resumen,
    documento_ambiental_detail,
    documentos_ambientales,
    limite_ambiental_detail,
    limites_ambientales,
    variable_ambiental_detail,
    variables_ambientales,
)
from .views_environmental_action_closure import (
    environmental_action_attach_evidence,
    environmental_action_close,
    environmental_action_closure_status,
)
from .views_environmental_decision_actions import (
    environmental_decision_action_preview,
    environmental_decision_create_action,
)
from .views_environmental_decisions import environmental_decision_priorities
from .views_environmental_executive_report import environmental_executive_report
from .views_environmental_ingestion import environmental_ingestion_readiness
from .views_environmental_kpis import environmental_kpis
from .views_environmental_recommendations import environmental_recommendations
from .views_environmental_scenarios import environmental_scenarios
from .views_forestal import (
    organizacion_lote_forestal_detail,
    organizacion_lote_forestal_transportes,
    organizacion_lotes_forestales,
    organizacion_lotes_forestales_resumen,
)
from .views_importaciones import (
    importacion_completa_confirm,
    importacion_completa_preview,
    importacion_confirm,
    importacion_generica_preview,
    importacion_preview,
    plantilla_importacion_construccion,
    plantilla_importacion_generica,
)
from .views_recommendations import recommendation_context, recomendaciones
from .views_environmental_engine import (
    environmental_engine_results,
    environmental_lca_results,
)
from .views_problematicas import (
    problematica_action_implement,
    problematica_actions,
    problematica_detail,
    problematica_action_select,
    problematica_action_start,
    problematica_cycles,
    problematica_escalate,
    problematica_evaluate,
    problematica_history,
    problematica_indicators,
    problematica_measure_engine,
    problematica_measurements,
    problematica_reevaluate,
    problematica_scope,
    problematica_snapshot_base,
    problematica_transition,
    problematicas,
)
from .views_environmental_context import (
    material_lifecycle_view,
    organization_context_view,
    organization_kpis_view,
    problem_actions_view,
    problem_context_view,
    problem_evidence_view,
    problem_history_view,
    problem_normative_view,
    problem_recommendations_view,
    problem_sources_view,
)
from .views_environmental_escalation import (
    problem_dossier_view,
    problem_escalation_view,
)
from .views_foundation import (
    capacidad_organizacion_detail,
    capacidades_disponibles,
    capacidades_organizacion,
    diagnostico_ambiental,
    preparacion_ambiental,
    proceso_operacional_detail,
    procesos_operacionales,
    unidad_operacional_detail,
    unidades_operacionales,
    aplicabilidad_capacidad_obra,
)
from .views_construction_v1 import (
    environmental_work,
    work_context_view,
    work_indicators,
    work_materials,
    work_timeline,
)
from .views_activity_core import (
    actividad_operacional_detail,
    actividades_operacionales,
    fuente_datos_detail,
    fuentes_datos,
    observacion_detail,
    observaciones_actividad,
)
from .views_ingestion_v2 import (
    ingesta_analizar,
    ingesta_confirmar,
    ingesta_detail,
    ingesta_mapeo,
    ingesta_preview,
    ingestas,
    plantillas_mapeo,
)
from .views_assets import (
    activo_detail,
    activos,
    condiciones_activo,
    mantenimiento_detail,
    mantenimientos_activo,
)
from .views_sensors_v2 import (
    calibraciones,
    instalaciones,
    lecturas_sensor_v2,
    sensor_detail,
    sensores,
)
from .views_calculation_v2 import (
    calcular_actividad,
    calculo_compare,
    calculo_detail,
    calculos_actividad,
    calculo_recalculate,
    calculo_snapshot,
    elegibilidad_actividad,
    factores_ambientales,
    impactos_ambientales,
    metodologia_detail,
    metodologia_transition,
    metodologia_variables,
    metodologias,
)
from .views_quality_v2 import (
    calidad_observaciones,
    comparacion_indicador,
    discrepancia_detail,
    discrepancias,
    indicadores,
    lineas_base,
    politicas_fuente,
    resumen_ambiental_v2,
    serie_indicador,
)
from .views_copilot_v2 import (
    agent_problem_proposals,
    agent_proposal_feedback,
    agent_reevaluation_draft,
    confirm_copilot_command,
    context_asset,
    context_asset_maintenance,
    context_evidence,
    context_indicator_history,
    context_organization_memory,
    context_problem,
    context_sensor_health,
)
from .views_professional_v2 import (
    auditoria,
    expediente_close,
    expediente_detail,
    expediente_reopen,
    expedientes,
    informe_detail,
    informe_pdf,
    informe_validate,
    informes,
    revision_decision,
    revision_hallazgos,
    revision_profesional_detail,
    revisiones_profesionales,
)
from .views_knowledge_v1 import (
    knowledge_aggregate,
    knowledge_case_detail,
    knowledge_cases,
)
from .views_transport_v2 import journey_detail, journey_indicators, journeys, routes
from .views_materials_v2 import (
    balance as material_balance_v2,
    event_detail,
    events as material_events,
    lineage as material_lineage_v2,
    lots as material_lots,
    material_detail,
    material_indicators,
    materials as operational_materials,
)
from .views_sector_flows_v1 import (
    environmental_points,
    sector_indicators,
    sector_record_detail,
    sector_records,
)

urlpatterns = [
    path(
        "organizaciones/<str:organizacion_id>/puntos-ambientales/", environmental_points
    ),
    path("organizaciones/<str:organizacion_id>/flujos-ambientales/", sector_records),
    path(
        "organizaciones/<str:organizacion_id>/flujos-ambientales/indicadores/",
        sector_indicators,
    ),
    path(
        "organizaciones/<str:organizacion_id>/flujos-ambientales/<int:record_id>/",
        sector_record_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/materiales-operacionales/",
        operational_materials,
    ),
    path(
        "organizaciones/<str:organizacion_id>/materiales-operacionales/indicadores/",
        material_indicators,
    ),
    path(
        "organizaciones/<str:organizacion_id>/materiales-operacionales/<int:material_id>/",
        material_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/materiales-operacionales/<int:material_id>/balance/",
        material_balance_v2,
    ),
    path(
        "organizaciones/<str:organizacion_id>/materiales-operacionales/<int:material_id>/lineage/",
        material_lineage_v2,
    ),
    path("organizaciones/<str:organizacion_id>/lotes-materiales/", material_lots),
    path("organizaciones/<str:organizacion_id>/eventos-materiales/", material_events),
    path(
        "organizaciones/<str:organizacion_id>/eventos-materiales/<int:event_id>/",
        event_detail,
    ),
    path("organizaciones/<str:organizacion_id>/rutas-operacionales/", routes),
    path("organizaciones/<str:organizacion_id>/viajes-operacionales/", journeys),
    path(
        "organizaciones/<str:organizacion_id>/viajes-operacionales/indicadores/",
        journey_indicators,
    ),
    path(
        "organizaciones/<str:organizacion_id>/viajes-operacionales/<int:journey_id>/",
        journey_detail,
    ),
    path("organizaciones/<str:organizacion_id>/conocimiento/casos/", knowledge_cases),
    path(
        "organizaciones/<str:organizacion_id>/conocimiento/casos/<int:case_id>/",
        knowledge_case_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/conocimiento/agregado/",
        knowledge_aggregate,
    ),
    path(
        "organizaciones/<str:organizacion_id>/revisiones-profesionales/",
        revisiones_profesionales,
    ),
    path(
        "organizaciones/<str:organizacion_id>/revisiones-profesionales/<int:revision_id>/",
        revision_profesional_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/revisiones-profesionales/<int:revision_id>/hallazgos/",
        revision_hallazgos,
    ),
    path(
        "organizaciones/<str:organizacion_id>/revisiones-profesionales/<int:revision_id>/decision/",
        revision_decision,
    ),
    path("organizaciones/<str:organizacion_id>/auditoria/", auditoria),
    path("organizaciones/<str:organizacion_id>/expedientes/", expedientes),
    path(
        "organizaciones/<str:organizacion_id>/expedientes/<int:expediente_id>/",
        expediente_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/expedientes/<int:expediente_id>/cerrar/",
        expediente_close,
    ),
    path(
        "organizaciones/<str:organizacion_id>/expedientes/<int:expediente_id>/reabrir/",
        expediente_reopen,
    ),
    path("organizaciones/<str:organizacion_id>/informes/", informes),
    path(
        "organizaciones/<str:organizacion_id>/informes/<int:informe_id>/",
        informe_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/informes/<int:informe_id>/pdf/",
        informe_pdf,
    ),
    path(
        "organizaciones/<str:organizacion_id>/informes/<int:informe_id>/validar/",
        informe_validate,
    ),
    path("context/problems/<int:problem_id>/", context_problem),
    path("context/assets/<int:asset_id>/", context_asset),
    path("context/assets/<int:asset_id>/maintenance/", context_asset_maintenance),
    path("context/sensors/<int:sensor_id>/health/", context_sensor_health),
    path("context/indicators/<int:indicator_id>/history/", context_indicator_history),
    path("context/evidence/<int:evidence_id>/", context_evidence),
    path(
        "context/organizations/<str:organization_id>/memory/",
        context_organization_memory,
    ),
    path("agent/problems/<int:problem_id>/proposals/", agent_problem_proposals),
    path(
        "agent/problems/<int:problem_id>/proposals/<int:proposal_id>/feedback/",
        agent_proposal_feedback,
    ),
    path(
        "agent/problems/<int:problem_id>/reevaluation-draft/", agent_reevaluation_draft
    ),
    path("agent/commands/<int:command_id>/confirm/", confirm_copilot_command),
    path("capacidades-ambientales/", capacidades_disponibles),
    path("auth/me/", auth_me),
    path("auth/csrf-token/", auth_csrf_token),
    path("auth/login/", auth_login),
    path("auth/logout/", auth_logout),
    path("auth/bootstrap/", auth_bootstrap),
    path("dashboard/", dashboard_data),
    path("organizaciones/", organizaciones),
    path("organizaciones/<str:organizacion_id>/", organizacion_detail_safe),
    path(
        "organizaciones/<str:organizacion_id>/diagnostico-ambiental/",
        diagnostico_ambiental,
    ),
    path(
        "organizaciones/<str:organizacion_id>/capacidades-ambientales/",
        capacidades_organizacion,
    ),
    path(
        "organizaciones/<str:organizacion_id>/capacidades-ambientales/<int:capacidad_id>/",
        capacidad_organizacion_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/unidades-operacionales/",
        unidades_operacionales,
    ),
    path(
        "organizaciones/<str:organizacion_id>/unidades-operacionales/<int:unidad_id>/",
        unidad_operacional_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/procesos-operacionales/",
        procesos_operacionales,
    ),
    path(
        "organizaciones/<str:organizacion_id>/procesos-operacionales/<int:proceso_id>/",
        proceso_operacional_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/preparacion-ambiental/",
        preparacion_ambiental,
    ),
    path(
        "organizaciones/<str:organizacion_id>/obras/<int:obra_id>/ambiental/",
        environmental_work,
    ),
    path(
        "organizaciones/<str:organizacion_id>/obras/<int:obra_id>/timeline/",
        work_timeline,
    ),
    path(
        "organizaciones/<str:organizacion_id>/obras/<int:obra_id>/indicadores/",
        work_indicators,
    ),
    path(
        "organizaciones/<str:organizacion_id>/obras/<int:obra_id>/materiales/",
        work_materials,
    ),
    path(
        "organizaciones/<str:organizacion_id>/obras/<int:obra_id>/contexto/",
        work_context_view,
    ),
    path("organizaciones/<str:organizacion_id>/fuentes-datos/", fuentes_datos),
    path(
        "organizaciones/<str:organizacion_id>/fuentes-datos/<int:fuente_id>/",
        fuente_datos_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/actividades-operacionales/",
        actividades_operacionales,
    ),
    path(
        "organizaciones/<str:organizacion_id>/actividades-operacionales/<int:actividad_id>/",
        actividad_operacional_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/actividades-operacionales/<int:actividad_id>/observaciones/",
        observaciones_actividad,
    ),
    path(
        "organizaciones/<str:organizacion_id>/observaciones/<int:observacion_id>/",
        observacion_detail,
    ),
    path("organizaciones/<str:organizacion_id>/ingestas/", ingestas),
    path(
        "organizaciones/<str:organizacion_id>/ingestas/<int:ingesta_id>/",
        ingesta_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/ingestas/<int:ingesta_id>/analizar/",
        ingesta_analizar,
    ),
    path(
        "organizaciones/<str:organizacion_id>/ingestas/<int:ingesta_id>/mapeo/",
        ingesta_mapeo,
    ),
    path(
        "organizaciones/<str:organizacion_id>/ingestas/<int:ingesta_id>/preview/",
        ingesta_preview,
    ),
    path(
        "organizaciones/<str:organizacion_id>/ingestas/<int:ingesta_id>/confirmar/",
        ingesta_confirmar,
    ),
    path("organizaciones/<str:organizacion_id>/plantillas-mapeo/", plantillas_mapeo),
    path("organizaciones/<str:organizacion_id>/activos/", activos),
    path(
        "organizaciones/<str:organizacion_id>/activos/<int:activo_id>/", activo_detail
    ),
    path(
        "organizaciones/<str:organizacion_id>/activos/<int:activo_id>/mantenimientos/",
        mantenimientos_activo,
    ),
    path(
        "organizaciones/<str:organizacion_id>/mantenimientos/<int:mantenimiento_id>/",
        mantenimiento_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/activos/<int:activo_id>/condiciones/",
        condiciones_activo,
    ),
    path("organizaciones/<str:organizacion_id>/sensores/", sensores),
    path(
        "organizaciones/<str:organizacion_id>/sensores/<int:sensor_id>/", sensor_detail
    ),
    path(
        "organizaciones/<str:organizacion_id>/sensores/<int:sensor_id>/instalaciones/",
        instalaciones,
    ),
    path(
        "organizaciones/<str:organizacion_id>/sensores/<int:sensor_id>/calibraciones/",
        calibraciones,
    ),
    path(
        "organizaciones/<str:organizacion_id>/sensores/<int:sensor_id>/lecturas/",
        lecturas_sensor_v2,
    ),
    path("organizaciones/<str:organizacion_id>/metodologias/", metodologias),
    path(
        "organizaciones/<str:organizacion_id>/metodologias/<int:metodologia_id>/",
        metodologia_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/metodologias/<int:metodologia_id>/versiones/<int:version_id>/transicion/",
        metodologia_transition,
    ),
    path(
        "organizaciones/<str:organizacion_id>/metodologias/<int:metodologia_id>/versiones/<int:version_id>/variables/",
        metodologia_variables,
    ),
    path(
        "organizaciones/<str:organizacion_id>/metodologias/<int:metodologia_id>/versiones/<int:version_id>/variables/<int:variable_id>/",
        metodologia_variables,
    ),
    path(
        "organizaciones/<str:organizacion_id>/factores-ambientales/",
        factores_ambientales,
    ),
    path(
        "organizaciones/<str:organizacion_id>/actividades-operacionales/<int:actividad_id>/elegibilidad/",
        elegibilidad_actividad,
    ),
    path(
        "organizaciones/<str:organizacion_id>/actividades-operacionales/<int:actividad_id>/calcular/",
        calcular_actividad,
    ),
    path(
        "organizaciones/<str:organizacion_id>/actividades-operacionales/<int:actividad_id>/calculos/",
        calculos_actividad,
    ),
    path(
        "organizaciones/<str:organizacion_id>/calculos/<int:calculo_id>/",
        calculo_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/calculos/<int:calculo_id>/recalcular/",
        calculo_recalculate,
    ),
    path(
        "organizaciones/<str:organizacion_id>/calculos/<int:calculo_id>/snapshot/",
        calculo_snapshot,
    ),
    path(
        "organizaciones/<str:organizacion_id>/calculos/<int:calculo_id>/comparar/<int:other_id>/",
        calculo_compare,
    ),
    path(
        "organizaciones/<str:organizacion_id>/impactos-ambientales/",
        impactos_ambientales,
    ),
    path(
        "organizaciones/<str:organizacion_id>/calidad/observaciones/",
        calidad_observaciones,
    ),
    path("organizaciones/<str:organizacion_id>/discrepancias/", discrepancias),
    path(
        "organizaciones/<str:organizacion_id>/discrepancias/<int:discrepancia_id>/",
        discrepancia_detail,
    ),
    path("organizaciones/<str:organizacion_id>/politicas-fuente/", politicas_fuente),
    path("organizaciones/<str:organizacion_id>/indicadores/", indicadores),
    path(
        "organizaciones/<str:organizacion_id>/indicadores/<int:indicador_id>/serie/",
        serie_indicador,
    ),
    path(
        "organizaciones/<str:organizacion_id>/indicadores/<int:indicador_id>/comparacion/",
        comparacion_indicador,
    ),
    path("organizaciones/<str:organizacion_id>/lineas-base/", lineas_base),
    path(
        "organizaciones/<str:organizacion_id>/resumen-ambiental-v2/",
        resumen_ambiental_v2,
    ),
    path("organizaciones/<str:organizacion_id>/estado/", organizacion_estado),
    path(
        "organizaciones/<str:organizacion_id>/configuracion/",
        organizacion_configuracion,
    ),
    path("organizaciones/<str:organizacion_id>/dashboard/", organizacion_dashboard),
    path("organizaciones/<str:organizacion_id>/etapas/", organizacion_etapas),
    path("organizaciones/<str:organizacion_id>/usuarios/", organizacion_usuarios),
    path("organizaciones/<str:organizacion_id>/usuarios/<int:user_id>/", organizacion_usuario_detail),
    path("organizaciones/<str:organizacion_id>/obras/", organizacion_obras),
    path(
        "organizaciones/<str:organizacion_id>/registros-emision/",
        organizacion_registros_emision,
    ),
    path(
        "organizaciones/<str:organizacion_id>/registros-emision/<int:registro_id>/aplicar-factor/",
        organizacion_registro_aplicar_factor,
    ),
    path("organizaciones/<str:organizacion_id>/emisiones/", organizacion_emisiones),
    path(
        "organizaciones/<str:organizacion_id>/acciones-ambientales/resumen/",
        organizacion_acciones_ambientales_resumen,
    ),
    path(
        "organizaciones/<str:organizacion_id>/acciones-ambientales/",
        organizacion_acciones_ambientales,
    ),
    path(
        "organizaciones/<str:organizacion_id>/acciones-ambientales/<int:action_id>/",
        organizacion_accion_ambiental_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/lotes-forestales/",
        organizacion_lotes_forestales,
    ),
    path(
        "organizaciones/<str:organizacion_id>/lotes-forestales/resumen/",
        organizacion_lotes_forestales_resumen,
    ),
    path(
        "organizaciones/<str:organizacion_id>/lotes-forestales/<str:lote_id>/transportes/",
        organizacion_lote_forestal_transportes,
    ),
    path(
        "organizaciones/<str:organizacion_id>/lotes-forestales/<str:lote_id>/",
        organizacion_lote_forestal_detail,
    ),
    path("organizaciones/<str:organizacion_id>/evidencias/", organizacion_evidencias),
    path(
        "organizaciones/<str:organizacion_id>/evidencias/extraer/",
        organizacion_evidencia_extraer,
    ),
    path("organizaciones/<str:organizacion_id>/reportes/", organizacion_reportes),
    path(
        "organizaciones/<str:organizacion_id>/documentos-ambientales/",
        documentos_ambientales,
    ),
    path(
        "organizaciones/<str:organizacion_id>/documentos-ambientales/<int:documento_id>/",
        documento_ambiental_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/variables-ambientales/",
        variables_ambientales,
    ),
    path(
        "organizaciones/<str:organizacion_id>/variables-ambientales/<int:variable_id>/",
        variable_ambiental_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/limites-ambientales/", limites_ambientales
    ),
    path(
        "organizaciones/<str:organizacion_id>/limites-ambientales/<int:limite_id>/",
        limite_ambiental_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/alertas-cumplimiento/",
        alertas_cumplimiento,
    ),
    path(
        "organizaciones/<str:organizacion_id>/alertas-cumplimiento/<int:alerta_id>/",
        alerta_cumplimiento_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/cumplimiento-ambiental/resumen/",
        cumplimiento_ambiental_resumen,
    ),
    path(
        "organizaciones/<str:organizacion_id>/motor-ambiental/",
        environmental_engine_results,
    ),
    path("organizaciones/<str:organizacion_id>/acv/", environmental_lca_results),
    path("organizaciones/<str:organizacion_id>/contexto/", organization_context_view),
    path("organizaciones/<str:organizacion_id>/kpis/", organization_kpis_view),
    path("problemas/<int:problem_id>/contexto/", problem_context_view),
    path("problemas/<int:problem_id>/historial/", problem_history_view),
    path("problemas/<int:problem_id>/fuentes/", problem_sources_view),
    path("problemas/<int:problem_id>/acciones-previas/", problem_actions_view),
    path("problemas/<int:problem_id>/evidencias-resumen/", problem_evidence_view),
    path("problemas/<int:problem_id>/contexto-normativo/", problem_normative_view),
    path("problemas/<int:problem_id>/recomendaciones/", problem_recommendations_view),
    path("problemas/<int:problem_id>/escalamiento/", problem_escalation_view),
    path("problemas/<int:problem_id>/expediente/", problem_dossier_view),
    path("materiales/<int:material_id>/ciclo-vida/", material_lifecycle_view),
    path("organizaciones/<str:organizacion_id>/problematicas/", problematicas),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/",
        problematica_detail,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/transicion/",
        problematica_transition,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/acciones/",
        problematica_actions,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/alcance/",
        problematica_scope,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/indicadores/",
        problematica_indicators,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/acciones/<int:action_id>/seleccionar/",
        problematica_action_select,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/acciones/<int:action_id>/iniciar/",
        problematica_action_start,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/acciones/<int:action_id>/implementar/",
        problematica_action_implement,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/seguimientos/",
        problematica_measurements,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/seguimientos/motor/",
        problematica_measure_engine,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/evaluar/",
        problematica_evaluate,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/snapshot-base/",
        problematica_snapshot_base,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/ciclos/",
        problematica_cycles,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/reevaluar/",
        problematica_reevaluate,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/escalar/",
        problematica_escalate,
    ),
    path(
        "organizaciones/<str:organizacion_id>/problematicas/<int:problematica_id>/historial/",
        problematica_history,
    ),
    path("environmental/kpis/<str:organizacion_id>/", environmental_kpis),
    path(
        "environmental/recommendations/<str:organizacion_id>/",
        environmental_recommendations,
    ),
    path("environmental/scenarios/<str:organizacion_id>/", environmental_scenarios),
    path(
        "environmental/decisions/priorities/<str:organizacion_id>/",
        environmental_decision_priorities,
    ),
    path(
        "environmental/executive-report/<str:organizacion_id>/",
        environmental_executive_report,
    ),
    path(
        "environmental/ingestion-readiness/<str:organizacion_id>/",
        environmental_ingestion_readiness,
    ),
    path(
        "environmental/decisions/priorities/<str:organizacion_id>/<str:priority_id>/action-preview/",
        environmental_decision_action_preview,
    ),
    path(
        "environmental/decisions/priorities/<str:organizacion_id>/<str:priority_id>/create-action/",
        environmental_decision_create_action,
    ),
    path(
        "environmental/actions/<int:action_id>/closure-status/",
        environmental_action_closure_status,
    ),
    path(
        "environmental/actions/<int:action_id>/attach-evidence/",
        environmental_action_attach_evidence,
    ),
    path("environmental/actions/<int:action_id>/close/", environmental_action_close),
    path("importaciones/completa/preview/", importacion_completa_preview),
    path("importaciones/completa/confirm/", importacion_completa_confirm),
    path("importaciones/plantilla-construccion/", plantilla_importacion_construccion),
    path("importaciones/plantilla-generica/", plantilla_importacion_generica),
    path("importaciones/generica/preview/", importacion_generica_preview),
    path(
        "organizaciones/<str:organizacion_id>/importaciones/<str:kind>/preview/",
        importacion_preview,
    ),
    path(
        "organizaciones/<str:organizacion_id>/importaciones/<str:kind>/confirm/",
        importacion_confirm,
    ),
    path("importaciones/<str:kind>/preview/", importacion_preview),
    path("importaciones/<str:kind>/confirm/", importacion_confirm),
    path("obras/", obras),
    path("obras/<str:codigo_obra>/", obra_detail),
    path("obras/<str:codigo_obra>/registros-emision/", obra_registros_emision),
    path("obras/<str:codigo_obra>/evidencias/", obra_evidencias),
    path("obras/<str:codigo_obra>/transportes/", obra_transportes),
    path("verificar/obra/<str:codigo_obra>/", verificar_obra),
    path("factores-emision/", factores_emision),
    path("factores-emision/<int:factor_id>/", factores_emision_detail),
    path("factores/catalogo/", factores_catalogo),
    path("materiales-construccion/", materiales_construccion),
    path("rutas/calcular-distancia/", calcular_distancia_ruta),
    path("sistema/estado/", sistema_estado),
    path("ai-advisor/", ai_advisor),
    path("intelligence/context/", recommendation_context),
    path("intelligence/recommendations/", recomendaciones),
]
