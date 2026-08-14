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
    organizacion = instance.organizacion.organizacion_id if instance.organizacion_id else "SIN_ORGANIZACION"
    obra = instance.obra.codigo_obra if instance.obra_id else "GENERAL"
    return f"evidencias/{organizacion}/{obra}/{filename}"


def version_evidencia_upload_path(instance, filename):
    organizacion = instance.organizacion.organizacion_id if instance.organizacion_id else "SIN_ORGANIZACION"
    return f"evidencias/{organizacion}/versiones/{filename}"


def documento_ambiental_upload_path(instance, filename):
    organizacion = instance.organizacion.organizacion_id if instance.organizacion_id else "SIN_ORGANIZACION"
    return f"documentos_ambientales/{organizacion}/{filename}"


def evidencia_formatos_default():
    return ["PDF", "JPG", "PNG", "XLSX", "CSV", "DOCX"]


class Organizacion(models.Model):
    class Preset(models.TextChoices):
        CONSTRUCCION = "construccion", "Construcción"
        FORESTAL = "forestal", "Forestal"
        ASERRADERO = "aserradero", "Aserradero"
        TRANSPORTE = "transporte", "Transporte"
        INDUSTRIAL = "industrial", "Industrial"

    organizacion_id = models.CharField(max_length=80, unique=True, blank=True)
    nombre = models.CharField(max_length=180)
    rut = models.CharField(max_length=30, blank=True)
    region = models.CharField(max_length=120, blank=True)
    comuna = models.CharField(max_length=120, blank=True)
    direccion = models.CharField(max_length=240, blank=True)
    rubro = models.CharField(max_length=120, blank=True)
    preset = models.CharField(max_length=40, choices=Preset.choices, default=Preset.CONSTRUCCION, db_index=True)
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
        if not self.organizacion_id:
            self.organizacion_id = unique_code(Organizacion, "organizacion_id", self.nombre, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class UsuarioOrganizacion(models.Model):
    class Rol(models.TextChoices):
        ADMIN = "admin", "Administrador"
        ANALISTA = "analista", "Analista"
        OPERADOR = "operador", "Operador"
        LECTOR = "lector", "Lector"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organizaciones_perfil")
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="usuarios")
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.ANALISTA)
    cargo = models.CharField(max_length=120, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organizacion__nombre", "user__first_name", "user__username"]
        constraints = [
            models.UniqueConstraint(fields=["user", "organizacion"], name="unique_usuario_organizacion")
        ]

    def __str__(self):
        return f"{self.user.username} - {self.organizacion.nombre}"


class DiagnosticoAmbientalInicial(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROGRESO = "en_progreso", "En progreso"
        COMPLETADO = "completado", "Completado"
        REQUIERE_ACTUALIZACION = "requiere_actualizacion", "Requiere actualizacion"

    organizacion = models.OneToOneField(Organizacion, on_delete=models.CASCADE, related_name="diagnostico_ambiental")
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_finalizacion = models.DateField(null=True, blank=True)
    objetivo_principal = models.TextField(blank=True)
    descripcion_contexto = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="diagnosticos_ambientales")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ElementoDiagnosticoAmbiental(models.Model):
    class Tipo(models.TextChoices):
        PROCESO = "proceso", "Proceso identificado"
        INFORMACION_DISPONIBLE = "informacion_disponible", "Informacion disponible"
        INFORMACION_FALTANTE = "informacion_faltante", "Informacion faltante"
        FUENTE = "fuente", "Fuente conocida"
        BRECHA = "brecha", "Brecha ambiental"

    diagnostico = models.ForeignKey(DiagnosticoAmbientalInicial, on_delete=models.CASCADE, related_name="elementos")
    tipo = models.CharField(max_length=30, choices=Tipo.choices, db_index=True)
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo", "nombre"]


class CapacidadAmbiental(models.Model):
    clave = models.SlugField(max_length=60, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]


class CapacidadOrganizacion(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE_DIAGNOSTICO = "pendiente_diagnostico", "Pendiente de diagnostico"
        APLICA = "aplica", "Aplica"
        NO_APLICA = "no_aplica", "No aplica"
        SIN_DATOS = "sin_datos", "Sin datos"
        CONSTRUYENDO_LINEA_BASE = "construyendo_linea_base", "Construyendo linea base"
        OPERATIVA = "operativa", "Operativa"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="capacidades_ambientales")
    capacidad = models.ForeignKey(CapacidadAmbiental, on_delete=models.PROTECT, related_name="organizaciones")
    estado = models.CharField(max_length=35, choices=Estado.choices, default=Estado.PENDIENTE_DIAGNOSTICO, db_index=True)
    recomendada_por_preset = models.BooleanField(default=False)
    configuracion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organizacion", "capacidad"], name="unique_capacidad_organizacion")]


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

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="activos_operacionales")
    codigo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.OTRO, db_index=True)
    descripcion = models.TextField(blank=True)
    unidad_operacional = models.ForeignKey("UnidadOperacional", on_delete=models.SET_NULL, null=True, blank=True, related_name="activos")
    proceso_operacional = models.ForeignKey("ProcesoOperacional", on_delete=models.SET_NULL, null=True, blank=True, related_name="activos")
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.OPERATIVO, db_index=True)
    fecha_alta = models.DateField(null=True, blank=True)
    fecha_baja = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(fields=["organizacion", "codigo"], name="unique_activo_codigo_org")]

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.unidad_operacional_id and self.unidad_operacional.organizacion_id != self.organizacion_id:
            errors["unidad_operacional"] = "La unidad pertenece a otra organizacion."
        if self.proceso_operacional_id and self.proceso_operacional.organizacion_id != self.organizacion_id:
            errors["proceso_operacional"] = "El proceso pertenece a otra organizacion."
        if errors:
            raise ValidationError(errors)


class Vehiculo(models.Model):
    activo = models.OneToOneField(ActivoOperacional, on_delete=models.CASCADE, related_name="vehiculo")
    patente = models.CharField(max_length=30, blank=True)
    marca = models.CharField(max_length=80, blank=True)
    modelo = models.CharField(max_length=80, blank=True)
    anio = models.PositiveIntegerField(null=True, blank=True)
    tipo_vehiculo = models.CharField(max_length=80, blank=True)
    combustible = models.CharField(max_length=80, blank=True)
    capacidad_carga = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    numero_ejes = models.PositiveSmallIntegerField(null=True, blank=True)


class Maquinaria(models.Model):
    activo = models.OneToOneField(ActivoOperacional, on_delete=models.CASCADE, related_name="maquinaria")
    marca = models.CharField(max_length=80, blank=True)
    modelo = models.CharField(max_length=80, blank=True)
    anio = models.PositiveIntegerField(null=True, blank=True)
    tipo_maquinaria = models.CharField(max_length=100, blank=True)
    combustible = models.CharField(max_length=80, blank=True)
    horometro_actual = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)


class MantenimientoActivo(models.Model):
    class Estado(models.TextChoices):
        PROGRAMADO = "programado", "Programado"
        EN_PROCESO = "en_proceso", "En proceso"
        REALIZADO = "realizado", "Realizado"
        VENCIDO = "vencido", "Vencido"
        CANCELADO = "cancelado", "Cancelado"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="mantenimientos_activos")
    activo = models.ForeignKey(ActivoOperacional, on_delete=models.CASCADE, related_name="mantenimientos")
    tipo = models.CharField(max_length=100)
    fecha_programada = models.DateField(null=True, blank=True, db_index=True)
    fecha_realizada = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PROGRAMADO, db_index=True)
    descripcion = models.TextField(blank=True)
    lectura_momento = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    unidad_lectura = models.CharField(max_length=20, blank=True)
    proveedor_responsable = models.CharField(max_length=180, blank=True)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.activo_id and self.activo.organizacion_id != self.organizacion_id:
            raise ValidationError({"activo": "El activo pertenece a otra organizacion."})


