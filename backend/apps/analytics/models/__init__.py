from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, Sum
from django.db.models.signals import pre_delete
from django.dispatch import receiver
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
from .utils import normalize_key, unique_code


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


class MaterialOperacional(models.Model):
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="materiales_operacionales"
    )
    codigo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=180)
    categoria = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    unidad_base = models.CharField(max_length=40)
    proveedor_fabricante = models.CharField(max_length=180, blank=True)
    especificacion_tecnica = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "codigo"],
                name="unique_material_operacional_codigo_org",
            )
        ]


class LoteMaterial(models.Model):
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="lotes_materiales"
    )
    material = models.ForeignKey(
        MaterialOperacional, on_delete=models.PROTECT, related_name="lotes"
    )
    codigo = models.CharField(max_length=120)
    proveedor = models.CharField(max_length=180, blank=True)
    referencia_documental = models.CharField(max_length=180, blank=True)
    fecha = models.DateField(null=True, blank=True)
    cantidad_inicial = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    unidad = models.CharField(max_length=40, blank=True)
    fuente = models.ForeignKey(
        FuenteDatos,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lotes_materiales",
    )
    evidencia = models.ForeignKey(
        "EvidenciaObra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lotes_materiales",
    )
    version_evidencia = models.ForeignKey(
        "VersionEvidencia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lotes_materiales",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "codigo"],
                name="unique_lote_material_codigo_org",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        for field in ("material", "fuente", "evidencia", "version_evidencia"):
            value = getattr(self, field, None)
            if value and value.organizacion_id != self.organizacion_id:
                errors[field] = "La referencia debe pertenecer a la misma organizacion."
        if (
            self.version_evidencia_id
            and self.evidencia_id
            and self.version_evidencia.evidencia_id != self.evidencia_id
        ):
            errors["version_evidencia"] = (
                "La version debe pertenecer a la evidencia asociada."
            )
        if self.cantidad_inicial is not None and self.cantidad_inicial < 0:
            errors["cantidad_inicial"] = "La cantidad inicial no puede ser negativa."
        if self.cantidad_inicial is not None and not self.unidad:
            errors["unidad"] = "Debe indicar la unidad de la cantidad inicial."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class EventoMaterial(models.Model):
    class Tipo(models.TextChoices):
        ADQUISICION = "adquisicion", "Adquisicion"
        DESPACHO = "despacho", "Despacho"
        RECEPCION = "recepcion", "Recepcion"
        ALMACENAMIENTO = "almacenamiento", "Almacenamiento"
        USO = "uso", "Uso"
        CONSUMO = "consumo", "Consumo"
        TRASLADO = "traslado", "Traslado"
        SOBRANTE = "sobrante", "Sobrante"
        DEVOLUCION = "devolucion", "Devolucion"
        REUTILIZACION = "reutilizacion", "Reutilizacion"
        RESIDUO = "residuo", "Residuo"
        AJUSTE = "ajuste", "Ajuste"

    class Estado(models.TextChoices):
        REGISTRADO = "registrado", "Registrado"
        ANULADO = "anulado", "Anulado"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="eventos_materiales"
    )
    material = models.ForeignKey(
        MaterialOperacional, on_delete=models.PROTECT, related_name="eventos"
    )
    lote = models.ForeignKey(
        LoteMaterial,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos",
    )
    actividad = models.OneToOneField(
        ActividadOperacional, on_delete=models.PROTECT, related_name="evento_material"
    )
    evento_origen = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_derivados",
    )
    tipo = models.CharField(max_length=25, choices=Tipo.choices, db_index=True)
    fecha_hora = models.DateTimeField(db_index=True)
    observacion_cantidad = models.ForeignKey(
        Observacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="eventos_material_cantidad_seleccionada",
    )
    origen = models.CharField(max_length=240, blank=True)
    destino = models.CharField(max_length=240, blank=True)
    obra = models.ForeignKey(
        "Obra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_materiales",
    )
    proceso = models.ForeignKey(
        ProcesoOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_materiales",
    )
    fuente = models.ForeignKey(
        FuenteDatos,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="eventos_materiales",
    )
    evidencia = models.ForeignKey(
        "EvidenciaObra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_materiales",
    )
    version_evidencia = models.ForeignKey(
        "VersionEvidencia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_materiales",
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.REGISTRADO, db_index=True
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["fecha_hora", "id"]
        indexes = [
            models.Index(fields=["organizacion", "material", "fecha_hora"]),
            models.Index(fields=["organizacion", "lote", "fecha_hora"]),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        for field in (
            "material",
            "lote",
            "actividad",
            "evento_origen",
            "obra",
            "proceso",
            "fuente",
            "evidencia",
            "version_evidencia",
            "observacion_cantidad",
        ):
            value = getattr(self, field, None)
            if value and value.organizacion_id != self.organizacion_id:
                errors[field] = "La referencia debe pertenecer a la misma organizacion."
        if (
            self.actividad_id
            and self.actividad.tipo != ActividadOperacional.Tipo.MOVIMIENTO_MATERIAL
        ):
            errors["actividad"] = "La actividad debe ser un movimiento de material."
        if (
            self.actividad_id
            and self.obra_id
            and self.actividad.obra_id not in {None, self.obra_id}
        ):
            errors["obra"] = "La obra debe coincidir con el contexto de la actividad."
        if self.actividad_id and self.actividad.obra_id and not self.obra_id:
            errors["obra"] = "El evento debe heredar la obra de la actividad."
        if (
            self.proceso_id
            and self.actividad_id
            and self.actividad.proceso_operacional_id not in {None, self.proceso_id}
        ):
            errors["proceso"] = (
                "El proceso debe coincidir con el contexto de la actividad."
            )
        if self.lote_id and self.lote.material_id != self.material_id:
            errors["lote"] = "El lote debe pertenecer al material del evento."
        if self.evento_origen_id and (
            self.evento_origen.material_id != self.material_id
            or (self.lote_id and self.evento_origen.lote_id not in {None, self.lote_id})
        ):
            errors["evento_origen"] = (
                "El evento origen debe corresponder al mismo material y lote."
            )
        if self.evento_origen_id:
            if self.pk and self.evento_origen_id == self.pk:
                errors["evento_origen"] = "Un evento no puede ser su propio origen."
            elif self.fecha_hora and self.evento_origen.fecha_hora > self.fecha_hora:
                errors["evento_origen"] = (
                    "El evento origen no puede ocurrir despues del evento."
                )
            else:
                visited = {self.pk} if self.pk else set()
                current = self.evento_origen
                while current:
                    if current.pk in visited:
                        errors["evento_origen"] = (
                            "La relacion de origen no puede formar ciclos."
                        )
                        break
                    visited.add(current.pk)
                    current = current.evento_origen
        if self.observacion_cantidad_id:
            observation = self.observacion_cantidad
            if (
                observation.actividad_id != self.actividad_id
                or observation.concepto != "cantidad_material"
            ):
                errors["observacion_cantidad"] = (
                    "La observacion debe ser la cantidad de la actividad del evento."
                )
            elif (
                observation.valor_numerico is None
                or observation.valor_numerico < 0
                or not observation.unidad
            ):
                errors["observacion_cantidad"] = (
                    "La cantidad seleccionada debe ser numerica, no negativa y tener unidad."
                )
        if (
            self.version_evidencia_id
            and self.evidencia_id
            and self.version_evidencia.evidencia_id != self.evidencia_id
        ):
            errors["version_evidencia"] = (
                "La version debe pertenecer a la evidencia asociada."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class RegistroFlujoAmbiental(models.Model):
    class Flujo(models.TextChoices):
        ENERGIA = "energia", "Energia"
        GENERACION_PROPIA = "generacion_propia", "Generacion propia"
        AGUA = "agua", "Agua"
        COMBUSTIBLE = "combustible", "Combustible por clasificar"
        COMBUSTIBLE_ESTACIONARIO = (
            "combustible_estacionario",
            "Combustible estacionario",
        )
        COMBUSTIBLE_MOVIL = "combustible_movil", "Combustible movil"
        RESIDUO = "residuo", "Residuo"
        RUIDO = "ruido", "Ruido"
        EMISIONES_ATMOSFERICAS = "emisiones_atmosfericas", "Emisiones atmosfericas"
        SUELO = "suelo", "Suelo"
        GESTION_HIDRICA_SUELO = "gestion_hidrica_suelo", "Gestion hidrica y suelo"

    class Granularidad(models.TextChoices):
        ORGANIZACION = "organizacion", "Organizacion"
        INSTALACION = "instalacion", "Instalacion"
        OBRA = "obra", "Obra"
        PROCESO = "proceso", "Proceso"
        ACTIVO = "activo", "Activo"
        PUNTO = "punto", "Punto de medicion"

    class DestinoResiduo(models.TextChoices):
        SIN_CLASIFICAR = "sin_clasificar", "Sin clasificar"
        RESIDUO = "residuo", "Residuo"
        REUTILIZACION = "reutilizacion", "Reutilizacion"
        RECICLAJE = "reciclaje", "Reciclaje"
        VALORIZACION = "valorizacion", "Valorizacion"
        DISPOSICION = "disposicion", "Disposicion"
        SUBPRODUCTO = "subproducto_reutilizado", "Subproducto reutilizado"

    class DestinoOperacional(models.TextChoices):
        SIN_CLASIFICAR = "sin_clasificar", "Sin clasificar"
        GENERADOR = "generador", "Generador"
        MAQUINARIA = "maquinaria", "Maquinaria"
        VEHICULO = "vehiculo", "Vehiculo"
        EQUIPO_MENOR = "equipo_menor", "Equipo menor"
        CALEFACCION = "calefaccion", "Calefaccion"
        OTRO = "otro", "Otro"
        RESIDUO = "residuo", "Residuo"
        REUTILIZACION = "reutilizacion", "Reutilizacion"
        RECICLAJE = "reciclaje", "Reciclaje"
        VALORIZACION = "valorizacion", "Valorizacion"
        DISPOSICION = "disposicion", "Disposicion"
        SUBPRODUCTO_REUTILIZADO = (
            "subproducto_reutilizado",
            "Subproducto reutilizado",
        )

    EXPECTED_ACTIVITY_TYPES = {
        Flujo.ENERGIA: ActividadOperacional.Tipo.CONSUMO_ENERGIA,
        Flujo.GENERACION_PROPIA: ActividadOperacional.Tipo.GENERACION_ENERGIA,
        Flujo.AGUA: ActividadOperacional.Tipo.CONSUMO_AGUA,
        Flujo.COMBUSTIBLE: ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE,
        Flujo.COMBUSTIBLE_ESTACIONARIO: ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE_ESTACIONARIO,
        Flujo.COMBUSTIBLE_MOVIL: ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE,
        Flujo.RESIDUO: ActividadOperacional.Tipo.GESTION_RESIDUO,
        Flujo.RUIDO: ActividadOperacional.Tipo.MONITOREO_RUIDO,
        Flujo.EMISIONES_ATMOSFERICAS: ActividadOperacional.Tipo.MONITOREO_EMISIONES_ATMOSFERICAS,
        Flujo.SUELO: ActividadOperacional.Tipo.GESTION_SUELO,
        Flujo.GESTION_HIDRICA_SUELO: ActividadOperacional.Tipo.GESTION_HIDRICA_SUELO,
    }

    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="registros_flujos_ambientales",
    )
    actividad = models.OneToOneField(
        ActividadOperacional,
        on_delete=models.PROTECT,
        related_name="registro_flujo_ambiental",
    )
    flujo = models.CharField(max_length=35, choices=Flujo.choices, db_index=True)
    periodo_inicio = models.DateTimeField()
    periodo_fin = models.DateTimeField(null=True, blank=True)
    granularidad = models.CharField(
        max_length=20, choices=Granularidad.choices, default=Granularidad.ORGANIZACION
    )
    punto = models.ForeignKey(
        PuntoAmbientalOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros",
    )
    unidad_operacional = models.ForeignKey(
        UnidadOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_flujos_ambientales",
    )
    proceso = models.ForeignKey(
        ProcesoOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_flujos_ambientales",
    )
    activo = models.ForeignKey(
        ActivoOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_flujos_ambientales",
    )
    obra = models.ForeignKey(
        "Obra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_flujos_ambientales",
    )
    evento_material = models.ForeignKey(
        EventoMaterial,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_flujos_ambientales",
    )
    tipo_recurso = models.CharField(max_length=120, blank=True)
    metrica = models.CharField(max_length=80, blank=True)
    destino_operacional = models.CharField(
        max_length=30,
        choices=DestinoOperacional.choices,
        default=DestinoOperacional.SIN_CLASIFICAR,
    )
    proveedor_gestor = models.CharField(max_length=180, blank=True)
    ubicacion_contexto = models.CharField(max_length=240, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-periodo_inicio", "id"]
        indexes = [models.Index(fields=["organizacion", "flujo", "periodo_inicio"])]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        for field in (
            "actividad",
            "punto",
            "unidad_operacional",
            "proceso",
            "activo",
            "obra",
            "evento_material",
        ):
            value = getattr(self, field, None)
            if value and value.organizacion_id != self.organizacion_id:
                errors[field] = "La referencia debe pertenecer a la misma organizacion."
        expected = self.EXPECTED_ACTIVITY_TYPES.get(self.flujo)
        if self.actividad_id and expected and self.actividad.tipo != expected:
            errors["actividad"] = (
                "La actividad no corresponde al flujo ambiental declarado."
            )
        if (
            self.actividad_id
            and self.obra_id
            and self.actividad.obra_id not in {None, self.obra_id}
        ):
            errors["obra"] = "La obra debe coincidir con el contexto de la actividad."
        if self.actividad_id and self.actividad.obra_id and not self.obra_id:
            errors["obra"] = "El registro debe heredar la obra de la actividad."
        required_scope = {
            self.Granularidad.INSTALACION: "unidad_operacional",
            self.Granularidad.OBRA: "obra",
            self.Granularidad.PROCESO: "proceso",
            self.Granularidad.ACTIVO: "activo",
            self.Granularidad.PUNTO: "punto",
        }
        required = required_scope.get(self.granularidad)
        if required and not getattr(self, f"{required}_id"):
            errors[required] = (
                "Debe indicar la referencia correspondiente a la granularidad."
            )
        scope_ids = {
            "unidad_operacional": self.unidad_operacional_id,
            "obra": self.obra_id,
            "proceso": self.proceso_id,
            "activo": self.activo_id,
            "punto": self.punto_id,
        }
        allowed_scope = {
            self.Granularidad.ORGANIZACION: set(),
            self.Granularidad.INSTALACION: {"unidad_operacional"},
            self.Granularidad.OBRA: {"obra"},
            self.Granularidad.PROCESO: {"proceso", "unidad_operacional"},
            self.Granularidad.ACTIVO: {"activo", "proceso", "unidad_operacional"},
            self.Granularidad.PUNTO: {
                "punto",
                "activo",
                "proceso",
                "unidad_operacional",
                "obra",
            },
        }.get(self.granularidad, set())
        for field, value in scope_ids.items():
            if value and field not in allowed_scope:
                errors[field] = (
                    "La referencia excede la granularidad atribuible declarada."
                )
        if (
            self.granularidad == self.Granularidad.PROCESO
            and self.proceso_id
            and self.unidad_operacional_id
            and self.proceso.unidad_id != self.unidad_operacional_id
        ):
            errors["unidad_operacional"] = (
                "La unidad debe corresponder al proceso declarado."
            )
        if self.granularidad == self.Granularidad.ACTIVO and self.activo_id:
            if (
                self.proceso_id
                and self.activo.proceso_operacional_id != self.proceso_id
            ):
                errors["proceso"] = "El proceso debe corresponder al activo declarado."
            if (
                self.unidad_operacional_id
                and self.activo.unidad_operacional_id != self.unidad_operacional_id
            ):
                errors["unidad_operacional"] = (
                    "La unidad debe corresponder al activo declarado."
                )
        if self.granularidad == self.Granularidad.PUNTO and self.punto_id:
            point_fields = {
                "activo": "activo_id",
                "proceso": "proceso_operacional_id",
                "unidad_operacional": "unidad_operacional_id",
                "obra": "obra_id",
            }
            for field, point_field in point_fields.items():
                record_id = scope_ids[field]
                point_id = getattr(self.punto, point_field)
                if record_id and point_id and record_id != point_id:
                    errors[field] = (
                        "La referencia contradice el contexto del punto ambiental."
                    )
        if self.periodo_fin and self.periodo_fin < self.periodo_inicio:
            errors["periodo_fin"] = (
                "El fin del periodo no puede ser anterior al inicio."
            )
        if self.evento_material_id and self.flujo != self.Flujo.RESIDUO:
            errors["evento_material"] = (
                "Un evento material solo puede enlazarse a un flujo de residuo."
            )
        destinos_residuo = {
            self.DestinoOperacional.RESIDUO,
            self.DestinoOperacional.REUTILIZACION,
            self.DestinoOperacional.RECICLAJE,
            self.DestinoOperacional.VALORIZACION,
            self.DestinoOperacional.DISPOSICION,
            self.DestinoOperacional.SUBPRODUCTO_REUTILIZADO,
        }

        destinos_combustible = {
            self.DestinoOperacional.GENERADOR,
            self.DestinoOperacional.MAQUINARIA,
            self.DestinoOperacional.VEHICULO,
            self.DestinoOperacional.EQUIPO_MENOR,
            self.DestinoOperacional.CALEFACCION,
            self.DestinoOperacional.OTRO,
        }

        if (
            self.flujo == self.Flujo.RESIDUO
            and self.destino_operacional in destinos_combustible
        ):
            errors["destino_operacional"] = (
                "El destino seleccionado no corresponde a un flujo de residuos."
            )

        if (
            self.flujo in {
                self.Flujo.COMBUSTIBLE,
                self.Flujo.COMBUSTIBLE_ESTACIONARIO,
                self.Flujo.COMBUSTIBLE_MOVIL,
            }
            and self.destino_operacional in destinos_residuo
        ):
            errors["destino_operacional"] = (
                "El uso seleccionado no corresponde a un registro de combustible."
            )

        if (
            self.flujo
            not in {
                self.Flujo.RESIDUO,
                self.Flujo.COMBUSTIBLE,
                self.Flujo.COMBUSTIBLE_ESTACIONARIO,
                self.Flujo.COMBUSTIBLE_MOVIL,
            }
            and self.destino_operacional
            != self.DestinoOperacional.SIN_CLASIFICAR
        ):
            errors["destino_operacional"] = (
                "Este flujo ambiental no admite un destino operacional."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
            from ..services.environmental_records import build_environmental_fingerprints

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
        RegistroEmision, blank=True, related_name="evidencias"
    )
    lote_forestal = models.ForeignKey(
        LoteForestal,
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
                self.lote_forestal = LoteForestal.objects.filter(
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


class MetodologiaAmbiental(models.Model):
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="metodologias_ambientales",
    )
    codigo = models.SlugField(max_length=100)
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=80, db_index=True)
    flujo = models.SlugField(max_length=100, db_index=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                condition=Q(organizacion__isnull=True),
                name="unique_metodologia_codigo_global",
            ),
            models.UniqueConstraint(
                fields=["organizacion", "codigo"],
                condition=Q(organizacion__isnull=False),
                name="unique_metodologia_codigo_tenant",
            ),
        ]


class VersionMetodologia(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PRUEBAS = "pruebas", "Pruebas"
        VALIDADA = "validada", "Validada"
        ACTIVA = "activa", "Activa"
        OBSOLETA = "obsoleta", "Obsoleta"

    metodologia = models.ForeignKey(
        MetodologiaAmbiental, on_delete=models.CASCADE, related_name="versiones"
    )
    version = models.PositiveIntegerField()
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.BORRADOR, db_index=True
    )
    descripcion_tecnica = models.TextField(blank=True)
    fuente_referencia = models.TextField(blank=True)
    vigencia_desde = models.DateField(null=True, blank=True)
    vigencia_hasta = models.DateField(null=True, blank=True)
    validado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="metodologias_validadas",
    )
    fecha_validacion = models.DateTimeField(null=True, blank=True)
    aplicabilidad = models.JSONField(default=dict, blank=True)
    prioridad = models.PositiveIntegerField(default=100, db_index=True)
    requiere_revision_profesional = models.BooleanField(default=False)
    tipo_resultado = models.CharField(max_length=30, default="emision")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["metodologia", "version"], name="unique_version_metodologia"
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            previous = VersionMetodologia.objects.filter(pk=self.pk).first()
            if previous and previous.estado == self.Estado.ACTIVA:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    "Una version activa es inmutable; cree una nueva version."
                )
            if previous and previous.estado != self.estado:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    "Use la transición metodológica explícita para cambiar el estado."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.estado in {
            self.Estado.VALIDADA,
            self.Estado.ACTIVA,
            self.Estado.OBSOLETA,
        }:
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Una versión metodológica gobernada no puede eliminarse."
            )
        return super().delete(*args, **kwargs)


