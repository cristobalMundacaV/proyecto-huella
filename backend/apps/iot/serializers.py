from rest_framework import serializers

from .models import LecturaSensor


class LecturaSensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = LecturaSensor
        fields = [
            "id",
            "empresa",
            "unidad_operativa",
            "sensor",
            "tipo",
            "valor",
            "unidad",
            "co2e_estimado",
            "fecha_registro",
        ]
        read_only_fields = ["id", "unidad", "co2e_estimado", "fecha_registro"]

    def validate_valor(self, value):
        if value is None:
            raise serializers.ValidationError("El valor es requerido.")
        if value < 0:
            raise serializers.ValidationError("El valor no puede ser negativo.")
        return value
