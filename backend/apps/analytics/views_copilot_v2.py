from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.iot.models import DispositivoSensor

from .models import (
    ActivoOperacional,
    EvidenciaObra,
    IndicadorAmbiental,
    Organizacion,
    ProblematicaAmbiental,
)
from .selectors.intelligence import (
    copilot_command,
    owned_resource,
    problem_proposals,
    proposal_for_problem,
    user_can_access_organization,
)
from .policies.intelligence import require_human_confirmation
from .services.context_gateway import ContextGateway
from .services.copilot_commands import confirm_command, prepare_action
from .services.copilot_v2 import default_copilot_service


def _can_access(user, organization):
    return user_can_access_organization(user, organization)


def _owned(request, model, pk):
    item = get_object_or_404(owned_resource(model, pk))
    return item if _can_access(request.user, item.organizacion) else None


def _problem(request, pk):
    item = get_object_or_404(owned_resource(ProblematicaAmbiental, pk))
    return item if _can_access(request.user, item.organizacion) else None


def _proposal(row):
    return {
        "id": row.id,
        "problematica": row.problematica_id,
        "titulo": row.titulo or row.accion,
        "descripcion": row.descripcion,
        "justificacion": row.justificacion,
        "kpis_afectados": row.kpis_afectados,
        "requisitos": row.requisitos,
        "riesgos": row.riesgos,
        "restricciones_consideradas": row.restricciones_consideradas,
        "referencias_contexto": row.referencias_contexto,
        "diagnostico": row.diagnostico,
        "prioridad": row.prioridad,
        "estado": row.estado,
        "version": row.version,
        "propuesta_anterior": row.propuesta_anterior_id,
        "proveedor": row.proveedor,
        "modelo": row.modelo,
        "created_at": row.created_at,
    }


def _not_found():
    return Response({"detail": "Recurso no encontrado."}, status=404)


@api_view(["GET"])
def context_problem(request, problem_id):
    problem = _problem(request, problem_id)
    return (
        Response(ContextGateway().problem(problem, problem.organizacion))
        if problem
        else _not_found()
    )


@api_view(["GET"])
def context_asset(request, asset_id):
    asset = _owned(request, ActivoOperacional, asset_id)
    return (
        Response(ContextGateway().asset(asset, asset.organizacion))
        if asset
        else _not_found()
    )


@api_view(["GET"])
def context_asset_maintenance(request, asset_id):
    asset = _owned(request, ActivoOperacional, asset_id)
    return (
        Response(ContextGateway().asset_maintenance(asset, asset.organizacion))
        if asset
        else _not_found()
    )


@api_view(["GET"])
def context_sensor_health(request, sensor_id):
    sensor = _owned(request, DispositivoSensor, sensor_id)
    if sensor:
        sensor = DispositivoSensor.objects.select_related(
            "organizacion", "activo_operacional"
        ).get(pk=sensor.pk)
    return (
        Response(ContextGateway().sensor_health(sensor, sensor.organizacion))
        if sensor
        else _not_found()
    )


@api_view(["GET"])
def context_indicator_history(request, indicator_id):
    indicator = _owned(request, IndicadorAmbiental, indicator_id)
    return (
        Response(ContextGateway().indicator_history(indicator, indicator.organizacion))
        if indicator
        else _not_found()
    )


@api_view(["GET"])
def context_evidence(request, evidence_id):
    evidence = _owned(request, EvidenciaObra, evidence_id)
    return (
        Response(ContextGateway().evidence(evidence, evidence.organizacion))
        if evidence
        else _not_found()
    )


@api_view(["GET"])
def context_organization_memory(request, organization_id):
    organization = get_object_or_404(Organizacion, organizacion_id=organization_id)
    return (
        Response(ContextGateway().organization_memory(organization))
        if _can_access(request.user, organization)
        else _not_found()
    )


@api_view(["GET", "POST"])
def agent_problem_proposals(request, problem_id):
    problem = _problem(request, problem_id)
    if not problem:
        return _not_found()
    if request.method == "GET":
        return Response([_proposal(row) for row in problem_proposals(problem)])
    try:
        proposal = default_copilot_service().propose(
            problem,
            request.data.get("mensaje", ""),
            request.user,
            context_categories=request.data.get("referencias_contextuales", []),
        )
        return Response(_proposal(proposal), status=201)
    except ValidationError as exc:
        return Response({"detail": exc.messages}, status=400)
    except Exception:
        return Response(
            {
                "detail": "El copiloto no esta disponible; el dominio ambiental continua operativo."
            },
            status=503,
        )


@api_view(["POST"])
def agent_proposal_feedback(request, problem_id, proposal_id):
    problem = _problem(request, problem_id)
    if not problem:
        return _not_found()
    proposal = get_object_or_404(proposal_for_problem(problem, proposal_id))
    decision = request.data.get("decision")
    if decision == "aceptar":
        proposal.estado = "aceptada"
        proposal.save(update_fields=["estado"])
        command = prepare_action(proposal)
        return Response(
            {
                "propuesta": _proposal(proposal),
                "comando": command.id,
                "requiere_confirmacion": True,
            }
        )
    if decision in {"rechazar", "descartar"}:
        proposal.estado = "rechazada" if decision == "rechazar" else "descartada"
        proposal.save(update_fields=["estado"])
        return Response(_proposal(proposal))
    if decision in {"refutar", "alternativa"}:
        try:
            restriction, adjusted = default_copilot_service().refute(
                proposal, request.data.get("mensaje", ""), request.user
            )
            return Response(
                {
                    "restriccion": restriction.id,
                    "propuesta_anterior": _proposal(proposal),
                    "propuesta_ajustada": _proposal(adjusted),
                },
                status=201,
            )
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=400)
        except Exception:
            return Response(
                {
                    "detail": "La restriccion fue conservada, pero el proveedor no genero una alternativa."
                },
                status=503,
            )
    return Response({"decision": ["Decision invalida."]}, status=400)


@api_view(["POST"])
def agent_reevaluation_draft(request, problem_id):
    problem = _problem(request, problem_id)
    if not problem:
        return _not_found()
    try:
        proposal = default_copilot_service().propose(
            problem,
            request.data.get("mensaje", "Preparar alternativa para reevaluacion."),
            request.user,
            context_categories=["intervention"],
        )
        return Response(
            {
                "propuesta": _proposal(proposal),
                "ciclo_iniciado": False,
                "requiere_confirmacion": True,
            },
            status=201,
        )
    except ValidationError as exc:
        return Response({"detail": exc.messages}, status=400)
    except Exception:
        return Response(
            {"detail": "El copiloto no esta disponible; no se inicio ningun ciclo."},
            status=503,
        )


@api_view(["POST"])
def confirm_copilot_command(request, command_id):
    command = get_object_or_404(
        copilot_command(command_id),
    )
    if not _can_access(request.user, command.organizacion):
        return _not_found()
    try:
        require_human_confirmation(request.data.get("confirmado"))
    except ValidationError:
        return Response(
            {"confirmado": ["Se requiere confirmacion humana explicita."]}, status=400
        )
    try:
        return Response(confirm_command(command, request.user), status=201)
    except ValidationError as exc:
        return Response({"detail": exc.messages}, status=400)