class FactorAmbiental(models.Model):
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="factores_ambientales_v2",
    )
    codigo = models.SlugField(max_length=100)
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=80, db_index=True)
    sustancia_impacto = models.CharField(max_length=80, default="CO2e")
    unidad_entrada = models.CharField(max_length=60)
    unidad_resultado = models.CharField(max_length=60, default="kgCO2e")
    contexto = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                condition=Q(organizacion__isnull=True),
                name="unique_factor_ambiental_codigo_global",
            ),
            models.UniqueConstraint(
                fields=["organizacion", "codigo"],
                condition=Q(organizacion__isnull=False),
                name="unique_factor_ambiental_codigo_tenant",
            ),
        ]


class VersionFactorAmbiental(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PRUEBAS = "pruebas", "Pruebas"
        VALIDADO = "validado", "Validado"
        ACTIVO = "activo", "Activo"
        OBSOLETO = "obsoleto", "Obsoleto"

    factor = models.ForeignKey(
        FactorAmbiental, on_delete=models.CASCADE, related_name="versiones"
    )
    version = models.PositiveIntegerField()
    valor = models.DecimalField(max_digits=20, decimal_places=10)
    fuente = models.TextField()
    referencia = models.TextField(blank=True)
    region = models.CharField(max_length=100, blank=True)
    vigencia_desde = models.DateField(null=True, blank=True)
    vigencia_hasta = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.BORRADOR, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["factor", "version"], name="unique_version_factor_ambiental"
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            previous = VersionFactorAmbiental.objects.filter(pk=self.pk).first()
            if previous and previous.estado == self.Estado.ACTIVO:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    "Una version activa es inmutable; cree una nueva version."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.estado in {
            self.Estado.VALIDADO,
            self.Estado.ACTIVO,
            self.Estado.OBSOLETO,
        }:
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Una versión gobernada del factor no puede eliminarse."
            )
        return super().delete(*args, **kwargs)


