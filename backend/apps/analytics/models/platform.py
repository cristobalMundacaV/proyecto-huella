from django.contrib.auth.models import User
from django.db import models

from .utils import unique_code


class Organizacion(models.Model):
    class Preset(models.TextChoices):
        CONSTRUCCION = "construccion", "Construcción"
        FORESTAL = "forestal", "Forestal"
        ASERRADERO = "aserradero", "Aserradero"
        TRANSPORTE = "transporte", "Transporte"
        INDUSTRIAL = "industrial", "Industrial"

    organizacion_id = models.CharField(max_length=80, unique=True, blank=True)
    nombre = models.CharField(max_length=180)
    nombre_comercial = models.CharField(max_length=180, blank=True)
    rut = models.CharField(max_length=30, blank=True)
    region = models.CharField(max_length=120, blank=True)
    comuna = models.CharField(max_length=120, blank=True)
    direccion = models.CharField(max_length=240, blank=True)
    rubro = models.CharField(max_length=120, blank=True)
    preset = models.CharField(
        max_length=40,
        choices=Preset.choices,
        default=Preset.CONSTRUCCION,
        db_index=True,
    )
    activa = models.BooleanField(default=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    contacto = models.CharField(max_length=160, blank=True)
    observaciones = models.TextField(blank=True)
    pais = models.CharField(max_length=80, default="Chile")
    onboarding_step = models.PositiveSmallIntegerField(default=1)
    onboarding_completado = models.BooleanField(default=False, db_index=True)
    onboarding_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def save(self, *args, **kwargs):
        if not self.organizacion_id:
            self.organizacion_id = unique_code(
                Organizacion, "organizacion_id", self.nombre, self.pk
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class SuscripcionSaaS(models.Model):
    class Plan(models.TextChoices):
        SIN_PLAN = "sin_plan", "Sin plan"
        STARTER = "starter", "Starter"
        PROFESSIONAL = "professional", "Professional"
        ENTERPRISE = "enterprise", "Enterprise"

    class Estado(models.TextChoices):
        PILOTO = "piloto", "Piloto"
        ACTIVO = "activo", "Activo"
        PAGO_PENDIENTE = "pago_pendiente", "Pago pendiente"
        SUSPENDIDO = "suspendido", "Suspendido"
        CANCELADO = "cancelado", "Cancelado"

    class Disponibilidad(models.TextChoices):
        OPERATIVO = "operativo", "Operativo"
        BLOQUEADO = "bloqueado", "Bloqueado"

    organizacion = models.OneToOneField(
        Organizacion, on_delete=models.CASCADE, related_name="suscripcion_saas"
    )
    plan = models.CharField(
        max_length=24, choices=Plan.choices, default=Plan.SIN_PLAN, db_index=True
    )
    estado = models.CharField(
        max_length=24, choices=Estado.choices, default=Estado.PILOTO, db_index=True
    )
    disponibilidad = models.CharField(
        max_length=16,
        choices=Disponibilidad.choices,
        default=Disponibilidad.OPERATIVO,
        db_index=True,
    )
    inicio_plan = models.DateField(null=True, blank=True)
    fin_piloto = models.DateField(null=True, blank=True)
    proximo_vencimiento = models.DateField(null=True, blank=True)
    fecha_suspension = models.DateTimeField(null=True, blank=True)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    responsable_comercial = models.CharField(max_length=160, blank=True)
    limites = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organizacion__nombre"]


class EventoAuditoriaSaaS(models.Model):
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="auditoria_saas"
    )
    actor = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="eventos_saas"
    )
    accion = models.CharField(max_length=60, db_index=True)
    detalle = models.TextField(blank=True)
    estado_anterior = models.JSONField(default=dict, blank=True)
    estado_nuevo = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class UsuarioOrganizacion(models.Model):
    class Rol(models.TextChoices):
        ADMIN = "admin", "Administrador"
        RESPONSABLE_AMBIENTAL = "responsable_ambiental", "Responsable ambiental"
        ANALISTA = "analista", "Analista ambiental"
        OPERADOR = "operador", "Operador"
        REVISOR_AMBIENTAL = "revisor_ambiental", "Revisor ambiental"
        LECTOR = "lector", "Lector"

    class Alcance(models.TextChoices):
        ORGANIZACION = "organizacion", "Toda la organización"
        OBRAS = "obras", "Obras específicas"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="organizaciones_perfil"
    )
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.CASCADE, related_name="usuarios"
    )
    rol = models.CharField(max_length=24, choices=Rol.choices, default=Rol.ANALISTA)
    alcance = models.CharField(
        max_length=20, choices=Alcance.choices, default=Alcance.ORGANIZACION
    )
    cargo = models.CharField(max_length=120, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organizacion__nombre", "user__first_name", "user__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organizacion"], name="unique_usuario_organizacion"
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.organizacion.nombre}"


class UsuarioObraAcceso(models.Model):
    usuario_organizacion = models.ForeignKey(
        UsuarioOrganizacion, on_delete=models.CASCADE, related_name="accesos_obra"
    )
    obra = models.ForeignKey(
        "analytics.Obra", on_delete=models.CASCADE, related_name="accesos_usuario"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario_organizacion", "obra"],
                name="unique_usuario_obra_acceso",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.obra_id
            and self.usuario_organizacion_id
            and self.obra.organizacion_id != self.usuario_organizacion.organizacion_id
        ):
            raise ValidationError(
                {"obra": "La obra debe pertenecer a la organización de la membresía."}
            )
