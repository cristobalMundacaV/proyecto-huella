from rest_framework import serializers

from .models import (
    CalibracionSensor,
    DispositivoSensor,
    InstalacionSensor,
    LecturaSensorV2,
)
from .services_v2 import (
    actualizar_estado_tecnico,
    registrar_calibracion,
    registrar_lectura,
)


class InstalacionSensorSerializer(serializers.ModelSerializer):
    activo_nombre = serializers.CharField(source="activo.nombre", read_only=True)

    class Meta:
        model = InstalacionSensor
        fields = [
            "id",
            "activo",
            "activo_nombre",
            "unidad_operacional",
            "proceso_operacional",
            "fecha_instalacion",
            "fecha_retiro",
            "ubicacion",
            "estado",
            "responsable",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        org = self.context["sensor"].organizacion
        for field in (
            "obra",
            "punto_ambiental",
            "activo_operacional",
            "unidad_operacional",
            "proceso_operacional",
        ):
            relation = attrs.get(field)
            if relation and relation.organizacion_id != org.id:
                raise serializers.ValidationError(
                    {field: "La relacion pertenece a otra organizacion."}
                )

        obra = attrs.get(
            "obra",
            getattr(self.instance, "obra", None),
        )
        punto = attrs.get(
            "punto_ambiental",
            getattr(
                self.instance,
                "punto_ambiental",
                None,
            ),
        )

        if obra and punto and punto.obra_id and punto.obra_id != obra.id:
            raise serializers.ValidationError(
                {"punto_ambiental": "El punto ambiental pertenece a otra obra."}
            )
        return attrs

    def create(self, data):
        item = InstalacionSensor(sensor=self.context["sensor"], **data)
        item.full_clean()
        item.save()
        return item


class CalibracionSensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalibracionSensor
        fields = [
            "id",
            "fecha",
            "tipo",
            "resultado",
            "fecha_proxima_calibracion",
            "responsable",
            "evidencia",
            "observaciones",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_evidencia(self, evidencia):
        if (
            evidencia
            and evidencia.organizacion_id != self.context["sensor"].organizacion_id
        ):
            raise serializers.ValidationError(
                "La evidencia pertenece a otra organizacion."
            )
        return evidencia

    def create(self, data):
        return registrar_calibracion(self.context["sensor"], data)


class LecturaSensorV2Serializer(serializers.ModelSerializer):
    observacion_id = serializers.IntegerField(source="observacion.id", read_only=True)
    fuente_nombre = serializers.CharField(
        source="observacion.fuente.nombre", read_only=True
    )

    class Meta:
        model = LecturaSensorV2
        fields = [
            "id",
            "actividad",
            "timestamp",
            "concepto",
            "valor_numerico",
            "unidad",
            "metadata_tecnica",
            "calidad_tecnica",
            "observacion_id",
            "fuente_nombre",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "calidad_tecnica",
            "observacion_id",
            "fuente_nombre",
            "created_at",
        ]

    def validate_actividad(self, actividad):
        if (
            actividad
            and actividad.organizacion_id != self.context["sensor"].organizacion_id
        ):
            raise serializers.ValidationError(
                "La actividad pertenece a otra organizacion."
            )
        return actividad

    def create(self, data):
        return registrar_lectura(self.context["sensor"], data)


class DispositivoSensorV2Serializer(serializers.ModelSerializer):
    activo_nombre = serializers.CharField(
        source="activo_operacional.nombre",
        read_only=True,
    )
    obra_nombre = serializers.CharField(
        source="obra.nombre",
        read_only=True,
    )
    punto_ambiental_nombre = serializers.CharField(
        source="punto_ambiental.nombre",
        read_only=True,
    )
    ultima_calibracion = serializers.SerializerMethodField()
    proxima_calibracion = serializers.SerializerMethodField()
    instalaciones = InstalacionSensorSerializer(many=True, read_only=True)
    calibraciones = CalibracionSensorSerializer(many=True, read_only=True)
    lecturas = serializers.SerializerMethodField()

    class Meta:
        model = DispositivoSensor
        fields = [
            "id",
            "dispositivo_id",
            "nombre",
            "tipo_sensor",
            "fabricante",
            "modelo",
            "estado",
            "fecha_alta",
            "last_seen_at",
            "obra",
            "obra_nombre",
            "ambito_operacional",
            "punto_ambiental",
            "punto_ambiental_nombre",
            "activo_operacional",
            "activo_nombre",
            "unidad_operacional",
            "proceso_operacional",
            "ubicacion",
            "descripcion",
            "metadata",
            "instalaciones",
            "calibraciones",
            "lecturas",
            "ultima_calibracion",
            "proxima_calibracion",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_seen_at",
            "instalaciones",
            "calibraciones",
            "lecturas",
            "ultima_calibracion",
            "proxima_calibracion",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        org = self.context["organizacion"]

        for field in (
            "obra",
            "punto_ambiental",
            "activo_operacional",
            "unidad_operacional",
            "proceso_operacional",
        ):
            relation = attrs.get(
                field,
                getattr(
                    self.instance,
                    field,
                    None,
                ),
            )

            if relation and relation.organizacion_id != org.id:
                raise serializers.ValidationError(
                    {field: "La relacion pertenece a otra organizacion."}
                )

        obra = attrs.get(
            "obra",
            getattr(
                self.instance,
                "obra",
                None,
            ),
        )

        punto = attrs.get(
            "punto_ambiental",
            getattr(
                self.instance,
                "punto_ambiental",
                None,
            ),
        )

        if obra and punto and punto.obra_id and punto.obra_id != obra.id:
            raise serializers.ValidationError(
                {"punto_ambiental": "El punto ambiental pertenece a otra obra."}
            )

        return attrs

    def create(self, data):
        item = DispositivoSensor(
            organizacion=self.context["organizacion"], activo=True, **data
        )
        item.full_clean()
        item.save()
        return item

    def update(self, instance, data):
        for field, value in data.items():
            setattr(instance, field, value)
        instance.full_clean()
        instance.save()
        return instance

    def get_ultima_calibracion(self, sensor):
        item = sensor.calibraciones.order_by("-fecha").first()
        return item.fecha if item else None

    def get_proxima_calibracion(self, sensor):
        item = sensor.calibraciones.order_by("-fecha").first()
        return item.fecha_proxima_calibracion if item else None

    def get_lecturas(self, sensor):
        return LecturaSensorV2Serializer(
            sensor.lecturas_v2.select_related("observacion__fuente")[:20], many=True
        ).data

    def to_representation(self, instance):
        actualizar_estado_tecnico(instance)
        return super().to_representation(instance)