class FormulaAmbiental(models.Model):
    class Tipo(models.TextChoices):
        TRANSPORTE_TKM = "transporte_tkm", "Masa x distancia x factor"
        TRANSPORTE_VEHICULO_KM = "transporte_vehiculo_km", "Distancia x factor vehiculo"
        TRANSPORTE_COMBUSTIBLE = "transporte_combustible", "Combustible x factor"

    version_metodologia = models.OneToOneField(
        VersionMetodologia, on_delete=models.PROTECT, related_name="formula"
    )
    factor_ambiental = models.ForeignKey(
        FactorAmbiental, on_delete=models.PROTECT, related_name="formulas"
    )
    codigo = models.SlugField(max_length=100)
    tipo = models.CharField(max_length=40, choices=Tipo.choices)
    expresion_legible = models.CharField(max_length=300)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if (
            self.pk
            and self.version_metodologia.estado != VersionMetodologia.Estado.BORRADOR
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "La formula de una metodologia activa es inmutable; cree una nueva version."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.version_metodologia.estado != VersionMetodologia.Estado.BORRADOR:
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "La formula de una metodologia activa no puede eliminarse."
            )
        return super().delete(*args, **kwargs)


class VariableFormula(models.Model):
    class Criticidad(models.TextChoices):
        CRITICA = "critica", "Crítica"
        COMPLEMENTARIA = "complementaria", "Complementaria"
        OPCIONAL = "opcional", "Opcional"

    class Rol(models.TextChoices):
        ACTIVIDAD = "actividad", "Actividad"
        COMPLEMENTARIA = "complementaria", "Complementaria"

    formula = models.ForeignKey(
        FormulaAmbiental, on_delete=models.CASCADE, related_name="variables"
    )
    clave = models.SlugField(max_length=100)
    concepto_observacion = models.SlugField(max_length=120)
    unidad_esperada = models.CharField(max_length=40)
    obligatoria = models.BooleanField(default=True)
    criticidad = models.CharField(
        max_length=20, choices=Criticidad.choices, default=Criticidad.CRITICA
    )
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.ACTIVIDAD)
    descripcion = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["formula", "clave"], name="unique_variable_formula"
            )
        ]

    def save(self, *args, **kwargs):
        if (
            self.formula.version_metodologia.estado
            != VersionMetodologia.Estado.BORRADOR
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Las variables de una metodologia activa son inmutables; cree una nueva version."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if (
            self.formula.version_metodologia.estado
            != VersionMetodologia.Estado.BORRADOR
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Las variables de una metodologia activa no pueden eliminarse."
            )
        return super().delete(*args, **kwargs)


@receiver(pre_delete, sender=FormulaAmbiental)
def proteger_eliminacion_formula_activa(sender, instance, **kwargs):
    if instance.version_metodologia.estado != VersionMetodologia.Estado.BORRADOR:
        from django.core.exceptions import ValidationError

        raise ValidationError(
            "La formula de una metodologia activa no puede eliminarse."
        )


@receiver(pre_delete, sender=VariableFormula)
def proteger_eliminacion_variable_activa(sender, instance, **kwargs):
    if (
        instance.formula.version_metodologia.estado
        != VersionMetodologia.Estado.BORRADOR
    ):
        from django.core.exceptions import ValidationError

        raise ValidationError(
            "Las variables de una metodologia activa no pueden eliminarse."
        )


@receiver(pre_delete, sender=VersionMetodologia)
def proteger_eliminacion_version_metodologia(sender, instance, **kwargs):
    if instance.estado in {
        instance.Estado.VALIDADA,
        instance.Estado.ACTIVA,
        instance.Estado.OBSOLETA,
    }:
        from django.core.exceptions import ValidationError

        raise ValidationError("Una versión metodológica gobernada no puede eliminarse.")


