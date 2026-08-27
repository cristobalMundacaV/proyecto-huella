from rest_framework import serializers

from .models import (
    ActivoOperacional,
    CondicionOperacionalActivo,
    MantenimientoActivo,
    Maquinaria,
    Vehiculo,
)
from .policies.assets import asset_relation_errors, condition_source_error
from .services.assets import (
    create_asset,
    create_condition,
    create_maintenance,
    update_asset,
    update_maintenance,
)


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
        fields = [
            "id",
            "tipo",
            "fecha_programada",
            "fecha_realizada",
            "estado",
            "descripcion",
            "lectura_momento",
            "unidad_lectura",
            "proveedor_responsable",
            "observaciones",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        return create_maintenance(
            organization=self.context["organizacion"],
            asset=self.context["activo"],
            data=validated_data,
        )

    def update(self, instance, validated_data):
        return update_maintenance(maintenance=instance, data=validated_data)


class CondicionOperacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CondicionOperacionalActivo
        fields = [
            "id",
            "timestamp_inicio",
            "timestamp_fin",
            "estado",
            "fuente",
            "observaciones",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_fuente(self, fuente):
        error = condition_source_error(
            organization=self.context["organizacion"], source=fuente
        )
        if error:
            raise serializers.ValidationError(error)
        return fuente

    def create(self, validated_data):
        return create_condition(asset=self.context["activo"], data=validated_data)


class ActivoOperacionalSerializer(serializers.ModelSerializer):
    unidad_nombre = serializers.CharField(
        source="unidad_operacional.nombre", read_only=True
    )
    proceso_nombre = serializers.CharField(
        source="proceso_operacional.nombre", read_only=True
    )
    vehiculo = VehiculoSerializer(required=False)
    maquinaria = MaquinariaSerializer(required=False)
    mantenimientos = MantenimientoActivoSerializer(many=True, read_only=True)
    condiciones = CondicionOperacionalSerializer(many=True, read_only=True)
    sensores_count = serializers.IntegerField(source="sensores.count", read_only=True)

    class Meta:
        model = ActivoOperacional
        fields = [
            "id",
            "codigo",
            "nombre",
            "tipo",
            "descripcion",
            "unidad_operacional",
            "unidad_nombre",
            "proceso_operacional",
            "proceso_nombre",
            "estado",
            "fecha_alta",
            "fecha_baja",
            "metadata",
            "vehiculo",
            "maquinaria",
            "mantenimientos",
            "condiciones",
            "sensores_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "mantenimientos",
            "condiciones",
            "sensores_count",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        organizacion = self.context["organizacion"]
        errors = asset_relation_errors(
            organization=organizacion,
            unit=attrs.get(
                "unidad_operacional", getattr(self.instance, "unidad_operacional", None)
            ),
            process=attrs.get(
                "proceso_operacional",
                getattr(self.instance, "proceso_operacional", None),
            ),
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        return create_asset(
            organization=self.context["organizacion"], data=validated_data
        )

    def update(self, instance, validated_data):
        return update_asset(asset=instance, data=validated_data)
