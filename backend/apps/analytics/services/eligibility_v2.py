from django.db.models import Q
from django.utils import timezone

from ..models import EvaluacionCalidadDato, Observacion, VersionFactorAmbiental
from .observation_resolver import resolve_observation
from .fuel_classification import (
    activity_fuel_classification,
    activity_fuel_type,
    activity_vehicle,
)
from .fuel_factor_selector import select_fuel_factor
from .unit_conversion import UnitConversionError, convert_value
from .quality_v2 import ensure_current_quality_evaluation
from .material_factor_selector import select_material_factor


def _operational_date(value):
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.date()


def active_factor_version(formula, organizacion, effective_date=None):
    effective_date = effective_date or timezone.localdate()
    queryset = VersionFactorAmbiental.objects.filter(
        factor=formula.factor_ambiental, estado=VersionFactorAmbiental.Estado.ACTIVO,
    ).filter(
        Q(factor__organizacion__isnull=True) |
        Q(factor__organizacion=organizacion)
    ).filter(
        Q(vigencia_desde__isnull=True) | Q(vigencia_desde__lte=effective_date),
        Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=effective_date),
    )
    for version in queryset.order_by("-version"):
        allowed_methods = (version.factor.contexto or {}).get("formula_tipos", [])
        if not allowed_methods or formula.tipo in allowed_methods:
            return version
    return None


def _fuel_required_unit(formula):
    variables = list(formula.variables.all())
    variable = next(
        (
            item
            for item in variables
            if item.clave in {"combustible", "combustible_consumido"}
            or "combustible" in item.concepto_observacion
        ),
        variables[0] if len(variables) == 1 else None,
    )
    return variable.unidad_esperada if variable else ""


