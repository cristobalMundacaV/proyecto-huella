from rest_framework import serializers

from .models import FuenteDatos, RutaOperacional, ViajeOperacional
from .serializers_activity_core import ObservacionSerializer
from .policies.transport import journey_relation_errors
from .services.transport_v2 import create_route, journey_metrics, save_journey


class RutaOperacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RutaOperacional
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, data):
        return create_route(self.context["organizacion"], data)


class ViajeOperacionalSerializer(serializers.ModelSerializer):
    distancia = serializers.DecimalField(
        max_digits=16, decimal_places=3, required=False, write_only=True
    )
    carga = serializers.DecimalField(
        max_digits=16, decimal_places=3, required=False, write_only=True
    )
    combustible = serializers.DecimalField(
        max_digits=16, decimal_places=3, required=False, write_only=True
    )
    fuente = serializers.PrimaryKeyRelatedField(
        queryset=FuenteDatos.objects.all(), required=False, write_only=True
    )
    distancia_detalle = ObservacionSerializer(
        source="observacion_distancia", read_only=True
    )
    carga_detalle = ObservacionSerializer(source="observacion_carga", read_only=True)
    combustible_detalle = ObservacionSerializer(
        source="observacion_combustible", read_only=True
    )
    metricas = serializers.SerializerMethodField()
    vehiculo_detalle = serializers.SerializerMethodField()

    class Meta:
        model = ViajeOperacional
        exclude = ["organizacion"]
        read_only_fields = ["id", "metodologia_tercerizado", "created_at", "updated_at"]

    def validate(self, attrs):
        errors = journey_relation_errors(
            attrs, self.context["organizacion"], self.instance
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _save(self, instance, data):
        return save_journey(instance, self.context["organizacion"], data)

    def create(self, data):
        return self._save(ViajeOperacional(), data)

    def update(self, instance, data):
        return self._save(instance, data)

    def get_metricas(self, obj):
        return journey_metrics(obj)

    def get_vehiculo_detalle(self, obj):
        return {
            "id": obj.vehiculo_id,
            "activo_id": obj.vehiculo.activo_id,
            "codigo": obj.vehiculo.activo.codigo,
            "nombre": obj.vehiculo.activo.nombre,
            "patente": obj.vehiculo.patente,
            "capacidad_carga": obj.vehiculo.capacidad_carga,
            "unidad_capacidad_carga": obj.vehiculo.unidad_capacidad_carga,
        }
