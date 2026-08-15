from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Organizacion, RutaOperacional, UsuarioOrganizacion, ViajeOperacional
from .serializers_transport_v2 import RutaOperacionalSerializer, ViajeOperacionalSerializer
from .services.transport_v2 import transport_indicators


def _organization(request, value):
    organization = get_object_or_404(Organizacion, organizacion_id=value)
    allowed = request.user.is_authenticated and (request.user.is_superuser or UsuarioOrganizacion.objects.filter(user=request.user, organizacion=organization, activo=True).exists())
    return organization if allowed else None


@api_view(["GET", "POST"])
def routes(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization}
    if request.method == "GET": return Response(RutaOperacionalSerializer(organization.rutas_operacionales.all(), many=True, context=context).data)
    serializer = RutaOperacionalSerializer(data=request.data, context=context); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "POST"])
def journeys(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization}
    rows = organization.viajes_operacionales.select_related("actividad", "vehiculo__activo", "ruta", "observacion_distancia__fuente", "observacion_carga__fuente", "observacion_combustible__fuente")
    if request.method == "GET": return Response(ViajeOperacionalSerializer(rows, many=True, context=context).data)
    serializer = ViajeOperacionalSerializer(data=request.data, context=context); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "PATCH"])
def journey_detail(request, organizacion_id, journey_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    journey = get_object_or_404(ViajeOperacional, organizacion=organization, id=journey_id); context = {"organizacion": organization}
    if request.method == "GET": return Response(ViajeOperacionalSerializer(journey, context=context).data)
    serializer = ViajeOperacionalSerializer(journey, data=request.data, partial=True, context=context); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def journey_indicators(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    return Response(transport_indicators(organization, request.query_params.get("desde"), request.query_params.get("hasta")))