class CondicionOperacionalActivo(models.Model):
    class Estado(models.TextChoices):
        OPERATIVO = "operativo", "Operativo"
        RALENTI = "ralenti", "Ralenti"
        DETENIDO = "detenido", "Detenido"
        MANTENIMIENTO = "mantenimiento", "Mantenimiento"
        FALLA = "falla", "Falla"
        FUERA_SERVICIO = "fuera_servicio", "Fuera de servicio"

    activo = models.ForeignKey(ActivoOperacional, on_delete=models.CASCADE, related_name="condiciones")
    timestamp_inicio = models.DateTimeField(db_index=True)
    timestamp_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=30, choices=Estado.choices)
    fuente = models.ForeignKey("FuenteDatos", on_delete=models.SET_NULL, null=True, blank=True, related_name="condiciones_activos")
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp_inicio"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.fuente_id and self.fuente.organizacion_id != self.activo.organizacion_id:
            raise ValidationError({"fuente": "La fuente pertenece a otra organizacion."})


class UnidadOperacional(models.Model):
    class Tipo(models.TextChoices):
        PLANTA = "planta", "Planta"
        INSTALACION = "instalacion", "Instalacion"
        FAENA = "faena", "Faena"
        SUCURSAL = "sucursal", "Sucursal"
        CENTRO = "centro_operacional", "Centro operacional"
        OTRO = "otro", "Otro"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="unidades_operacionales")
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.OTRO)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ProcesoOperacional(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        EN_DISENO = "en_diseno", "En diseno"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="procesos_operacionales")
    unidad = models.ForeignKey(UnidadOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="procesos")
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.unidad_id and self.unidad.organizacion_id != self.organizacion_id:
            from django.core.exceptions import ValidationError
            raise ValidationError({"unidad": "La unidad debe pertenecer a la misma organizacion."})


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

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="fuentes_datos")
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.MANUAL, db_index=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    identificador_externo = models.CharField(max_length=180, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(fields=["organizacion", "nombre"], name="unique_fuente_datos_nombre_org")]


class ActividadOperacional(models.Model):
    class Tipo(models.TextChoices):
        TRANSPORTE = "transporte", "Transporte"
        CONSUMO_ENERGIA = "consumo_energia", "Consumo de energia"
        CONSUMO_AGUA = "consumo_agua", "Consumo de agua"
        CONSUMO_COMBUSTIBLE = "consumo_combustible", "Consumo de combustible"
        OPERACION_MAQUINARIA = "operacion_maquinaria", "Operacion de maquinaria"
        MOVIMIENTO_MATERIAL = "movimiento_material", "Movimiento de material"
        GESTION_RESIDUO = "gestion_residuo", "Gestion de residuo"
        GENERACION_ENERGIA = "generacion_energia", "Generacion de energia"
        PROCESO_PRODUCTIVO = "proceso_productivo", "Proceso productivo"
        OTRO = "otro", "Otro"

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        REGISTRADA = "registrada", "Registrada"
        INCOMPLETA = "incompleta", "Incompleta"
        LISTA_EVALUACION = "lista_para_evaluacion", "Lista para evaluacion"
        ANULADA = "anulada", "Anulada"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="actividades_operacionales")
    tipo = models.CharField(max_length=40, choices=Tipo.choices, default=Tipo.OTRO, db_index=True)
    codigo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=180)
    timestamp_inicio = models.DateTimeField(db_index=True)
    timestamp_fin = models.DateTimeField(null=True, blank=True)
    unidad_operacional = models.ForeignKey(UnidadOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="actividades")
    proceso_operacional = models.ForeignKey(ProcesoOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="actividades")
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.BORRADOR, db_index=True)
    referencia_externa = models.CharField(max_length=180, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    activos = models.ManyToManyField(ActivoOperacional, blank=True, related_name="actividades")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-timestamp_inicio", "codigo"]
        constraints = [models.UniqueConstraint(fields=["organizacion", "codigo"], name="unique_actividad_codigo_org")]
        indexes = [models.Index(fields=["organizacion", "tipo", "estado"])]

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.unidad_operacional_id and self.unidad_operacional.organizacion_id != self.organizacion_id:
            errors["unidad_operacional"] = "La unidad debe pertenecer a la misma organizacion."
        if self.proceso_operacional_id and self.proceso_operacional.organizacion_id != self.organizacion_id:
            errors["proceso_operacional"] = "El proceso debe pertenecer a la misma organizacion."
        if self.timestamp_fin and self.timestamp_inicio and self.timestamp_fin < self.timestamp_inicio:
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

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="observaciones_operacionales")
    actividad = models.ForeignKey(ActividadOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="observaciones")
    fuente = models.ForeignKey(FuenteDatos, on_delete=models.PROTECT, related_name="observaciones")
    concepto = models.SlugField(max_length=120, db_index=True)
    valor_numerico = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    valor_texto = models.TextField(blank=True)
    unidad = models.CharField(max_length=40, blank=True)
    timestamp_observacion = models.DateTimeField(db_index=True)
    metodo_captura = models.CharField(max_length=35, choices=MetodoCaptura.choices, default=MetodoCaptura.MANUAL)
    naturaleza = models.CharField(max_length=35, choices=Naturaleza.choices, default=Naturaleza.DECLARATIVO)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="observaciones_operacionales")
    evidencia = models.ForeignKey("EvidenciaObra", on_delete=models.SET_NULL, null=True, blank=True, related_name="observaciones_operacionales")
    version_evidencia = models.ForeignKey("VersionEvidencia", on_delete=models.SET_NULL, null=True, blank=True, related_name="observaciones_operacionales")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-timestamp_observacion", "id"]
        indexes = [models.Index(fields=["organizacion", "concepto"])]

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.actividad_id and self.actividad.organizacion_id != self.organizacion_id:
            errors["actividad"] = "La actividad debe pertenecer a la misma organizacion."
        if self.fuente_id and self.fuente.organizacion_id != self.organizacion_id:
            errors["fuente"] = "La fuente debe pertenecer a la misma organizacion."
        if self.evidencia_id and self.evidencia.organizacion_id != self.organizacion_id:
            errors["evidencia"] = "La evidencia debe pertenecer a la misma organizacion."
        if self.version_evidencia_id and self.version_evidencia.organizacion_id != self.organizacion_id:
            errors["version_evidencia"] = "La version de evidencia debe pertenecer a la misma organizacion."
        if self.version_evidencia_id and self.evidencia_id and self.version_evidencia.evidencia_id != self.evidencia_id:
            errors["version_evidencia"] = "La version debe pertenecer a la evidencia asociada."
        if self.valor_numerico is None and not self.valor_texto:
            errors["valor_numerico"] = "Debe informar un valor numerico o textual."
        if self.valor_numerico is not None and self.valor_texto:
            errors["valor_texto"] = "Use solo un tipo de valor por observacion."
        if errors:
            raise ValidationError(errors)


