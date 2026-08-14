from decimal import Decimal

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from apps.analytics.models import (ActivoOperacional, ActividadOperacional, EvidenciaObra, FuenteDatos,
                                   Organizacion, EtapaObra, FactorEmision, Obra, Observacion,
                                   ProcesoOperacional, RegistroEmision, UnidadOperacional)


class LecturaSensor(models.Model):
    class Tipo(models.TextChoices):
        DIESEL_LITROS = "diesel_litros", "Diesel litros"
        GASOLINA_LITROS = "gasolina_litros", "Gasolina litros"
        ELECTRICIDAD_KWH = "electricidad_kwh", "Electricidad kWh"
        HORAS_MAQUINARIA = "horas_maquinaria", "Horas maquinaria"
        HORAS_ENCENDIDO = "horas_encendido", "Horas encendido"
        AGUA_LITROS = "agua_litros", "Agua litros"
        GPS_EVENTO = "gps_evento", "GPS evento"
        TEMPERATURA = "temperatura", "Temperatura"
        HUMEDAD = "humedad", "Humedad"

    UNIDADES_POR_TIPO = {
        Tipo.DIESEL_LITROS: "litros",
        Tipo.GASOLINA_LITROS: "litros",
        Tipo.ELECTRICIDAD_KWH: "kWh",
        Tipo.HORAS_MAQUINARIA: "horas",
        Tipo.HORAS_ENCENDIDO: "horas",
        Tipo.AGUA_LITROS: "litros",
        Tipo.GPS_EVENTO: "evento",
        Tipo.TEMPERATURA: "C",
        Tipo.HUMEDAD: "%",
    }

    FACTORES_CO2E = {
        Tipo.DIESEL_LITROS: Decimal("2.68"),
        Tipo.GASOLINA_LITROS: Decimal("2.31"),
        Tipo.ELECTRICIDAD_KWH: Decimal("0.39"),
        Tipo.HORAS_MAQUINARIA: Decimal("5.50"),
        Tipo.HORAS_ENCENDIDO: Decimal("5.50"),
        Tipo.AGUA_LITROS: Decimal("0"),
        Tipo.GPS_EVENTO: Decimal("0"),
        Tipo.TEMPERATURA: Decimal("0"),
        Tipo.HUMEDAD: Decimal("0"),
    }

    organizacion = models.CharField(max_length=180)
    etapa_obra = models.CharField(max_length=180)
    sensor = models.CharField(max_length=120)
    tipo = models.CharField(max_length=40, choices=Tipo.choices)
    valor = models.DecimalField(max_digits=12, decimal_places=3)
    unidad = models.CharField(max_length=40)
    co2e_estimado = models.DecimalField(max_digits=14, decimal_places=3)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_registro"]
        indexes = [
            models.Index(fields=["fecha_registro"]),
            models.Index(fields=["sensor", "fecha_registro"]),
            models.Index(fields=["organizacion", "fecha_registro"]),
            models.Index(fields=["tipo", "fecha_registro"]),
        ]

    def save(self, *args, **kwargs):
        self.unidad = self.UNIDADES_POR_TIPO.get(self.tipo, "")
        factor = self.FACTORES_CO2E.get(self.tipo, Decimal("0"))
        self.co2e_estimado = (self.valor or Decimal("0")) * factor
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sensor} - {self.tipo} - {self.valor} {self.unidad}"


