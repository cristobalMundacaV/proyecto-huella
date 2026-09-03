from rest_framework import serializers

from .models import (
    DiscrepanciaDato,
    EvaluacionCalidadDato,
    IndicadorAmbiental,
    LineaBaseAmbiental,
    PoliticaConfianzaFuente,
    ValorIndicador,
)
from .policies.quality import discrepancy_errors
from .services.quality_v2 import update_discrepancy
from .services.evidence_documents import current_document_result, current_evidence_version


class EvaluacionCalidadSerializer(serializers.ModelSerializer):
    observacion_detalle = serializers.SerializerMethodField()

    def get_observacion_detalle(
        self,
        obj,
    ):
        item = obj.observacion
        actividad = item.actividad
        obra = actividad.obra if actividad else None

        return {
            "id": item.id,
            "concepto": item.concepto,
            "valor": item.valor_numerico,
            "valor_texto": item.valor_texto,
            "unidad": item.unidad,
            "timestamp": item.timestamp_observacion,
            "estado": item.estado,
            "metodo_captura": item.metodo_captura,
            "naturaleza": item.naturaleza,
            "fuente": {
                "id": item.fuente_id,
                "nombre": item.fuente.nombre,
                "tipo": item.fuente.tipo,
            },
            "evidencia": (
                {
                    "id": item.evidencia_id,
                    "nombre": item.evidencia.nombre,
                    "estado_documental": current_document_result(item.evidencia, item).get("veredicto"),
                    "estado_procesamiento": getattr(current_evidence_version(item.evidencia, item), "estado_procesamiento", None),
                    "validacion_documental": current_document_result(item.evidencia, item),
                }
                if item.evidencia_id
                else None
            ),
            "actividad": (
                {
                    "id": actividad.id,
                    "nombre": actividad.nombre,
                    "tipo": actividad.tipo,
                }
                if actividad
                else None
            ),
            "obra": (
                {
                    "id": obra.id,
                    "nombre": obra.nombre,
                }
                if obra
                else None
            ),
        }

    class Meta:
        model = EvaluacionCalidadDato

        fields = [
            "id",
            "observacion",
            "observacion_detalle",
            "estado",
            "motivos",
            "dimensiones",
            "fecha_evaluacion",
            "version_reglas",
            "automatica",
            "evaluado_por",
        ]


class DiscrepanciaSerializer(serializers.ModelSerializer):
    observaciones_detalle = serializers.SerializerMethodField()

    actividad_detalle = serializers.SerializerMethodField()

    def get_actividad_detalle(
        self,
        obj,
    ):
        activity = obj.actividad

        if not activity:
            return None

        return {
            "id": activity.id,
            "nombre": activity.nombre,
            "tipo": activity.tipo,
            "obra": activity.obra_id,
        }

    def get_observaciones_detalle(
        self,
        obj,
    ):
        return [
            {
                "id": observation.id,
                "concepto": observation.concepto,
                "valor": observation.valor_numerico,
                "valor_texto": observation.valor_texto,
                "unidad": observation.unidad,
                "timestamp": observation.timestamp_observacion,
                "fuente": {
                    "id": observation.fuente_id,
                    "nombre": observation.fuente.nombre,
                    "tipo": observation.fuente.tipo,
                },
                "metodo_captura": observation.metodo_captura,
                "estado": observation.estado,
            }
            for observation in obj.observaciones.all()
        ]

    class Meta:
        model = DiscrepanciaDato

        fields = [
            "id",
            "actividad",
            "actividad_detalle",
            "concepto",
            "observaciones",
            "observaciones_detalle",
            "estado",
            "diferencia_absoluta",
            "diferencia_relativa",
            "severidad",
            "resolucion",
            "observacion_seleccionada",
            "motivo",
            "responsable",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "actividad",
            "concepto",
            "observaciones",
            "observaciones_detalle",
            "actividad_detalle",
            "diferencia_absoluta",
            "diferencia_relativa",
            "severidad",
            "created_at",
            "updated_at",
        ]

    def validate_observacion_seleccionada(
        self,
        value,
    ):
        return value

    def validate(self, attrs):
        errors = discrepancy_errors(self.instance, attrs)
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def update(self, instance, validated_data):
        return update_discrepancy(instance, validated_data)


class PoliticaFuenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoliticaConfianzaFuente
        fields = [
            "id",
            "organizacion",
            "concepto",
            "tipo_fuente",
            "prioridad",
            "activa",
            "descripcion",
        ]


class ValorIndicadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValorIndicador
        fields = [
            "id",
            "periodo_inicio",
            "periodo_fin",
            "valor",
            "unidad",
            "fuente_calculo",
            "version",
            "metadata",
            "created_at",
        ]


class IndicadorSerializer(serializers.ModelSerializer):
    valor_actual = serializers.SerializerMethodField()

    def get_valor_actual(self, obj):
        value = obj.valores.order_by("-periodo_fin", "-version").first()
        if value and value.metadata.get("disponible") is False:
            return None
        return ValorIndicadorSerializer(value).data if value else None

    class Meta:
        model = IndicadorAmbiental
        fields = [
            "id",
            "codigo",
            "nombre",
            "tipo",
            "alcance",
            "obra",
            "unidad",
            "descripcion",
            "origen_numerador",
            "origen_denominador",
            "direccion_deseable",
            "activo",
            "valor_actual",
            "created_at",
            "updated_at",
        ]


class LineaBaseSerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(source="indicador.nombre", read_only=True)

    class Meta:
        model = LineaBaseAmbiental
        fields = [
            "id",
            "indicador",
            "indicador_nombre",
            "periodo_inicio",
            "periodo_fin",
            "metodo",
            "estado",
            "valor_base",
            "cantidad_periodos",
            "observaciones",
            "created_at",
        ]
        read_only_fields = [
            "periodo_inicio",
            "periodo_fin",
            "estado",
            "valor_base",
            "cantidad_periodos",
            "observaciones",
            "created_at",
        ]
