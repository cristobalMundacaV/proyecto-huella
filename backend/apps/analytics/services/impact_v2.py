from ..models import ImpactoAmbiental


def create_generated_impact(calculation):
    type_map = {
        "emision": ImpactoAmbiental.Tipo.GENERADO,
        "reduccion": ImpactoAmbiental.Tipo.REDUCCION,
        "emision_evitada": ImpactoAmbiental.Tipo.EVITADO,
        "remocion": ImpactoAmbiental.Tipo.CAPTURA_REMOCION,
        "compensacion": ImpactoAmbiental.Tipo.COMPENSACION,
        "otro": ImpactoAmbiental.Tipo.OTRO,
    }
    return ImpactoAmbiental.objects.create(
        organizacion=calculation.organizacion, actividad=calculation.actividad, calculo=calculation,
        tipo=type_map.get(calculation.tipo_resultado, ImpactoAmbiental.Tipo.GENERADO), categoria=calculation.version_metodologia.metodologia.categoria,
        valor=calculation.resultado, unidad=calculation.unidad_resultado,
        timestamp=calculation.actividad.timestamp_inicio,
    )
