from django.db import transaction

from ..models import ActividadOperacional, Observacion
from .capture import capture_observation


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


@transaction.atomic
def create_activity(*, organization, data):
    values = dict(data)
    assets = values.pop("activos", [])
    activity = ActividadOperacional(organizacion=organization, **values)
    activity.full_clean()
    activity.save()
    activity.activos.set(assets)
    return activity


@transaction.atomic
def update_activity(*, activity, data):
    values = dict(data)
    assets = values.pop("activos", None)
    for field, value in values.items():
        setattr(activity, field, value)
    activity.full_clean()
    activity.save()
    if assets is not None:
        activity.activos.set(assets)
    return activity


@transaction.atomic
def create_observation(*, organization, activity, actor, data):
    values = dict(data)
    return capture_observation(
        channel="manual",
        organization=organization,
        activity=activity,
        actor=actor,
        source=values.pop("fuente"),
        concept=values.pop("concepto"),
        timestamp=values.pop("timestamp_observacion"),
        numeric_value=values.pop("valor_numerico", None),
        text_value=values.pop("valor_texto", ""),
        unit=values.pop("unidad", ""),
        evidence=values.pop("evidencia", None),
        evidence_version=values.pop("version_evidencia", None),
        method=values.pop("metodo_captura", None),
        nature=values.pop("naturaleza", None),
        state=values.pop("estado", None),
    )


@transaction.atomic
def update_observation(*, observation, data):
    for field, value in data.items():
        setattr(observation, field, value)
    observation.full_clean()
    observation.save()
    return observation
