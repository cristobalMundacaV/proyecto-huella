from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.analytics.models_acciones import AccionAmbiental
from apps.analytics.services.environmental_decision_priority_service import build_environmental_decision_priorities
from apps.analytics.views_acciones import serialize_action


ACTIVE_STATUSES = {"pendiente", "en_progreso", "validacion"}


class DecisionPriorityNotFound(ValueError):
    pass


def build_action_payload_from_priority(constructora, priority_id, overrides=None):
    priority = find_priority(constructora, priority_id)
    overrides = overrides or {}
    due_date = overrides.get("due_date") or overrides.get("dueDate") or suggested_due_date(priority)
    evidence = overrides.get("required_evidence") or overrides.get("evidence") or evidence_from_priority(priority)
    notes = overrides.get("notes") or ""
    description = build_action_description(priority, evidence, notes)

    return {
        "title": str(overrides.get("title") or priority["title"])[:180],
        "description": description,
        "responsible": str(overrides.get("responsible") or "Equipo ambiental")[:160],
        "due_date": due_date,
        "status": AccionAmbiental.Estado.PENDIENTE,
        "source": "Decision ambiental priorizada",
        "evidence": str(evidence or "Evidencia ambiental trazable")[:220],
        "tracking_kpi": tracking_kpi_for_priority(priority),
        "source_card_id": priority["id"][:120],
        "metadata": {
            "origin": "environmental_decision_priority",
            "priority_id": priority["id"],
            "priority": priority.get("priority"),
            "area": priority.get("area"),
            "decision_type": priority.get("decision_type"),
            "score": priority.get("score"),
            "related_recommendation_id": priority.get("related_recommendation_id", ""),
            "related_scenario_id": priority.get("related_scenario_id", ""),
            "expected_impact": priority.get("expected_impact", {}),
        },
    }


def create_action_from_priority(constructora, priority_id, user=None, overrides=None):
    priority = find_priority(constructora, priority_id)
    payload = build_action_payload(priority, overrides)
    duplicate = find_duplicate_action(constructora, priority_id, payload["title"])
    if duplicate:
        return {
            "created": False,
            "duplicate": True,
            "action": serialize_action(duplicate),
            "source_priority": priority,
            "message": "Ya existe una accion abierta asociada a esta decision.",
        }

    metadata = dict(payload.get("metadata") or {})
    if user and getattr(user, "is_authenticated", False):
        metadata["created_by"] = getattr(user, "username", "")
    action = AccionAmbiental.objects.create(constructora=constructora, **{**payload, "metadata": metadata})
    return {
        "created": True,
        "duplicate": False,
        "action": serialize_action(action),
        "source_priority": priority,
    }


def find_priority(constructora, priority_id):
    priorities = build_environmental_decision_priorities(constructora)
    for priority in priorities.get("priorities", []):
        if priority.get("id") == priority_id:
            return priority
    raise DecisionPriorityNotFound("Decision ambiental priorizada no encontrada.")


def build_action_payload(priority, overrides=None):
    overrides = overrides or {}
    due_date = overrides.get("due_date") or overrides.get("dueDate") or suggested_due_date(priority)
    evidence = overrides.get("required_evidence") or overrides.get("evidence") or evidence_from_priority(priority)
    notes = overrides.get("notes") or ""
    return {
        "title": str(overrides.get("title") or priority["title"])[:180],
        "description": build_action_description(priority, evidence, notes),
        "responsible": str(overrides.get("responsible") or "Equipo ambiental")[:160],
        "due_date": due_date,
        "status": AccionAmbiental.Estado.PENDIENTE,
        "source": "Decision ambiental priorizada",
        "evidence": str(evidence or "Evidencia ambiental trazable")[:220],
        "tracking_kpi": tracking_kpi_for_priority(priority),
        "source_card_id": priority["id"][:120],
        "metadata": {
            "origin": "environmental_decision_priority",
            "priority_id": priority["id"],
            "priority": priority.get("priority"),
            "area": priority.get("area"),
            "decision_type": priority.get("decision_type"),
            "score": priority.get("score"),
            "related_recommendation_id": priority.get("related_recommendation_id", ""),
            "related_scenario_id": priority.get("related_scenario_id", ""),
            "expected_impact": priority.get("expected_impact", {}),
        },
    }


def find_duplicate_action(constructora, priority_id, title):
    return (
        AccionAmbiental.objects.filter(constructora=constructora, status__in=ACTIVE_STATUSES)
        .filter(
            Q(metadata__priority_id=priority_id)
            | Q(source_card_id=priority_id[:120])
            | Q(description__icontains=f"Priority ID: {priority_id}")
            | Q(title__iexact=title)
        )
        .order_by("-created_at")
        .first()
    )


def build_action_description(priority, evidence, notes):
    impact = priority.get("expected_impact") or {}
    impact_text = "; ".join(
        item
        for item in [
            value_text("kgCO2e", impact.get("kg_co2e")),
            value_text("tCO2e", impact.get("tco2e")),
            value_text("% reduccion", impact.get("pct")),
            value_text("reduccion riesgo", impact.get("risk_reduction")),
        ]
        if item
    ) or "Requiere datos para cuantificar impacto."
    evidence_text = evidence or "Evidencia ambiental trazable."
    notes_text = f"\n\nObservaciones:\n{notes}" if notes else ""
    return (
        f"Decision priorizada:\n{priority.get('title')}\n\n"
        f"Por que ahora:\n{priority.get('why_now')}\n\n"
        f"Base tecnica:\n{priority.get('technical_basis')}\n\n"
        f"Impacto esperado:\n{impact_text}\n\n"
        f"Siguiente paso:\n{priority.get('next_step')}\n\n"
        f"Evidencia requerida:\n{evidence_text}\n\n"
        "Origen:\nDecision ambiental priorizada generada por Carbono Zero.\n\n"
        f"Priority ID: {priority.get('id')}"
        f"{notes_text}"
    )


def evidence_from_priority(priority):
    if priority.get("evidence"):
        return priority["evidence"][0][:220]
    if priority.get("area") == "documental":
        return "Documento ambiental validado y trazable."
    return "Registro operacional, evidencia documental y verificacion tecnica."


def suggested_due_date(priority):
    days = {"critica": 7, "alta": 14, "media": 30, "baja": 45}.get(priority.get("priority"), 30)
    return (timezone.localdate() + timedelta(days=days)).isoformat()


def tracking_kpi_for_priority(priority):
    area = priority.get("area") or "cumplimiento"
    if priority.get("decision_type") == "reducir_huella":
        return f"reduccion kgCO2e - {area}"[:180]
    if priority.get("decision_type") == "cumplimiento":
        return f"cierre de riesgo regulatorio - {area}"[:180]
    return f"avance accion ambiental - {area}"[:180]


def value_text(label, value):
    if value is None or value == "":
        return ""
    return f"{label}: {value}"
