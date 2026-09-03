import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Prefetch

from ..models import (
    IndicadorAmbiental,
    Observacion,
    RegistroFlujoAmbiental,
    ValorIndicador,
)
from .operational_indicators import calendar_month
from .unit_conversion import UnitConversionError, convert_value
from .waste_catalog import WASTE_INDICATOR_SERIES, is_valued_waste_destination


logger = logging.getLogger(__name__)
WASTE_QUANTITY_CONCEPT = "cantidad_residuo"
WASTE_VALUE_SOURCE = "registros_residuo_operacionales_v1"


def waste_indicator_sync_targets(record):
    """Return the work/month pairs affected by the current waste record state."""
    if (
        record.flujo != RegistroFlujoAmbiental.Flujo.RESIDUO
        or not record.obra_id
    ):
        return set()
    timestamps = record.actividad.observaciones.filter(
        concepto=WASTE_QUANTITY_CONCEPT
    ).values_list("timestamp_observacion", flat=True)
    return {
        (record.obra, *calendar_month(timestamp)) for timestamp in timestamps
    }


def _indicator_contract(series_key):
    series = WASTE_INDICATOR_SERIES[series_key]
    return {
        "nombre": series["nombre"],
        "tipo": IndicadorAmbiental.Tipo.OPERACIONAL,
        "alcance": IndicadorAmbiental.Alcance.OBRA,
        "unidad": series["unidad_base"],
        "origen_numerador": series_key,
        "origen_denominador": (
            "masa_generada" if series_key == "tasa_valorizacion_masa" else ""
        ),
        "direccion_deseable": series["direccion_deseable"],
        "activo": True,
    }


def ensure_waste_indicator(work, series_key):
    series = WASTE_INDICATOR_SERIES[series_key]
    contract = _indicator_contract(series_key)
    indicator, created = IndicadorAmbiental.objects.get_or_create(
        organizacion=work.organizacion,
        obra=work,
        codigo=series["codigo"],
        defaults=contract,
    )
    incompatible = [
        field for field, expected in contract.items() if getattr(indicator, field) != expected
    ]
    if incompatible:
        raise ValidationError(
            "El indicador de residuos existente tiene un contrato incompatible: "
            + ", ".join(incompatible)
        )
    return indicator, created


def _waste_records(work, start, end):
    valid_observations = (
        Observacion.objects.filter(
            concepto=WASTE_QUANTITY_CONCEPT,
            valor_numerico__isnull=False,
            timestamp_observacion__date__gte=start,
            timestamp_observacion__date__lte=end,
        )
        .exclude(estado=Observacion.Estado.RECHAZADA)
        .order_by("id")
    )
    return (
        RegistroFlujoAmbiental.objects.filter(
            organizacion=work.organizacion,
            obra=work,
            flujo=RegistroFlujoAmbiental.Flujo.RESIDUO,
            actividad__observaciones__in=valid_observations,
        )
        .select_related("actividad")
        .prefetch_related(
            Prefetch(
                "actividad__observaciones",
                queryset=valid_observations,
                to_attr="waste_indicator_observations",
            )
        )
        .distinct()
        .order_by("id")
    )


def _classification(record):
    if record.clasificacion_residuo:
        return record.clasificacion_residuo
    if record.tipo_recurso in {"no_peligroso", "peligroso"}:
        return record.tipo_recurso
    return ""


def _source(record, observation, target_unit):
    normalized = convert_value(
        observation.valor_numerico, observation.unidad, target_unit
    )
    return {
        "registro_id": record.id,
        "observacion_id": observation.id,
        "actividad_id": record.actividad_id,
        "valor_original": str(observation.valor_numerico),
        "unidad_original": observation.unidad,
        "valor_normalizado": str(normalized["valor_normalizado"]),
        "unidad_normalizada": normalized["unidad_normalizada"],
        "conversion_aplicada": normalized["conversion_aplicada"],
        "regla_conversion": normalized["regla"],
        "factor_conversion": str(normalized["factor_conversion"]),
        "destino_operacional": record.destino_operacional,
        "clasificacion_residuo": _classification(record),
        "tipo_residuo": record.tipo_residuo,
        "tipo_residuo_otro": record.tipo_residuo_otro,
    }


def _sources_by_dimension(work, start, end):
    sources = {"masa": [], "volumen": []}
    targets = {
        "masa": WASTE_INDICATOR_SERIES["masa_generada"]["unidad_base"],
        "volumen": WASTE_INDICATOR_SERIES["volumen_generado"]["unidad_base"],
    }
    for record in _waste_records(work, start, end):
        for observation in record.actividad.waste_indicator_observations:
            matched = False
            for dimension, target_unit in targets.items():
                try:
                    source = _source(record, observation, target_unit)
                except UnitConversionError:
                    continue
                sources[dimension].append(source)
                matched = True
                break
            if not matched:
                logger.warning(
                    "Observacion %s omitida de indicadores de residuos por unidad incompatible %s.",
                    observation.id,
                    observation.unidad,
                )
    return sources


