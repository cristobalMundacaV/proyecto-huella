from django.utils import timezone

from ..models import EvaluacionCalidadDato
from ..policies.quality import quality_assessment, source_health

RULES_VERSION = "calidad-v1"


def evaluate_observation_quality(observation, persist=True, user=None):
    payload = quality_assessment(observation, reviewed_by_user=bool(user))
    payload["version_reglas"] = RULES_VERSION
    if not persist:
        return payload
    return EvaluacionCalidadDato.objects.create(
        organizacion=observation.organizacion,
        observacion=observation,
        automatica=user is None,
        evaluado_por=user,
        **payload,
    )


def update_discrepancy(discrepancy, data):
    for field, value in data.items():
        setattr(discrepancy, field, value)
    discrepancy.full_clean()
    discrepancy.save()
    return discrepancy
