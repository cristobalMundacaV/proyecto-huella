from django.db.models import Q
from django.utils import timezone

from ..models import RestriccionContextual, ValorIndicador
from .compliance import limits_for_organization


def applicable_normative_limits(
    organization, variable, *, on_date=None, installation_type=""
):
    on_date = on_date or timezone.localdate()
    return (
        limits_for_organization(organization, active=True)
        .filter(variable_id=variable, validado=True)
        .filter(Q(industria="") | Q(industria=organization.preset))
        .filter(Q(region="") | Q(region__iexact=organization.region))
        .filter(Q(tipo_instalacion="") | Q(tipo_instalacion__iexact=installation_type))
        .filter(Q(vigencia_desde__isnull=True) | Q(vigencia_desde__lte=on_date))
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=on_date))
    )


def active_operational_restrictions(organization, *, on_datetime=None):
    on_datetime = on_datetime or timezone.now()
    return (
        RestriccionContextual.objects.filter(
            organizacion=organization,
            activa=True,
            tipo="restriccion_operacional",
        )
        .filter(Q(vigente_desde__lte=on_datetime))
        .filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=on_datetime))
    )


def indicator_results(organization, indicator, *, work=None):
    rows = ValorIndicador.objects.filter(
        indicador=indicator,
        indicador__organizacion=organization,
    )
    if work is not None:
        rows = rows.filter(indicador__obra=work)
    return rows.order_by("-periodo_fin", "-version")
