from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import ActivoOperacional, MantenimientoActivo, Organizacion
from .serializers_assets import (ActivoOperacionalSerializer, CondicionOperacionalSerializer,
                                 MantenimientoActivoSerializer)


def _org(value): return get_object_or_404(Organizacion, organizacion_id=value)


@api_view(["GET", "POST"])
def activos(request, organizacion_id):
    org = _org(organizacion_id)
    queryset = org.activos_operacionales.select_related("unidad_operacional", "proceso_operacional").prefetch_related("mantenimientos", "condiciones", "sensores")
    if request.query_params.get("tipo"): queryset = queryset.filter(tipo=request.query_params["tipo"])
    if request.query_params.get("estado"): queryset = queryset.filter(estado=request.query_params["estado"])
    if request.method == "GET": return Response(ActivoOperacionalSerializer(queryset, many=True).data)
    serializer = ActivoOperacionalSerializer(data=request.data, context={"organizacion": org}); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
def activo_detail(request, organizacion_id, activo_id):
    org = _org(organizacion_id)
    activo = get_object_or_404(ActivoOperacional.objects.select_related("unidad_operacional", "proceso_operacional").prefetch_related("mantenimientos", "condiciones", "sensores"), organizacion=org, id=activo_id)
    if request.method == "GET": return Response(ActivoOperacionalSerializer(activo).data)
    serializer = ActivoOperacionalSerializer(activo, data=request.data, partial=True, context={"organizacion": org}); serializer.is_valid(raise_exception=True); serializer.save(); return Response(serializer.data)


@api_view(["GET", "POST"])
def mantenimientos_activo(request, organizacion_id, activo_id):
    org = _org(organizacion_id); activo = get_object_or_404(ActivoOperacional, organizacion=org, id=activo_id)
    if request.method == "GET": return Response(MantenimientoActivoSerializer(activo.mantenimientos.all(), many=True).data)
    serializer = MantenimientoActivoSerializer(data=request.data, context={"organizacion": org, "activo": activo}); serializer.is_valid(raise_exception=True); serializer.save(); return Response(serializer.data, status=201)


@api_view(["GET", "PATCH"])
def mantenimiento_detail(request, organizacion_id, mantenimiento_id):
    org = _org(organizacion_id); item = get_object_or_404(MantenimientoActivo, organizacion=org, id=mantenimiento_id)
    if request.method == "GET": return Response(MantenimientoActivoSerializer(item).data)
    serializer = MantenimientoActivoSerializer(item, data=request.data, partial=True, context={"organizacion": org, "activo": item.activo}); serializer.is_valid(raise_exception=True); serializer.save(); return Response(serializer.data)


@api_view(["GET", "POST"])
def condiciones_activo(request, organizacion_id, activo_id):
    org = _org(organizacion_id); activo = get_object_or_404(ActivoOperacional, organizacion=org, id=activo_id)
    if request.method == "GET": return Response(CondicionOperacionalSerializer(activo.condiciones.all(), many=True).data)
    serializer = CondicionOperacionalSerializer(data=request.data, context={"organizacion": org, "activo": activo}); serializer.is_valid(raise_exception=True); serializer.save(); return Response(serializer.data, status=201)
