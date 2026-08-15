from datetime import datetime, time, timedelta

from django.db.models import Avg, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.analytics.models import Organizacion

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


def resolve_organizacion(request):
    organizacion_id = (
        request.query_params.get("organizacion_id")
        or request.query_params.get("organizacion")
    )
    if not organizacion_id:
        return None

    organization = (
        Organizacion.objects.filter(organizacion_id=organizacion_id).first()
        or Organizacion.objects.filter(nombre__iexact=organizacion_id).first()
    )
    if organization and not (request.user.is_superuser or organization.usuarios.filter(user=request.user, activo=True).exists()):
        return None
    return organization


def lecturas_organizacion_hoy_queryset(organizacion=None, request=None):
    queryset = lecturas_de_hoy_queryset()
    if organizacion:
        queryset = queryset.filter(organizacion__iexact=organizacion.nombre)
    elif request and not request.user.is_superuser:
        names = Organizacion.objects.filter(usuarios__user=request.user, usuarios__activo=True).values_list("nombre", flat=True)
        queryset = queryset.filter(organizacion__in=names)
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
    organization = Organizacion.objects.filter(nombre__iexact=serializer.validated_data["organizacion"]).first()
    if not organization or not (request.user.is_superuser or organization.usuarios.filter(user=request.user, activo=True).exists()):
        return Response({"detail": "Recurso no encontrado."}, status=404)
    lectura = serializer.save()
    return Response(
        LecturaSensorSerializer(lectura).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def kpis(request):
    organizacion = resolve_organizacion(request)
    queryset = lecturas_organizacion_hoy_queryset(organizacion, request)
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
    organizacion = resolve_organizacion(request)
    queryset = lecturas_organizacion_hoy_queryset(organizacion, request)
    queryset = queryset.order_by("-fecha_registro")[:20]
    serializer = LecturaSensorSerializer(queryset, many=True)
    return Response(serializer.data)