@receiver(pre_delete, sender=VersionFactorAmbiental)
def proteger_eliminacion_version_factor(sender, instance, **kwargs):
    if instance.estado in {
        instance.Estado.VALIDADO,
        instance.Estado.ACTIVO,
        instance.Estado.OBSOLETO,
    }:
        from django.core.exceptions import ValidationError

        raise ValidationError("Una versión gobernada del factor no puede eliminarse.")


class CalculoAmbiental(models.Model):
    class Estado(models.TextChoices):
        FINALIZADO = "finalizado", "Finalizado"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        FALLIDO = "fallido", "Fallido"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.PROTECT, related_name="calculos_ambientales_v2"
    )
    actividad = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.PROTECT,
        related_name="calculos_ambientales",
    )
    version_metodologia = models.ForeignKey(
        VersionMetodologia, on_delete=models.PROTECT, related_name="calculos"
    )
    formula = models.ForeignKey(
        FormulaAmbiental, on_delete=models.PROTECT, related_name="calculos"
    )
    version_factor = models.ForeignKey(
        VersionFactorAmbiental, on_delete=models.PROTECT, related_name="calculos"
    )
    resultado = models.DecimalField(max_digits=24, decimal_places=10)
    unidad_resultado = models.CharField(max_length=60)
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.FINALIZADO
    )
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    version_interna = models.PositiveIntegerField(default=1)
    formula_aplicada = models.CharField(max_length=300)
    advertencias = models.JSONField(default=list, blank=True)
    completitud = models.CharField(max_length=30)
    snapshot_tecnico = models.JSONField(default=dict, blank=True)
    tipo_resultado = models.CharField(max_length=30, default="emision")
    recalculo_de = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recalculos",
    )
    motivo_recalculo = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha_calculo"]

    def save(self, *args, **kwargs):
        if self.pk and CalculoAmbiental.objects.filter(pk=self.pk).exists():
            from django.core.exceptions import ValidationError

            raise ValidationError("Un calculo finalizado es inmutable; cree uno nuevo.")
        super().save(*args, **kwargs)


class CompatibilidadVersionMetodologia(models.Model):
    class Estado(models.TextChoices):
        COMPATIBLE = "compatible", "Compatible"
        INCOMPATIBLE = "incompatible", "Incompatible"
        REQUIERE_REVISION = "requiere_revision", "Requiere revisión"

    version_origen = models.ForeignKey(
        VersionMetodologia,
        on_delete=models.CASCADE,
        related_name="compatibilidades_origen",
    )
    version_destino = models.ForeignKey(
        VersionMetodologia,
        on_delete=models.CASCADE,
        related_name="compatibilidades_destino",
    )
    estado = models.CharField(max_length=30, choices=Estado.choices)
    detalle = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["version_origen", "version_destino"],
                name="unique_compatibilidad_version_metodologia",
            )
        ]


class InputCalculoAmbiental(models.Model):
    calculo = models.ForeignKey(
        CalculoAmbiental, on_delete=models.PROTECT, related_name="inputs"
    )
    variable = models.ForeignKey(
        VariableFormula, on_delete=models.PROTECT, related_name="inputs_calculo"
    )
    observacion = models.ForeignKey(
        Observacion, on_delete=models.PROTECT, related_name="inputs_calculo"
    )
    valor_utilizado = models.DecimalField(max_digits=20, decimal_places=10)
    unidad = models.CharField(max_length=40)
    concepto = models.SlugField(max_length=120)
    fuente = models.ForeignKey(
        FuenteDatos, on_delete=models.PROTECT, related_name="inputs_calculo"
    )
    evidencia = models.ForeignKey(
        EvidenciaObra,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inputs_calculo",
    )
    version_evidencia = models.ForeignKey(
        VersionEvidencia,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inputs_calculo",
    )


class ImpactoAmbiental(models.Model):
    class Tipo(models.TextChoices):
        GENERADO = "generado", "Generado"
        REDUCCION = "reduccion", "Reduccion"
        EVITADO = "evitado", "Evitado"
        CAPTURA_REMOCION = "captura_remocion", "Captura/remocion"
        COMPENSACION = "compensacion", "Compensacion"
        OTRO = "otro", "Otro"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.PROTECT, related_name="impactos_ambientales_v2"
    )
    actividad = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.PROTECT,
        related_name="impactos_ambientales",
    )
    calculo = models.OneToOneField(
        CalculoAmbiental, on_delete=models.PROTECT, related_name="impacto"
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.GENERADO)
    categoria = models.CharField(max_length=80)
    valor = models.DecimalField(max_digits=24, decimal_places=10)
    unidad = models.CharField(max_length=60)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class EvaluacionCalidadDato(models.Model):
    class Estado(models.TextChoices):
        CONFIABLE = "confiable", "Confiable"
        CONFIABLE_OBSERVACIONES = (
            "confiable_con_observaciones",
            "Confiable con observaciones",
        )
        INCOMPLETO = "incompleto", "Incompleto"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        NO_CONFIABLE = "no_confiable", "No confiable"
        NO_CALCULABLE = "no_calculable", "No calculable"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="evaluaciones_calidad"
    )
    observacion = models.ForeignKey(
        Observacion, on_delete=models.PROTECT, related_name="evaluaciones_calidad"
    )
    estado = models.CharField(max_length=40, choices=Estado.choices, db_index=True)
    motivos = models.JSONField(default=list, blank=True)
    dimensiones = models.JSONField(default=dict, blank=True)
    fecha_evaluacion = models.DateTimeField(auto_now_add=True)
    version_reglas = models.CharField(max_length=30, default="calidad-v1")
    automatica = models.BooleanField(default=True)
    evaluado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluaciones_calidad",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.observacion_id
            and self.observacion.organizacion_id != self.organizacion_id
        ):
            raise ValidationError(
                {"observacion": "La observacion pertenece a otra organizacion."}
            )


class DiscrepanciaDato(models.Model):
    class Estado(models.TextChoices):
        DETECTADA = "detectada", "Detectada"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        RESUELTA = "resuelta", "Resuelta"
        ACEPTADA = "aceptada", "Aceptada"
        DESCARTADA = "descartada", "Descartada"

    class Severidad(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="discrepancias_dato"
    )
    actividad = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discrepancias",
    )
    concepto = models.SlugField(max_length=120, db_index=True)
    observaciones = models.ManyToManyField(Observacion, related_name="discrepancias")
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.DETECTADA
    )
    diferencia_absoluta = models.DecimalField(
        max_digits=24, decimal_places=10, null=True, blank=True
    )
    diferencia_relativa = models.DecimalField(
        max_digits=16, decimal_places=8, null=True, blank=True
    )
    severidad = models.CharField(
        max_length=15, choices=Severidad.choices, default=Severidad.MEDIA
    )
    resolucion = models.TextField(blank=True)
    observacion_seleccionada = models.ForeignKey(
        Observacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="discrepancias_seleccionada",
    )
    motivo = models.TextField(blank=True)
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discrepancias_responsable",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.actividad_id and self.actividad.organizacion_id != self.organizacion_id:
            raise ValidationError(
                {"actividad": "La actividad pertenece a otra organizacion."}
            )
        if (
            self.observacion_seleccionada_id
            and self.observacion_seleccionada.organizacion_id != self.organizacion_id
        ):
            raise ValidationError(
                {
                    "observacion_seleccionada": "La observacion pertenece a otra organizacion."
                }
            )


class PoliticaConfianzaFuente(models.Model):
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="politicas_confianza_fuente",
    )
    concepto = models.SlugField(max_length=120)
    tipo_fuente = models.CharField(max_length=30, choices=FuenteDatos.Tipo.choices)
    prioridad = models.PositiveIntegerField()
    activa = models.BooleanField(default=True)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["concepto", "tipo_fuente"],
                condition=Q(organizacion__isnull=True),
                name="unique_politica_fuente_global",
            ),
            models.UniqueConstraint(
                fields=["organizacion", "concepto", "tipo_fuente"],
                condition=Q(organizacion__isnull=False),
                name="unique_politica_fuente_tenant",
            ),
        ]


