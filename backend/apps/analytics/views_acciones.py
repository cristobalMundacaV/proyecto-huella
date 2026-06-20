from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Constructora
from .models_acciones import AccionAmbiental

VALID_STATUSES = {"pendiente", "en_progreso", "validacion", "completada"}


def serialize_action(action):
    return {
        "id": action.id,
        "title": action.title,
        "description": action.description or "",
        "responsible": action.responsible or "Equipo ambiental",
        "dueDate": action.due_date.isoformat() if action.due_date else "",
        "status": action.status or "pendiente",
        "source": action.source or "",
        "evidence": action.evidence or "",
        "trackingKpi": action.tracking_kpi or "",
        "sourceCardId": action.source_card_id or "",
        "metadata": action.metadata if isinstance(action.metadata, dict) else {},
        "createdAt": action.created_at.isoformat() if action.created_at else "",
        "updatedAt": action.updated_at.isoformat() if action.updated_at else "",
    }


def normalize_payload(data, current=None):
    current = current or {}
    status_value = data.get("status", current.get("status", "pendiente"))
    if status_value not in VALID_STATUSES:
        status_value = "pendiente"

    title = data.get("title", data.get("titulo", current.get("title", "Acción ambiental")))
    description = data.get("description", data.get("descripcion", current.get("description", "")))
    responsible = data.get("responsible", data.get("responsable", current.get("responsible", "Equipo ambiental")))
    due_date = data.get("dueDate", data.get("due_date", current.get("dueDate") or current.get("due_date")))
    metadata = data.get("metadata", current.get("metadata", {}))

    return {
        "title": str(title or "Acción ambiental").strip()[:180],
        "description": description or "",
        "responsible": str(responsible or "Equipo ambiental")[:160],
        "due_date": due_date or None,
        "status": status_value,
        "source": str(data.get("source", data.get("origen", current.get("source", ""))) or "")[:160],
        "evidence": str(data.get("evidence", data.get("evidencia", current.get("evidence", ""))) or "")[:220],
        "tracking_kpi": str(data.get("trackingKpi", data.get("tracking_kpi", current.get("trackingKpi", current.get("tracking_kpi", "")))) or "")[:180],
        "source_card_id": str(data.get("sourceCardId", data.get("source_card_id", current.get("sourceCardId", current.get("source_card_id", "")))) or "")[:120],
        "metadata": metadata if isinstance(metadata, dict) else {},
    }


@api_view(["GET", "POST"])
def constructora_acciones_ambientales(request, constructora_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)

    if request.method == "GET":
        actions = AccionAmbiental.objects.filter(constructora=constructora).order_by("-created_at", "-id")
        return Response([serialize_action(action) for action in actions])

    payload = normalize_payload(request.data)
    action = AccionAmbiental.objects.create(constructora=constructora, **payload)
    return Response(serialize_action(action), status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
def constructora_accion_ambiental_detail(request, constructora_id, action_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)
    action = get_object_or_404(AccionAmbiental, id=action_id, constructora=constructora)

    if request.method == "DELETE":
        action.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    current = serialize_action(action)
    payload = normalize_payload(request.data, current=current)
    for field, value in payload.items():
        setattr(action, field, value)
    action.save()

    return Response(serialize_action(action))
