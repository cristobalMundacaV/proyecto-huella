from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Obra, Organizacion, UsuarioOrganizacion
from .serializers import ObraSerializer
from .services.construction_v1 import (close_environmental_work,
                                       construction_indicators,
                                       construction_materials,
                                       environmental_timeline, work_context)


def _scope(request, organization_id, work_id):
    organization = get_object_or_404(Organizacion, organizacion_id=organization_id)
    allowed = request.user.is_authenticated and (request.user.is_superuser or UsuarioOrganizacion.objects.filter(
        user=request.user, organizacion=organization, activo=True).exists())
    if not allowed:
        return None, None
    return organization, get_object_or_404(Obra, organizacion=organization, id=work_id)


@api_view(["GET", "POST"])
def environmental_work(request, organizacion_id, obra_id):
    organization, work = _scope(request, organizacion_id, obra_id)
    if not work: return Response({"detail": "Recurso no encontrado."}, status=404)
    if request.method == "POST":
        close_environmental_work(work, request.data.get("observaciones", ""))
    payload = ObraSerializer(work).data
    payload.update({"alcance": {"tipo": "obra", "obra_id": work.id}, "contexto": work_context(work)})
    return Response(payload)


@api_view(["GET"])
def work_timeline(request, organizacion_id, obra_id):
    _, work = _scope(request, organizacion_id, obra_id)
    return Response(environmental_timeline(work)) if work else Response({"detail": "Recurso no encontrado."}, status=404)


@api_view(["GET"])
def work_indicators(request, organizacion_id, obra_id):
    _, work = _scope(request, organizacion_id, obra_id)
    return Response(construction_indicators(work)) if work else Response({"detail": "Recurso no encontrado."}, status=404)


@api_view(["GET"])
def work_materials(request, organizacion_id, obra_id):
    _, work = _scope(request, organizacion_id, obra_id)
    return Response(construction_materials(work)) if work else Response({"detail": "Recurso no encontrado."}, status=404)


@api_view(["GET"])
def work_context_view(request, organizacion_id, obra_id):
    _, work = _scope(request, organizacion_id, obra_id)
    return Response(work_context(work)) if work else Response({"detail": "Recurso no encontrado."}, status=404)
