from ..models import Obra, RutaOperacional, ViajeOperacional


def routes_for_organization(organization):
    return organization.rutas_operacionales.all()


def journeys_for_organization(organization, work=None):
    rows = organization.viajes_operacionales.select_related(
        "actividad",
        "vehiculo__activo",
        "ruta",
        "observacion_distancia__fuente",
        "observacion_carga__fuente",
        "observacion_combustible__fuente",
    )
    return rows.filter(actividad__obra=work) if work else rows


def journey_for_organization(organization, journey_id):
    return ViajeOperacional.objects.filter(organizacion=organization, id=journey_id)


def work_for_organization(organization, work_id):
    return Obra.objects.filter(organizacion=organization, id=work_id)


def completed_journeys(organization, start=None, end=None, work=None):
    rows = ViajeOperacional.objects.filter(
        organizacion=organization, estado=ViajeOperacional.Estado.COMPLETADO
    ).select_related(
        "vehiculo",
        "observacion_distancia",
        "observacion_carga",
        "observacion_combustible",
        "ruta",
    )
    if start:
        rows = rows.filter(fecha_salida__date__gte=start)
    if end:
        rows = rows.filter(fecha_salida__date__lte=end)
    if work is not None:
        rows = rows.filter(actividad__obra=work)
    return rows