class ConfiguracionOrganizacion(models.Model):
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

    organizacion = models.OneToOneField(Organizacion, on_delete=models.CASCADE, related_name="configuracion")
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
    meta_emisiones_kg_co2e = models.DecimalField(max_digits=16, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuracion - {self.organizacion.organizacion_id}"


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
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="etapas")
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
        ordering = ["organizacion__nombre", "nombre"]

    def save(self, *args, **kwargs):
        if not self.etapa_id:
            self.etapa_id = unique_code(EtapaObra, "etapa_id", f"{self.organizacion.organizacion_id}_{self.nombre}", self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.organizacion.nombre} - {self.nombre}"


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
    organizacion = models.ForeignKey(Organizacion, on_delete=models.PROTECT, related_name="obras")
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
        MATERIA_PRIMA = "Materia prima", "Materia prima"
        MATERIALES = "Materiales", "Materiales"
        PRODUCCION = "Produccion", "Produccion"
        SECADO = "Secado", "Secado"
        TRANSPORTE = "Transporte", "Transporte"
        COMBUSTIBLE = "Combustible", "Combustible"
        RUTAS = "Rutas", "Rutas"
        FLOTA = "Flota", "Flota"
        MANTENCION = "Mantencion", "Mantencion"
        CARGA = "Carga", "Carga"
        MAQUINARIA = "Maquinaria", "Maquinaria"
        ENERGIA = "Energia", "Energia"
        AGUA = "Agua", "Agua"
        RESIDUOS = "Residuos", "Residuos"
        SUBPRODUCTOS = "Subproductos", "Subproductos"
        PROCESOS = "Procesos", "Procesos"
        PROCESOS_EXTERNOS = "Procesos externos", "Procesos externos"
        OTROS = "Otros", "Otros"

    actividad = models.CharField(max_length=120)
    preset = models.CharField(max_length=40, choices=Organizacion.Preset.choices, default=Organizacion.Preset.CONSTRUCCION, db_index=True)
    module = models.CharField(max_length=80, blank=True)
    categoria = models.CharField(max_length=40, choices=Categoria.choices, default=Categoria.OTROS)
    unidad = models.CharField(max_length=40)
    factor_emision = models.DecimalField(max_digits=12, decimal_places=6)
    fuente = models.CharField(max_length=180)
    anio = models.PositiveIntegerField()
    alcance = models.CharField(max_length=80, blank=True)
    descripcion = models.TextField(blank=True)
    actividad_key = models.CharField(max_length=160, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    activo = models.BooleanField(default=True)
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


class EspecieMadera(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    densidad_kg_m3 = models.DecimalField(max_digits=10, decimal_places=3)
    porcentaje_carbono = models.DecimalField(max_digits=8, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def save(self, *args, **kwargs):
        if self.porcentaje_carbono and self.porcentaje_carbono > 1:
            self.porcentaje_carbono = self.porcentaje_carbono / Decimal("100")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class LoteForestal(models.Model):
    lote_id = models.CharField(max_length=80, unique=True)
    organizacion = models.ForeignKey(Organizacion, on_delete=models.PROTECT, related_name="lotes_forestales")
    fecha = models.DateField()
    especie = models.CharField(max_length=120)
    volumen_m3 = models.DecimalField(max_digits=14, decimal_places=3)
    origen = models.CharField(max_length=240)
    destino = models.CharField(max_length=240, blank=True)
    tipo_producto = models.CharField(max_length=120, blank=True)
    densidad_kg_m3 = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    porcentaje_carbono = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    estado = models.CharField(max_length=80, blank=True)
    observaciones = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "lote_id"]
        indexes = [
            models.Index(fields=["organizacion_id", "fecha"]),
            models.Index(fields=["organizacion_id", "lote_id"]),
            models.Index(fields=["organizacion_id", "especie"]),
        ]

    def save(self, *args, **kwargs):
        if self.porcentaje_carbono and self.porcentaje_carbono > 1:
            self.porcentaje_carbono = self.porcentaje_carbono / Decimal("100")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.organizacion.organizacion_id} - {self.lote_id}"


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

    class TipoIngreso(models.TextChoices):
        MANUAL = "manual", "Manual"
        EXCEL = "excel", "Excel"
        CSV = "csv", "CSV"
        DOCUMENTO = "documento", "Documento"
        API_EXTERNA = "api_externa", "API externa"
        SENSOR_IOT = "sensor_iot", "Sensor IoT"
        SISTEMA = "sistema", "Sistema"

    class EstadoValidacion(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        VALIDADO = "validado", "Validado"
        RECHAZADO = "rechazado", "Rechazado"

    class EstadoGobernanza(models.TextChoices):
        NUEVO = "nuevo", "Nuevo"
        POSIBLE_DUPLICADO = "posible_duplicado", "Posible duplicado"
        DUPLICADO_CONFIRMADO = "duplicado_confirmado", "Duplicado confirmado"
        VALIDADO = "validado", "Validado"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.PROTECT, related_name="registros_emision", null=True, blank=True)
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="registros_emision", null=True, blank=True)
    etapa = models.ForeignKey(EtapaObra, on_delete=models.PROTECT, related_name="registros_emision", null=True, blank=True)
    lote_forestal = models.ForeignKey(LoteForestal, on_delete=models.SET_NULL, related_name="registros_emision", null=True, blank=True)
    actividad_operacional = models.ForeignKey(ActividadOperacional, on_delete=models.SET_NULL, related_name="registros_emision_legacy", null=True, blank=True)
    categoria = models.CharField(max_length=40, choices=Categoria.choices, default=Categoria.OTROS)
    fuente_emision = models.CharField(max_length=120)
    actividad_key = models.CharField(max_length=160, blank=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    unidad = models.CharField(max_length=40)
    factor_emision = models.DecimalField(max_digits=12, decimal_places=6)
    emisiones_kg_co2e = models.DecimalField(max_digits=14, decimal_places=3, editable=False)
    fecha = models.DateField(null=True, blank=True)
    proveedor = models.CharField(max_length=180, blank=True)
    numero_documento = models.CharField(max_length=120, blank=True)
    area_operacional = models.CharField(max_length=180, blank=True)
    unidad_operacional = models.CharField(max_length=180, blank=True)
    identificador_externo = models.CharField(max_length=180, blank=True)
    tipo_ingreso = models.CharField(max_length=30, choices=TipoIngreso.choices, default=TipoIngreso.SISTEMA, db_index=True)
    fuente_ingreso = models.CharField(max_length=180, blank=True)
    estado_validacion = models.CharField(
        max_length=20,
        choices=EstadoValidacion.choices,
        default=EstadoValidacion.PENDIENTE,
        db_index=True,
    )
    fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    fingerprint_nucleo = models.CharField(max_length=64, blank=True, db_index=True)
    estado_gobernanza = models.CharField(
        max_length=30,
        choices=EstadoGobernanza.choices,
        default=EstadoGobernanza.NUEVO,
        db_index=True,
    )
    registro_canonico = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="duplicados_detectados",
    )
    contabilizable = models.BooleanField(default=True, db_index=True)
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
            models.Index(fields=["organizacion_id", "fecha"]),
            models.Index(fields=["organizacion_id", "categoria"]),
            models.Index(fields=["organizacion_id", "actividad_key"]),
            models.Index(fields=["organizacion_id", "tipo_ingreso"]),
            models.Index(fields=["organizacion_id", "estado_validacion"]),
            models.Index(fields=["organizacion_id", "identificador_externo"]),
            models.Index(fields=["organizacion_id", "fingerprint"]),
            models.Index(fields=["organizacion_id", "fingerprint_nucleo"]),
            models.Index(fields=["obra_id", "categoria"]),
            models.Index(fields=["etapa_id", "categoria"]),
            models.Index(fields=["lote_forestal_id"]),
        ]

    def save(self, *args, **kwargs):
        if self.obra_id:
            self.organizacion = self.obra.organizacion
            if not self.etapa_id:
                self.etapa = self.obra.etapa_principal
        elif self.etapa_id and not self.organizacion_id:
            self.organizacion = self.etapa.organizacion
        if not self.lote_forestal_id and self.organizacion_id:
            metadata = self.metadata if isinstance(self.metadata, dict) else {}
            lote_reference = metadata.get("lote") or metadata.get("lote_id") or metadata.get("lote_forestal")
            if lote_reference:
                self.lote_forestal = LoteForestal.objects.filter(
                    organizacion_id=self.organizacion_id,
                    lote_id=str(lote_reference).strip(),
                ).first()
        if not self.actividad_key:
            self.actividad_key = normalize_key(self.fuente_emision).replace(" ", "_")
        if self.organizacion_id and self.fecha and self.fuente_emision and self.categoria and self.cantidad is not None and self.unidad:
            from .services.environmental_records import build_environmental_fingerprints

            self.fingerprint, self.fingerprint_nucleo = build_environmental_fingerprints(
                {
                    "organizacion": self.organizacion,
                    "fecha": self.fecha,
                    "fuente_emision": self.fuente_emision,
                    "categoria": self.categoria,
                    "cantidad": self.cantidad,
                    "unidad": self.unidad,
                    "proveedor": self.proveedor,
                    "numero_documento": self.numero_documento,
                    "area_operacional": self.area_operacional,
                    "unidad_operacional": self.unidad_operacional,
                    "identificador_externo": self.identificador_externo,
                }
            )
        self.emisiones_kg_co2e = (
            (self.cantidad or Decimal("0")) * (self.factor_emision or Decimal("0"))
            if self.contabilizable
            else Decimal("0")
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.obra or self.organizacion} - {self.fuente_emision}"


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

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="evidencias")
    obra = models.ForeignKey(Obra, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidencias")
    etapa = models.ForeignKey(EtapaObra, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidencias")
    registros_emision = models.ManyToManyField(RegistroEmision, blank=True, related_name="evidencias")
    lote_forestal = models.ForeignKey(LoteForestal, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidencias")
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
            models.Index(fields=["organizacion_id", "estado_documental"]),
            models.Index(fields=["organizacion_id", "tipo_evidencia"]),
            models.Index(fields=["obra_id", "estado_documental"]),
            models.Index(fields=["lote_forestal_id"]),
        ]

    def save(self, *args, **kwargs):
        if self.obra_id and not self.organizacion_id:
            self.organizacion = self.obra.organizacion
        if not self.lote_forestal_id and self.organizacion_id:
            metadata = self.metadata_extraccion if isinstance(self.metadata_extraccion, dict) else {}
            lote_reference = metadata.get("lote") or metadata.get("lote_id") or metadata.get("lote_forestal")
            if lote_reference:
                self.lote_forestal = LoteForestal.objects.filter(
                    organizacion_id=self.organizacion_id,
                    lote_id=str(lote_reference).strip(),
                ).first()
        if self.lote_forestal_id and self.estado_documental in {"sin_vinculo", ""}:
            self.estado_documental = self.EstadoDocumental.VINCULADA
        elif not self.obra_id and self.estado_documental == self.EstadoDocumental.PENDIENTE:
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

    evidencia = models.ForeignKey(EvidenciaObra, on_delete=models.CASCADE, related_name="versiones")
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="versiones_evidencia")
    version = models.PositiveIntegerField()
    archivo = models.FileField(upload_to=version_evidencia_upload_path)
    nombre_original = models.CharField(max_length=240)
    tipo_documental = models.CharField(max_length=80, blank=True)
    checksum_sha256 = models.CharField(max_length=64, db_index=True)
    estado_procesamiento = models.CharField(max_length=20, choices=EstadoProcesamiento.choices, default=EstadoProcesamiento.RECIBIDA)
    metadata_tecnica = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["evidencia", "version"], name="unique_version_evidencia")]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.evidencia_id and self.organizacion_id != self.evidencia.organizacion_id:
            raise ValidationError({"organizacion": "La version debe pertenecer a la organizacion de la evidencia."})


