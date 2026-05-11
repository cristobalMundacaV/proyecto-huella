from datetime import timedelta

from django.db.models import Avg, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import LecturaSensor
from .serializers import LecturaSensorSerializer


def ultimas_24_horas_queryset():
    desde = timezone.now() - timedelta(hours=24)
    return LecturaSensor.objects.filter(fecha_registro__gte=desde)


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
    queryset = ultimas_24_horas_queryset()
    agregados = queryset.aggregate(
        emisiones_totales=Sum("co2e_estimado"),
        consumo_promedio=Avg("valor"),
    )
    ultima = LecturaSensor.objects.order_by("-fecha_registro").first()

    return Response(
        {
            "total_lecturas": queryset.count(),
            "emisiones_totales_kg_co2e": float(agregados["emisiones_totales"] or 0),
            "consumo_promedio": float(agregados["consumo_promedio"] or 0),
            "sensores_activos": queryset.values("sensor").distinct().count(),
            "ultima_actualizacion": (
                ultima.fecha_registro.isoformat() if ultima else None
            ),
        }
    )


@api_view(["GET"])
def ultimas_lecturas(request):
    queryset = LecturaSensor.objects.all()[:20]
    serializer = LecturaSensorSerializer(queryset, many=True)
    return Response(serializer.data)
