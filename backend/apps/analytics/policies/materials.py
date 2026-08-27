def tenant_relation_errors(data, organization, fields, instance=None):
    errors = {}
    for field in fields:
        value = data.get(field, getattr(instance, field, None))
        if value and value.organizacion_id != organization.id:
            errors[field] = "La referencia pertenece a otra organizacion."
    return errors


def material_event_errors(data, organization, instance=None):
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
    return errors
