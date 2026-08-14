from decimal import Decimal

from django.db import transaction

from ..models import DiscrepanciaDato, Observacion, PoliticaConfianzaFuente
from .quality_v2 import evaluate_observation_quality


def is_technical_duplicate(first, second):
    if first.actividad_id != second.actividad_id or first.concepto != second.concepto or first.fuente_id != second.fuente_id:
        return False
    if first.valor_numerico != second.valor_numerico or first.valor_texto != second.valor_texto or first.unidad != second.unidad:
        return False
    first_reading = getattr(first, "lectura_sensor_v2", None)
    second_reading = getattr(second, "lectura_sensor_v2", None)
    if first_reading and second_reading:
        if first_reading.pk == second_reading.pk:
            return True
        same_measurement = (
            first_reading.sensor_id == second_reading.sensor_id
            and first_reading.timestamp == second_reading.timestamp
            and first_reading.concepto == second_reading.concepto
            and first_reading.valor_numerico == second_reading.valor_numerico
            and first_reading.unidad == second_reading.unidad
        )
        if not same_measurement:
            return False
        technical_keys = ("external_id", "message_id", "reading_id", "idempotency_key")
        first_reference = next((first_reading.metadata_tecnica.get(key) for key in technical_keys if first_reading.metadata_tecnica.get(key)), None)
        second_reference = next((second_reading.metadata_tecnica.get(key) for key in technical_keys if second_reading.metadata_tecnica.get(key)), None)
        return not (first_reference or second_reference) or first_reference == second_reference
    if first_reading or second_reading:
        return False
    if first.version_evidencia_id and first.version_evidencia_id == second.version_evidencia_id:
        return (
            first.metodo_captura == second.metodo_captura
            and first.timestamp_observacion == second.timestamp_observacion
        )
    return False


def _policy_priority(organization, concept, source_type):
    policies = PoliticaConfianzaFuente.objects.filter(concepto=concept, tipo_fuente=source_type, activa=True)
    policy = policies.filter(organizacion=organization).first()
    if policy is None:
        policy = policies.filter(organizacion__isnull=True).first()
    return policy.prioridad if policy else None


@transaction.atomic
def resolve_observation(activity, concept):
    observations = list(activity.observaciones.filter(concepto=concept).exclude(estado=Observacion.Estado.RECHAZADA).select_related("fuente"))
    if not observations:
        return {"observacion": None, "alternativas": [], "motivo": "No existen observaciones.", "discrepancia": None, "estado": "sin_datos"}
    unique = []
    duplicates = []
    for observation in observations:
        if any(is_technical_duplicate(observation, current) for current in unique):
            duplicates.append(observation)
        else:
            unique.append(observation)
    if len(unique) == 1:
        return {"observacion": unique[0], "alternativas": duplicates, "motivo": "Unica observacion no duplicada.", "discrepancia": None, "estado": "seleccion_inequivoca"}

    numeric = [item for item in unique if item.valor_numerico is not None]
    discrepancy = None
    if len(numeric) > 1 and len({item.valor_numerico for item in numeric}) > 1:
        values = [Decimal(item.valor_numerico) for item in numeric]
        absolute = max(values) - min(values)
        base = min(abs(value) for value in values if value != 0) if any(values) else None
        relative = absolute / base if base else None
        discrepancy = DiscrepanciaDato.objects.filter(
            organizacion=activity.organizacion, actividad=activity, concepto=concept,
            estado__in=[DiscrepanciaDato.Estado.DETECTADA, DiscrepanciaDato.Estado.REQUIERE_REVISION],
        ).first()
        if not discrepancy:
            discrepancy = DiscrepanciaDato.objects.create(
                organizacion=activity.organizacion, actividad=activity, concepto=concept,
                estado=DiscrepanciaDato.Estado.REQUIERE_REVISION, diferencia_absoluta=absolute,
                diferencia_relativa=relative, severidad=DiscrepanciaDato.Severidad.MEDIA,
                motivo="Valores distintos para la misma actividad y concepto.",
            )
        discrepancy.observaciones.set(numeric)

    ranked = []
    for observation in unique:
        quality = evaluate_observation_quality(observation, persist=False)
        priority = _policy_priority(activity.organizacion, concept, observation.fuente.tipo)
        if quality["estado"] not in {"no_confiable", "requiere_revision", "incompleto"} and priority is not None:
            ranked.append((priority, observation))
    ranked.sort(key=lambda item: item[0])
    if ranked and (len(ranked) == 1 or ranked[0][0] < ranked[1][0]):
        selected = ranked[0][1]
        if discrepancy:
            discrepancy.observacion_seleccionada = selected
            discrepancy.motivo = "Seleccion automatica por politica de fuente inequivoca."
            discrepancy.save(update_fields=["observacion_seleccionada", "motivo", "updated_at"])
        return {"observacion": selected, "alternativas": [x for x in observations if x.pk != selected.pk], "motivo": "Politica de fuente inequivoca.", "discrepancia": discrepancy, "estado": "seleccion_inequivoca"}
    return {"observacion": None, "alternativas": observations, "motivo": "Fuentes contradictorias sin prioridad inequivoca.", "discrepancia": discrepancy, "estado": "requiere_revision"}
