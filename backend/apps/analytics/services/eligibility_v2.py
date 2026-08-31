from django.db.models import Q
from django.utils import timezone

from ..models import EvaluacionCalidadDato, Observacion, VersionFactorAmbiental
from .observation_resolver import resolve_observation
from .fuel_classification import activity_fuel_classification, activity_fuel_type
from .fuel_factor_selector import select_fuel_factor
from .unit_conversion import UnitConversionError, convert_value
from .quality_v2 import ensure_current_quality_evaluation


def active_factor_version(formula, organizacion):
    today = timezone.localdate()
    queryset = VersionFactorAmbiental.objects.filter(
        factor=formula.factor_ambiental, estado=VersionFactorAmbiental.Estado.ACTIVO,
    ).filter(
        Q(factor__organizacion__isnull=True) |
        Q(factor__organizacion=organizacion)
    ).filter(
        Q(vigencia_desde__isnull=True) | Q(vigencia_desde__lte=today),
        Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=today),
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
            if item.clave == "combustible"
            or "combustible" in item.concepto_observacion
        ),
        variables[0] if len(variables) == 1 else None,
    )
    return variable.unidad_esperada if variable else ""


def evaluate_formula(actividad, formula):
    reasons, warnings, inputs, normalizations = [], [], {}, {}
    record = getattr(actividad, "registro_flujo_ambiental", None)
    work = record.obra if record else actividad.obra
    record_date = record.periodo_inicio.date() if record else actividad.timestamp_inicio.date()
    if work and work.fecha_inicio and record_date < work.fecha_inicio:
        reasons.append("El registro es anterior al inicio de la obra y no puede alimentar cálculos ambientales.")
    if work and work.fecha_termino_estimada and record_date > work.fecha_termino_estimada:
        reasons.append("El registro es posterior al término de la obra y no puede alimentar cálculos ambientales.")
    fuel_classification = activity_fuel_classification(actividad)
    fuel_factor_selection = None
    if fuel_classification:
        fuel_factor_selection = select_fuel_factor(
            actividad.organizacion,
            fuel_classification,
            activity_fuel_type(actividad),
            _fuel_required_unit(formula),
            actividad.timestamp_inicio,
        )
        factor_version = fuel_factor_selection["factor_version"]
    else:
        factor_version = active_factor_version(formula, actividad.organizacion)
    if fuel_classification and fuel_classification.get("estado") in {
        "requiere_clasificacion",
        "requiere_revision",
    }:
        reasons.append(
            "El uso del combustible requiere clasificación como fuente móvil "
            "o estacionaria antes de calcular emisiones."
        )
    if not factor_version:
        reasons.append(
            fuel_factor_selection["razon"]
            if fuel_factor_selection
            else "No existe una version activa y aplicable del factor."
        )
    elif formula.tipo == "transporte_tkm" and factor_version.factor.unidad_entrada.lower() not in {"t.km", "t·km", "tkm"}:
        reasons.append("La unidad de entrada del factor no es compatible con t.km.")
    elif formula.tipo in {"transporte_vehiculo_km"} and factor_version.factor.unidad_entrada.lower() != "km":
        reasons.append("La unidad de entrada del factor no es compatible con vehículo.km.")
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
                normalization = convert_value(
                    observation.valor_numerico,
                    observation.unidad,
                    variable.unidad_esperada,
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

    vehicle = actividad.activos.filter(tipo="vehiculo").select_related("vehiculo").first()
    if formula.tipo in {"transporte_vehiculo_km", "transporte_combustible"}:
        if not vehicle:
            reasons.append("La actividad no tiene un vehiculo asociado.")
        elif factor_version:
            context = factor_version.factor.contexto or {}
            if formula.tipo == "transporte_vehiculo_km" and context.get("tipo_vehiculo"):
                vehicle_type = getattr(getattr(vehicle, "vehiculo", None), "tipo_vehiculo", "")
                if vehicle_type != context["tipo_vehiculo"]:
                    reasons.append("El factor no es compatible con el tipo de vehiculo.")
            if formula.tipo == "transporte_combustible" and context.get("combustible"):
                fuel = getattr(getattr(vehicle, "vehiculo", None), "combustible", "")
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
    }
