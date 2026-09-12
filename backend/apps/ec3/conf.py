from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_date

BASE_URL = "https://openepd.buildingtransparency.org/api"
ATTRIBUTION = "Fuente: EC3 / Building Transparency. EC3 conserva la autoridad sobre la EPD."


def enabled():
    if not getattr(settings, "EC3_ENABLED", False):
        raise ValidationError("EC3_ENABLED está deshabilitado.")


def storage_allowed():
    try:
        end = parse_date(str(getattr(settings, "EC3_RIGHTS_VALID_UNTIL", "")))
    except ValueError:
        return False
    return bool(
        getattr(settings, "EC3_STORAGE_ALLOWED", False)
        and getattr(settings, "EC3_RIGHTS_REFERENCE", "").strip()
        and end and timezone.localdate() <= end
    )


def require_storage():
    enabled()
    if not storage_allowed():
        raise ValidationError("Configure derechos de persistencia EC3 y su vigencia antes de ingerir.")
