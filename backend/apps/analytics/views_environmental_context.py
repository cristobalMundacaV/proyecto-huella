from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import MaterialConstruccion, Organizacion, ProblematicaAmbiental, UsuarioOrganizacion
from .services.environmental_agent import default_agent_service
from .services.environmental_context import (
    evidence_summary, material_lifecycle, normative_context, organization_context,
    organization_kpis, previous_actions, problem_context, problem_history, problem_sources,
)


def _can_access(user, organization):
    return user.is_authenticated and (user.is_superuser or UsuarioOrganizacion.objects.filter(user=user, organizacion=organization, activo=True, organizacion__activa=True).exists())


def _problem_for_user(request, problem_id):
    problem = get_object_or_404(ProblematicaAmbiental.objects.select_related("organizacion"), pk=problem_id)
    if not _can_access(request.user, problem.organizacion):
        return None
    return problem


def _protected_problem_response(request, problem_id, builder):
    problem = _problem_for_user(request, problem_id)
    return Response(builder(problem)) if problem else Response({"error": "Problema no encontrado."}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
def organization_context_view(request, organizacion_id):
    return Response(organization_context(get_object_or_404(Organizacion, organizacion_id=organizacion_id)))


@api_view(["GET"])
def organization_kpis_view(request, organizacion_id):
    return Response(organization_kpis(get_object_or_404(Organizacion, organizacion_id=organizacion_id)))


@api_view(["GET"])
def problem_context_view(request, problem_id):
    return _protected_problem_response(request, problem_id, problem_context)


@api_view(["GET"])
def problem_history_view(request, problem_id):
    return _protected_problem_response(request, problem_id, problem_history)


@api_view(["GET"])
def problem_sources_view(request, problem_id):
    return _protected_problem_response(request, problem_id, problem_sources)


@api_view(["GET"])
def problem_actions_view(request, problem_id):
    return _protected_problem_response(request, problem_id, previous_actions)


@api_view(["GET"])
def problem_evidence_view(request, problem_id):
    return _protected_problem_response(request, problem_id, evidence_summary)


@api_view(["GET"])
def problem_normative_view(request, problem_id):
    return _protected_problem_response(request, problem_id, normative_context)


@api_view(["GET"])
def material_lifecycle_view(request, material_id):
    organization = get_object_or_404(Organizacion, organizacion_id=request.query_params.get("organizacion_id", ""))
    if not _can_access(request.user, organization):
        return Response({"error": "Material no encontrado."}, status=status.HTTP_404_NOT_FOUND)
    return Response(material_lifecycle(organization, get_object_or_404(MaterialConstruccion, pk=material_id)))


def _serialize_recommendation(row):
    return {"id": row.id, "accion": row.accion, "justificacion": row.justificacion, "indicador_afectado": row.indicador_afectado, "resultado_esperado": row.resultado_esperado, "prioridad": row.prioridad, "periodo_seguimiento": row.periodo_seguimiento, "nivel_confianza": row.nivel_confianza, "diagnostico": row.diagnostico, "contexto_resumen": row.contexto_resumen, "created_at": row.created_at}


@api_view(["GET", "POST"])
def problem_recommendations_view(request, problem_id):
    problem = _problem_for_user(request, problem_id)
    if not problem:
        return Response({"error": "Problema no encontrado."}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response([_serialize_recommendation(row) for row in problem.recomendaciones_agente.all()[:10]])
    try:
        result = default_agent_service().recommend(problem)
        return Response(_serialize_recommendation(result.recommendation), status=status.HTTP_201_CREATED)
    except (ValidationError, ValueError) as exc:
        detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or [str(exc)]
        return Response({"error": detail}, status=status.HTTP_503_SERVICE_UNAVAILABLE if isinstance(exc, ValueError) else status.HTTP_400_BAD_REQUEST)
