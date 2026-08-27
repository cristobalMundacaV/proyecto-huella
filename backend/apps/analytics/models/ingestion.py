from django.db import models

from .operational_data import ActividadOperacional, FuenteDatos
from .platform import Organizacion
from .provenance import VersionEvidencia


class PlantillaMapeo(models.Model):
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="plantillas_mapeo"
    )
    fuente_datos = models.ForeignKey(
        FuenteDatos, on_delete=models.CASCADE, related_name="plantillas_mapeo"
    )
    nombre = models.CharField(max_length=180)
    formato = models.CharField(max_length=20, default="excel_csv")
    tipo_ingesta = models.CharField(max_length=30, default="tabular")
    destino_operacional = models.CharField(max_length=30, default="actividad_generica")
    flujo = models.CharField(max_length=35, blank=True)
    version = models.PositiveIntegerField(default=1)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "fuente_datos", "nombre", "version"],
                name="unique_plantilla_mapeo_version",
            )
        ]

    def clean(self):
        if (
            self.fuente_datos_id
            and self.fuente_datos.organizacion_id != self.organizacion_id
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                {
                    "fuente_datos": "La fuente de la plantilla pertenece a otra organizacion."
                }
            )


class MapeoColumna(models.Model):
    plantilla = models.ForeignKey(
        PlantillaMapeo, on_delete=models.CASCADE, related_name="mapeos"
    )
    columna_origen = models.CharField(max_length=180)
    columna_normalizada = models.SlugField(max_length=180)
    concepto_normalizado = models.SlugField(max_length=120)
    unidad_esperada = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["columna_origen"]
        constraints = [
            models.UniqueConstraint(
                fields=["plantilla", "columna_normalizada"],
                name="unique_mapeo_columna_plantilla",
            )
        ]


class ProcesoIngesta(models.Model):
    class TipoIngesta(models.TextChoices):
        TABULAR = "tabular", "Tabular"
        DOCUMENTAL = "documental", "Documental"
        MANUAL_ESTRUCTURADO = "manual_estructurado", "Manual estructurado"
        API = "api", "API"
        TELEMETRIA = "telemetria", "Telemetria"
        SENSOR = "sensor", "Sensor"

    class DestinoOperacional(models.TextChoices):
        TRANSPORTE = "transporte", "Transporte"
        MATERIAL = "material", "Material"
        FLUJO_AMBIENTAL = "flujo_ambiental", "Flujo ambiental"
        ACTIVIDAD_GENERICA = "actividad_generica", "Actividad generica"

    class Estado(models.TextChoices):
        RECIBIDO = "recibido", "Recibido"
        ANALIZANDO = "analizando", "Analizando"
        REQUIERE_MAPEO = "requiere_mapeo", "Requiere mapeo"
        LISTO_CONFIRMAR = "listo_para_confirmar", "Listo para confirmar"
        PROCESANDO = "procesando", "Procesando"
        COMPLETADO = "completado", "Completado"
        COMPLETADO_OBSERVACIONES = (
            "completado_con_observaciones",
            "Completado con observaciones",
        )
        FALLIDO = "fallido", "Fallido"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="procesos_ingesta"
    )
    version_evidencia = models.ForeignKey(
        VersionEvidencia,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="procesos_ingesta",
    )
    fuente_datos = models.ForeignKey(
        FuenteDatos, on_delete=models.PROTECT, related_name="procesos_ingesta"
    )
    plantilla_mapeo = models.ForeignKey(
        PlantillaMapeo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procesos_ingesta",
    )
    tipo_ingesta = models.CharField(
        max_length=30, choices=TipoIngesta.choices, default=TipoIngesta.TABULAR
    )
    destino_operacional = models.CharField(
        max_length=30,
        choices=DestinoOperacional.choices,
        default=DestinoOperacional.ACTIVIDAD_GENERICA,
    )
    flujo = models.CharField(max_length=35, blank=True)
    clasificacion_sugerida = models.CharField(max_length=80, blank=True)
    clasificacion_confirmada = models.CharField(max_length=80, blank=True)
    contexto_sugerido = models.JSONField(default=dict, blank=True)
    contexto_confirmado = models.JSONField(default=dict, blank=True)
    estado = models.CharField(
        max_length=40, choices=Estado.choices, default=Estado.RECIBIDO, db_index=True
    )
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    filas_detectadas = models.PositiveIntegerField(default=0)
    filas_procesadas = models.PositiveIntegerField(default=0)
    filas_con_error = models.PositiveIntegerField(default=0)
    resumen_errores = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.version_evidencia_id
            and self.version_evidencia.organizacion_id != self.organizacion_id
        ):
            raise ValidationError(
                {"version_evidencia": "La evidencia pertenece a otra organizacion."}
            )
        if (
            self.tipo_ingesta in {self.TipoIngesta.TABULAR, self.TipoIngesta.DOCUMENTAL}
            and not self.version_evidencia_id
        ):
            raise ValidationError(
                {
                    "version_evidencia": "La ingesta tabular o documental requiere una versión de evidencia."
                }
            )
        if (
            self.fuente_datos_id
            and self.fuente_datos.organizacion_id != self.organizacion_id
        ):
            raise ValidationError(
                {"fuente_datos": "La fuente pertenece a otra organizacion."}
            )
        if (
            self.plantilla_mapeo_id
            and self.plantilla_mapeo.organizacion_id != self.organizacion_id
        ):
            raise ValidationError(
                {"plantilla_mapeo": "La plantilla pertenece a otra organizacion."}
            )


class RegistroExtraido(models.Model):
    class Estado(models.TextChoices):
        EXTRAIDO = "extraido", "Extraido"
        NORMALIZADO = "normalizado", "Normalizado"
        REQUIERE_MAPEO = "requiere_mapeo", "Requiere mapeo"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        LISTO = "listo", "Listo"
        VALIDO = "valido", "Valido"
        ERROR = "error", "Error"
        PROCESADO = "procesado", "Procesado"

    proceso_ingesta = models.ForeignKey(
        ProcesoIngesta, on_delete=models.CASCADE, related_name="registros_extraidos"
    )
    numero_fila = models.PositiveIntegerField()
    origen = models.CharField(max_length=120, blank=True)
    datos_originales = models.JSONField(default=dict)
    datos_normalizados = models.JSONField(default=dict, blank=True)
    auto_confirmable = models.BooleanField(default=False)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.EXTRAIDO, db_index=True
    )
    errores = models.JSONField(default=list, blank=True)
    actividad_creada = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_origen",
    )
    resultado_procesamiento = models.JSONField(default=dict, blank=True)
    procesado_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["numero_fila"]
        constraints = [
            models.UniqueConstraint(
                fields=["proceso_ingesta", "numero_fila"],
                name="unique_registro_extraido_fila",
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            previous = (
                RegistroExtraido.objects.filter(pk=self.pk)
                .values("estado", "datos_originales")
                .first()
            )
            if (
                previous
                and previous["estado"] == self.Estado.PROCESADO
                and previous["datos_originales"] != self.datos_originales
            ):
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    "Los datos originales de un registro procesado son inmutables."
                )
        super().save(*args, **kwargs)
