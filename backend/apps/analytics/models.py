from decimal import Decimal

from django.db import models
from django.db.models import Sum

from .factores import format_activity_display_name, normalize_activity_key, normalize_factor_category


def documento_lote_upload_path(instance, filename):
    return f"lotes/{instance.lote.id_lote}/documentos/{filename}"


class EspecieMadera(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    densidad_kg_m3 = models.DecimalField(max_digits=8, decimal_places=3)
    porcentaje_carbono = models.DecimalField(max_digits=5, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Empresa(models.Model):
    empresa_id = models.CharField(max_length=80, unique=True)
    nombre = models.CharField(max_length=180)
    rut = models.CharField(max_length=30, blank=True)
    region = models.CharField(max_length=120, blank=True)
    comuna = models.CharField(max_length=120, blank=True)
    direccion = models.CharField(max_length=240, blank=True)
    rubro = models.CharField(max_length=120, blank=True)
    activa = models.BooleanField(default=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    contacto = models.CharField(max_length=160, blank=True)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class UnidadOperativa(models.Model):
    class Tipo(models.TextChoices):
        GENERAL = "General", "General"
        PLANTA = "Planta", "Planta"
        ASERRADERO = "Aserradero", "Aserradero"
        SECADO = "Secado", "Secado"
        PRODUCTOS_TERMINADOS = "Productos terminados", "Productos terminados"
        BODEGA = "Bodega", "Bodega"
        DESPACHO = "Despacho", "Despacho"
        MANTENCION = "Mantencion", "Mantencion"
        ADMINISTRACION = "Administracion", "Administracion"
        OTRO = "Otro", "Otro"

    unidad_id = models.CharField(max_length=80, unique=True)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="unidades_operativas",
    )
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(max_length=40, choices=Tipo.choices, default=Tipo.OTRO)
    region = models.CharField(max_length=120, blank=True)
    comuna = models.CharField(max_length=120, blank=True)
    direccion = models.CharField(max_length=240, blank=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["empresa__nombre", "nombre"]

    def __str__(self):
        return f"{self.empresa.nombre} - {self.nombre}"


def normalize_identifier(value):
    key = normalize_activity_key(value)
    return key.upper() if key else ""


def get_or_create_default_company_and_unit(nombre_empresa):
    nombre = str(nombre_empresa or "Empresa sin nombre").strip() or "Empresa sin nombre"
    empresa_id = normalize_identifier(nombre) or "EMPRESA_GENERAL"
    empresa, _ = Empresa.objects.get_or_create(
        empresa_id=empresa_id,
        defaults={"nombre": nombre, "rubro": "Madera"},
    )
    unidad, _ = UnidadOperativa.objects.get_or_create(
        unidad_id=f"{empresa.empresa_id}_GENERAL",
        defaults={
            "empresa": empresa,
            "nombre": "Unidad General",
            "tipo": UnidadOperativa.Tipo.GENERAL,
        },
    )
    return empresa, unidad


class Lote(models.Model):
    id_lote = models.CharField(max_length=80, unique=True)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="lotes",
        null=True,
        blank=True,
    )
    unidad_operativa = models.ForeignKey(
        UnidadOperativa,
        on_delete=models.PROTECT,
        related_name="lotes",
        null=True,
        blank=True,
    )
    empresa_aserradero = models.CharField(max_length=160)
    fecha = models.DateField()
    especie = models.CharField(max_length=120)
    volumen_m3 = models.DecimalField(max_digits=12, decimal_places=3)
    origen = models.CharField(max_length=180)
    destino = models.CharField(max_length=180, blank=True, default="")
    tipo_producto = models.CharField(max_length=120, blank=True)
    densidad_kg_m3 = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
    )
    porcentaje_carbono = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )
    estado = models.CharField(max_length=60, blank=True)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-created_at"]

    def __str__(self):
        return f"{self.id_lote} - {self.empresa_aserradero}"

    def save(self, *args, **kwargs):
        if not self.empresa_id and self.empresa_aserradero:
            self.empresa, self.unidad_operativa = get_or_create_default_company_and_unit(
                self.empresa_aserradero
            )
        elif self.unidad_operativa_id and not self.empresa_id:
            self.empresa = self.unidad_operativa.empresa
        super().save(*args, **kwargs)

    @property
    def emisiones_kg_co2e(self):
        total = self.actividades.aggregate(total=Sum("emisiones_kg_co2e"))["total"]
        return total or 0


