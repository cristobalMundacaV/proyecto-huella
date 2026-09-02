from django.db.models import OuterRef, Subquery

from ..models import ImpactoAmbiental


def effective_generated_ghg_impacts(organization, work, start, end):
    """Latest impact per activity, then strict filtering for the generated-GHG KPI."""
    scoped = ImpactoAmbiental.objects.filter(
        organizacion=organization,
        actividad__obra=work,
        timestamp__date__gte=start,
        timestamp__date__lte=end,
    )
    latest_for_activity = (
        scoped.filter(actividad_id=OuterRef("actividad_id"))
        .order_by("-calculo__version_interna", "-calculo_id", "-id")
        .values("id")[:1]
    )
    return (
        scoped.filter(
            id=Subquery(latest_for_activity),
            tipo=ImpactoAmbiental.Tipo.GENERADO,
            unidad="tCO2e",
        )
        .select_related("calculo", "actividad")
        .order_by("actividad_id", "id")
    )
