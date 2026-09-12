"""AI-INTELLIGENCE-01 — LLM provider abstraction.

`AIProvider` is the minimal interface the orchestrator depends on. Adding a
future provider (a different model host, a local model, ...) means writing
one new class here — the orchestrator, tools and system prompt never change.
This is intentionally a NEW, narrower interface than `apps.analytics.services
.environmental_agent.EnvironmentalAgentProvider`: that one is single-shot
(`generate(system_rules, context) -> dict`), with no message history and no
tool/function calling. Conversational tool-calling needs both, so a parallel
interface is the right amount of reuse here (same spirit — `name`/`model`
attributes, a narrow `generate`-like entry point — without forcing a shape
that does not fit).

The API key never appears in an exception message, a log line, or a
persisted row — only `AIProviderError.code`/`detail` (short, safe strings)
ever leave this module.
"""
import json
from dataclasses import dataclass, field

from django.conf import settings


class AIProviderError(Exception):
    def __init__(self, code, *, detail="", provider="", model=""):
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.provider = provider
        self.model = model


@dataclass
class ToolCallRequest:
    id: str
    name: str
    arguments: dict


@dataclass
class AIChatResult:
    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    model: str = ""
    tokens_input: int | None = None
    tokens_output: int | None = None
    finish_reason: str = ""


class AIProvider:
    """Abstract provider contract. Never called with a raw DB connection or
    credential from outside this module's own constructor."""

    name = "abstract"
    model = ""

    @property
    def available(self):
        raise NotImplementedError

    def chat(self, *, messages, tools=None):
        """`messages`: OpenAI-style role/content (+ tool_call_id/name where
        applicable) list. `tools`: OpenAI-style function-tool schema list, or
        None. Returns an `AIChatResult`. Must never raise anything other than
        `AIProviderError`."""
        raise NotImplementedError


def _parse_tool_calls(message):
    calls = []
    for raw in getattr(message, "tool_calls", None) or []:
        function = getattr(raw, "function", None)
        name = getattr(function, "name", "") if function else ""
        raw_arguments = getattr(function, "arguments", "") if function else ""
        try:
            arguments = json.loads(raw_arguments) if raw_arguments else {}
        except (ValueError, TypeError):
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        calls.append(ToolCallRequest(id=str(getattr(raw, "id", "") or ""), name=str(name or ""), arguments=arguments))
    return calls


class OpenRouterProvider(AIProvider):
    name = "openrouter"

    def __init__(self, *, client=None, model=None):
        self.model = model if model is not None else settings.OPENROUTER_MODEL
        self._client = client
        self._api_key = getattr(settings, "OPENROUTER_API_KEY", "") or ""

    @property
    def available(self):
        return bool(settings.OPENROUTER_ENABLED and self._api_key and self.model)

    def _get_client(self):
        if self._client is not None:
            return self._client
        from openai import OpenAI
        return OpenAI(
            api_key=self._api_key,
            base_url=settings.OPENROUTER_BASE_URL,
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )

    def chat(self, *, messages, tools=None):
        if not settings.OPENROUTER_ENABLED:
            raise AIProviderError("provider_disabled", provider=self.name, model=self.model)
        if not self._api_key:
            raise AIProviderError("missing_api_key", provider=self.name, model=self.model)
        if not self.model:
            raise AIProviderError("missing_model", provider=self.name, model=self.model)

        from openai import APIConnectionError, APIStatusError, APITimeoutError

        client = self._get_client()
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": settings.AI_MAX_OUTPUT_TOKENS,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        attempts = 2
        last_error = None
        for attempt in range(attempts):
            try:
                response = client.chat.completions.create(**kwargs)
                break
            except (APIConnectionError, APITimeoutError) as exc:
                last_error = exc
                if attempt == attempts - 1:
                    raise AIProviderError("network_error", detail=exc.__class__.__name__,
                                          provider=self.name, model=self.model) from None
                continue
            except APIStatusError as exc:
                status = getattr(exc, "status_code", None)
                if status == 429:
                    raise AIProviderError("rate_limited", detail="429", provider=self.name, model=self.model) from None
                if status in (401, 403):
                    raise AIProviderError("authentication_failed", detail=str(status),
                                          provider=self.name, model=self.model) from None
                raise AIProviderError("upstream_error", detail=str(status or "unknown"),
                                      provider=self.name, model=self.model) from None
            except Exception as exc:
                raise AIProviderError("provider_error", detail=exc.__class__.__name__,
                                      provider=self.name, model=self.model) from None
        else:
            raise AIProviderError("network_error", detail=last_error.__class__.__name__ if last_error else "unknown",
                                  provider=self.name, model=self.model)

        choices = getattr(response, "choices", None) or []
        if not choices:
            raise AIProviderError("empty_response", provider=self.name, model=self.model)
        message = choices[0].message
        usage = getattr(response, "usage", None)
        return AIChatResult(
            content=getattr(message, "content", None),
            tool_calls=_parse_tool_calls(message),
            model=str(getattr(response, "model", "") or self.model),
            tokens_input=getattr(usage, "prompt_tokens", None) if usage else None,
            tokens_output=getattr(usage, "completion_tokens", None) if usage else None,
            finish_reason=str(getattr(choices[0], "finish_reason", "") or ""),
        )


def default_provider():
    return OpenRouterProvider()