class EmisionLote(models.Model):
    class TipoAsignacion(models.TextChoices):
        LOTE = "lote", "Lote"
        UNIDAD = "unidad", "Unidad operativa"
        EMPRESA = "empresa", "Empresa"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="actividades_emision",
        null=True,
        blank=True,
    )
    unidad_operativa = models.ForeignKey(
        UnidadOperativa,
        on_delete=models.PROTECT,
        related_name="actividades_emision",
        null=True,
        blank=True,
    )
    lote = models.ForeignKey(
        Lote,
        on_delete=models.CASCADE,
        related_name="actividades",
        null=True,
        blank=True,
    )
    actividad = models.CharField(max_length=120)
    actividad_key = models.CharField(max_length=160, blank=True)
    categoria = models.CharField(max_length=40, blank=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    unidad = models.CharField(max_length=40)
    fecha = models.DateField(null=True, blank=True)
    factor_emision = models.DecimalField(max_digits=12, decimal_places=6)
    emisiones_kg_co2e = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        editable=False,
    )
    tipo_asignacion = models.CharField(
        max_length=20,
        choices=TipoAsignacion.choices,
        default=TipoAsignacion.LOTE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "lote",
                    "actividad",
                    "unidad",
                    "fecha",
                    "cantidad",
                    "factor_emision",
                ],
                name="unique_emision_lote_importada",
            )
        ]

    def save(self, *args, **kwargs):
        self.actividad = format_activity_display_name(self.actividad)
        if self.lote_id:
            self.empresa = self.lote.empresa
            self.unidad_operativa = self.lote.unidad_operativa
            self.tipo_asignacion = self.TipoAsignacion.LOTE
        elif self.unidad_operativa_id:
            self.empresa = self.unidad_operativa.empresa
            self.tipo_asignacion = self.TipoAsignacion.UNIDAD
        elif self.empresa_id:
            self.tipo_asignacion = self.TipoAsignacion.EMPRESA
        if not self.actividad_key:
            self.actividad_key = normalize_activity_key(self.actividad)
        self.categoria = normalize_factor_category(
            self.categoria,
            self.actividad,
            self.unidad,
        )
        self.emisiones_kg_co2e = self.cantidad * self.factor_emision
        super().save(*args, **kwargs)

    def __str__(self):
        owner = self.lote.id_lote if self.lote_id else self.empresa or "Sin asignacion"
        return f"{owner} - {self.actividad}"


class FactorEmision(models.Model):
    class Categoria(models.TextChoices):
        COMBUSTIBLE = "Combustible", "Combustible"
        ELECTRICIDAD = "Electricidad", "Electricidad"
        TRANSPORTE = "Transporte", "Transporte"
        AGUA = "Agua", "Agua"
        MATERIALES = "Materiales", "Materiales"
        RESIDUOS = "Residuos", "Residuos"
        REFRIGERANTES = "Refrigerantes", "Refrigerantes"
        OTROS = "Otros", "Otros"

    categoria = models.CharField(
        max_length=40,
        choices=Categoria.choices,
        default=Categoria.OTROS,
    )
    actividad = models.CharField(max_length=120)
    actividad_key = models.CharField(max_length=160, blank=True)
    descripcion = models.TextField(blank=True)
    metadata_clasificacion = models.JSONField(default=dict, blank=True)
    unidad = models.CharField(max_length=40)
    factor_emision = models.DecimalField(max_digits=12, decimal_places=6)
    fuente = models.CharField(max_length=180)
    anio = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria", "actividad", "unidad", "-anio"]
        constraints = [
            models.UniqueConstraint(
                fields=["actividad", "unidad", "fuente", "anio"],
                name="unique_factor_emision_fuente_anio",
            ),
            models.UniqueConstraint(
                fields=["actividad_key", "unidad", "fuente", "anio"],
                name="unique_factor_emision_key_fuente_anio",
            ),
        ]

    def save(self, *args, **kwargs):
        self.actividad = format_activity_display_name(self.actividad)
        self.actividad_key = self.actividad_key or normalize_activity_key(self.actividad)
        self.actividad_key = normalize_activity_key(self.actividad_key)
        categoria_archivo = (self.metadata_clasificacion or {}).get("categoria_archivo")
        categoria_invalida = (self.metadata_clasificacion or {}).get("categoria_invalida")
        if (
            self.categoria == self.Categoria.OTROS
            and categoria_archivo != self.Categoria.OTROS
            and not categoria_invalida
        ):
            self.categoria = normalize_factor_category(
                "",
                self.actividad,
                self.unidad,
                self.fuente,
            )
        else:
            self.categoria = normalize_factor_category(
                self.categoria,
                self.actividad,
                self.unidad,
                self.fuente,
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.actividad} - {self.unidad} ({self.anio})"


