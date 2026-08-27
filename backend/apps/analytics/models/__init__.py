from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime


from .platform import (
    EventoAuditoriaSaaS,
    Organizacion,
    SuscripcionSaaS,
    UsuarioObraAcceso,
    UsuarioOrganizacion,
)
from .operational_context import (
    AreaOperacional,
    EspacioTrabajoOperacional,
    EtapaObra,
    Obra,
    ProcesoOperacional,
    UnidadOperacional,
)
from .assets import (
    ActivoOperacional,
    CondicionOperacionalActivo,
    MantenimientoActivo,
    Maquinaria,
    PuntoAmbientalOperacional,
    Vehiculo,
)
from .operational_data import ActividadOperacional, FuenteDatos, Observacion
from .transport import RutaOperacional, ViajeOperacional
from .materials import EventoMaterial, LoteMaterial, MaterialOperacional
from .provenance import (
    EvidenciaObra,
    VersionEvidencia,
    evidencia_obra_upload_path,
    version_evidencia_upload_path,
)
from .ingestion import MapeoColumna, PlantillaMapeo, ProcesoIngesta, RegistroExtraido
from .environmental_flows import RegistroFlujoAmbiental
from .quality import DiscrepanciaDato, EvaluacionCalidadDato, PoliticaConfianzaFuente
from .indicators import (
    IndicadorAmbiental,
    LineaBaseAmbiental,
    PeriodoComparable,
    ValorIndicador,
)
from .governance import (
    CompatibilidadVersionMetodologia,
    FactorAmbiental,
    FormulaAmbiental,
    MetodologiaAmbiental,
    VariableFormula,
    VersionFactorAmbiental,
    VersionMetodologia,
)
from .calculations import CalculoAmbiental, ImpactoAmbiental, InputCalculoAmbiental
from .improvement import (
    AccionMejoraAmbiental,
    AlcanceProblematica,
    CicloReevaluacionProblematica,
    HistorialMetaProblematica,
    HistorialProblematicaAmbiental,
    IndicadorProblematica,
    MedicionSeguimientoAmbiental,
    ProblematicaAmbiental,
    ResultadoIntervencion,
    SnapshotIntervencion,
    SnapshotValorIndicador,
)
from .intelligence import (
    CasoConocimientoAmbiental,
    ComandoCopiloto,
    HistorialRestriccionContextual,
    HitoDecisionIA,
    MemoriaOrganizacion,
    RecomendacionAgenteAmbiental,
    RestriccionContextual,
)
from .reporting import (
    EventoAuditoriaAmbiental,
    ExpedienteAmbiental,
    InformeAmbiental,
    SnapshotInformeAmbiental,
)
from .professional import (
    CorreccionHistoricaAmbiental,
    HallazgoRevisionProfesional,
    RevisionProfesionalAmbiental,
)
from .utils import normalize_key, unique_code


def documento_ambiental_upload_path(instance, filename):
    organizacion = (
        instance.organizacion.organizacion_id
        if instance.organizacion_id
        else "SIN_ORGANIZACION"
    )
    return f"documentos_ambientales/{organizacion}/{filename}"


def evidencia_formatos_default():
    return ["PDF", "JPG", "PNG", "XLSX", "CSV", "DOCX"]


