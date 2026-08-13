from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models_acciones import AccionAmbiental
from .services.environmental_action_closure_service import (
    attach_evidence_to_action,
    build_action_closure_status,
    close_environmental_action,
)


@api_view(["GET"])
def environmental_action_closure_status(request, action_id):
    action = get_object_or_404(action_queryset(), pk=action_id)
    try:
        return Response(build_action_closure_status(action))
    except Exception:
        return Response(
            {"error": "No se pudo calcular el estado de cierre ambiental."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def environmental_action_attach_evidence(request, action_id):
    action = get_object_or_404(action_queryset(), pk=action_id)
    try:
        return Response(attach_evidence_to_action(action, request.data))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response(
            {"error": "No se pudo vincular evidencia a la accion ambiental."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def environmental_action_close(request, action_id):
    action = get_object_or_404(action_queryset(), pk=action_id)
    try:
        return Response(close_environmental_action(action, request.data))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response(
            {"error": "No se pudo cerrar la accion ambiental."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def action_queryset():
    return AccionAmbiental.objects.select_related("organizacion", "evidencia")
