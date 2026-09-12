from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.analytics.permissions import Permission, require_tenant_permission, require_work_access
from apps.analytics.selectors.environmental_flows import organization_available_to_user, work_for_organization

from .greeting import GREETING_TEXT, ensure_greeting
from .models import Conversation, Message
from .orchestrator import OrchestratorError, get_or_create_conversation, run_turn
from .providers import default_provider


def _organization_or_404(request, organizacion_id):
    organization = organization_available_to_user(request.user, organizacion_id)
    if organization is None:
        return None, Response({"detail": "Recurso no encontrado."}, status=404)
    return organization, None


def _message_data(message):
    return {
        "id": message.pk, "role": message.role, "content": message.content,
        "tool_calls": message.tool_calls, "tool_name": message.tool_name,
        "provenance": message.provenance, "model": message.model,
        "created_at": message.created_at,
    }


def _conversation_data(conversation, *, include_messages=True):
    data = {
        "id": conversation.pk, "titulo": conversation.titulo, "obra_id": conversation.obra_id,
        "created_at": conversation.created_at, "updated_at": conversation.updated_at,
    }
    if include_messages:
        visible = conversation.messages.exclude(role=Message.Role.TOOL).exclude(
            role=Message.Role.ASSISTANT, content="",
        )
        data["messages"] = [_message_data(message) for message in visible]
    return data


class CreateConversationInput(serializers.Serializer):
    obra_id = serializers.IntegerField(required=False, allow_null=True)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def conversations(request, organizacion_id):
    organization, error = _organization_or_404(request, organizacion_id)
    if error:
        return error
    require_tenant_permission(request.user, organization, Permission.INTELLIGENCE_CHAT_VIEW)

    if request.method == "GET":
        rows = Conversation.objects.filter(organizacion=organization, usuario=request.user)[:50]
        return Response({"conversaciones": [_conversation_data(row, include_messages=False) for row in rows]})

    serializer = CreateConversationInput(data=request.data)
    serializer.is_valid(raise_exception=True)
    obra = None
    obra_id = serializer.validated_data.get("obra_id")
    if obra_id:
        obra = get_object_or_404(work_for_organization(organization, obra_id))
        require_work_access(request.user, organization, obra)

    conversation = get_or_create_conversation(organization=organization, user=request.user, obra=obra)
    ensure_greeting(conversation)
    return Response(_conversation_data(conversation), status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def conversation_detail(request, organizacion_id, conversation_id):
    organization, error = _organization_or_404(request, organizacion_id)
    if error:
        return error
    require_tenant_permission(request.user, organization, Permission.INTELLIGENCE_CHAT_VIEW)
    conversation = get_object_or_404(Conversation, pk=conversation_id, organizacion=organization, usuario=request.user)
    return Response(_conversation_data(conversation))


class SendMessageInput(serializers.Serializer):
    content = serializers.CharField(max_length=4000, trim_whitespace=True, allow_blank=False)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_message(request, organizacion_id, conversation_id):
    organization, error = _organization_or_404(request, organizacion_id)
    if error:
        return error
    require_tenant_permission(request.user, organization, Permission.INTELLIGENCE_CHAT_VIEW)
    conversation = get_object_or_404(Conversation, pk=conversation_id, organizacion=organization, usuario=request.user)

    serializer = SendMessageInput(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        assistant_message = run_turn(
            conversation=conversation, organization=organization, user=request.user,
            user_message=serializer.validated_data["content"], provider=default_provider(),
        )
    except OrchestratorError as exc:
        status = 429 if exc.code in ("rate_limit_reached", "conversation_limit_reached") else 400
        return Response({"detail": exc.detail or exc.code, "code": exc.code}, status=status)

    conversation.save(update_fields=["updated_at"])
    return Response(_message_data(assistant_message), status=201)
