from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .improvement import ProblematicaAmbiental, ResultadoIntervencion
from .operational_data import ActividadOperacional
from .platform import Organizacion


class ExpedienteAmbiental(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = "abierto", "Abierto"
        RECOPILANDO = "recopilando_antecedentes", "Recopilando antecedentes"
        EN_REVISION = "en_revision", "En revision"
        REQUIERE_ANTECEDENTES = "requiere_antecedentes", "Requiere antecedentes"
        VALIDADO = "validado", "Validado"
        CERRADO = "cerrado", "Cerrado"
        REABIERTO = "reabierto", "Reabierto"

    problematica = models.ForeignKey(
        ProblematicaAmbiental, on_delete=models.CASCADE, related_name="expedientes"
    )
    version = models.PositiveIntegerField(default=1)
    contenido_procesado = models.JSONField(default=dict)
    resumen_ejecutivo = models.TextField()
    proveedor_resumen = models.CharField(max_length=80, blank=True)
    modelo_resumen = models.CharField(max_length=120, blank=True)
    generado_por = models.CharField(max_length=150, blank=True)
    estado = models.CharField(
        max_length=35, choices=Estado.choices, default=Estado.ABIERTO
    )
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_ambientales_responsable",
    )
    referencias = models.JSONField(default=dict, blank=True)
    cerrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_ambientales_cerrados",
    )
    cerrado_at = models.DateTimeField(null=True, blank=True)
    reabierto_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_ambientales_reabiertos",
    )
    reabierto_at = models.DateTimeField(null=True, blank=True)
    motivo_reapertura = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["problematica", "version"],
                name="unique_expediente_problematica_version",
            )
        ]


class EventoAuditoriaAmbiental(models.Model):
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="eventos_auditoria_ambiental",
    )
    tipo = models.SlugField(max_length=80, db_index=True)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_auditoria_ambiental",
    )
    entidad = models.CharField(max_length=80)
    referencia = models.CharField(max_length=120)
    resumen = models.TextField()
    metadata_auditable = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp", "-id"]


class InformeAmbiental(models.Model):
    class Tipo(models.TextChoices):
        ACTIVIDAD = "actividad", "Actividad"
        PROBLEMATICA = "problematica", "Problematica"
        INTERVENCION = "intervencion", "Intervencion"
        EXPEDIENTE = "expediente", "Expediente"

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        GENERADO = "generado", "Generado"
        REVISADO = "revisado", "Revisado"
        VALIDADO = "validado", "Validado"
        OBSOLETO = "obsoleto", "Obsoleto"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="informes_ambientales"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    actividad = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="informes_ambientales",
    )
    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="informes_ambientales",
    )
    intervencion = models.ForeignKey(
        ResultadoIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="informes_ambientales",
    )
    expediente = models.ForeignKey(
        ExpedienteAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="informes",
    )
    version = models.PositiveIntegerField()
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.BORRADOR
    )
    generado_por = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="informes_ambientales_generados"
    )
    fecha = models.DateTimeField(default=timezone.now)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    archivo = models.FileField(upload_to="informes_ambientales/%Y/%m/", blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    validado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="informes_ambientales_validados",
    )
    validado_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organizacion",
                    "tipo",
                    "actividad",
                    "problematica",
                    "intervencion",
                    "expediente",
                    "version",
                ],
                name="unique_informe_ambiental_version",
            )
        ]

    def save(self, *args, **kwargs):
        if (
            self.pk
            and InformeAmbiental.objects.filter(
                pk=self.pk, estado=self.Estado.VALIDADO
            ).exists()
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Un informe validado es inmutable; genere una nueva version."
            )
        super().save(*args, **kwargs)


class SnapshotInformeAmbiental(models.Model):
    informe = models.OneToOneField(
        InformeAmbiental, on_delete=models.PROTECT, related_name="snapshot"
    )
    contenido = models.JSONField(default=dict)
    referencias = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            from django.core.exceptions import ValidationError

            raise ValidationError("El snapshot de informe es inmutable.")
        super().save(*args, **kwargs)
