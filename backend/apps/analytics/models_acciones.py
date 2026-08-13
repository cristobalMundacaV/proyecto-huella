from django.db import models

from .models import Organizacion, EvidenciaObra, LoteForestal, Obra, RegistroEmision


class AccionAmbiental(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROGRESO = "en_progreso", "En progreso"
        VALIDACION = "validacion", "En validacion"
        COMPLETADA = "completada", "Completada"

    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="acciones_ambientales_orm",
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_ambientales_orm",
    )
    lote_forestal = models.ForeignKey(
        LoteForestal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_ambientales_orm",
    )
    registro_emision = models.ForeignKey(
        RegistroEmision,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_ambientales_orm",
    )
    evidencia = models.ForeignKey(
        EvidenciaObra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_ambientales_orm",
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    responsible = models.CharField(max_length=160, blank=True, default="Equipo ambiental")
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
    )
    source = models.CharField(max_length=160, blank=True)
    evidence = models.CharField(max_length=220, blank=True)
    tracking_kpi = models.CharField(max_length=180, blank=True)
    source_card_id = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "analytics"
        db_table = "analytics_accionambiental"
        managed = False
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organizacion", "status"]),
            models.Index(fields=["organizacion", "due_date"]),
            models.Index(fields=["organizacion", "obra"]),
            models.Index(fields=["organizacion", "lote_forestal"]),
            models.Index(fields=["organizacion", "registro_emision"]),
            models.Index(fields=["organizacion", "evidencia"]),
        ]

    def __str__(self):
        return f"{self.organizacion.organizacion_id} - {self.title}"
