from uuid import uuid4

from django.db import transaction
from rest_framework import serializers

from .models import ActividadOperacional, EventoMaterial, LoteMaterial, MaterialOperacional
from .serializers_activity_core import ObservacionSerializer
from .policies.materials import material_event_errors, tenant_relation_errors
from .services.materials_v2 import save_entity, save_material_event
from .services.evidence_taxonomy import validate_evidence_type
from .services.quality_v2 import ensure_current_quality_evaluation


class MaterialOperacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialOperacional
        exclude = ["organizacion"]
        read_only_fields = ["id", "codigo", "created_at", "updated_at"]

    def create(self, data):
        data["codigo"] = f"MAT-{uuid4().hex.upper()}"
        return save_entity(MaterialOperacional(), self.context["organizacion"], data)

    def update(self, instance, data):
        return save_entity(instance, self.context["organizacion"], data)


class LoteMaterialSerializer(serializers.ModelSerializer):
    material_nombre = serializers.CharField(source="material.nombre", read_only=True)

    class Meta:
        model = LoteMaterial
        exclude = ["organizacion"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        organization = self.context["organizacion"]
        errors = tenant_relation_errors(
            attrs,
            organization,
            ("material", "fuente", "evidencia", "version_evidencia"),
            self.instance,
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, data):
        return save_entity(LoteMaterial(), self.context["organizacion"], data)

    def update(self, instance, data):
        return save_entity(instance, self.context["organizacion"], data)


class ActividadEventoMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActividadOperacional
        fields = ["id", "codigo", "nombre", "tipo", "estado", "timestamp_inicio"]


class EventoMaterialSerializer(serializers.ModelSerializer):
    actividad_detalle = ActividadEventoMaterialSerializer(source="actividad", read_only=True)
    cantidad = serializers.DecimalField(
        max_digits=20, decimal_places=6, required=False, write_only=True, min_value=0
    )
    unidad = serializers.CharField(max_length=40, required=False, write_only=True)
    evidencia_archivo = serializers.FileField(required=False, write_only=True)
    evidencia_nombre = serializers.CharField(
        required=False, allow_blank=True, max_length=240, write_only=True
    )
    evidencia_tipo = serializers.CharField(
        required=False, allow_blank=True, max_length=40, write_only=True
    )
    cantidad_detalle = ObservacionSerializer(
        source="observacion_cantidad", read_only=True
    )
    material_nombre = serializers.CharField(source="material.nombre", read_only=True)
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    proceso_nombre = serializers.CharField(source="proceso.nombre", read_only=True)

    class Meta:
        model = EventoMaterial
        exclude = ["organizacion"]
        read_only_fields = ["id", "observacion_cantidad", "created_at", "updated_at"]

    def validate(self, attrs):
        uploaded_file = attrs.get("evidencia_archivo")
        evidence_type = attrs.get("evidencia_tipo")
        if uploaded_file and not evidence_type:
            raise serializers.ValidationError(
                {"evidencia_tipo": "Selecciona el tipo de respaldo."}
            )
        if evidence_type and not uploaded_file:
            raise serializers.ValidationError(
                {"evidencia_archivo": "Adjunta el archivo del respaldo."}
            )
        if uploaded_file:
            attrs["evidencia_tipo"] = validate_evidence_type(
                evidence_type, "materiales"
            )
        errors = material_event_errors(
            attrs, self.context["organizacion"], self.instance
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _save(self, instance, data):
        request = self.context.get("request")
        actor = request.user if request and request.user.is_authenticated else None
        uploaded_file = data.pop("evidencia_archivo", None)
        evidence_name = data.pop("evidencia_nombre", "")
        evidence_type = data.pop("evidencia_tipo", "")
        stored_files = []
        try:
            with transaction.atomic():
                if uploaded_file:
                    from .serializers import EvidenciaObraSerializer

                    evidence_serializer = EvidenciaObraSerializer(
                        data={
                            "organizacion": self.context["organizacion"].id,
                            "obra": data.get("obra").id if data.get("obra") else None,
                            "archivo": uploaded_file,
                            "nombre": (evidence_name or uploaded_file.name)[:240],
                            "tipo_evidencia": evidence_type,
                            "metadata_extraccion": {
                                "origen_operacional": True,
                                "evento_material": True,
                                "dominio": "materiales",
                                "mime_type": uploaded_file.content_type or "",
                                "nombre_original": uploaded_file.name,
                            },
                        },
                        context={"request": request},
                    )
                    evidence_serializer.is_valid(raise_exception=True)
                    evidence = evidence_serializer.save(
                        usuario_origen=actor, metodo_captura="manual"
                    )
                    evidence_version = evidence._created_version
                    stored_files = [evidence.archivo, evidence_version.archivo]
                    data["evidencia"] = evidence
                    data["version_evidencia"] = evidence_version
                event = save_material_event(
                    instance, self.context["organizacion"], data, actor
                )
                if event.observacion_cantidad_id:
                    ensure_current_quality_evaluation(event.observacion_cantidad)
                return event
        except Exception:
            for stored_file in stored_files:
                if stored_file and stored_file.name:
                    stored_file.storage.delete(stored_file.name)
            raise

    def create(self, data):
        return self._save(EventoMaterial(), data)

    def update(self, instance, data):
        return self._save(instance, data)
