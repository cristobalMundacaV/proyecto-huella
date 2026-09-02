import calendar
import logging
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from ..models import IndicadorAmbiental, Observacion, ValorIndicador
from .unit_conversion import UnitConversionError, convert_value


logger = logging.getLogger(__name__)

OPERATIONAL_INDICATOR_CONTRACTS = {
    "consumo_agua": {
        "codigo": "consumo-agua",
        "nombre": "Consumo de agua",
        "tipo": IndicadorAmbiental.Tipo.OPERACIONAL,
        "alcance": IndicadorAmbiental.Alcance.OBRA,
        "unidad": "m3",
        "origen_numerador": "consumo_agua",
        "origen_denominador": "",
        "direccion_deseable": IndicadorAmbiental.DireccionDeseable.MENOR,
        "activo": True,
    }
}


def calendar_month(value):
    if hasattr(value, "date"):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        value = value.date()
    start = date(value.year, value.month, 1)
    end = date(value.year, value.month, calendar.monthrange(value.year, value.month)[1])
    return start, end


def ensure_operational_indicator(work, concept):
    contract = OPERATIONAL_INDICATOR_CONTRACTS.get(concept)
    if not contract:
        return None, False
    indicator, created = IndicadorAmbiental.objects.get_or_create(
        organizacion=work.organizacion,
        obra=work,
        codigo=contract["codigo"],
        defaults=contract,
    )
    incompatible = [
        field for field, expected in contract.items() if getattr(indicator, field) != expected
    ]
    if incompatible:
        raise ValidationError(
            "El indicador operacional existente tiene un contrato incompatible: "
            + ", ".join(incompatible)
        )
    return indicator, created


def _effective_sources(work, concept, start, end, target_unit):
    observations = (
        Observacion.objects.filter(
            organizacion=work.organizacion,
            actividad__obra=work,
            concepto=concept,
            valor_numerico__isnull=False,
            timestamp_observacion__date__gte=start,
            timestamp_observacion__date__lte=end,
        )
        .exclude(estado=Observacion.Estado.RECHAZADA)
        .select_related("actividad")
        .order_by("id")
    )
    sources = []
    for observation in observations:
        try:
            normalized = convert_value(
                observation.valor_numerico, observation.unidad, target_unit
            )
        except UnitConversionError:
            logger.warning(
                "Observacion %s omitida del indicador %s por unidad incompatible %s.",
                observation.id,
                concept,
                observation.unidad,
            )
            continue
        sources.append(
            {
                "observacion_id": observation.id,
                "actividad_id": observation.actividad_id,
                "valor_original": str(observation.valor_numerico),
                "unidad_original": observation.unidad,
                "valor_normalizado": str(normalized["valor_normalizado"]),
                "unidad_normalizada": normalized["unidad_normalizada"],
                "conversion_aplicada": normalized["conversion_aplicada"],
                "regla_conversion": normalized["regla"],
                "factor_conversion": str(normalized["factor_conversion"]),
            }
        )
    return sources


@transaction.atomic
def sync_operational_indicator_month(work, concept, start, end):
    indicator, _ = ensure_operational_indicator(work, concept)
    if indicator is None:
        return None, False
    sources = _effective_sources(work, concept, start, end, indicator.unidad)
    total = sum(
        (Decimal(source["valor_normalizado"]) for source in sources), Decimal("0")
    )
    metadata = {
        "obra_id": work.id,
        "periodo": {"inicio": start.isoformat(), "fin": end.isoformat()},
        "concepto": concept,
        "unidad_agregada": indicator.unidad,
        "observaciones_fuente_ids": [source["observacion_id"] for source in sources],
        "actividades_fuente_ids": sorted(
            {source["actividad_id"] for source in sources if source["actividad_id"]}
        ),
        "cantidad_fuentes": len(sources),
        "fuentes": sources,
    }
    latest = (
        ValorIndicador.objects.select_for_update()
        .filter(indicador=indicator, periodo_inicio=start, periodo_fin=end)
        .order_by("-version")
        .first()
    )
    if (
        latest
        and latest.valor == total
        and latest.unidad == indicator.unidad
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
            valor=total,
            unidad=indicator.unidad,
            fuente_calculo="observaciones_operacionales_efectivas_v1",
            version=version,
            metadata=metadata,
        ),
        True,
    )


def sync_operational_indicators_for_observation(observation):
    if observation.concepto not in OPERATIONAL_INDICATOR_CONTRACTS:
        return None, False
    work = getattr(observation.actividad, "obra", None) if observation.actividad else None
    if not work:
        return None, False
    start, end = calendar_month(observation.timestamp_observacion)
    return sync_operational_indicator_month(work, observation.concepto, start, end)
