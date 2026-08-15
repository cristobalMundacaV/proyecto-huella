from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import CasoConocimientoAmbiental, Organizacion, ResultadoIntervencion, UsuarioOrganizacion
from .serializers_knowledge_v1 import CasoConocimientoPrivadoSerializer
from .services.knowledge_v1 import aggregate_knowledge, create_knowledge_case


def _organization(request, value):
    organization = get_object_or_404(Organizacion, organizacion_id=value)
    allowed = request.user.is_authenticated and (request.user.is_superuser or UsuarioOrganizacion.objects.filter(user=request.user, organizacion=organization, activo=True).exists())
    return organization if allowed else None


@api_view(["GET", "POST"])
def knowledge_cases(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    if request.method == "GET":
        rows = organization.casos_conocimiento.select_related("resultado_origen").order_by("-created_at")
        return Response(CasoConocimientoPrivadoSerializer(rows, many=True).data)
    result = get_object_or_404(ResultadoIntervencion, problematica__organizacion=organization, id=request.data.get("intervencion"))
    try:
        case, created = create_knowledge_case(result, organization, request.data.get("origen", "usuario"))
    except ValidationError as exc:
        return Response({"detail": exc.messages}, status=400)
    return Response(CasoConocimientoPrivadoSerializer(case).data, status=201 if created else 200)


@api_view(["GET"])
def knowledge_case_detail(request, organizacion_id, case_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    case = get_object_or_404(CasoConocimientoAmbiental, organizacion=organization, id=case_id)
    return Response(CasoConocimientoPrivadoSerializer(case).data)


@api_view(["GET"])
def knowledge_aggregate(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    allowed = {key: request.query_params.get(key) for key in ("preset", "categoria_ambiental", "tipo_problematica", "tipo_accion", "resultado", "fuerza_minima") if request.query_params.get(key)}
    return Response(aggregate_knowledge(**allowed))
