from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .selectors.transport import (
    journey_for_organization,
    journeys_for_organization,
    routes_for_organization,
    work_for_organization,
)
from .selectors.environmental_flows import organization_available_to_user
from .serializers_transport_v2 import (
    RutaOperacionalSerializer,
    ViajeOperacionalSerializer,
)
from .services.transport_v2 import transport_indicators


def _organization(request, value):
    return organization_available_to_user(request.user, value)


def _requested_work(request, organization):
    work_id = request.query_params.get("obra")
    if not work_id:
        return None
    work = work_for_organization(organization, work_id).first()
    if not work:
        raise Http404("Recurso no encontrado.")
    return work


@api_view(["GET", "POST"])
def routes(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization}
    if request.method == "GET":
        return Response(
            RutaOperacionalSerializer(
                routes_for_organization(organization), many=True, context=context
            ).data
        )
    serializer = RutaOperacionalSerializer(data=request.data, context=context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "POST"])
def journeys(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization}
    work = _requested_work(request, organization)
    rows = journeys_for_organization(organization, work)
    if request.method == "GET":
        return Response(
            ViajeOperacionalSerializer(rows, many=True, context=context).data
        )
    serializer = ViajeOperacionalSerializer(data=request.data, context=context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "PATCH"])
def journey_detail(request, organizacion_id, journey_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    journey = get_object_or_404(journey_for_organization(organization, journey_id))
    context = {"organizacion": organization}
    if request.method == "GET":
        return Response(ViajeOperacionalSerializer(journey, context=context).data)
    serializer = ViajeOperacionalSerializer(
        journey, data=request.data, partial=True, context=context
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def journey_indicators(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    work = _requested_work(request, organization)
    return Response(
        transport_indicators(
            organization,
            request.query_params.get("desde"),
            request.query_params.get("hasta"),
            work=work,
        )
    )