class DiagnosticoAmbientalInicial(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROGRESO = "en_progreso", "En progreso"
        COMPLETADO = "completado", "Completado"
        REQUIERE_ACTUALIZACION = "requiere_actualizacion", "Requiere actualizacion"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="diagnosticos_ambientales"
    )
    obra = models.ForeignKey(
        "Obra",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="diagnosticos_ambientales",
    )
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_finalizacion = models.DateField(null=True, blank=True)
    objetivo_principal = models.TextField(blank=True)
    descripcion_contexto = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="diagnosticos_ambientales",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion"],
                condition=models.Q(obra__isnull=True),
                name="unique_diagnostico_general_org",
            ),
            models.UniqueConstraint(
                fields=["organizacion", "obra"],
                condition=models.Q(obra__isnull=False),
                name="unique_diagnostico_obra_org",
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.obra_id and self.obra.organizacion_id != self.organizacion_id:
            raise ValidationError(
                {"obra": "La obra debe pertenecer a la misma organizacion."}
            )


class ElementoDiagnosticoAmbiental(models.Model):
    class Tipo(models.TextChoices):
        PROCESO = "proceso", "Proceso identificado"
        INFORMACION_DISPONIBLE = "informacion_disponible", "Informacion disponible"
        INFORMACION_FALTANTE = "informacion_faltante", "Informacion faltante"
        FUENTE = "fuente", "Fuente conocida"
        BRECHA = "brecha", "Brecha ambiental"

    diagnostico = models.ForeignKey(
        DiagnosticoAmbientalInicial, on_delete=models.CASCADE, related_name="elementos"
    )
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

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="capacidades_ambientales"
    )
    capacidad = models.ForeignKey(
        CapacidadAmbiental, on_delete=models.PROTECT, related_name="organizaciones"
    )
    estado = models.CharField(
        max_length=35,
        choices=Estado.choices,
        default=Estado.PENDIENTE_DIAGNOSTICO,
        db_index=True,
    )
    recomendada_por_preset = models.BooleanField(default=False)
    disponibilidad_inicial = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("regular", "Informacion regular"),
            ("parcial", "Informacion parcial"),
            ("sin_informacion", "Sin informacion"),
            ("no_seguro", "No estoy seguro"),
        ],
    )
    configuracion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "capacidad"],
                name="unique_capacidad_organizacion",
            )
        ]


class AreaCapacidadAmbiental(models.Model):
    area = models.ForeignKey(
        AreaOperacional, on_delete=models.CASCADE, related_name="flujos_asociados"
    )
    capacidad_organizacion = models.ForeignKey(
        CapacidadOrganizacion, on_delete=models.CASCADE, related_name="areas_origen"
    )
    sugerida = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["area", "capacidad_organizacion"],
                name="unique_area_capacidad_ambiental",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.area_id
            and self.capacidad_organizacion_id
            and self.area.organizacion_id != self.capacidad_organizacion.organizacion_id
        ):
            raise ValidationError(
                "El area y el flujo deben pertenecer a la misma organizacion."
            )