class PlantillaMapeo(models.Model):
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="plantillas_mapeo")
    fuente_datos = models.ForeignKey(FuenteDatos, on_delete=models.CASCADE, related_name="plantillas_mapeo")
    nombre = models.CharField(max_length=180)
    formato = models.CharField(max_length=20, default="excel_csv")
    version = models.PositiveIntegerField(default=1)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version", "nombre"]
        constraints = [models.UniqueConstraint(fields=["organizacion", "fuente_datos", "nombre", "version"], name="unique_plantilla_mapeo_version")]


class MapeoColumna(models.Model):
    plantilla = models.ForeignKey(PlantillaMapeo, on_delete=models.CASCADE, related_name="mapeos")
    columna_origen = models.CharField(max_length=180)
    columna_normalizada = models.SlugField(max_length=180)
    concepto_normalizado = models.SlugField(max_length=120)
    unidad_esperada = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["columna_origen"]
        constraints = [models.UniqueConstraint(fields=["plantilla", "columna_normalizada"], name="unique_mapeo_columna_plantilla")]


class ProcesoIngesta(models.Model):
    class Estado(models.TextChoices):
        RECIBIDO = "recibido", "Recibido"
        ANALIZANDO = "analizando", "Analizando"
        REQUIERE_MAPEO = "requiere_mapeo", "Requiere mapeo"
        LISTO_CONFIRMAR = "listo_para_confirmar", "Listo para confirmar"
        PROCESANDO = "procesando", "Procesando"
        COMPLETADO = "completado", "Completado"
        COMPLETADO_OBSERVACIONES = "completado_con_observaciones", "Completado con observaciones"
        FALLIDO = "fallido", "Fallido"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="procesos_ingesta")
    version_evidencia = models.ForeignKey(VersionEvidencia, on_delete=models.PROTECT, related_name="procesos_ingesta")
    fuente_datos = models.ForeignKey(FuenteDatos, on_delete=models.PROTECT, related_name="procesos_ingesta")
    plantilla_mapeo = models.ForeignKey(PlantillaMapeo, on_delete=models.SET_NULL, null=True, blank=True, related_name="procesos_ingesta")
    tipo_ingesta = models.CharField(max_length=30, default="transporte_excel_csv")
    estado = models.CharField(max_length=40, choices=Estado.choices, default=Estado.RECIBIDO, db_index=True)
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
        if self.version_evidencia_id and self.version_evidencia.organizacion_id != self.organizacion_id:
            raise ValidationError({"version_evidencia": "La evidencia pertenece a otra organizacion."})
        if self.fuente_datos_id and self.fuente_datos.organizacion_id != self.organizacion_id:
            raise ValidationError({"fuente_datos": "La fuente pertenece a otra organizacion."})


class RegistroExtraido(models.Model):
    class Estado(models.TextChoices):
        EXTRAIDO = "extraido", "Extraido"
        VALIDO = "valido", "Valido"
        ERROR = "error", "Error"
        PROCESADO = "procesado", "Procesado"

    proceso_ingesta = models.ForeignKey(ProcesoIngesta, on_delete=models.CASCADE, related_name="registros_extraidos")
    numero_fila = models.PositiveIntegerField()
    origen = models.CharField(max_length=120, blank=True)
    datos_originales = models.JSONField(default=dict)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.EXTRAIDO, db_index=True)
    errores = models.JSONField(default=list, blank=True)
    actividad_creada = models.ForeignKey(ActividadOperacional, on_delete=models.SET_NULL, null=True, blank=True, related_name="registros_origen")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["numero_fila"]
        constraints = [models.UniqueConstraint(fields=["proceso_ingesta", "numero_fila"], name="unique_registro_extraido_fila")]


