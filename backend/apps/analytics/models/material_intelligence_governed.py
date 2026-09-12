"""Shared direct-queryset-mutation guard for MATERIAL-INTELLIGENCE governed
authorities. Instance-level save()/delete() overrides already block ungoverned
writes on a single row; this additionally blocks bulk `.update()`/`.delete()`/
`.bulk_create()` on the queryset, which would otherwise bypass those checks
entirely (Django never calls an instance's save()/delete() for those paths)."""

from django.core.exceptions import ValidationError
from django.db import models


class GovernedQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Use el servicio correspondiente; escritura directa no permitida.")

    def delete(self):
        raise ValidationError("El historial de esta autoridad es inmutable.")

    def bulk_create(self, *args, **kwargs):
        raise ValidationError("Use el servicio correspondiente; escritura directa no permitida.")

    def bulk_update(self, *args, **kwargs):
        raise ValidationError("Use el servicio correspondiente; escritura directa no permitida.")
