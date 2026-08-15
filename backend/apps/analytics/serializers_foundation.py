from django.db import transaction
from rest_framework import serializers

from .models import (CapacidadAmbiental, CapacidadOrganizacion, DiagnosticoAmbientalInicial,
                     ElementoDiagnosticoAmbiental, ProcesoOperacional, UnidadOperacional)


class ElementoDiagnosticoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    tipo = serializers.ChoiceField(choices=ElementoDiagnosticoAmbiental.Tipo.choices, required=False)
    nombre = serializers.CharField(max_length=180, required=False)
    eliminar = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = ElementoDiagnosticoAmbiental
        fields = ["id", "tipo", "nombre", "descripcion", "eliminar", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class DiagnosticoAmbientalSerializer(serializers.ModelSerializer):
    elementos = ElementoDiagnosticoSerializer(many=True, required=False)

    class Meta:
        model = DiagnosticoAmbientalInicial
        fields = ["id", "obra", "estado", "fecha_inicio", "fecha_finalizacion", "objetivo_principal",
                  "descripcion_contexto", "observaciones", "responsable", "elementos", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_responsable(self, responsable):
        organizacion = self.context["organizacion"]
        if responsable and not responsable.organizaciones_perfil.filter(organizacion=organizacion, activo=True).exists():
            raise serializers.ValidationError("El responsable debe pertenecer a la organizacion.")
        return responsable

    def validate_obra(self, obra):
        if obra and obra.organizacion_id != self.context["organizacion"].id:
            raise serializers.ValidationError("La obra debe pertenecer a la organizacion.")
        return obra

    def _guardar_elementos(self, diagnostico, elementos):
        if elementos is None:
            return

        ids = [item["id"] for item in elementos if item.get("id") is not None]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError({"elementos": "No se puede enviar el mismo id mas de una vez."})
        existentes = {item.id: item for item in diagnostico.elementos.filter(id__in=ids)}
        ajenos = sorted(set(ids) - set(existentes))
        if ajenos:
            raise serializers.ValidationError({"elementos": f"Elementos no pertenecientes al diagnostico: {ajenos}."})

        for datos in elementos:
            elemento_id = datos.pop("id", None)
            eliminar = datos.pop("eliminar", False)
            if elemento_id is not None:
                elemento = existentes[elemento_id]
                if eliminar:
                    elemento.delete()
                    continue
                for campo, valor in datos.items():
                    setattr(elemento, campo, valor)
                elemento.save()
                continue
            if eliminar:
                raise serializers.ValidationError({"elementos": "Eliminar requiere el id de un elemento existente."})
            if not datos.get("tipo") or not datos.get("nombre"):
                raise serializers.ValidationError({"elementos": "Los elementos nuevos requieren tipo y nombre."})
            ElementoDiagnosticoAmbiental.objects.create(diagnostico=diagnostico, **datos)

    @transaction.atomic
    def create(self, validated_data):
        elementos = validated_data.pop("elementos", [])
        diagnostico = super().create(validated_data)
        self._guardar_elementos(diagnostico, elementos)
        return diagnostico

    @transaction.atomic
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
