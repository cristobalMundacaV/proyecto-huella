from django.utils import timezone

from ..models import EvaluacionCalidadDato, Observacion


RULES_VERSION = "calidad-v1"


def source_health(observation):
    source = observation.fuente
    if not source.activa:
        return "fuera_servicio", "La fuente esta inactiva."
    try:
        reading = observation.lectura_sensor_v2
    except Exception:
        reading = None
    if reading:
        sensor = reading.sensor
        if sensor.estado in {"fuera_servicio", "calibracion_vencida", "requiere_revision"}:
            return sensor.estado, f"El sensor esta {sensor.get_estado_display().lower()}."
        if reading.calidad_tecnica == "requiere_revision":
            return "requiere_revision", "La lectura requiere revision tecnica."
        return "operativo", "Sensor operativo y lectura tecnicamente valida."
    if source.tipo == "manual":
        return "declarativa", "Dato manual con procedencia declarativa."
    return "disponible", "Fuente disponible; no se infiere certeza adicional."


def evaluate_observation_quality(observation, persist=True, user=None):
    health, health_reason = source_health(observation)
    reasons = [health_reason]
    if observation.estado == Observacion.Estado.RECHAZADA:
        state = EvaluacionCalidadDato.Estado.NO_CONFIABLE
        reasons.append("La observacion fue rechazada.")
    elif observation.valor_numerico is None and not observation.valor_texto:
        state = EvaluacionCalidadDato.Estado.INCOMPLETO
        reasons.append("La observacion no contiene valor.")
    elif health in {"fuera_servicio"}:
        state = EvaluacionCalidadDato.Estado.NO_CONFIABLE
    elif health in {"calibracion_vencida", "requiere_revision"}:
        state = EvaluacionCalidadDato.Estado.REQUIERE_REVISION
    elif health == "declarativa" or observation.estado == Observacion.Estado.PENDIENTE:
        state = EvaluacionCalidadDato.Estado.CONFIABLE_OBSERVACIONES
    else:
        state = EvaluacionCalidadDato.Estado.CONFIABLE
    dimensions = {
        "procedencia": observation.naturaleza,
        "estado_fuente": health,
        "completitud": "completa" if observation.valor_numerico is not None or observation.valor_texto else "incompleta",
        "coherencia": "sin_alertas",
        "discrepancia": "no_evaluada",
        "elegibilidad_calculo": "evaluable",
        "revision_humana": bool(user),
    }
    payload = {"estado": state, "motivos": reasons, "dimensiones": dimensions, "version_reglas": RULES_VERSION}
    if not persist:
        return payload
    return EvaluacionCalidadDato.objects.create(
        organizacion=observation.organizacion, observacion=observation, automatica=user is None,
        evaluado_por=user, **payload,
    )
