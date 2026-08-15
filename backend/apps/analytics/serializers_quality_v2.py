from rest_framework import serializers

from .models import (DiscrepanciaDato, EvaluacionCalidadDato, IndicadorAmbiental,
                     LineaBaseAmbiental, PoliticaConfianzaFuente, ValorIndicador)


class EvaluacionCalidadSerializer(serializers.ModelSerializer):
    observacion_detalle = serializers.SerializerMethodField()
    def get_observacion_detalle(self, obj):
        item = obj.observacion
        return {"id": item.id, "concepto": item.concepto, "valor": item.valor_numerico, "unidad": item.unidad, "fuente": item.fuente.nombre}
    class Meta:
        model = EvaluacionCalidadDato
        fields = ["id", "observacion", "observacion_detalle", "estado", "motivos", "dimensiones", "fecha_evaluacion", "version_reglas", "automatica", "evaluado_por"]


class DiscrepanciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscrepanciaDato
        fields = ["id", "actividad", "concepto", "observaciones", "estado", "diferencia_absoluta", "diferencia_relativa", "severidad", "resolucion", "observacion_seleccionada", "motivo", "responsable", "created_at", "updated_at"]
        read_only_fields = ["actividad", "concepto", "observaciones", "diferencia_absoluta", "diferencia_relativa", "severidad", "created_at", "updated_at"]

    def validate_observacion_seleccionada(self, value):
        if value and value.organizacion_id != self.instance.organizacion_id:
            raise serializers.ValidationError("La observacion pertenece a otra organizacion.")
        return value


class PoliticaFuenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoliticaConfianzaFuente
        fields = ["id", "organizacion", "concepto", "tipo_fuente", "prioridad", "activa", "descripcion"]


class ValorIndicadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValorIndicador
        fields = ["id", "periodo_inicio", "periodo_fin", "valor", "unidad", "fuente_calculo", "version", "metadata", "created_at"]


class IndicadorSerializer(serializers.ModelSerializer):
    valor_actual = serializers.SerializerMethodField()
    def get_valor_actual(self, obj):
        value = obj.valores.order_by("-periodo_fin", "-version").first()
        return ValorIndicadorSerializer(value).data if value else None
    class Meta:
        model = IndicadorAmbiental
        fields = ["id", "codigo", "nombre", "tipo", "alcance", "obra", "unidad", "descripcion", "origen_numerador", "origen_denominador", "direccion_deseable", "activo", "valor_actual", "created_at", "updated_at"]


class LineaBaseSerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(source="indicador.nombre", read_only=True)
    class Meta:
        model = LineaBaseAmbiental
        fields = ["id", "indicador", "indicador_nombre", "periodo_inicio", "periodo_fin", "metodo", "estado", "valor_base", "cantidad_periodos", "observaciones", "created_at"]
        read_only_fields = ["periodo_inicio", "periodo_fin", "estado", "valor_base", "cantidad_periodos", "observaciones", "created_at"]
