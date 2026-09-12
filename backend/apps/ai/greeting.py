"""AI-INTELLIGENCE-01 — the standard opening greeting.

Shown the first time a conversation is opened. Never calls the LLM — it is
a fixed, versioned string, so opening the chat has zero cost and zero
latency and never fails even if the provider is disabled or misconfigured.
"""
from .models import Message

GREETING_TEXT = (
    "Hola, soy el asistente de inteligencia ambiental de Carbono Zero. "
    "Puedo ayudarte a analizar la información de tus obras, indicadores, "
    "materiales, evidencias y oportunidades de mejora. ¿En qué puedo ayudarte?"
)


def ensure_greeting(conversation):
    if conversation.messages.exists():
        return conversation.messages.first()
    return Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content=GREETING_TEXT)
