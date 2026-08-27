from decimal import Decimal

from django.db import models
from django.db.models import Sum

from .platform import Organizacion, UsuarioOrganizacion
from .utils import unique_code


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
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="etapas"
    )
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(max_length=40, choices=Tipo.choices, default=Tipo.OTRO)
    region = models.CharField(max_length=120, blank=True)
    comuna = models.CharField(max_length=120, blank=True)
    direccion = models.CharField(max_length=240, blank=True)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.ACTIVA
    )
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organizacion__nombre", "nombre"]

    def save(self, *args, **kwargs):
        if not self.etapa_id:
            self.etapa_id = unique_code(
                EtapaObra,
                "etapa_id",
                f"{self.organizacion.organizacion_id}_{self.nombre}",
                self.pk,
            )
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
        EDIFICACION_HABITACIONAL = (
            "Edificación habitacional",
            "Edificación habitacional",
        )
        EDIFICACION_COMERCIAL = "Edificación comercial", "Edificación comercial"
        EDIFICACION_INDUSTRIAL = "Edificación industrial", "Edificación industrial"
        INFRAESTRUCTURA_VIAL = "Infraestructura vial", "Infraestructura vial"
        INFRAESTRUCTURA_SANITARIA = (
            "Infraestructura sanitaria",
            "Infraestructura sanitaria",
        )
        OBRA_PUBLICA_EQUIPAMIENTO = (
            "Obra pública / equipamiento",
            "Obra pública / equipamiento",
        )
        URBANIZACION_ACENTUADA = "Urbanización", "Urbanización"

    class Estado(models.TextChoices):
        PLANIFICADA = "planificada", "Planificada"
        EN_EJECUCION = "en_ejecucion", "En ejecucion"
        PAUSADA = "pausada", "Pausada"
        FINALIZADA = "finalizada", "Finalizada"

    class PerfilAmbiental(models.TextChoices):
        EDIFICACION = "edificacion", "Edificacion"
        VIAL = "vial", "Vial"
        PUENTE_INFRAESTRUCTURA = "puente_infraestructura", "Puente o infraestructura"
        URBANIZACION = "urbanizacion", "Urbanizacion"
        INDUSTRIAL = "industrial", "Industrial"
        OTRO = "otro", "Otro"

    class EstadoAmbiental(models.TextChoices):
        CONFIGURACION = "configuracion", "Configuracion"
        MONITOREO = "monitoreo", "Monitoreo"
        REQUIERE_ATENCION = "requiere_atencion", "Requiere atencion"
        MEJORA_EN_CURSO = "mejora_en_curso", "Mejora en curso"
        CIERRE_PENDIENTE = "cierre_pendiente", "Cierre pendiente"
        CERRADA = "cerrada", "Cerrada"

    codigo_obra = models.CharField(max_length=80, unique=True, blank=True)
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.PROTECT, related_name="obras"
    )
    etapa_principal = models.ForeignKey(
        EtapaObra, on_delete=models.PROTECT, related_name="obras", null=True, blank=True
    )
    nombre = models.CharField(max_length=180)
    tipo_proyecto = models.CharField(
        max_length=40, choices=TipoProyecto.choices, default=TipoProyecto.OTRO
    )
    perfil_ambiental = models.CharField(
        max_length=40,
        choices=PerfilAmbiental.choices,
        default=PerfilAmbiental.OTRO,
        db_index=True,
    )
    fecha_inicio = models.DateField()
    fecha_termino_estimada = models.DateField(null=True, blank=True)
    superficie_m2 = models.DecimalField(
        max_digits=14, decimal_places=3, null=True, blank=True
    )
    ubicacion = models.CharField(max_length=240, blank=True)
    region = models.CharField(max_length=120, blank=True)
    comuna = models.CharField(max_length=120, blank=True)
    codigo_interno = models.CharField(max_length=120, blank=True)
    mandante = models.CharField(max_length=180, blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.EN_EJECUCION
    )
    estado_ambiental = models.CharField(
        max_length=30,
        choices=EstadoAmbiental.choices,
        default=EstadoAmbiental.CONFIGURACION,
        db_index=True,
    )
    fecha_cierre_ambiental = models.DateField(null=True, blank=True)
    observaciones_cierre_ambiental = models.TextField(blank=True)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_inicio", "nombre"]

    @property
    def emisiones_kg_co2e(self):
        return self.registros_emision.aggregate(total=Sum("emisiones_kg_co2e"))[
            "total"
        ] or Decimal("0")

    def save(self, *args, **kwargs):
        if not self.codigo_obra:
            self.codigo_obra = unique_code(Obra, "codigo_obra", self.nombre, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_obra} - {self.nombre}"


