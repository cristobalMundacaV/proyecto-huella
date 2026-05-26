from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from django.utils.dateparse import parse_datetime


def normalize_key(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
        .replace("/", " ")
        .replace("-", " ")
    )


def unique_code(model, field, base, pk=None, limit=80):
    root = (normalize_key(base).upper().replace(" ", "_") or model.__name__.upper())[:limit]
    candidate = root
    suffix = 2
    while model.objects.filter(**{field: candidate}).exclude(pk=pk).exists():
        candidate = f"{root[: limit - len(str(suffix)) - 1]}_{suffix}"
        suffix += 1
    return candidate


def evidencia_obra_upload_path(instance, filename):
    constructora = instance.constructora.constructora_id if instance.constructora_id else "SIN_CONSTRUCTORA"
    obra = instance.obra.codigo_obra if instance.obra_id else "GENERAL"
    return f"evidencias/{constructora}/{obra}/{filename}"


def evidencia_formatos_default():
    return ["PDF", "JPG", "PNG", "XLSX", "CSV", "DOCX"]


class Constructora(models.Model):
    constructora_id = models.CharField(max_length=80, unique=True, blank=True)
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

    def save(self, *args, **kwargs):
        if not self.constructora_id:
            self.constructora_id = unique_code(Constructora, "constructora_id", self.nombre, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class UsuarioConstructora(models.Model):
    class Rol(models.TextChoices):
        ADMIN = "admin", "Administrador"
        ANALISTA = "analista", "Analista"
        OPERADOR = "operador", "Operador"
        LECTOR = "lector", "Lector"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="constructoras_perfil")
    constructora = models.ForeignKey(Constructora, on_delete=models.CASCADE, related_name="usuarios")
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.ANALISTA)
    cargo = models.CharField(max_length=120, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["constructora__nombre", "user__first_name", "user__username"]
        constraints = [
            models.UniqueConstraint(fields=["user", "constructora"], name="unique_usuario_constructora")
        ]

    def __str__(self):
        return f"{self.user.username} - {self.constructora.nombre}"


class ConfiguracionConstructora(models.Model):
    class ModoImportacion(models.TextChoices):
        FLEXIBLE = "flexible", "Flexible"
        ESTRICTO = "estricto", "Estricto"

    class AgrupacionReporte(models.TextChoices):
        DIA = "dia", "Dia"
        SEMANA = "semana", "Semana"
        MES = "mes", "Mes"
        TRIMESTRE = "trimestre", "Trimestre"
        ANIO = "anio", "Anio"

    class PeriodoReporte(models.TextChoices):
        ULTIMOS_30_DIAS = "ultimos_30_dias", "Ultimos 30 dias"
        ULTIMOS_3_MESES = "ultimos_3_meses", "Ultimos 3 meses"
        ULTIMOS_6_MESES = "ultimos_6_meses", "Ultimos 6 meses"
        ULTIMOS_12_MESES = "ultimos_12_meses", "Ultimos 12 meses"
        ANIO_ACTUAL = "anio_actual", "Anio actual"

    constructora = models.OneToOneField(Constructora, on_delete=models.CASCADE, related_name="configuracion")
    unidad_emisiones = models.CharField(max_length=20, default="kg CO2e")
    factor_electrico_default = models.CharField(max_length=160, blank=True, default="Factor electrico vigente")
    region_electrica_default = models.CharField(max_length=120, blank=True, default="Biobio")
    redondeo_decimales = models.PositiveSmallIntegerField(default=1)
    modo_importacion = models.CharField(max_length=20, choices=ModoImportacion.choices, default=ModoImportacion.FLEXIBLE)
    crear_etapas_automaticamente = models.BooleanField(default=True)
    crear_obras_automaticamente = models.BooleanField(default=True)
    permitir_registros_sin_factor = models.BooleanField(default=False)
    actualizar_registros_existentes = models.BooleanField(default=True)
    bloquear_duplicados = models.BooleanField(default=True)
    requerir_etapa_obra = models.BooleanField(default=False)
    requerir_obra_registro = models.BooleanField(default=True)
    permitir_evidencias_sin_vinculo = models.BooleanField(default=True)
    ficha_ambiental_activa = models.BooleanField(default=True)
    evidencia_obligatoria = models.BooleanField(default=False)
    formatos_evidencia_permitidos = models.JSONField(default=evidencia_formatos_default)
    max_file_size_mb = models.PositiveSmallIntegerField(default=10)
    reporte_agrupacion_default = models.CharField(max_length=20, choices=AgrupacionReporte.choices, default=AgrupacionReporte.MES)
    reporte_periodo_default = models.CharField(max_length=30, choices=PeriodoReporte.choices, default=PeriodoReporte.ULTIMOS_12_MESES)
    reporte_mostrar_categoria = models.BooleanField(default=True)
    reporte_mostrar_etapa = models.BooleanField(default=True)
    reporte_mostrar_tabla = models.BooleanField(default=True)
    reporte_unidad_visual_emisiones = models.CharField(max_length=20, default="kg CO2e")
    reporte_lectura_ejecutiva = models.BooleanField(default=True)
    reporte_equivalencias = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuracion - {self.constructora.constructora_id}"


class EtapaObra(models.Model):
    class Tipo(models.TextChoices):
        EXCAVACION = "Excavacion", "Excavacion"
        FUNDACIONES = "Fundaciones", "Fundaciones"
        OBRA_GRUESA = "Obra gruesa", "Obra gruesa"
        ESTRUCTURA = "Estructura", "Estructura"
        INSTALACIONES = "Instalaciones", "Instalaciones"
        TERMINACIONES = "Terminaciones", "Terminaciones"
        URBANIZACION = "Urbanizacion", "Urbanizacion"
        RETIRO_RESIDUOS = "Retiro de residuos", "Retiro de residuos"
        LOGISTICA = "Logistica", "Logistica"
        ADMINISTRACION = "Administracion de obra", "Administracion de obra"
        OTRO = "Otro", "Otro"

    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        INACTIVA = "inactiva", "Inactiva"
        SUSPENDIDA = "suspendida", "Suspendida"
        FINALIZADA = "finalizada", "Finalizada"

    etapa_id = models.CharField(max_length=80, unique=True, blank=True)
    constructora = models.ForeignKey(Constructora, on_delete=models.CASCADE, related_name="etapas")
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(max_length=40, choices=Tipo.choices, default=Tipo.OTRO)
    region = models.CharField(max_length=120, blank=True)
    comuna = models.CharField(max_length=120, blank=True)
    direccion = models.CharField(max_length=240, blank=True)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVA)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["constructora__nombre", "nombre"]

    def save(self, *args, **kwargs):
        if not self.etapa_id:
            self.etapa_id = unique_code(EtapaObra, "etapa_id", f"{self.constructora.constructora_id}_{self.nombre}", self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.constructora.nombre} - {self.nombre}"


