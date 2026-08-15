from django.db import transaction
from rest_framework import serializers

from .models import (EvidenciaObra, FuenteDatos, Observacion,
                     PuntoAmbientalOperacional, RegistroFlujoAmbiental,
                     VersionEvidencia)
from .serializers_activity_core import ObservacionSerializer
from .services.activity_core import actualizar_entidad, crear_entidad


class PuntoAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuntoAmbientalOperacional
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        organization = self.context["organizacion"]
        for field in ("activo", "unidad_operacional", "proceso_operacional", "obra"):
            value = attrs.get(field, getattr(self.instance, field, None))
            if value and value.organizacion_id != organization.id:
                raise serializers.ValidationError({field: "La referencia pertenece a otra organizacion."})
        return attrs

    def create(self, data): return crear_entidad(PuntoAmbientalOperacional, organizacion=self.context["organizacion"], datos=data)
    def update(self, instance, data): return actualizar_entidad(instance, data)


class RegistroFlujoAmbientalSerializer(serializers.ModelSerializer):
    concepto = serializers.SlugField(max_length=120, required=False, write_only=True)
    valor_numerico = serializers.DecimalField(max_digits=20, decimal_places=6, required=False, allow_null=True, write_only=True)
    valor_texto = serializers.CharField(required=False, allow_blank=True, write_only=True)
    unidad = serializers.CharField(max_length=40, required=False, allow_blank=True, write_only=True)
    fuente = serializers.PrimaryKeyRelatedField(queryset=FuenteDatos.objects.all(), required=False, write_only=True)
    evidencia = serializers.PrimaryKeyRelatedField(queryset=EvidenciaObra.objects.all(), required=False, allow_null=True, write_only=True)
    version_evidencia = serializers.PrimaryKeyRelatedField(queryset=VersionEvidencia.objects.all(), required=False, allow_null=True, write_only=True)
    metodo_captura = serializers.ChoiceField(choices=Observacion.MetodoCaptura.choices, default=Observacion.MetodoCaptura.MANUAL, write_only=True)
    naturaleza = serializers.ChoiceField(choices=Observacion.Naturaleza.choices, default=Observacion.Naturaleza.DECLARATIVO, write_only=True)
    observaciones = ObservacionSerializer(source="actividad.observaciones", many=True, read_only=True)

    class Meta:
        model = RegistroFlujoAmbiental
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        organization = self.context["organizacion"]
        for field in ("actividad", "punto", "unidad_operacional", "proceso", "activo", "obra", "evento_material", "fuente", "evidencia", "version_evidencia"):
            value = attrs.get(field, getattr(self.instance, field, None))
            if value and value.organizacion_id != organization.id:
                raise serializers.ValidationError({field: "La referencia pertenece a otra organizacion."})
        number, text = attrs.get("valor_numerico"), attrs.get("valor_texto", "")
        if number is not None and text: raise serializers.ValidationError("Use solo un valor numerico o textual.")
        if (number is not None or text) and not attrs.get("concepto"): raise serializers.ValidationError({"concepto": "Debe indicar el concepto observado."})
        if (number is not None or text) and not attrs.get("fuente"): raise serializers.ValidationError({"fuente": "Debe indicar la fuente."})
        version, evidence = attrs.get("version_evidencia"), attrs.get("evidencia")
        if version and evidence and version.evidencia_id != evidence.id: raise serializers.ValidationError({"version_evidencia": "La version no pertenece a la evidencia."})
        return attrs

    @transaction.atomic
    def _save(self, instance, data):
        observation_data = {key: data.pop(key, None) for key in ("concepto", "valor_numerico", "valor_texto", "unidad", "fuente", "evidencia", "version_evidencia", "metodo_captura", "naturaleza")}
        for field, value in data.items(): setattr(instance, field, value)
        instance.organizacion = self.context["organizacion"]; instance.save()
        if observation_data["valor_numerico"] is not None or observation_data["valor_texto"]:
            observation_data["valor_texto"] = observation_data["valor_texto"] or ""
            observation_data["unidad"] = observation_data["unidad"] or ""
            observation_data["metodo_captura"] = observation_data["metodo_captura"] or Observacion.MetodoCaptura.MANUAL
            observation_data["naturaleza"] = observation_data["naturaleza"] or Observacion.Naturaleza.DECLARATIVO
            request = self.context.get("request")
            observation = Observacion(organizacion=instance.organizacion, actividad=instance.actividad,
                                      timestamp_observacion=instance.periodo_fin or instance.periodo_inicio,
                                      actor=request.user if request and request.user.is_authenticated else None, **observation_data)
            observation.full_clean(); observation.save()
        return instance

    def create(self, data): return self._save(RegistroFlujoAmbiental(), data)
    def update(self, instance, data): return self._save(instance, data)
