from django.db import models

from .operational_context import Obra, ProcesoOperacional, UnidadOperacional
from .platform import Organizacion


class ActivoOperacional(models.Model):
    class Tipo(models.TextChoices):
        VEHICULO = "vehiculo", "Vehiculo"
        MAQUINARIA = "maquinaria", "Maquinaria"
        EQUIPO = "equipo", "Equipo"
        MEDIDOR = "medidor", "Medidor"
        INFRAESTRUCTURA = "infraestructura", "Infraestructura"
        OTRO = "otro", "Otro"

    class Estado(models.TextChoices):
        OPERATIVO = "operativo", "Operativo"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        FUERA_SERVICIO = "fuera_servicio", "Fuera de servicio"
        RETIRADO = "retirado", "Retirado"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="activos_operacionales"
    )
    codigo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(
        max_length=30, choices=Tipo.choices, default=Tipo.OTRO, db_index=True
    )
    descripcion = models.TextField(blank=True)
    unidad_operacional = models.ForeignKey(
        UnidadOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activos",
    )
    proceso_operacional = models.ForeignKey(
        ProcesoOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activos",
    )
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.OPERATIVO, db_index=True
    )
    fecha_alta = models.DateField(null=True, blank=True)
    fecha_baja = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "codigo"], name="unique_activo_codigo_org"
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if (
            self.unidad_operacional_id
            and self.unidad_operacional.organizacion_id != self.organizacion_id
        ):
            errors["unidad_operacional"] = "La unidad pertenece a otra organizacion."
        if (
            self.proceso_operacional_id
            and self.proceso_operacional.organizacion_id != self.organizacion_id
        ):
            errors["proceso_operacional"] = "El proceso pertenece a otra organizacion."
        if errors:
            raise ValidationError(errors)


class Vehiculo(models.Model):
    activo = models.OneToOneField(
        ActivoOperacional, on_delete=models.CASCADE, related_name="vehiculo"
    )
    patente = models.CharField(max_length=30, blank=True)
    marca = models.CharField(max_length=80, blank=True)
    modelo = models.CharField(max_length=80, blank=True)
    anio = models.PositiveIntegerField(null=True, blank=True)
    tipo_vehiculo = models.CharField(max_length=80, blank=True)
    combustible = models.CharField(max_length=80, blank=True)
    capacidad_carga = models.DecimalField(
        max_digits=14, decimal_places=3, null=True, blank=True
    )
    unidad_capacidad_carga = models.CharField(max_length=20, blank=True)
    numero_ejes = models.PositiveSmallIntegerField(null=True, blank=True)


class Maquinaria(models.Model):
    activo = models.OneToOneField(
        ActivoOperacional, on_delete=models.CASCADE, related_name="maquinaria"
    )
    marca = models.CharField(max_length=80, blank=True)
    modelo = models.CharField(max_length=80, blank=True)
    anio = models.PositiveIntegerField(null=True, blank=True)
    tipo_maquinaria = models.CharField(max_length=100, blank=True)
    combustible = models.CharField(max_length=80, blank=True)
    horometro_actual = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )


class MantenimientoActivo(models.Model):
    class Estado(models.TextChoices):
        PROGRAMADO = "programado", "Programado"
        EN_PROCESO = "en_proceso", "En proceso"
        REALIZADO = "realizado", "Realizado"
        VENCIDO = "vencido", "Vencido"
        CANCELADO = "cancelado", "Cancelado"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="mantenimientos_activos"
    )
    activo = models.ForeignKey(
        ActivoOperacional, on_delete=models.CASCADE, related_name="mantenimientos"
    )
    tipo = models.CharField(max_length=100)
    fecha_programada = models.DateField(null=True, blank=True, db_index=True)
    fecha_realizada = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PROGRAMADO, db_index=True
    )
    descripcion = models.TextField(blank=True)
    lectura_momento = models.DecimalField(
        max_digits=14, decimal_places=3, null=True, blank=True
    )
    unidad_lectura = models.CharField(max_length=20, blank=True)
    proveedor_responsable = models.CharField(max_length=180, blank=True)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.activo_id and self.activo.organizacion_id != self.organizacion_id:
            raise ValidationError(
                {"activo": "El activo pertenece a otra organizacion."}
            )


class CondicionOperacionalActivo(models.Model):
    class Estado(models.TextChoices):
        OPERATIVO = "operativo", "Operativo"
        RALENTI = "ralenti", "Ralenti"
        DETENIDO = "detenido", "Detenido"
        MANTENIMIENTO = "mantenimiento", "Mantenimiento"
        FALLA = "falla", "Falla"
        FUERA_SERVICIO = "fuera_servicio", "Fuera de servicio"

    activo = models.ForeignKey(
        ActivoOperacional, on_delete=models.CASCADE, related_name="condiciones"
    )
    timestamp_inicio = models.DateTimeField(db_index=True)
    timestamp_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=30, choices=Estado.choices)
    fuente = models.ForeignKey(
        "analytics.FuenteDatos",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="condiciones_activos",
    )
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp_inicio"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.fuente_id
            and self.fuente.organizacion_id != self.activo.organizacion_id
        ):
            raise ValidationError(
                {"fuente": "La fuente pertenece a otra organizacion."}
            )


class PuntoAmbientalOperacional(models.Model):
    class Tipo(models.TextChoices):
        MEDIDOR_ENERGIA = "medidor_energia", "Medidor de energia"
        PUNTO_AGUA = "punto_agua", "Punto de agua"
        SISTEMA_GENERACION = "sistema_generacion", "Sistema de generacion"
        PUNTO_DESCARGA = "punto_descarga", "Punto de descarga"
        PUNTO_RUIDO = "punto_ruido", "Punto de ruido"
        PUNTO_DRENAJE = "punto_drenaje", "Punto de drenaje"
        OTRO = "otro", "Otro"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="puntos_ambientales"
    )
    codigo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(
        max_length=30, choices=Tipo.choices, default=Tipo.OTRO, db_index=True
    )
    activo = models.ForeignKey(
        ActivoOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="puntos_ambientales",
    )
    unidad_operacional = models.ForeignKey(
        UnidadOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="puntos_ambientales",
    )
    proceso_operacional = models.ForeignKey(
        ProcesoOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="puntos_ambientales",
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="puntos_ambientales",
    )
    ubicacion = models.CharField(max_length=240, blank=True)
    descripcion = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    activo_registro = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "codigo"],
                name="unique_punto_ambiental_codigo_org",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        for field in ("activo", "unidad_operacional", "proceso_operacional", "obra"):
            value = getattr(self, field, None)
            if value and value.organizacion_id != self.organizacion_id:
                errors[field] = "La referencia debe pertenecer a la misma organizacion."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