class Obra(models.Model):
    class TipoProyecto(models.TextChoices):
        VIVIENDA = "Vivienda", "Vivienda"
        EDIFICIO = "Edificio habitacional", "Edificio habitacional"
        INFRAESTRUCTURA = "Infraestructura", "Infraestructura"
        INDUSTRIAL = "Industrial", "Industrial"
        COMERCIAL = "Comercial", "Comercial"
        OBRA_PUBLICA = "Obra publica", "Obra publica"
        URBANIZACION = "Urbanizacion", "Urbanizacion"
        OTRO = "Otro", "Otro"

    class Estado(models.TextChoices):
        PLANIFICADA = "planificada", "Planificada"
        EN_EJECUCION = "en_ejecucion", "En ejecucion"
        PAUSADA = "pausada", "Pausada"
        FINALIZADA = "finalizada", "Finalizada"

    codigo_obra = models.CharField(max_length=80, unique=True, blank=True)
    constructora = models.ForeignKey(Constructora, on_delete=models.PROTECT, related_name="obras")
    etapa_principal = models.ForeignKey(EtapaObra, on_delete=models.PROTECT, related_name="obras", null=True, blank=True)
    nombre = models.CharField(max_length=180)
    tipo_proyecto = models.CharField(max_length=40, choices=TipoProyecto.choices, default=TipoProyecto.OTRO)
    fecha_inicio = models.DateField()
    fecha_termino_estimada = models.DateField(null=True, blank=True)
    superficie_m2 = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    ubicacion = models.CharField(max_length=240, blank=True)
    region = models.CharField(max_length=120, blank=True)
    comuna = models.CharField(max_length=120, blank=True)
    mandante = models.CharField(max_length=180, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.EN_EJECUCION)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_inicio", "nombre"]

    @property
    def emisiones_kg_co2e(self):
        return self.registros_emision.aggregate(total=Sum("emisiones_kg_co2e"))["total"] or Decimal("0")

    def save(self, *args, **kwargs):
        if not self.codigo_obra:
            self.codigo_obra = unique_code(Obra, "codigo_obra", self.nombre, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_obra} - {self.nombre}"


