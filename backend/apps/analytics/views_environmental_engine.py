from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Organizacion
from .services.environmental_engine import calculate_environmental_metrics, calculate_partial_lca
from django.shortcuts import get_object_or_404


@api_view(["GET"])
def environmental_engine_results(request, organizacion_id):
    organizacion = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    result = calculate_environmental_metrics(
        organizacion,
        start=parse_date(request.query_params.get("desde", "")),
        end=parse_date(request.query_params.get("hasta", "")),
        intensity_denominator=request.query_params.get("denominador"),
        intensity_unit=request.query_params.get("unidad_intensidad", "unidad"),
    )
    return Response(result)


@api_view(["GET"])
def environmental_lca_results(request, organizacion_id):
    organizacion = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    return Response(calculate_partial_lca(organizacion, material_producto=request.query_params.get("material_producto")))
