from rest_framework import serializers

from .models import ActividadOperacional, FuenteDatos, Observacion
from .services.activity_core import actualizar_entidad, crear_entidad


class FuenteDatosSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuenteDatos
        fields = ["id", "nombre", "tipo", "descripcion", "activa", "identificador_externo", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        return crear_entidad(FuenteDatos, organizacion=self.context["organizacion"], datos=validated_data)

    def update(self, instance, validated_data):
        return actualizar_entidad(instance, validated_data)


class ObservacionSerializer(serializers.ModelSerializer):
    fuente_detalle = FuenteDatosSerializer(source="fuente", read_only=True)
    evidencia_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Observacion
        fields = ["id", "actividad", "fuente", "fuente_detalle", "concepto", "valor_numerico", "valor_texto",
                  "unidad", "timestamp_observacion", "metodo_captura", "naturaleza", "actor", "evidencia",
                  "evidencia_detalle", "estado", "created_at", "updated_at"]
        read_only_fields = ["id", "actividad", "actor", "created_at", "updated_at"]

    def validate(self, attrs):
        organizacion = self.context["organizacion"]
        actividad = self.context.get("actividad") or getattr(self.instance, "actividad", None)
        actividad_enviada = self.initial_data.get("actividad") if hasattr(self, "initial_data") else None
        if actividad_enviada is not None and actividad and str(actividad_enviada) != str(actividad.id):
            raise serializers.ValidationError({"actividad": "La actividad no coincide con el recurso solicitado."})
        fuente = attrs.get("fuente", getattr(self.instance, "fuente", None))
        evidencia = attrs.get("evidencia", getattr(self.instance, "evidencia", None))
        if actividad and actividad.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"actividad": "La actividad pertenece a otra organizacion."})
        if fuente and fuente.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"fuente": "La fuente pertenece a otra organizacion."})
        if evidencia and evidencia.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"evidencia": "La evidencia pertenece a otra organizacion."})
        numerico = attrs.get("valor_numerico", getattr(self.instance, "valor_numerico", None))
        texto = attrs.get("valor_texto", getattr(self.instance, "valor_texto", ""))
        if numerico is None and not texto:
            raise serializers.ValidationError("Debe informar un valor numerico o textual.")
        if numerico is not None and texto:
            raise serializers.ValidationError("Use solo un tipo de valor por observacion.")
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["actor"] = request.user
        validated_data["actividad"] = self.context["actividad"]
        return crear_entidad(Observacion, organizacion=self.context["organizacion"], datos=validated_data)

    def update(self, instance, validated_data):
        return actualizar_entidad(instance, validated_data)

    def get_evidencia_detalle(self, observacion):
        if not observacion.evidencia_id:
            return None
        return {"id": observacion.evidencia_id, "nombre": observacion.evidencia.nombre, "tipo_evidencia": observacion.evidencia.tipo_evidencia}


class ActividadOperacionalSerializer(serializers.ModelSerializer):
    unidad_nombre = serializers.CharField(source="unidad_operacional.nombre", read_only=True)
    proceso_nombre = serializers.CharField(source="proceso_operacional.nombre", read_only=True)
    observaciones_count = serializers.IntegerField(source="observaciones.count", read_only=True)
    observaciones = ObservacionSerializer(many=True, read_only=True)
    registros_emision_legacy_count = serializers.IntegerField(source="registros_emision_legacy.count", read_only=True)

    class Meta:
        model = ActividadOperacional
        fields = ["id", "tipo", "codigo", "nombre", "timestamp_inicio", "timestamp_fin", "unidad_operacional",
                  "unidad_nombre", "proceso_operacional", "proceso_nombre", "estado", "referencia_externa", "metadata",
                  "observaciones_count", "observaciones", "registros_emision_legacy_count", "created_at", "updated_at"]
        read_only_fields = ["id", "observaciones_count", "observaciones", "registros_emision_legacy_count", "created_at", "updated_at"]

    def validate(self, attrs):
        organizacion = self.context["organizacion"]
        unidad = attrs.get("unidad_operacional", getattr(self.instance, "unidad_operacional", None))
        proceso = attrs.get("proceso_operacional", getattr(self.instance, "proceso_operacional", None))
        if unidad and unidad.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"unidad_operacional": "La unidad pertenece a otra organizacion."})
        if proceso and proceso.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"proceso_operacional": "El proceso pertenece a otra organizacion."})
        return attrs

    def create(self, validated_data):
        return crear_entidad(ActividadOperacional, organizacion=self.context["organizacion"], datos=validated_data)

    def update(self, instance, validated_data):
        return actualizar_entidad(instance, validated_data)
