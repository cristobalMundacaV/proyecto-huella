from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (CapacidadAmbiental, CapacidadOrganizacion, DiagnosticoAmbientalInicial,
                     Organizacion, ProcesoOperacional, UnidadOperacional)
from .serializers_foundation import (CapacidadAmbientalSerializer, CapacidadOrganizacionSerializer,
                                     DiagnosticoAmbientalSerializer, ProcesoOperacionalSerializer,
                                     UnidadOperacionalSerializer)
from .services.foundation import inicializar_capacidades_preset, resumen_preparacion_ambiental


def _organizacion(organizacion_id):
    return get_object_or_404(Organizacion, organizacion_id=organizacion_id)


@api_view(["GET"])
def capacidades_disponibles(request):
    return Response(CapacidadAmbientalSerializer(CapacidadAmbiental.objects.filter(activa=True), many=True).data)


@api_view(["GET", "POST", "PATCH"])
def diagnostico_ambiental(request, organizacion_id):
    organizacion = _organizacion(organizacion_id)
    obra_id = request.query_params.get("obra") or request.data.get("obra")
    obra = get_object_or_404(organizacion.obras, id=obra_id) if obra_id else None
    diagnostico = DiagnosticoAmbientalInicial.objects.filter(organizacion=organizacion, obra=obra).first()
    if request.method == "GET":
        return Response(DiagnosticoAmbientalSerializer(diagnostico).data if diagnostico else None)
    if request.method == "POST" and diagnostico:
        return Response({"error": "El alcance ya tiene un diagnostico."}, status=status.HTTP_409_CONFLICT)
    if request.method == "PATCH" and not diagnostico:
        return Response({"error": "Diagnostico no encontrado."}, status=status.HTTP_404_NOT_FOUND)
    serializer = DiagnosticoAmbientalSerializer(diagnostico, data=request.data, partial=request.method == "PATCH", context={"organizacion": organizacion})
    serializer.is_valid(raise_exception=True)
    serializer.save(organizacion=organizacion, obra=obra)
    return Response(serializer.data, status=status.HTTP_201_CREATED if request.method == "POST" else status.HTTP_200_OK)


@api_view(["GET"])
def capacidades_organizacion(request, organizacion_id):
    relaciones = inicializar_capacidades_preset(_organizacion(organizacion_id))
    return Response(CapacidadOrganizacionSerializer(relaciones, many=True).data)


@api_view(["PATCH"])
def capacidad_organizacion_detail(request, organizacion_id, capacidad_id):
    relacion = get_object_or_404(CapacidadOrganizacion, id=capacidad_id, organizacion=_organizacion(organizacion_id))
    serializer = CapacidadOrganizacionSerializer(relacion, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


def _coleccion(request, organizacion, queryset, serializer_class):
    if request.method == "GET":
        return Response(serializer_class(queryset, many=True, context={"organizacion": organizacion}).data)
    serializer = serializer_class(data=request.data, context={"organizacion": organizacion})
    serializer.is_valid(raise_exception=True)
    serializer.save(organizacion=organizacion)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def unidades_operacionales(request, organizacion_id):
    organizacion = _organizacion(organizacion_id)
    return _coleccion(request, organizacion, organizacion.unidades_operacionales.all(), UnidadOperacionalSerializer)


@api_view(["PATCH"])
def unidad_operacional_detail(request, organizacion_id, unidad_id):
    unidad = get_object_or_404(UnidadOperacional, id=unidad_id, organizacion=_organizacion(organizacion_id))
    serializer = UnidadOperacionalSerializer(unidad, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def procesos_operacionales(request, organizacion_id):
    organizacion = _organizacion(organizacion_id)
    return _coleccion(request, organizacion, organizacion.procesos_operacionales.all(), ProcesoOperacionalSerializer)


@api_view(["PATCH"])
def proceso_operacional_detail(request, organizacion_id, proceso_id):
    organizacion = _organizacion(organizacion_id)
    proceso = get_object_or_404(ProcesoOperacional, id=proceso_id, organizacion=organizacion)
    serializer = ProcesoOperacionalSerializer(proceso, data=request.data, partial=True, context={"organizacion": organizacion})
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def preparacion_ambiental(request, organizacion_id):
    organizacion = _organizacion(organizacion_id)
    inicializar_capacidades_preset(organizacion)
    return Response(resumen_preparacion_ambiental(organizacion))