def evaluate_formula(actividad, formula):
    reasons, warnings, inputs, normalizations = [], [], {}, {}
    record = getattr(actividad, "registro_flujo_ambiental", None)
    work = record.obra if record else actividad.obra
    record_date = _operational_date(
        record.periodo_inicio if record else actividad.timestamp_inicio
    )
    if work and work.fecha_inicio and record_date < work.fecha_inicio:
        reasons.append("El registro es anterior al inicio de la obra y no puede alimentar cálculos ambientales.")
    if work and work.fecha_termino_estimada and record_date > work.fecha_termino_estimada:
        reasons.append("El registro es posterior al término de la obra y no puede alimentar cálculos ambientales.")
    fuel_classification = activity_fuel_classification(actividad)
    fuel_factor_selection = None
    dynamic_fuel_formula = (
        (
            formula.tipo == "transporte_combustible"
            and (
                formula.factor_ambiental_id is None
                or (
                    fuel_classification is not None
                    and actividad.tipo != "transporte"
                )
            )
        )
        or (
            formula.tipo == "combustible_consumido"
            and formula.factor_ambiental_id is None
        )
    )
    material_event = getattr(actividad, "evento_material", None)
    material_factor_selection = None
    if formula.tipo == "material_cantidad":
        if not material_event or material_event.tipo != "recepcion":
            reasons.append("Este movimiento no es un punto contable de la metodologia de material recibido.")
            factor_version = None
        else:
            observation = material_event.observacion_cantidad
            material_factor_selection = select_material_factor(
                actividad.organizacion, material_event.material,
                observation.unidad if observation else "", record_date,
            )
            factor_version = material_factor_selection["factor_version"]
    elif dynamic_fuel_formula:
        fuel_factor_selection = select_fuel_factor(
            actividad.organizacion,
            fuel_classification,
            activity_fuel_type(actividad),
            _fuel_required_unit(formula),
            actividad.timestamp_inicio,
        )
        factor_version = fuel_factor_selection["factor_version"]
    else:
        factor_version = active_factor_version(
            formula, actividad.organizacion, record_date
        )
    if dynamic_fuel_formula and fuel_classification and fuel_classification.get("estado") in {
        "requiere_clasificacion",
        "requiere_revision",
    }:
        reasons.append(
            "El uso del combustible requiere clasificación como fuente móvil "
            "o estacionaria antes de calcular emisiones."
        )
        if fuel_classification.get("razon"):
            reasons.append(fuel_classification["razon"])
    if not factor_version and formula.tipo != "material_cantidad":
        reasons.append(
            fuel_factor_selection["razon"]
            if fuel_factor_selection
            else "No existe una version activa y aplicable del factor."
        )
    elif formula.tipo == "transporte_tkm" and factor_version.factor.unidad_entrada.lower() not in {"t.km", "t·km", "tkm"}:
        reasons.append("La unidad de entrada del factor no es compatible con t.km.")
    elif formula.tipo in {"transporte_vehiculo_km"} and factor_version.factor.unidad_entrada.lower() != "km":
        reasons.append("La unidad de entrada del factor no es compatible con vehículo.km.")
    if formula.tipo == "material_cantidad" and material_event and material_event.tipo == "recepcion" and not factor_version:
        reasons.append(material_factor_selection["razon"])
    for variable in formula.variables.all():
        resolution = resolve_observation(actividad, variable.concepto_observacion)
        observation = resolution["observacion"]
        if resolution["estado"] == "requiere_revision":
            reasons.append(f"Existen multiples observaciones para {variable.concepto_observacion}; requiere revision.")
            continue
        if not observation:
            criticality = getattr(variable, "criticidad", "critica" if variable.obligatoria else "complementaria")
            if criticality == "critica":
                reasons.append(f"Falta la variable critica {variable.concepto_observacion}.")
            elif criticality == "complementaria":
                warnings.append(f"Falta la variable complementaria {variable.concepto_observacion}.")
            continue
        quality = ensure_current_quality_evaluation(observation)
        if quality.estado in {
            EvaluacionCalidadDato.Estado.REQUIERE_REVISION,
            EvaluacionCalidadDato.Estado.NO_CONFIABLE,
            EvaluacionCalidadDato.Estado.NO_CALCULABLE,
        }:
            reasons.append(
                f"{variable.concepto_observacion} no puede calcularse mientras su calidad requiera revisión: "
                + " ".join(quality.motivos)
            )
            continue
        if observation.valor_numerico is None:
            reasons.append(f"{variable.concepto_observacion} no tiene valor numerico.")
        else:
            try:
                target_unit = factor_version.factor.unidad_entrada if formula.tipo == "material_cantidad" and factor_version else variable.unidad_esperada
                normalization = convert_value(
                    observation.valor_numerico,
                    observation.unidad,
                    target_unit,
                )
            except UnitConversionError as error:
                reasons.append(str(error))
            else:
                inputs[variable.clave] = (variable, observation, normalization)
                normalizations[variable.clave] = {
                    "variable_id": variable.id,
                    "observacion_id": observation.id,
                    **normalization,
                }

    vehicle = activity_vehicle(actividad)
    if formula.tipo in {"transporte_vehiculo_km", "transporte_combustible"}:
        if not vehicle:
            reasons.append("La actividad no tiene un vehiculo asociado.")
        elif factor_version:
            context = factor_version.factor.contexto or {}
            if formula.tipo == "transporte_vehiculo_km" and context.get("tipo_vehiculo"):
                vehicle_type = vehicle.tipo_vehiculo
                if vehicle_type != context["tipo_vehiculo"]:
                    reasons.append("El factor no es compatible con el tipo de vehiculo.")
            if formula.tipo == "transporte_combustible" and context.get("combustible"):
                fuel = vehicle.combustible
                if fuel.lower() != str(context["combustible"]).lower():
                    reasons.append("El factor no es compatible con el combustible del vehiculo.")

    status = "no_calculable" if reasons else ("calculable_incompleto" if warnings else "calculable_completo")
    return {
        "estado": status,
        "motivos": reasons,
        "advertencias": warnings,
        "inputs": inputs,
        "normalizaciones": normalizations,
        "clasificacion_combustible": fuel_classification,
        "seleccion_factor_combustible": fuel_factor_selection,
        "factor_version": factor_version,
        "seleccion_factor_material": material_factor_selection,
        "especificidad_factor": material_factor_selection.get("especificidad") if material_factor_selection else None,
        "evento_material": {"id": material_event.id, "tipo": material_event.tipo} if material_event else None,
        "material": ({"id": material_event.material_id, "codigo": material_event.material.codigo, "nombre": material_event.material.nombre, "categoria": material_event.material.categoria} if material_event else None),
    }