class MetodologiaAmbiental(models.Model):
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, null=True, blank=True, related_name="metodologias_ambientales")
    codigo = models.SlugField(max_length=100)
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=80, db_index=True)
    flujo = models.SlugField(max_length=100, db_index=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organizacion", "codigo"], name="unique_metodologia_codigo_org")]


class VersionMetodologia(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PRUEBAS = "pruebas", "Pruebas"
        VALIDADA = "validada", "Validada"
        ACTIVA = "activa", "Activa"
        OBSOLETA = "obsoleta", "Obsoleta"

    metodologia = models.ForeignKey(MetodologiaAmbiental, on_delete=models.CASCADE, related_name="versiones")
    version = models.PositiveIntegerField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR, db_index=True)
    descripcion_tecnica = models.TextField(blank=True)
    fuente_referencia = models.TextField(blank=True)
    vigencia_desde = models.DateField(null=True, blank=True)
    vigencia_hasta = models.DateField(null=True, blank=True)
    validado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="metodologias_validadas")
    fecha_validacion = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["metodologia", "version"], name="unique_version_metodologia")]

    def save(self, *args, **kwargs):
        if self.pk:
            previous = VersionMetodologia.objects.filter(pk=self.pk).first()
            if previous and previous.estado == self.Estado.ACTIVA:
                from django.core.exceptions import ValidationError
                raise ValidationError("Una version activa es inmutable; cree una nueva version.")
        super().save(*args, **kwargs)


class FactorAmbiental(models.Model):
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, null=True, blank=True, related_name="factores_ambientales_v2")
    codigo = models.SlugField(max_length=100)
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=80, db_index=True)
    sustancia_impacto = models.CharField(max_length=80, default="CO2e")
    unidad_entrada = models.CharField(max_length=60)
    unidad_resultado = models.CharField(max_length=60, default="kgCO2e")
    contexto = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organizacion", "codigo"], name="unique_factor_ambiental_codigo_org")]


class VersionFactorAmbiental(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PRUEBAS = "pruebas", "Pruebas"
        VALIDADO = "validado", "Validado"
        ACTIVO = "activo", "Activo"
        OBSOLETO = "obsoleto", "Obsoleto"

    factor = models.ForeignKey(FactorAmbiental, on_delete=models.CASCADE, related_name="versiones")
    version = models.PositiveIntegerField()
    valor = models.DecimalField(max_digits=20, decimal_places=10)
    fuente = models.TextField()
    referencia = models.TextField(blank=True)
    region = models.CharField(max_length=100, blank=True)
    vigencia_desde = models.DateField(null=True, blank=True)
    vigencia_hasta = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["factor", "version"], name="unique_version_factor_ambiental")]

    def save(self, *args, **kwargs):
        if self.pk:
            previous = VersionFactorAmbiental.objects.filter(pk=self.pk).first()
            if previous and previous.estado == self.Estado.ACTIVO:
                from django.core.exceptions import ValidationError
                raise ValidationError("Una version activa es inmutable; cree una nueva version.")
        super().save(*args, **kwargs)


class FormulaAmbiental(models.Model):
    class Tipo(models.TextChoices):
        TRANSPORTE_TKM = "transporte_tkm", "Masa x distancia x factor"
        TRANSPORTE_VEHICULO_KM = "transporte_vehiculo_km", "Distancia x factor vehiculo"
        TRANSPORTE_COMBUSTIBLE = "transporte_combustible", "Combustible x factor"

    version_metodologia = models.OneToOneField(VersionMetodologia, on_delete=models.PROTECT, related_name="formula")
    factor_ambiental = models.ForeignKey(FactorAmbiental, on_delete=models.PROTECT, related_name="formulas")
    codigo = models.SlugField(max_length=100)
    tipo = models.CharField(max_length=40, choices=Tipo.choices)
    expresion_legible = models.CharField(max_length=300)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)


class VariableFormula(models.Model):
    class Rol(models.TextChoices):
        ACTIVIDAD = "actividad", "Actividad"
        COMPLEMENTARIA = "complementaria", "Complementaria"

    formula = models.ForeignKey(FormulaAmbiental, on_delete=models.CASCADE, related_name="variables")
    clave = models.SlugField(max_length=100)
    concepto_observacion = models.SlugField(max_length=120)
    unidad_esperada = models.CharField(max_length=40)
    obligatoria = models.BooleanField(default=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.ACTIVIDAD)
    descripcion = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["formula", "clave"], name="unique_variable_formula")]


class CalculoAmbiental(models.Model):
    class Estado(models.TextChoices):
        FINALIZADO = "finalizado", "Finalizado"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        FALLIDO = "fallido", "Fallido"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.PROTECT, related_name="calculos_ambientales_v2")
    actividad = models.ForeignKey(ActividadOperacional, on_delete=models.PROTECT, related_name="calculos_ambientales")
    version_metodologia = models.ForeignKey(VersionMetodologia, on_delete=models.PROTECT, related_name="calculos")
    formula = models.ForeignKey(FormulaAmbiental, on_delete=models.PROTECT, related_name="calculos")
    version_factor = models.ForeignKey(VersionFactorAmbiental, on_delete=models.PROTECT, related_name="calculos")
    resultado = models.DecimalField(max_digits=24, decimal_places=10)
    unidad_resultado = models.CharField(max_length=60)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.FINALIZADO)
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    version_interna = models.PositiveIntegerField(default=1)
    formula_aplicada = models.CharField(max_length=300)
    advertencias = models.JSONField(default=list, blank=True)
    completitud = models.CharField(max_length=30)
    snapshot_tecnico = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-fecha_calculo"]

    def save(self, *args, **kwargs):
        if self.pk and CalculoAmbiental.objects.filter(pk=self.pk).exists():
            from django.core.exceptions import ValidationError
            raise ValidationError("Un calculo finalizado es inmutable; cree uno nuevo.")
        super().save(*args, **kwargs)


class InputCalculoAmbiental(models.Model):
    calculo = models.ForeignKey(CalculoAmbiental, on_delete=models.PROTECT, related_name="inputs")
    variable = models.ForeignKey(VariableFormula, on_delete=models.PROTECT, related_name="inputs_calculo")
    observacion = models.ForeignKey(Observacion, on_delete=models.PROTECT, related_name="inputs_calculo")
    valor_utilizado = models.DecimalField(max_digits=20, decimal_places=10)
    unidad = models.CharField(max_length=40)
    concepto = models.SlugField(max_length=120)
    fuente = models.ForeignKey(FuenteDatos, on_delete=models.PROTECT, related_name="inputs_calculo")
    evidencia = models.ForeignKey(EvidenciaObra, on_delete=models.PROTECT, null=True, blank=True, related_name="inputs_calculo")
    version_evidencia = models.ForeignKey(VersionEvidencia, on_delete=models.PROTECT, null=True, blank=True, related_name="inputs_calculo")


