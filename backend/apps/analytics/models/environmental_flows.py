from django.db import models

from .assets import ActivoOperacional, PuntoAmbientalOperacional
from .materials import EventoMaterial
from .operational_context import ProcesoOperacional, UnidadOperacional
from .operational_data import ActividadOperacional
from .platform import Organizacion


class RegistroFlujoAmbiental(models.Model):
    class ClasificacionResiduo(models.TextChoices):
        NO_PELIGROSO = "no_peligroso", "No peligroso"
        PELIGROSO = "peligroso", "Peligroso"

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
    clasificacion_residuo = models.CharField(
        max_length=20, choices=ClasificacionResiduo.choices, blank=True
    )
    tipo_residuo = models.SlugField(max_length=120, blank=True)
    tipo_residuo_otro = models.CharField(max_length=180, blank=True)
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
            self.flujo
            in {
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
            and self.destino_operacional != self.DestinoOperacional.SIN_CLASIFICAR
        ):
            errors["destino_operacional"] = (
                "Este flujo ambiental no admite un destino operacional."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
