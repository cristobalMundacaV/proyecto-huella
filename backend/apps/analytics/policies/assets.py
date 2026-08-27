def asset_relation_errors(*, organization, unit=None, process=None):
    for field, relation in (
        ("unidad_operacional", unit),
        ("proceso_operacional", process),
    ):
        if relation and relation.organizacion_id != organization.id:
            return {field: "La relacion pertenece a otra organizacion."}
    return None


def condition_source_error(*, organization, source):
    if source and source.organizacion_id != organization.id:
        return "La fuente pertenece a otra organizacion."
    return None
