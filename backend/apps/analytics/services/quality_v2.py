from ..models import EvaluacionCalidadDato
from ..policies.quality import quality_assessment, source_health

RULES_VERSION = "calidad-v2-evidencia"


def quality_input_fingerprint(observation):
    evidence = observation.evidencia
    return {
        "observacion_actualizada": observation.updated_at.isoformat(),
        "estado_observacion": observation.estado,
        "fuente_activa": observation.fuente.activa,
        "evidencia_id": observation.evidencia_id,
        "estado_evidencia": evidence.estado_documental if evidence else None,
        "evidencia_actualizada": evidence.updated_at.isoformat() if evidence else None,
    }


def evaluate_observation_quality(observation, persist=True, user=None):
    payload = quality_assessment(observation, reviewed_by_user=bool(user))
    payload["version_reglas"] = RULES_VERSION
    payload["dimensiones"]["inputs_relevantes"] = quality_input_fingerprint(observation)
    if not persist:
        return payload
    return EvaluacionCalidadDato.objects.create(
        organizacion=observation.organizacion,
        observacion=observation,
        automatica=user is None,
        evaluado_por=user,
        **payload,
    )


def ensure_current_quality_evaluation(observation):
    latest = observation.evaluaciones_calidad.order_by("-fecha_evaluacion", "-id").first()
    fingerprint = quality_input_fingerprint(observation)
    if (
        latest
        and latest.version_reglas == RULES_VERSION
        and latest.dimensiones.get("inputs_relevantes") == fingerprint
    ):
        return latest
    return evaluate_observation_quality(observation)


def update_discrepancy(discrepancy, data):
    for field, value in data.items():
        setattr(discrepancy, field, value)
    discrepancy.full_clean()
    discrepancy.save()
    return discrepancy
