from datetime import datetime, time, timedelta

from django.db.models import Avg, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.analytics.models import Constructora

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


def resolve_constructora(request):
    constructora_id = (
        request.query_params.get("constructora_id")
        or request.query_params.get("constructora")
    )
    if not constructora_id:
        return None

    return (
        Constructora.objects.filter(constructora_id=constructora_id).first()
        or Constructora.objects.filter(nombre__iexact=constructora_id).first()
    )


def lecturas_constructora_hoy_queryset(constructora=None):
    queryset = lecturas_de_hoy_queryset()
    if constructora:
        queryset = queryset.filter(constructora__iexact=constructora.nombre)
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
    constructora = resolve_constructora(request)
    queryset = lecturas_constructora_hoy_queryset(constructora)
    agregados = queryset.aggregate(
        emisiones_totales=Sum("co2e_estimado"),
        consumo_promedio=Avg("valor"),
    )
    etapa_top = top_emisiones(queryset, "etapa_obra")
    fuente_top = top_emisiones(queryset, "tipo")
    ultima = queryset.order_by("-fecha_registro").first()

    return Response(
        {
            "total_lecturas": queryset.count(),
            "emisiones_totales_kg_co2e": float(agregados["emisiones_totales"] or 0),
            "consumo_promedio": float(agregados["consumo_promedio"] or 0),
            "sensores_activos": queryset.values("sensor").distinct().count(),
            "etapa_mayor_emision_hoy": (
                etapa_top["etapa_obra"] if etapa_top else None
            ),
            "etapa_mayor_emision_hoy_kg_co2e": (
                float(etapa_top["emisiones"] or 0) if etapa_top else 0
            ),
            "fuente_emision_mayor_emision_hoy": (
                fuente_top["tipo"] if fuente_top else None
            ),
            "fuente_emision_mayor_emision_hoy_kg_co2e": (
                float(fuente_top["emisiones"] or 0) if fuente_top else 0
            ),
            "ultima_actualizacion": (
                ultima.fecha_registro.isoformat() if ultima else None
            ),
        }
    )


@api_view(["GET"])
def ultimas_lecturas(request):
    constructora = resolve_constructora(request)
    queryset = LecturaSensor.objects.all()
    if constructora:
        queryset = queryset.filter(constructora__iexact=constructora.nombre)
    queryset = queryset[:20]
    serializer = LecturaSensorSerializer(queryset, many=True)
    return Response(serializer.data)
