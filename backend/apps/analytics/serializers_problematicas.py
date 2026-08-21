from rest_framework import serializers

from .models import (
    AccionMejoraAmbiental,
    AlcanceProblematica,
    CicloReevaluacionProblematica,
    HistorialProblematicaAmbiental,
    IndicadorProblematica,
    MedicionSeguimientoAmbiental,
    ProblematicaAmbiental,
    ResultadoIntervencion,
    SnapshotIntervencion,
    SnapshotValorIndicador,
)


class ProblematicaAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblematicaAmbiental
        exclude = ["organizacion"]
        read_only_fields = [
            "estado",
            "valor_posterior",
            "mejora_absoluta",
            "mejora_porcentaje",
            "resultado_evaluacion",
            "created_at",
            "updated_at",
        ]

    def validate_obra(self, obra):
        if obra and obra.organizacion_id != self.context["organizacion"].id:
            raise serializers.ValidationError(
                "Debe pertenecer a la organizacion activa."
            )
        return obra


class AccionMejoraAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccionMejoraAmbiental
        exclude = ["problematica"]
        read_only_fields = [
            "estado",
            "fecha_seleccion",
            "fecha_inicio_efectiva",
            "implementada_at",
            "created_at",
            "updated_at",
        ]


class MedicionSeguimientoAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicionSeguimientoAmbiental
        exclude = ["problematica"]
        read_only_fields = ["created_at"]

    def validate(
        self,
        attrs,
    ):
        problem = self.context.get("problematica")

        for field in (
            "indicador_v2",
            "evidencia",
        ):
            value = attrs.get(field)

            if value and problem and value.organizacion_id != problem.organizacion_id:
                raise serializers.ValidationError(
                    {field: "La referencia pertenece a otra organizacion."}
                )

        action = attrs.get("accion")

        if action and problem and action.problematica_id != problem.id:
            raise serializers.ValidationError(
                {"accion": "La accion pertenece a otra problematica."}
            )

        indicator = attrs.get("indicador_v2")

        value = attrs.get("valor_indicador")

        if indicator and problem.obra_id and indicator.obra_id != problem.obra_id:
            raise serializers.ValidationError(
                {"indicador_v2": "El indicador pertenece a otra obra."}
            )

        if value and indicator and value.indicador_id != indicator.id:
            raise serializers.ValidationError(
                {"valor_indicador": "El valor no pertenece al indicador seleccionado."}
            )

        return attrs


class HistorialProblematicaAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialProblematicaAmbiental
        exclude = ["problematica"]


class AlcanceProblematicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlcanceProblematica
        exclude = ["problematica"]
        read_only_fields = ["created_at"]

    def validate(
        self,
        attrs,
    ):
        problem = self.context["problematica"]

        fields = (
            "unidad_operacional",
            "proceso_operacional",
            "activo_operacional",
            "actividad_operacional",
            "indicador",
        )

        if not any(attrs.get(field) for field in fields):
            raise serializers.ValidationError(
                "El alcance debe contener una referencia."
            )

        for field in fields:
            value = attrs.get(field)

            if value and value.organizacion_id != problem.organizacion_id:
                raise serializers.ValidationError(
                    {field: "La referencia pertenece a otra organizacion."}
                )

        activity = attrs.get("actividad_operacional")

        if problem.obra_id and activity and activity.obra_id != problem.obra_id:
            raise serializers.ValidationError(
                {"actividad_operacional": "La actividad pertenece a otra obra."}
            )

        indicator = attrs.get("indicador")

        if problem.obra_id and indicator and indicator.obra_id != problem.obra_id:
            raise serializers.ValidationError(
                {"indicador": "El indicador pertenece a otra obra."}
            )

        return attrs


class IndicadorProblematicaSerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(source="indicador.nombre", read_only=True)

    class Meta:
        model = IndicadorProblematica
        exclude = ["problematica"]

    def validate_indicador(
        self,
        value,
    ):
        problem = self.context["problematica"]

        if value.organizacion_id != problem.organizacion_id:
            raise serializers.ValidationError(
                "El indicador pertenece a otra organizacion."
            )

        if problem.obra_id and value.obra_id != problem.obra_id:
            raise serializers.ValidationError(
                "El indicador debe pertenecer a la misma obra de la problematica."
            )

        return value


class SnapshotValorSerializer(serializers.ModelSerializer):
    indicador_nombre = serializers.CharField(source="indicador.nombre", read_only=True)

    class Meta:
        model = SnapshotValorIndicador
        fields = [
            "id",
            "indicador",
            "indicador_nombre",
            "valor",
            "unidad",
            "periodo_inicio",
            "periodo_fin",
            "valor_indicador_origen",
        ]


class SnapshotIntervencionSerializer(serializers.ModelSerializer):
    valores = SnapshotValorSerializer(many=True, read_only=True)

    class Meta:
        model = SnapshotIntervencion
        fields = [
            "id",
            "problematica",
            "accion",
            "ciclo",
            "tipo",
            "fecha",
            "alcance_congelado",
            "indicadores_evaluados",
            "metadata_tecnica",
            "congelado",
            "valores",
            "created_at",
        ]


class ResultadoIntervencionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultadoIntervencion
        fields = "__all__"


class CicloReevaluacionSerializer(serializers.ModelSerializer):
    resultado_detalle = ResultadoIntervencionSerializer(
        source="resultado", read_only=True
    )

    class Meta:
        model = CicloReevaluacionProblematica
        fields = [
            "id",
            "numero",
            "accion",
            "snapshot_base",
            "snapshot_resultado",
            "resultado",
            "resultado_detalle",
            "fecha_inicio",
            "fecha_cierre",
            "motivo",
            "created_at",
        ]
