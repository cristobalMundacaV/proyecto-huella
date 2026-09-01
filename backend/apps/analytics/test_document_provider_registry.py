import json
import httpx
from pathlib import Path
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from openai import APIConnectionError, APIStatusError

from .services.document_extractors import VisualAIExtractor
from .services.document_provider import DocumentProviderConfigurationError, DocumentProviderError
from .services.document_provider_registry import get_document_ai_provider
from .services.openai_document_provider import OpenAIDocumentProvider
from .services.openrouter_document_provider import OpenRouterDocumentProvider


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


PROVIDER_RESULT = {
    "tipo_documento": "factura_combustible",
    "relevancia_detectada": "pertinente",
    "motivo_relevancia": "Factura legible.",
    "confianza_clasificacion": 0.97,
    "legibilidad": "legible",
    "confianza_extraccion": 0.96,
    "claims": {
        "tipo_recurso": {"valor_original": "Diésel Grado B", "confianza": 0.98},
        "cantidad": {"valor_original": "250,00", "confianza": 0.99},
        "unidad": {"valor_original": "L", "confianza": 0.99},
        "fecha": {"valor_original": "06-09-2026", "confianza": 0.98},
    },
}


def upload():
    return SimpleUploadedFile("factura.png", PNG_BYTES, content_type="image/png")


def openrouter_response(content, *, choices=True, model="google/gemini-2.5-flash", finish_reason="stop"):
    items = [Mock(message=Mock(content=content), finish_reason=finish_reason)] if choices else []
    return Mock(id="gen-test", model=model, choices=items)


