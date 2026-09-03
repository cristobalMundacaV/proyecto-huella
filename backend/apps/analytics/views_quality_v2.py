from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    EvaluacionCalidadDato,
    Organizacion,
)
from .permissions import Permission, has_tenant_permission, require_resource_work_access
from .selectors.quality import (
    baselines_for_user,
    confidence_policies,
    discrepancies_for_organization,
    discrepancy_for_organization,
    indicator_comparison_period,
    indicator_for_organization,
    indicators_for_user,
    latest_indicator_values,
    observations_for_quality,
)
from .serializers_quality_v2 import (
    DiscrepanciaSerializer,
    EvaluacionCalidadSerializer,
    IndicadorSerializer,
    LineaBaseSerializer,
    PoliticaFuenteSerializer,
    ValorIndicadorSerializer,
)
from .services.comparison_v2 import compare_values
from .services.indicators_v2 import build_baseline
from .services.quality_v2 import ensure_current_quality_evaluation


def _org(request, value, permission=Permission.INDICATOR_VIEW):
    organization = get_object_or_404(Organizacion, organizacion_id=value)
    allowed = has_tenant_permission(request.user, organization, permission)
    if not allowed:
        raise Http404("Recurso no encontrado.")
    return organization


@api_view(["GET"])
def calidad_observaciones(
    request,
    organizacion_id,
):
    org = _org(
        request,
        organizacion_id,
    )

    obra_id = request.query_params.get("obra")

    observations = observations_for_quality(org, obra_id)

    queryset = [ensure_current_quality_evaluation(observation) for observation in observations]

    return Response(
        EvaluacionCalidadSerializer(
            queryset,
            many=True,
        ).data
    )


@api_view(["GET"])
def discrepancias(
    request,
    organizacion_id,
):
    org = _org(
        request,
        organizacion_id,
    )

    obra_id = request.query_params.get("obra")

    queryset = discrepancies_for_organization(org, obra_id)

    return Response(
        DiscrepanciaSerializer(
            queryset,
            many=True,
        ).data
    )


@api_view(["PATCH"])
def discrepancia_detail(request, organizacion_id, discrepancia_id):
    org = _org(request, organizacion_id, Permission.IMPORT_REVIEW)
    item = get_object_or_404(discrepancy_for_organization(org, discrepancia_id))
    serializer = DiscrepanciaSerializer(item, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def politicas_fuente(request, organizacion_id):
    org = _org(request, organizacion_id, Permission.FACTOR_VIEW)
    queryset = confidence_policies(org)
    return Response(PoliticaFuenteSerializer(queryset, many=True).data)


@api_view(["GET"])
def indicadores(
    request,
    organizacion_id,
):
    org = _org(
        request,
        organizacion_id,
    )

    obra_id = request.query_params.get("obra")
    queryset = indicators_for_user(org, request.user, obra_id)

    return Response(
        IndicadorSerializer(
            queryset,
            many=True,
        ).data
    )


@api_view(["GET"])
def serie_indicador(
    request,
    organizacion_id,
    indicador_id,
):
    org = _org(
        request,
        organizacion_id,
    )

    indicator = get_object_or_404(
        indicator_for_organization(org, indicador_id),
    )
    require_resource_work_access(request.user, org, indicator)

    return Response(
        ValorIndicadorSerializer(
            indicator.valores.all(),
            many=True,
        ).data
    )


@api_view(["GET"])
def comparacion_indicador(request, organizacion_id, indicador_id):
    org = _org(request, organizacion_id)
    indicator = get_object_or_404(indicator_for_organization(org, indicador_id))
    require_resource_work_access(request.user, org, indicator)
    effective_periods = latest_indicator_values(indicator)
    current = effective_periods[0] if effective_periods else None
    if not current or current.metadata.get("disponible") is False:
        return Response({"estado": "sin_base", "calidad_comparacion": "sin_datos"})
    comparable = indicator_comparison_period(indicator, current)
    if comparable:
        reference = (
            indicator.valores.filter(
                periodo_inicio=comparable.periodo_referencia_inicio,
                periodo_fin=comparable.periodo_referencia_fin,
            )
            .order_by("-version")
            .first()
        )
    else:
        reference = next(
            (
                value
                for value in effective_periods[1:]
                if value.metadata.get("disponible") is not False
            ),
            None,
        )
    if reference and reference.metadata.get("disponible") is False:
        reference = None
    return Response(
        compare_values(
            indicator, current.valor, reference.valor if reference else None, comparable
        )
    )


@api_view(["GET", "POST"])
def lineas_base(
    request,
    organizacion_id,
):
    org = _org(
        request,
        organizacion_id,
        (
            Permission.INDICATOR_MANAGE
            if request.method == "POST"
            else Permission.INDICATOR_VIEW
        ),
    )

    obra_id = request.query_params.get("obra")

    if request.method == "POST":
        indicator = get_object_or_404(
            indicator_for_organization(org, request.data.get("indicador")),
        )
        require_resource_work_access(request.user, org, indicator)

        baseline = build_baseline(indicator)

        return Response(
            LineaBaseSerializer(baseline).data,
            status=201,
        )

    queryset = baselines_for_user(org, request.user, obra_id)

    return Response(
        LineaBaseSerializer(
            queryset,
            many=True,
        ).data
    )


@api_view(["GET"])
def resumen_ambiental_v2(request, organizacion_id):
    org = _org(request, organizacion_id)
    indicators = indicators_for_user(org, request.user)
    baselines = baselines_for_user(org, request.user)
    return Response(
        {
            "mensaje": (
                "Carbono Zero esta construyendo tu linea base ambiental."
                if not baselines.filter(estado__in=["suficiente", "cerrada"]).exists()
                else "Linea base ambiental disponible."
            ),
            "indicadores": IndicadorSerializer(indicators, many=True).data,
            "lineas_base": LineaBaseSerializer(baselines, many=True).data,
            "calidad": {
                state: org.evaluaciones_calidad.filter(estado=state).count()
                for state, _ in EvaluacionCalidadDato.Estado.choices
            },
            "discrepancias_abiertas": org.discrepancias_dato.filter(
                estado__in=["detectada", "requiere_revision"]
            ).count(),
        }
    )
