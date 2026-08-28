from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (
    AccionMejoraAmbiental,
    ComandoCopiloto,
    HitoDecisionIA,
    MemoriaOrganizacion,
    RestriccionContextual,
)
from .intervention_v2 import escalate_problem, select_action
from ..policies.intelligence import validate_command_execution


def prepare_action(proposal):
    return ComandoCopiloto.objects.create(
        organizacion=proposal.problematica.organizacion,
        problematica=proposal.problematica,
        propuesta=proposal,
        tipo="prepare_action",
        payload={
            "titulo": proposal.titulo or proposal.accion,
            "descripcion": proposal.descripcion or proposal.accion,
            "justificacion": proposal.justificacion,
        },
    )


def prepare_reevaluation(problem, action):
    if action.problematica_id != problem.id:
        raise ValidationError("La accion pertenece a otra problematica.")
    return ComandoCopiloto.objects.create(
        organizacion=problem.organizacion,
        problematica=problem,
        tipo="prepare_reevaluation",
        payload={"accion": action.id},
    )


def prepare_restriction(problem, payload):
    return ComandoCopiloto.objects.create(
        organizacion=problem.organizacion,
        problematica=problem,
        tipo="prepare_restriction",
        payload=payload,
    )


def prepare_escalation(problem, reason):
    return ComandoCopiloto.objects.create(
        organizacion=problem.organizacion,
        problematica=problem,
        tipo="prepare_escalation",
        payload={"motivo": reason},
    )


@transaction.atomic
def confirm_command(command, user, *, confirmed=False):
    validate_command_execution(command, confirmed=confirmed, user=user)
    if command.tipo == ComandoCopiloto.Tipo.ACCION:
        action = AccionMejoraAmbiental.objects.create(
            problematica=command.problematica, estado="propuesta", **command.payload
        )
        select_action(action, user=user)
        result = {"accion": action.id, "ciclo": action.ciclos_reevaluacion.get().numero}
        command.propuesta.estado = "convertida_en_accion"
        command.propuesta.save(update_fields=["estado"])
        MemoriaOrganizacion.objects.create(
            organizacion=command.organizacion,
            problematica=command.problematica,
            tipo="accion_aceptada",
            contenido=result,
            fuente_origen="confirmacion_copiloto",
        )
    elif command.tipo == ComandoCopiloto.Tipo.REEVALUACION:
        action = command.problematica.acciones.get(id=command.payload["accion"])
        cycle = select_action(action, user=user)
        result = {"ciclo": cycle.numero, "accion": action.id}
    elif command.tipo == ComandoCopiloto.Tipo.RESTRICCION:
        restriction = RestriccionContextual.objects.create(
            organizacion=command.organizacion,
            problematica=command.problematica,
            created_by=user,
            **command.payload,
        )
        result = {"restriccion": restriction.id}
    elif command.tipo == ComandoCopiloto.Tipo.ESCALAMIENTO:
        problem = escalate_problem(
            command.problematica, command.payload.get("motivo", ""), user
        )
        result = {"problematica": problem.id, "estado": problem.estado}
    else:
        raise ValidationError("Tipo de comando no soportado.")
    command.estado = "confirmado"
    command.confirmado_por = user
    command.confirmed_at = timezone.now()
    command.save(update_fields=["estado", "confirmado_por", "confirmed_at"])
    HitoDecisionIA.objects.create(
        organizacion=command.organizacion,
        problematica=command.problematica,
        propuesta=command.propuesta,
        tipo="decision_humana",
        resumen=f"Comando {command.tipo} confirmado por usuario.",
        payload_auditable=result,
        usuario=user,
    )
    return result
