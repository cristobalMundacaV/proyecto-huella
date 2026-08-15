import json

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.analytics.models import ExpedienteAmbiental
from apps.analytics.services.environmental_context import evidence_summary, normative_context, problem_context


DOSSIER_RULES = """Resume el expediente ambiental procesado para evaluacion profesional.
No inventes datos, mediciones, causas, normativa ni cumplimiento. No recalcules valores.
Distingue hechos de hipotesis, declara brechas de informacion y no concluyas efectividad sin medicion.
Devuelve solo JSON con la clave resumen_ejecutivo."""


def build_processed_dossier(problem):
    context = problem_context(problem)
    actions = problem.acciones.order_by("created_at")[:50]
    measurements = problem.mediciones.select_related("accion").order_by("fecha", "created_at")[:50]
    history = problem.historial.order_by("created_at")[:50]
    recommendations = problem.recomendaciones_agente.order_by("created_at")[:20]
    hypotheses = []
    for recommendation in recommendations:
        hypotheses.extend((recommendation.diagnostico or {}).get("hipotesis", []))
    current = problem.valor_posterior if problem.valor_posterior is not None else context["kpi_actual"]
    gap = current - problem.objetivo_meta if current is not None else None
    return {
        "organizacion": {"id": problem.organizacion.organizacion_id, "nombre": problem.organizacion.nombre, "preset": problem.organizacion.preset},
        "obra": ({"id": problem.obra_id, "codigo": problem.obra.codigo_obra, "nombre": problem.obra.nombre,
                  "perfil": problem.obra.perfil_ambiental} if problem.obra_id else None),
        "problema": {"id": problem.id, "titulo": problem.titulo, "descripcion": problem.descripcion[:1000], "area": problem.area_operacional, "unidad_operacional": problem.unidad_operacional, "estado": problem.estado},
        "evaluacion": {"riesgo": problem.nivel_riesgo, "indicador": problem.indicador, "unidad": problem.unidad_indicador, "valor_inicial": problem.valor_inicial, "valor_actual": current, "meta": problem.objetivo_meta, "brecha": gap, "mejora_absoluta": problem.mejora_absoluta, "mejora_porcentaje": problem.mejora_porcentaje, "resultado": problem.resultado_evaluacion},
        "escalamiento": {"requiere_evaluacion_profesional": problem.requiere_evaluacion_profesional, "criterios": problem.criterios_escalamiento, "fecha": problem.escalada_at},
        "historial": [{"evento": row.evento, "estado_anterior": row.estado_anterior, "estado_nuevo": row.estado_nuevo, "detalle": row.detalle[:300], "fecha": row.created_at} for row in history],
        "acciones": [{"id": row.id, "titulo": row.titulo, "descripcion": row.descripcion[:500], "responsable": row.responsable, "implementada_at": row.implementada_at, "fecha_objetivo": row.fecha_objetivo} for row in actions],
        "mediciones": [{"id": row.id, "fecha": row.fecha, "valor": row.valor, "unidad": row.unidad, "fuente": row.fuente, "accion_id": row.accion_id} for row in measurements],
        "evidencias_resumen": evidence_summary(problem),
        "contexto_normativo": normative_context(problem),
        "causas_hipotesis": hypotheses[:20],
        "recomendaciones_previas": [{"id": row.id, "accion": row.accion, "justificacion": row.justificacion[:500], "resultado_esperado": row.resultado_esperado, "prioridad": row.prioridad, "confianza": row.nivel_confianza} for row in recommendations],
        "limites_contexto": {"historial": 50, "acciones": 50, "mediciones": 50, "recomendaciones": 20, "documentos_completos_incluidos": False},
    }


@transaction.atomic
def generate_dossier(problem, provider, *, user=None):
    problem = type(problem).objects.select_for_update().get(pk=problem.pk)
    if not problem.requiere_evaluacion_profesional or problem.estado != "escalada":
        raise ValidationError("Solo se puede generar expediente para una problematica escalada.")
    content = json.loads(json.dumps(build_processed_dossier(problem), default=str, ensure_ascii=False))
    response = provider.generate(system_rules=DOSSIER_RULES, context=content)
    summary = response.get("resumen_ejecutivo", "") if isinstance(response, dict) else ""
    if not summary or not isinstance(summary, str):
        raise ValidationError("El proveedor no devolvio un resumen ejecutivo estructurado.")
    normalized_summary = summary.lower()
    if ("cumple la normativa" in normalized_summary or "cumplimiento legal confirmado" in normalized_summary) and not content["contexto_normativo"]["reglas_validadas"]:
        raise ValidationError("El resumen no puede afirmar cumplimiento sin una regla validada.")
    if ("accion efectiva" in normalized_summary or "la accion es efectiva" in normalized_summary) and problem.valor_posterior is None:
        raise ValidationError("El resumen no puede afirmar efectividad sin medicion posterior.")
    version = (problem.expedientes.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    return ExpedienteAmbiental.objects.create(
        problematica=problem, version=version, contenido_procesado=content, resumen_ejecutivo=summary,
        proveedor_resumen=provider.name, modelo_resumen=provider.model,
        generado_por=user.get_username() if user and user.is_authenticated else "",
    )
