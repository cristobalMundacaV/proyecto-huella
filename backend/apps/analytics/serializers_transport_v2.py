from rest_framework import serializers

from .models import FuenteDatos, RutaOperacional, ViajeOperacional
from .serializers_activity_core import ObservacionSerializer
from .services.transport_v2 import journey_metrics, save_journey_observations


class RutaOperacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RutaOperacional
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, data):
        return RutaOperacional.objects.create(organizacion=self.context["organizacion"], **data)


class ViajeOperacionalSerializer(serializers.ModelSerializer):
    distancia = serializers.DecimalField(max_digits=16, decimal_places=3, required=False, write_only=True)
    carga = serializers.DecimalField(max_digits=16, decimal_places=3, required=False, write_only=True)
    combustible = serializers.DecimalField(max_digits=16, decimal_places=3, required=False, write_only=True)
    fuente = serializers.PrimaryKeyRelatedField(queryset=FuenteDatos.objects.all(), required=False, write_only=True)
    distancia_detalle = ObservacionSerializer(source="observacion_distancia", read_only=True)
    carga_detalle = ObservacionSerializer(source="observacion_carga", read_only=True)
    combustible_detalle = ObservacionSerializer(source="observacion_combustible", read_only=True)
    metricas = serializers.SerializerMethodField()
    vehiculo_detalle = serializers.SerializerMethodField()

    class Meta:
        model = ViajeOperacional
        exclude = ["organizacion"]
        read_only_fields = ["id", "metodologia_tercerizado", "created_at", "updated_at"]

    def validate(self, attrs):
        organization = self.context["organizacion"]
        for field in ("actividad", "ruta"):
            item = attrs.get(field, getattr(self.instance, field, None))
            if item and item.organizacion_id != organization.id: raise serializers.ValidationError({field: "La referencia pertenece a otra organizacion."})
        vehicle = attrs.get("vehiculo", getattr(self.instance, "vehiculo", None))
        if vehicle and vehicle.activo.organizacion_id != organization.id: raise serializers.ValidationError({"vehiculo": "El vehiculo pertenece a otra organizacion."})
        source = attrs.get("fuente")
        if source and source.organizacion_id != organization.id: raise serializers.ValidationError({"fuente": "La fuente pertenece a otra organizacion."})
        if any(attrs.get(key) is not None for key in ("distancia", "carga", "combustible")) and not source:
            raise serializers.ValidationError({"fuente": "Debe indicar la fuente de los valores observados."})
        for field in ("distancia", "carga", "combustible"):
            if attrs.get(field) is not None and attrs[field] < 0:
                raise serializers.ValidationError({field: "El valor no puede ser negativo."})
        return attrs

    def _save(self, instance, data):
        values = {key: data.pop(key, None) for key in ("distancia", "carga", "combustible")}; source = data.pop("fuente", None)
        for field, value in data.items(): setattr(instance, field, value)
        instance.organizacion = self.context["organizacion"]; instance.save()
        return save_journey_observations(instance, source, values) if source else instance

    def create(self, data): return self._save(ViajeOperacional(), data)
    def update(self, instance, data): return self._save(instance, data)
    def get_metricas(self, obj): return journey_metrics(obj)
    def get_vehiculo_detalle(self, obj): return {"id": obj.vehiculo_id, "activo_id": obj.vehiculo.activo_id, "codigo": obj.vehiculo.activo.codigo, "nombre": obj.vehiculo.activo.nombre, "patente": obj.vehiculo.patente, "capacidad_carga": obj.vehiculo.capacidad_carga, "unidad_capacidad_carga": obj.vehiculo.unidad_capacidad_carga}