class ImpactoAmbiental(models.Model):
    class Tipo(models.TextChoices):
        GENERADO = "generado", "Generado"
        REDUCCION = "reduccion", "Reduccion"
        EVITADO = "evitado", "Evitado"
        CAPTURA_REMOCION = "captura_remocion", "Captura/remocion"
        COMPENSACION = "compensacion", "Compensacion"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.PROTECT, related_name="impactos_ambientales_v2")
    actividad = models.ForeignKey(ActividadOperacional, on_delete=models.PROTECT, related_name="impactos_ambientales")
    calculo = models.OneToOneField(CalculoAmbiental, on_delete=models.PROTECT, related_name="impacto")
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.GENERADO)
    categoria = models.CharField(max_length=80)
    valor = models.DecimalField(max_digits=24, decimal_places=10)
    unidad = models.CharField(max_length=60)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class DocumentoAmbiental(models.Model):
    class FuenteOrigen(models.TextChoices):
        MANUAL = "manual", "Manual"
        EXCEL = "excel", "Excel"
        CSV = "csv", "CSV"
        PDF = "pdf", "PDF"
        FOTO = "foto", "Foto"
        CEMS = "cems", "CEMS"
        LABORATORIO = "laboratorio", "Laboratorio"
        OTRO = "otro", "Otro"

    class EstadoProcesamiento(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PROCESANDO = "procesando", "Procesando"
        EXTRAIDO = "extraido", "Extraido"
        OBSERVADO = "observado", "Observado"
        VALIDADO = "validado", "Validado"
        ERROR = "error", "Error"

    class EstadoValidacion(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        VALIDO = "valido", "Valido"
        OBSERVADO = "observado", "Observado"
        RECHAZADO = "rechazado", "Rechazado"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="documentos_ambientales")
    obra = models.ForeignKey(Obra, on_delete=models.SET_NULL, null=True, blank=True, related_name="documentos_ambientales")
    etapa = models.ForeignKey(EtapaObra, on_delete=models.SET_NULL, null=True, blank=True, related_name="documentos_ambientales")
    registros_emision = models.ManyToManyField(RegistroEmision, blank=True, related_name="documentos_ambientales")
    tipo_documento = models.CharField(max_length=80)
    industria = models.CharField(max_length=80, db_index=True)
    nombre = models.CharField(max_length=240)
    fecha_documento = models.DateField()
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)
    fuente_origen = models.CharField(max_length=20, choices=FuenteOrigen.choices, default=FuenteOrigen.MANUAL)
    archivo = models.FileField(upload_to=documento_ambiental_upload_path, null=True, blank=True)
    estado_procesamiento = models.CharField(max_length=20, choices=EstadoProcesamiento.choices, default=EstadoProcesamiento.PENDIENTE)
    estado_validacion = models.CharField(max_length=20, choices=EstadoValidacion.choices, default=EstadoValidacion.PENDIENTE)
    resumen = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_documento", "-created_at"]
        indexes = [
            models.Index(fields=["organizacion_id", "industria"]),
            models.Index(fields=["organizacion_id", "estado_validacion"]),
            models.Index(fields=["organizacion_id", "tipo_documento"]),
        ]

    def save(self, *args, **kwargs):
        if not self.industria and self.organizacion_id:
            self.industria = self.organizacion.preset
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.organizacion.organizacion_id} - {self.nombre}"


class LimiteNormativoAmbiental(models.Model):
    class Normativa(models.TextChoices):
        ISO_14001 = "ISO 14001", "ISO 14001"
        ISO_14064_1 = "ISO 14064-1", "ISO 14064-1"
        ISO_14067 = "ISO 14067", "ISO 14067"
        ISO_14040_14044 = "ISO 14040/14044", "ISO 14040/14044"
        ISO_21930 = "ISO 21930", "ISO 21930"
        LEY_21455 = "Ley 21.455", "Ley 21.455"
        LEY_20920 = "Ley 20.920", "Ley 20.920"
        LEY_19300 = "Ley 19.300", "Ley 19.300"
        HUELLA_CHILE = "HuellaChile", "HuellaChile"
        RCA = "RCA", "RCA"
        DS90 = "DS90", "DS90"
        DS38 = "DS38", "DS38"
        DS148 = "DS148", "DS148"
        RETC = "RETC", "RETC"
        SIDREP = "SIDREP", "SIDREP"
        SINADER = "SINADER", "SINADER"
        REP = "REP", "REP"
        CEMS = "CEMS", "CEMS"
        SERNAGEOMIN = "Sernageomin", "Sernageomin"
        SERNAPESCA = "Sernapesca", "Sernapesca"
        OTRO = "otro", "Otro"

    class Comparador(models.TextChoices):
        MENOR_IGUAL = "<=", "<="
        MAYOR_IGUAL = ">=", ">="
        RANGO = "rango", "Rango"
        PRESENCIA = "presencia", "Presencia"
        OBLIGATORIO = "obligatorio", "Obligatorio"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="limites_ambientales")
    industria = models.CharField(max_length=80, db_index=True)
    variable_id = models.CharField(max_length=80, db_index=True)
    nombre = models.CharField(max_length=180)
    normativa = models.CharField(max_length=40, choices=Normativa.choices)
    limite = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    unidad = models.CharField(max_length=40, blank=True)
    comparador = models.CharField(max_length=20, choices=Comparador.choices, default=Comparador.MENOR_IGUAL)
    region = models.CharField(max_length=120, blank=True)
    tipo_instalacion = models.CharField(max_length=120, blank=True)
    vigencia_desde = models.DateField(null=True, blank=True)
    vigencia_hasta = models.DateField(null=True, blank=True)
    fuente_normativa = models.CharField(max_length=300, blank=True)
    validado = models.BooleanField(default=False, db_index=True)
    activo = models.BooleanField(default=True)
    descripcion = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["variable_id", "normativa", "-created_at"]
        indexes = [
            models.Index(fields=["organizacion_id", "industria"]),
            models.Index(fields=["organizacion_id", "variable_id", "activo"]),
            models.Index(fields=["organizacion_id", "industria", "region", "validado"]),
        ]

    def save(self, *args, **kwargs):
        if not self.industria and self.organizacion_id:
            self.industria = self.organizacion.preset
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.organizacion.organizacion_id} - {self.variable_id} {self.comparador} {self.limite}"


