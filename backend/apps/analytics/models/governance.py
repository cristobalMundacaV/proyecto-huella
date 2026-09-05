from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .platform import Organizacion


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
    contexto = models.JSONField(default=dict, blank=True)
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
        COMBUSTIBLE_CONSUMIDO = "combustible_consumido", "Combustible consumido x factor"
        ENERGIA_CONSUMIDA = "energia_consumida", "Energia consumida x factor"
        MATERIAL_CANTIDAD = "material_cantidad", "Cantidad de material x factor"

    version_metodologia = models.OneToOneField(
        VersionMetodologia, on_delete=models.PROTECT, related_name="formula"
    )
    factor_ambiental = models.ForeignKey(
        FactorAmbiental,
        on_delete=models.PROTECT,
        related_name="formulas",
        null=True,
        blank=True,
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
