def activity_relation_errors(
    *, organization, unit=None, process=None, work=None, assets=()
):
    if unit and unit.organizacion_id != organization.id:
        return {"unidad_operacional": "La unidad pertenece a otra organizacion."}
    if process and process.organizacion_id != organization.id:
        return {"proceso_operacional": "El proceso pertenece a otra organizacion."}
    if work and work.organizacion_id != organization.id:
        return {"obra": "La obra pertenece a otra organizacion."}
    if any(asset.organizacion_id != organization.id for asset in assets):
        return {"activos": "Todos los activos deben pertenecer a la organizacion."}
    return None


def observation_context_errors(
    *, organization, activity, submitted_activity, source, evidence, evidence_version
):
    if (
        submitted_activity is not None
        and activity
        and str(submitted_activity) != str(activity.id)
    ):
        return {"actividad": "La actividad no coincide con el recurso solicitado."}
    relations = (
        ("actividad", activity, "La actividad pertenece a otra organizacion."),
        ("fuente", source, "La fuente pertenece a otra organizacion."),
        ("evidencia", evidence, "La evidencia pertenece a otra organizacion."),
        (
            "version_evidencia",
            evidence_version,
            "La version de evidencia pertenece a otra organizacion.",
        ),
    )
    for field, relation, message in relations:
        if relation and relation.organizacion_id != organization.id:
            return {field: message}
    if evidence_version and evidence and evidence_version.evidencia_id != evidence.id:
        return {"version_evidencia": "La version no pertenece a la evidencia asociada."}
    return None


def observation_value_error(*, numeric_value, text_value):
    if numeric_value is None and not text_value:
        return "Debe informar un valor numerico o textual."
    if numeric_value is not None and text_value:
        return "Use solo un tipo de valor por observacion."
    return None
