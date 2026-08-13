from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Organizacion
from .services.environmental_decision_action_service import (
    DecisionPriorityNotFound,
    build_action_payload_from_priority,
    create_action_from_priority,
    find_priority,
)


@api_view(["GET"])
def environmental_decision_action_preview(request, organizacion_id, priority_id):
    organizacion = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    try:
        payload = build_action_payload_from_priority(organizacion, priority_id)
        return Response({"payload": payload, "source_priority": find_priority(organizacion, priority_id)})
    except DecisionPriorityNotFound:
        return Response({"error": "Decision ambiental priorizada no encontrada."}, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return Response(
            {"error": "No se pudo preparar la accion ambiental sugerida."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def environmental_decision_create_action(request, organizacion_id, priority_id):
    organizacion = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    overrides = {
        "responsible": request.data.get("responsible", ""),
        "due_date": request.data.get("due_date") or request.data.get("dueDate") or "",
        "required_evidence": request.data.get("required_evidence") or request.data.get("evidence") or "",
        "notes": request.data.get("notes", ""),
    }
    try:
        result = create_action_from_priority(
            organizacion,
            priority_id,
            user=request.user,
            overrides=overrides,
        )
        response_status = status.HTTP_200_OK if result.get("duplicate") else status.HTTP_201_CREATED
        return Response(result, status=response_status)
    except DecisionPriorityNotFound:
        return Response({"error": "Decision ambiental priorizada no encontrada."}, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return Response(
            {"error": "No se pudo crear la accion ambiental desde la decision."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