class VariableAmbientalExtraida(models.Model):
    class EstadoCumplimiento(models.TextChoices):
        SIN_LIMITE = "sin_limite", "Sin limite"
        CUMPLE = "cumple", "Cumple"
        ALERTA = "alerta", "Alerta"
        INCUMPLE = "incumple", "Incumple"
        SIN_DATO = "sin_dato", "Sin dato"

    documento = models.ForeignKey(DocumentoAmbiental, on_delete=models.CASCADE, related_name="variables_extraidas")
    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="variables_ambientales")
    variable_id = models.CharField(max_length=80, db_index=True)
    nombre = models.CharField(max_length=180)
    categoria = models.CharField(max_length=80, blank=True)
    valor = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    unidad = models.CharField(max_length=40, blank=True)
    fecha_medicion = models.DateField(null=True, blank=True)
    punto_medicion = models.CharField(max_length=160, blank=True)
    limite_aplicable = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    unidad_limite = models.CharField(max_length=40, blank=True)
    estado_cumplimiento = models.CharField(max_length=20, choices=EstadoCumplimiento.choices, default=EstadoCumplimiento.SIN_DATO)
    porcentaje_sobre_limite = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    confianza_extraccion = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_medicion", "-created_at"]
        indexes = [
            models.Index(fields=["organizacion_id", "variable_id"]),
            models.Index(fields=["organizacion_id", "estado_cumplimiento"]),
            models.Index(fields=["documento_id"]),
        ]

    def save(self, *args, **kwargs):
        if self.documento_id and not self.organizacion_id:
            self.organizacion = self.documento.organizacion
        self.apply_applicable_limit()
        previous_status = None
        if self.pk:
            previous_status = VariableAmbientalExtraida.objects.filter(pk=self.pk).values_list("estado_cumplimiento", flat=True).first()
        self.calculate_compliance()
        super().save(*args, **kwargs)
        if self.estado_cumplimiento in {self.EstadoCumplimiento.ALERTA, self.EstadoCumplimiento.INCUMPLE}:
            self.sync_compliance_alert(previous_status)

    def apply_applicable_limit(self):
        if self.limite_aplicable is not None or not self.organizacion_id or not self.variable_id:
            return
        from .services.environmental_normative import applicable_validated_rules
        limite = applicable_validated_rules(
            self.organizacion, self.variable_id, on_date=self.fecha_medicion,
            installation_type=(self.metadata or {}).get("tipo_instalacion", ""),
        ).filter(limite__isnull=False).order_by("-created_at").first()
        if not limite:
            return
        metadata = dict(self.metadata or {})
        metadata.setdefault("normativa", limite.normativa)
        metadata.setdefault("comparador_limite", limite.comparador)
        metadata.setdefault("limite_id", limite.id)
        self.limite_aplicable = limite.limite
        self.unidad_limite = limite.unidad
        self.metadata = metadata

    def calculate_compliance(self):
        if self.valor is None:
            self.estado_cumplimiento = self.EstadoCumplimiento.SIN_DATO
            self.porcentaje_sobre_limite = None
            return
        if self.limite_aplicable is None:
            self.estado_cumplimiento = self.EstadoCumplimiento.SIN_LIMITE
            self.porcentaje_sobre_limite = None
            return
        limit = Decimal(self.limite_aplicable)
        value = Decimal(self.valor)
        if limit == 0:
            self.porcentaje_sobre_limite = None
        else:
            self.porcentaje_sobre_limite = ((value / limit) * Decimal("100")).quantize(Decimal("0.01"))
        comparator = (self.metadata or {}).get("comparador_limite", "<=")
        if comparator == ">=":
            if value >= limit:
                self.estado_cumplimiento = self.EstadoCumplimiento.CUMPLE
            elif value >= limit * Decimal("0.9"):
                self.estado_cumplimiento = self.EstadoCumplimiento.ALERTA
            else:
                self.estado_cumplimiento = self.EstadoCumplimiento.INCUMPLE
            return
        if value <= limit:
            self.estado_cumplimiento = self.EstadoCumplimiento.CUMPLE
        elif value <= limit * Decimal("1.1"):
            self.estado_cumplimiento = self.EstadoCumplimiento.ALERTA
        else:
            self.estado_cumplimiento = self.EstadoCumplimiento.INCUMPLE

    def sync_compliance_alert(self, previous_status=None):
        tipo_alerta = self.estado_cumplimiento
        severidad = "amarillo" if tipo_alerta == self.EstadoCumplimiento.ALERTA else "rojo"
        normativa = (self.metadata or {}).get("normativa", "")
        base = {
            "organizacion": self.organizacion,
            "documento": self.documento,
            "variable": self,
            "severidad": severidad,
            "tipo_alerta": tipo_alerta,
            "titulo": f"{self.nombre} en {self.get_estado_cumplimiento_display().lower()}",
            "descripcion": f"Valor registrado: {self.valor} {self.unidad}. Limite aplicable: {self.limite_aplicable} {self.unidad_limite}.",
            "accion_sugerida": "Revisar evidencia, validar dato y ejecutar accion correctiva si corresponde.",
            "normativa": normativa,
            "fecha_evento": self.fecha_medicion or self.documento.fecha_documento,
            "metadata": {"variable_id": self.variable_id, "estado_cumplimiento": self.estado_cumplimiento},
        }
        latest = AlertaCumplimientoAmbiental.objects.filter(variable=self).order_by("-created_at").first()
        if latest and latest.tipo_alerta == tipo_alerta:
            for field, value in base.items():
                setattr(latest, field, value)
            latest.save()
            return
        if latest and previous_status == self.estado_cumplimiento:
            return
        AlertaCumplimientoAmbiental.objects.create(**base)

    def __str__(self):
        return f"{self.organizacion.organizacion_id} - {self.variable_id}: {self.valor}"


class AlertaCumplimientoAmbiental(models.Model):
    class Severidad(models.TextChoices):
        VERDE = "verde", "Verde"
        AMARILLO = "amarillo", "Amarillo"
        ROJO = "rojo", "Rojo"
        GRIS = "gris", "Gris"

    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        EN_REVISION = "en_revision", "En revision"
        RESUELTA = "resuelta", "Resuelta"
        DESCARTADA = "descartada", "Descartada"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="alertas_cumplimiento")
    documento = models.ForeignKey(DocumentoAmbiental, on_delete=models.SET_NULL, null=True, blank=True, related_name="alertas_cumplimiento")
    variable = models.ForeignKey(VariableAmbientalExtraida, on_delete=models.SET_NULL, null=True, blank=True, related_name="alertas_cumplimiento")
    severidad = models.CharField(max_length=20, choices=Severidad.choices, default=Severidad.GRIS)
    tipo_alerta = models.CharField(max_length=80)
    titulo = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    accion_sugerida = models.TextField(blank=True)
    normativa = models.CharField(max_length=80, blank=True)
    fecha_evento = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_evento", "-created_at"]
        indexes = [
            models.Index(fields=["organizacion_id", "estado"]),
            models.Index(fields=["organizacion_id", "severidad"]),
            models.Index(fields=["variable_id", "tipo_alerta"]),
        ]

    def __str__(self):
        return f"{self.organizacion.organizacion_id} - {self.titulo}"


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


class TransporteLoteForestal(models.Model):
    lote_forestal = models.ForeignKey(LoteForestal, on_delete=models.CASCADE, related_name="transportes")
    fecha = models.DateField(null=True, blank=True)
    vehiculo = models.CharField(max_length=120, blank=True)
    patente = models.CharField(max_length=30, blank=True)
    conductor = models.CharField(max_length=120, blank=True)
    origen = models.CharField(max_length=240)
    destino = models.CharField(max_length=240)
    distancia_km = models.DecimalField(max_digits=12, decimal_places=3)
    litros_diesel = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    consumo_estimado_litro_km = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.3000"))
    factor_diesel = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("2.6800"))
    emisiones_transporte_kg_co2e = models.DecimalField(max_digits=14, decimal_places=3, editable=False)
    registro_emision = models.OneToOneField(RegistroEmision, on_delete=models.SET_NULL, null=True, blank=True, related_name="transporte_lote_forestal")
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-created_at"]
        indexes = [
            models.Index(fields=["lote_forestal_id", "fecha"]),
            models.Index(fields=["patente"]),
        ]

    @property
    def litros_calculados(self):
        if self.litros_diesel is not None:
            return self.litros_diesel
        return (self.distancia_km or Decimal("0")) * (self.consumo_estimado_litro_km or Decimal("0"))

    def save(self, *args, **kwargs):
        litros = self.litros_calculados
        self.emisiones_transporte_kg_co2e = litros * (self.factor_diesel or Decimal("0"))
        super().save(*args, **kwargs)
        self.sync_registro_emision(litros)

    def sync_registro_emision(self, litros):
        metadata = {
            "preset": self.lote_forestal.organizacion.preset,
            "module": "transporte_forestal",
            "lote": self.lote_forestal.lote_id,
            "patente": self.patente,
            "origen": self.origen,
            "destino": self.destino,
            "distancia_km": str(self.distancia_km),
        }
        defaults = {
            "organizacion": self.lote_forestal.organizacion,
            "lote_forestal": self.lote_forestal,
            "categoria": RegistroEmision.Categoria.TRANSPORTE,
            "fuente_emision": "Transporte forestal",
            "cantidad": litros,
            "unidad": "litros diesel",
            "factor_emision": self.factor_diesel,
            "fecha": self.fecha,
            "origen_transporte": self.origen,
            "destino_transporte": self.destino,
            "distancia_km": self.distancia_km,
            "observaciones": self.observaciones,
            "metadata": metadata,
        }
        if self.registro_emision_id:
            for field, value in defaults.items():
                setattr(self.registro_emision, field, value)
            self.registro_emision.save()
            return
        registro = RegistroEmision.objects.create(**defaults)
        TransporteLoteForestal.objects.filter(pk=self.pk).update(registro_emision=registro)
        self.registro_emision = registro

    def __str__(self):
        return f"{self.lote_forestal.lote_id} - {self.patente or self.fecha}"


