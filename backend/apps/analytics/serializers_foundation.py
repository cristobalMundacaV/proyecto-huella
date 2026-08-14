from rest_framework import serializers

from .models import (CapacidadAmbiental, CapacidadOrganizacion, DiagnosticoAmbientalInicial,
                     ElementoDiagnosticoAmbiental, ProcesoOperacional, UnidadOperacional)


class ElementoDiagnosticoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElementoDiagnosticoAmbiental
        fields = ["id", "tipo", "nombre", "descripcion", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class DiagnosticoAmbientalSerializer(serializers.ModelSerializer):
    elementos = ElementoDiagnosticoSerializer(many=True, required=False)

    class Meta:
        model = DiagnosticoAmbientalInicial
        fields = ["id", "estado", "fecha_inicio", "fecha_finalizacion", "objetivo_principal",
                  "descripcion_contexto", "observaciones", "responsable", "elementos", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_responsable(self, responsable):
        organizacion = self.context["organizacion"]
        if responsable and not responsable.organizaciones_perfil.filter(organizacion=organizacion, activo=True).exists():
            raise serializers.ValidationError("El responsable debe pertenecer a la organizacion.")
        return responsable

    def _guardar_elementos(self, diagnostico, elementos):
        if elementos is None:
            return
        diagnostico.elementos.all().delete()
        ElementoDiagnosticoAmbiental.objects.bulk_create(
            [ElementoDiagnosticoAmbiental(diagnostico=diagnostico, **item) for item in elementos]
        )

    def create(self, validated_data):
        elementos = validated_data.pop("elementos", [])
        diagnostico = super().create(validated_data)
        self._guardar_elementos(diagnostico, elementos)
        return diagnostico

    def update(self, instance, validated_data):
        elementos = validated_data.pop("elementos", None)
        diagnostico = super().update(instance, validated_data)
        self._guardar_elementos(diagnostico, elementos)
        return diagnostico


class CapacidadAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapacidadAmbiental
        fields = ["id", "clave", "nombre", "descripcion", "activa", "orden"]


class CapacidadOrganizacionSerializer(serializers.ModelSerializer):
    capacidad = CapacidadAmbientalSerializer(read_only=True)

    class Meta:
        model = CapacidadOrganizacion
        fields = ["id", "capacidad", "estado", "recomendada_por_preset", "configuracion", "created_at", "updated_at"]
        read_only_fields = ["id", "capacidad", "recomendada_por_preset", "created_at", "updated_at"]


class UnidadOperacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadOperacional
        fields = ["id", "nombre", "tipo", "descripcion", "activa", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProcesoOperacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcesoOperacional
        fields = ["id", "unidad", "nombre", "descripcion", "estado", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_unidad(self, unidad):
        organizacion = self.context["organizacion"]
        if unidad and unidad.organizacion_id != organizacion.id:
            raise serializers.ValidationError("La unidad debe pertenecer a la misma organizacion.")
        return unidad
