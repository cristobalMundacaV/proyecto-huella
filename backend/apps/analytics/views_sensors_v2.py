from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.iot.models import CalibracionSensor, DispositivoSensor, InstalacionSensor
from apps.iot.serializers_v2 import (CalibracionSensorSerializer, DispositivoSensorV2Serializer,
                                     InstalacionSensorSerializer, LecturaSensorV2Serializer)

from .models import Organizacion


def _org(value): return get_object_or_404(Organizacion, organizacion_id=value)
def _sensor(org, value): return get_object_or_404(DispositivoSensor, organizacion=org, id=value)


@api_view(["GET", "POST"])
def sensores(request, organizacion_id):
    org = _org(organizacion_id)
    queryset = org.dispositivos_iot.select_related("activo_operacional", "unidad_operacional", "proceso_operacional").prefetch_related("instalaciones", "calibraciones")
    if request.method == "GET": return Response(DispositivoSensorV2Serializer(queryset, many=True, context={"organizacion": org}).data)
    serializer = DispositivoSensorV2Serializer(data=request.data, context={"organizacion": org}); serializer.is_valid(raise_exception=True); serializer.save(); return Response(serializer.data, status=201)


@api_view(["GET", "PATCH"])
def sensor_detail(request, organizacion_id, sensor_id):
    org = _org(organizacion_id); sensor = _sensor(org, sensor_id)
    if request.method == "GET": return Response(DispositivoSensorV2Serializer(sensor, context={"organizacion": org}).data)
    serializer = DispositivoSensorV2Serializer(sensor, data=request.data, partial=True, context={"organizacion": org}); serializer.is_valid(raise_exception=True); serializer.save(); return Response(serializer.data)


def _nested(request, org, sensor, queryset, serializer_class):
    context = {"sensor": sensor}
    if request.method == "GET": return Response(serializer_class(queryset, many=True, context=context).data)
    serializer = serializer_class(data=request.data, context=context); serializer.is_valid(raise_exception=True); serializer.save(); return Response(serializer.data, status=201)


@api_view(["GET", "POST"])
def instalaciones(request, organizacion_id, sensor_id):
    org = _org(organizacion_id); sensor = _sensor(org, sensor_id); return _nested(request, org, sensor, sensor.instalaciones.all(), InstalacionSensorSerializer)


@api_view(["GET", "POST"])
def calibraciones(request, organizacion_id, sensor_id):
    org = _org(organizacion_id); sensor = _sensor(org, sensor_id); return _nested(request, org, sensor, sensor.calibraciones.all(), CalibracionSensorSerializer)


@api_view(["GET", "POST"])
def lecturas_sensor_v2(request, organizacion_id, sensor_id):
    org = _org(organizacion_id); sensor = _sensor(org, sensor_id); return _nested(request, org, sensor, sensor.lecturas_v2.select_related("observacion__fuente"), LecturaSensorV2Serializer)
