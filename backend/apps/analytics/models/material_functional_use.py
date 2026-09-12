"""Governed functional-use quantity for a material relative to one approved
application profile (MI-01C): how much of this material fulfills exactly one
functional unit of that application. This value can never be inferred from
density/name; it always requires an explicit rationale/evidence and human
approval, and it is the fundamental input that makes environmental
comparisons across alternatives meaningful (see MI-01E)."""

from contextvars import ContextVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .material_intelligence_governed import GovernedQuerySet

functional_use_write = ContextVar("material_functional_use_write", default=False)


class MaterialFunctionalUse(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        REEMPLAZADO = "reemplazado", "Reemplazado"

    TERMINAL = {Estado.RECHAZADO, Estado.REEMPLAZADO}

    objects = GovernedQuerySet.as_manager()

    organizacion = models.ForeignKey(
        "analytics.Organizacion",
        on_delete=models.CASCADE,
        related_name="usos_funcionales_material",
    )
    material = models.ForeignKey(
        "analytics.MaterialOperacional",
        on_delete=models.PROTECT,
        related_name="usos_funcionales",
    )
    profile = models.ForeignKey(
        "analytics.MaterialApplicationProfile",
        on_delete=models.PROTECT,
        related_name="usos_funcionales_material",
    )
    cantidad_por_unidad_funcional = models.DecimalField(max_digits=20, decimal_places=6)
    unidad = models.CharField(max_length=40)
    rationale = models.TextField()
    evidencia = models.ForeignKey(
        "analytics.EvidenciaObra",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usos_funcionales_material",
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.BORRADOR, db_index=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="usos_funcionales_material_creados",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usos_funcionales_material_revisados",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=["borrador", "aprobado", "rechazado", "reemplazado"]
                ),
                name="material_functional_use_valid_status",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad_por_unidad_funcional__gt=0),
                name="material_functional_use_positive_quantity",
            ),
        ]

    def clean(self):
        errors = {}
        if self.material_id and self.organizacion_id and self.material.organizacion_id != self.organizacion_id:
            errors["material"] = "El material debe pertenecer a la misma organizacion."
        if self.profile_id and self.organizacion_id and self.profile.organizacion_id != self.organizacion_id:
            errors["profile"] = "El perfil debe pertenecer a la misma organizacion."
        if not self.rationale or not self.rationale.strip():
            errors["rationale"] = "Se requiere una justificación explícita."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not functional_use_write.get():
            raise ValidationError("Use el servicio de uso funcional material.")
        if self.pk:
            previous = MaterialFunctionalUse.objects.get(pk=self.pk)
            if previous.estado in self.TERMINAL:
                raise ValidationError("El uso funcional es histórico e inmutable.")
            immutable_fields = (
                "organizacion_id", "material_id", "profile_id",
                "cantidad_por_unidad_funcional", "unidad", "created_by_id",
            )
            if previous.estado == self.Estado.APROBADO and any(
                getattr(previous, field) != getattr(self, field)
                for field in immutable_fields
            ):
                raise ValidationError(
                    "Un uso funcional aprobado es inmutable; registre uno nuevo."
                )
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("El historial de uso funcional es inmutable.")


class MaterialFunctionalUseDecision(models.Model):
    class Decision(models.TextChoices):
        CREADO = "creado", "Creado"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        REEMPLAZADO = "reemplazado", "Reemplazado"

    objects = GovernedQuerySet.as_manager()

    functional_use = models.ForeignKey(
        MaterialFunctionalUse, on_delete=models.PROTECT, related_name="decisiones"
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="decisiones_uso_funcional_material",
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    nota = models.TextField(blank=True)
    contexto = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["functional_use_id", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    decision__in=["creado", "aprobado", "rechazado", "reemplazado"]
                ),
                name="material_functional_use_decision_valid",
            )
        ]

    def save(self, *args, **kwargs):
        if not functional_use_write.get():
            raise ValidationError("Use el servicio de uso funcional material.")
        if self.pk:
            raise ValidationError("Las decisiones de uso funcional son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Las decisiones de uso funcional son inmutables.")


class MaterialApplicationAssessment(models.Model):
    """Immutable, append-only snapshot of one deterministic suitability
    evaluation of a material against an approved application profile. Never
    mutated after creation; a re-evaluation is always a new row, so a past
    assessment always reconstructs from exactly the inputs it recorded."""

    class Resultado(models.TextChoices):
        SUITABLE_CANDIDATE = "suitable_candidate", "Candidato adecuado"
        NOT_SUITABLE = "not_suitable", "No adecuado"
        REQUIRES_REVIEW = "requires_review", "Requiere revisión"

    class DecisionHumana(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado para la aplicación"
        RECHAZADO = "rechazado", "Rechazado"

    objects = GovernedQuerySet.as_manager()

    organizacion = models.ForeignKey(
        "analytics.Organizacion",
        on_delete=models.CASCADE,
        related_name="evaluaciones_aplicacion_material",
    )
    material = models.ForeignKey(
        "analytics.MaterialOperacional",
        on_delete=models.PROTECT,
        related_name="evaluaciones_aplicacion",
    )
    profile = models.ForeignKey(
        "analytics.MaterialApplicationProfile",
        on_delete=models.PROTECT,
        related_name="evaluaciones_aplicacion_material",
    )
    resultado = models.CharField(max_length=20, choices=Resultado.choices)
    requirement_results = models.JSONField(default=list, blank=True)
    missing_properties = models.JSONField(default=list, blank=True)
    failed_requirements = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    profile_version = models.PositiveIntegerField()
    assertion_ids_used = models.JSONField(default=list, blank=True)
    decision_humana = models.CharField(
        max_length=20, choices=DecisionHumana.choices, default=DecisionHumana.PENDIENTE
    )
    decidido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="evaluaciones_aplicacion_decididas",
    )
    decidido_en = models.DateTimeField(null=True, blank=True)
    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evaluaciones_aplicacion_material_creadas",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    resultado__in=["suitable_candidate", "not_suitable", "requires_review"]
                ),
                name="material_application_assessment_valid_result",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    decision_humana__in=["pendiente", "aprobado", "rechazado"]
                ),
                name="material_application_assessment_valid_human_decision",
            ),
        ]

    def clean(self):
        errors = {}
        if self.material_id and self.organizacion_id and self.material.organizacion_id != self.organizacion_id:
            errors["material"] = "El material debe pertenecer a la misma organizacion."
        if self.profile_id and self.organizacion_id and self.profile.organizacion_id != self.organizacion_id:
            errors["profile"] = "El perfil debe pertenecer a la misma organizacion."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not functional_use_write.get():
            raise ValidationError("Use el servicio de evaluación de aplicación material.")
        if self.pk:
            previous = MaterialApplicationAssessment.objects.get(pk=self.pk)
            immutable_fields = (
                "organizacion_id", "material_id", "profile_id", "resultado",
                "requirement_results", "missing_properties", "failed_requirements",
                "warnings", "profile_version", "assertion_ids_used", "evaluated_by_id",
            )
            if any(getattr(previous, field) != getattr(self, field) for field in immutable_fields):
                raise ValidationError("La evaluación de aplicación es inmutable.")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("El historial de evaluación de aplicación es inmutable.")
