from decimal import Decimal

from django.db import transaction

from ..models import CalculoAmbiental, FormulaAmbiental, InputCalculoAmbiental
from .impact_v2 import create_generated_impact
from .methodology_selector import select_methodology


def _apply_formula(formula, inputs, factor):
    values = {key: observation.valor_numerico for key, (_, observation) in inputs.items()}
    if formula.tipo == FormulaAmbiental.Tipo.TRANSPORTE_TKM:
        return values["masa"] * values["distancia"] * factor
    if formula.tipo == FormulaAmbiental.Tipo.TRANSPORTE_VEHICULO_KM:
        return values["distancia"] * factor
    if formula.tipo == FormulaAmbiental.Tipo.TRANSPORTE_COMBUSTIBLE:
        return values["combustible"] * factor
    raise ValueError("Tipo de formula no soportado.")


@transaction.atomic
def calculate_activity(actividad):
    selection = select_methodology(actividad)
    selected = selection["seleccion"]
    if not selected:
        raise ValueError(selection["razon"])
    eligibility = selected["elegibilidad"]
    formula = selected["formula"]
    factor_version = eligibility["factor_version"]
    result = _apply_formula(formula, eligibility["inputs"], Decimal(factor_version.valor))
    internal_version = actividad.calculos_ambientales.count() + 1
    calculation = CalculoAmbiental.objects.create(
        organizacion=actividad.organizacion, actividad=actividad,
        version_metodologia=selected["version_metodologia"], formula=formula, version_factor=factor_version,
        resultado=result, unidad_resultado=formula.factor_ambiental.unidad_resultado,
        formula_aplicada=formula.expresion_legible, version_interna=internal_version,
        advertencias=eligibility["advertencias"], completitud=eligibility["estado"],
        snapshot_tecnico={"factor_valor": str(factor_version.valor), "formula_tipo": formula.tipo},
    )
    for variable, observation in eligibility["inputs"].values():
        InputCalculoAmbiental.objects.create(
            calculo=calculation, variable=variable, observacion=observation,
            valor_utilizado=observation.valor_numerico, unidad=observation.unidad,
            concepto=observation.concepto, fuente=observation.fuente,
            evidencia=observation.evidencia, version_evidencia=observation.version_evidencia,
        )
    create_generated_impact(calculation)
    return calculation, selection
