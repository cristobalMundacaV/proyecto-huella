from django.contrib.auth.models import User
from django.db import models

from .operational_context import AreaOperacional, EtapaObra, Obra
from .platform import Organizacion


def evidencia_obra_upload_path(instance, filename):
    organizacion = (
        instance.organizacion.organizacion_id
        if instance.organizacion_id
        else "SIN_ORGANIZACION"
    )
    obra = instance.obra.codigo_obra if instance.obra_id else "GENERAL"
    return f"evidencias/{organizacion}/{obra}/{filename}"


def version_evidencia_upload_path(instance, filename):
    organizacion = (
        instance.organizacion.organizacion_id
        if instance.organizacion_id
        else "SIN_ORGANIZACION"
    )
    return f"evidencias/{organizacion}/versiones/{filename}"


# Keep historical migration serialization paths stable after physical extraction.
evidencia_obra_upload_path.__module__ = "apps.analytics.models"
version_evidencia_upload_path.__module__ = "apps.analytics.models"


class EvidenciaObra(models.Model):
    class TipoEvidencia(models.TextChoices):
        FACTURA_MATERIAL = "factura_material", "Factura de material"
        GUIA_DESPACHO = "guia_despacho", "Guia de despacho"
        ORDEN_COMPRA = "orden_compra", "Orden de compra"
        FACTURA_COMBUSTIBLE = "factura_combustible", "Factura de combustible"
        DOCUMENTO_ORIGEN = "documento_origen", "Documento de origen"
        BOLETA_ELECTRICA = "boleta_electrica", "Boleta electrica"
        TICKET_PESAJE = "ticket_pesaje", "Ticket de pesaje"
        FICHA_TECNICA = "ficha_tecnica_material", "Ficha tecnica de material"
        CERTIFICADO_PROVEEDOR = "certificado_proveedor", "Certificado de proveedor"
        CERTIFICADO_FORESTAL = "certificado_forestal", "Certificado forestal"
        REGISTRO_MAQUINARIA = "registro_maquinaria", "Registro de maquinaria"
        REGISTRO_RESIDUOS = "registro_retiro_residuos", "Registro de retiro de residuos"
        REGISTRO_PRODUCCION = "registro_produccion", "Registro produccion"
        REGISTRO_SECADO = "registro_secado", "Registro secado"
        DOCUMENTO_TRANSPORTE = "documento_transporte", "Documento de transporte"
        OTRO = "otro", "Otro"

    class EstadoDocumental(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        VALIDADA = "validada", "Validada"
        OBSERVADA = "observada", "Observada"
        RECHAZADA = "rechazada", "Rechazada"
        SIN_VINCULO = "sin_vinculo", "Sin vinculo"
        VINCULADA = "vinculada", "Vinculada"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="evidencias"
    )
    area_origen = models.ForeignKey(
        AreaOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidencias_origen",
    )
    usuario_origen = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidencias_originadas",
    )
    metodo_captura = models.CharField(max_length=30, default="documento", blank=True)
    obra = models.ForeignKey(
        Obra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidencias",
    )
    etapa = models.ForeignKey(
        EtapaObra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidencias",
    )
    registros_emision = models.ManyToManyField(
        "RegistroEmision", blank=True, related_name="evidencias"
    )
    lote_forestal = models.ForeignKey(
        "LoteForestal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidencias",
    )
    tipo_evidencia = models.CharField(
        max_length=40, choices=TipoEvidencia.choices, default=TipoEvidencia.OTRO
    )
    estado_documental = models.CharField(
        max_length=20,
        choices=EstadoDocumental.choices,
        default=EstadoDocumental.PENDIENTE,
    )
    fecha_documento = models.DateField(null=True, blank=True)
    archivo = models.FileField(upload_to=evidencia_obra_upload_path)
    nombre = models.CharField(max_length=240)
    observaciones = models.TextField(blank=True)
    texto_extraido = models.TextField(blank=True)
    metadata_extraccion = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organizacion_id", "estado_documental"]),
            models.Index(fields=["organizacion_id", "tipo_evidencia"]),
            models.Index(fields=["obra_id", "estado_documental"]),
            models.Index(fields=["lote_forestal_id"]),
        ]

    def save(self, *args, **kwargs):
        if self.obra_id and not self.organizacion_id:
            self.organizacion = self.obra.organizacion
        if not self.lote_forestal_id and self.organizacion_id:
            metadata = (
                self.metadata_extraccion
                if isinstance(self.metadata_extraccion, dict)
                else {}
            )
            lote_reference = (
                metadata.get("lote")
                or metadata.get("lote_id")
                or metadata.get("lote_forestal")
            )
            if lote_reference:
                lote_model = self._meta.get_field("lote_forestal").remote_field.model
                self.lote_forestal = lote_model.objects.filter(
                    organizacion_id=self.organizacion_id,
                    lote_id=str(lote_reference).strip(),
                ).first()
        if self.lote_forestal_id and self.estado_documental in {"sin_vinculo", ""}:
            self.estado_documental = self.EstadoDocumental.VINCULADA
        elif (
            not self.obra_id
            and self.estado_documental == self.EstadoDocumental.PENDIENTE
        ):
            self.estado_documental = self.EstadoDocumental.SIN_VINCULO
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.organizacion.organizacion_id} - {self.nombre}"


class VersionEvidencia(models.Model):
    class EstadoProcesamiento(models.TextChoices):
        RECIBIDA = "recibida", "Recibida"
        ANALIZANDO = "analizando", "Analizando"
        LISTA = "lista", "Lista"
        PROCESADA = "procesada", "Procesada"
        ERROR = "error", "Error"

    evidencia = models.ForeignKey(
        EvidenciaObra, on_delete=models.CASCADE, related_name="versiones"
    )
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="versiones_evidencia"
    )
    version = models.PositiveIntegerField()
    archivo = models.FileField(upload_to=version_evidencia_upload_path)
    nombre_original = models.CharField(max_length=240)
    tipo_documental = models.CharField(max_length=80, blank=True)
    checksum_sha256 = models.CharField(max_length=64, db_index=True)
    estado_procesamiento = models.CharField(
        max_length=20,
        choices=EstadoProcesamiento.choices,
        default=EstadoProcesamiento.RECIBIDA,
    )
    metadata_tecnica = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["evidencia", "version"], name="unique_version_evidencia"
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.evidencia_id and self.organizacion_id != self.evidencia.organizacion_id:
            raise ValidationError(
                {
                    "organizacion": "La version debe pertenecer a la organizacion de la evidencia."
                }
            )
