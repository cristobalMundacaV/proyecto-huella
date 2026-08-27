from django.db import transaction

from ..models import (
    ActivoOperacional,
    CondicionOperacionalActivo,
    MantenimientoActivo,
    Maquinaria,
    Vehiculo,
)


def _save_specialization(asset, vehicle_data, machinery_data):
    if vehicle_data is not None:
        Vehiculo.objects.update_or_create(activo=asset, defaults=vehicle_data)
    if machinery_data is not None:
        Maquinaria.objects.update_or_create(activo=asset, defaults=machinery_data)


@transaction.atomic
def create_asset(*, organization, data):
    values = dict(data)
    vehicle_data = values.pop("vehiculo", None)
    machinery_data = values.pop("maquinaria", None)
    asset = ActivoOperacional(organizacion=organization, **values)
    asset.full_clean()
    asset.save()
    _save_specialization(asset, vehicle_data, machinery_data)
    return asset


@transaction.atomic
def update_asset(*, asset, data):
    values = dict(data)
    vehicle_data = values.pop("vehiculo", None)
    machinery_data = values.pop("maquinaria", None)
    for field, value in values.items():
        setattr(asset, field, value)
    asset.full_clean()
    asset.save()
    _save_specialization(asset, vehicle_data, machinery_data)
    return asset


@transaction.atomic
def create_maintenance(*, organization, asset, data):
    maintenance = MantenimientoActivo(organizacion=organization, activo=asset, **data)
    maintenance.full_clean()
    maintenance.save()
    return maintenance


@transaction.atomic
def update_maintenance(*, maintenance, data):
    for field, value in data.items():
        setattr(maintenance, field, value)
    maintenance.full_clean()
    maintenance.save()
    return maintenance


@transaction.atomic
def create_condition(*, asset, data):
    condition = CondicionOperacionalActivo(activo=asset, **data)
    condition.full_clean()
    condition.save()
    return condition
