from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (DiscrepanciaDato, EvaluacionCalidadDato, IndicadorAmbiental,
                     LineaBaseAmbiental, Organizacion, PeriodoComparable,
                     PoliticaConfianzaFuente)
from .serializers_quality_v2 import (DiscrepanciaSerializer, EvaluacionCalidadSerializer,
                                     IndicadorSerializer, LineaBaseSerializer,
                                     PoliticaFuenteSerializer, ValorIndicadorSerializer)
from .services.comparison_v2 import compare_values
from .services.indicators_v2 import build_baseline
from .services.quality_v2 import evaluate_observation_quality


def _org(value):
    return get_object_or_404(Organizacion, organizacion_id=value)


@api_view(["GET"])
def calidad_observaciones(request, organizacion_id):
    org = _org(organizacion_id)
    for observation in org.observaciones_operacionales.select_related("fuente"):
        if not observation.evaluaciones_calidad.exists():
            evaluate_observation_quality(observation)
    queryset = EvaluacionCalidadDato.objects.filter(organizacion=org).select_related("observacion__fuente").order_by("-fecha_evaluacion")
    return Response(EvaluacionCalidadSerializer(queryset, many=True).data)


@api_view(["GET"])
def discrepancias(request, organizacion_id):
    org = _org(organizacion_id)
    return Response(DiscrepanciaSerializer(org.discrepancias_dato.prefetch_related("observaciones"), many=True).data)


@api_view(["PATCH"])
def discrepancia_detail(request, organizacion_id, discrepancia_id):
    item = get_object_or_404(DiscrepanciaDato, organizacion=_org(organizacion_id), id=discrepancia_id)
    serializer = DiscrepanciaSerializer(item, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def politicas_fuente(request, organizacion_id):
    org = _org(organizacion_id)
    queryset = PoliticaConfianzaFuente.objects.filter(Q(organizacion=org) | Q(organizacion__isnull=True), activa=True).order_by("concepto", "prioridad")
    return Response(PoliticaFuenteSerializer(queryset, many=True).data)


@api_view(["GET"])
def indicadores(request, organizacion_id):
    org = _org(organizacion_id)
    return Response(IndicadorSerializer(org.indicadores_ambientales_v2.prefetch_related("valores"), many=True).data)


@api_view(["GET"])
def serie_indicador(request, organizacion_id, indicador_id):
    indicator = get_object_or_404(IndicadorAmbiental, organizacion=_org(organizacion_id), id=indicador_id)
    return Response(ValorIndicadorSerializer(indicator.valores.all(), many=True).data)


@api_view(["GET"])
def comparacion_indicador(request, organizacion_id, indicador_id):
    indicator = get_object_or_404(IndicadorAmbiental, organizacion=_org(organizacion_id), id=indicador_id)
    current = indicator.valores.order_by("-periodo_fin", "-version").first()
    if not current:
        return Response({"estado": "sin_base", "calidad_comparacion": "sin_datos"})
    comparable = PeriodoComparable.objects.filter(indicador=indicator, periodo_actual_inicio=current.periodo_inicio, periodo_actual_fin=current.periodo_fin).first()
    if comparable:
        reference = indicator.valores.filter(periodo_inicio=comparable.periodo_referencia_inicio, periodo_fin=comparable.periodo_referencia_fin).order_by("-version").first()
    else:
        reference = indicator.valores.exclude(pk=current.pk).order_by("-periodo_fin", "-version").first()
    return Response(compare_values(indicator, current.valor, reference.valor if reference else None, comparable))


@api_view(["GET", "POST"])
def lineas_base(request, organizacion_id):
    org = _org(organizacion_id)
    if request.method == "POST":
        indicator = get_object_or_404(IndicadorAmbiental, organizacion=org, id=request.data.get("indicador"))
        return Response(LineaBaseSerializer(build_baseline(indicator)).data, status=201)
    return Response(LineaBaseSerializer(org.lineas_base_ambientales.select_related("indicador"), many=True).data)


@api_view(["GET"])
def resumen_ambiental_v2(request, organizacion_id):
    org = _org(organizacion_id)
    indicators = org.indicadores_ambientales_v2.prefetch_related("valores")
    baselines = org.lineas_base_ambientales.select_related("indicador")
    return Response({
        "mensaje": "Carbono Zero esta construyendo tu linea base ambiental." if not baselines.filter(estado__in=["suficiente", "cerrada"]).exists() else "Linea base ambiental disponible.",
        "indicadores": IndicadorSerializer(indicators, many=True).data,
        "lineas_base": LineaBaseSerializer(baselines, many=True).data,
        "calidad": {state: org.evaluaciones_calidad.filter(estado=state).count() for state, _ in EvaluacionCalidadDato.Estado.choices},
        "discrepancias_abiertas": org.discrepancias_dato.filter(estado__in=["detectada", "requiere_revision"]).count(),
    })
