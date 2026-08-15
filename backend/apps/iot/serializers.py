from rest_framework import serializers

from .models import DispositivoSensor, LecturaSensor, RegistroSensor


class LecturaSensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = LecturaSensor
        fields = [
            "id",
            "organizacion",
            "etapa_obra",
            "sensor",
            "tipo",
            "valor",
            "unidad",
            "fecha_registro",
        ]
        read_only_fields = ["id", "unidad", "fecha_registro"]

    def validate_valor(self, value):
        if value is None:
            raise serializers.ValidationError("El valor es requerido.")
        if value < 0:
            raise serializers.ValidationError("El valor no puede ser negativo.")
        return value


class DispositivoSensorSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)
    organizacion_nombre = serializers.CharField(source="organizacion.nombre", read_only=True)
    obra_codigo = serializers.CharField(source="obra.codigo_obra", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    etapa_codigo = serializers.CharField(source="etapa.etapa_id", read_only=True)
    etapa_nombre = serializers.CharField(source="etapa.nombre", read_only=True)

    class Meta:
        model = DispositivoSensor
        fields = [
            "id",
            "dispositivo_id",
            "nombre",
            "organizacion",
            "organizacion_id",
            "organizacion_nombre",
            "obra",
            "obra_codigo",
            "obra_nombre",
            "etapa",
            "etapa_codigo",
            "etapa_nombre",
            "tipo_sensor",
            "ubicacion",
            "descripcion",
            "api_key",
            "activo",
            "metadata",
            "last_seen_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organizacion_id",
            "organizacion_nombre",
            "obra_codigo",
            "obra_nombre",
            "etapa_codigo",
            "etapa_nombre",
            "last_seen_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"organizacion": {"write_only": True}}

    def create(self, validated_data):
        raw_key = validated_data.pop("api_key", None)
        dispositivo = DispositivoSensor(**validated_data)
        dispositivo.set_api_key(raw_key)
        dispositivo.save()
        return dispositivo

    def update(self, instance, validated_data):
        raw_key = validated_data.pop("api_key", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if raw_key:
            instance.set_api_key(raw_key)
        instance.save()
        return instance


class RegistroSensorSerializer(serializers.ModelSerializer):
    dispositivo_id = serializers.CharField(source="dispositivo.dispositivo_id", read_only=True)
    dispositivo_nombre = serializers.CharField(source="dispositivo.nombre", read_only=True)
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)
    organizacion_nombre = serializers.CharField(source="organizacion.nombre", read_only=True)
    obra_codigo = serializers.CharField(source="obra.codigo_obra", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    etapa_codigo = serializers.CharField(source="etapa.etapa_id", read_only=True)
    etapa_nombre = serializers.CharField(source="etapa.nombre", read_only=True)
    lectura_v2_id = serializers.IntegerField(source="lectura_v2.id", read_only=True)
    observacion_id = serializers.IntegerField(source="lectura_v2.observacion_id", read_only=True)

    class Meta:
        model = RegistroSensor
        fields = [
            "id",
            "external_id",
            "dispositivo",
            "dispositivo_id",
            "dispositivo_nombre",
            "organizacion",
            "organizacion_id",
            "organizacion_nombre",
            "obra",
            "obra_codigo",
            "obra_nombre",
            "etapa",
            "etapa_codigo",
            "etapa_nombre",
            "tipo",
            "valor",
            "unidad",
            "timestamp_sensor",
            "received_at",
            "estado_procesamiento",
            "lectura_v2",
            "lectura_v2_id",
            "observacion_id",
            "metadata",
            "raw_payload",
            "error_procesamiento",
        ]
        read_only_fields = [
            "id",
            "dispositivo_id",
            "dispositivo_nombre",
            "organizacion_id",
            "organizacion_nombre",
            "obra_codigo",
            "obra_nombre",
            "etapa_codigo",
            "etapa_nombre",
            "received_at",
            "estado_procesamiento",
            "lectura_v2_id",
            "observacion_id",
            "error_procesamiento",
        ]
