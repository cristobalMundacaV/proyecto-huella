from dataclasses import dataclass

from ..models import FuenteDatos, Observacion


@dataclass(frozen=True)
class CaptureProvenance:
    channel: str
    method: str
    nature: str
    state: str


CHANNEL_PROVENANCE = {
    "manual": CaptureProvenance(
        "manual",
        Observacion.MetodoCaptura.MANUAL,
        Observacion.Naturaleza.DECLARATIVO,
        Observacion.Estado.PENDIENTE,
    ),
    "document": CaptureProvenance(
        "document",
        Observacion.MetodoCaptura.IMPORTADO,
        Observacion.Naturaleza.DOCUMENTAL,
        Observacion.Estado.PENDIENTE,
    ),
    "import": CaptureProvenance(
        "import",
        Observacion.MetodoCaptura.IMPORTADO,
        Observacion.Naturaleza.DOCUMENTAL,
        Observacion.Estado.PENDIENTE,
    ),
    "api": CaptureProvenance(
        "api",
        Observacion.MetodoCaptura.API,
        Observacion.Naturaleza.EXTRAIDO,
        Observacion.Estado.PENDIENTE,
    ),
    "sensor": CaptureProvenance(
        "sensor",
        Observacion.MetodoCaptura.INSTRUMENTAL,
        Observacion.Naturaleza.INSTRUMENTAL,
        Observacion.Estado.PENDIENTE,
    ),
}


def ingestion_capture_channel(ingestion_type):
    return {
        "tabular": "import",
        "documental": "document",
        "manual_estructurado": "manual",
        "api": "api",
        "telemetria": "sensor",
        "sensor": "sensor",
    }[ingestion_type]


def capture_contract_errors(
    *,
    organization,
    provenance,
    source,
    activity=None,
    evidence=None,
    evidence_version=None,
    extracted_record=None,
):
    errors = {}
    relations = (
        ("fuente", source),
        ("actividad", activity),
        ("evidencia", evidence),
        ("version_evidencia", evidence_version),
    )
    for field, relation in relations:
        if relation is not None and relation.organizacion_id != organization.id:
            errors[field] = "La referencia pertenece a otra organizacion."
    if evidence_version and evidence and evidence_version.evidencia_id != evidence.id:
        errors["version_evidencia"] = "La version no pertenece a la evidencia."
    if provenance.channel in {"document", "import", "api"} and not (
        extracted_record or evidence_version
    ):
        errors["provenance"] = (
            "La captura requiere un registro extraido o una version de evidencia."
        )
    if provenance.channel == "sensor" and source.tipo not in {
        FuenteDatos.Tipo.SENSOR,
        FuenteDatos.Tipo.TELEMETRIA,
        FuenteDatos.Tipo.GPS,
    }:
        errors["fuente"] = "La captura instrumental requiere una fuente tecnica."
    return errors
