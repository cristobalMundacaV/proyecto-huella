from django.db.models import Count

from ..models import CasoConocimientoAmbiental, ResultadoIntervencion


def knowledge_cases_for_organization(organization):
    return organization.casos_conocimiento.select_related("resultado_origen").order_by(
        "-created_at"
    )


def knowledge_case_for_organization(organization, case_id):
    return CasoConocimientoAmbiental.objects.filter(
        organizacion=organization, id=case_id
    )


def intervention_for_organization(organization, intervention_id):
    return ResultadoIntervencion.objects.filter(
        problematica__organizacion=organization, id=intervention_id
    )


def usable_knowledge(**filters):
    rows = CasoConocimientoAmbiental.objects.filter(estado="utilizable")
    for field in (
        "preset",
        "categoria_ambiental",
        "tipo_problematica",
        "tipo_accion",
        "resultado",
    ):
        if filters.get(field):
            rows = rows.filter(**{field: filters[field]})
    minimum = filters.get("fuerza_minima")
    if minimum in {"media", "alta"}:
        rows = rows.filter(
            fuerza_evidencia__in=["alta"] if minimum == "alta" else ["media", "alta"]
        )
    return rows


def knowledge_counts(rows, field):
    return {
        item[field]: item["total"]
        for item in rows.values(field).annotate(total=Count("id"))
    }
