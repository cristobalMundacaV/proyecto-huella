from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (CalculoAmbiental, FactorAmbiental, ImpactoAmbiental,
                     MetodologiaAmbiental, Organizacion)
from .serializers_calculation_v2 import (CalculoAmbientalSerializer, FactorAmbientalSerializer,
                                        ImpactoAmbientalSerializer, MetodologiaSerializer)
from .services.calculation_v2 import calculate_activity
from .services.methodology_selector import select_methodology


def _org(value): return get_object_or_404(Organizacion, organizacion_id=value)
def _activity(org, value): return get_object_or_404(org.actividades_operacionales, id=value)


def _serialize_selection(selection):
    selected = selection["seleccion"]
    return {
        "estado": selected["elegibilidad"]["estado"] if selected else "no_calculable",
        "metodologia_seleccionada": ({"id": selected["version_metodologia"].metodologia_id,
                                      "nombre": selected["version_metodologia"].metodologia.nombre,
                                      "version": selected["version_metodologia"].version,
                                      "formula": selected["formula"].expresion_legible,
                                      "factor": selected["elegibilidad"]["factor_version"].factor.nombre} if selected else None),
        "razon": selection["razon"],
        "alternativos": [item["metodo"] for item in selection["alternativos"]],
        "descartados": selection["descartados"],
        "advertencias": selected["elegibilidad"]["advertencias"] if selected else [],
    }


@api_view(["GET"])
def metodologias(request, organizacion_id):
    org = _org(organizacion_id)
    queryset = MetodologiaAmbiental.objects.filter(Q(organizacion=org) | Q(organizacion__isnull=True)).prefetch_related("versiones__formula__variables", "versiones__formula__factor_ambiental")
    return Response(MetodologiaSerializer(queryset, many=True).data)


@api_view(["GET"])
def metodologia_detail(request, organizacion_id, metodologia_id):
    org = _org(organizacion_id)
    item = get_object_or_404(MetodologiaAmbiental.objects.prefetch_related("versiones__formula__variables"), Q(organizacion=org) | Q(organizacion__isnull=True), id=metodologia_id)
    return Response(MetodologiaSerializer(item).data)


@api_view(["GET"])
def factores_ambientales(request, organizacion_id):
    org = _org(organizacion_id)
    queryset = FactorAmbiental.objects.filter(Q(organizacion=org) | Q(organizacion__isnull=True)).prefetch_related("versiones")
    return Response(FactorAmbientalSerializer(queryset, many=True).data)


@api_view(["GET"])
def elegibilidad_actividad(request, organizacion_id, actividad_id):
    org = _org(organizacion_id); return Response(_serialize_selection(select_methodology(_activity(org, actividad_id))))


@api_view(["POST"])
def calcular_actividad(request, organizacion_id, actividad_id):
    org = _org(organizacion_id)
    try: calculation, selection = calculate_activity(_activity(org, actividad_id))
    except ValueError as exc: return Response({"error": str(exc), "elegibilidad": _serialize_selection(select_methodology(_activity(org, actividad_id)))}, status=400)
    return Response({"calculo": CalculoAmbientalSerializer(calculation).data, "seleccion": _serialize_selection(selection)}, status=201)


@api_view(["GET"])
def calculos_actividad(request, organizacion_id, actividad_id):
    org = _org(organizacion_id); activity = _activity(org, actividad_id)
    queryset = activity.calculos_ambientales.select_related("version_metodologia__metodologia", "formula__factor_ambiental", "version_factor__factor").prefetch_related("inputs__observacion", "inputs__fuente")
    return Response(CalculoAmbientalSerializer(queryset, many=True).data)


@api_view(["GET"])
def calculo_detail(request, organizacion_id, calculo_id):
    org = _org(organizacion_id)
    item = get_object_or_404(CalculoAmbiental.objects.select_related("version_metodologia__metodologia", "formula__factor_ambiental", "version_factor__factor").prefetch_related("inputs__observacion", "inputs__fuente"), organizacion=org, id=calculo_id)
    return Response(CalculoAmbientalSerializer(item).data)


@api_view(["GET"])
def impactos_ambientales(request, organizacion_id):
    org = _org(organizacion_id); return Response(ImpactoAmbientalSerializer(org.impactos_ambientales_v2.all(), many=True).data)
