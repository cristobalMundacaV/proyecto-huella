import json

from django.db import connection
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Constructora

VALID_STATUSES = {"pendiente", "en_progreso", "validacion", "completada"}
TABLE_NAME = "analytics_accionambiental"


def parse_metadata(value):
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def serialize_action(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"] or "",
        "responsible": row["responsible"] or "Equipo ambiental",
        "dueDate": row["due_date"].isoformat() if row.get("due_date") else "",
        "status": row["status"] or "pendiente",
        "source": row["source"] or "",
        "evidence": row["evidence"] or "",
        "trackingKpi": row["tracking_kpi"] or "",
        "sourceCardId": row["source_card_id"] or "",
        "metadata": parse_metadata(row.get("metadata")),
        "createdAt": row["created_at"].isoformat() if row.get("created_at") else "",
        "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else "",
    }


def dict_fetchall(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_action_or_404(constructora, action_id):
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT * FROM {TABLE_NAME} WHERE id = %s AND constructora_id = %s",
            [action_id, constructora.id],
        )
        rows = dict_fetchall(cursor)
    return rows[0] if rows else None


def normalize_payload(data):
    status_value = data.get("status") or "pendiente"
    if status_value not in VALID_STATUSES:
        status_value = "pendiente"

    title = (data.get("title") or data.get("titulo") or "Acción ambiental").strip()
    description = data.get("description") or data.get("descripcion") or ""
    responsible = data.get("responsible") or data.get("responsable") or "Equipo ambiental"
    due_date = data.get("dueDate") or data.get("due_date") or None

    return {
        "title": title[:180],
        "description": description,
        "responsible": responsible[:160],
        "due_date": due_date or None,
        "status": status_value,
        "source": (data.get("source") or data.get("origen") or "")[:160],
        "evidence": (data.get("evidence") or data.get("evidencia") or "")[:220],
        "tracking_kpi": (data.get("trackingKpi") or data.get("tracking_kpi") or "")[:180],
        "source_card_id": (data.get("sourceCardId") or data.get("source_card_id") or "")[:120],
        "metadata": data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
    }


@api_view(["GET", "POST"])
def constructora_acciones_ambientales(request, constructora_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)

    if request.method == "GET":
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE constructora_id = %s ORDER BY created_at DESC, id DESC",
                [constructora.id],
            )
            rows = dict_fetchall(cursor)
        return Response([serialize_action(row) for row in rows])

    payload = normalize_payload(request.data)
    now = timezone.now()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {TABLE_NAME}
            (constructora_id, title, description, responsible, due_date, status, source, evidence,
             tracking_kpi, source_card_id, metadata, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            [
                constructora.id,
                payload["title"],
                payload["description"],
                payload["responsible"],
                payload["due_date"],
                payload["status"],
                payload["source"],
                payload["evidence"],
                payload["tracking_kpi"],
                payload["source_card_id"],
                json.dumps(payload["metadata"]),
                now,
                now,
            ],
        )
        row = dict_fetchall(cursor)[0]

    return Response(serialize_action(row), status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
def constructora_accion_ambiental_detail(request, constructora_id, action_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)
    current = get_action_or_404(constructora, action_id)
    if not current:
        return Response({"error": "Acción ambiental no encontrada."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        with connection.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM {TABLE_NAME} WHERE id = %s AND constructora_id = %s",
                [action_id, constructora.id],
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    payload = normalize_payload({**current, **request.data})
    now = timezone.now()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE {TABLE_NAME}
            SET title = %s,
                description = %s,
                responsible = %s,
                due_date = %s,
                status = %s,
                source = %s,
                evidence = %s,
                tracking_kpi = %s,
                source_card_id = %s,
                metadata = %s,
                updated_at = %s
            WHERE id = %s AND constructora_id = %s
            RETURNING *
            """,
            [
                payload["title"],
                payload["description"],
                payload["responsible"],
                payload["due_date"],
                payload["status"],
                payload["source"],
                payload["evidence"],
                payload["tracking_kpi"],
                payload["source_card_id"],
                json.dumps(payload["metadata"]),
                now,
                action_id,
                constructora.id,
            ],
        )
        row = dict_fetchall(cursor)[0]

    return Response(serialize_action(row))
