from django.db.models import Count, Q

from ..models import (
    AlertaCumplimientoAmbiental,
    DocumentoAmbiental,
    LimiteNormativoAmbiental,
    Obra,
    VariableAmbientalExtraida,
)
from ..permissions import filter_works_for_user


def documents_for_user(organization, user, work=None):
    rows = (
        DocumentoAmbiental.objects.filter(organizacion=organization)
        .select_related("organizacion", "obra", "etapa")
        .prefetch_related("registros_emision")
    )
    if work is not None:
        return rows.filter(obra=work)
    allowed = filter_works_for_user(Obra.objects.all(), user, organization)
    return rows.filter(Q(obra__isnull=True) | Q(obra__in=allowed))


def document_for_organization(organization, document_id):
    return DocumentoAmbiental.objects.filter(pk=document_id, organizacion=organization)


def variables_for_organization(organization, work=None, state=None):
    rows = VariableAmbientalExtraida.objects.filter(
        organizacion=organization
    ).select_related("organizacion", "documento")
    if work is not None:
        rows = rows.filter(documento__obra=work)
    return rows.filter(estado_cumplimiento=state) if state else rows


def variable_for_organization(organization, variable_id):
    return VariableAmbientalExtraida.objects.filter(
        pk=variable_id, organizacion=organization
    )


def limits_for_organization(organization, active=None):
    rows = LimiteNormativoAmbiental.objects.filter(organizacion=organization)
    return rows.filter(activo=active) if active is not None else rows


def limit_for_organization(organization, limit_id):
    return LimiteNormativoAmbiental.objects.filter(
        pk=limit_id, organizacion=organization
    )


def filter_alerts_for_work(rows, work):
    return rows.filter(
        Q(documento__obra=work, variable__isnull=True)
        | Q(documento__isnull=True, variable__documento__obra=work)
        | Q(documento__obra=work, variable__documento__obra=work)
    ).distinct()


def alerts_for_user(organization, user, work=None, state=None):
    rows = AlertaCumplimientoAmbiental.objects.filter(
        organizacion=organization
    ).select_related("documento", "variable")
    if work is not None:
        rows = filter_alerts_for_work(rows, work)
    else:
        allowed = filter_works_for_user(Obra.objects.all(), user, organization)
        rows = rows.filter(
            Q(documento__obra__isnull=True, variable__documento__obra__isnull=True)
            | Q(documento__obra__in=allowed)
            | Q(variable__documento__obra__in=allowed)
        ).distinct()
    return rows.filter(estado=state) if state else rows


def alert_for_organization(organization, alert_id):
    return AlertaCumplimientoAmbiental.objects.filter(
        pk=alert_id, organizacion=organization
    )


def compliance_scope(organization, user, work=None):
    return (
        documents_for_user(organization, user, work),
        variables_for_organization(organization, work),
        alerts_for_user(organization, user, work),
    )


def compliance_state_counts(variables):
    return {
        row["estado_cumplimiento"]: row["total"]
        for row in variables.values("estado_cumplimiento").annotate(total=Count("id"))
    }
