import json
import logging

from openai import APIConnectionError, APIStatusError, OpenAI

from .document_provider import (
    DOCUMENT_EXTRACTION_PROMPT,
    DocumentProviderError,
    attach_provider_metadata,
    parse_provider_json,
    read_visual_upload,
    validate_provider_result,
)


logger = logging.getLogger(__name__)

RELEVANCE_VALUES = [
    "pertinente", "parcialmente_pertinente", "no_pertinente", "indeterminado",
]
CLAIM_FIELDS = ["tipo_recurso", "cantidad", "unidad", "fecha", "identificador_documento"]
DOCUMENT_TYPE_VALUES = [
    "factura_combustible", "factura_material", "boleta_electrica", "factura_agua",
    "guia_despacho", "ticket_pesaje", "certificado_residuos", "registro_maquinaria",
    "documento_transporte", "otro",
]


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


CLAIM_SCHEMA = _nullable({
    "type": "object",
    "properties": {
        "valor_original": _nullable({"type": ["string", "number"]}),
        "confianza": _nullable({"type": "number", "minimum": 0, "maximum": 1}),
    },
    "required": ["valor_original", "confianza"],
    "additionalProperties": False,
})

DOCUMENT_RESPONSE_SCHEMA = {
    "name": "environmental_document_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "tipo_documento": {"type": "string", "enum": DOCUMENT_TYPE_VALUES},
            "relevancia_detectada": {"type": "string", "enum": RELEVANCE_VALUES},
            "motivo_relevancia": {"type": "string"},
            "confianza_clasificacion": {"type": "number", "minimum": 0, "maximum": 1},
            "legibilidad": {"type": "string"},
            "confianza_extraccion": _nullable({"type": "number", "minimum": 0, "maximum": 1}),
            "claims": {
                "type": "object",
                "properties": {field: CLAIM_SCHEMA for field in CLAIM_FIELDS},
                "required": CLAIM_FIELDS,
                "additionalProperties": False,
            },
        },
        "required": [
            "tipo_documento", "relevancia_detectada", "motivo_relevancia",
            "confianza_clasificacion", "legibilidad", "confianza_extraccion", "claims",
        ],
        "additionalProperties": False,
    },
}


def _response_metadata(response, *, requested_model, content=None):
    choices = getattr(response, "choices", None) or []
    first = choices[0] if choices else None
    return {
        "requested_model": requested_model,
        "actual_model": str(getattr(response, "model", "") or ""),
        "response_id": str(getattr(response, "id", "") or ""),
        "finish_reason": str(getattr(first, "finish_reason", "") or "") if first else "",
        "choices_count": len(choices),
        "content_type": type(content).__name__ if content is not None else "null",
        "unstable_router": requested_model == "openrouter/free",
    }


def _validate_shape(result):
    if not isinstance(result, dict):
        raise DocumentProviderError("invalid_root")
    if not isinstance(result.get("claims"), dict):
        raise DocumentProviderError("invalid_claims_type")
    if result.get("relevancia_detectada") not in RELEVANCE_VALUES:
        raise DocumentProviderError("invalid_relevance")
    try:
        float(result.get("confianza_clasificacion", result.get("confianza", 0)))
    except (TypeError, ValueError) as exc:
        raise DocumentProviderError("invalid_confidence") from exc
    return validate_provider_result(result)


class OpenRouterDocumentProvider:
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    def __init__(self, *, api_key, model):
        self.api_key = api_key or ""
        self.model = model or ""

    @property
    def available(self):
        return bool(self.api_key)

    def extract_visual(self, upload):
        if not self.available:
            raise DocumentProviderError("missing_api_key", provider=self.name, model=self.model)
        if self.model == "openrouter/free":
            logger.warning("OpenRouter free router is enabled for document extraction; this mode is not stable for production")
        data = read_visual_upload(upload)
        if data["content_type"] == "application/pdf" or data["filename"].lower().endswith(".pdf"):
            attachment = {
                "type": "file",
                "file": {"filename": data["filename"], "file_data": data["data_url"]},
            }
        else:
            attachment = {"type": "image_url", "image_url": {"url": data["data_url"]}}
        metadata = {"requested_model": self.model, "unstable_router": self.model == "openrouter/free"}
        try:
            response = OpenAI(api_key=self.api_key, base_url=self.base_url).chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": DOCUMENT_EXTRACTION_PROMPT}, attachment,
                ]}],
                response_format={"type": "json_schema", "json_schema": DOCUMENT_RESPONSE_SCHEMA},
                extra_body={"provider": {"require_parameters": True}},
            )
            choices = getattr(response, "choices", None) or []
            if not choices:
                raise DocumentProviderError("empty_choices", metadata=_response_metadata(response, requested_model=self.model))
            message = getattr(choices[0], "message", None)
            raw = getattr(message, "content", None)
            metadata = _response_metadata(response, requested_model=self.model, content=raw)
            if raw is None:
                raise DocumentProviderError("null_content", metadata=metadata)
            if not isinstance(raw, str) or not raw.strip():
                raise DocumentProviderError("null_content", detail="empty_content", metadata=metadata)
            try:
                parsed = parse_provider_json(raw)
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                raise DocumentProviderError("json_decode_error", detail=exc.__class__.__name__, metadata=metadata) from exc
            try:
                result = _validate_shape(parsed)
            except DocumentProviderError as exc:
                exc.metadata = metadata
                raise
            result = attach_provider_metadata(
                result, provider=self.name, model=metadata["actual_model"] or self.model, upload_data=data,
            )
            result["_provider_metadata"].update(metadata)
            return result
        except DocumentProviderError as exc:
            if not exc.provider:
                exc.provider = self.name
            if not exc.model:
                exc.model = self.model
            if not exc.metadata:
                exc.metadata = metadata
            raise
        except (APIConnectionError, TimeoutError) as exc:
            raise DocumentProviderError(
                "provider_timeout", detail=exc.__class__.__name__, provider=self.name,
                model=self.model, metadata=metadata,
            ) from exc
        except APIStatusError as exc:
            status_code = getattr(exc, "status_code", None)
            raise DocumentProviderError(
                "provider_http_error", detail=str(status_code or exc.__class__.__name__),
                provider=self.name, model=self.model,
                metadata={**metadata, "http_status": status_code},
            ) from exc
        except Exception as exc:
            raise DocumentProviderError(
                "provider_error", detail=exc.__class__.__name__, provider=self.name,
                model=self.model, metadata=metadata,
            ) from exc