class IndicadorAmbiental(models.Model):
    class Tipo(models.TextChoices):
        ABSOLUTO = "absoluto", "Absoluto"
        INTENSIDAD = "intensidad", "Intensidad"
        OPERACIONAL = "operacional", "Operacional"
        PROBLEMATICA = "problematica", "Problematica"

    class DireccionDeseable(models.TextChoices):
        MENOR = "menor_es_mejor", "Menor es mejor"
        MAYOR = "mayor_es_mejor", "Mayor es mejor"
        NEUTRAL = "neutral", "Neutral"

    class Alcance(models.TextChoices):
        ORGANIZACION = "organizacion", "Organizacion"
        OBRA = "obra", "Obra"

    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="indicadores_ambientales_v2",
    )
    alcance = models.CharField(
        max_length=20,
        choices=Alcance.choices,
        default=Alcance.ORGANIZACION,
        db_index=True,
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="indicadores_ambientales",
    )
    codigo = models.SlugField(max_length=120)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    unidad = models.CharField(max_length=60)
    descripcion = models.TextField(blank=True)
    origen_numerador = models.CharField(max_length=120)
    origen_denominador = models.CharField(max_length=120, blank=True)
    direccion_deseable = models.CharField(
        max_length=25,
        choices=DireccionDeseable.choices,
        default=DireccionDeseable.NEUTRAL,
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "codigo"],
                condition=Q(alcance="organizacion"),
                name="unique_indicador_codigo_organizacion",
            ),
            models.UniqueConstraint(
                fields=["organizacion", "obra", "codigo"],
                condition=Q(alcance="obra"),
                name="unique_indicador_codigo_obra",
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if self.alcance == self.Alcance.OBRA and not self.obra_id:
            errors["obra"] = "El indicador con alcance obra requiere una obra."
        if self.alcance == self.Alcance.ORGANIZACION and self.obra_id:
            errors["obra"] = (
                "Un indicador corporativo no puede quedar asociado a una obra."
            )
        if self.obra_id and self.obra.organizacion_id != self.organizacion_id:
            errors["obra"] = "La obra debe pertenecer a la organizacion."
        if errors:
            raise ValidationError(errors)


class ValorIndicador(models.Model):
    indicador = models.ForeignKey(
        IndicadorAmbiental, on_delete=models.PROTECT, related_name="valores"
    )
    periodo_inicio = models.DateField(db_index=True)
    periodo_fin = models.DateField()
    valor = models.DecimalField(max_digits=24, decimal_places=10)
    unidad = models.CharField(max_length=60)
    fuente_calculo = models.CharField(max_length=160)
    version = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["periodo_inicio", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["indicador", "periodo_inicio", "periodo_fin", "version"],
                name="unique_valor_indicador_version",
            )
        ]


class LineaBaseAmbiental(models.Model):
    class Estado(models.TextChoices):
        CONSTRUYENDO = "construyendo", "Construyendo"
        SUFICIENTE = "suficiente", "Suficiente"
        REQUIERE_REVISION = "requiere_revision", "Requiere revision"
        CERRADA = "cerrada", "Cerrada"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="lineas_base_ambientales"
    )
    indicador = models.ForeignKey(
        IndicadorAmbiental, on_delete=models.PROTECT, related_name="lineas_base"
    )
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)
    metodo = models.CharField(max_length=80, default="promedio_periodos")
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.CONSTRUYENDO
    )
    valor_base = models.DecimalField(
        max_digits=24, decimal_places=10, null=True, blank=True
    )
    cantidad_periodos = models.PositiveIntegerField(default=0)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.indicador_id and self.indicador.organizacion_id != self.organizacion_id:
            raise ValidationError(
                {"indicador": "El indicador pertenece a otra organizacion."}
            )


class PeriodoComparable(models.Model):
    class Regla(models.TextChoices):
        MISMO_MES_ANTERIOR = "mismo_mes_anio_anterior", "Mismo mes del ano anterior"
        ANTERIOR_EQUIVALENTE = (
            "periodo_anterior_equivalente",
            "Periodo anterior equivalente",
        )
        MANUAL = "manual", "Manual"

    indicador = models.ForeignKey(
        IndicadorAmbiental,
        on_delete=models.CASCADE,
        related_name="periodos_comparables",
    )
    periodo_actual_inicio = models.DateField()
    periodo_actual_fin = models.DateField()
    periodo_referencia_inicio = models.DateField()
    periodo_referencia_fin = models.DateField()
    regla = models.CharField(max_length=40, choices=Regla.choices)
    motivo_comparabilidad = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["indicador", "periodo_actual_inicio", "periodo_actual_fin"],
                name="unique_periodo_comparable_indicador",
            )
        ]


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


class ProblematicaAmbiental(models.Model):
    class Estado(models.TextChoices):
        DETECTADA = "detectada", "Detectada"
        ANALIZANDO = "analizando", "Analizando"
        PROPUESTA = "propuesta", "Propuesta"
        ACCION_SELECCIONADA = "accion_seleccionada", "Accion seleccionada"
        IMPLEMENTANDO = "implementando", "Implementando"
        SEGUIMIENTO = "seguimiento", "Seguimiento"
        EVALUANDO = "evaluando", "Evaluando"
        ESCALADA_PROFESIONAL = "escalada_profesional", "Escalada profesional"
        CERRADA = "cerrada", "Cerrada"
        # Estados legacy preservados.
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

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="problematicas_ambientales"
    )
    titulo = models.CharField(max_length=240)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=120)
    indicador = models.CharField(max_length=120, default="co2e_total_kg")
    unidad_indicador = models.CharField(max_length=40, default="kgCO2e")
    obra = models.ForeignKey(
        Obra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problematicas_ambientales",
    )
    area_operacional = models.CharField(max_length=180, blank=True)
    unidad_operacional = models.CharField(max_length=180, blank=True)
    valor_inicial = models.DecimalField(max_digits=18, decimal_places=6)
    objetivo_meta = models.DecimalField(max_digits=18, decimal_places=6)
    valor_posterior = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    mejora_absoluta = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    mejora_porcentaje = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True
    )
    fecha_deteccion = models.DateField()
    nivel_riesgo = models.CharField(
        max_length=20, choices=Riesgo.choices, default=Riesgo.MEDIO
    )
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.DETECTADA
    )
    resultado_evaluacion = models.CharField(
        max_length=30, choices=Resultado.choices, default=Resultado.PENDIENTE
    )
    requiere_evaluacion_profesional = models.BooleanField(default=False, db_index=True)
    criterios_escalamiento = models.JSONField(default=list, blank=True)
    escalada_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    origen_deteccion = models.CharField(max_length=40, default="manual")
    responsable_usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problematicas_responsable",
    )
    objetivo_ambiental = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_deteccion", "-created_at"]
        indexes = [
            models.Index(fields=["organizacion", "estado"]),
            models.Index(fields=["organizacion", "categoria"]),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.obra_id and self.obra.organizacion_id != self.organizacion_id:
            raise ValidationError({"obra": "Debe pertenecer a la organizacion."})


class AccionMejoraAmbiental(models.Model):
    class Estado(models.TextChoices):
        PROPUESTA = "propuesta", "Propuesta"
        AJUSTADA = "ajustada", "Ajustada"
        SELECCIONADA = "seleccionada", "Seleccionada"
        EN_IMPLEMENTACION = "en_implementacion", "En implementacion"
        SEGUIMIENTO = "seguimiento", "Seguimiento"
        EVALUADA = "evaluada", "Evaluada"
        DESCARTADA = "descartada", "Descartada"
        CANCELADA = "cancelada", "Cancelada"

    problematica = models.ForeignKey(
        ProblematicaAmbiental, on_delete=models.CASCADE, related_name="acciones"
    )
    titulo = models.CharField(max_length=240)
    descripcion = models.TextField()
    justificacion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.PROPUESTA
    )
    fecha_propuesta = models.DateField(default=timezone.localdate)
    fecha_seleccion = models.DateField(null=True, blank=True)
    fecha_inicio_efectiva = models.DateField(null=True, blank=True)
    fecha_termino_real = models.DateField(null=True, blank=True)
    responsable_usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_mejora_responsable",
    )
    observaciones = models.TextField(blank=True)
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
    problematica = models.ForeignKey(
        ProblematicaAmbiental, on_delete=models.CASCADE, related_name="mediciones"
    )
    accion = models.ForeignKey(
        AccionMejoraAmbiental,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mediciones",
    )
    fecha = models.DateField()
    valor = models.DecimalField(max_digits=18, decimal_places=6)
    unidad = models.CharField(max_length=40)
    fuente = models.CharField(max_length=120, default="manual")
    indicador_v2 = models.ForeignKey(
        "IndicadorAmbiental",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mediciones_intervencion",
    )
    valor_indicador = models.ForeignKey(
        "ValorIndicador",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mediciones_intervencion",
    )
    referencia = models.CharField(max_length=240, blank=True)
    observaciones = models.TextField(blank=True)
    evidencia = models.ForeignKey(
        "EvidenciaObra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mediciones_intervencion",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        organization_id = self.problematica.organizacion_id
        if self.accion_id and self.accion.problematica_id != self.problematica_id:
            raise ValidationError(
                {"accion": "La accion pertenece a otra problematica."}
            )
        if (
            self.indicador_v2_id
            and self.indicador_v2.organizacion_id != organization_id
        ):
            raise ValidationError(
                {"indicador_v2": "El indicador pertenece a otra organizacion."}
            )
        if self.evidencia_id and self.evidencia.organizacion_id != organization_id:
            raise ValidationError(
                {"evidencia": "La evidencia pertenece a otra organizacion."}
            )


class AlcanceProblematica(models.Model):
    problematica = models.ForeignKey(
        ProblematicaAmbiental, on_delete=models.CASCADE, related_name="alcances_v2"
    )
    unidad_operacional = models.ForeignKey(
        UnidadOperacional,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="alcances_problematicas",
    )
    proceso_operacional = models.ForeignKey(
        ProcesoOperacional,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="alcances_problematicas",
    )
    activo_operacional = models.ForeignKey(
        ActivoOperacional,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="alcances_problematicas",
    )
    actividad_operacional = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="alcances_problematicas",
    )
    indicador = models.ForeignKey(
        IndicadorAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="alcances_problematicas",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        organization_id = self.problematica.organizacion_id
        if not any(
            [
                self.unidad_operacional_id,
                self.proceso_operacional_id,
                self.activo_operacional_id,
                self.actividad_operacional_id,
                self.indicador_id,
            ]
        ):
            raise ValidationError("El alcance debe contener al menos una referencia.")
        for field in (
            "unidad_operacional",
            "proceso_operacional",
            "activo_operacional",
            "actividad_operacional",
            "indicador",
        ):
            relation = getattr(self, field, None)
            if relation and relation.organizacion_id != organization_id:
                raise ValidationError(
                    {field: "La referencia pertenece a otra organizacion."}
                )


class IndicadorProblematica(models.Model):
    class Rol(models.TextChoices):
        PRINCIPAL = "principal", "Principal"
        SECUNDARIO = "secundario", "Secundario"
        CONTEXTO = "contexto", "Contexto"

    problematica = models.ForeignKey(
        ProblematicaAmbiental, on_delete=models.CASCADE, related_name="indicadores_v2"
    )
    indicador = models.ForeignKey(
        IndicadorAmbiental, on_delete=models.PROTECT, related_name="problematicas_v2"
    )
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.PRINCIPAL)
    valor_objetivo = models.DecimalField(
        max_digits=24, decimal_places=10, null=True, blank=True
    )
    direccion_deseada = models.CharField(
        max_length=25, choices=IndicadorAmbiental.DireccionDeseable.choices
    )
    obligatorio = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["orden", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["problematica", "indicador"],
                name="unique_indicador_problematica",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.indicador_id
            and self.indicador.organizacion_id != self.problematica.organizacion_id
        ):
            raise ValidationError(
                {"indicador": "El indicador pertenece a otra organizacion."}
            )


