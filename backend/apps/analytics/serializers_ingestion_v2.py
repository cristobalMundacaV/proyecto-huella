from rest_framework import serializers

from .models import (
    MapeoColumna,
    PlantillaMapeo,
    ProcesoIngesta,
    RegistroExtraido,
    VersionEvidencia,
)


class MapeoColumnaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapeoColumna
        fields = [
            "id",
            "columna_origen",
            "columna_normalizada",
            "concepto_normalizado",
            "unidad_esperada",
        ]


class PlantillaMapeoSerializer(serializers.ModelSerializer):
    mapeos = MapeoColumnaSerializer(many=True, read_only=True)
    fuente_nombre = serializers.CharField(source="fuente_datos.nombre", read_only=True)

    class Meta:
        model = PlantillaMapeo
        fields = [
            "id",
            "nombre",
            "formato",
            "tipo_ingesta",
            "destino_operacional",
            "flujo",
            "version",
            "activa",
            "fuente_datos",
            "fuente_nombre",
            "mapeos",
            "created_at",
        ]


class RegistroExtraidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroExtraido
        fields = [
            "id",
            "numero_fila",
            "origen",
            "datos_originales",
            "datos_normalizados",
            "auto_confirmable",
            "estado",
            "errores",
            "actividad_creada",
            "resultado_procesamiento",
            "procesado_at",
        ]


class VersionEvidenciaSerializer(serializers.ModelSerializer):
    evidencia_nombre = serializers.CharField(source="evidencia.nombre", read_only=True)

    class Meta:
        model = VersionEvidencia
        fields = [
            "id",
            "evidencia",
            "evidencia_nombre",
            "version",
            "nombre_original",
            "tipo_documental",
            "checksum_sha256",
            "estado_procesamiento",
            "metadata_tecnica",
            "resultado_documental",
            "created_at",
        ]

    resultado_documental = serializers.SerializerMethodField()

    def get_resultado_documental(self, instance):
        return (instance.metadata_tecnica or {}).get("document_result")


class ProcesoIngestaSerializer(serializers.ModelSerializer):
    version_evidencia_detalle = VersionEvidenciaSerializer(
        source="version_evidencia", read_only=True
    )
    fuente_nombre = serializers.CharField(source="fuente_datos.nombre", read_only=True)
    plantilla = PlantillaMapeoSerializer(source="plantilla_mapeo", read_only=True)
    registros_extraidos = RegistroExtraidoSerializer(many=True, read_only=True)

    class Meta:
        model = ProcesoIngesta
        fields = [
            "id",
            "version_evidencia",
            "version_evidencia_detalle",
            "fuente_datos",
            "fuente_nombre",
            "plantilla_mapeo",
            "plantilla",
            "tipo_ingesta",
            "destino_operacional",
            "flujo",
            "clasificacion_sugerida",
            "clasificacion_confirmada",
            "contexto_sugerido",
            "contexto_confirmado",
            "estado",
            "fecha_inicio",
            "fecha_fin",
            "filas_detectadas",
            "filas_procesadas",
            "filas_con_error",
            "resumen_errores",
            "registros_extraidos",
            "created_at",
            "updated_at",
        ]
