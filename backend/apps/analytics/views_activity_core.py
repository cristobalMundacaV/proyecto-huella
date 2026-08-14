from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import ActividadOperacional, FuenteDatos, Observacion, Organizacion
from .serializers_activity_core import ActividadOperacionalSerializer, FuenteDatosSerializer, ObservacionSerializer
from .services.activity_core import detalle_actividad


def _organizacion(organizacion_id):
    return get_object_or_404(Organizacion, organizacion_id=organizacion_id)


def _respuesta_coleccion(request, organizacion, queryset, serializer_class, context=None):
    serializer_context = {"organizacion": organizacion, "request": request, **(context or {})}
    if request.method == "GET":
        return Response(serializer_class(queryset, many=True, context=serializer_context).data)
    serializer = serializer_class(data=request.data, context=serializer_context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def fuentes_datos(request, organizacion_id):
    organizacion = _organizacion(organizacion_id)
    return _respuesta_coleccion(request, organizacion, organizacion.fuentes_datos.all(), FuenteDatosSerializer)


@api_view(["GET", "PATCH"])
def fuente_datos_detail(request, organizacion_id, fuente_id):
    organizacion = _organizacion(organizacion_id)
    fuente = get_object_or_404(FuenteDatos, organizacion=organizacion, id=fuente_id)
    if request.method == "GET":
        return Response(FuenteDatosSerializer(fuente).data)
    serializer = FuenteDatosSerializer(fuente, data=request.data, partial=True, context={"organizacion": organizacion})
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)


def _filtrar_actividades(queryset, params):
    mapping = {"tipo": "tipo", "proceso": "proceso_operacional_id", "unidad": "unidad_operacional_id", "estado": "estado"}
    for parametro, campo in mapping.items():
        if params.get(parametro):
            queryset = queryset.filter(**{campo: params[parametro]})
    if params.get("fecha_desde"):
        queryset = queryset.filter(timestamp_inicio__date__gte=params["fecha_desde"])
    if params.get("fecha_hasta"):
        queryset = queryset.filter(timestamp_inicio__date__lte=params["fecha_hasta"])
    return queryset


@api_view(["GET", "POST"])
def actividades_operacionales(request, organizacion_id):
    organizacion = _organizacion(organizacion_id)
    queryset = _filtrar_actividades(organizacion.actividades_operacionales.select_related("unidad_operacional", "proceso_operacional"), request.query_params)
    return _respuesta_coleccion(request, organizacion, queryset, ActividadOperacionalSerializer)


@api_view(["GET", "PATCH"])
def actividad_operacional_detail(request, organizacion_id, actividad_id):
    organizacion = _organizacion(organizacion_id)
    actividad = get_object_or_404(organizacion.actividades_operacionales, id=actividad_id)
    if request.method == "GET":
        actividad = detalle_actividad(organizacion.actividades_operacionales, actividad_id)
        return Response(ActividadOperacionalSerializer(actividad, context={"organizacion": organizacion}).data)
    serializer = ActividadOperacionalSerializer(actividad, data=request.data, partial=True, context={"organizacion": organizacion})
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def observaciones_actividad(request, organizacion_id, actividad_id):
    organizacion = _organizacion(organizacion_id)
    actividad = get_object_or_404(ActividadOperacional, organizacion=organizacion, id=actividad_id)
    queryset = actividad.observaciones.select_related("fuente", "evidencia")
    if request.query_params.get("concepto"):
        queryset = queryset.filter(concepto=request.query_params["concepto"])
    if request.query_params.get("fuente"):
        queryset = queryset.filter(fuente_id=request.query_params["fuente"])
    return _respuesta_coleccion(request, organizacion, queryset, ObservacionSerializer, {"actividad": actividad})


@api_view(["GET", "PATCH"])
def observacion_detail(request, organizacion_id, observacion_id):
    organizacion = _organizacion(organizacion_id)
    observacion = get_object_or_404(Observacion.objects.select_related("fuente", "evidencia", "actividad"), organizacion=organizacion, id=observacion_id)
    if request.method == "GET":
        return Response(ObservacionSerializer(observacion).data)
    serializer = ObservacionSerializer(observacion, data=request.data, partial=True, context={"organizacion": organizacion, "actividad": observacion.actividad})
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)
