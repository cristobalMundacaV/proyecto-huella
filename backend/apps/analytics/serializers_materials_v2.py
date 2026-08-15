from django.db import transaction
from rest_framework import serializers

from .models import EventoMaterial, LoteMaterial, MaterialOperacional
from .serializers_activity_core import ObservacionSerializer
from .services.activity_core import actualizar_entidad, crear_entidad
from .services.materials_v2 import save_event_quantity


def _same_tenant(attrs, organization, fields):
    errors = {}
    for field in fields:
        value = attrs.get(field)
        if value and value.organizacion_id != organization.id:
            errors[field] = "La referencia pertenece a otra organizacion."
    if errors:
        raise serializers.ValidationError(errors)


class MaterialOperacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialOperacional
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, data):
        return crear_entidad(MaterialOperacional, organizacion=self.context["organizacion"], datos=data)

    def update(self, instance, data):
        return actualizar_entidad(instance, data)


class LoteMaterialSerializer(serializers.ModelSerializer):
    material_nombre = serializers.CharField(source="material.nombre", read_only=True)

    class Meta:
        model = LoteMaterial
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        organization = self.context["organizacion"]
        merged = {field: attrs.get(field, getattr(self.instance, field, None)) for field in ("material", "fuente", "evidencia", "version_evidencia")}
        _same_tenant(merged, organization, merged)
        return attrs

    def create(self, data):
        return crear_entidad(LoteMaterial, organizacion=self.context["organizacion"], datos=data)

    def update(self, instance, data):
        return actualizar_entidad(instance, data)


class EventoMaterialSerializer(serializers.ModelSerializer):
    cantidad = serializers.DecimalField(max_digits=20, decimal_places=6, required=False, write_only=True, min_value=0)
    unidad = serializers.CharField(max_length=40, required=False, write_only=True)
    cantidad_detalle = ObservacionSerializer(source="observacion_cantidad", read_only=True)
    material_nombre = serializers.CharField(source="material.nombre", read_only=True)
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    proceso_nombre = serializers.CharField(source="proceso.nombre", read_only=True)

    class Meta:
        model = EventoMaterial
        exclude = ["organizacion"]
        read_only_fields = ["id", "observacion_cantidad", "created_at", "updated_at"]

    def validate(self, attrs):
        organization = self.context["organizacion"]
        fields = ("material", "lote", "actividad", "evento_origen", "obra", "proceso", "fuente", "evidencia", "version_evidencia", "observacion_cantidad")
        merged = {field: attrs.get(field, getattr(self.instance, field, None)) for field in fields}
        _same_tenant(merged, organization, fields)
        amount = attrs.get("cantidad")
        unit = attrs.get("unidad")
        source = attrs.get("fuente", getattr(self.instance, "fuente", None))
        if amount is not None and not unit:
            raise serializers.ValidationError({"unidad": "Debe indicar la unidad de la cantidad."})
        if amount is not None and not source:
            raise serializers.ValidationError({"fuente": "Debe indicar la fuente de la cantidad."})
        evidence = merged["evidencia"]
        version = merged["version_evidencia"]
        if version and evidence and version.evidencia_id != evidence.id:
            raise serializers.ValidationError({"version_evidencia": "La version no pertenece a la evidencia asociada."})
        return attrs

    @transaction.atomic
    def _save(self, instance, data):
        amount = data.pop("cantidad", None)
        unit = data.pop("unidad", None)
        for field, value in data.items():
            setattr(instance, field, value)
        instance.organizacion = self.context["organizacion"]
        instance.save()
        if amount is not None:
            request = self.context.get("request")
            save_event_quantity(instance, amount=amount, unit=unit, source=instance.fuente,
                                evidence=instance.evidencia, evidence_version=instance.version_evidencia,
                                actor=request.user if request and request.user.is_authenticated else None)
        return instance

    def create(self, data):
        return self._save(EventoMaterial(), data)

    def update(self, instance, data):
        return self._save(instance, data)
