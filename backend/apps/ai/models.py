"""AI-INTELLIGENCE-01 — conversation persistence.

Every conversation belongs to exactly one organization, one user and
(optionally) one obra — never resolved implicitly, always set at creation
and never changed afterwards. Messages are append-only: a conversation's
history is never silently rewritten, matching this project's "Operational
Truth" principle applied to the chat itself. Nothing here ever stores an
API key, a secret, or the model's internal chain-of-thought — only the
final visible content, the structured tool calls/results, and minimal
accounting metadata.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from apps.analytics.models.operational_context import Obra
from apps.analytics.models.platform import Organizacion


class Conversation(models.Model):
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="ai_conversations")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_conversations")
    obra = models.ForeignKey(Obra, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_conversations")
    titulo = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["organizacion", "usuario", "-updated_at"])]
        ordering = ["-updated_at"]

    def clean(self):
        if self.obra_id and self.obra.organizacion_id != self.organizacion_id:
            raise ValidationError({"obra": "La obra debe pertenecer a la misma organización de la conversación."})


class MessageQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Los mensajes de una conversación son de solo lectura una vez creados.")

    def delete(self):
        raise ValidationError("Los mensajes de una conversación son de solo lectura una vez creados.")


class Message(models.Model):
    class Role(models.TextChoices):
        SYSTEM = "system", "Sistema"
        USER = "user", "Usuario"
        ASSISTANT = "assistant", "Asistente"
        TOOL = "tool", "Herramienta"

    objects = MessageQuerySet.as_manager()

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField(blank=True)
    # Tool calls the assistant requested for this turn: [{"id","name","arguments"}].
    tool_calls = models.JSONField(default=list, blank=True, encoder=DjangoJSONEncoder)
    # Only set on role=TOOL messages: which tool this result answers.
    tool_name = models.CharField(max_length=80, blank=True)
    tool_call_id = models.CharField(max_length=80, blank=True)
    # Minimized structured tool output (never the raw upstream/DB row).
    # DjangoJSONEncoder is required here: tool results carry real Decimal
    # (GWP totals, factor values) and date/datetime values from the
    # underlying services — the plain json encoder cannot serialize those.
    tool_result = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    # Structured "fuentes utilizadas" attached to an assistant's final answer.
    provenance = models.JSONField(default=list, blank=True, encoder=DjangoJSONEncoder)
    model = models.CharField(max_length=120, blank=True)
    tokens_input = models.PositiveIntegerField(null=True, blank=True)
    tokens_output = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Los mensajes de una conversación son de solo lectura una vez creados.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Los mensajes de una conversación son de solo lectura una vez creados.")
