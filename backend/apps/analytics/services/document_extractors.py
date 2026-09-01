import logging
import mimetypes
from pathlib import Path
from typing import Protocol

from .document_claim_normalization import normalize_provider_claims
from .document_claims import DocumentClaims, safe_document_claims
from .document_provider import DocumentProviderConfigurationError, DocumentProviderError
from .document_provider_registry import get_document_ai_provider

logger = logging.getLogger(__name__)


def _provider_name(provider):
    name = getattr(provider, "name", "")
    return name if isinstance(name, str) and name else provider.__class__.__name__


def _provider_model(provider):
    model = getattr(provider, "model", "")
    return model if isinstance(model, str) else ""


class DocumentExtractor(Protocol):
    def extract(self, upload, *, text="", heuristic=None) -> DocumentClaims: ...


class TextHeuristicExtractor:
    origin = "texto_heuristico"

    def extract(self, upload, *, text="", heuristic=None):
        raw = heuristic(text) if heuristic else {}
        claims, trace = normalize_provider_claims(raw.get("claims") or {}, self.origin)
        for item in trace.values():
            if item["confianza"] is None:
                item["confianza"] = raw.get("confianza")
        has_result = bool(claims) or raw.get("relevancia_detectada") == "no_pertinente"
        return DocumentClaims(
            tipo_documento=raw.get("tipo_documento") or "otro",
            relevancia_detectada=raw.get("relevancia_detectada") or ("parcialmente_pertinente" if text else "indeterminado"),
            confianza=float(raw.get("confianza") or 0),
            texto_extraido=text or "",
            claims=claims,
            claims_trazables=trace,
            origen_extraccion=self.origin,
            motivo_relevancia=raw.get("motivo_relevancia") or "",
            execution_status="success" if has_result else "empty",
            extractor_used=self.__class__.__name__,
            provider_used="deterministic",
            failure_code="" if has_result else "no_claims_detected",
            claims_count=len(claims),
        )


class VisualAIExtractor:
    def __init__(self, provider=None):
        self.configuration_error = None
        if provider is not None:
            self.provider = provider
            return
        try:
            self.provider = get_document_ai_provider()
        except DocumentProviderConfigurationError as exc:
            self.provider = None
            self.configuration_error = exc

    def extract(self, upload, *, text="", heuristic=None):
        if self.configuration_error:
            return safe_document_claims(
                origin="visual_no_disponible",
                status="unavailable" if self.configuration_error.code.startswith("missing_") else "failed",
                extractor=self.__class__.__name__,
                provider=self.configuration_error.provider or "not_configured",
                model=self.configuration_error.model,
                failure_code=self.configuration_error.code,
            )
        try:
            raw = self.provider.extract_visual(upload)
        except DocumentProviderError as exc:
            status = "unavailable" if exc.code == "missing_api_key" else (
                "unsupported" if exc.code == "unsupported_mime" else (
                    "empty" if exc.code == "empty_file" else "failed"
                )
            )
            logger.warning(
                "Document provider extraction did not complete",
                extra={"failure_code": exc.code, "provider": _provider_name(self.provider), "detail": exc.detail},
            )
            return safe_document_claims(
                origin="visual_no_disponible",
                status=status,
                extractor=self.__class__.__name__,
                provider=exc.provider or _provider_name(self.provider),
                model=exc.model or _provider_model(self.provider),
                failure_code=exc.code,
                metadata={
                    **dict(exc.metadata or {}),
                    **({"provider_attempts": exc.attempts} if exc.attempts else {}),
                    "failure_detail": exc.detail,
                },
            )
        except Exception as exc:
            logger.exception("Unexpected visual document extraction failure")
            return safe_document_claims(
                origin="visual_no_disponible",
                status="failed",
                extractor=self.__class__.__name__,
                provider=_provider_name(self.provider),
                model=_provider_model(self.provider),
                failure_code="provider_error",
                metadata={"exception_type": exc.__class__.__name__},
            )
        if not isinstance(raw, dict):
            return safe_document_claims(
                origin="visual_no_disponible", status="failed",
                extractor=self.__class__.__name__, provider=_provider_name(self.provider),
                model=_provider_model(self.provider),
                failure_code="invalid_provider_response",
            )
        provider_metadata = raw.get("_provider_metadata") or {}
        provider_used = provider_metadata.get("provider") or _provider_name(self.provider)
        model_used = provider_metadata.get("model") or _provider_model(self.provider)
        origin = f"{provider_used}_visual"
        claims, trace = normalize_provider_claims(raw.get("claims") or {}, origin)
        relevance = raw.get("relevancia_detectada") or "indeterminado"
        has_result = bool(claims) or relevance == "no_pertinente"
        return DocumentClaims(
            tipo_documento=raw.get("tipo_documento") or "otro",
            relevancia_detectada=relevance,
            confianza=float(raw.get("confianza_clasificacion") or raw.get("confianza") or 0),
            texto_extraido=text or "",
            claims=claims,
            claims_trazables=trace,
            origen_extraccion=origin,
            motivo_relevancia=raw.get("motivo_relevancia") or "",
            legibilidad=raw.get("legibilidad") or "",
            confianza_extraccion=raw.get("confianza_extraccion"),
            execution_status="success" if has_result else "empty",
            extractor_used=self.__class__.__name__,
            provider_used=provider_used,
            model_used=model_used,
            failure_code="" if has_result else "no_claims_detected",
            claims_count=len(claims),
            extraction_metadata=provider_metadata,
        )


def select_document_extractor(*, upload, text, provider=None):
    if text:
        return TextHeuristicExtractor()
    filename = getattr(upload, "name", "") or ""
    content_type = getattr(upload, "content_type", "") or mimetypes.guess_type(filename)[0] or ""
    extension = Path(filename).suffix.lower()
    if content_type.startswith("image/") or content_type == "application/pdf" or extension == ".pdf":
        return VisualAIExtractor(provider=provider)
    return None
