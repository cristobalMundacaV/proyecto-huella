"""AI-INTELLIGENCE-01 — OpenRouterProvider unit tests. OpenRouter is always
mocked; no real network access happens in this file."""
from unittest.mock import Mock

import httpx
from django.test import SimpleTestCase, override_settings
from openai import APIConnectionError, APIStatusError

from apps.ai.providers import AIProviderError, OpenRouterProvider
from .fixtures import openrouter_response, tool_call


def _mock_client(response=None, side_effect=None):
    client = Mock()
    if side_effect is not None:
        client.chat.completions.create.side_effect = side_effect
    else:
        client.chat.completions.create.return_value = response
    return client

SETTINGS = {
    "OPENROUTER_ENABLED": True, "OPENROUTER_API_KEY": "synthetic-not-a-credential",
    "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1", "OPENROUTER_MODEL": "synthetic/model",
    "AI_REQUEST_TIMEOUT_SECONDS": 30, "AI_MAX_OUTPUT_TOKENS": 1200, "AI_TEMPERATURE": 0.2,
}


@override_settings(**SETTINGS)
class OpenRouterProviderTests(SimpleTestCase):
    def _provider(self, client=None, **overrides):
        provider = OpenRouterProvider(client=client)
        for key, value in overrides.items():
            setattr(provider, key, value)
        return provider

    def test_disabled_provider_never_calls_network(self):
        with override_settings(OPENROUTER_ENABLED=False):
            provider = self._provider(client="should-never-be-used")
            with self.assertRaises(AIProviderError) as ctx:
                provider.chat(messages=[{"role": "user", "content": "hola"}])
            self.assertEqual(ctx.exception.code, "provider_disabled")

    def test_missing_api_key_never_calls_network(self):
        with override_settings(OPENROUTER_API_KEY=""):
            provider = self._provider(client="should-never-be-used")
            with self.assertRaises(AIProviderError) as ctx:
                provider.chat(messages=[{"role": "user", "content": "hola"}])
            self.assertEqual(ctx.exception.code, "missing_api_key")

    def test_missing_model_never_calls_network(self):
        with override_settings(OPENROUTER_MODEL=""):
            provider = self._provider(client="should-never-be-used")
            with self.assertRaises(AIProviderError) as ctx:
                provider.chat(messages=[{"role": "user", "content": "hola"}])
            self.assertEqual(ctx.exception.code, "missing_model")

    def test_available_reflects_full_configuration(self):
        self.assertTrue(self._provider().available)
        with override_settings(OPENROUTER_ENABLED=False):
            self.assertFalse(self._provider().available)
        with override_settings(OPENROUTER_MODEL=""):
            self.assertFalse(self._provider().available)

    def test_successful_plain_text_reply(self):
        client = _mock_client(openrouter_response(content="Hola, ¿en qué puedo ayudarte?"))
        provider = self._provider(client=client)
        result = provider.chat(messages=[{"role": "user", "content": "hola"}])
        self.assertEqual(result.content, "Hola, ¿en qué puedo ayudarte?")
        self.assertEqual(result.tool_calls, [])
        self.assertEqual(result.tokens_input, 10)
        self.assertEqual(result.tokens_output, 5)

    def test_tool_call_is_parsed_with_arguments(self):
        call = tool_call("call_1", "get_current_organization", {})
        client = _mock_client(openrouter_response(content=None, tool_calls=[call]))
        provider = self._provider(client=client)
        result = provider.chat(messages=[{"role": "user", "content": "hola"}], tools=[{"type": "function"}])
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].name, "get_current_organization")
        self.assertEqual(result.tool_calls[0].arguments, {})

    def test_malformed_tool_arguments_never_raise(self):
        call = tool_call("call_1", "get_current_organization", {})
        call.function.arguments = "{not json"
        client = _mock_client(openrouter_response(content=None, tool_calls=[call]))
        provider = self._provider(client=client)
        result = provider.chat(messages=[{"role": "user", "content": "hola"}])
        self.assertEqual(result.tool_calls[0].arguments, {})

    def test_timeout_and_connection_error_become_network_error(self):
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        client = _mock_client(side_effect=APIConnectionError(request=request))
        provider = self._provider(client=client)
        with self.assertRaises(AIProviderError) as ctx:
            provider.chat(messages=[{"role": "user", "content": "hola"}])
        self.assertEqual(ctx.exception.code, "network_error")

    def test_429_becomes_rate_limited(self):
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        response = httpx.Response(429, request=request)
        error = APIStatusError("rate limited", response=response, body={"error": "rate_limited"})
        client = _mock_client(side_effect=error)
        provider = self._provider(client=client)
        with self.assertRaises(AIProviderError) as ctx:
            provider.chat(messages=[{"role": "user", "content": "hola"}])
        self.assertEqual(ctx.exception.code, "rate_limited")

    def test_401_becomes_authentication_failed(self):
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        response = httpx.Response(401, request=request)
        error = APIStatusError("unauthorized", response=response, body={"error": "unauthorized"})
        client = _mock_client(side_effect=error)
        provider = self._provider(client=client)
        with self.assertRaises(AIProviderError) as ctx:
            provider.chat(messages=[{"role": "user", "content": "hola"}])
        self.assertEqual(ctx.exception.code, "authentication_failed")

    def test_invalid_response_shape_never_leaks_raw_error(self):
        client = _mock_client(openrouter_response(content=None, tool_calls=None))
        client.chat.completions.create.return_value.choices = []
        provider = self._provider(client=client)
        with self.assertRaises(AIProviderError) as ctx:
            provider.chat(messages=[{"role": "user", "content": "hola"}])
        self.assertEqual(ctx.exception.code, "empty_response")

    def test_error_never_contains_the_api_key(self):
        request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        client = _mock_client(side_effect=APIConnectionError(request=request))
        provider = self._provider(client=client)
        try:
            provider.chat(messages=[{"role": "user", "content": "hola"}])
        except AIProviderError as exc:
            self.assertNotIn("synthetic-not-a-credential", str(exc))
            self.assertNotIn("synthetic-not-a-credential", exc.detail)

    def test_model_is_configurable_not_hardcoded(self):
        with override_settings(OPENROUTER_MODEL="another/model"):
            provider = OpenRouterProvider()
            self.assertEqual(provider.model, "another/model")
        explicit = OpenRouterProvider(model="explicit/model")
        self.assertEqual(explicit.model, "explicit/model")
