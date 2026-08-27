from django.db import models

from .governance import (
    FormulaAmbiental,
    VariableFormula,
    VersionFactorAmbiental,
    VersionMetodologia,
)
from .operational_data import ActividadOperacional, FuenteDatos, Observacion
from .platform import Organizacion
from .provenance import EvidenciaObra, VersionEvidencia


class CalculoAmbiental(models.Model):
    class Estado(models.TextChoices):
        FINALIZADO = "finalizado", "Finalizado"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        FALLIDO = "fallido", "Fallido"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.PROTECT, related_name="calculos_ambientales_v2"
    )
    actividad = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.PROTECT,
        related_name="calculos_ambientales",
    )
    version_metodologia = models.ForeignKey(
        VersionMetodologia, on_delete=models.PROTECT, related_name="calculos"
    )
    formula = models.ForeignKey(
        FormulaAmbiental, on_delete=models.PROTECT, related_name="calculos"
    )
    version_factor = models.ForeignKey(
        VersionFactorAmbiental, on_delete=models.PROTECT, related_name="calculos"
    )
    resultado = models.DecimalField(max_digits=24, decimal_places=10)
    unidad_resultado = models.CharField(max_length=60)
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.FINALIZADO
    )
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    version_interna = models.PositiveIntegerField(default=1)
    formula_aplicada = models.CharField(max_length=300)
    advertencias = models.JSONField(default=list, blank=True)
    completitud = models.CharField(max_length=30)
    snapshot_tecnico = models.JSONField(default=dict, blank=True)
    tipo_resultado = models.CharField(max_length=30, default="emision")
    recalculo_de = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recalculos",
    )
    motivo_recalculo = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha_calculo"]

    def save(self, *args, **kwargs):
        if self.pk and CalculoAmbiental.objects.filter(pk=self.pk).exists():
            from django.core.exceptions import ValidationError

            raise ValidationError("Un calculo finalizado es inmutable; cree uno nuevo.")
        super().save(*args, **kwargs)


class InputCalculoAmbiental(models.Model):
    calculo = models.ForeignKey(
        CalculoAmbiental, on_delete=models.PROTECT, related_name="inputs"
    )
    variable = models.ForeignKey(
        VariableFormula, on_delete=models.PROTECT, related_name="inputs_calculo"
    )
    observacion = models.ForeignKey(
        Observacion, on_delete=models.PROTECT, related_name="inputs_calculo"
    )
    valor_utilizado = models.DecimalField(max_digits=20, decimal_places=10)
    unidad = models.CharField(max_length=40)
    concepto = models.SlugField(max_length=120)
    fuente = models.ForeignKey(
        FuenteDatos, on_delete=models.PROTECT, related_name="inputs_calculo"
    )
    evidencia = models.ForeignKey(
        EvidenciaObra,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inputs_calculo",
    )
    version_evidencia = models.ForeignKey(
        VersionEvidencia,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inputs_calculo",
    )


class ImpactoAmbiental(models.Model):
    class Tipo(models.TextChoices):
        GENERADO = "generado", "Generado"
        REDUCCION = "reduccion", "Reduccion"
        EVITADO = "evitado", "Evitado"
        CAPTURA_REMOCION = "captura_remocion", "Captura/remocion"
        COMPENSACION = "compensacion", "Compensacion"
        OTRO = "otro", "Otro"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.PROTECT, related_name="impactos_ambientales_v2"
    )
    actividad = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.PROTECT,
        related_name="impactos_ambientales",
    )
    calculo = models.OneToOneField(
        CalculoAmbiental, on_delete=models.PROTECT, related_name="impacto"
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.GENERADO)
    categoria = models.CharField(max_length=80)
    valor = models.DecimalField(max_digits=24, decimal_places=10)
    unidad = models.CharField(max_length=60)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
