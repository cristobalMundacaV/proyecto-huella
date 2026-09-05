from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import CalculoAmbiental, FormulaAmbiental, InputCalculoAmbiental
from .impact_v2 import create_generated_impact
from .methodology_selector import select_methodology


def _transport_tkm(values, factor):
    return values["masa"] * values["distancia"] * factor


def _transport_vehicle_km(values, factor):
    return values["distancia"] * factor


def _consumed_fuel(values, factor):
    value = values.get("combustible_consumido", values.get("combustible"))
    if value is None:
        raise ValidationError("La formula requiere combustible_consumido.")
    return value * factor


def _consumed_energy(values, factor):
    value = values.get("energia_consumida")
    if value is None:
        raise ValidationError("La formula requiere energia_consumida.")
    return value * factor


def _material_quantity(values, factor):
    return values["cantidad_material_normalizada"] * factor


FORMULA_HANDLERS = {
    FormulaAmbiental.Tipo.TRANSPORTE_TKM: _transport_tkm,
    FormulaAmbiental.Tipo.TRANSPORTE_VEHICULO_KM: _transport_vehicle_km,
    FormulaAmbiental.Tipo.TRANSPORTE_COMBUSTIBLE: _consumed_fuel,
    FormulaAmbiental.Tipo.COMBUSTIBLE_CONSUMIDO: _consumed_fuel,
    FormulaAmbiental.Tipo.ENERGIA_CONSUMIDA: _consumed_energy,
    FormulaAmbiental.Tipo.MATERIAL_CANTIDAD: _material_quantity,
}


def _apply_formula(formula, inputs, factor):
    values = {
        key: normalization["valor_normalizado"]
        for key, (_, _, normalization) in inputs.items()
    }
    handler = FORMULA_HANDLERS.get(formula.tipo)
    if not handler:
        raise ValidationError("La fórmula no tiene una estrategia registrada y segura.")
    return handler(values, factor)


def _validate_result_context(result_type, context):
    if result_type not in {"reduccion", "emision_evitada", "remocion", "compensacion"}:
        return
    required = {"referencia", "metodo", "evidencia", "periodo", "alcance"}
    missing = sorted(required - set(context or {}))
    if missing:
        raise ValidationError(f"El resultado {result_type} requiere: {', '.join(missing)}.")


@transaction.atomic
def calculate_activity(actividad, *, result_context=None, recalculation_of=None, recalculation_reason=""):
    selection = select_methodology(actividad)
    selected = selection["seleccion"]
    if not selected:
        raise ValueError(selection["razon"])
    eligibility = selected["elegibilidad"]
    formula = selected["formula"]
    factor_version = eligibility["factor_version"]
    result_type = selected["version_metodologia"].tipo_resultado
    _validate_result_context(result_type, result_context)
    result = _apply_formula(formula, eligibility["inputs"], Decimal(factor_version.valor))
    internal_version = actividad.calculos_ambientales.count() + 1
    calculation = CalculoAmbiental.objects.create(
        organizacion=actividad.organizacion, actividad=actividad,
        version_metodologia=selected["version_metodologia"], formula=formula, version_factor=factor_version,
        resultado=result, unidad_resultado=factor_version.factor.unidad_resultado,
        formula_aplicada=formula.expresion_legible, version_interna=internal_version,
        advertencias=eligibility["advertencias"], completitud=eligibility["estado"],
        tipo_resultado=result_type, recalculo_de=recalculation_of, motivo_recalculo=recalculation_reason,
        snapshot_tecnico={
            "metodologia_id": selected["version_metodologia"].metodologia_id,
            "metodologia_codigo": selected["version_metodologia"].metodologia.codigo,
            "metodologia_version": selected["version_metodologia"].version,
            "version_metodologia_id": selected["version_metodologia"].id,
            "formula_id": formula.id, "formula_tipo": formula.tipo,
            "version_factor_id": factor_version.id, "factor_id": factor_version.factor_id,
            "factor_codigo": factor_version.factor.codigo,
            "factor_valor": str(factor_version.valor), "factor_fuente": factor_version.fuente,
            "factor_referencia": factor_version.referencia,
            "factor_contexto": factor_version.contexto or factor_version.factor.contexto,
            "evento_material": eligibility.get("evento_material"),
            "material": eligibility.get("material"),
            "especificidad_factor": eligibility.get("especificidad_factor"),
            "factor_vigencia": {"desde": str(factor_version.vigencia_desde or ""), "hasta": str(factor_version.vigencia_hasta or "")},
            "tipo_resultado": result_type, "unidad_resultado": factor_version.factor.unidad_resultado,
            "resultado": str(result),
            "contexto_resultado": result_context or {}, "decision": selection["razon"],
            "candidatos": [{"metodo": item["metodo"], "estado": item["estado"], "motivos": item["motivos"]}
                           for item in selection["candidatos"]],
            "inputs": [{"variable_id": variable.id, "clave": variable.clave, "observacion_id": observation.id,
                        "valor_original": str(observation.valor_numerico), "unidad_original": observation.unidad,
                        "valor": str(normalization["valor_normalizado"]),
                        "unidad": normalization["unidad_normalizada"],
                        "conversion_aplicada": normalization["conversion_aplicada"],
                        "regla_conversion": normalization["regla"],
                        "factor_conversion": str(normalization["factor_conversion"]),
                        "fuente_id": observation.fuente_id, "evidencia_id": observation.evidencia_id,
                        "version_evidencia_id": observation.version_evidencia_id}
                       for variable, observation, normalization in eligibility["inputs"].values()],
        },
    )
    for variable, observation, normalization in eligibility["inputs"].values():
        InputCalculoAmbiental.objects.create(
            calculo=calculation, variable=variable, observacion=observation,
            valor_utilizado=normalization["valor_normalizado"],
            unidad=normalization["unidad_normalizada"],
            concepto=observation.concepto, fuente=observation.fuente,
            evidencia=observation.evidencia, version_evidencia=observation.version_evidencia,
        )
    create_generated_impact(calculation)
    return calculation, selection


def recalculate(calculation, reason, *, result_context=None):
    if not reason or not reason.strip():
        raise ValidationError("El motivo del recálculo es obligatorio.")
    return calculate_activity(calculation.actividad, result_context=result_context,
                              recalculation_of=calculation, recalculation_reason=reason.strip())
