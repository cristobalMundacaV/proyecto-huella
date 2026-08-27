from rest_framework import serializers

from .models import (
    EvidenciaObra,
    FuenteDatos,
    Observacion,
    PuntoAmbientalOperacional,
    RegistroFlujoAmbiental,
    VersionEvidencia,
)
from .policies.environmental_flows import (
    environmental_record_errors,
    point_relation_errors,
)
from .serializers_activity_core import ObservacionSerializer
from .services.sector_flows_v1 import save_environmental_record, save_point


class PuntoAmbientalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuntoAmbientalOperacional
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        errors = point_relation_errors(
            attrs, self.context["organizacion"], self.instance
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, data):
        return save_point(
            PuntoAmbientalOperacional(), self.context["organizacion"], data
        )

    def update(self, instance, data):
        return save_point(instance, self.context["organizacion"], data)


class RegistroFlujoAmbientalSerializer(serializers.ModelSerializer):
    concepto = serializers.SlugField(max_length=120, required=False, write_only=True)
    valor_numerico = serializers.DecimalField(
        max_digits=20,
        decimal_places=6,
        required=False,
        allow_null=True,
        write_only=True,
    )
    valor_texto = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    unidad = serializers.CharField(
        max_length=40, required=False, allow_blank=True, write_only=True
    )
    fuente = serializers.PrimaryKeyRelatedField(
        queryset=FuenteDatos.objects.all(), required=False, write_only=True
    )
    evidencia = serializers.PrimaryKeyRelatedField(
        queryset=EvidenciaObra.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    version_evidencia = serializers.PrimaryKeyRelatedField(
        queryset=VersionEvidencia.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    metodo_captura = serializers.ChoiceField(
        choices=Observacion.MetodoCaptura.choices,
        default=Observacion.MetodoCaptura.MANUAL,
        write_only=True,
    )
    naturaleza = serializers.ChoiceField(
        choices=Observacion.Naturaleza.choices,
        default=Observacion.Naturaleza.DECLARATIVO,
        write_only=True,
    )
    observaciones = ObservacionSerializer(
        source="actividad.observaciones", many=True, read_only=True
    )

    class Meta:
        model = RegistroFlujoAmbiental
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        errors = environmental_record_errors(
            attrs, self.context["organizacion"], self.instance
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _save(self, instance, data):
        request = self.context.get("request")
        actor = request.user if request and request.user.is_authenticated else None
        return save_environmental_record(
            instance, self.context["organizacion"], data, actor
        )

    def create(self, data):
        return self._save(RegistroFlujoAmbiental(), data)

    def update(self, instance, data):
        return self._save(instance, data)
