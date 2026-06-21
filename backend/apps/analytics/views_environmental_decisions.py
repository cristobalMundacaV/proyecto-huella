from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Constructora
from .services.environmental_decision_priority_service import build_environmental_decision_priorities


@api_view(["GET"])
def environmental_decision_priorities(request, constructora_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)
    try:
        return Response(build_environmental_decision_priorities(constructora))
    except Exception:
        return Response(
            {"error": "No se pudieron priorizar decisiones ambientales."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
