from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q

from .operational_data import ActividadOperacional, FuenteDatos, Observacion
from .platform import Organizacion


class EvaluacionCalidadDato(models.Model):
    class Estado(models.TextChoices):
        CONFIABLE = "confiable", "Confiable"
        CONFIABLE_OBSERVACIONES = (
            "confiable_con_observaciones",
            "Confiable con observaciones",
        )
        INCOMPLETO = "incompleto", "Incompleto"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        NO_CONFIABLE = "no_confiable", "No confiable"
        NO_CALCULABLE = "no_calculable", "No calculable"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="evaluaciones_calidad"
    )
    observacion = models.ForeignKey(
        Observacion, on_delete=models.PROTECT, related_name="evaluaciones_calidad"
    )
    estado = models.CharField(max_length=40, choices=Estado.choices, db_index=True)
    motivos = models.JSONField(default=list, blank=True)
    dimensiones = models.JSONField(default=dict, blank=True)
    fecha_evaluacion = models.DateTimeField(auto_now_add=True)
    version_reglas = models.CharField(max_length=30, default="calidad-v1")
    automatica = models.BooleanField(default=True)
    evaluado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluaciones_calidad",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.observacion_id
            and self.observacion.organizacion_id != self.organizacion_id
        ):
            raise ValidationError(
                {"observacion": "La observacion pertenece a otra organizacion."}
            )


class DiscrepanciaDato(models.Model):
    class Estado(models.TextChoices):
        DETECTADA = "detectada", "Detectada"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        RESUELTA = "resuelta", "Resuelta"
        ACEPTADA = "aceptada", "Aceptada"
        DESCARTADA = "descartada", "Descartada"

    class Severidad(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="discrepancias_dato"
    )
    actividad = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discrepancias",
    )
    concepto = models.SlugField(max_length=120, db_index=True)
    observaciones = models.ManyToManyField(Observacion, related_name="discrepancias")
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.DETECTADA
    )
    diferencia_absoluta = models.DecimalField(
        max_digits=24, decimal_places=10, null=True, blank=True
    )
    diferencia_relativa = models.DecimalField(
        max_digits=16, decimal_places=8, null=True, blank=True
    )
    severidad = models.CharField(
        max_length=15, choices=Severidad.choices, default=Severidad.MEDIA
    )
    resolucion = models.TextField(blank=True)
    observacion_seleccionada = models.ForeignKey(
        Observacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="discrepancias_seleccionada",
    )
    motivo = models.TextField(blank=True)
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discrepancias_responsable",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.actividad_id and self.actividad.organizacion_id != self.organizacion_id:
            raise ValidationError(
                {"actividad": "La actividad pertenece a otra organizacion."}
            )
        if (
            self.observacion_seleccionada_id
            and self.observacion_seleccionada.organizacion_id != self.organizacion_id
        ):
            raise ValidationError(
                {
                    "observacion_seleccionada": "La observacion pertenece a otra organizacion."
                }
            )


class PoliticaConfianzaFuente(models.Model):
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="politicas_confianza_fuente",
    )
    concepto = models.SlugField(max_length=120)
    tipo_fuente = models.CharField(max_length=30, choices=FuenteDatos.Tipo.choices)
    prioridad = models.PositiveIntegerField()
    activa = models.BooleanField(default=True)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["concepto", "tipo_fuente"],
                condition=Q(organizacion__isnull=True),
                name="unique_politica_fuente_global",
            ),
            models.UniqueConstraint(
                fields=["organizacion", "concepto", "tipo_fuente"],
                condition=Q(organizacion__isnull=False),
                name="unique_politica_fuente_tenant",
            ),
        ]