class DocumentoLote(models.Model):
    class TipoDocumento(models.TextChoices):
        GUIA_DESPACHO = "guia_despacho", "Guia de despacho"
        FACTURA_COMBUSTIBLE = "factura_combustible", "Factura de combustible"
        BOLETA_ELECTRICA = "boleta_electrica", "Boleta electrica"
        REGISTRO_PRODUCCION = "registro_produccion", "Registro de produccion"
        DOCUMENTO_ORIGEN = "documento_origen", "Documento de origen"
        REGISTRO_TRANSPORTE = "registro_transporte", "Registro de transporte"

    class EstadoValidacion(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        VALIDADO = "validado", "Validado"
        RECHAZADO = "rechazado", "Rechazado"

    lote = models.ForeignKey(
        Lote,
        on_delete=models.CASCADE,
        related_name="documentos",
    )
    tipo_documento = models.CharField(
        max_length=40,
        choices=TipoDocumento.choices,
    )
    archivo = models.FileField(upload_to=documento_lote_upload_path)
    fecha = models.DateField()
    estado_validacion = models.CharField(
        max_length=20,
        choices=EstadoValidacion.choices,
        default=EstadoValidacion.PENDIENTE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-created_at"]

    def __str__(self):
        return f"{self.lote.id_lote} - {self.get_tipo_documento_display()}"


class TransporteLote(models.Model):
    lote = models.ForeignKey(
        Lote,
        on_delete=models.CASCADE,
        related_name="transportes",
    )
    vehiculo = models.CharField(max_length=120)
    patente = models.CharField(max_length=30)
    latitud = models.DecimalField(max_digits=10, decimal_places=7)
    longitud = models.DecimalField(max_digits=10, decimal_places=7)
    fecha_hora = models.DateTimeField()
    ruta = models.CharField(max_length=240)
    distancia_km = models.DecimalField(max_digits=12, decimal_places=3)
    consumo_estimado_litro_km = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.3000"),
    )
    litros_combustible = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    factor_diesel = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal("2.680000"),
    )
    litros_calculados = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        editable=False,
    )
    emisiones_transporte_kg_co2e = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        editable=False,
    )
    actividad_emision = models.OneToOneField(
        EmisionLote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transporte",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_hora", "-created_at"]

    def save(self, *args, **kwargs):
        self.litros_calculados = (
            self.litros_combustible
            if self.litros_combustible is not None
            else self.distancia_km * self.consumo_estimado_litro_km
        )
        self.emisiones_transporte_kg_co2e = self.litros_calculados * self.factor_diesel
        super().save(*args, **kwargs)
        self.sync_emision_lote()

    def sync_emision_lote(self):
        if self.actividad_emision_id:
            actividad = self.actividad_emision
            actividad.cantidad = self.litros_calculados
            actividad.factor_emision = self.factor_diesel
            actividad.unidad = "litros diesel"
            actividad.actividad = "transporte"
            actividad.save()
            return

        actividad = EmisionLote.objects.create(
            lote=self.lote,
            actividad="transporte",
            cantidad=self.litros_calculados,
            unidad="litros diesel",
            factor_emision=self.factor_diesel,
        )
        TransporteLote.objects.filter(pk=self.pk).update(actividad_emision=actividad)
        self.actividad_emision = actividad

    def __str__(self):
        return f"{self.lote.id_lote} - {self.patente} - {self.ruta}"


class ExtraccionDocumento(models.Model):
    class EstadoRevision(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        VALIDADO = "validado", "Validado"
        RECHAZADO = "rechazado", "Rechazado"

    documento = models.ForeignKey(
        DocumentoLote,
        on_delete=models.CASCADE,
        related_name="extracciones",
    )
    texto_extraido = models.TextField(blank=True)
    datos_sugeridos = models.JSONField(default=dict)
    datos_validados = models.JSONField(default=dict, blank=True)
    estado_revision = models.CharField(
        max_length=20,
        choices=EstadoRevision.choices,
        default=EstadoRevision.PENDIENTE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.documento} - {self.get_estado_revision_display()}"


class HistorialCambioLote(models.Model):
    class TipoCambio(models.TextChoices):
        EXTRAIDO = "extraido", "Dato extraído"
        IMPORTADO = "importado", "Dato importado"
        VALIDADO = "validado", "Dato validado"
        RECHAZADO = "rechazado", "Dato rechazado"
        CORREGIDO = "corregido", "Dato corregido"

    lote = models.ForeignKey(
        Lote,
        on_delete=models.CASCADE,
        related_name="historial_cambios",
    )
    tipo = models.CharField(max_length=20, choices=TipoCambio.choices)
    fuente = models.CharField(max_length=80, blank=True)  # p.ej. 'ia', 'heuristica', 'usuario'
    usuario = models.CharField(max_length=120, blank=True, null=True)
    documento = models.ForeignKey(
        DocumentoLote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historial_entries",
    )
    extraccion = models.ForeignKey(
        ExtraccionDocumento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historial_entries",
    )
    raw_payload = models.JSONField(default=dict, blank=True)
    normalized_payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.lote.id_lote} - {self.get_tipo_display()} - {self.created_at.isoformat()}"
