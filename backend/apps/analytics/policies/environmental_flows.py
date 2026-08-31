def point_relation_errors(data, organization, instance=None):
    errors = {}
    for field in ("activo", "unidad_operacional", "proceso_operacional", "obra"):
        value = data.get(field, getattr(instance, field, None))
        if value and value.organizacion_id != organization.id:
            errors[field] = "La referencia pertenece a otra organizacion."
    return errors


def environmental_record_errors(data, organization, instance=None):
    fields = (
        "actividad",
        "punto",
        "unidad_operacional",
        "proceso",
        "activo",
        "obra",
        "evento_material",
        "fuente",
        "evidencia",
        "version_evidencia",
    )
    errors = {}
    values = {}
    for field in fields:
        value = data.get(field, getattr(instance, field, None))
        values[field] = value
        if value and value.organizacion_id != organization.id:
            errors[field] = "La referencia pertenece a otra organizacion."
    work, activity, point, evidence = (
        values["obra"],
        values["actividad"],
        values["punto"],
        values["evidencia"],
    )
    if work and activity and activity.obra_id and activity.obra_id != work.id:
        errors["actividad"] = "La actividad pertenece a otra obra."
    if work and point and point.obra_id and point.obra_id != work.id:
        errors["punto"] = "El punto ambiental pertenece a otra obra."
    if work and evidence and evidence.obra_id and evidence.obra_id != work.id:
        errors["evidencia"] = "La evidencia pertenece a otra obra."
    period_start = data.get("periodo_inicio", getattr(instance, "periodo_inicio", None))
    period_end = data.get("periodo_fin", getattr(instance, "periodo_fin", None))
    if work and work.fecha_inicio and period_start and period_start.date() < work.fecha_inicio:
        errors["periodo_inicio"] = (
            f"La fecha del registro no puede ser anterior al inicio de la obra ({work.fecha_inicio:%d-%m-%Y})."
        )
    if work and work.fecha_termino_estimada:
        if period_start and period_start.date() > work.fecha_termino_estimada:
            errors["periodo_inicio"] = (
                f"La fecha del registro no puede ser posterior al término de la obra ({work.fecha_termino_estimada:%d-%m-%Y})."
            )
        if period_end and period_end.date() > work.fecha_termino_estimada:
            errors["periodo_fin"] = (
                f"El fin del registro no puede ser posterior al término de la obra ({work.fecha_termino_estimada:%d-%m-%Y})."
            )
    number, text = data.get("valor_numerico"), data.get("valor_texto", "")
    if number is not None and text:
        errors["non_field_errors"] = ["Use solo un valor numerico o textual."]
    if (number is not None or text) and not data.get("concepto"):
        errors["concepto"] = "Debe indicar el concepto observado."
    if (number is not None or text) and not data.get("fuente"):
        errors["fuente"] = "Debe indicar la fuente."
    version = values["version_evidencia"]
    if version and evidence and version.evidencia_id != evidence.id:
        errors["version_evidencia"] = "La version no pertenece a la evidencia."
    return errors
