from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Constructora
from .services.environmental_kpi_service import build_environmental_kpis


@api_view(["GET"])
def environmental_kpis(request, constructora_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)
    try:
        return Response(build_environmental_kpis(constructora))
    except Exception as error:
        return Response(
            {
                "error": "No se pudieron calcular los KPIs ambientales.",
                "detail": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
