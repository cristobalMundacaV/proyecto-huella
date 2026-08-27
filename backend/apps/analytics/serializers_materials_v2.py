from rest_framework import serializers

from .models import EventoMaterial, LoteMaterial, MaterialOperacional
from .serializers_activity_core import ObservacionSerializer
from .policies.materials import material_event_errors, tenant_relation_errors
from .services.materials_v2 import save_entity, save_material_event


class MaterialOperacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialOperacional
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, data):
        return save_entity(MaterialOperacional(), self.context["organizacion"], data)

    def update(self, instance, data):
        return save_entity(instance, self.context["organizacion"], data)


class LoteMaterialSerializer(serializers.ModelSerializer):
    material_nombre = serializers.CharField(source="material.nombre", read_only=True)

    class Meta:
        model = LoteMaterial
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        organization = self.context["organizacion"]
        errors = tenant_relation_errors(
            attrs,
            organization,
            ("material", "fuente", "evidencia", "version_evidencia"),
            self.instance,
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, data):
        return save_entity(LoteMaterial(), self.context["organizacion"], data)

    def update(self, instance, data):
        return save_entity(instance, self.context["organizacion"], data)


class EventoMaterialSerializer(serializers.ModelSerializer):
    cantidad = serializers.DecimalField(
        max_digits=20, decimal_places=6, required=False, write_only=True, min_value=0
    )
    unidad = serializers.CharField(max_length=40, required=False, write_only=True)
    cantidad_detalle = ObservacionSerializer(
        source="observacion_cantidad", read_only=True
    )
    material_nombre = serializers.CharField(source="material.nombre", read_only=True)
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    proceso_nombre = serializers.CharField(source="proceso.nombre", read_only=True)

    class Meta:
        model = EventoMaterial
        exclude = ["organizacion"]
        read_only_fields = ["id", "observacion_cantidad", "created_at", "updated_at"]

    def validate(self, attrs):
        errors = material_event_errors(
            attrs, self.context["organizacion"], self.instance
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _save(self, instance, data):
        request = self.context.get("request")
        actor = request.user if request and request.user.is_authenticated else None
        return save_material_event(instance, self.context["organizacion"], data, actor)

    def create(self, data):
        return self._save(EventoMaterial(), data)

    def update(self, instance, data):
        return self._save(instance, data)