class DocumentProviderRegistryTests(SimpleTestCase):
    @override_settings(DOCUMENT_AI_PROVIDER="openai", DOCUMENT_AI_MODEL="gpt-test", OPENAI_API_KEY="key", DOCUMENT_AI_FALLBACK_PROVIDER="")
    def test_selecciona_openai_por_configuracion(self):
        provider = get_document_ai_provider()
        self.assertIsInstance(provider, OpenAIDocumentProvider)
        self.assertEqual(provider.model, "gpt-test")

    @override_settings(DOCUMENT_AI_PROVIDER="openrouter", DOCUMENT_AI_MODEL="openrouter/free", OPENROUTER_API_KEY="key", DOCUMENT_AI_FALLBACK_PROVIDER="")
    def test_selecciona_openrouter_por_configuracion(self):
        provider = get_document_ai_provider()
        self.assertIsInstance(provider, OpenRouterDocumentProvider)
        self.assertEqual(provider.model, "openrouter/free")

    @override_settings(DOCUMENT_AI_PROVIDER="openrouter", DOCUMENT_AI_MODEL="openrouter/free", OPENROUTER_API_KEY="", DOCUMENT_AI_FALLBACK_PROVIDER="")
    def test_key_ausente_es_unavailable_y_no_inventa_claims(self):
        result = VisualAIExtractor().extract(upload())
        self.assertEqual(result.execution_status, "unavailable")
        self.assertEqual(result.failure_code, "missing_api_key")
        self.assertEqual(result.provider_used, "openrouter")
        self.assertEqual(result.model_used, "openrouter/free")
        self.assertEqual(result.claims, {})

    @override_settings(DOCUMENT_AI_PROVIDER="desconocido", DOCUMENT_AI_MODEL="modelo", DOCUMENT_AI_FALLBACK_PROVIDER="")
    def test_proveedor_invalido_entrega_error_de_configuracion_claro(self):
        with self.assertRaises(DocumentProviderConfigurationError) as raised:
            get_document_ai_provider()
        self.assertEqual(raised.exception.code, "invalid_provider_configuration")
        result = VisualAIExtractor().extract(upload())
        self.assertEqual(result.execution_status, "failed")
        self.assertEqual(result.failure_code, "invalid_provider_configuration")

    def test_openai_y_openrouter_producen_el_mismo_document_claims(self):
        openai_client = Mock()
        openai_client.responses.create.return_value = Mock(output_text=json.dumps(PROVIDER_RESULT))
        with override_settings(DOCUMENT_AI_PROVIDER="openai", DOCUMENT_AI_MODEL="gpt-test", OPENAI_API_KEY="key", DOCUMENT_AI_FALLBACK_PROVIDER=""), patch(
            "apps.analytics.services.openai_document_provider.OpenAI", return_value=openai_client
        ):
            openai_claims = VisualAIExtractor().extract(upload())

        openrouter_client = Mock()
        openrouter_client.chat.completions.create.return_value = openrouter_response(json.dumps(PROVIDER_RESULT))
        with override_settings(DOCUMENT_AI_PROVIDER="openrouter", DOCUMENT_AI_MODEL="openrouter/free", OPENROUTER_API_KEY="key", DOCUMENT_AI_FALLBACK_PROVIDER=""), patch(
            "apps.analytics.services.openrouter_document_provider.OpenAI", return_value=openrouter_client
        ):
            openrouter_claims = VisualAIExtractor().extract(upload())

        for field in ("tipo_documento", "relevancia_detectada", "confianza", "claims", "claims_count", "execution_status"):
            self.assertEqual(getattr(openai_claims, field), getattr(openrouter_claims, field))
        self.assertEqual(openai_claims.provider_used, "openai")
        self.assertEqual(openrouter_claims.provider_used, "openrouter")
        request = openrouter_client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["response_format"]["type"], "json_schema")
        self.assertTrue(request["response_format"]["json_schema"]["strict"])
        self.assertEqual(
            request["response_format"]["json_schema"]["schema"]["properties"]["relevancia_detectada"]["enum"],
            ["pertinente", "parcialmente_pertinente", "no_pertinente", "indeterminado"],
        )
        self.assertEqual(request["extra_body"], {"provider": {"require_parameters": True}})
        self.assertEqual(request["messages"][0]["content"][1]["type"], "image_url")
        self.assertTrue(request["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,"))

    @override_settings(
        DOCUMENT_AI_PROVIDER="openai", DOCUMENT_AI_MODEL="gpt-test", OPENAI_API_KEY="",
        DOCUMENT_AI_FALLBACK_PROVIDER="openrouter", DOCUMENT_AI_FALLBACK_MODEL="openrouter/free", OPENROUTER_API_KEY="key",
    )
    @patch("apps.analytics.services.openrouter_document_provider.OpenAI")
    def test_fallback_se_usa_solo_cuando_esta_configurado(self, openrouter_sdk):
        client = Mock()
        client.chat.completions.create.return_value = openrouter_response(json.dumps(PROVIDER_RESULT))
        openrouter_sdk.return_value = client

        result = VisualAIExtractor().extract(upload())

        self.assertEqual(result.execution_status, "success")
        self.assertEqual(result.provider_used, "openrouter")
        self.assertEqual(result.model_used, "google/gemini-2.5-flash")
        self.assertTrue(result.extraction_metadata["fallback_used"])
        self.assertEqual(result.extraction_metadata["provider_attempts"][0]["failure_code"], "missing_api_key")

    @override_settings(DOCUMENT_AI_PROVIDER="openai", DOCUMENT_AI_MODEL="gpt-test", OPENAI_API_KEY="", DOCUMENT_AI_FALLBACK_PROVIDER="")
    @patch("apps.analytics.services.openrouter_document_provider.OpenAI")
    def test_no_hay_fallback_implicito(self, openrouter_sdk):
        result = VisualAIExtractor().extract(upload())
        self.assertEqual(result.execution_status, "unavailable")
        openrouter_sdk.assert_not_called()

    def _provider_failure(self, response=None, side_effect=None):
        client = Mock()
        if side_effect is not None:
            client.chat.completions.create.side_effect = side_effect
        else:
            client.chat.completions.create.return_value = response
        with patch("apps.analytics.services.openrouter_document_provider.OpenAI", return_value=client):
            with self.assertRaises(DocumentProviderError) as raised:
                OpenRouterDocumentProvider(api_key="key", model="openrouter/free").extract_visual(upload())
        return raised.exception

    def test_openrouter_persiste_modelo_solicitado_y_modelo_real(self):
        client = Mock()
        client.chat.completions.create.return_value = openrouter_response(json.dumps(PROVIDER_RESULT))
        with patch("apps.analytics.services.openrouter_document_provider.OpenAI", return_value=client):
            result = OpenRouterDocumentProvider(api_key="key", model="openrouter/free").extract_visual(upload())
        metadata = result["_provider_metadata"]
        self.assertEqual(metadata["requested_model"], "openrouter/free")
        self.assertEqual(metadata["actual_model"], "google/gemini-2.5-flash")
        self.assertEqual(metadata["response_id"], "gen-test")
        self.assertEqual(metadata["finish_reason"], "stop")
        self.assertEqual(metadata["choices_count"], 1)
        self.assertEqual(metadata["content_type"], "str")
        self.assertTrue(metadata["unstable_router"])

    def test_openrouter_distingue_respuestas_invalidas(self):
        cases = [
            (openrouter_response(json.dumps({**PROVIDER_RESULT, "relevancia_detectada": "relevante"})), "invalid_relevance"),
            (openrouter_response(json.dumps({**PROVIDER_RESULT, "claims": None})), "invalid_claims_type"),
            (openrouter_response(json.dumps({**PROVIDER_RESULT, "claims": []})), "invalid_claims_type"),
            (openrouter_response("{invalid"), "json_decode_error"),
            (openrouter_response(""), "null_content"),
            (openrouter_response(None), "null_content"),
            (openrouter_response("[]"), "invalid_root"),
            (openrouter_response("ignored", choices=False), "empty_choices"),
            (openrouter_response(json.dumps({**PROVIDER_RESULT, "confianza_clasificacion": "alta"})), "invalid_confidence"),
        ]
        for response, code in cases:
            with self.subTest(code=code):
                self.assertEqual(self._provider_failure(response=response).code, code)

    def test_openrouter_distingue_timeout(self):
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(
            self._provider_failure(side_effect=APIConnectionError(request=request)).code,
            "provider_timeout",
        )

    def test_openrouter_distingue_error_http(self):
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        response = httpx.Response(422, request=request)
        error = APIStatusError("unprocessable", response=response, body={"error": {"message": "sanitized"}})
        raised = self._provider_failure(side_effect=error)
        self.assertEqual(raised.code, "provider_http_error")
        self.assertEqual(raised.metadata["http_status"], 422)

    def test_motor_ambiental_y_extractor_no_importan_sdks_especificos(self):
        services = Path(__file__).parent / "services"
        for name in (
            "document_extractors.py", "document_provider.py", "evidence_validation.py",
            "quality_v2.py", "eligibility_v2.py", "calculation_v2.py",
        ):
            source = (services / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("from openai", source)
            self.assertNotIn("import openai", source)
            self.assertNotIn("openrouter_document_provider", source)
            self.assertNotIn("openai_document_provider", source)