class DispositivoSensor(models.Model):
    class Estado(models.TextChoices):
        OPERATIVO = "operativo", "Operativo"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        FUERA_SERVICIO = "fuera_servicio", "Fuera de servicio"
        CALIBRACION_VENCIDA = "calibracion_vencida", "Calibracion vencida"
    class TipoSensor(models.TextChoices):
        COMBUSTIBLE = "combustible", "Combustible"
        ENERGIA = "energia", "Energia"
        MAQUINARIA = "maquinaria", "Maquinaria"
        AGUA = "agua", "Agua"
        GPS = "gps", "GPS"
        AMBIENTE = "ambiente", "Ambiente"
        MIXTO = "mixto", "Mixto"

    dispositivo_id = models.CharField(max_length=120, unique=True)
    nombre = models.CharField(max_length=160)
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.PROTECT,
        related_name="dispositivos_iot",
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.SET_NULL,
        related_name="dispositivos_iot",
        null=True,
        blank=True,
    )
    etapa = models.ForeignKey(
        EtapaObra,
        on_delete=models.SET_NULL,
        related_name="dispositivos_iot",
        null=True,
        blank=True,
    )
    tipo_sensor = models.CharField(
        max_length=40,
        choices=TipoSensor.choices,
        default=TipoSensor.MIXTO,
    )
    ubicacion = models.CharField(max_length=180, blank=True)
    descripcion = models.TextField(blank=True)
    activo_operacional = models.ForeignKey(ActivoOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="sensores")
    unidad_operacional = models.ForeignKey(UnidadOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="sensores")
    proceso_operacional = models.ForeignKey(ProcesoOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="sensores")
    fuente_datos = models.ForeignKey(FuenteDatos, on_delete=models.SET_NULL, null=True, blank=True, related_name="sensores")
    fabricante = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.OPERATIVO, db_index=True)
    fecha_alta = models.DateField(null=True, blank=True)
    factor_emision_default = models.ForeignKey(
        FactorEmision,
        on_delete=models.SET_NULL,
        related_name="dispositivos_iot",
        null=True,
        blank=True,
    )
    api_key_hash = models.CharField(max_length=180, blank=True)
    activo = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organizacion__nombre", "nombre"]
        indexes = [
            models.Index(fields=["organizacion", "activo"]),
            models.Index(fields=["dispositivo_id"]),
            models.Index(fields=["tipo_sensor", "activo"]),
        ]

    def set_api_key(self, raw_key):
        if raw_key:
            self.api_key_hash = make_password(str(raw_key))

    def verify_api_key(self, raw_key):
        if not self.api_key_hash:
            return True
        if not raw_key:
            return False
        return check_password(str(raw_key), self.api_key_hash)

    def mark_seen(self):
        self.last_seen_at = timezone.now()
        self.save(update_fields=["last_seen_at", "updated_at"])

    def __str__(self):
        return f"{self.dispositivo_id} - {self.nombre}"

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        for field in ("activo_operacional", "unidad_operacional", "proceso_operacional", "fuente_datos"):
            relation = getattr(self, field, None)
            if relation and relation.organizacion_id != self.organizacion_id:
                errors[field] = "La relacion pertenece a otra organizacion."
        if errors:
            raise ValidationError(errors)


