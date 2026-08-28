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

GENERIC_UPDATE_FORBIDDEN_STATES = {
    ProblematicaAmbiental.Estado.CERRADA,
    ProblematicaAmbiental.Estado.RESUELTA,
}


def validate_generic_problem_update(problem, payload):
    requested_state = payload.get("estado") if payload else None
    if requested_state in GENERIC_UPDATE_FORBIDDEN_STATES:
        raise ValidationError(
            {
                "estado": (
                    "El cierre no puede realizarse mediante una actualización "
                    "genérica. Debe completar la reevaluación verificable."
                )
            }
        )


def validate_verified_resolution(cycle, result):
    errors = []
    if not cycle or not cycle.accion_id or not cycle.accion.fecha_seleccion:
        errors.append("La acción debe haber sido seleccionada explícitamente.")
    if not cycle or not cycle.snapshot_base_id or not cycle.snapshot_resultado_id:
        errors.append("Se requieren snapshots BASE y RESULTADO.")
    elif not cycle.snapshot_base.congelado or not cycle.snapshot_resultado.congelado:
        errors.append("Los snapshots de verificación deben estar congelados.")
    if not result or not cycle or cycle.resultado_id != result.id:
        errors.append("El ciclo debe conservar su resultado determinístico.")
    elif (
        result.problematica_id != cycle.problematica_id
        or result.accion_id != cycle.accion_id
        or result.snapshot_base_id != cycle.snapshot_base_id
        or result.snapshot_resultado_id != cycle.snapshot_resultado_id
    ):
        errors.append("El resultado no corresponde al ciclo de reevaluación.")
    if not cycle or not cycle.fecha_cierre:
        errors.append("El ciclo de reevaluación debe estar cerrado.")
    if errors:
        raise ValidationError({"estado": errors})


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
