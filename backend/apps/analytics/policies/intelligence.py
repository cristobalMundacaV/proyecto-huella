from enum import Enum

from django.core.exceptions import ValidationError


class IntelligenceOperation(str, Enum):
    READ_CONTEXT = "read_context"
    SUGGEST = "suggest"
    PREPARE_COMMAND = "prepare_command"
    APPLY_ACTION = "apply_action"
    CALCULATE_ENVIRONMENTAL_TRUTH = "calculate_environmental_truth"
    DECIDE_COMPLIANCE = "decide_compliance"
    VERIFY_IMPROVEMENT = "verify_improvement"
    CLOSE_PROBLEM = "close_problem"


AI_AUTHORITY = {
    IntelligenceOperation.READ_CONTEXT: True,
    IntelligenceOperation.SUGGEST: True,
    IntelligenceOperation.PREPARE_COMMAND: True,
    IntelligenceOperation.APPLY_ACTION: False,
    IntelligenceOperation.CALCULATE_ENVIRONMENTAL_TRUTH: False,
    IntelligenceOperation.DECIDE_COMPLIANCE: False,
    IntelligenceOperation.VERIFY_IMPROVEMENT: False,
    IntelligenceOperation.CLOSE_PROBLEM: False,
}


def validate_ai_operation(operation):
    try:
        operation = IntelligenceOperation(operation)
    except ValueError as exc:
        raise ValidationError("Operación de inteligencia no reconocida.") from exc
    if not AI_AUTHORITY[operation]:
        raise ValidationError(
            "La inteligencia artificial no tiene autoridad para esta operación."
        )


def validate_structured_proposal(payload, *, required_fields, priorities, allowed_kpis):
    if not isinstance(payload, dict) or not required_fields.issubset(payload):
        raise ValidationError(
            "El proveedor no devolvió una propuesta estructurada válida."
        )
    for field in (
        "kpis_afectados",
        "requisitos",
        "riesgos",
        "hechos_utilizados",
        "limitaciones",
        "supuestos",
    ):
        if not isinstance(payload[field], list):
            raise ValidationError({field: "Debe ser una lista."})
    if payload["prioridad"] not in priorities:
        raise ValidationError({"prioridad": "Valor inválido."})
    if not set(payload["kpis_afectados"]).issubset(allowed_kpis):
        raise ValidationError(
            "La propuesta referencia KPIs no asociados a la problemática."
        )


def require_human_confirmation(value, user=None):
    if value is not True or (
        user is not None and not getattr(user, "is_authenticated", False)
    ):
        raise ValidationError(
            {"confirmado": "Se requiere confirmacion humana explicita."}
        )


def validate_command_transition(command):
    if command.estado != command.Estado.PREPARADO:
        raise ValidationError("El comando ya fue procesado.")
    if command.problematica.organizacion_id != command.organizacion_id:
        raise ValidationError("El comando no pertenece al contexto de la problemática.")
    if command.propuesta_id and (
        command.propuesta.problematica_id != command.problematica_id
        or command.propuesta.problematica.organizacion_id != command.organizacion_id
    ):
        raise ValidationError("La propuesta no pertenece al contexto del comando.")


def validate_command_execution(command, *, confirmed, user):
    require_human_confirmation(confirmed, user)
    validate_command_transition(command)