def _metadata(work, start, end, series_key, sources, **extra):
    series = WASTE_INDICATOR_SERIES[series_key]
    return {
        "obra_id": work.id,
        "periodo": {"inicio": start.isoformat(), "fin": end.isoformat()},
        "serie": series_key,
        "dimension": series["dimension"],
        "unidad_agregada": series["unidad_base"],
        "registros_fuente_ids": sorted({source["registro_id"] for source in sources}),
        "observaciones_fuente_ids": [source["observacion_id"] for source in sources],
        "cantidad_fuentes": len(sources),
        "fuentes": sources,
        **extra,
    }


def _store_value(work, start, end, series_key, value, metadata):
    indicator, _ = ensure_waste_indicator(work, series_key)
    latest = (
        ValorIndicador.objects.select_for_update()
        .filter(indicador=indicator, periodo_inicio=start, periodo_fin=end)
        .order_by("-version")
        .first()
    )
    if (
        latest
        and latest.valor == value
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
            valor=value,
            unidad=indicator.unidad,
            fuente_calculo=WASTE_VALUE_SOURCE,
            version=version,
            metadata=metadata,
        ),
        True,
    )


def _mark_unavailable(work, start, end, series_key):
    series = WASTE_INDICATOR_SERIES[series_key]
    indicator = IndicadorAmbiental.objects.filter(
        organizacion=work.organizacion,
        obra=work,
        codigo=series["codigo"],
    ).first()
    if not indicator or not indicator.valores.filter(
        periodo_inicio=start, periodo_fin=end
    ).exists():
        return None
    return _store_value(
        work,
        start,
        end,
        series_key,
        Decimal("0"),
        _metadata(
            work,
            start,
            end,
            series_key,
            [],
            disponible=False,
            estado="sin_fuentes",
        ),
    )


@transaction.atomic
def sync_waste_indicator_month(work, start, end):
    sources = _sources_by_dimension(work, start, end)
    results = {}

    mass_sources = sources["masa"]
    if mass_sources:
        generated = sum(
            (Decimal(source["valor_normalizado"]) for source in mass_sources),
            Decimal("0"),
        )
        valued_sources = [
            source
            for source in mass_sources
            if is_valued_waste_destination(source["destino_operacional"])
        ]
        valuation_sources = [
            {
                **source,
                "incluido_en_serie": is_valued_waste_destination(
                    source["destino_operacional"]
                ),
            }
            for source in mass_sources
        ]
        valued = sum(
            (Decimal(source["valor_normalizado"]) for source in valued_sources),
            Decimal("0"),
        )
        results["masa_generada"] = _store_value(
            work,
            start,
            end,
            "masa_generada",
            generated,
            _metadata(work, start, end, "masa_generada", mass_sources),
        )
        results["masa_valorizada"] = _store_value(
            work,
            start,
            end,
            "masa_valorizada",
            valued,
            _metadata(
                work,
                start,
                end,
                "masa_valorizada",
                valuation_sources,
                registros_valorizados_ids=[
                    source["registro_id"] for source in valued_sources
                ],
            ),
        )
        if generated > 0:
            rate = valued / generated * Decimal("100")
            results["tasa_valorizacion_masa"] = _store_value(
                work,
                start,
                end,
                "tasa_valorizacion_masa",
                rate,
                _metadata(
                    work,
                    start,
                    end,
                    "tasa_valorizacion_masa",
                    mass_sources,
                    masa_generada=str(generated),
                    masa_valorizada=str(valued),
                    formula=WASTE_INDICATOR_SERIES["tasa_valorizacion_masa"]["formula"],
                ),
            )
        else:
            unavailable = _mark_unavailable(
                work, start, end, "tasa_valorizacion_masa"
            )
            if unavailable:
                results["tasa_valorizacion_masa"] = unavailable
    else:
        for series_key in (
            "masa_generada",
            "masa_valorizada",
            "tasa_valorizacion_masa",
        ):
            unavailable = _mark_unavailable(work, start, end, series_key)
            if unavailable:
                results[series_key] = unavailable

    volume_sources = sources["volumen"]
    if volume_sources:
        volume = sum(
            (Decimal(source["valor_normalizado"]) for source in volume_sources),
            Decimal("0"),
        )
        results["volumen_generado"] = _store_value(
            work,
            start,
            end,
            "volumen_generado",
            volume,
            _metadata(work, start, end, "volumen_generado", volume_sources),
        )
    else:
        unavailable = _mark_unavailable(work, start, end, "volumen_generado")
        if unavailable:
            results["volumen_generado"] = unavailable

    return results
