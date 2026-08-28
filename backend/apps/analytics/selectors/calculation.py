from django.db.models import Q

from ..models import CalculoAmbiental, Obra
from ..permissions import filter_works_for_user


def calculations_for_activity(activity):
    return activity.calculos_ambientales.select_related(
        "version_metodologia__metodologia",
        "formula__factor_ambiental",
        "version_factor__factor",
    ).prefetch_related("inputs__observacion", "inputs__fuente")


def calculation_for_organization(organization, calculation_id, *, detailed=False):
    rows = CalculoAmbiental.objects.filter(organizacion=organization, id=calculation_id)
    if detailed:
        rows = rows.select_related(
            "version_metodologia__metodologia",
            "formula__factor_ambiental",
            "version_factor__factor",
            "actividad__obra",
        ).prefetch_related("inputs__observacion", "inputs__fuente")
    else:
        rows = rows.select_related("actividad__obra")
    return rows


def impacts_for_user(organization, user, work_id=None):
    rows = organization.impactos_ambientales_v2.select_related(
        "actividad", "actividad__obra", "calculo"
    ).order_by("-timestamp", "-created_at")
    if work_id:
        rows = rows.filter(actividad__obra_id=work_id)
    allowed = filter_works_for_user(Obra.objects.all(), user, organization)
    return rows.filter(Q(actividad__obra__isnull=True) | Q(actividad__obra__in=allowed))
