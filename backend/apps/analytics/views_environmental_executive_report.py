from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Organizacion
from .services.environmental_executive_report_service import build_environmental_executive_report


@api_view(["GET"])
def environmental_executive_report(request, organizacion_id):
    organizacion = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    try:
        return Response(build_environmental_executive_report(organizacion))
    except Exception:
        return Response(
            {"error": "No se pudo generar el informe ejecutivo ambiental."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
