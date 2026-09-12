"""Governed, tenant-scoped functional application profile (MI-01A).

A MaterialApplicationProfile represents what function a material must serve
in an explicit context (e.g. "1 m2 of finished exterior wall") and the
deterministic, typed requirements a material must satisfy to be considered
for that function. This is NOT a global material<->material equivalence:
comparability in later MATERIAL-INTELLIGENCE phases is only ever valid
relative to one approved profile (see docs/architecture/ARQ_10). An approved
profile is immutable; substantive changes require a new revision, never a
silent overwrite.
"""

from contextvars import ContextVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .material_intelligence_governed import GovernedQuerySet

application_profile_write = ContextVar(
    "material_application_profile_write", default=False
)


class MaterialApplicationProfile(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        RETIRADO = "retirado", "Retirado"
        REEMPLAZADO = "reemplazado", "Reemplazado"

    TERMINAL = {Estado.RECHAZADO, Estado.RETIRADO, Estado.REEMPLAZADO}

    objects = GovernedQuerySet.as_manager()

    organizacion = models.ForeignKey(
        "analytics.Organizacion",
        on_delete=models.CASCADE,
        related_name="perfiles_aplicacion_material",
    )
    obra = models.ForeignKey(
        "analytics.Obra",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="perfiles_aplicacion_material",
    )
    codigo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    cantidad_unidad_funcional = models.DecimalField(max_digits=20, decimal_places=6)
    unidad_funcional = models.CharField(max_length=40)
    requisitos = models.JSONField(default=list, blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.BORRADOR, db_index=True
    )
    version = models.PositiveIntegerField(default=1)
    reemplaza_a = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reemplazado_por_perfil",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="perfiles_aplicacion_creados",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="perfiles_aplicacion_revisados",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    retired_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="perfiles_aplicacion_retirados",
    )
    retired_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=[
                        "borrador",
                        "aprobado",
                        "rechazado",
                        "retirado",
                        "reemplazado",
                    ]
                ),
                name="material_application_profile_valid_status",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad_unidad_funcional__gt=0),
                name="material_application_profile_positive_functional_quantity",
            ),
        ]

    def clean(self):
        from ..services.material_application_requirements import validate_requirements

        errors = {}
        if self.obra_id and self.organizacion_id and self.obra.organizacion_id != self.organizacion_id:
            errors["obra"] = "La obra debe pertenecer a la misma organizacion."
        try:
            validate_requirements(self.requisitos)
        except ValidationError as exc:
            errors["requisitos"] = exc.messages
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not application_profile_write.get():
            raise ValidationError("Use el servicio de perfiles de aplicación material.")
        if self.pk:
            previous = MaterialApplicationProfile.objects.get(pk=self.pk)
            if previous.estado in self.TERMINAL:
                raise ValidationError("El perfil de aplicación es histórico e inmutable.")
            immutable_fields = (
                "organizacion_id",
                "obra_id",
                "codigo",
                "version",
                "created_by_id",
            )
            if previous.estado == self.Estado.APROBADO and any(
                getattr(previous, field) != getattr(self, field)
                for field in immutable_fields
            ):
                raise ValidationError(
                    "Un perfil aprobado es inmutable; proponga una nueva revisión."
                )
            if previous.estado == self.Estado.APROBADO and previous.estado == self.estado:
                content_fields = (
                    "nombre",
                    "descripcion",
                    "cantidad_unidad_funcional",
                    "unidad_funcional",
                    "requisitos",
                )
                if any(
                    getattr(previous, field) != getattr(self, field)
                    for field in content_fields
                ):
                    raise ValidationError(
                        "Un perfil aprobado es inmutable; proponga una nueva revisión."
                    )
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("El historial de perfiles de aplicación es inmutable.")


class MaterialApplicationProfileDecision(models.Model):
    class Decision(models.TextChoices):
        CREADO = "creado", "Creado"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        RETIRADO = "retirado", "Retirado"
        REEMPLAZADO = "reemplazado", "Reemplazado"

    objects = GovernedQuerySet.as_manager()

    profile = models.ForeignKey(
        MaterialApplicationProfile, on_delete=models.PROTECT, related_name="decisiones"
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="decisiones_perfil_aplicacion_material",
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    nota = models.TextField(blank=True)
    contexto = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["profile_id", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    decision__in=[
                        "creado",
                        "aprobado",
                        "rechazado",
                        "retirado",
                        "reemplazado",
                    ]
                ),
                name="material_application_profile_decision_valid",
            )
        ]

    def save(self, *args, **kwargs):
        if not application_profile_write.get():
            raise ValidationError("Use el servicio de perfiles de aplicación material.")
        if self.pk:
            raise ValidationError("Las decisiones de perfil de aplicación son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Las decisiones de perfil de aplicación son inmutables.")
