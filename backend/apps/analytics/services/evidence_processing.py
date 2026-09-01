import logging

from django.db import transaction

from ..models import Observacion, VersionEvidencia
from .document_extraction import extract_environmental_document
from .evidence_documents import DOCUMENT_RESULT_VERSION, document_result_for_version
from .evidence_validation import validate_observation_evidence
from .quality_v2 import ensure_current_quality_evaluation


logger = logging.getLogger(__name__)
PIPELINE_VERSION = "evidence-pipeline-v2"


def _mark_analyzing(version_id):
    with transaction.atomic():
        version = VersionEvidencia.objects.select_for_update().get(pk=version_id)
        existing = document_result_for_version(version)
        if version.estado_procesamiento == VersionEvidencia.EstadoProcesamiento.PROCESADA and existing:
            return version, existing
        version.estado_procesamiento = VersionEvidencia.EstadoProcesamiento.ANALIZANDO
        metadata = dict(version.metadata_tecnica or {})
        metadata["pipeline_version"] = PIPELINE_VERSION
        metadata["attempts"] = int(metadata.get("attempts") or 0) + 1
        version.metadata_tecnica = metadata
        version.save(update_fields=["estado_procesamiento", "metadata_tecnica", "updated_at"])
        return version, None


def process_evidence_version(version_id, *, force=False):
    version, existing = _mark_analyzing(version_id)
    if existing and not force:
        return existing
    try:
        version.archivo.open("rb")
        extraction = extract_environmental_document(
            version.archivo,
            preset=version.organizacion.preset,
        )
    except Exception as exc:
        logger.exception("evidence_extraction_failed", extra={"version_id": version_id})
        extraction = {
            "execution_status": "failed",
            "failure_code": "extraction_error",
            "claims": {},
            "claims_trazables": {},
            "claims_count": 0,
            "texto_extraido": "",
        }
    finally:
        try:
            version.archivo.close()
        except Exception:
            pass

    observations = list(
        Observacion.objects.filter(version_evidencia_id=version_id)
        .select_related("evidencia", "actividad", "fuente", "version_evidencia")
    )
    validations = []
    for observation in observations:
        record = getattr(observation.actividad, "registro_flujo_ambiental", None)
        validation = validate_observation_evidence(
            observation,
            extraction,
            context={"tipo_recurso": getattr(record, "tipo_recurso", "")},
            version=version,
        )
        validations.append({"observation_id": observation.id, **validation})

    technical_ok = extraction.get("execution_status") == "success"
    if validations:
        result = dict(validations[0])
    else:
        result = {
            "veredicto": "indeterminada",
            "relevancia": None,
            "comparaciones": [],
            "motivos": ["El documento aún no está vinculado a un dato ambiental comparable."],
        }
    result.update({
        "version_contrato": DOCUMENT_RESULT_VERSION,
        "tipo_detectado": extraction.get("tipo_documento"),
        "claims": dict(extraction.get("claims") or {}),
        "claims_trazables": dict(extraction.get("claims_trazables") or {}),
        "texto_extraido": extraction.get("texto_extraido") or "",
        "extraccion": {key: extraction.get(key) for key in (
            "execution_status", "extractor_used", "provider_used", "model_used",
            "failure_code", "claims_count", "relevancia_detectada", "confianza",
        )},
        "validaciones": validations,
    })
    result["extraccion"]["metadata"] = dict(
        extraction.get("extraction_metadata") or extraction.get("metadata") or {}
    )
    with transaction.atomic():
        locked = VersionEvidencia.objects.select_for_update().get(pk=version_id)
        metadata = dict(locked.metadata_tecnica or {})
        metadata["document_result"] = result
        locked.metadata_tecnica = metadata
        locked.tipo_documental = extraction.get("tipo_documento") or ""
        locked.estado_procesamiento = (
            VersionEvidencia.EstadoProcesamiento.PROCESADA
            if technical_ok
            else VersionEvidencia.EstadoProcesamiento.ERROR
        )
        locked.save(update_fields=["metadata_tecnica", "tipo_documental", "estado_procesamiento", "updated_at"])
    for observation in observations:
        fresh = Observacion.objects.select_related(
            "evidencia", "version_evidencia", "fuente"
        ).get(pk=observation.pk)
        ensure_current_quality_evaluation(fresh)
    return result
