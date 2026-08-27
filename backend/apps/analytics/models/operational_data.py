from django.contrib.auth.models import User
from django.db import models

from .assets import ActivoOperacional
from .operational_context import Obra, ProcesoOperacional, UnidadOperacional
from .platform import Organizacion


class FuenteDatos(models.Model):
    class Tipo(models.TextChoices):
        MANUAL = "manual", "Manual"
        DOCUMENTO = "documento", "Documento"
        EXCEL_CSV = "excel_csv", "Excel o CSV"
        API = "api", "API"
        GPS = "gps", "GPS"
        SENSOR = "sensor", "Sensor"
        TELEMETRIA = "telemetria", "Telemetria"
        ERP = "erp", "ERP"
        SISTEMA_EXTERNO = "sistema_externo", "Sistema externo"
        SISTEMA = "sistema", "Sistema"
        OTRO = "otro", "Otro"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="fuentes_datos"
    )
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(
        max_length=30, choices=Tipo.choices, default=Tipo.MANUAL, db_index=True
    )
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    identificador_externo = models.CharField(max_length=180, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "nombre"], name="unique_fuente_datos_nombre_org"
            )
        ]


class ActividadOperacional(models.Model):
    class Tipo(models.TextChoices):
        TRANSPORTE = "transporte", "Transporte"
        CONSUMO_ENERGIA = "consumo_energia", "Consumo de energia"
        CONSUMO_AGUA = "consumo_agua", "Consumo de agua"
        CONSUMO_COMBUSTIBLE = "consumo_combustible", "Consumo de combustible"
        CONSUMO_COMBUSTIBLE_ESTACIONARIO = (
            "consumo_combustible_estacionario",
            "Consumo de combustible estacionario",
        )
        OPERACION_MAQUINARIA = "operacion_maquinaria", "Operacion de maquinaria"
        MOVIMIENTO_MATERIAL = "movimiento_material", "Movimiento de material"
        GESTION_RESIDUO = "gestion_residuo", "Gestion de residuo"
        GENERACION_ENERGIA = "generacion_energia", "Generacion de energia"
        MONITOREO_RUIDO = "monitoreo_ruido", "Monitoreo de ruido"
        MONITOREO_EMISIONES_ATMOSFERICAS = (
            "monitoreo_emisiones_atmosfericas",
            "Monitoreo de emisiones atmosfericas",
        )
        GESTION_SUELO = "gestion_suelo", "Gestion de suelo"
        GESTION_HIDRICA_SUELO = "gestion_hidrica_suelo", "Gestion hidrica y suelo"
        PROCESO_PRODUCTIVO = "proceso_productivo", "Proceso productivo"
        OTRO = "otro", "Otro"

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        REGISTRADA = "registrada", "Registrada"
        INCOMPLETA = "incompleta", "Incompleta"
        LISTA_EVALUACION = "lista_para_evaluacion", "Lista para evaluacion"
        ANULADA = "anulada", "Anulada"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="actividades_operacionales"
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actividades_operacionales",
    )
    tipo = models.CharField(
        max_length=40, choices=Tipo.choices, default=Tipo.OTRO, db_index=True
    )
    codigo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=180)
    timestamp_inicio = models.DateTimeField(db_index=True)
    timestamp_fin = models.DateTimeField(null=True, blank=True)
    unidad_operacional = models.ForeignKey(
        UnidadOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actividades",
    )
    proceso_operacional = models.ForeignKey(
        ProcesoOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actividades",
    )
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.BORRADOR, db_index=True
    )
    referencia_externa = models.CharField(max_length=180, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    activos = models.ManyToManyField(
        ActivoOperacional, blank=True, related_name="actividades"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-timestamp_inicio", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "codigo"], name="unique_actividad_codigo_org"
            )
        ]
        indexes = [models.Index(fields=["organizacion", "tipo", "estado"])]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if (
            self.unidad_operacional_id
            and self.unidad_operacional.organizacion_id != self.organizacion_id
        ):
            errors["unidad_operacional"] = (
                "La unidad debe pertenecer a la misma organizacion."
            )
        if (
            self.proceso_operacional_id
            and self.proceso_operacional.organizacion_id != self.organizacion_id
        ):
            errors["proceso_operacional"] = (
                "El proceso debe pertenecer a la misma organizacion."
            )
        if self.obra_id and self.obra.organizacion_id != self.organizacion_id:
            errors["obra"] = "La obra debe pertenecer a la misma organizacion."
        if (
            self.timestamp_fin
            and self.timestamp_inicio
            and self.timestamp_fin < self.timestamp_inicio
        ):
            errors["timestamp_fin"] = "El fin no puede ser anterior al inicio."
        if errors:
            raise ValidationError(errors)


