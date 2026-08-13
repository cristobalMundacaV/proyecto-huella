from django.db.models import Q
from django.utils import timezone

from apps.analytics.models import LimiteNormativoAmbiental


def applicable_validated_rules(organization, indicator, *, on_date=None, installation_type=""):
    on_date = on_date or timezone.localdate()
    return LimiteNormativoAmbiental.objects.filter(
        organizacion=organization, variable_id=indicator, activo=True, validado=True,
    ).filter(Q(industria="") | Q(industria=organization.preset)).filter(
        Q(region="") | Q(region__iexact=organization.region),
    ).filter(Q(tipo_instalacion="") | Q(tipo_instalacion__iexact=installation_type)).filter(
        Q(vigencia_desde__isnull=True) | Q(vigencia_desde__lte=on_date),
    ).filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=on_date))