class DatoACV(models.Model):
    class Etapa(models.TextChoices):
        MATERIA_PRIMA = "materia_prima", "Materia prima"
        FABRICACION = "fabricacion", "Fabricacion"
        TRANSPORTE = "transporte", "Transporte"
        USO_OPERACION = "uso_operacion", "Uso / operacion"
        MANTENCION = "mantencion", "Mantencion"
        FIN_VIDA = "fin_vida", "Fin de vida"
        REUTILIZACION_RECICLAJE_DISPOSICION = "reutilizacion_reciclaje_disposicion", "Reutilizacion / reciclaje / disposicion"

    class CalidadDato(models.TextChoices):
        MEDIDO = "medido", "Medido"
        CALCULADO = "calculado", "Calculado"
        REFERENCIAL = "referencial", "Referencial"
        DESCONOCIDO = "desconocido", "Desconocido"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="datos_acv")
    material_producto = models.CharField(max_length=240)
    obra = models.ForeignKey(Obra, on_delete=models.SET_NULL, null=True, blank=True, related_name="datos_acv")
    lote_forestal = models.ForeignKey(LoteForestal, on_delete=models.SET_NULL, null=True, blank=True, related_name="datos_acv")
    etapa = models.CharField(max_length=50, choices=Etapa.choices)
    valor = models.DecimalField(max_digits=16, decimal_places=6)
    unidad = models.CharField(max_length=40)
    fuente = models.CharField(max_length=240)
    evidencias = models.ManyToManyField(EvidenciaObra, blank=True, related_name="datos_acv")
    documentos = models.ManyToManyField(DocumentoAmbiental, blank=True, related_name="datos_acv")
    calidad_dato = models.CharField(max_length=20, choices=CalidadDato.choices, default=CalidadDato.DESCONOCIDO)
    origen_dato = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["material_producto", "etapa"]
        indexes = [models.Index(fields=["organizacion", "etapa"])]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.valor is None or self.valor < 0:
            raise ValidationError({"valor": "No puede ser negativo."})
        for field in ("obra", "lote_forestal"):
            relation = getattr(self, field)
            if relation and relation.organizacion_id != self.organizacion_id:
                raise ValidationError({field: "Debe pertenecer a la organizacion."})


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


class ProblematicaAmbiental(models.Model):
    class Estado(models.TextChoices):
        DETECTADA = "detectada", "Detectada"
        EN_ANALISIS = "en_analisis", "En analisis"
        ACCION_PROPUESTA = "accion_propuesta", "Accion propuesta"
        EN_IMPLEMENTACION = "en_implementacion", "En implementacion"
        EN_SEGUIMIENTO = "en_seguimiento", "En seguimiento"
        RESUELTA = "resuelta", "Resuelta"
        MEJORA_INSUFICIENTE = "mejora_insuficiente", "Mejora insuficiente"
        NO_RESUELTA = "no_resuelta", "No resuelta"
        ESCALADA = "escalada", "Escalada"

    class Riesgo(models.TextChoices):
        BAJO = "bajo", "Bajo"
        MEDIO = "medio", "Medio"
        ALTO = "alto", "Alto"
        CRITICO = "critico", "Critico"

    class Resultado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de medicion"
        EFECTIVA = "efectiva", "Efectiva"
        PARCIAL = "parcialmente_efectiva", "Parcialmente efectiva"
        NO_EFECTIVA = "no_efectiva", "No efectiva"

    organizacion = models.ForeignKey(Organizacion, on_delete=models.CASCADE, related_name="problematicas_ambientales")
    titulo = models.CharField(max_length=240)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=120)
    indicador = models.CharField(max_length=120, default="co2e_total_kg")
    unidad_indicador = models.CharField(max_length=40, default="kgCO2e")
    obra = models.ForeignKey(Obra, on_delete=models.SET_NULL, null=True, blank=True, related_name="problematicas_ambientales")
    area_operacional = models.CharField(max_length=180, blank=True)
    unidad_operacional = models.CharField(max_length=180, blank=True)
    valor_inicial = models.DecimalField(max_digits=18, decimal_places=6)
    objetivo_meta = models.DecimalField(max_digits=18, decimal_places=6)
    valor_posterior = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    mejora_absoluta = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    mejora_porcentaje = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    fecha_deteccion = models.DateField()
    nivel_riesgo = models.CharField(max_length=20, choices=Riesgo.choices, default=Riesgo.MEDIO)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.DETECTADA)
    resultado_evaluacion = models.CharField(max_length=30, choices=Resultado.choices, default=Resultado.PENDIENTE)
    requiere_evaluacion_profesional = models.BooleanField(default=False, db_index=True)
    criterios_escalamiento = models.JSONField(default=list, blank=True)
    escalada_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_deteccion", "-created_at"]
        indexes = [models.Index(fields=["organizacion", "estado"]), models.Index(fields=["organizacion", "categoria"])]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.obra_id and self.obra.organizacion_id != self.organizacion_id:
            raise ValidationError({"obra": "Debe pertenecer a la organizacion."})


class AccionMejoraAmbiental(models.Model):
    problematica = models.ForeignKey(ProblematicaAmbiental, on_delete=models.CASCADE, related_name="acciones")
    titulo = models.CharField(max_length=240)
    descripcion = models.TextField()
    responsable = models.CharField(max_length=180, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_objetivo = models.DateField(null=True, blank=True)
    implementada_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]


class MedicionSeguimientoAmbiental(models.Model):
    problematica = models.ForeignKey(ProblematicaAmbiental, on_delete=models.CASCADE, related_name="mediciones")
    accion = models.ForeignKey(AccionMejoraAmbiental, on_delete=models.SET_NULL, null=True, blank=True, related_name="mediciones")
    fecha = models.DateField()
    valor = models.DecimalField(max_digits=18, decimal_places=6)
    unidad = models.CharField(max_length=40)
    fuente = models.CharField(max_length=120, default="manual")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "created_at"]


class HistorialProblematicaAmbiental(models.Model):
    problematica = models.ForeignKey(ProblematicaAmbiental, on_delete=models.CASCADE, related_name="historial")
    evento = models.CharField(max_length=40)
    estado_anterior = models.CharField(max_length=30, blank=True)
    estado_nuevo = models.CharField(max_length=30, blank=True)
    detalle = models.TextField(blank=True)
    usuario = models.CharField(max_length=150, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class RecomendacionAgenteAmbiental(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"
        CRITICA = "critica", "Critica"

    class Confianza(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"

    problematica = models.ForeignKey(ProblematicaAmbiental, on_delete=models.CASCADE, related_name="recomendaciones_agente")
    accion = models.TextField()
    justificacion = models.TextField()
    indicador_afectado = models.CharField(max_length=120)
    resultado_esperado = models.TextField()
    prioridad = models.CharField(max_length=20, choices=Prioridad.choices)
    periodo_seguimiento = models.CharField(max_length=120)
    nivel_confianza = models.CharField(max_length=20, choices=Confianza.choices)
    diagnostico = models.JSONField(default=dict, blank=True)
    contexto_resumen = models.JSONField(default=dict, blank=True)
    proveedor = models.CharField(max_length=80, blank=True)
    modelo = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["problematica", "prioridad"])]


class ExpedienteAmbiental(models.Model):
    problematica = models.ForeignKey(ProblematicaAmbiental, on_delete=models.CASCADE, related_name="expedientes")
    version = models.PositiveIntegerField(default=1)
    contenido_procesado = models.JSONField(default=dict)
    resumen_ejecutivo = models.TextField()
    proveedor_resumen = models.CharField(max_length=80, blank=True)
    modelo_resumen = models.CharField(max_length=120, blank=True)
    generado_por = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version", "-created_at"]
        constraints = [models.UniqueConstraint(fields=["problematica", "version"], name="unique_expediente_problematica_version")]
