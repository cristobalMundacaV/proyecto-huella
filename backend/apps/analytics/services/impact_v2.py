import logging

from django.db import transaction

from ..models import ImpactoAmbiental


logger = logging.getLogger(__name__)


def create_generated_impact(calculation):
    type_map = {
        "emision": ImpactoAmbiental.Tipo.GENERADO,
        "reduccion": ImpactoAmbiental.Tipo.REDUCCION,
        "emision_evitada": ImpactoAmbiental.Tipo.EVITADO,
        "remocion": ImpactoAmbiental.Tipo.CAPTURA_REMOCION,
        "compensacion": ImpactoAmbiental.Tipo.COMPENSACION,
        "otro": ImpactoAmbiental.Tipo.OTRO,
    }
    impact = ImpactoAmbiental.objects.create(
        organizacion=calculation.organizacion, actividad=calculation.actividad, calculo=calculation,
        tipo=type_map.get(calculation.tipo_resultado, ImpactoAmbiental.Tipo.GENERADO), categoria=calculation.version_metodologia.metodologia.categoria,
        valor=calculation.resultado, unidad=calculation.unidad_resultado,
        timestamp=calculation.actividad.timestamp_inicio,
    )
    from .generated_emissions_indicator import sync_generated_emissions_for_impact

    try:
        with transaction.atomic():
            sync_generated_emissions_for_impact(impact)
    except Exception:
        logger.exception(
            "No se pudo sincronizar el indicador GEI para el impacto %s; "
            "el calculo y el impacto se conservan para backfill.",
            impact.id,
        )
    return impact
