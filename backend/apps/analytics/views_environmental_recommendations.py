from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Organizacion
from .services.environmental_recommendation_engine import build_environmental_recommendations


@api_view(["GET"])
def environmental_recommendations(request, organizacion_id):
    organizacion = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    try:
        return Response(build_environmental_recommendations(organizacion))
    except Exception:
        return Response(
            {"error": "No se pudieron generar recomendaciones ambientales."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
