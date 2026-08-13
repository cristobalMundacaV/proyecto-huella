from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Organizacion
from .services.environmental_decision_priority_service import build_environmental_decision_priorities


@api_view(["GET"])
def environmental_decision_priorities(request, organizacion_id):
    organizacion = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    try:
        return Response(build_environmental_decision_priorities(organizacion))
    except Exception:
        return Response(
            {"error": "No se pudieron priorizar decisiones ambientales."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
