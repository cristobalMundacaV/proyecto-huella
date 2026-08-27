from django.db import transaction

from ..models import ActividadOperacional, Observacion


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
    if actor is not None:
        values["actor"] = actor
    observation = Observacion(organizacion=organization, actividad=activity, **values)
    observation.full_clean()
    observation.save()
    return observation


@transaction.atomic
def update_observation(*, observation, data):
    for field, value in data.items():
        setattr(observation, field, value)
    observation.full_clean()
    observation.save()
    return observation
