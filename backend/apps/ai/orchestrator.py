"""AI-INTELLIGENCE-01 — orchestration layer.

Flow: user question -> load bounded conversation history -> LLM decides
which tool(s) it needs -> backend executes only permitted, tenant-checked
tools -> structured results are fed back -> LLM produces the final answer.
The model never touches the database directly and — enforced by
`system_prompt.SYSTEM_PROMPT` plus the simple fact that tools are the ONLY
source of data in its context — never invents a result a tool did not
provide.
"""
import json
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.analytics.policies.intelligence import IntelligenceOperation, validate_ai_operation

from .models import Conversation, Message
from .providers import AIProviderError
from .system_prompt import SYSTEM_PROMPT_VERSION, build_messages
from .tools import execute_tool, openai_tool_schemas

MAX_HISTORY_MESSAGES = 20


class OrchestratorError(Exception):
    def __init__(self, code, *, detail=""):
        super().__init__(code)
        self.code = code
        self.detail = detail


def _requests_this_hour(organization):
    since = timezone.now() - timedelta(hours=1)
    return Message.objects.filter(
        conversation__organizacion=organization, role=Message.Role.ASSISTANT, created_at__gte=since,
    ).count()


def enforce_cost_controls(conversation, organization):
    if conversation.messages.count() >= settings.AI_MAX_MESSAGES_PER_CONVERSATION:
        raise OrchestratorError("conversation_limit_reached",
                                detail=f"Máximo {settings.AI_MAX_MESSAGES_PER_CONVERSATION} mensajes por conversación.")
    if _requests_this_hour(organization) >= settings.AI_MAX_REQUESTS_PER_ORG_PER_HOUR:
        raise OrchestratorError("rate_limit_reached",
                                detail=f"Máximo {settings.AI_MAX_REQUESTS_PER_ORG_PER_HOUR} solicitudes por hora para esta organización.")


def _load_history_for_prompt(conversation):
    """Only replays user/assistant *content* from past turns — tool
    round-trips are turn-local and never replayed (each tool message must
    immediately follow the exact assistant tool_calls message that requested
    it; replaying that pairing across turns is unnecessary complexity this
    macrophase does not need)."""
    rows = list(
        conversation.messages.filter(role__in=[Message.Role.USER, Message.Role.ASSISTANT])
        .exclude(content="")
        .order_by("-created_at")[:MAX_HISTORY_MESSAGES]
    )
    rows.reverse()
    return [{"role": row.role, "content": row.content} for row in rows]


def _provider_error_message(exc):
    messages = {
        "provider_disabled": "El asistente de inteligencia ambiental no está habilitado en este entorno.",
        "missing_api_key": "El asistente no está configurado (falta credencial del proveedor).",
        "missing_model": "El asistente no tiene un modelo configurado.",
        "network_error": "No se pudo conectar con el proveedor de IA. Intenta nuevamente.",
        "rate_limited": "El proveedor de IA está temporalmente saturado. Intenta en unos segundos.",
        "authentication_failed": "El proveedor de IA rechazó la credencial configurada.",
        "upstream_error": "El proveedor de IA no pudo procesar la solicitud.",
        "empty_response": "El proveedor de IA no devolvió una respuesta.",
        "provider_error": "Ocurrió un error inesperado con el proveedor de IA.",
    }
    return messages.get(exc.code, "Ocurrió un error con el asistente de IA.")


def run_turn(*, conversation, organization, user, user_message, provider):
    """Persists `user_message`, runs the tool-calling loop, persists every
    tool round-trip and the final assistant message, and returns it."""
    validate_ai_operation(IntelligenceOperation.READ_CONTEXT)
    enforce_cost_controls(conversation, organization)

    Message.objects.create(conversation=conversation, role=Message.Role.USER, content=user_message[:4000])

    history = _load_history_for_prompt(conversation)
    messages = build_messages(history=history)
    tools = openai_tool_schemas()
    provenance = []
    total_input_tokens = 0
    total_output_tokens = 0

    if not provider.available:
        content = _provider_error_message(AIProviderError("provider_disabled"))
        return Message.objects.create(
            conversation=conversation, role=Message.Role.ASSISTANT, content=content,
            model=provider.model, provenance=[],
        )

    for _ in range(settings.AI_MAX_TOOL_ITERATIONS):
        try:
            result = provider.chat(messages=messages, tools=tools)
        except AIProviderError as exc:
            return Message.objects.create(
                conversation=conversation, role=Message.Role.ASSISTANT,
                content=_provider_error_message(exc), model=provider.model, provenance=provenance,
            )

        total_input_tokens += result.tokens_input or 0
        total_output_tokens += result.tokens_output or 0

        if not result.tool_calls:
            return Message.objects.create(
                conversation=conversation, role=Message.Role.ASSISTANT,
                content=result.content or "", model=result.model or provider.model,
                tokens_input=total_input_tokens or None, tokens_output=total_output_tokens or None,
                provenance=provenance,
            )

        assistant_tool_calls = [
            {"id": call.id, "name": call.name, "arguments": call.arguments} for call in result.tool_calls
        ]
        Message.objects.create(
            conversation=conversation, role=Message.Role.ASSISTANT, content=result.content or "",
            tool_calls=assistant_tool_calls, model=result.model or provider.model,
        )
        messages.append({
            "role": "assistant", "content": result.content,
            "tool_calls": [
                {"id": call.id, "type": "function",
                 "function": {"name": call.name, "arguments": _dumps(call.arguments)}}
                for call in result.tool_calls
            ],
        })

        for call in result.tool_calls:
            tool_result = execute_tool(call.name, organization=organization, user=user, arguments=call.arguments)
            Message.objects.create(
                conversation=conversation, role=Message.Role.TOOL, tool_name=call.name,
                tool_call_id=call.id, tool_result=tool_result,
            )
            messages.append({"role": "tool", "tool_call_id": call.id, "content": _dumps(tool_result)})
            if tool_result.get("ok"):
                provenance.append({"tool": call.name, "arguments": call.arguments})

    # Exhausted the iteration budget without a final answer — never let the
    # model keep chaining tool calls unboundedly (cost control).
    return Message.objects.create(
        conversation=conversation, role=Message.Role.ASSISTANT,
        content="No pude completar la consulta dentro del límite de pasos permitidos. "
                "Intenta reformular la pregunta de forma más específica.",
        model=provider.model, tokens_input=total_input_tokens or None,
        tokens_output=total_output_tokens or None, provenance=provenance,
    )


def _dumps(value):
    return json.dumps(value, default=str, ensure_ascii=False)


def get_or_create_conversation(*, organization, user, obra=None, conversation_id=None):
    if conversation_id:
        conversation = Conversation.objects.filter(pk=conversation_id, organizacion=organization, usuario=user).first()
        if conversation is not None:
            return conversation
    conversation = Conversation(organizacion=organization, usuario=user, obra=obra)
    conversation.full_clean()
    conversation.save()
    return conversation
