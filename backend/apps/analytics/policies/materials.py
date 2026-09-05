def tenant_relation_errors(data, organization, fields, instance=None):
    errors = {}
    for field in fields:
        value = data.get(field, getattr(instance, field, None))
        if value and value.organizacion_id != organization.id:
            errors[field] = "La referencia pertenece a otra organizacion."
    return errors


def material_event_errors(data, organization, instance=None):
    from decimal import Decimal

    from ..models import EventoMaterial
    from ..services.unit_conversion import UnitConversionError, convert_value

    fields = (
        "material",
        "lote",
        "actividad",
        "evento_origen",
        "obra",
        "proceso",
        "fuente",
        "evidencia",
        "version_evidencia",
        "observacion_cantidad",
    )
    errors = tenant_relation_errors(data, organization, fields, instance)
    amount, unit = data.get("cantidad"), data.get("unidad")
    source = data.get("fuente", getattr(instance, "fuente", None))
    if amount is not None and not unit:
        errors["unidad"] = "Debe indicar la unidad de la cantidad."
    if amount is not None and not source:
        errors["fuente"] = "Debe indicar la fuente de la cantidad."
    evidence = data.get("evidencia", getattr(instance, "evidencia", None))
    version = data.get(
        "version_evidencia", getattr(instance, "version_evidencia", None)
    )
    if version and evidence and version.evidencia_id != evidence.id:
        errors["version_evidencia"] = "La version no pertenece a la evidencia asociada."
    event_type = data.get("tipo", getattr(instance, "tipo", None))
    origin = data.get("evento_origen", getattr(instance, "evento_origen", None))
    if origin and event_type in {EventoMaterial.Tipo.USO, EventoMaterial.Tipo.CONSUMO}:
        material = data.get("material", getattr(instance, "material", None))
        work = data.get("obra", getattr(instance, "obra", None))
        event_date = data.get("fecha_hora", getattr(instance, "fecha_hora", None))
        if origin.tipo != EventoMaterial.Tipo.RECEPCION:
            errors["evento_origen"] = "El evento origen debe ser una recepcion."
        elif origin.material_id != getattr(material, "id", None):
            errors["evento_origen"] = "La recepcion debe corresponder al mismo material."
        elif origin.obra_id != getattr(work, "id", None):
            errors["evento_origen"] = "La recepcion debe pertenecer a la misma obra."
        elif event_date and origin.fecha_hora > event_date:
            errors["evento_origen"] = "La recepcion no puede ser posterior al movimiento."
        origin_quantity = origin.observacion_cantidad
        target_unit = unit or getattr(
            getattr(instance, "observacion_cantidad", None), "unidad", None
        )
        if not origin_quantity or not target_unit:
            errors["evento_origen"] = (
                "La recepcion debe tener una cantidad y unidad trazables."
            )
        else:
            try:
                convert_value(Decimal("1"), origin_quantity.unidad, target_unit)
            except UnitConversionError:
                errors["evento_origen"] = (
                    "La unidad de la recepcion no es compatible con la del movimiento."
                )
    return errors
