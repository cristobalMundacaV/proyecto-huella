from django.core.exceptions import ValidationError

from ..models import ProblematicaAmbiental

ALLOWED_TRANSITIONS = {
    "detectada": {"en_analisis", "escalada"},
    "en_analisis": {"accion_propuesta", "no_resuelta", "escalada"},
    "accion_propuesta": {"en_implementacion", "escalada"},
    "en_implementacion": {"en_seguimiento", "escalada"},
    "en_seguimiento": {"resuelta", "mejora_insuficiente", "no_resuelta", "escalada"},
    "mejora_insuficiente": {"accion_propuesta", "no_resuelta", "escalada"},
    "no_resuelta": {"en_analisis", "escalada"},
    "escalada": {"en_analisis", "no_resuelta"},
    "resuelta": set(),
}


def validate_problem_transition(problem, new_state):
    if new_state not in ALLOWED_TRANSITIONS.get(problem.estado, set()):
        raise ValidationError(
            {"estado": f"Transicion no permitida: {problem.estado} -> {new_state}."}
        )


def validate_action_recommendation(problem):
    allowed = {
        ProblematicaAmbiental.Estado.EN_ANALISIS,
        ProblematicaAmbiental.Estado.ANALIZANDO,
        ProblematicaAmbiental.Estado.DETECTADA,
    }
    if problem.estado not in allowed:
        raise ValidationError({"estado": "La problematica debe estar en analisis."})


def validate_measurement(problem, date, action=None, implemented=None):
    allowed = {
        ProblematicaAmbiental.Estado.EN_IMPLEMENTACION,
        ProblematicaAmbiental.Estado.EN_SEGUIMIENTO,
        ProblematicaAmbiental.Estado.IMPLEMENTANDO,
        ProblematicaAmbiental.Estado.SEGUIMIENTO,
    }
    if problem.estado not in allowed:
        raise ValidationError(
            {"estado": "La problematica debe estar en implementacion o seguimiento."}
        )
    if date <= problem.fecha_deteccion:
        raise ValidationError(
            {"fecha": "La medicion posterior debe ser posterior a la deteccion."}
        )
    if action and action.problematica_id != problem.id:
        raise ValidationError({"accion": "La accion no pertenece a la problematica."})
    if implemented and date < implemented.implementada_at.date():
        raise ValidationError(
            {"fecha": "La medicion debe ser posterior a la implementacion."}
        )


def validate_legacy_evaluation(problem, measurement):
    if problem.estado != ProblematicaAmbiental.Estado.EN_SEGUIMIENTO:
        raise ValidationError({"estado": "La problematica debe estar en seguimiento."})
    if not measurement:
        raise ValidationError(
            {"medicion": "Se requiere una medicion posterior para verificar la accion."}
        )
    if measurement.problematica_id != problem.id:
        raise ValidationError(
            {"medicion": "La medicion no pertenece a la problematica."}
        )


def validate_cycle_selection(problem):
    if not problem.indicadores_v2.exists():
        raise ValidationError(
            "Debe asociar al menos un indicador antes de seleccionar una accion."
        )
    if problem.ciclos_reevaluacion.count() + 1 > 3:
        raise ValidationError(
            "No se permite un cuarto ciclo automatico; escale profesionalmente."
        )


def validate_action_start(confirmed, cycle):
    if not confirmed:
        raise ValidationError("El inicio requiere confirmacion humana explicita.")
    if not cycle or not cycle.snapshot_base_id:
        raise ValidationError(
            "Seleccione la accion y prepare el snapshot BASE primero."
        )
