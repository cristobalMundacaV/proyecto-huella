from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Organizacion
from .services.environmental_ingestion_readiness_service import build_environmental_ingestion_readiness


@api_view(["GET"])
def environmental_ingestion_readiness(request, organizacion_id):
    organizacion = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    try:
        return Response(build_environmental_ingestion_readiness(organizacion))
    except Exception:
        return Response(
            {"error": "No se pudo calcular la preparacion de ingesta ambiental."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
