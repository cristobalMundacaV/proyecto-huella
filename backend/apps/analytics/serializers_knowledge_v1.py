from rest_framework import serializers

from .models import CasoConocimientoAmbiental


class CasoConocimientoPrivadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CasoConocimientoAmbiental
        fields = ["id", "resultado_origen", "preset", "tipo_problematica", "categoria_ambiental", "tipo_accion", "contexto_operacional", "indicadores", "resultado", "metricas_comparadas", "grado_implementacion", "viabilidad", "fuerza_evidencia", "fundamento_evidencia", "origen_conocimiento", "fecha_caso", "version", "estado", "created_at"]
        read_only_fields = fields
