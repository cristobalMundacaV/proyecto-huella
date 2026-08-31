from rest_framework import serializers

from .models import ActividadOperacional, FuenteDatos, Observacion
from .policies.activity_core import (
    activity_relation_errors,
    observation_context_errors,
    observation_value_error,
)
from .services.activity_core import (
    actualizar_entidad,
    create_activity,
    create_observation,
    crear_entidad,
    update_activity,
    update_observation,
)
from .services.evidence_documents import current_document_result, current_evidence_version


class FuenteDatosSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuenteDatos
        fields = [
            "id",
            "nombre",
            "tipo",
            "descripcion",
            "activa",
            "identificador_externo",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        return crear_entidad(
            FuenteDatos, organizacion=self.context["organizacion"], datos=validated_data
        )

    def update(self, instance, validated_data):
        return actualizar_entidad(instance, validated_data)


class ObservacionSerializer(serializers.ModelSerializer):
    fuente_detalle = FuenteDatosSerializer(source="fuente", read_only=True)
    evidencia_detalle = serializers.SerializerMethodField()
    version_evidencia_detalle = serializers.SerializerMethodField()
    sensor_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Observacion
        fields = [
            "id",
            "actividad",
            "fuente",
            "fuente_detalle",
            "concepto",
            "valor_numerico",
            "valor_texto",
            "unidad",
            "timestamp_observacion",
            "metodo_captura",
            "naturaleza",
            "actor",
            "evidencia",
            "evidencia_detalle",
            "version_evidencia",
            "version_evidencia_detalle",
            "sensor_detalle",
            "estado",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "actividad", "actor", "created_at", "updated_at"]

    def validate(self, attrs):
        organizacion = self.context["organizacion"]
        actividad = self.context.get("actividad") or getattr(
            self.instance, "actividad", None
        )
        actividad_enviada = (
            self.initial_data.get("actividad")
            if hasattr(self, "initial_data")
            else None
        )
        fuente = attrs.get("fuente", getattr(self.instance, "fuente", None))
        evidencia = attrs.get("evidencia", getattr(self.instance, "evidencia", None))
        version_evidencia = attrs.get(
            "version_evidencia", getattr(self.instance, "version_evidencia", None)
        )
        errors = observation_context_errors(
            organization=organizacion,
            activity=actividad,
            submitted_activity=actividad_enviada,
            source=fuente,
            evidence=evidencia,
            evidence_version=version_evidencia,
        )
        if errors:
            raise serializers.ValidationError(errors)
        numerico = attrs.get(
            "valor_numerico", getattr(self.instance, "valor_numerico", None)
        )
        texto = attrs.get("valor_texto", getattr(self.instance, "valor_texto", ""))
        value_error = observation_value_error(numeric_value=numerico, text_value=texto)
        if value_error:
            raise serializers.ValidationError(value_error)
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        actor = request.user if request and request.user.is_authenticated else None
        return create_observation(
            organization=self.context["organizacion"],
            activity=self.context["actividad"],
            actor=actor,
            data=validated_data,
        )

    def update(self, instance, validated_data):
        return update_observation(observation=instance, data=validated_data)

    def get_evidencia_detalle(self, observacion):
        if not observacion.evidencia_id:
            return None
        return {
            "id": observacion.evidencia_id,
            "nombre": observacion.evidencia.nombre,
            "tipo_evidencia": observacion.evidencia.tipo_evidencia,
            "estado_documental": current_document_result(observacion.evidencia, observacion).get("veredicto"),
            "estado_procesamiento": getattr(current_evidence_version(observacion.evidencia, observacion), "estado_procesamiento", None),
            "validacion_documental": current_document_result(observacion.evidencia, observacion),
        }

    def get_version_evidencia_detalle(self, observacion):
        if not observacion.version_evidencia_id:
            return None
        version = observacion.version_evidencia
        return {
            "id": version.id,
            "version": version.version,
            "nombre_original": version.nombre_original,
            "checksum_sha256": version.checksum_sha256,
            "estado_procesamiento": version.estado_procesamiento,
            "resultado_documental": (version.metadata_tecnica or {}).get("document_result"),
        }

    def get_sensor_detalle(self, observacion):
        lectura = getattr(observacion, "lectura_sensor_v2", None)
        if not lectura:
            return None
        return {
            "id": lectura.sensor_id,
            "identificador": lectura.sensor.dispositivo_id,
            "nombre": lectura.sensor.nombre,
            "lectura_id": lectura.id,
            "calidad_tecnica": lectura.calidad_tecnica,
        }


class ActividadOperacionalSerializer(serializers.ModelSerializer):
    unidad_nombre = serializers.CharField(
        source="unidad_operacional.nombre", read_only=True
    )
    proceso_nombre = serializers.CharField(
        source="proceso_operacional.nombre", read_only=True
    )
    observaciones_count = serializers.IntegerField(
        source="observaciones.count", read_only=True
    )
    observaciones = ObservacionSerializer(many=True, read_only=True)
    registros_emision_legacy_count = serializers.IntegerField(
        source="registros_emision_legacy.count", read_only=True
    )

    class Meta:
        model = ActividadOperacional
        fields = [
            "id",
            "obra",
            "tipo",
            "codigo",
            "nombre",
            "timestamp_inicio",
            "timestamp_fin",
            "unidad_operacional",
            "unidad_nombre",
            "proceso_operacional",
            "proceso_nombre",
            "activos",
            "estado",
            "referencia_externa",
            "metadata",
            "observaciones_count",
            "observaciones",
            "registros_emision_legacy_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "observaciones_count",
            "observaciones",
            "registros_emision_legacy_count",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        organizacion = self.context["organizacion"]
        unidad = attrs.get(
            "unidad_operacional", getattr(self.instance, "unidad_operacional", None)
        )
        proceso = attrs.get(
            "proceso_operacional", getattr(self.instance, "proceso_operacional", None)
        )
        obra = attrs.get("obra", getattr(self.instance, "obra", None))
        errors = activity_relation_errors(
            organization=organizacion,
            unit=unidad,
            process=proceso,
            work=obra,
            assets=attrs.get("activos", []),
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        return create_activity(
            organization=self.context["organizacion"], data=validated_data
        )

    def update(self, instance, validated_data):
        return update_activity(activity=instance, data=validated_data)
