from django.db.models import Q

from ..models import (
    DiscrepanciaDato,
    EvaluacionCalidadDato,
    ImpactoAmbiental,
    IndicadorAmbiental,
    Obra,
    Observacion,
    PeriodoComparable,
    PoliticaConfianzaFuente,
    ValorIndicador,
)
from ..permissions import filter_works_for_user


def observations_for_quality(organization, work_id=None):
    rows = organization.observaciones_operacionales.select_related(
        "fuente", "actividad", "actividad__obra", "evidencia"
    )
    return rows.filter(actividad__obra_id=work_id) if work_id else rows


def quality_evaluations(organization, observations):
    return (
        EvaluacionCalidadDato.objects.filter(
            organizacion=organization, observacion__in=observations
        )
        .select_related(
            "observacion__fuente",
            "observacion__actividad",
            "observacion__actividad__obra",
            "observacion__evidencia",
        )
        .order_by("-fecha_evaluacion")
    )


def discrepancies_for_organization(organization, work_id=None):
    rows = organization.discrepancias_dato.select_related(
        "actividad", "actividad__obra", "observacion_seleccionada"
    ).prefetch_related("observaciones", "observaciones__fuente")
    return rows.filter(actividad__obra_id=work_id) if work_id else rows


def discrepancy_for_organization(organization, discrepancy_id):
    return DiscrepanciaDato.objects.filter(organizacion=organization, id=discrepancy_id)


def confidence_policies(organization):
    return PoliticaConfianzaFuente.objects.filter(
        Q(organizacion=organization) | Q(organizacion__isnull=True), activa=True
    ).order_by("concepto", "prioridad")


def indicators_for_user(organization, user, work_id=None):
    rows = organization.indicadores_ambientales_v2.prefetch_related("valores")
    allowed = filter_works_for_user(Obra.objects.all(), user, organization)
    rows = rows.filter(Q(obra__isnull=True) | Q(obra__in=allowed))
    return rows.filter(obra_id=work_id) if work_id else rows


def indicator_for_organization(organization, indicator_id):
    return IndicadorAmbiental.objects.filter(organizacion=organization, id=indicator_id)


def indicator_comparison_period(indicator, current):
    return PeriodoComparable.objects.filter(
        indicador=indicator,
        periodo_actual_inicio=current.periodo_inicio,
        periodo_actual_fin=current.periodo_fin,
    ).first()


def baselines_for_user(organization, user, work_id=None):
    rows = organization.lineas_base_ambientales.select_related("indicador")
    allowed = filter_works_for_user(Obra.objects.all(), user, organization)
    rows = rows.filter(Q(indicador__obra__isnull=True) | Q(indicador__obra__in=allowed))
    return rows.filter(indicador__obra_id=work_id) if work_id else rows


def indicator_inputs(indicator, start, end):
    impacts = ImpactoAmbiental.objects.filter(
        organizacion=indicator.organizacion,
        timestamp__date__gte=start,
        timestamp__date__lte=end,
    )
    observations = Observacion.objects.filter(
        organizacion=indicator.organizacion,
        timestamp_observacion__date__gte=start,
        timestamp_observacion__date__lte=end,
    )
    if indicator.alcance == indicator.Alcance.OBRA:
        impacts = impacts.filter(actividad__obra=indicator.obra)
        observations = observations.filter(actividad__obra=indicator.obra)
    return impacts, observations


def next_indicator_value_version(indicator, start, end):
    return (
        ValorIndicador.objects.filter(
            indicador=indicator, periodo_inicio=start, periodo_fin=end
        ).count()
        + 1
    )


def baseline_values(indicator):
    return indicator.valores.order_by("periodo_inicio", "-version")
