"""Hypothetical substitution scenario (MI-01G): "what if this material were
replaced by this approved comparable alternative." Strictly read-only over
Operational Truth — it never mutates EventoMaterial, the ledger, a mapping,
or approves a substitution. Once evaluated it is an immutable audit
snapshot: every governed input (functional use, factor version, profile
version) is frozen at creation, so a later change to any of them never
rewrites this scenario, and it can be reconstructed exactly, months later,
from itself alone."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .material_intelligence_governed import GovernedQuerySet


class MaterialSubstitutionScenario(models.Model):
    class Basis(models.TextChoices):
        RECEPTION = "reception", "Recepción real"
        AGGREGATE_QUANTITY = "aggregate_quantity", "Cantidad agregada hipotética"

    class Resultado(models.TextChoices):
        LOWER_IMPACT = "lower_impact_alternative", "Alternativa con menor impacto"
        HIGHER_IMPACT = "higher_impact_alternative", "Alternativa con mayor impacto"
        EQUAL_IMPACT = "equal_impact", "Impacto equivalente"
        NOT_COMPARABLE = "not_comparable", "No comparable"

    objects = GovernedQuerySet.as_manager()

    organizacion = models.ForeignKey(
        "analytics.Organizacion", on_delete=models.CASCADE,
        related_name="escenarios_sustitucion_material",
    )
    profile = models.ForeignKey(
        "analytics.MaterialApplicationProfile", on_delete=models.PROTECT,
        related_name="escenarios_sustitucion",
    )
    profile_version = models.PositiveIntegerField()
    baseline_material = models.ForeignKey(
        "analytics.MaterialOperacional", on_delete=models.PROTECT,
        related_name="escenarios_como_base",
    )
    alternative_material = models.ForeignKey(
        "analytics.MaterialOperacional", on_delete=models.PROTECT,
        related_name="escenarios_como_alternativa",
    )
    basis = models.CharField(max_length=20, choices=Basis.choices)
    reception = models.ForeignKey(
        "analytics.EventoMaterial", on_delete=models.PROTECT, null=True, blank=True,
        related_name="escenarios_sustitucion",
    )
    source_quantity_input = models.DecimalField(max_digits=20, decimal_places=6)
    source_quantity_unit = models.CharField(max_length=40)
    functional_units = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    baseline_functional_use = models.ForeignKey(
        "analytics.MaterialFunctionalUse", on_delete=models.PROTECT, null=True, blank=True,
        related_name="escenarios_base",
    )
    alternative_functional_use = models.ForeignKey(
        "analytics.MaterialFunctionalUse", on_delete=models.PROTECT, null=True, blank=True,
        related_name="escenarios_alternativa",
    )
    baseline_factor_version = models.ForeignKey(
        "analytics.VersionFactorAmbiental", on_delete=models.PROTECT, null=True, blank=True,
        related_name="escenarios_base",
    )
    alternative_factor_version = models.ForeignKey(
        "analytics.VersionFactorAmbiental", on_delete=models.PROTECT, null=True, blank=True,
        related_name="escenarios_alternativa",
    )
    baseline_quantity_per_functional_unit = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    alternative_quantity_per_functional_unit = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    alternative_quantity_equivalent = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    baseline_impact_per_functional_unit = models.DecimalField(max_digits=24, decimal_places=10, null=True, blank=True)
    alternative_impact_per_functional_unit = models.DecimalField(max_digits=24, decimal_places=10, null=True, blank=True)
    absolute_delta = models.DecimalField(max_digits=24, decimal_places=10, null=True, blank=True)
    relative_delta = models.DecimalField(max_digits=24, decimal_places=10, null=True, blank=True)
    resultado = models.CharField(max_length=30, choices=Resultado.choices)
    not_comparable_reason = models.CharField(max_length=60, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="escenarios_sustitucion_material_creados",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    basis__in=["reception", "aggregate_quantity"]
                ),
                name="material_substitution_scenario_valid_basis",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    resultado__in=[
                        "lower_impact_alternative", "higher_impact_alternative",
                        "equal_impact", "not_comparable",
                    ]
                ),
                name="material_substitution_scenario_valid_result",
            ),
        ]

    def clean(self):
        errors = {}
        if self.organizacion_id:
            for field_name in ("profile", "baseline_material", "alternative_material", "reception"):
                value = getattr(self, f"{field_name}_id", None)
                if value and getattr(self, field_name).organizacion_id != self.organizacion_id:
                    errors[field_name] = "Debe pertenecer a la misma organizacion."
        if self.basis == self.Basis.RECEPTION and not self.reception_id:
            errors["reception"] = "Se requiere la recepción real cuando basis=reception."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Un escenario de sustitución es inmutable una vez evaluado.")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("El historial de escenarios de sustitución es inmutable.")