class InstalacionSensor(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        RETIRADA = "retirada", "Retirada"
        SUSPENDIDA = "suspendida", "Suspendida"

    sensor = models.ForeignKey(DispositivoSensor, on_delete=models.CASCADE, related_name="instalaciones")
    activo = models.ForeignKey(ActivoOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="instalaciones_sensor")
    unidad_operacional = models.ForeignKey(UnidadOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="instalaciones_sensor")
    proceso_operacional = models.ForeignKey(ProcesoOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="instalaciones_sensor")
    fecha_instalacion = models.DateField()
    fecha_retiro = models.DateField(null=True, blank=True)
    ubicacion = models.CharField(max_length=240, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVA)
    responsable = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_instalacion", "-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        for field in ("activo", "unidad_operacional", "proceso_operacional"):
            relation = getattr(self, field, None)
            if relation and relation.organizacion_id != self.sensor.organizacion_id:
                errors[field] = "La relacion pertenece a otra organizacion."
        if errors:
            raise ValidationError(errors)


class CalibracionSensor(models.Model):
    class Resultado(models.TextChoices):
        APROBADA = "aprobada", "Aprobada"
        APROBADA_OBSERVACIONES = "aprobada_con_observaciones", "Aprobada con observaciones"
        RECHAZADA = "rechazada", "Rechazada"

    sensor = models.ForeignKey(DispositivoSensor, on_delete=models.CASCADE, related_name="calibraciones")
    fecha = models.DateField()
    tipo = models.CharField(max_length=100)
    resultado = models.CharField(max_length=35, choices=Resultado.choices)
    fecha_proxima_calibracion = models.DateField(null=True, blank=True, db_index=True)
    responsable = models.CharField(max_length=180, blank=True)
    evidencia = models.ForeignKey(EvidenciaObra, on_delete=models.SET_NULL, null=True, blank=True, related_name="calibraciones_sensor")
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.evidencia_id and self.evidencia.organizacion_id != self.sensor.organizacion_id:
            raise ValidationError({"evidencia": "La evidencia pertenece a otra organizacion."})


class LecturaSensorV2(models.Model):
    class CalidadTecnica(models.TextChoices):
        VALIDA = "valida", "Valida"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"

    sensor = models.ForeignKey(DispositivoSensor, on_delete=models.PROTECT, related_name="lecturas_v2")
    actividad = models.ForeignKey(ActividadOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="lecturas_sensor")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    concepto = models.SlugField(max_length=120, db_index=True)
    valor_numerico = models.DecimalField(max_digits=20, decimal_places=6)
    unidad = models.CharField(max_length=40)
    metadata_tecnica = models.JSONField(default=dict, blank=True)
    calidad_tecnica = models.CharField(max_length=30, choices=CalidadTecnica.choices, default=CalidadTecnica.VALIDA)
    observacion = models.OneToOneField(Observacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="lectura_sensor_v2")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.actividad_id and self.actividad.organizacion_id != self.sensor.organizacion_id:
            raise ValidationError({"actividad": "La actividad pertenece a otra organizacion."})


class RegistroSensor(models.Model):
    class EstadoProcesamiento(models.TextChoices):
        RECIBIDO = "recibido", "Recibido"
        CONSOLIDADO = "consolidado", "Consolidado como emision"
        SOLO_TELEMETRIA = "solo_telemetria", "Solo telemetria"
        ERROR = "error", "Error"

    external_id = models.CharField(max_length=120, blank=True)
    dispositivo = models.ForeignKey(
        DispositivoSensor,
        on_delete=models.PROTECT,
        related_name="registros",
    )
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.PROTECT,
        related_name="registros_iot",
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.SET_NULL,
        related_name="registros_iot",
        null=True,
        blank=True,
    )
    etapa = models.ForeignKey(
        EtapaObra,
        on_delete=models.SET_NULL,
        related_name="registros_iot",
        null=True,
        blank=True,
    )
    tipo = models.CharField(max_length=40, choices=LecturaSensor.Tipo.choices)
    valor = models.DecimalField(max_digits=14, decimal_places=3)
    unidad = models.CharField(max_length=40, blank=True)
    factor_catalogo = models.ForeignKey(
        FactorEmision,
        on_delete=models.SET_NULL,
        related_name="registros_iot",
        null=True,
        blank=True,
    )
    factor_emision_usado = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal("0"),
    )
    co2e_estimado = models.DecimalField(max_digits=14, decimal_places=3, editable=False)
    timestamp_sensor = models.DateTimeField(default=timezone.now, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    estado_procesamiento = models.CharField(
        max_length=30,
        choices=EstadoProcesamiento.choices,
        default=EstadoProcesamiento.RECIBIDO,
        db_index=True,
    )
    registro_emision = models.ForeignKey(
        RegistroEmision,
        on_delete=models.SET_NULL,
        related_name="registros_iot_origen",
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    error_procesamiento = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp_sensor", "-received_at"]
        indexes = [
            models.Index(fields=["organizacion", "timestamp_sensor"]),
            models.Index(fields=["dispositivo", "timestamp_sensor"]),
            models.Index(fields=["tipo", "timestamp_sensor"]),
            models.Index(fields=["estado_procesamiento"]),
            models.Index(fields=["external_id"]),
        ]

    def save(self, *args, **kwargs):
        if self.dispositivo_id:
            if not self.organizacion_id:
                self.organizacion = self.dispositivo.organizacion
            if not self.obra_id:
                self.obra = self.dispositivo.obra
            if not self.etapa_id:
                self.etapa = self.dispositivo.etapa
            if not self.factor_catalogo_id and self.dispositivo.factor_emision_default_id:
                self.factor_catalogo = self.dispositivo.factor_emision_default

        if not self.unidad:
            self.unidad = LecturaSensor.UNIDADES_POR_TIPO.get(self.tipo, "")
        if self.factor_catalogo_id:
            self.factor_emision_usado = self.factor_catalogo.factor_emision
        elif not self.factor_emision_usado:
            self.factor_emision_usado = LecturaSensor.FACTORES_CO2E.get(self.tipo, Decimal("0"))

        self.co2e_estimado = (self.valor or Decimal("0")) * (self.factor_emision_usado or Decimal("0"))
        super().save(*args, **kwargs)

    @property
    def es_emision_consolidable(self):
        return self.factor_emision_usado > 0 and self.tipo not in {
            LecturaSensor.Tipo.TEMPERATURA,
            LecturaSensor.Tipo.HUMEDAD,
            LecturaSensor.Tipo.GPS_EVENTO,
        }

    def __str__(self):
        return f"{self.dispositivo.dispositivo_id} - {self.tipo} - {self.valor} {self.unidad}"
