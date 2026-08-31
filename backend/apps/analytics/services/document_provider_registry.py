import logging

from django.conf import settings

from .document_provider import DocumentProviderConfigurationError, DocumentProviderError
from .openai_document_provider import OpenAIDocumentProvider
from .openrouter_document_provider import OpenRouterDocumentProvider

logger = logging.getLogger(__name__)


PROVIDER_REGISTRY = {
    "openai": OpenAIDocumentProvider,
    "openrouter": OpenRouterDocumentProvider,
}


def _configuration(name, *, fallback=False):
    normalized = str(name or "").strip().lower()
    if not normalized:
        raise DocumentProviderConfigurationError(
            "missing_provider_configuration",
            detail="DOCUMENT_AI_PROVIDER" if not fallback else "DOCUMENT_AI_FALLBACK_PROVIDER",
        )
    provider_class = PROVIDER_REGISTRY.get(normalized)
    if not provider_class:
        raise DocumentProviderConfigurationError(
            "invalid_provider_configuration",
            detail=normalized,
            provider=normalized,
        )
    model_setting = "DOCUMENT_AI_FALLBACK_MODEL" if fallback else "DOCUMENT_AI_MODEL"
    model = str(getattr(settings, model_setting, "") or "").strip()
    if fallback and not model:
        model = str(getattr(settings, "DOCUMENT_AI_MODEL", "") or "").strip()
    if not model:
        raise DocumentProviderConfigurationError(
            "missing_model_configuration",
            detail=model_setting,
            provider=normalized,
        )
    key_setting = "OPENAI_API_KEY" if normalized == "openai" else "OPENROUTER_API_KEY"
    return provider_class(api_key=getattr(settings, key_setting, ""), model=model)


class FallbackDocumentProvider:
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback
        self.name = primary.name
        self.model = primary.model

    @property
    def available(self):
        return self.primary.available or self.fallback.available

    def extract_visual(self, upload):
        try:
            return self.primary.extract_visual(upload)
        except DocumentProviderError as primary_error:
            primary_attempt = {
                "provider": self.primary.name,
                "model": self.primary.model,
                "failure_code": primary_error.code,
            }
            logger.warning("Primary document provider failed; explicit fallback will be attempted", extra=primary_attempt)
            try:
                result = self.fallback.extract_visual(upload)
            except DocumentProviderError as fallback_error:
                attempts = [primary_attempt, {
                    "provider": self.fallback.name,
                    "model": self.fallback.model,
                    "failure_code": fallback_error.code,
                }]
                fallback_error.attempts = attempts
                raise
            metadata = result.setdefault("_provider_metadata", {})
            metadata["fallback_used"] = True
            metadata["provider_attempts"] = [primary_attempt, {
                "provider": self.fallback.name,
                "model": self.fallback.model,
                "failure_code": "",
            }]
            return result


def get_document_ai_provider():
    primary = _configuration(getattr(settings, "DOCUMENT_AI_PROVIDER", ""))
    fallback_name = str(getattr(settings, "DOCUMENT_AI_FALLBACK_PROVIDER", "") or "").strip()
    if not fallback_name:
        return primary
    fallback = _configuration(fallback_name, fallback=True)
    if fallback.name == primary.name and fallback.model == primary.model:
        raise DocumentProviderConfigurationError(
            "invalid_fallback_configuration",
            detail="El fallback replica proveedor y modelo primarios.",
            provider=fallback.name,
            model=fallback.model,
        )
    return FallbackDocumentProvider(primary, fallback)