class SnapshotIntervencion(models.Model):
    class Tipo(models.TextChoices):
        BASE = "base", "Base"
        RESULTADO = "resultado", "Resultado"

    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.PROTECT,
        related_name="snapshots_intervencion",
    )
    accion = models.ForeignKey(
        AccionMejoraAmbiental,
        on_delete=models.PROTECT,
        related_name="snapshots_intervencion",
    )
    ciclo = models.PositiveIntegerField(default=1)
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    fecha = models.DateField()
    alcance_congelado = models.JSONField(default=dict)
    indicadores_evaluados = models.JSONField(default=list)
    metadata_tecnica = models.JSONField(default=dict, blank=True)
    congelado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["problematica", "accion", "ciclo", "tipo"],
                name="unique_snapshot_intervencion_ciclo",
            )
        ]

    def save(self, *args, **kwargs):
        if (
            self.pk
            and SnapshotIntervencion.objects.filter(pk=self.pk, congelado=True).exists()
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError("Un snapshot congelado es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.congelado:
            from django.core.exceptions import ValidationError

            raise ValidationError("Un snapshot congelado no puede eliminarse.")
        return super().delete(*args, **kwargs)


class SnapshotValorIndicador(models.Model):
    snapshot = models.ForeignKey(
        SnapshotIntervencion, on_delete=models.PROTECT, related_name="valores"
    )
    indicador = models.ForeignKey(
        IndicadorAmbiental, on_delete=models.PROTECT, related_name="valores_snapshot"
    )
    valor = models.DecimalField(max_digits=24, decimal_places=10)
    unidad = models.CharField(max_length=60)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    valor_indicador_origen = models.ForeignKey(
        ValorIndicador,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="snapshots_intervencion",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "indicador"], name="unique_valor_snapshot_indicador"
            )
        ]

    def save(self, *args, **kwargs):
        if self.snapshot.congelado:
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Los valores de un snapshot congelado son inmutables."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.snapshot.congelado:
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Los valores de un snapshot congelado no pueden eliminarse."
            )
        return super().delete(*args, **kwargs)


class ResultadoIntervencion(models.Model):
    class Estado(models.TextChoices):
        NO_IMPLEMENTADA = "no_implementada", "No implementada"
        NO_VIABLE = "no_viable", "No viable"
        PARCIAL = "parcial", "Parcial"
        SIN_EFECTO = "implementada_sin_efecto", "Implementada sin efecto"
        POSITIVA = "positiva", "Positiva"
        NEGATIVA = "negativa", "Negativa"
        INCONCLUSA = "inconclusa", "Inconclusa"

    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.PROTECT,
        related_name="resultados_intervencion",
    )
    accion = models.ForeignKey(
        AccionMejoraAmbiental,
        on_delete=models.PROTECT,
        related_name="resultados_intervencion",
    )
    ciclo = models.PositiveIntegerField()
    snapshot_base = models.ForeignKey(
        SnapshotIntervencion,
        on_delete=models.PROTECT,
        related_name="resultados_como_base",
    )
    snapshot_resultado = models.ForeignKey(
        SnapshotIntervencion,
        on_delete=models.PROTECT,
        related_name="resultados_como_resultado",
    )
    estado = models.CharField(max_length=35, choices=Estado.choices)
    conclusion_estructurada = models.JSONField(default=dict)
    fecha_evaluacion = models.DateField()
    metricas_comparadas = models.JSONField(default=list)
    limitaciones = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["problematica", "accion", "ciclo"],
                name="unique_resultado_intervencion_ciclo",
            )
        ]


class CicloReevaluacionProblematica(models.Model):
    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.PROTECT,
        related_name="ciclos_reevaluacion",
    )
    numero = models.PositiveSmallIntegerField()
    accion = models.ForeignKey(
        AccionMejoraAmbiental,
        on_delete=models.PROTECT,
        related_name="ciclos_reevaluacion",
    )
    snapshot_base = models.ForeignKey(
        SnapshotIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ciclos_como_base",
    )
    snapshot_resultado = models.ForeignKey(
        SnapshotIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ciclos_como_resultado",
    )
    resultado = models.ForeignKey(
        ResultadoIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ciclo_reevaluacion",
    )
    fecha_inicio = models.DateField()
    fecha_cierre = models.DateField(null=True, blank=True)
    motivo = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["problematica", "numero"], name="unique_ciclo_problematica"
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.numero > 3:
            raise ValidationError(
                {"numero": "No se permite un cuarto ciclo automatico."}
            )
        if self.accion_id and self.accion.problematica_id != self.problematica_id:
            raise ValidationError(
                {"accion": "La accion pertenece a otra problematica."}
            )


class HistorialMetaProblematica(models.Model):
    problematica = models.ForeignKey(
        ProblematicaAmbiental, on_delete=models.PROTECT, related_name="historial_metas"
    )
    indicador_problematica = models.ForeignKey(
        IndicadorProblematica, on_delete=models.PROTECT, related_name="historial_metas"
    )
    valor_anterior = models.DecimalField(
        max_digits=24, decimal_places=10, null=True, blank=True
    )
    valor_nuevo = models.DecimalField(max_digits=24, decimal_places=10)
    justificacion_tecnica = models.TextField()
    motivo = models.TextField()
    usuario = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="cambios_meta_problematica"
    )
    fecha = models.DateTimeField(auto_now_add=True)


class HistorialProblematicaAmbiental(models.Model):
    problematica = models.ForeignKey(
        ProblematicaAmbiental, on_delete=models.CASCADE, related_name="historial"
    )
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

    class Estado(models.TextChoices):
        PROPUESTA = "propuesta", "Propuesta"
        AJUSTADA = "ajustada", "Ajustada"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        DESCARTADA = "descartada", "Descartada"
        CONVERTIDA = "convertida_en_accion", "Convertida en accion"

    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.CASCADE,
        related_name="recomendaciones_agente",
    )
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
    titulo = models.CharField(max_length=240, blank=True)
    descripcion = models.TextField(blank=True)
    requisitos = models.JSONField(default=list, blank=True)
    riesgos = models.JSONField(default=list, blank=True)
    restricciones_consideradas = models.JSONField(default=list, blank=True)
    kpis_afectados = models.JSONField(default=list, blank=True)
    referencias_contexto = models.JSONField(default=list, blank=True)
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.PROPUESTA
    )
    version = models.PositiveIntegerField(default=1)
    propuesta_anterior = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="ajustes"
    )
    mensaje_usuario = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["problematica", "prioridad"])]


