def journey_relation_errors(data, organization, instance=None):
    errors = {}
    for field in ("actividad", "ruta"):
        value = data.get(field, getattr(instance, field, None))
        if value and value.organizacion_id != organization.id:
            errors[field] = "La referencia pertenece a otra organizacion."
    vehicle = data.get("vehiculo", getattr(instance, "vehiculo", None))
    if vehicle and vehicle.activo.organizacion_id != organization.id:
        errors["vehiculo"] = "El vehiculo pertenece a otra organizacion."
    source = data.get("fuente")
    if source and source.organizacion_id != organization.id:
        errors["fuente"] = "La fuente pertenece a otra organizacion."
    if (
        any(data.get(key) is not None for key in ("distancia", "carga", "combustible"))
        and not source
    ):
        errors["fuente"] = "Debe indicar la fuente de los valores observados."
    for field in ("distancia", "carga", "combustible"):
        if data.get(field) is not None and data[field] < 0:
            errors[field] = "El valor no puede ser negativo."
    return errors