class FactorEmision(models.Model):
    class Categoria(models.TextChoices):
        MATERIALES = "Materiales", "Materiales"
        TRANSPORTE = "Transporte", "Transporte"
        MAQUINARIA = "Maquinaria", "Maquinaria"
        ENERGIA = "Energia", "Energia"
        AGUA = "Agua", "Agua"
        RESIDUOS = "Residuos", "Residuos"
        PROCESOS_EXTERNOS = "Procesos externos", "Procesos externos"
        OTROS = "Otros", "Otros"

    actividad = models.CharField(max_length=120)
    categoria = models.CharField(max_length=40, choices=Categoria.choices, default=Categoria.OTROS)
    unidad = models.CharField(max_length=40)
    factor_emision = models.DecimalField(max_digits=12, decimal_places=6)
    fuente = models.CharField(max_length=180)
    anio = models.PositiveIntegerField()
    alcance = models.CharField(max_length=80, blank=True)
    descripcion = models.TextField(blank=True)
    actividad_key = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria", "actividad", "unidad", "-anio"]
        constraints = [
            models.UniqueConstraint(fields=["actividad", "unidad", "fuente", "anio"], name="unique_factor_construccion")
        ]

    def save(self, *args, **kwargs):
        if not self.actividad_key:
            self.actividad_key = normalize_key(self.actividad).replace(" ", "_")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.actividad} - {self.unidad} ({self.anio})"


