from decimal import Decimal

from django.db.models import Sum

from ..models import ImpactoAmbiental, LineaBaseAmbiental, Observacion, ValorIndicador


def generate_indicator_value(indicator, start, end):
    impacts = ImpactoAmbiental.objects.filter(
        organizacion=indicator.organizacion, timestamp__date__gte=start, timestamp__date__lte=end,
    )
    numerator = impacts.aggregate(total=Sum("valor"))["total"] or Decimal("0")
    if indicator.tipo == "intensidad":
        denominator = Observacion.objects.filter(
            organizacion=indicator.organizacion, concepto=indicator.origen_denominador,
            timestamp_observacion__date__gte=start, timestamp_observacion__date__lte=end,
        ).aggregate(total=Sum("valor_numerico"))["total"] or Decimal("0")
        if not denominator:
            raise ValueError("No existe denominador para el periodo.")
        result = numerator / denominator
    elif indicator.origen_numerador == "impactos_ambientales":
        result = numerator
    else:
        result = Observacion.objects.filter(
            organizacion=indicator.organizacion, concepto=indicator.origen_numerador,
            timestamp_observacion__date__gte=start, timestamp_observacion__date__lte=end,
        ).aggregate(total=Sum("valor_numerico"))["total"] or Decimal("0")
    version = ValorIndicador.objects.filter(indicador=indicator, periodo_inicio=start, periodo_fin=end).count() + 1
    return ValorIndicador.objects.create(
        indicador=indicator, periodo_inicio=start, periodo_fin=end, valor=result, unidad=indicator.unidad,
        fuente_calculo="impactos_y_observaciones_v2", version=version,
    )


def build_baseline(indicator):
    values = list(indicator.valores.order_by("periodo_inicio", "-version"))
    latest = {}
    for value in values:
        latest.setdefault((value.periodo_inicio, value.periodo_fin), value)
    periods = list(latest.values())
    if not periods:
        return LineaBaseAmbiental.objects.create(
            organizacion=indicator.organizacion, indicador=indicator, estado="construyendo",
            observaciones="Carbono Zero esta construyendo tu linea base ambiental.",
        )
    total = sum((item.valor for item in periods), Decimal("0"))
    return LineaBaseAmbiental.objects.create(
        organizacion=indicator.organizacion, indicador=indicator,
        periodo_inicio=min(x.periodo_inicio for x in periods), periodo_fin=max(x.periodo_fin for x in periods),
        estado="suficiente" if len(periods) >= 2 else "construyendo", valor_base=total / len(periods),
        cantidad_periodos=len(periods), observaciones="Promedio deterministico de periodos disponibles.",
    )
