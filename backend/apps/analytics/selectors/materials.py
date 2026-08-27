from ..models import EventoMaterial, LoteMaterial, MaterialOperacional, Obra


def materials_for_organization(organization):
    return organization.materiales_operacionales.all()


def material_for_organization(organization, material_id):
    return MaterialOperacional.objects.filter(organizacion=organization, id=material_id)


def lots_for_organization(organization, material_id=None):
    rows = organization.lotes_materiales.select_related(
        "material", "fuente", "evidencia", "version_evidencia"
    )
    return rows.filter(material_id=material_id) if material_id else rows


def lot_for_scope(organization, material, lot_id):
    return LoteMaterial.objects.filter(
        organizacion=organization, material=material, id=lot_id
    )


def work_for_organization(organization, work_id):
    return Obra.objects.filter(organizacion=organization, id=work_id)


def events_for_organization(organization, params=None):
    rows = organization.eventos_materiales.select_related(
        "material",
        "lote",
        "actividad",
        "evento_origen",
        "obra",
        "proceso",
        "fuente",
        "evidencia",
        "version_evidencia",
        "observacion_cantidad__fuente",
    )
    mapping = {
        "material": "material_id",
        "lote": "lote_id",
        "obra": "obra_id",
        "tipo": "tipo",
    }
    for parameter, field in mapping.items():
        if params and params.get(parameter):
            rows = rows.filter(**{field: params[parameter]})
    return rows


def event_for_organization(organization, event_id):
    return EventoMaterial.objects.filter(organizacion=organization, id=event_id)


def registered_material_events(
    organization, material, *, lot=None, start=None, end=None, before=None, work=None
):
    rows = EventoMaterial.objects.filter(
        organizacion=organization,
        material=material,
        estado=EventoMaterial.Estado.REGISTRADO,
    ).select_related(
        "observacion_cantidad",
        "actividad",
        "lote",
        "obra",
        "proceso",
        "fuente",
        "evidencia",
        "version_evidencia",
    )
    if lot is not None:
        rows = rows.filter(lote=lot)
    if start:
        rows = rows.filter(fecha_hora__date__gte=start)
    if end:
        rows = rows.filter(fecha_hora__date__lte=end)
    if before:
        rows = rows.filter(fecha_hora__date__lt=before)
    if work is not None:
        rows = rows.filter(obra=work)
    return rows.order_by("fecha_hora", "id")