class Observacion(models.Model):
    class MetodoCaptura(models.TextChoices):
        MANUAL = "manual", "Manual"
        EXTRAIDO = "extraido_automaticamente", "Extraido automaticamente"
        IMPORTADO = "importado", "Importado"
        API = "api", "API"
        INSTRUMENTAL = "instrumental", "Instrumental"
        DERIVADO = "derivado", "Derivado"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        VALIDADA = "validada", "Validada"
        RECHAZADA = "rechazada", "Rechazada"

    class Naturaleza(models.TextChoices):
        DECLARATIVO = "declarativo", "Declarativo"
        DOCUMENTAL = "documental", "Documental"
        INSTRUMENTAL = "instrumental", "Instrumental"
        EXTRAIDO = "extraido_automaticamente", "Extraido automaticamente"

    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="observaciones_operacionales",
    )
    actividad = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="observaciones",
    )
    fuente = models.ForeignKey(
        FuenteDatos, on_delete=models.PROTECT, related_name="observaciones"
    )
    concepto = models.SlugField(max_length=120, db_index=True)
    valor_numerico = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    valor_texto = models.TextField(blank=True)
    unidad = models.CharField(max_length=40, blank=True)
    timestamp_observacion = models.DateTimeField(db_index=True)
    metodo_captura = models.CharField(
        max_length=35, choices=MetodoCaptura.choices, default=MetodoCaptura.MANUAL
    )
    naturaleza = models.CharField(
        max_length=35, choices=Naturaleza.choices, default=Naturaleza.DECLARATIVO
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="observaciones_operacionales",
    )
    evidencia = models.ForeignKey(
        "analytics.EvidenciaObra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="observaciones_operacionales",
    )
    version_evidencia = models.ForeignKey(
        "analytics.VersionEvidencia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="observaciones_operacionales",
    )
    registro_extraido = models.ForeignKey(
        "analytics.RegistroExtraido",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="observaciones_creadas",
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-timestamp_observacion", "id"]
        indexes = [models.Index(fields=["organizacion", "concepto"])]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if self.actividad_id and self.actividad.organizacion_id != self.organizacion_id:
            errors["actividad"] = (
                "La actividad debe pertenecer a la misma organizacion."
            )
        if self.fuente_id and self.fuente.organizacion_id != self.organizacion_id:
            errors["fuente"] = "La fuente debe pertenecer a la misma organizacion."
        if self.evidencia_id and self.evidencia.organizacion_id != self.organizacion_id:
            errors["evidencia"] = (
                "La evidencia debe pertenecer a la misma organizacion."
            )
        if (
            self.version_evidencia_id
            and self.version_evidencia.organizacion_id != self.organizacion_id
        ):
            errors["version_evidencia"] = (
                "La version de evidencia debe pertenecer a la misma organizacion."
            )
        if (
            self.version_evidencia_id
            and self.evidencia_id
            and self.version_evidencia.evidencia_id != self.evidencia_id
        ):
            errors["version_evidencia"] = (
                "La version debe pertenecer a la evidencia asociada."
            )
        if self.valor_numerico is None and not self.valor_texto:
            errors["valor_numerico"] = "Debe informar un valor numerico o textual."
        if self.valor_numerico is not None and self.valor_texto:
            errors["valor_texto"] = "Use solo un tipo de valor por observacion."
        if errors:
            raise ValidationError(errors)