class MemoriaOrganizacion(models.Model):
    class Tipo(models.TextChoices):
        SOLUCION_INTENTADA = "solucion_intentada", "Solucion intentada"
        ACCION_ACEPTADA = "accion_aceptada", "Accion aceptada"
        ACCION_RECHAZADA = "accion_rechazada", "Accion rechazada"
        RESTRICCION = "restriccion_operacional", "Restriccion operacional"
        ACTIVO_PROBLEMATICO = "activo_problematico", "Activo problematico"
        PROCESO_RECURRENT = "proceso_recurrente", "Proceso recurrente"
        EVOLUCION_KPI = "evolucion_kpi", "Evolucion KPI"
        INTERVENCION = "intervencion", "Intervencion"
        CAMBIO_OPERACIONAL = "cambio_operacional", "Cambio operacional"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="memoria_organizacional"
    )
    tipo = models.CharField(max_length=40, choices=Tipo.choices, db_index=True)
    contenido = models.JSONField(default=dict)
    fuente_origen = models.CharField(max_length=80)
    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memorias_organizacionales",
    )
    vigente_desde = models.DateTimeField(default=timezone.now)
    vigente_hasta = models.DateTimeField(null=True, blank=True)
    contexto = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.problematica_id
            and self.problematica.organizacion_id != self.organizacion_id
        ):
            raise ValidationError(
                {"problematica": "La problematica pertenece a otra organizacion."}
            )


class RestriccionContextual(models.Model):
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="restricciones_contextuales",
    )
    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restricciones_contextuales",
    )
    tipo = models.SlugField(max_length=80)
    descripcion = models.TextField()
    contenido = models.JSONField(default=dict, blank=True)
    vigente_desde = models.DateTimeField(default=timezone.now)
    vigente_hasta = models.DateTimeField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restricciones_contextuales",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.problematica_id
            and self.problematica.organizacion_id != self.organizacion_id
        ):
            raise ValidationError(
                {"problematica": "La problematica pertenece a otra organizacion."}
            )


class HistorialRestriccionContextual(models.Model):
    restriccion = models.ForeignKey(
        RestriccionContextual, on_delete=models.PROTECT, related_name="historial"
    )
    contenido_anterior = models.JSONField(default=dict)
    contenido_nuevo = models.JSONField(default=dict)
    motivo = models.TextField()
    usuario = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="historial_restricciones"
    )
    created_at = models.DateTimeField(auto_now_add=True)


class HitoDecisionIA(models.Model):
    class Tipo(models.TextChoices):
        CONTEXTO = "contexto_consultado", "Contexto consultado"
        PROPUESTA = "propuesta", "Propuesta"
        REFUTACION = "refutacion", "Refutacion"
        ADAPTACION = "adaptacion", "Adaptacion"
        PROPUESTA_FINAL = "propuesta_final", "Propuesta final"
        DECISION = "decision_humana", "Decision humana"
        RESULTADO = "resultado_posterior", "Resultado posterior"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="hitos_decision_ia"
    )
    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.CASCADE,
        related_name="hitos_decision_ia",
    )
    propuesta = models.ForeignKey(
        RecomendacionAgenteAmbiental,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hitos",
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    resumen = models.TextField()
    referencias_contexto = models.JSONField(default=list, blank=True)
    payload_auditable = models.JSONField(default=dict, blank=True)
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hitos_decision_ia",
    )
    created_at = models.DateTimeField(auto_now_add=True)


class ComandoCopiloto(models.Model):
    class Tipo(models.TextChoices):
        ACCION = "prepare_action", "Preparar accion"
        REEVALUACION = "prepare_reevaluation", "Preparar reevaluacion"
        RESTRICCION = "prepare_restriction", "Preparar restriccion"
        ESCALAMIENTO = "prepare_escalation", "Preparar escalamiento"

    class Estado(models.TextChoices):
        PREPARADO = "preparado", "Preparado"
        CONFIRMADO = "confirmado", "Confirmado"
        RECHAZADO = "rechazado", "Rechazado"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="comandos_copiloto"
    )
    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.CASCADE,
        related_name="comandos_copiloto",
    )
    propuesta = models.ForeignKey(
        RecomendacionAgenteAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="comandos",
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    payload = models.JSONField(default=dict)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PREPARADO
    )
    confirmado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comandos_copiloto_confirmados",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)


class ExpedienteAmbiental(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = "abierto", "Abierto"
        RECOPILANDO = "recopilando_antecedentes", "Recopilando antecedentes"
        EN_REVISION = "en_revision", "En revision"
        REQUIERE_ANTECEDENTES = "requiere_antecedentes", "Requiere antecedentes"
        VALIDADO = "validado", "Validado"
        CERRADO = "cerrado", "Cerrado"
        REABIERTO = "reabierto", "Reabierto"

    problematica = models.ForeignKey(
        ProblematicaAmbiental, on_delete=models.CASCADE, related_name="expedientes"
    )
    version = models.PositiveIntegerField(default=1)
    contenido_procesado = models.JSONField(default=dict)
    resumen_ejecutivo = models.TextField()
    proveedor_resumen = models.CharField(max_length=80, blank=True)
    modelo_resumen = models.CharField(max_length=120, blank=True)
    generado_por = models.CharField(max_length=150, blank=True)
    estado = models.CharField(
        max_length=35, choices=Estado.choices, default=Estado.ABIERTO
    )
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_ambientales_responsable",
    )
    referencias = models.JSONField(default=dict, blank=True)
    cerrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_ambientales_cerrados",
    )
    cerrado_at = models.DateTimeField(null=True, blank=True)
    reabierto_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_ambientales_reabiertos",
    )
    reabierto_at = models.DateTimeField(null=True, blank=True)
    motivo_reapertura = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["problematica", "version"],
                name="unique_expediente_problematica_version",
            )
        ]


