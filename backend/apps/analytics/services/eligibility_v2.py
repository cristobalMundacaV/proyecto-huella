from django.db.models import Q

from ..models import Observacion, VersionFactorAmbiental


def active_factor_version(formula, organizacion):
    queryset = VersionFactorAmbiental.objects.filter(
        factor=formula.factor_ambiental, estado=VersionFactorAmbiental.Estado.ACTIVO,
    ).filter(
        Q(factor__organizacion__isnull=True) |
        Q(factor__organizacion=organizacion)
    )
    return queryset.order_by("-version").first()


def evaluate_formula(actividad, formula):
    factor_version = active_factor_version(formula, actividad.organizacion)
    reasons, warnings, inputs = [], [], {}
    if not factor_version:
        reasons.append("No existe una version activa y aplicable del factor.")
    for variable in formula.variables.all():
        observations = list(actividad.observaciones.filter(
            concepto=variable.concepto_observacion,
        ).exclude(estado=Observacion.Estado.RECHAZADA).select_related("fuente", "evidencia", "version_evidencia"))
        if len(observations) > 1:
            reasons.append(f"Existen multiples observaciones para {variable.concepto_observacion}; requiere revision.")
            continue
        if not observations:
            if variable.obligatoria:
                reasons.append(f"Falta la variable critica {variable.concepto_observacion}.")
            else:
                warnings.append(f"Falta la variable complementaria {variable.concepto_observacion}.")
            continue
        observation = observations[0]
        if observation.valor_numerico is None:
            reasons.append(f"{variable.concepto_observacion} no tiene valor numerico.")
        elif observation.unidad.lower() != variable.unidad_esperada.lower():
            reasons.append(f"Unidad incompatible para {variable.concepto_observacion}: {observation.unidad}.")
        else:
            inputs[variable.clave] = (variable, observation)

    vehicle = actividad.activos.filter(tipo="vehiculo").select_related("vehiculo").first()
    if formula.tipo in {"transporte_vehiculo_km", "transporte_combustible"}:
        if not vehicle:
            reasons.append("La actividad no tiene un vehiculo asociado.")
        elif factor_version:
            context = formula.factor_ambiental.contexto or {}
            if formula.tipo == "transporte_vehiculo_km" and context.get("tipo_vehiculo"):
                vehicle_type = getattr(getattr(vehicle, "vehiculo", None), "tipo_vehiculo", "")
                if vehicle_type != context["tipo_vehiculo"]:
                    reasons.append("El factor no es compatible con el tipo de vehiculo.")
            if formula.tipo == "transporte_combustible" and context.get("combustible"):
                fuel = getattr(getattr(vehicle, "vehiculo", None), "combustible", "")
                if fuel.lower() != str(context["combustible"]).lower():
                    reasons.append("El factor no es compatible con el combustible del vehiculo.")

    status = "no_calculable" if reasons else ("calculable_incompleto" if warnings else "calculable_completo")
    return {"estado": status, "motivos": reasons, "advertencias": warnings, "inputs": inputs,
            "factor_version": factor_version}
