import hashlib

from django.core.files.base import ContentFile
from django.db import transaction

from ..models import VersionEvidencia


DOCUMENT_RESULT_VERSION = "document-result-v2"
CANONICAL_VERDICTS = {
    "verificada",
    "compatible_incompleta",
    "contradiccion",
    "no_pertinente",
    "indeterminada",
}


def document_result_for_version(version):
    if not version:
        return None
    result = dict((version.metadata_tecnica or {}).get("document_result") or {})
    return result if result.get("veredicto") in CANONICAL_VERDICTS else None


def current_evidence_version(evidence, observation=None):
    if observation and observation.version_evidencia_id:
        return observation.version_evidencia
    return evidence.versiones.order_by("-version", "-id").first() if evidence else None


def current_document_result(evidence, observation=None):
    version = current_evidence_version(evidence, observation)
    result = document_result_for_version(version)
    if result:
        return result
    # Read-only historical adapter. New writes never use parent metadata as authority.
    legacy = dict((evidence.metadata_extraccion or {}).get("validacion_documental") or {}) if evidence else {}
    verdict = legacy.get("estado")
    if verdict not in CANONICAL_VERDICTS:
        verdict = "indeterminada"
    return {
        "version_contrato": DOCUMENT_RESULT_VERSION,
        "veredicto": verdict,
        "relevancia": legacy.get("relevancia"),
        "comparaciones": legacy.get("comparaciones") or [],
        "motivos": legacy.get("motivos") or [],
        "claims": {},
        "claims_trazables": {},
        "tipo_detectado": None,
        "legacy": True,
    }


@transaction.atomic
def create_evidence_version(evidence, *, content=None, filename=None, mime_type="", actor=None):
    if content is None:
        evidence.archivo.open("rb")
        try:
            content = evidence.archivo.read()
        finally:
            evidence.archivo.close()
    filename = filename or evidence.archivo.name.rsplit("/", 1)[-1]
    checksum = hashlib.sha256(content).hexdigest()
    existing = evidence.versiones.filter(checksum_sha256=checksum).order_by("-version").first()
    if existing:
        return existing, False
    number = (evidence.versiones.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    version = VersionEvidencia(
        evidencia=evidence,
        organizacion=evidence.organizacion,
        version=number,
        archivo=ContentFile(content, name=filename),
        nombre_original=filename[:240],
        checksum_sha256=checksum,
        metadata_tecnica={
            "mime_type": mime_type or "",
            "size_bytes": len(content),
            "actor_id": getattr(actor, "id", None),
            "document_result_version": DOCUMENT_RESULT_VERSION,
        },
    )
    version.full_clean()
    version.save()
    return version, True
