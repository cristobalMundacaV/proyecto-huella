import calendar
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from ..models import IndicadorAmbiental, ValorIndicador
from ..selectors.effective_impacts import effective_generated_ghg_impacts


INDICATOR_CODE = "emisiones-gei-generadas"
INDICATOR_CONTRACT = {
    "nombre": "Emisiones GEI generadas",
    "alcance": IndicadorAmbiental.Alcance.OBRA,
    "tipo": IndicadorAmbiental.Tipo.ABSOLUTO,
    "unidad": "tCO2e",
    "origen_numerador": "impactos_gei_generados",
    "origen_denominador": "",
    "direccion_deseable": IndicadorAmbiental.DireccionDeseable.MENOR,
    "activo": True,
}


def calendar_month(value):
    value = value.date() if hasattr(value, "date") else value
    start = date(value.year, value.month, 1)
    end = date(value.year, value.month, calendar.monthrange(value.year, value.month)[1])
    return start, end


def ensure_generated_emissions_indicator(work):
    indicator, created = IndicadorAmbiental.objects.get_or_create(
        organizacion=work.organizacion,
        obra=work,
        codigo=INDICATOR_CODE,
        defaults=INDICATOR_CONTRACT,
    )
    incompatible = [
        field
        for field, expected in INDICATOR_CONTRACT.items()
        if getattr(indicator, field) != expected
    ]
    if incompatible:
        raise ValidationError(
            "El indicador existente emisiones-gei-generadas tiene un contrato "
            f"incompatible: {', '.join(incompatible)}."
        )
    return indicator, created


def _source_metadata(work, start, end, impacts):
    sources = [
        {
            "impacto_id": impact.id,
            "calculo_id": impact.calculo_id,
            "actividad_id": impact.actividad_id,
            "valor": str(impact.valor),
        }
        for impact in impacts
    ]
    return {
        "obra_id": work.id,
        "periodo": {"inicio": start.isoformat(), "fin": end.isoformat()},
        "impactos_efectivos_ids": [item["impacto_id"] for item in sources],
        "calculos_fuente_ids": [item["calculo_id"] for item in sources],
        "cantidad_fuentes": len(sources),
        "filtro_indicador": {
            "origen_numerador": "impactos_gei_generados",
            "tipo_impacto": "generado",
            "unidad": "tCO2e",
            "version_efectiva": "ultimo_calculo_por_actividad",
        },
        "unidad_agregada": "tCO2e",
        "fuentes": sources,
    }


@transaction.atomic
def sync_generated_emissions_month(work, start, end):
    indicator, _ = ensure_generated_emissions_indicator(work)
    impacts = list(effective_generated_ghg_impacts(work.organizacion, work, start, end))
    metadata = _source_metadata(work, start, end, impacts)
    value = sum((impact.valor for impact in impacts), Decimal("0"))
    latest = (
        ValorIndicador.objects.select_for_update()
        .filter(indicador=indicator, periodo_inicio=start, periodo_fin=end)
        .order_by("-version")
        .first()
    )
    if (
        latest
        and latest.valor == value
        and latest.unidad == "tCO2e"
        and latest.metadata == metadata
    ):
        return latest, False
    version = (
        ValorIndicador.objects.filter(
            indicador=indicator, periodo_inicio=start, periodo_fin=end
        ).aggregate(max_version=Max("version"))["max_version"]
        or 0
    ) + 1
    return (
        ValorIndicador.objects.create(
            indicador=indicator,
            periodo_inicio=start,
            periodo_fin=end,
            valor=value,
            unidad="tCO2e",
            fuente_calculo="impactos_gei_generados_efectivos_v1",
            version=version,
            metadata=metadata,
        ),
        True,
    )


def sync_generated_emissions_for_impact(impact):
    work = impact.actividad.obra
    if not work:
        return None, False
    start, end = calendar_month(impact.timestamp)
    return sync_generated_emissions_month(work, start, end)
