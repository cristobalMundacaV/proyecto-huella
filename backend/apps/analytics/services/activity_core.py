from django.db import transaction


@transaction.atomic
def crear_entidad(model, *, organizacion, datos):
    entidad = model(organizacion=organizacion, **datos)
    entidad.full_clean()
    entidad.save()
    return entidad


@transaction.atomic
def actualizar_entidad(entidad, datos):
    for campo, valor in datos.items():
        setattr(entidad, campo, valor)
    entidad.full_clean()
    entidad.save()
    return entidad


def detalle_actividad(queryset, actividad_id):
    return queryset.select_related("unidad_operacional", "proceso_operacional").prefetch_related(
        "observaciones__fuente", "observaciones__evidencia", "registros_emision_legacy"
    ).get(id=actividad_id)
