from django.db import models

from .operational_context import ProcesoOperacional
from .operational_data import ActividadOperacional, FuenteDatos, Observacion
from .platform import Organizacion


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
            if self.tipo in {self.Tipo.USO, self.Tipo.CONSUMO} and self.evento_origen.tipo != self.Tipo.RECEPCION:
                errors["evento_origen"] = "El evento origen debe ser una recepcion."
            elif self.tipo in {self.Tipo.USO, self.Tipo.CONSUMO} and self.evento_origen.obra_id != self.obra_id:
                errors["evento_origen"] = "La recepcion debe pertenecer a la misma obra."
            elif self.pk and self.evento_origen_id == self.pk:
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