class RevisionProfesionalAmbiental(models.Model):
    class Tipo(models.TextChoices):
        EVIDENCIA = "evidencia", "Evidencia"
        OBSERVACION = "observacion", "Observacion"
        CALCULO = "calculo", "Calculo"
        INDICADOR = "indicador", "Indicador"
        PROBLEMATICA = "problematica", "Problematica"
        INTERVENCION = "intervencion", "Intervencion"
        EXPEDIENTE = "expediente", "Expediente"
        METODOLOGIA = "metodologia", "Version metodologica"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        VALIDADA = "validada", "Validada"
        VALIDADA_OBSERVACIONES = (
            "validada_con_observaciones",
            "Validada con observaciones",
        )
        SOLICITA_ANTECEDENTES = "solicita_antecedentes", "Solicita antecedentes"
        RECHAZADA = "rechazada", "Rechazada"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="revisiones_profesionales"
    )
    tipo = models.CharField(max_length=25, choices=Tipo.choices)
    evidencia = models.ForeignKey(
        EvidenciaObra,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    observacion = models.ForeignKey(
        Observacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    calculo = models.ForeignKey(
        CalculoAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    indicador = models.ForeignKey(
        IndicadorAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    intervencion = models.ForeignKey(
        ResultadoIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    expediente = models.ForeignKey(
        ExpedienteAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    version_metodologia = models.ForeignKey(
        VersionMetodologia,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    estado = models.CharField(
        max_length=35, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    profesional = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisiones_profesionales",
    )
    profesional_nombre = models.CharField(max_length=180, blank=True)
    profesional_cargo = models.CharField(max_length=120, blank=True)
    fecha = models.DateTimeField(null=True, blank=True)
    conclusion = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    antecedentes_solicitados = models.JSONField(default=list, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    REFERENCE_BY_TYPE = {
        Tipo.EVIDENCIA: "evidencia",
        Tipo.OBSERVACION: "observacion",
        Tipo.CALCULO: "calculo",
        Tipo.INDICADOR: "indicador",
        Tipo.PROBLEMATICA: "problematica",
        Tipo.INTERVENCION: "intervencion",
        Tipo.EXPEDIENTE: "expediente",
        Tipo.METODOLOGIA: "version_metodologia",
    }

    def clean(self):
        from django.core.exceptions import ValidationError

        references = {
            field: getattr(self, f"{field}_id")
            for field in self.REFERENCE_BY_TYPE.values()
        }
        populated = [field for field, value in references.items() if value]
        if len(populated) != 1:
            raise ValidationError("La revision debe referenciar exactamente un objeto.")
        expected = self.REFERENCE_BY_TYPE.get(self.tipo)
        if not expected or populated[0] != expected:
            raise ValidationError(
                {"tipo": "El tipo de revision no corresponde al objeto revisado."}
            )
        item = getattr(self, expected)
        owner_id = getattr(item, "organizacion_id", None)
        if isinstance(item, VersionMetodologia):
            owner_id = item.metodologia.organizacion_id
        elif owner_id is None:
            owner_id = item.problematica.organizacion_id
        if (
            self.organizacion_id
            and owner_id is not None
            and owner_id != self.organizacion_id
        ):
            raise ValidationError("El objeto revisado pertenece a otra organizacion.")

    def save(self, *args, **kwargs):
        if (
            self.pk
            and RevisionProfesionalAmbiental.objects.filter(
                pk=self.pk,
                estado__in=[
                    self.Estado.VALIDADA,
                    self.Estado.VALIDADA_OBSERVACIONES,
                    self.Estado.RECHAZADA,
                ],
            ).exists()
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Una revision profesional decidida es inmutable; cree una nueva version."
            )
        self.full_clean()
        super().save(*args, **kwargs)


class HallazgoRevisionProfesional(models.Model):
    class Tipo(models.TextChoices):
        OBSERVACION = "observacion", "Observacion"
        INCONSISTENCIA = "inconsistencia", "Inconsistencia"
        FALTA_ANTECEDENTE = "falta_antecedente", "Falta antecedente"
        CORRECCION = "correccion_requerida", "Correccion requerida"
        VALIDACION = "validacion", "Validacion"
        RECOMENDACION = "recomendacion", "Recomendacion"

    class Severidad(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"
        CRITICA = "critica", "Critica"

    revision = models.ForeignKey(
        RevisionProfesionalAmbiental, on_delete=models.PROTECT, related_name="hallazgos"
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    severidad = models.CharField(
        max_length=15, choices=Severidad.choices, default=Severidad.MEDIA
    )
    observacion = models.TextField()
    recomendacion = models.TextField(blank=True)
    requerimiento = models.TextField(blank=True)
    decision = models.TextField(blank=True)
    referencia_tecnica = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CorreccionHistoricaAmbiental(models.Model):
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="correcciones_historicas"
    )
    observacion_afectada = models.ForeignKey(
        Observacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_historicas",
    )
    calculo_afectado = models.ForeignKey(
        CalculoAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_historicas",
    )
    impacto_afectado = models.ForeignKey(
        ImpactoAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_historicas",
    )
    snapshot_afectado = models.ForeignKey(
        SnapshotIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_historicas",
    )
    resultado_afectado = models.ForeignKey(
        ResultadoIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_historicas",
    )
    motivo = models.TextField()
    valor_estado_anterior = models.JSONField(default=dict)
    propuesta_corregida = models.JSONField(default=dict)
    autor = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="correcciones_historicas"
    )
    fecha = models.DateTimeField(auto_now_add=True)
    revision_origen = models.ForeignKey(
        RevisionProfesionalAmbiental,
        on_delete=models.PROTECT,
        related_name="correcciones_historicas",
    )
    version = models.PositiveIntegerField(default=1)
    recalculo_generado = models.ForeignKey(
        CalculoAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_origen",
    )

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.revision_origen_id
            and self.organizacion_id != self.revision_origen.organizacion_id
        ):
            raise ValidationError(
                {"revision_origen": "La revision origen pertenece a otra organizacion."}
            )

        owners = {
            "observacion_afectada": (
                self.observacion_afectada.organizacion_id
                if self.observacion_afectada_id
                else None
            ),
            "calculo_afectado": (
                self.calculo_afectado.organizacion_id
                if self.calculo_afectado_id
                else None
            ),
            "impacto_afectado": (
                self.impacto_afectado.organizacion_id
                if self.impacto_afectado_id
                else None
            ),
            "snapshot_afectado": (
                self.snapshot_afectado.problematica.organizacion_id
                if self.snapshot_afectado_id
                else None
            ),
            "resultado_afectado": (
                self.resultado_afectado.problematica.organizacion_id
                if self.resultado_afectado_id
                else None
            ),
            "recalculo_generado": (
                self.recalculo_generado.organizacion_id
                if self.recalculo_generado_id
                else None
            ),
        }
        errors = {
            field: "La referencia pertenece a otra organizacion."
            for field, owner_id in owners.items()
            if owner_id is not None and owner_id != self.organizacion_id
        }
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class EventoAuditoriaAmbiental(models.Model):
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.CASCADE,
        related_name="eventos_auditoria_ambiental",
    )
    tipo = models.SlugField(max_length=80, db_index=True)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_auditoria_ambiental",
    )
    entidad = models.CharField(max_length=80)
    referencia = models.CharField(max_length=120)
    resumen = models.TextField()
    metadata_auditable = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp", "-id"]


class InformeAmbiental(models.Model):
    class Tipo(models.TextChoices):
        ACTIVIDAD = "actividad", "Actividad"
        PROBLEMATICA = "problematica", "Problematica"
        INTERVENCION = "intervencion", "Intervencion"
        EXPEDIENTE = "expediente", "Expediente"

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        GENERADO = "generado", "Generado"
        REVISADO = "revisado", "Revisado"
        VALIDADO = "validado", "Validado"
        OBSOLETO = "obsoleto", "Obsoleto"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="informes_ambientales"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    actividad = models.ForeignKey(
        ActividadOperacional,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="informes_ambientales",
    )
    problematica = models.ForeignKey(
        ProblematicaAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="informes_ambientales",
    )
    intervencion = models.ForeignKey(
        ResultadoIntervencion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="informes_ambientales",
    )
    expediente = models.ForeignKey(
        ExpedienteAmbiental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="informes",
    )
    version = models.PositiveIntegerField()
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.BORRADOR
    )
    generado_por = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="informes_ambientales_generados"
    )
    fecha = models.DateTimeField(default=timezone.now)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    archivo = models.FileField(upload_to="informes_ambientales/%Y/%m/", blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    validado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="informes_ambientales_validados",
    )
    validado_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organizacion",
                    "tipo",
                    "actividad",
                    "problematica",
                    "intervencion",
                    "expediente",
                    "version",
                ],
                name="unique_informe_ambiental_version",
            )
        ]

    def save(self, *args, **kwargs):
        if (
            self.pk
            and InformeAmbiental.objects.filter(
                pk=self.pk, estado=self.Estado.VALIDADO
            ).exists()
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Un informe validado es inmutable; genere una nueva version."
            )
        super().save(*args, **kwargs)


class SnapshotInformeAmbiental(models.Model):
    informe = models.OneToOneField(
        InformeAmbiental, on_delete=models.PROTECT, related_name="snapshot"
    )
    contenido = models.JSONField(default=dict)
    referencias = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            from django.core.exceptions import ValidationError

            raise ValidationError("El snapshot de informe es inmutable.")
        super().save(*args, **kwargs)


class CasoConocimientoAmbiental(models.Model):
    class Resultado(models.TextChoices):
        EXITOSO = "exitoso", "Exitoso"
        PARCIAL = "parcialmente_exitoso", "Parcialmente exitoso"
        SIN_EFECTO = "sin_efecto", "Sin efecto"
        NEGATIVO = "negativo", "Negativo"
        NO_VIABLE = "no_viable", "No viable"
        NO_IMPLEMENTADO = "no_implementado", "No implementado"
        INCONCLUSO = "inconcluso", "Inconcluso"

    class Fuerza(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"

    class Origen(models.TextChoices):
        IA = "ia", "IA"
        PROFESIONAL = "profesional", "Profesional"
        USUARIO = "usuario", "Usuario"
        MIXTO = "mixto", "Mixto"

    class Estado(models.TextChoices):
        CANDIDATO = "candidato", "Candidato"
        UTILIZABLE = "utilizable", "Utilizable"
        DESCARTADO = "descartado", "Descartado"
        INVALIDADO = "invalidado", "Invalidado"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="casos_conocimiento"
    )
    resultado_origen = models.ForeignKey(
        ResultadoIntervencion,
        on_delete=models.PROTECT,
        related_name="casos_conocimiento",
    )
    preset = models.CharField(max_length=40, db_index=True)
    tipo_problematica = models.SlugField(max_length=120, db_index=True)
    categoria_ambiental = models.SlugField(max_length=120, db_index=True)
    tipo_accion = models.SlugField(max_length=120, db_index=True)
    contexto_operacional = models.JSONField(default=dict)
    indicadores = models.JSONField(default=list, blank=True)
    resultado = models.CharField(
        max_length=30, choices=Resultado.choices, db_index=True
    )
    metricas_comparadas = models.JSONField(default=list)
    grado_implementacion = models.CharField(max_length=30)
    viabilidad = models.CharField(max_length=30)
    fuerza_evidencia = models.CharField(
        max_length=10, choices=Fuerza.choices, db_index=True
    )
    fundamento_evidencia = models.JSONField(default=list)
    origen_conocimiento = models.CharField(max_length=20, choices=Origen.choices)
    fecha_caso = models.DateField()
    version = models.PositiveIntegerField(default=1)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.CANDIDATO, db_index=True
    )
    fingerprint = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_caso", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["resultado_origen", "version"],
                name="unique_caso_conocimiento_version",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.resultado_origen_id
            and self.resultado_origen.problematica.organizacion_id
            != self.organizacion_id
        ):
            raise ValidationError(
                {"resultado_origen": "La intervencion pertenece a otra organizacion."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
