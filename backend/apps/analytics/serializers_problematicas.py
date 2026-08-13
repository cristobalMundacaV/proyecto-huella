from rest_framework import serializers

from .models import AccionMejoraAmbiental, HistorialProblematicaAmbiental, MedicionSeguimientoAmbiental, ProblematicaAmbiental


class ProblematicaAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblematicaAmbiental
        exclude = ["organizacion"]
        read_only_fields = ["estado", "valor_posterior", "mejora_absoluta", "mejora_porcentaje", "resultado_evaluacion", "created_at", "updated_at"]

    def validate_obra(self, obra):
        if obra and obra.organizacion_id != self.context["organizacion"].id:
            raise serializers.ValidationError("Debe pertenecer a la organizacion activa.")
        return obra


class AccionMejoraAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccionMejoraAmbiental
        exclude = ["problematica"]
        read_only_fields = ["implementada_at", "created_at", "updated_at"]


class MedicionSeguimientoAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicionSeguimientoAmbiental
        exclude = ["problematica"]
        read_only_fields = ["created_at"]


class HistorialProblematicaAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialProblematicaAmbiental
        exclude = ["problematica"]
