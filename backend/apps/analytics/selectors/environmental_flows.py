from django.db.models import Prefetch

from ..models import (
    Obra,
    Observacion,
    Organizacion,
    PuntoAmbientalOperacional,
    RegistroFlujoAmbiental,
    UsuarioOrganizacion,
)


def organization_available_to_user(user, organization_id):
    organization = Organizacion.objects.filter(organizacion_id=organization_id).first()
    if not organization or not user.is_authenticated:
        return None
    if (
        user.is_superuser
        or UsuarioOrganizacion.objects.filter(
            user=user, organizacion=organization, activo=True
        ).exists()
    ):
        return organization
    return None


def work_for_organization(organization, work_id):
    return Obra.objects.filter(organizacion=organization, id=work_id)


def environmental_points_for_organization(organization, params):
    rows = organization.puntos_ambientales.select_related(
        "activo", "unidad_operacional", "proceso_operacional", "obra"
    )
    if params.get("obra"):
        rows = rows.filter(obra_id=params["obra"])
    if params.get("tipo"):
        rows = rows.filter(tipo=params["tipo"])
    return rows


def environmental_records_for_organization(organization, params=None, **filters):
    rows = (
        RegistroFlujoAmbiental.objects.filter(organizacion=organization)
        .select_related(
            "actividad",
            "punto",
            "unidad_operacional",
            "proceso",
            "activo",
            "obra",
            "evento_material",
        )
        .prefetch_related(
            Prefetch(
                "actividad__observaciones",
                queryset=Observacion.objects.select_related(
                    "fuente", "evidencia", "version_evidencia"
                ).order_by("timestamp_observacion", "id"),
            )
        )
    )
    params = params or {}
    mapping = {
        "flujo": "flujo",
        "obra": "obra_id",
        "proceso": "proceso_id",
        "activo": "activo_id",
        "punto": "punto_id",
    }
    for parameter, field in mapping.items():
        if params.get(parameter):
            rows = rows.filter(**{field: params[parameter]})
    if filters.get("flow"):
        rows = rows.filter(flujo=filters["flow"])
    if filters.get("start"):
        rows = rows.filter(periodo_inicio__date__gte=filters["start"])
    if filters.get("end"):
        rows = rows.filter(periodo_inicio__date__lte=filters["end"])
    analytical_mapping = {
        "work": "obra",
        "process": "proceso",
        "asset": "activo",
        "point": "punto",
    }
    for parameter, field in analytical_mapping.items():
        if filters.get(parameter) is not None:
            rows = rows.filter(**{field: filters[parameter]})
    return rows


def environmental_record_for_organization(organization, record_id):
    return RegistroFlujoAmbiental.objects.filter(
        organizacion=organization, id=record_id
    )
