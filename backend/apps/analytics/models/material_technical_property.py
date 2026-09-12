"""Governed technical property evidence for MaterialOperacional (MI-01B).

Represents what is actually known, and by which evidence, about a material's
technical properties — never an inference from its name/category. Reuses the
existing documentary evidence infrastructure (EvidenciaObra/VersionEvidencia)
and FuenteDatos instead of creating a second documentary authority. Only
approved assertions may feed automatic suitability evaluation (MI-01C);
unknown stays unknown, it is never invented.
"""

from contextvars import ContextVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .material_intelligence_governed import GovernedQuerySet

property_assertion_write = ContextVar(
    "material_technical_property_assertion_write", default=False
)


class MaterialTechnicalPropertyAssertion(models.Model):
    class TipoPropiedad(models.TextChoices):
        NUMERIC = "numeric", "Numérica"
        CATEGORICAL = "categorical", "Categórica"
        BOOLEAN = "boolean", "Booleana"

    class TipoProvenance(models.TextChoices):
        MANUFACTURER_DATASHEET = "manufacturer_datasheet", "Ficha técnica del fabricante"
        TECHNICAL_SPEC = "technical_spec", "Especificación técnica"
        CERTIFICATE = "certificate", "Certificado"
        LAB_RESULT = "lab_result", "Resultado de laboratorio"
        PROJECT_REQUIREMENT = "project_requirement", "Requisito de proyecto"
        MANUAL_PROFESSIONAL_ASSERTION = (
            "manual_professional_assertion",
            "Aserción profesional manual",
        )

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
        related_name="aserciones_propiedad_material",
    )
    material = models.ForeignKey(
        "analytics.MaterialOperacional",
        on_delete=models.PROTECT,
        related_name="aserciones_propiedad",
    )
    property_key = models.CharField(max_length=100)
    property_type = models.CharField(max_length=20, choices=TipoPropiedad.choices)
    value_numeric = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    value_text = models.CharField(max_length=180, blank=True)
    value_boolean = models.BooleanField(null=True, blank=True)
    unit = models.CharField(max_length=40, blank=True)
    provenance_type = models.CharField(max_length=40, choices=TipoProvenance.choices)
    evidencia = models.ForeignKey(
        "analytics.EvidenciaObra",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aserciones_propiedad_material",
    )
    version_evidencia = models.ForeignKey(
        "analytics.VersionEvidencia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aserciones_propiedad_material",
    )
    fuente = models.ForeignKey(
        "analytics.FuenteDatos",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aserciones_propiedad_material",
    )
    rationale = models.TextField(blank=True)
    effective_date = models.DateField()
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.BORRADOR, db_index=True
    )
    asserted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="aserciones_propiedad_material_creadas",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aserciones_propiedad_material_revisadas",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=["borrador", "aprobado", "rechazado", "reemplazado"]
                ),
                name="material_property_assertion_valid_status",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        property_type="numeric",
                        value_numeric__isnull=False,
                        value_text="",
                        value_boolean__isnull=True,
                    )
                    | models.Q(
                        property_type="categorical",
                        value_numeric__isnull=True,
                        value_boolean__isnull=True,
                    )
                    | models.Q(
                        property_type="boolean",
                        value_numeric__isnull=True,
                        value_text="",
                        value_boolean__isnull=False,
                    )
                ),
                name="material_property_assertion_typed_value_pair",
            ),
        ]

    def clean(self):
        errors = {}
        if self.material_id and self.organizacion_id and self.material.organizacion_id != self.organizacion_id:
            errors["material"] = "El material debe pertenecer a la misma organizacion."
        for field_name in ("evidencia", "fuente"):
            value = getattr(self, f"{field_name}_id", None)
            if value and self.organizacion_id:
                related = getattr(self, field_name)
                if related.organizacion_id != self.organizacion_id:
                    errors[field_name] = "Debe pertenecer a la misma organizacion."
        if (
            self.version_evidencia_id
            and self.evidencia_id
            and self.version_evidencia.evidencia_id != self.evidencia_id
        ):
            errors["version_evidencia"] = "Debe corresponder a la evidencia indicada."
        if self.property_type == self.TipoPropiedad.CATEGORICAL and not self.value_text:
            errors["value_text"] = "Las propiedades categóricas requieren un valor de texto."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not property_assertion_write.get():
            raise ValidationError("Use el servicio de aserciones de propiedad técnica.")
        if self.pk:
            previous = MaterialTechnicalPropertyAssertion.objects.get(pk=self.pk)
            if previous.estado in self.TERMINAL:
                raise ValidationError("La aserción de propiedad es histórica e inmutable.")
            immutable_fields = (
                "organizacion_id",
                "material_id",
                "property_key",
                "property_type",
                "value_numeric",
                "value_text",
                "value_boolean",
                "unit",
                "provenance_type",
                "evidencia_id",
                "version_evidencia_id",
                "fuente_id",
                "effective_date",
                "asserted_by_id",
            )
            if previous.estado == self.Estado.APROBADO and any(
                getattr(previous, field) != getattr(self, field)
                for field in immutable_fields
            ):
                raise ValidationError(
                    "Una aserción aprobada es inmutable; registre una nueva aserción."
                )
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("El historial de aserciones de propiedad es inmutable.")


class MaterialTechnicalPropertyAssertionDecision(models.Model):
    class Decision(models.TextChoices):
        CREADO = "creado", "Creado"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        REEMPLAZADO = "reemplazado", "Reemplazado"

    objects = GovernedQuerySet.as_manager()

    assertion = models.ForeignKey(
        MaterialTechnicalPropertyAssertion, on_delete=models.PROTECT, related_name="decisiones"
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="decisiones_propiedad_material",
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    nota = models.TextField(blank=True)
    contexto = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["assertion_id", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    decision__in=["creado", "aprobado", "rechazado", "reemplazado"]
                ),
                name="material_property_assertion_decision_valid",
            )
        ]

    def save(self, *args, **kwargs):
        if not property_assertion_write.get():
            raise ValidationError("Use el servicio de aserciones de propiedad técnica.")
        if self.pk:
            raise ValidationError("Las decisiones de aserción de propiedad son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Las decisiones de aserción de propiedad son inmutables.")
