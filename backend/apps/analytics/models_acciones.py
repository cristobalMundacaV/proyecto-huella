from django.db import models

from .models import Constructora


class AccionAmbiental(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROGRESO = "en_progreso", "En progreso"
        VALIDACION = "validacion", "En validacion"
        COMPLETADA = "completada", "Completada"

    constructora = models.ForeignKey(
        Constructora,
        on_delete=models.CASCADE,
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
            models.Index(fields=["constructora", "status"]),
            models.Index(fields=["constructora", "due_date"]),
        ]

    def __str__(self):
        return f"{self.constructora.constructora_id} - {self.title}"
