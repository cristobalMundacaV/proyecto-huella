from django.conf import settings
from django.core.checks import Error, register

from .conf import storage_allowed


@register()
def ec3_configuration(app_configs, **kwargs):
    issues = []
    if not getattr(settings, "EC3_ENABLED", False):
        return issues
    if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        issues.append(Error("EC3 requires PostgreSQL for a shared token budget.", id="ec3.E001"))
    if not getattr(settings, "EC3_API_TOKEN", ""):
        issues.append(Error("EC3_API_TOKEN is required when EC3_ENABLED=true.", id="ec3.E002"))
    if getattr(settings, "EC3_STORAGE_ALLOWED", False) and not storage_allowed():
        issues.append(Error("EC3 storage requires a current rights reference and valid-until date.", id="ec3.E003"))
    if not 0 <= getattr(settings, "EC3_CACHE_TTL_SECONDS", 300) <= 3600:
        issues.append(Error("EC3_CACHE_TTL_SECONDS must be 0..3600.", id="ec3.E004"))
    if not 1 <= getattr(settings, "EC3_EVIDENCE_MAX_AGE_HOURS", 168) <= 8760:
        issues.append(Error("EC3_EVIDENCE_MAX_AGE_HOURS must be 1..8760.", id="ec3.E005"))
    return issues
