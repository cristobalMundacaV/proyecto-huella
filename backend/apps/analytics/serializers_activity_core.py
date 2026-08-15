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
    version_evidencia_detalle = serializers.SerializerMethodField()
    sensor_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Observacion
        fields = ["id", "actividad", "fuente", "fuente_detalle", "concepto", "valor_numerico", "valor_texto",
                  "unidad", "timestamp_observacion", "metodo_captura", "naturaleza", "actor", "evidencia",
                  "evidencia_detalle", "version_evidencia", "version_evidencia_detalle", "sensor_detalle", "estado", "created_at", "updated_at"]
        read_only_fields = ["id", "actividad", "actor", "created_at", "updated_at"]

    def validate(self, attrs):
        organizacion = self.context["organizacion"]
        actividad = self.context.get("actividad") or getattr(self.instance, "actividad", None)
        actividad_enviada = self.initial_data.get("actividad") if hasattr(self, "initial_data") else None
        if actividad_enviada is not None and actividad and str(actividad_enviada) != str(actividad.id):
            raise serializers.ValidationError({"actividad": "La actividad no coincide con el recurso solicitado."})
        fuente = attrs.get("fuente", getattr(self.instance, "fuente", None))
        evidencia = attrs.get("evidencia", getattr(self.instance, "evidencia", None))
        version_evidencia = attrs.get("version_evidencia", getattr(self.instance, "version_evidencia", None))
        if actividad and actividad.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"actividad": "La actividad pertenece a otra organizacion."})
        if fuente and fuente.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"fuente": "La fuente pertenece a otra organizacion."})
        if evidencia and evidencia.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"evidencia": "La evidencia pertenece a otra organizacion."})
        if version_evidencia and version_evidencia.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"version_evidencia": "La version de evidencia pertenece a otra organizacion."})
        if version_evidencia and evidencia and version_evidencia.evidencia_id != evidencia.id:
            raise serializers.ValidationError({"version_evidencia": "La version no pertenece a la evidencia asociada."})
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

    def get_version_evidencia_detalle(self, observacion):
        if not observacion.version_evidencia_id:
            return None
        version = observacion.version_evidencia
        return {"id": version.id, "version": version.version, "nombre_original": version.nombre_original, "checksum_sha256": version.checksum_sha256}

    def get_sensor_detalle(self, observacion):
        lectura = getattr(observacion, "lectura_sensor_v2", None)
        if not lectura:
            return None
        return {"id": lectura.sensor_id, "identificador": lectura.sensor.dispositivo_id, "nombre": lectura.sensor.nombre,
                "lectura_id": lectura.id, "calidad_tecnica": lectura.calidad_tecnica}


class ActividadOperacionalSerializer(serializers.ModelSerializer):
    unidad_nombre = serializers.CharField(source="unidad_operacional.nombre", read_only=True)
    proceso_nombre = serializers.CharField(source="proceso_operacional.nombre", read_only=True)
    observaciones_count = serializers.IntegerField(source="observaciones.count", read_only=True)
    observaciones = ObservacionSerializer(many=True, read_only=True)
    registros_emision_legacy_count = serializers.IntegerField(source="registros_emision_legacy.count", read_only=True)

    class Meta:
        model = ActividadOperacional
        fields = ["id", "obra", "tipo", "codigo", "nombre", "timestamp_inicio", "timestamp_fin", "unidad_operacional",
                  "unidad_nombre", "proceso_operacional", "proceso_nombre", "activos", "estado", "referencia_externa", "metadata",
                  "observaciones_count", "observaciones", "registros_emision_legacy_count", "created_at", "updated_at"]
        read_only_fields = ["id", "observaciones_count", "observaciones", "registros_emision_legacy_count", "created_at", "updated_at"]

    def validate(self, attrs):
        organizacion = self.context["organizacion"]
        unidad = attrs.get("unidad_operacional", getattr(self.instance, "unidad_operacional", None))
        proceso = attrs.get("proceso_operacional", getattr(self.instance, "proceso_operacional", None))
        obra = attrs.get("obra", getattr(self.instance, "obra", None))
        if unidad and unidad.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"unidad_operacional": "La unidad pertenece a otra organizacion."})
        if proceso and proceso.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"proceso_operacional": "El proceso pertenece a otra organizacion."})
        if obra and obra.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"obra": "La obra pertenece a otra organizacion."})
        if any(activo.organizacion_id != organizacion.id for activo in attrs.get("activos", [])):
            raise serializers.ValidationError({"activos": "Todos los activos deben pertenecer a la organizacion."})
        return attrs

    def create(self, validated_data):
        activos = validated_data.pop("activos", [])
        actividad = crear_entidad(ActividadOperacional, organizacion=self.context["organizacion"], datos=validated_data)
        actividad.activos.set(activos)
        return actividad

    def update(self, instance, validated_data):
        activos = validated_data.pop("activos", None)
        actividad = actualizar_entidad(instance, validated_data)
        if activos is not None:
            actividad.activos.set(activos)
        return actividad
