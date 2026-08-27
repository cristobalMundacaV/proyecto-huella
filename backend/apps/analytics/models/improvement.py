from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .assets import ActivoOperacional
from .indicators import IndicadorAmbiental, ValorIndicador
from .operational_context import Obra, ProcesoOperacional, UnidadOperacional
from .operational_data import ActividadOperacional
from .platform import Organizacion
from .provenance import EvidenciaObra


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
