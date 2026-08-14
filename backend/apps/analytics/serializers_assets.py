from rest_framework import serializers

from .models import (ActivoOperacional, CondicionOperacionalActivo, MantenimientoActivo,
                     Maquinaria, Vehiculo)
from .services.activity_core import actualizar_entidad, crear_entidad


class VehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehiculo
        exclude = ["activo"]


class MaquinariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Maquinaria
        exclude = ["activo"]


class MantenimientoActivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MantenimientoActivo
        fields = ["id", "tipo", "fecha_programada", "fecha_realizada", "estado", "descripcion", "lectura_momento",
                  "unidad_lectura", "proveedor_responsable", "observaciones", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        return crear_entidad(MantenimientoActivo, organizacion=self.context["organizacion"], datos={"activo": self.context["activo"], **validated_data})

    def update(self, instance, validated_data):
        return actualizar_entidad(instance, validated_data)


class CondicionOperacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CondicionOperacionalActivo
        fields = ["id", "timestamp_inicio", "timestamp_fin", "estado", "fuente", "observaciones", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_fuente(self, fuente):
        if fuente and fuente.organizacion_id != self.context["organizacion"].id:
            raise serializers.ValidationError("La fuente pertenece a otra organizacion.")
        return fuente

    def create(self, validated_data):
        instance = CondicionOperacionalActivo(activo=self.context["activo"], **validated_data)
        instance.full_clean(); instance.save(); return instance


class ActivoOperacionalSerializer(serializers.ModelSerializer):
    unidad_nombre = serializers.CharField(source="unidad_operacional.nombre", read_only=True)
    proceso_nombre = serializers.CharField(source="proceso_operacional.nombre", read_only=True)
    vehiculo = VehiculoSerializer(required=False)
    maquinaria = MaquinariaSerializer(required=False)
    mantenimientos = MantenimientoActivoSerializer(many=True, read_only=True)
    condiciones = CondicionOperacionalSerializer(many=True, read_only=True)
    sensores_count = serializers.IntegerField(source="sensores.count", read_only=True)

    class Meta:
        model = ActivoOperacional
        fields = ["id", "codigo", "nombre", "tipo", "descripcion", "unidad_operacional", "unidad_nombre",
                  "proceso_operacional", "proceso_nombre", "estado", "fecha_alta", "fecha_baja", "metadata",
                  "vehiculo", "maquinaria", "mantenimientos", "condiciones", "sensores_count", "created_at", "updated_at"]
        read_only_fields = ["id", "mantenimientos", "condiciones", "sensores_count", "created_at", "updated_at"]

    def validate(self, attrs):
        organizacion = self.context["organizacion"]
        for field in ("unidad_operacional", "proceso_operacional"):
            relation = attrs.get(field, getattr(self.instance, field, None))
            if relation and relation.organizacion_id != organizacion.id:
                raise serializers.ValidationError({field: "La relacion pertenece a otra organizacion."})
        return attrs

    def _specialization(self, activo, vehiculo, maquinaria):
        if vehiculo is not None:
            Vehiculo.objects.update_or_create(activo=activo, defaults=vehiculo)
        if maquinaria is not None:
            Maquinaria.objects.update_or_create(activo=activo, defaults=maquinaria)

    def create(self, validated_data):
        vehiculo = validated_data.pop("vehiculo", None); maquinaria = validated_data.pop("maquinaria", None)
        activo = crear_entidad(ActivoOperacional, organizacion=self.context["organizacion"], datos=validated_data)
        self._specialization(activo, vehiculo, maquinaria); return activo

    def update(self, instance, validated_data):
        vehiculo = validated_data.pop("vehiculo", None); maquinaria = validated_data.pop("maquinaria", None)
        activo = actualizar_entidad(instance, validated_data); self._specialization(activo, vehiculo, maquinaria); return activo