class MaterialConstruccion(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    categoria = models.CharField(max_length=80, blank=True)
    unidad_default = models.CharField(max_length=40, blank=True)
    factor_emision_default = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    fuente = models.CharField(max_length=180, blank=True)
    anio = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class RegistroEmision(models.Model):
    class Categoria(models.TextChoices):
        MATERIALES = "Materiales", "Materiales"
        TRANSPORTE = "Transporte", "Transporte"
        MAQUINARIA = "Maquinaria", "Maquinaria"
        ENERGIA = "Energia", "Energia"
        AGUA = "Agua", "Agua"
        RESIDUOS = "Residuos", "Residuos"
        PROCESOS_EXTERNOS = "Procesos externos", "Procesos externos"
        OTROS = "Otros", "Otros"

    constructora = models.ForeignKey(Constructora, on_delete=models.PROTECT, related_name="registros_emision", null=True, blank=True)
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="registros_emision", null=True, blank=True)
    etapa = models.ForeignKey(EtapaObra, on_delete=models.PROTECT, related_name="registros_emision", null=True, blank=True)
    categoria = models.CharField(max_length=40, choices=Categoria.choices, default=Categoria.OTROS)
    fuente_emision = models.CharField(max_length=120)
    actividad_key = models.CharField(max_length=160, blank=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    unidad = models.CharField(max_length=40)
    factor_emision = models.DecimalField(max_digits=12, decimal_places=6)
    emisiones_kg_co2e = models.DecimalField(max_digits=14, decimal_places=3, editable=False)
    fecha = models.DateField(null=True, blank=True)
    proveedor = models.CharField(max_length=180, blank=True)
    origen_transporte = models.CharField(max_length=240, blank=True)
    destino_transporte = models.CharField(max_length=240, blank=True)
    distancia_km = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    ruta_geometry = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-created_at"]
        indexes = [
            models.Index(fields=["constructora_id", "fecha"]),
            models.Index(fields=["constructora_id", "categoria"]),
            models.Index(fields=["constructora_id", "actividad_key"]),
            models.Index(fields=["obra_id", "categoria"]),
            models.Index(fields=["etapa_id", "categoria"]),
        ]

    def save(self, *args, **kwargs):
        if self.obra_id:
            self.constructora = self.obra.constructora
            if not self.etapa_id:
                self.etapa = self.obra.etapa_principal
        elif self.etapa_id and not self.constructora_id:
            self.constructora = self.etapa.constructora
        if not self.actividad_key:
            self.actividad_key = normalize_key(self.fuente_emision).replace(" ", "_")
        self.emisiones_kg_co2e = (self.cantidad or Decimal("0")) * (self.factor_emision or Decimal("0"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.obra or self.constructora} - {self.fuente_emision}"


class EvidenciaObra(models.Model):
    class TipoEvidencia(models.TextChoices):
        FACTURA_MATERIAL = "factura_material", "Factura de material"
        GUIA_DESPACHO = "guia_despacho", "Guia de despacho"
        ORDEN_COMPRA = "orden_compra", "Orden de compra"
        FACTURA_COMBUSTIBLE = "factura_combustible", "Factura de combustible"
        BOLETA_ELECTRICA = "boleta_electrica", "Boleta electrica"
        TICKET_PESAJE = "ticket_pesaje", "Ticket de pesaje"
        FICHA_TECNICA = "ficha_tecnica_material", "Ficha tecnica de material"
        CERTIFICADO_PROVEEDOR = "certificado_proveedor", "Certificado de proveedor"
        REGISTRO_MAQUINARIA = "registro_maquinaria", "Registro de maquinaria"
        REGISTRO_RESIDUOS = "registro_retiro_residuos", "Registro de retiro de residuos"
        DOCUMENTO_TRANSPORTE = "documento_transporte", "Documento de transporte"
        OTRO = "otro", "Otro"

    class EstadoDocumental(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        VALIDADA = "validada", "Validada"
        OBSERVADA = "observada", "Observada"
        RECHAZADA = "rechazada", "Rechazada"
        SIN_VINCULO = "sin_vinculo", "Sin vinculo"
        VINCULADA = "vinculada", "Vinculada"

    constructora = models.ForeignKey(Constructora, on_delete=models.CASCADE, related_name="evidencias")
    obra = models.ForeignKey(Obra, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidencias")
    etapa = models.ForeignKey(EtapaObra, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidencias")
    registro_emision = models.ForeignKey(RegistroEmision, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidencias")
    tipo_evidencia = models.CharField(max_length=40, choices=TipoEvidencia.choices, default=TipoEvidencia.OTRO)
    estado_documental = models.CharField(max_length=20, choices=EstadoDocumental.choices, default=EstadoDocumental.PENDIENTE)
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
            models.Index(fields=["constructora_id", "estado_documental"]),
            models.Index(fields=["constructora_id", "tipo_evidencia"]),
            models.Index(fields=["obra_id", "estado_documental"]),
            models.Index(fields=["registro_emision_id"]),
        ]

    def save(self, *args, **kwargs):
        if self.obra_id and not self.constructora_id:
            self.constructora = self.obra.constructora
        if self.registro_emision_id and self.estado_documental in {"sin_vinculo", ""}:
            self.estado_documental = self.EstadoDocumental.VINCULADA
        elif not self.obra_id and self.estado_documental == self.EstadoDocumental.PENDIENTE:
            self.estado_documental = self.EstadoDocumental.SIN_VINCULO
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.constructora.constructora_id} - {self.nombre}"


class TransporteObra(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="transportes")
    etapa = models.ForeignKey(EtapaObra, on_delete=models.SET_NULL, null=True, blank=True, related_name="transportes")
    vehiculo = models.CharField(max_length=120)
    patente = models.CharField(max_length=30)
    origen = models.CharField(max_length=240)
    destino = models.CharField(max_length=240)
    origen_coords = models.JSONField(null=True, blank=True)
    destino_coords = models.JSONField(null=True, blank=True)
    distancia_km = models.DecimalField(max_digits=12, decimal_places=3)
    consumo_estimado_litro_km = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.3000"))
    litros_combustible = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    emisiones_kg_co2e = models.DecimalField(max_digits=14, decimal_places=3, editable=False)
    fecha_hora = models.DateTimeField()
    registro_emision = models.OneToOneField(RegistroEmision, on_delete=models.SET_NULL, null=True, blank=True, related_name="transporte")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_hora", "-created_at"]

    def save(self, *args, **kwargs):
        litros = self.litros_combustible
        if litros is None:
            litros = self.distancia_km * self.consumo_estimado_litro_km
        self.emisiones_kg_co2e = litros * Decimal("2.680000")
        super().save(*args, **kwargs)
        self.sync_registro_emision(litros)

    def sync_registro_emision(self, litros):
        fecha_hora = self.fecha_hora
        if isinstance(fecha_hora, str):
            fecha_hora = parse_datetime(fecha_hora)
        defaults = {
            "obra": self.obra,
            "etapa": self.etapa or self.obra.etapa_principal,
            "categoria": RegistroEmision.Categoria.TRANSPORTE,
            "fuente_emision": f"Transporte {self.vehiculo}",
            "cantidad": litros,
            "unidad": "litros diesel",
            "factor_emision": Decimal("2.680000"),
            "fecha": fecha_hora.date() if fecha_hora else None,
            "origen_transporte": self.origen,
            "destino_transporte": self.destino,
            "distancia_km": self.distancia_km,
            "metadata": {"patente": self.patente},
        }
        if self.registro_emision_id:
            for field, value in defaults.items():
                setattr(self.registro_emision, field, value)
            self.registro_emision.save()
            return
        registro = RegistroEmision.objects.create(**defaults)
        TransporteObra.objects.filter(pk=self.pk).update(registro_emision=registro)
        self.registro_emision = registro

    def __str__(self):
        return f"{self.obra.codigo_obra} - {self.patente}"


class HistorialCambioObra(models.Model):
    class TipoCambio(models.TextChoices):
        IMPORTADO = "importado", "Dato importado"
        VALIDADO = "validado", "Dato validado"
        RECHAZADO = "rechazado", "Dato rechazado"
        CORREGIDO = "corregido", "Dato corregido"

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="historial_cambios")
    tipo = models.CharField(max_length=20, choices=TipoCambio.choices)
    fuente = models.CharField(max_length=80, blank=True)
    usuario = models.CharField(max_length=120, blank=True, null=True)
    evidencia = models.ForeignKey(EvidenciaObra, on_delete=models.SET_NULL, null=True, blank=True, related_name="historial_entries")
    raw_payload = models.JSONField(default=dict, blank=True)
    normalized_payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.obra.codigo_obra} - {self.get_tipo_display()}"
