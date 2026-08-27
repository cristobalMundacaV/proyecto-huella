from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .improvement import ProblematicaAmbiental, ResultadoIntervencion
from .platform import Organizacion


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
