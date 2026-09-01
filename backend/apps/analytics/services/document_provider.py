import base64
import json
import mimetypes
import re
from typing import Protocol


DOCUMENT_EXTRACTION_PROMPT = """Extrae solo datos visibles del archivo. Devuelve JSON con tipo_documento,
relevancia_detectada, motivo_relevancia, confianza_clasificacion, legibilidad,
confianza_extraccion y claims. Cada claim observado usa valor_original y confianza;
puede incluir tipo_recurso, cantidad, unidad, fecha e identificador_documento.
No normalices, no compares con formularios y no decidas calidad ambiental. Omite lo no visible."""


class DocumentProviderError(Exception):
    def __init__(self, code, *, detail="", provider="", model="", attempts=None, metadata=None):
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.provider = provider
        self.model = model
        self.attempts = attempts or []
        self.metadata = metadata or {}


class DocumentProviderConfigurationError(DocumentProviderError):
    pass


class DocumentProvider(Protocol):
    name: str
    model: str

    @property
    def available(self) -> bool: ...

    def extract_visual(self, upload) -> dict: ...


def parse_provider_json(raw):
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1] if start >= 0 and end >= 0 else text)


def validate_provider_result(result):
    if not isinstance(result, dict) or not isinstance(result.get("claims", {}), dict):
        raise DocumentProviderError("invalid_provider_response")
    relevance = result.get("relevancia_detectada")
    if relevance not in {"pertinente", "parcialmente_pertinente", "no_pertinente", "indeterminado"}:
        raise DocumentProviderError("invalid_provider_response", detail="invalid_relevance")
    try:
        float(result.get("confianza_clasificacion", result.get("confianza", 0)))
    except (TypeError, ValueError) as exc:
        raise DocumentProviderError("invalid_provider_response", detail="invalid_confidence") from exc
    return result


def read_visual_upload(upload):
    filename = getattr(upload, "name", "documento") or "documento"
    content_type = getattr(upload, "content_type", "") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    try:
        upload.seek(0)
    except Exception:
        pass
    content = upload.read()
    try:
        upload.seek(0)
    except Exception:
        pass
    if not content:
        raise DocumentProviderError("empty_file")
    if not content_type.startswith("image/") and content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise DocumentProviderError("unsupported_mime", detail=content_type)
    encoded = base64.b64encode(content).decode("ascii")
    return {
        "filename": filename,
        "content_type": content_type,
        "content": content,
        "data_url": f"data:{'application/pdf' if filename.lower().endswith('.pdf') else content_type};base64,{encoded}",
    }


def attach_provider_metadata(result, *, provider, model, upload_data):
    result["_provider_metadata"] = {
        "provider": provider,
        "model": model,
        "mime_type": upload_data["content_type"],
        "bytes_received": len(upload_data["content"]),
        "stream_rewound": True,
    }
    return result
