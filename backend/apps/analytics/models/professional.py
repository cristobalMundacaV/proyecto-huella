from django.contrib.auth.models import User
from django.db import models

from .calculations import CalculoAmbiental, ImpactoAmbiental
from .governance import VersionMetodologia
from .improvement import (
    ProblematicaAmbiental,
    ResultadoIntervencion,
    SnapshotIntervencion,
)
from .indicators import IndicadorAmbiental
from .operational_data import Observacion
from .platform import Organizacion
from .provenance import EvidenciaObra
from .reporting import ExpedienteAmbiental


class RevisionProfesionalAmbiental(models.Model):
    class Tipo(models.TextChoices):
        EVIDENCIA = "evidencia", "Evidencia"
        OBSERVACION = "observacion", "Observacion"
        CALCULO = "calculo", "Calculo"
        INDICADOR = "indicador", "Indicador"
        PROBLEMATICA = "problematica", "Problematica"
        INTERVENCION = "intervencion", "Intervencion"
        EXPEDIENTE = "expediente", "Expediente"
        METODOLOGIA = "metodologia", "Version metodologica"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        VALIDADA = "validada", "Validada"
        VALIDADA_OBSERVACIONES = (
            "validada_con_observaciones",
            "Validada con observaciones",
        )
        SOLICITA_ANTECEDENTES = "solicita_antecedentes", "Solicita antecedentes"
        RECHAZADA = "rechazada", "Rechazada"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="revisiones_profesionales"
    )
    tipo = models.CharField(max_length=25, choices=Tipo.choices)
    evidencia = models.ForeignKey(
        EvidenciaObra,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    observacion = models.ForeignKey(
        Observacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    calculo = models.ForeignKey(
        CalculoAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    indicador = models.ForeignKey(
        IndicadorAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    intervencion = models.ForeignKey(
        ResultadoIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    expediente = models.ForeignKey(
        ExpedienteAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    version_metodologia = models.ForeignKey(
        VersionMetodologia,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    estado = models.CharField(
        max_length=35, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    profesional = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    profesional_nombre = models.CharField(max_length=180, blank=True)
    profesional_cargo = models.CharField(max_length=120, blank=True)
    fecha = models.DateTimeField(null=True, blank=True)
    conclusion = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    antecedentes_solicitados = models.JSONField(default=list, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    REFERENCE_BY_TYPE = {
        Tipo.EVIDENCIA: "evidencia",
        Tipo.OBSERVACION: "observacion",
        Tipo.CALCULO: "calculo",
        Tipo.INDICADOR: "indicador",
        Tipo.PROBLEMATICA: "problematica",
        Tipo.INTERVENCION: "intervencion",
        Tipo.EXPEDIENTE: "expediente",
        Tipo.METODOLOGIA: "version_metodologia",
    }

    def clean(self):
        from django.core.exceptions import ValidationError

        references = {
            field: getattr(self, f"{field}_id")
            for field in self.REFERENCE_BY_TYPE.values()
        }
        populated = [field for field, value in references.items() if value]
        if len(populated) != 1:
            raise ValidationError("La revision debe referenciar exactamente un objeto.")
        expected = self.REFERENCE_BY_TYPE.get(self.tipo)
        if not expected or populated[0] != expected:
            raise ValidationError(
                {"tipo": "El tipo de revision no corresponde al objeto revisado."}
            )
        item = getattr(self, expected)
        owner_id = getattr(item, "organizacion_id", None)
        if isinstance(item, VersionMetodologia):
            owner_id = item.metodologia.organizacion_id
        elif owner_id is None:
            owner_id = item.problematica.organizacion_id
        if (
            self.organizacion_id
            and owner_id is not None
            and owner_id != self.organizacion_id
        ):
            raise ValidationError("El objeto revisado pertenece a otra organizacion.")

    def save(self, *args, **kwargs):
        if (
            self.pk
            and RevisionProfesionalAmbiental.objects.filter(
                pk=self.pk,
                estado__in=[
                    self.Estado.VALIDADA,
                    self.Estado.VALIDADA_OBSERVACIONES,
                    self.Estado.RECHAZADA,
                ],
            ).exists()
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Una revision profesional decidida es inmutable; cree una nueva version."
            )
        self.full_clean()
        super().save(*args, **kwargs)


class HallazgoRevisionProfesional(models.Model):
    class Tipo(models.TextChoices):
        OBSERVACION = "observacion", "Observacion"
        INCONSISTENCIA = "inconsistencia", "Inconsistencia"
        FALTA_ANTECEDENTE = "falta_antecedente", "Falta antecedente"
        CORRECCION = "correccion_requerida", "Correccion requerida"
        VALIDACION = "validacion", "Validacion"
        RECOMENDACION = "recomendacion", "Recomendacion"

    class Severidad(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"
        CRITICA = "critica", "Critica"

    revision = models.ForeignKey(
        RevisionProfesionalAmbiental, on_delete=models.PROTECT, related_name="hallazgos"
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    severidad = models.CharField(
        max_length=15, choices=Severidad.choices, default=Severidad.MEDIA
    )
    observacion = models.TextField()
    recomendacion = models.TextField(blank=True)
    requerimiento = models.TextField(blank=True)
    decision = models.TextField(blank=True)
    referencia_tecnica = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CorreccionHistoricaAmbiental(models.Model):
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="correcciones_historicas"
    )
    observacion_afectada = models.ForeignKey(
        Observacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_historicas",
    )
    calculo_afectado = models.ForeignKey(
        CalculoAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_historicas",
    )
    impacto_afectado = models.ForeignKey(
        ImpactoAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_historicas",
    )
    snapshot_afectado = models.ForeignKey(
        SnapshotIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_historicas",
    )
    resultado_afectado = models.ForeignKey(
        ResultadoIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_historicas",
    )
    motivo = models.TextField()
    valor_estado_anterior = models.JSONField(default=dict)
    propuesta_corregida = models.JSONField(default=dict)
    autor = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="correcciones_historicas"
    )
    fecha = models.DateTimeField(auto_now_add=True)
    revision_origen = models.ForeignKey(
        RevisionProfesionalAmbiental,
        on_delete=models.PROTECT,
        related_name="correcciones_historicas",
    )
    version = models.PositiveIntegerField(default=1)
    recalculo_generado = models.ForeignKey(
        CalculoAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_origen",
    )

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.revision_origen_id
            and self.organizacion_id != self.revision_origen.organizacion_id
        ):
            raise ValidationError(
                {"revision_origen": "La revision origen pertenece a otra organizacion."}
            )

        owners = {
            "observacion_afectada": (
                self.observacion_afectada.organizacion_id
                if self.observacion_afectada_id
                else None
            ),
            "calculo_afectado": (
                self.calculo_afectado.organizacion_id
                if self.calculo_afectado_id
                else None
            ),
            "impacto_afectado": (
                self.impacto_afectado.organizacion_id
                if self.impacto_afectado_id
                else None
            ),
            "snapshot_afectado": (
                self.snapshot_afectado.problematica.organizacion_id
                if self.snapshot_afectado_id
                else None
            ),
            "resultado_afectado": (
                self.resultado_afectado.problematica.organizacion_id
                if self.resultado_afectado_id
                else None
            ),
            "recalculo_generado": (
                self.recalculo_generado.organizacion_id
                if self.recalculo_generado_id
                else None
            ),
        }
        errors = {
            field: "La referencia pertenece a otra organizacion."
            for field, owner_id in owners.items()
            if owner_id is not None and owner_id != self.organizacion_id
        }
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
