from datetime import datetime, time, timedelta

from django.db.models import Avg, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.analytics.models import Empresa

from .models import LecturaSensor
from .serializers import LecturaSensorSerializer


def lecturas_de_hoy_queryset():
    current_timezone = timezone.get_current_timezone()
    today = timezone.localdate()
    start = timezone.make_aware(
        datetime.combine(today, time.min),
        current_timezone,
    )
    end = start + timedelta(days=1)
    return LecturaSensor.objects.filter(
        fecha_registro__gte=start,
        fecha_registro__lt=end,
    )


def resolve_empresa(request):
    empresa_id = request.query_params.get("empresa_id") or request.query_params.get("empresa")
    if not empresa_id:
        return None

    return (
        Empresa.objects.filter(empresa_id=empresa_id).first()
        or Empresa.objects.filter(nombre__iexact=empresa_id).first()
    )


def lecturas_empresa_hoy_queryset(empresa=None):
    queryset = lecturas_de_hoy_queryset()
    if empresa:
        queryset = queryset.filter(empresa__iexact=empresa.nombre)
    return queryset


def top_emisiones(queryset, group_field):
    return (
        queryset.values(group_field)
        .annotate(emisiones=Sum("co2e_estimado"))
        .order_by("-emisiones", group_field)
        .first()
    )


@api_view(["POST"])
def lecturas(request):
    serializer = LecturaSensorSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    lectura = serializer.save()
    return Response(
        LecturaSensorSerializer(lectura).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def kpis(request):
    empresa = resolve_empresa(request)
    queryset = lecturas_empresa_hoy_queryset(empresa)
    agregados = queryset.aggregate(
        emisiones_totales=Sum("co2e_estimado"),
        consumo_promedio=Avg("valor"),
    )
    unidad_top = top_emisiones(queryset, "unidad_operativa")
    actividad_top = top_emisiones(queryset, "tipo")
    ultima = queryset.order_by("-fecha_registro").first()

    return Response(
        {
            "total_lecturas": queryset.count(),
            "emisiones_totales_kg_co2e": float(agregados["emisiones_totales"] or 0),
            "consumo_promedio": float(agregados["consumo_promedio"] or 0),
            "sensores_activos": queryset.values("sensor").distinct().count(),
            "unidad_mayor_emision_hoy": (
                unidad_top["unidad_operativa"] if unidad_top else None
            ),
            "unidad_mayor_emision_hoy_kg_co2e": (
                float(unidad_top["emisiones"] or 0) if unidad_top else 0
            ),
            "actividad_mayor_emision_hoy": (
                actividad_top["tipo"] if actividad_top else None
            ),
            "actividad_mayor_emision_hoy_kg_co2e": (
                float(actividad_top["emisiones"] or 0) if actividad_top else 0
            ),
            "ultima_actualizacion": (
                ultima.fecha_registro.isoformat() if ultima else None
            ),
        }
    )


@api_view(["GET"])
def ultimas_lecturas(request):
    empresa = resolve_empresa(request)
    queryset = LecturaSensor.objects.all()
    if empresa:
        queryset = queryset.filter(empresa__iexact=empresa.nombre)
    queryset = queryset[:20]
    serializer = LecturaSensorSerializer(queryset, many=True)
    return Response(serializer.data)
