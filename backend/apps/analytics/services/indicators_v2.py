from decimal import Decimal

from django.db.models import Sum

from ..models import LineaBaseAmbiental, ValorIndicador
from ..selectors.quality import (
    baseline_values,
    indicator_inputs,
    next_indicator_value_version,
)


def generate_indicator_value(indicator, start, end):
    impacts, observations = indicator_inputs(indicator, start, end)
    numerator = impacts.aggregate(total=Sum("valor"))["total"] or Decimal("0")
    if indicator.tipo == "intensidad":
        denominator = observations.filter(
            concepto=indicator.origen_denominador
        ).aggregate(total=Sum("valor_numerico"))["total"] or Decimal("0")
        if not denominator:
            raise ValueError("No existe denominador para el periodo.")
        result = numerator / denominator
    elif indicator.origen_numerador == "impactos_ambientales":
        result = numerator
    else:
        result = observations.filter(concepto=indicator.origen_numerador).aggregate(
            total=Sum("valor_numerico")
        )["total"] or Decimal("0")
    version = next_indicator_value_version(indicator, start, end)
    return ValorIndicador.objects.create(
        indicador=indicator,
        periodo_inicio=start,
        periodo_fin=end,
        valor=result,
        unidad=indicator.unidad,
        fuente_calculo="impactos_y_observaciones_v2",
        version=version,
        metadata={"alcance": indicator.alcance, "obra_id": indicator.obra_id},
    )


def build_baseline(indicator):
    values = list(baseline_values(indicator))
    if not values:
        return LineaBaseAmbiental.objects.create(
            organizacion=indicator.organizacion,
            indicador=indicator,
            estado="construyendo",
            observaciones="Carbono Zero esta construyendo tu linea base ambiental.",
        )
    total = sum((item.valor for item in values), Decimal("0"))
    return LineaBaseAmbiental.objects.create(
        organizacion=indicator.organizacion,
        indicador=indicator,
        periodo_inicio=min(x.periodo_inicio for x in values),
        periodo_fin=max(x.periodo_fin for x in values),
        estado="suficiente" if len(values) >= 2 else "construyendo",
        valor_base=total / len(values),
        cantidad_periodos=len(values),
        observaciones="Promedio deterministico de periodos disponibles.",
    )
