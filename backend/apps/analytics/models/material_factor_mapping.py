"""Governed, tenant-scoped, temporally-versioned mapping between a
MaterialOperacional and the FactorAmbiental authorized to calculate its
received quantity. Separate domain from MaterialEnvironmentalFactorCandidate
(01C, global ÖKOBAUDAT governance) and from generic factor metadata matching:
this is the only authority the modern material_cantidad selector consults."""

from contextvars import ContextVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

mapping_write = ContextVar("material_factor_mapping_write", default=False)


class MaterialFactorMapping(models.Model):
    class Estado(models.TextChoices):
        PROPUESTO = "propuesto", "Propuesto"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        REVOCADO = "revocado", "Revocado"
        REEMPLAZADO = "reemplazado", "Reemplazado"

    TERMINAL = {Estado.RECHAZADO, Estado.REVOCADO, Estado.REEMPLAZADO}

    organizacion = models.ForeignKey(
        "analytics.Organizacion",
        on_delete=models.CASCADE,
        related_name="mapeos_material_factor",
    )
    material = models.ForeignKey(
        "analytics.MaterialOperacional",
        on_delete=models.PROTECT,
        related_name="mapeos_factor",
    )
    factor = models.ForeignKey(
        "analytics.FactorAmbiental",
        on_delete=models.PROTECT,
        related_name="mapeos_material",
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PROPUESTO, db_index=True
    )
    vigencia_desde = models.DateField()
    vigencia_hasta = models.DateField(null=True, blank=True)
    contexto = models.JSONField(default=dict, blank=True)
    propuesto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="mapeos_material_propuestos",
    )
    revocado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mapeos_material_revocados",
    )
    revocado_en = models.DateTimeField(null=True, blank=True)
    reemplazado_por = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reemplaza_a",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-vigencia_desde", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=[
                        "propuesto",
                        "aprobado",
                        "rechazado",
                        "revocado",
                        "reemplazado",
                    ]
                ),
                name="material_mapping_valid_status",
            ),
            models.CheckConstraint(
                condition=models.Q(vigencia_hasta__isnull=True)
                | models.Q(vigencia_hasta__gte=models.F("vigencia_desde")),
                name="material_mapping_valid_validity_window",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(estado="reemplazado", reemplazado_por__isnull=False)
                    | (
                        ~models.Q(estado="reemplazado")
                        & models.Q(reemplazado_por__isnull=True)
                    )
                ),
                name="material_mapping_reemplazado_pair",
            ),
            models.UniqueConstraint(
                fields=["material", "factor", "vigencia_desde", "vigencia_hasta"],
                condition=models.Q(estado="propuesto"),
                name="unique_material_mapping_pending_proposal",
            ),
        ]

    def clean(self):
        errors = {}
        if self.material_id and self.organizacion_id and (
            self.material.organizacion_id != self.organizacion_id
        ):
            errors["material"] = "El material debe pertenecer a la misma organizacion."
        if self.factor_id and self.organizacion_id and self.factor.organizacion_id not in (
            None,
            self.organizacion_id,
        ):
            errors["factor"] = (
                "El factor debe ser global o pertenecer a la misma organizacion."
            )
        if (
            self.vigencia_desde
            and self.vigencia_hasta
            and self.vigencia_hasta < self.vigencia_desde
        ):
            errors["vigencia_hasta"] = (
                "La vigencia hasta no puede ser anterior a la vigencia desde."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not mapping_write.get():
            raise ValidationError("Use el servicio de mapeo material-factor.")
        if self.pk:
            previous = MaterialFactorMapping.objects.get(pk=self.pk)
            if previous.estado in self.TERMINAL:
                raise ValidationError("La decisión del mapeo es histórica e inmutable.")
            immutable_fields = (
                "organizacion_id",
                "material_id",
                "factor_id",
                "vigencia_desde",
                "vigencia_hasta",
                "propuesto_por_id",
                "contexto",
            )
            if previous.estado == self.Estado.APROBADO and any(
                getattr(previous, field) != getattr(self, field)
                for field in immutable_fields
            ):
                raise ValidationError(
                    "Un mapeo aprobado es inmutable; proponga un nuevo mapeo."
                )
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("El historial de mapeo material-factor es inmutable.")


class MaterialFactorMappingDecision(models.Model):
    class Decision(models.TextChoices):
        PROPUESTO = "propuesto", "Propuesto"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        REVOCADO = "revocado", "Revocado"
        REEMPLAZADO = "reemplazado", "Reemplazado"

    mapping = models.ForeignKey(
        MaterialFactorMapping, on_delete=models.PROTECT, related_name="decisiones"
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="decisiones_mapeo_material",
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    nota = models.TextField(blank=True)
    contexto = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["mapping_id", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    decision__in=[
                        "propuesto",
                        "aprobado",
                        "rechazado",
                        "revocado",
                        "reemplazado",
                    ]
                ),
                name="material_mapping_decision_valid",
            )
        ]

    def save(self, *args, **kwargs):
        if not mapping_write.get():
            raise ValidationError("Use el servicio de mapeo material-factor.")
        if self.pk:
            raise ValidationError("Las decisiones de mapeo son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Las decisiones de mapeo son inmutables.")
