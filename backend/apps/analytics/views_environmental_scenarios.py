from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Constructora
from .services.environmental_scenario_service import build_environmental_scenarios


@api_view(["GET"])
def environmental_scenarios(request, constructora_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)
    try:
        return Response(build_environmental_scenarios(constructora))
    except Exception:
        return Response(
            {"error": "No se pudieron calcular escenarios ambientales."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
