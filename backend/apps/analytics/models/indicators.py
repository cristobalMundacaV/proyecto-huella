from django.db import models
from django.db.models import Q

from .operational_context import Obra
from .platform import Organizacion


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
