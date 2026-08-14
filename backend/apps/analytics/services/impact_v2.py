from ..models import ImpactoAmbiental


def create_generated_impact(calculation):
    return ImpactoAmbiental.objects.create(
        organizacion=calculation.organizacion, actividad=calculation.actividad, calculo=calculation,
        tipo=ImpactoAmbiental.Tipo.GENERADO, categoria=calculation.version_metodologia.metodologia.categoria,
        valor=calculation.resultado, unidad=calculation.unidad_resultado,
        timestamp=calculation.actividad.timestamp_inicio,
    )
