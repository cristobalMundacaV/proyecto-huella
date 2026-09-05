from rest_framework import serializers

from .models import (
    CalculoAmbiental,
    FactorAmbiental,
    FormulaAmbiental,
    ImpactoAmbiental,
    InputCalculoAmbiental,
    MetodologiaAmbiental,
    VariableFormula,
    VersionFactorAmbiental,
    VersionMetodologia,
)


class VariableFormulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariableFormula
        fields = [
            "id",
            "clave",
            "concepto_observacion",
            "unidad_esperada",
            "obligatoria",
            "criticidad",
            "rol",
            "descripcion",
        ]

    def validate(self, attrs):
        criticality = attrs.get(
            "criticidad", getattr(self.instance, "criticidad", "critica")
        )
        attrs["obligatoria"] = criticality == "critica"
        return attrs


class FormulaAmbientalSerializer(serializers.ModelSerializer):
    variables = VariableFormulaSerializer(many=True, read_only=True)
    factor_codigo = serializers.CharField(
        source="factor_ambiental.codigo", read_only=True
    )

    class Meta:
        model = FormulaAmbiental
        fields = [
            "id",
            "codigo",
            "tipo",
            "expresion_legible",
            "version",
            "factor_ambiental",
            "factor_codigo",
            "variables",
        ]


class VersionMetodologiaSerializer(serializers.ModelSerializer):
    formula = FormulaAmbientalSerializer(read_only=True)

    class Meta:
        model = VersionMetodologia
        fields = [
            "id",
            "version",
            "estado",
            "descripcion_tecnica",
            "fuente_referencia",
            "vigencia_desde",
            "vigencia_hasta",
            "aplicabilidad",
            "prioridad",
            "requiere_revision_profesional",
            "tipo_resultado",
            "validado_por",
            "fecha_validacion",
            "formula",
            "created_at",
        ]
        read_only_fields = ["estado", "validado_por", "fecha_validacion"]


class MetodologiaSerializer(serializers.ModelSerializer):
    versiones = VersionMetodologiaSerializer(many=True, read_only=True)

    class Meta:
        model = MetodologiaAmbiental
        fields = [
            "id",
            "codigo",
            "nombre",
            "categoria",
            "flujo",
            "descripcion",
            "organizacion",
            "activa",
            "versiones",
            "created_at",
            "updated_at",
        ]


class VersionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionFactorAmbiental
        fields = [
            "id",
            "version",
            "valor",
            "fuente",
            "referencia",
            "region",
            "vigencia_desde",
            "vigencia_hasta",
            "estado",
            "contexto",
            "created_at",
        ]


class FactorAmbientalSerializer(serializers.ModelSerializer):
    versiones = VersionFactorSerializer(many=True, read_only=True)

    class Meta:
        model = FactorAmbiental
        fields = [
            "id",
            "codigo",
            "nombre",
            "categoria",
            "sustancia_impacto",
            "unidad_entrada",
            "unidad_resultado",
            "contexto",
            "organizacion",
            "versiones",
            "created_at",
        ]


class InputCalculoSerializer(serializers.ModelSerializer):
    variable_clave = serializers.CharField(source="variable.clave", read_only=True)
    observacion_detalle = serializers.SerializerMethodField()

    class Meta:
        model = InputCalculoAmbiental
        fields = [
            "id",
            "variable",
            "variable_clave",
            "observacion",
            "observacion_detalle",
            "valor_utilizado",
            "unidad",
            "concepto",
            "fuente",
            "evidencia",
            "version_evidencia",
        ]

    def get_observacion_detalle(self, item):
        return {
            "id": item.observacion_id,
            "concepto": item.observacion.concepto,
            "fuente": item.fuente.nombre,
        }


class CalculoAmbientalSerializer(serializers.ModelSerializer):
    metodologia = serializers.CharField(
        source="version_metodologia.metodologia.nombre", read_only=True
    )
    metodologia_version = serializers.IntegerField(
        source="version_metodologia.version", read_only=True
    )
    formula_detalle = FormulaAmbientalSerializer(source="formula", read_only=True)
    factor_nombre = serializers.CharField(
        source="version_factor.factor.nombre", read_only=True
    )
    factor_version = serializers.IntegerField(
        source="version_factor.version", read_only=True
    )
    factor_valor = serializers.DecimalField(
        source="version_factor.valor", max_digits=20, decimal_places=10, read_only=True
    )
    inputs = InputCalculoSerializer(many=True, read_only=True)

    class Meta:
        model = CalculoAmbiental
        fields = [
            "id",
            "actividad",
            "metodologia",
            "metodologia_version",
            "version_metodologia",
            "formula",
            "formula_detalle",
            "version_factor",
            "factor_nombre",
            "factor_version",
            "factor_valor",
            "resultado",
            "unidad_resultado",
            "estado",
            "fecha_calculo",
            "version_interna",
            "formula_aplicada",
            "advertencias",
            "completitud",
            "tipo_resultado",
            "recalculo_de",
            "motivo_recalculo",
            "snapshot_tecnico",
            "inputs",
        ]
        read_only_fields = fields


class ImpactoAmbientalSerializer(serializers.ModelSerializer):
    actividad_nombre = serializers.CharField(
        source="actividad.nombre",
        read_only=True,
    )

    obra = serializers.IntegerField(
        source="actividad.obra_id",
        read_only=True,
    )

    calculo_estado = serializers.CharField(
        source="calculo.estado",
        read_only=True,
    )

    class Meta:
        model = ImpactoAmbiental

        fields = [
            "id",
            "actividad",
            "actividad_nombre",
            "obra",
            "calculo",
            "calculo_estado",
            "tipo",
            "categoria",
            "valor",
            "unidad",
            "timestamp",
            "created_at",
        ]