class AreaOperacional(models.Model):
    class Tipo(models.TextChoices):
        BODEGA = "bodega", "Bodega"
        MAQUINARIA_OPERACIONES = "maquinaria_operaciones", "Maquinaria y operaciones"
        LOGISTICA_TRANSPORTE = "logistica_transporte", "Logistica y transporte"
        ADMINISTRACION_COMPRAS = "administracion_compras", "Administracion y compras"
        MEDIO_AMBIENTE = "medio_ambiente", "Medio ambiente"
        GESTION_OBRA = "gestion_obra", "Gestion de obra"
        MANTENIMIENTO = "mantenimiento", "Mantenimiento"
        PRODUCCION = "produccion", "Produccion"
        CALIDAD_LABORATORIO = "calidad_laboratorio", "Calidad y laboratorio"
        OTRO = "otro", "Otro"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="areas_operacionales"
    )
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(
        max_length=40, choices=Tipo.choices, default=Tipo.OTRO, db_index=True
    )
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "nombre"], name="unique_area_operacional_nombre"
            )
        ]

    def __str__(self):
        return f"{self.organizacion.nombre} - {self.nombre}"


class EspacioTrabajoOperacional(models.Model):
    usuario_organizacion = models.ForeignKey(
        UsuarioOrganizacion, on_delete=models.CASCADE, related_name="espacios_trabajo"
    )
    area = models.ForeignKey(
        AreaOperacional, on_delete=models.PROTECT, related_name="espacios_trabajo"
    )
    obra = models.ForeignKey(
        Obra,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="espacios_operacionales",
    )
    nombre = models.CharField(max_length=140, blank=True)
    activo = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["area__nombre", "obra__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario_organizacion", "area", "obra"],
                name="unique_espacio_operacional_contexto",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        membership = self.usuario_organizacion
        if self.area.organizacion_id != membership.organizacion_id:
            raise ValidationError(
                {"area": "El area debe pertenecer a la organizacion de la membresia."}
            )
        if self.obra_id and self.obra.organizacion_id != membership.organizacion_id:
            raise ValidationError(
                {"obra": "La obra debe pertenecer a la organizacion de la membresia."}
            )
        if (
            self.obra_id
            and membership.alcance == UsuarioOrganizacion.Alcance.OBRAS
            and not membership.accesos_obra.filter(obra_id=self.obra_id).exists()
        ):
            raise ValidationError({"obra": "La membresia no tiene acceso a esta obra."})

    def __str__(self):
        scope = (
            self.obra.nombre
            if self.obra_id
            else self.usuario_organizacion.organizacion.nombre
        )
        return self.nombre or f"{self.area.nombre} - {scope}"


class UnidadOperacional(models.Model):
    class Tipo(models.TextChoices):
        PLANTA = "planta", "Planta"
        INSTALACION = "instalacion", "Instalacion"
        FAENA = "faena", "Faena"
        SUCURSAL = "sucursal", "Sucursal"
        CENTRO = "centro_operacional", "Centro operacional"
        OTRO = "otro", "Otro"

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="unidades_operacionales"
    )
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

    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="procesos_operacionales"
    )
    unidad = models.ForeignKey(
        UnidadOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procesos",
    )
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.ACTIVO
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.unidad_id and self.unidad.organizacion_id != self.organizacion_id:
            from django.core.exceptions import ValidationError

            raise ValidationError(
                {"unidad": "La unidad debe pertenecer a la misma organizacion."}
            )
