from ..models import ActivoOperacional, MantenimientoActivo, Organizacion


def organization_by_public_id(organization_id):
    return Organizacion.objects.filter(organizacion_id=organization_id)


def assets_for_organization(organization, params):
    queryset = organization.activos_operacionales.select_related(
        "unidad_operacional", "proceso_operacional"
    ).prefetch_related("mantenimientos", "condiciones", "sensores")
    if params.get("tipo"):
        queryset = queryset.filter(tipo=params["tipo"])
    if params.get("estado"):
        queryset = queryset.filter(estado=params["estado"])
    return queryset


def asset_for_organization(organization, asset_id, *, detailed=False):
    queryset = ActivoOperacional.objects.filter(organizacion=organization, id=asset_id)
    if detailed:
        queryset = queryset.select_related(
            "unidad_operacional", "proceso_operacional"
        ).prefetch_related("mantenimientos", "condiciones", "sensores")
    return queryset


def maintenance_for_organization(organization, maintenance_id):
    return MantenimientoActivo.objects.filter(
        organizacion=organization, id=maintenance_id
    )


def maintenances_for_asset(asset):
    return asset.mantenimientos.all()


def conditions_for_asset(asset):
    return asset.condiciones.all()