class AplicabilidadCapacidadObra(models.Model):
    class Estado(models.TextChoices):
        NO_DETERMINADO = "no_determinado", "No determinado"
        PENDIENTE = "pendiente", "Pendiente"
        APLICA = "aplica", "Aplica"
        NO_APLICA = "no_aplica", "No aplica"
        SIN_DATOS = "sin_datos", "Sin datos"

    obra = models.ForeignKey(
        "Obra", on_delete=models.CASCADE, related_name="aplicabilidades_capacidades"
    )
    capacidad = models.ForeignKey(
        CapacidadAmbiental,
        on_delete=models.PROTECT,
        related_name="aplicabilidades_obras",
    )
    diagnostico = models.ForeignKey(
        DiagnosticoAmbientalInicial,
        on_delete=models.CASCADE,
        related_name="aplicabilidades_capacidades",
    )
    estado = models.CharField(
        max_length=25,
        choices=Estado.choices,
        default=Estado.NO_DETERMINADO,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["obra", "capacidad"], name="unique_capacidad_obra"
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if self.diagnostico_id and self.diagnostico.obra_id != self.obra_id:
            errors["diagnostico"] = "El diagnostico debe pertenecer a la misma obra."
        if (
            self.diagnostico_id
            and self.diagnostico.organizacion_id != self.obra.organizacion_id
        ):
            errors["diagnostico"] = (
                "El diagnostico debe pertenecer a la organizacion de la obra."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


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

    organizacion = models.OneToOneField(
        Organizacion, on_delete=models.CASCADE, related_name="configuracion"
    )
    unidad_emisiones = models.CharField(max_length=20, default="kg CO2e")
    factor_electrico_default = models.CharField(
        max_length=160, blank=True, default="Factor electrico vigente"
    )
    region_electrica_default = models.CharField(
        max_length=120, blank=True, default="Biobio"
    )
    redondeo_decimales = models.PositiveSmallIntegerField(default=1)
    modo_importacion = models.CharField(
        max_length=20, choices=ModoImportacion.choices, default=ModoImportacion.FLEXIBLE
    )
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
    reporte_agrupacion_default = models.CharField(
        max_length=20, choices=AgrupacionReporte.choices, default=AgrupacionReporte.MES
    )
    reporte_periodo_default = models.CharField(
        max_length=30,
        choices=PeriodoReporte.choices,
        default=PeriodoReporte.ULTIMOS_12_MESES,
    )
    reporte_mostrar_categoria = models.BooleanField(default=True)
    reporte_mostrar_etapa = models.BooleanField(default=True)
    reporte_mostrar_tabla = models.BooleanField(default=True)
    reporte_unidad_visual_emisiones = models.CharField(max_length=20, default="kg CO2e")
    reporte_lectura_ejecutiva = models.BooleanField(default=True)
    reporte_equivalencias = models.BooleanField(default=True)
    meta_emisiones_kg_co2e = models.DecimalField(
        max_digits=16, decimal_places=3, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuracion - {self.organizacion.organizacion_id}"


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
    preset = models.CharField(
        max_length=40,
        choices=Organizacion.Preset.choices,
        default=Organizacion.Preset.CONSTRUCCION,
        db_index=True,
    )
    module = models.CharField(max_length=80, blank=True)
    categoria = models.CharField(
        max_length=40, choices=Categoria.choices, default=Categoria.OTROS
    )
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
            models.UniqueConstraint(
                fields=["actividad", "unidad", "fuente", "anio"],
                name="unique_factor_construccion",
            )
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
    factor_emision_default = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
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
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.PROTECT, related_name="lotes_forestales"
    )
    fecha = models.DateField()
    especie = models.CharField(max_length=120)
    volumen_m3 = models.DecimalField(max_digits=14, decimal_places=3)
    origen = models.CharField(max_length=240)
    destino = models.CharField(max_length=240, blank=True)
    tipo_producto = models.CharField(max_length=120, blank=True)
    densidad_kg_m3 = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    porcentaje_carbono = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )
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

    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.PROTECT,
        related_name="registros_emision",
        null=True,
        blank=True,
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.CASCADE,
        related_name="registros_emision",
        null=True,
        blank=True,
    )
    etapa = models.ForeignKey(
        EtapaObra,
        on_delete=models.PROTECT,
        related_name="registros_emision",
        null=True,
        blank=True,
    )
    lote_forestal = models.ForeignKey(
        LoteForestal,
        on_delete=models.SET_NULL,
        related_name="registros_emision",
        null=True,
        blank=True,
    )
    actividad_operacional = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.SET_NULL,
        related_name="registros_emision_legacy",
        null=True,
        blank=True,
    )
    categoria = models.CharField(
        max_length=40, choices=Categoria.choices, default=Categoria.OTROS
    )
    fuente_emision = models.CharField(max_length=120)
    actividad_key = models.CharField(max_length=160, blank=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    unidad = models.CharField(max_length=40)
    factor_emision = models.DecimalField(max_digits=12, decimal_places=6)
    emisiones_kg_co2e = models.DecimalField(
        max_digits=14, decimal_places=3, editable=False
    )
    fecha = models.DateField(null=True, blank=True)
    proveedor = models.CharField(max_length=180, blank=True)
    numero_documento = models.CharField(max_length=120, blank=True)
    area_operacional = models.CharField(max_length=180, blank=True)
    unidad_operacional = models.CharField(max_length=180, blank=True)
    identificador_externo = models.CharField(max_length=180, blank=True)
    tipo_ingreso = models.CharField(
        max_length=30,
        choices=TipoIngreso.choices,
        default=TipoIngreso.SISTEMA,
        db_index=True,
    )
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
    distancia_km = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True
    )
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
            lote_reference = (
                metadata.get("lote")
                or metadata.get("lote_id")
                or metadata.get("lote_forestal")
            )
            if lote_reference:
                self.lote_forestal = LoteForestal.objects.filter(
                    organizacion_id=self.organizacion_id,
                    lote_id=str(lote_reference).strip(),
                ).first()
        if not self.actividad_key:
            self.actividad_key = normalize_key(self.fuente_emision).replace(" ", "_")
        if (
            self.organizacion_id
            and self.fecha
            and self.fuente_emision
            and self.categoria
            and self.cantidad is not None
            and self.unidad
        ):
            from ..services.environmental_records import (
                build_environmental_fingerprints,
            )

            self.fingerprint, self.fingerprint_nucleo = (
                build_environmental_fingerprints(
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
            )
        self.emisiones_kg_co2e = (
            (self.cantidad or Decimal("0")) * (self.factor_emision or Decimal("0"))
            if self.contabilizable
            else Decimal("0")
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.obra or self.organizacion} - {self.fuente_emision}"


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

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="documentos_ambientales"
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_ambientales",
    )
    etapa = models.ForeignKey(
        EtapaObra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_ambientales",
    )
    registros_emision = models.ManyToManyField(
        RegistroEmision, blank=True, related_name="documentos_ambientales"
    )
    tipo_documento = models.CharField(max_length=80)
    industria = models.CharField(max_length=80, db_index=True)
    nombre = models.CharField(max_length=240)
    fecha_documento = models.DateField()
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)
    fuente_origen = models.CharField(
        max_length=20, choices=FuenteOrigen.choices, default=FuenteOrigen.MANUAL
    )
    archivo = models.FileField(
        upload_to=documento_ambiental_upload_path, null=True, blank=True
    )
    estado_procesamiento = models.CharField(
        max_length=20,
        choices=EstadoProcesamiento.choices,
        default=EstadoProcesamiento.PENDIENTE,
    )
    estado_validacion = models.CharField(
        max_length=20,
        choices=EstadoValidacion.choices,
        default=EstadoValidacion.PENDIENTE,
    )
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

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="limites_ambientales"
    )
    industria = models.CharField(max_length=80, db_index=True)
    variable_id = models.CharField(max_length=80, db_index=True)
    nombre = models.CharField(max_length=180)
    normativa = models.CharField(max_length=40, choices=Normativa.choices)
    limite = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    unidad = models.CharField(max_length=40, blank=True)
    comparador = models.CharField(
        max_length=20, choices=Comparador.choices, default=Comparador.MENOR_IGUAL
    )
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

    documento = models.ForeignKey(
        DocumentoAmbiental, on_delete=models.CASCADE, related_name="variables_extraidas"
    )
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="variables_ambientales"
    )
    variable_id = models.CharField(max_length=80, db_index=True)
    nombre = models.CharField(max_length=180)
    categoria = models.CharField(max_length=80, blank=True)
    valor = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    unidad = models.CharField(max_length=40, blank=True)
    fecha_medicion = models.DateField(null=True, blank=True)
    punto_medicion = models.CharField(max_length=160, blank=True)
    limite_aplicable = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    unidad_limite = models.CharField(max_length=40, blank=True)
    estado_cumplimiento = models.CharField(
        max_length=20,
        choices=EstadoCumplimiento.choices,
        default=EstadoCumplimiento.SIN_DATO,
    )
    porcentaje_sobre_limite = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True
    )
    confianza_extraccion = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
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
            previous_status = (
                VariableAmbientalExtraida.objects.filter(pk=self.pk)
                .values_list("estado_cumplimiento", flat=True)
                .first()
            )
        self.calculate_compliance()
        super().save(*args, **kwargs)
        if self.estado_cumplimiento in {
            self.EstadoCumplimiento.ALERTA,
            self.EstadoCumplimiento.INCUMPLE,
        }:
            self.sync_compliance_alert(previous_status)

    def apply_applicable_limit(self):
        if (
            self.limite_aplicable is not None
            or not self.organizacion_id
            or not self.variable_id
        ):
            return
        from ..services.environmental_normative import applicable_validated_rules

        limite = (
            applicable_validated_rules(
                self.organizacion,
                self.variable_id,
                on_date=self.fecha_medicion,
                installation_type=(self.metadata or {}).get("tipo_instalacion", ""),
            )
            .filter(limite__isnull=False)
            .order_by("-created_at")
            .first()
        )
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
            self.porcentaje_sobre_limite = ((value / limit) * Decimal("100")).quantize(
                Decimal("0.01")
            )
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
        severidad = (
            "amarillo" if tipo_alerta == self.EstadoCumplimiento.ALERTA else "rojo"
        )
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
            "metadata": {
                "variable_id": self.variable_id,
                "estado_cumplimiento": self.estado_cumplimiento,
            },
        }
        latest = (
            AlertaCumplimientoAmbiental.objects.filter(variable=self)
            .order_by("-created_at")
            .first()
        )
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

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="alertas_cumplimiento"
    )
    documento = models.ForeignKey(
        DocumentoAmbiental,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alertas_cumplimiento",
    )
    variable = models.ForeignKey(
        VariableAmbientalExtraida,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alertas_cumplimiento",
    )
    severidad = models.CharField(
        max_length=20, choices=Severidad.choices, default=Severidad.GRIS
    )
    tipo_alerta = models.CharField(max_length=80)
    titulo = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.ABIERTA
    )
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
    etapa = models.ForeignKey(
        EtapaObra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transportes",
    )
    vehiculo = models.CharField(max_length=120)
    patente = models.CharField(max_length=30)
    origen = models.CharField(max_length=240)
    destino = models.CharField(max_length=240)
    origen_coords = models.JSONField(null=True, blank=True)
    destino_coords = models.JSONField(null=True, blank=True)
    distancia_km = models.DecimalField(max_digits=12, decimal_places=3)
    consumo_estimado_litro_km = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("0.3000")
    )
    litros_combustible = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True
    )
    emisiones_kg_co2e = models.DecimalField(
        max_digits=14, decimal_places=3, editable=False
    )
    fecha_hora = models.DateTimeField()
    registro_emision = models.OneToOneField(
        RegistroEmision,
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
    lote_forestal = models.ForeignKey(
        LoteForestal, on_delete=models.CASCADE, related_name="transportes"
    )
    fecha = models.DateField(null=True, blank=True)
    vehiculo = models.CharField(max_length=120, blank=True)
    patente = models.CharField(max_length=30, blank=True)
    conductor = models.CharField(max_length=120, blank=True)
    origen = models.CharField(max_length=240)
    destino = models.CharField(max_length=240)
    distancia_km = models.DecimalField(max_digits=12, decimal_places=3)
    litros_diesel = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True
    )
    consumo_estimado_litro_km = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("0.3000")
    )
    factor_diesel = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("2.6800")
    )
    emisiones_transporte_kg_co2e = models.DecimalField(
        max_digits=14, decimal_places=3, editable=False
    )
    registro_emision = models.OneToOneField(
        RegistroEmision,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transporte_lote_forestal",
    )
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
        return (self.distancia_km or Decimal("0")) * (
            self.consumo_estimado_litro_km or Decimal("0")
        )

    def save(self, *args, **kwargs):
        litros = self.litros_calculados
        self.emisiones_transporte_kg_co2e = litros * (
            self.factor_diesel or Decimal("0")
        )
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
        TransporteLoteForestal.objects.filter(pk=self.pk).update(
            registro_emision=registro
        )
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
        REUTILIZACION_RECICLAJE_DISPOSICION = (
            "reutilizacion_reciclaje_disposicion",
            "Reutilizacion / reciclaje / disposicion",
        )

    class CalidadDato(models.TextChoices):
        MEDIDO = "medido", "Medido"
        CALCULADO = "calculado", "Calculado"
        REFERENCIAL = "referencial", "Referencial"
        DESCONOCIDO = "desconocido", "Desconocido"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="datos_acv"
    )
    material_producto = models.CharField(max_length=240)
    obra = models.ForeignKey(
        Obra, on_delete=models.SET_NULL, null=True, blank=True, related_name="datos_acv"
    )
    lote_forestal = models.ForeignKey(
        LoteForestal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="datos_acv",
    )
    etapa = models.CharField(max_length=50, choices=Etapa.choices)
    valor = models.DecimalField(max_digits=16, decimal_places=6)
    unidad = models.CharField(max_length=40)
    fuente = models.CharField(max_length=240)
    evidencias = models.ManyToManyField(
        EvidenciaObra, blank=True, related_name="datos_acv"
    )
    documentos = models.ManyToManyField(
        DocumentoAmbiental, blank=True, related_name="datos_acv"
    )
    calidad_dato = models.CharField(
        max_length=20, choices=CalidadDato.choices, default=CalidadDato.DESCONOCIDO
    )
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

    obra = models.ForeignKey(
        Obra, on_delete=models.CASCADE, related_name="historial_cambios"
    )
    tipo = models.CharField(max_length=20, choices=TipoCambio.choices)
    fuente = models.CharField(max_length=80, blank=True)
    usuario = models.CharField(max_length=120, blank=True, null=True)
    evidencia = models.ForeignKey(
        EvidenciaObra,
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
        return f"{self.obra.codigo_obra} - {self.get_tipo_display()}"
