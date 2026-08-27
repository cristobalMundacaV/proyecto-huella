from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .selectors.activity_core import (
    activities_for_organization,
    activity_detail,
    activity_for_organization,
    data_source_for_organization,
    data_sources_for_organization,
    observation_for_organization,
    observations_for_activity,
    organization_by_public_id,
)
from .serializers_activity_core import (
    ActividadOperacionalSerializer,
    FuenteDatosSerializer,
    ObservacionSerializer,
)


def _organizacion(organizacion_id):
    return get_object_or_404(organization_by_public_id(organizacion_id))


def _respuesta_coleccion(
    request, organizacion, queryset, serializer_class, context=None
):
    serializer_context = {
        "organizacion": organizacion,
        "request": request,
        **(context or {}),
    }
    if request.method == "GET":
        return Response(
            serializer_class(queryset, many=True, context=serializer_context).data
        )
    serializer = serializer_class(data=request.data, context=serializer_context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def fuentes_datos(request, organizacion_id):
    organizacion = _organizacion(organizacion_id)
    return _respuesta_coleccion(
        request,
        organizacion,
        data_sources_for_organization(organizacion),
        FuenteDatosSerializer,
    )


@api_view(["GET", "PATCH"])
def fuente_datos_detail(request, organizacion_id, fuente_id):
    organizacion = _organizacion(organizacion_id)
    fuente = get_object_or_404(data_source_for_organization(organizacion, fuente_id))
    if request.method == "GET":
        return Response(FuenteDatosSerializer(fuente).data)
    serializer = FuenteDatosSerializer(
        fuente, data=request.data, partial=True, context={"organizacion": organizacion}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def actividades_operacionales(request, organizacion_id):
    organizacion = _organizacion(organizacion_id)
    queryset = activities_for_organization(organizacion, request.query_params)
    return _respuesta_coleccion(
        request, organizacion, queryset, ActividadOperacionalSerializer
    )


@api_view(["GET", "PATCH"])
def actividad_operacional_detail(request, organizacion_id, actividad_id):
    organizacion = _organizacion(organizacion_id)
    actividad = get_object_or_404(activity_for_organization(organizacion, actividad_id))
    if request.method == "GET":
        actividad = activity_detail(
            organizacion.actividades_operacionales, actividad_id
        )
        return Response(
            ActividadOperacionalSerializer(
                actividad, context={"organizacion": organizacion}
            ).data
        )
    serializer = ActividadOperacionalSerializer(
        actividad,
        data=request.data,
        partial=True,
        context={"organizacion": organizacion},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def observaciones_actividad(request, organizacion_id, actividad_id):
    organizacion = _organizacion(organizacion_id)
    actividad = get_object_or_404(activity_for_organization(organizacion, actividad_id))
    queryset = observations_for_activity(actividad, request.query_params)
    return _respuesta_coleccion(
        request, organizacion, queryset, ObservacionSerializer, {"actividad": actividad}
    )


@api_view(["GET", "PATCH"])
def observacion_detail(request, organizacion_id, observacion_id):
    organizacion = _organizacion(organizacion_id)
    observacion = get_object_or_404(
        observation_for_organization(organizacion, observacion_id)
    )
    if request.method == "GET":
        return Response(ObservacionSerializer(observacion).data)
    serializer = ObservacionSerializer(
        observacion,
        data=request.data,
        partial=True,
        context={"organizacion": organizacion, "actividad": observacion.actividad},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)
