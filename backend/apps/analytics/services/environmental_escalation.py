from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.analytics.models import HistorialProblematicaAmbiental, ProblematicaAmbiental
from apps.analytics.services.environmental_context import normative_context, problem_context


PERSISTENCE_DAYS = 90


def _normative_gaps(problem, current_value):
    gaps = []
    if current_value is None:
        return gaps
    value = Decimal(current_value)
    for rule in normative_context(problem)["reglas_validadas"]:
        if rule["limite"] is None:
            continue
        limit = Decimal(rule["limite"])
        breached = (rule["comparador"] == "<=" and value > limit) or (rule["comparador"] == ">=" and value < limit)
        if breached:
            gaps.append({"regla_id": rule["id"], "normativa": rule["normativa"], "valor": str(value), "limite": str(limit), "comparador": rule["comparador"]})
    return gaps


def evaluate_escalation(problem):
    context = problem_context(problem)
    implemented = problem.acciones.filter(implementada_at__isnull=False).count()
    failed = problem.resultado_evaluacion in {ProblematicaAmbiental.Resultado.NO_EFECTIVA, ProblematicaAmbiental.Resultado.PARCIAL}
    insufficient_count = problem.historial.filter(evento="verificacion", detalle=ProblematicaAmbiental.Resultado.PARCIAL).count()
    restrictions = (problem.metadata or {}).get("restricciones_tecnicas") or (problem.metadata or {}).get("restricciones_operacionales") or []
    normative_gaps = _normative_gaps(problem, context["kpi_actual"])
    reasons = []
    if implemented >= 2 and failed:
        reasons.append({"criterio": "acciones_fallidas_repetidas", "acciones_implementadas": implemented})
    if problem.fecha_deteccion <= timezone.localdate() - timedelta(days=PERSISTENCE_DAYS) and problem.estado not in {"resuelta"}:
        reasons.append({"criterio": "problema_persistente", "dias_minimos": PERSISTENCE_DAYS})
    if problem.resultado_evaluacion == ProblematicaAmbiental.Resultado.NO_EFECTIVA:
        reasons.append({"criterio": "resultado_no_efectivo"})
    if insufficient_count >= 2:
        reasons.append({"criterio": "mejora_insuficiente_repetida", "evaluaciones": insufficient_count})
    if problem.nivel_riesgo in {ProblematicaAmbiental.Riesgo.ALTO, ProblematicaAmbiental.Riesgo.CRITICO}:
        reasons.append({"criterio": f"riesgo_{problem.nivel_riesgo}"})
    if normative_gaps:
        reasons.append({"criterio": "brecha_normativa_validada", "brechas": normative_gaps})
    if restrictions:
        reasons.append({"criterio": "restricciones_tecnicas_operacionales", "cantidad": len(restrictions) if isinstance(restrictions, list) else 1})
    return {"debe_escalar": bool(reasons), "requiere_evaluacion_profesional": bool(reasons), "criterios": reasons}


@transaction.atomic
def apply_escalation(problem, *, user=None):
    result = evaluate_escalation(problem)
    if not result["debe_escalar"] or problem.estado == ProblematicaAmbiental.Estado.RESUELTA:
        return result
    if not problem.requiere_evaluacion_profesional:
        old = problem.estado
        problem.estado = ProblematicaAmbiental.Estado.ESCALADA
        problem.requiere_evaluacion_profesional = True
        problem.criterios_escalamiento = result["criterios"]
        problem.escalada_at = timezone.now()
        problem.save(update_fields=["estado", "requiere_evaluacion_profesional", "criterios_escalamiento", "escalada_at", "updated_at"])
        HistorialProblematicaAmbiental.objects.create(
            problematica=problem, evento="escalamiento", estado_anterior=old, estado_nuevo="escalada",
            detalle="Requiere evaluacion profesional.", usuario=user.get_username() if user and user.is_authenticated else "",
            metadata={"criterios": result["criterios"]},
        )
    return result
