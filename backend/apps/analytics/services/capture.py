from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import Observacion
from ..policies.capture import CHANNEL_PROVENANCE, capture_contract_errors


@transaction.atomic
def capture_observation(
    *,
    channel,
    organization,
    source,
    concept,
    timestamp,
    numeric_value=None,
    text_value="",
    unit="",
    activity=None,
    actor=None,
    evidence=None,
    evidence_version=None,
    extracted_record=None,
    method=None,
    nature=None,
    state=None,
):
    provenance = CHANNEL_PROVENANCE[channel]
    errors = capture_contract_errors(
        organization=organization,
        provenance=provenance,
        source=source,
        activity=activity,
        evidence=evidence,
        evidence_version=evidence_version,
        extracted_record=extracted_record,
    )
    if errors:
        raise ValidationError(errors)
    observation = Observacion(
        organizacion=organization,
        actividad=activity,
        fuente=source,
        concepto=concept,
        valor_numerico=numeric_value,
        valor_texto=text_value or "",
        unidad=unit or "",
        timestamp_observacion=timestamp,
        metodo_captura=method or provenance.method,
        naturaleza=nature or provenance.nature,
        actor=actor,
        evidencia=evidence,
        version_evidencia=evidence_version,
        registro_extraido=extracted_record,
        estado=state or provenance.state,
    )
    observation.full_clean()
    observation.save()
    return observation
