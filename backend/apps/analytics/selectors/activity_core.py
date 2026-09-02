from django.db.models import Case, IntegerField, Value, When

from ..models import ActividadOperacional, FuenteDatos, Observacion, Organizacion


def organization_by_public_id(organization_id):
    return Organizacion.objects.filter(organizacion_id=organization_id)


def data_sources_for_organization(organization, domain=None):
    rows = organization.fuentes_datos.all()
    if domain:
        rows = rows.filter(activa=True, metadata__dominios__contains=[domain])
    return rows.annotate(
        catalog_order=Case(
            When(metadata__provisionada=True, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("catalog_order", "nombre", "id")


def data_source_for_organization(organization, source_id):
    return FuenteDatos.objects.filter(organizacion=organization, id=source_id)


def activities_for_organization(organization, params):
    queryset = organization.actividades_operacionales.select_related(
        "unidad_operacional", "proceso_operacional"
    )
    mapping = {
        "tipo": "tipo",
        "proceso": "proceso_operacional_id",
        "unidad": "unidad_operacional_id",
        "estado": "estado",
    }
    for parameter, field in mapping.items():
        if params.get(parameter):
            queryset = queryset.filter(**{field: params[parameter]})
    if params.get("fecha_desde"):
        queryset = queryset.filter(timestamp_inicio__date__gte=params["fecha_desde"])
    if params.get("fecha_hasta"):
        queryset = queryset.filter(timestamp_inicio__date__lte=params["fecha_hasta"])
    return queryset


def activity_for_organization(organization, activity_id):
    return organization.actividades_operacionales.filter(id=activity_id)


def activity_detail(queryset, activity_id):
    return (
        queryset.select_related("unidad_operacional", "proceso_operacional")
        .prefetch_related(
            "observaciones__fuente",
            "observaciones__evidencia",
            "observaciones__version_evidencia",
            "observaciones__lectura_sensor_v2__sensor",
            "registros_emision_legacy",
        )
        .get(id=activity_id)
    )


def observations_for_activity(activity, params):
    queryset = activity.observaciones.select_related(
        "fuente", "evidencia", "version_evidencia"
    )
    if params.get("concepto"):
        queryset = queryset.filter(concepto=params["concepto"])
    if params.get("fuente"):
        queryset = queryset.filter(fuente_id=params["fuente"])
    return queryset


def observation_for_organization(organization, observation_id):
    return Observacion.objects.select_related(
        "fuente", "evidencia", "version_evidencia", "actividad"
    ).filter(organizacion=organization, id=observation_id)
