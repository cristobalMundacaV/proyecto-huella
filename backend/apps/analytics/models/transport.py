from django.db import models

from .assets import Vehiculo
from .operational_data import ActividadOperacional, Observacion
from .platform import Organizacion


class RutaOperacional(models.Model):
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="rutas_operacionales"
    )
    codigo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=180, blank=True)
    origen_nombre = models.CharField(max_length=240)
    origen_referencia = models.CharField(max_length=180, blank=True)
    origen_coordenadas = models.JSONField(default=dict, blank=True)
    destino_nombre = models.CharField(max_length=240)
    destino_referencia = models.CharField(max_length=180, blank=True)
    destino_coordenadas = models.JSONField(default=dict, blank=True)
    distancia_planificada = models.DecimalField(
        max_digits=16, decimal_places=3, null=True, blank=True
    )
    unidad_distancia = models.CharField(max_length=20, default="km")
    fuente_distancia = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "codigo"],
                name="unique_ruta_operacional_codigo_org",
            )
        ]


class ViajeOperacional(models.Model):
    class EstadoCarga(models.TextChoices):
        CARGADO = "cargado", "Cargado"
        PARCIAL = "parcialmente_cargado", "Parcialmente cargado"
        VACIO = "vacio", "Vacio"
        DESCONOCIDO = "desconocido", "Desconocido"

    class TipoTrayecto(models.TextChoices):
        IDA = "ida", "Ida"
        RETORNO = "retorno", "Retorno"
        INTERNO = "interno", "Interno"
        OTRO = "otro", "Otro"

    class TipoGestion(models.TextChoices):
        PROPIO = "propio", "Propio"
        TERCERIZADO = "tercerizado", "Tercerizado"

    class Estado(models.TextChoices):
        PLANIFICADO = "planificado", "Planificado"
        EN_CURSO = "en_curso", "En curso"
        COMPLETADO = "completado", "Completado"
        CANCELADO = "cancelado", "Cancelado"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="viajes_operacionales"
    )
    actividad = models.OneToOneField(
        ActividadOperacional, on_delete=models.CASCADE, related_name="viaje"
    )
    codigo = models.CharField(max_length=100)
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, related_name="viajes"
    )
    ruta = models.ForeignKey(
        RutaOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="viajes",
    )
    origen_nombre = models.CharField(max_length=240)
    origen_referencia = models.CharField(max_length=180, blank=True)
    origen_coordenadas = models.JSONField(default=dict, blank=True)
    destino_nombre = models.CharField(max_length=240)
    destino_referencia = models.CharField(max_length=180, blank=True)
    destino_coordenadas = models.JSONField(default=dict, blank=True)
    fecha_salida = models.DateTimeField()
    fecha_llegada = models.DateTimeField(null=True, blank=True)
    observacion_distancia = models.ForeignKey(
        Observacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="viajes_distancia_seleccionada",
    )
    observacion_carga = models.ForeignKey(
        Observacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="viajes_carga_seleccionada",
    )
    observacion_combustible = models.ForeignKey(
        Observacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="viajes_combustible_seleccionado",
    )
    estado_carga = models.CharField(
        max_length=25, choices=EstadoCarga.choices, default=EstadoCarga.DESCONOCIDO
    )
    tipo_trayecto = models.CharField(
        max_length=15, choices=TipoTrayecto.choices, default=TipoTrayecto.IDA
    )
    tipo_gestion = models.CharField(
        max_length=15, choices=TipoGestion.choices, default=TipoGestion.PROPIO
    )
    metodologia_tercerizado = models.CharField(max_length=30, blank=True)
    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.PLANIFICADO
    )
    metadata_tecnica = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "codigo"],
                name="unique_viaje_operacional_codigo_org",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if self.actividad_id and (
            self.actividad.organizacion_id != self.organizacion_id
            or self.actividad.tipo != ActividadOperacional.Tipo.TRANSPORTE
        ):
            errors["actividad"] = (
                "La actividad debe ser de transporte y pertenecer a la organizacion."
            )
        if (
            self.vehiculo_id
            and self.vehiculo.activo.organizacion_id != self.organizacion_id
        ):
            errors["vehiculo"] = "El vehiculo pertenece a otra organizacion."
        if self.ruta_id and self.ruta.organizacion_id != self.organizacion_id:
            errors["ruta"] = "La ruta pertenece a otra organizacion."
        expected = {
            "observacion_distancia": "distancia_recorrida_km",
            "observacion_carga": "masa_transportada_t",
            "observacion_combustible": "combustible_consumido_l",
        }
        for field, concept in expected.items():
            observation = getattr(self, field, None)
            if observation and (
                observation.organizacion_id != self.organizacion_id
                or observation.actividad_id != self.actividad_id
                or observation.concepto != concept
            ):
                errors[field] = (
                    "La observacion no corresponde al viaje, tenant o concepto esperado."
                )
            elif (
                observation
                and observation.valor_numerico is not None
                and observation.valor_numerico < 0
            ):
                errors[field] = (
                    "El valor operacional seleccionado no puede ser negativo."
                )
        if self.observacion_carga and self.observacion_carga.valor_numerico is not None:
            load = self.observacion_carga.valor_numerico
            if self.estado_carga == self.EstadoCarga.VACIO and load > 0:
                errors["observacion_carga"] = (
                    "Un viaje vacio no puede tener carga mayor que cero."
                )
            elif (
                self.estado_carga
                in {self.EstadoCarga.CARGADO, self.EstadoCarga.PARCIAL}
                and load == 0
            ):
                errors["observacion_carga"] = (
                    "Un viaje cargado no puede tener carga igual a cero."
                )
        if self.fecha_llegada and self.fecha_llegada < self.fecha_salida:
            errors["fecha_llegada"] = "La llegada no puede ser anterior a la salida."
        if self.tipo_gestion == self.TipoGestion.TERCERIZADO:
            self.metodologia_tercerizado = "pendiente_validacion"
        elif self.metodologia_tercerizado == "pendiente_validacion":
            self.metodologia_tercerizado = ""
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
