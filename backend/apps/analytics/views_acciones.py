from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Constructora, EvidenciaObra, LoteForestal, Obra, RegistroEmision
from .models_acciones import AccionAmbiental

VALID_STATUSES = {"pendiente", "en_progreso", "validacion", "completada"}
ACTIVE_STATUSES = {"pendiente", "en_progreso", "validacion"}


def serialize_link(action):
    if action.obra_id:
        return {
            "type": "obra",
            "id": action.obra.codigo_obra,
            "label": action.obra.nombre or action.obra.codigo_obra,
        }
    if action.lote_forestal_id:
        return {
            "type": "lote_forestal",
            "id": action.lote_forestal.lote_id,
            "label": action.lote_forestal.lote_id,
        }
    if action.evidencia_id:
        return {
            "type": "evidencia",
            "id": action.evidencia_id,
            "label": action.evidencia.nombre,
        }
    if action.registro_emision_id:
        return {
            "type": "registro_emision",
            "id": action.registro_emision_id,
            "label": action.registro_emision.fuente_emision,
        }
    return None


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
        "obraCodigo": action.obra.codigo_obra if action.obra_id else "",
        "loteId": action.lote_forestal.lote_id if action.lote_forestal_id else "",
        "registroId": action.registro_emision_id or "",
        "evidenciaId": action.evidencia_id or "",
        "linkedTo": serialize_link(action),
        "metadata": action.metadata if isinstance(action.metadata, dict) else {},
        "createdAt": action.created_at.isoformat() if action.created_at else "",
        "updatedAt": action.updated_at.isoformat() if action.updated_at else "",
    }


def resolve_links(constructora, data, current=None):
    current = current or {}
    obra_codigo = data.get("obraCodigo") or data.get("codigo_obra") or data.get("obra") or current.get("obraCodigo")
    lote_id = data.get("loteId") or data.get("lote_id") or data.get("lote") or current.get("loteId")
    registro_id = data.get("registroId") or data.get("registro_emision_id") or current.get("registroId")
    evidencia_id = data.get("evidenciaId") or data.get("evidencia_id") or current.get("evidenciaId")

    links = {
        "obra": None,
        "lote_forestal": None,
        "registro_emision": None,
        "evidencia": None,
    }

    if obra_codigo:
        links["obra"] = Obra.objects.filter(
            constructora=constructora,
            codigo_obra=str(obra_codigo).strip(),
        ).first()
    if lote_id:
        links["lote_forestal"] = LoteForestal.objects.filter(
            constructora=constructora,
            lote_id=str(lote_id).strip(),
        ).first()
    if registro_id:
        links["registro_emision"] = RegistroEmision.objects.filter(
            constructora=constructora,
            id=registro_id,
        ).first()
    if evidencia_id:
        links["evidencia"] = EvidenciaObra.objects.filter(
            constructora=constructora,
            id=evidencia_id,
        ).first()

    return links


def normalize_payload(data, constructora, current=None):
    current = current or {}
    status_value = data.get("status", current.get("status", "pendiente"))
    if status_value not in VALID_STATUSES:
        status_value = "pendiente"

    title = data.get("title", data.get("titulo", current.get("title", "Acción ambiental")))
    description = data.get("description", data.get("descripcion", current.get("description", "")))
    responsible = data.get("responsible", data.get("responsable", current.get("responsible", "Equipo ambiental")))
    due_date = data.get("dueDate", data.get("due_date", current.get("dueDate") or current.get("due_date")))
    metadata = data.get("metadata", current.get("metadata", {}))
    links = resolve_links(constructora, data, current=current)

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
        **links,
    }


def action_queryset(constructora):
    return (
        AccionAmbiental.objects
        .filter(constructora=constructora)
        .select_related("obra", "lote_forestal", "registro_emision", "evidencia")
    )


@api_view(["GET"])
def constructora_acciones_ambientales_resumen(request, constructora_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)
    today = timezone.localdate()
    soon_limit = today + timezone.timedelta(days=7)
    actions = AccionAmbiental.objects.filter(constructora=constructora)

    by_status = {
        row["status"]: row["total"]
        for row in actions.values("status").annotate(total=Count("id"))
    }
    total = actions.count()
    completed = by_status.get("completada", 0)
    active = sum(by_status.get(status_value, 0) for status_value in ACTIVE_STATUSES)
    linked = actions.filter(
        Q(obra__isnull=False)
        | Q(lote_forestal__isnull=False)
        | Q(registro_emision__isnull=False)
        | Q(evidencia__isnull=False)
    ).count()
    due_soon = actions.filter(
        status__in=ACTIVE_STATUSES,
        due_date__isnull=False,
        due_date__lte=soon_limit,
    ).count()
    overdue = actions.filter(
        status__in=ACTIVE_STATUSES,
        due_date__isnull=False,
        due_date__lt=today,
    ).count()
    traceability_pct = round((linked / total) * 100, 1) if total else 0
    completion_pct = round((completed / total) * 100, 1) if total else 0

    latest_actions = action_queryset(constructora).order_by("-updated_at", "-id")[:5]

    return Response({
        "total": total,
        "active": active,
        "completed": completed,
        "dueSoon": due_soon,
        "overdue": overdue,
        "linked": linked,
        "unlinked": max(total - linked, 0),
        "traceabilityPct": traceability_pct,
        "completionPct": completion_pct,
        "byStatus": {
            "pendiente": by_status.get("pendiente", 0),
            "en_progreso": by_status.get("en_progreso", 0),
            "validacion": by_status.get("validacion", 0),
            "completada": completed,
        },
        "latestActions": [serialize_action(action) for action in latest_actions],
    })


@api_view(["GET", "POST"])
def constructora_acciones_ambientales(request, constructora_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)

    if request.method == "GET":
        actions = action_queryset(constructora).order_by("-created_at", "-id")
        return Response([serialize_action(action) for action in actions])

    payload = normalize_payload(request.data, constructora=constructora)
    action = AccionAmbiental.objects.create(constructora=constructora, **payload)
    action = action_queryset(constructora).get(pk=action.pk)
    return Response(serialize_action(action), status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
def constructora_accion_ambiental_detail(request, constructora_id, action_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)
    action = get_object_or_404(
        action_queryset(constructora),
        id=action_id,
        constructora=constructora,
    )

    if request.method == "DELETE":
        action.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    current = serialize_action(action)
    payload = normalize_payload(request.data, constructora=constructora, current=current)
    for field, value in payload.items():
        setattr(action, field, value)
    action.save()

    action = action_queryset(constructora).get(pk=action.pk)
    return Response(serialize_action(action))
