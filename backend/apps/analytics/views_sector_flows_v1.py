from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (Organizacion, PuntoAmbientalOperacional,
                     RegistroFlujoAmbiental, UsuarioOrganizacion)
from .serializers_sector_flows_v1 import (PuntoAmbientalSerializer,
                                          RegistroFlujoAmbientalSerializer)
from .services.sector_flows_v1 import sector_summary


def _organization(request, value):
    organization = get_object_or_404(Organizacion, organizacion_id=value)
    allowed = request.user.is_authenticated and (request.user.is_superuser or UsuarioOrganizacion.objects.filter(user=request.user, organizacion=organization, activo=True).exists())
    return organization if allowed else None


@api_view(["GET", "POST"])
def environmental_points(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    rows = organization.puntos_ambientales.select_related("activo", "unidad_operacional", "proceso_operacional", "obra")
    if request.query_params.get("tipo"): rows = rows.filter(tipo=request.query_params["tipo"])
    if request.method == "GET": return Response(PuntoAmbientalSerializer(rows, many=True, context=context).data)
    serializer = PuntoAmbientalSerializer(data=request.data, context=context); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "POST"])
def sector_records(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    rows = organization.registros_flujos_ambientales.select_related("actividad", "punto", "unidad_operacional", "proceso", "activo", "obra", "evento_material").prefetch_related("actividad__observaciones__fuente", "actividad__observaciones__evidencia", "actividad__observaciones__version_evidencia")
    for parameter, field in (("flujo", "flujo"), ("obra", "obra_id"), ("proceso", "proceso_id"), ("activo", "activo_id"), ("punto", "punto_id")):
        if request.query_params.get(parameter): rows = rows.filter(**{field: request.query_params[parameter]})
    if request.method == "GET": return Response(RegistroFlujoAmbientalSerializer(rows, many=True, context=context).data)
    serializer = RegistroFlujoAmbientalSerializer(data=request.data, context=context); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "PATCH"])
def sector_record_detail(request, organizacion_id, record_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    record = get_object_or_404(RegistroFlujoAmbiental, organizacion=organization, id=record_id)
    context = {"organizacion": organization, "request": request}
    if request.method == "GET": return Response(RegistroFlujoAmbientalSerializer(record, context=context).data)
    serializer = RegistroFlujoAmbientalSerializer(record, data=request.data, partial=True, context=context); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def sector_indicators(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    filters = {key: request.query_params.get(key) for key in ("flow", "start", "end") if request.query_params.get(key)}
    return Response(sector_summary(organization, **filters))
