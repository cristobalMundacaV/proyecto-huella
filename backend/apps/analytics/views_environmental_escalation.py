from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services.environmental_agent import OpenAIEnvironmentalProvider
from .services.environmental_dossier import generate_dossier
from .services.environmental_escalation import apply_escalation, evaluate_escalation
from .views_environmental_context import _problem_for_user


def _serialize_dossier(row):
    return {"id": row.id, "version": row.version, "problematica_id": row.problematica_id, "contenido_procesado": row.contenido_procesado, "resumen_ejecutivo": row.resumen_ejecutivo, "proveedor_resumen": row.proveedor_resumen, "modelo_resumen": row.modelo_resumen, "generado_por": row.generado_por, "created_at": row.created_at}


@api_view(["GET", "POST"])
def problem_escalation_view(request, problem_id):
    problem = _problem_for_user(request, problem_id)
    if not problem:
        return Response({"error": "Problema no encontrado."}, status=status.HTTP_404_NOT_FOUND)
    result = apply_escalation(problem, user=request.user) if request.method == "POST" else evaluate_escalation(problem)
    problem.refresh_from_db()
    return Response({**result, "estado": problem.estado, "escalada_at": problem.escalada_at})


@api_view(["GET", "POST"])
def problem_dossier_view(request, problem_id):
    problem = _problem_for_user(request, problem_id)
    if not problem:
        return Response({"error": "Problema no encontrado."}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response([_serialize_dossier(row) for row in problem.expedientes.all()[:10]])
    try:
        row = generate_dossier(problem, OpenAIEnvironmentalProvider(), user=request.user)
        return Response(_serialize_dossier(row), status=status.HTTP_201_CREATED)
    except (ValidationError, ValueError) as exc:
        detail = getattr(exc, "messages", None) or [str(exc)]
        return Response({"error": detail}, status=status.HTTP_503_SERVICE_UNAVAILABLE if isinstance(exc, ValueError) else status.HTTP_400_BAD_REQUEST)
