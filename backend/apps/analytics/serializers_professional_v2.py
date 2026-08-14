from rest_framework import serializers

from .models import (EventoAuditoriaAmbiental, ExpedienteAmbiental,
                     HallazgoRevisionProfesional, InformeAmbiental,
                     RevisionProfesionalAmbiental, SnapshotInformeAmbiental)


class HallazgoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HallazgoRevisionProfesional
        exclude = ["revision"]
        read_only_fields = ["created_at"]


class RevisionProfesionalSerializer(serializers.ModelSerializer):
    hallazgos = HallazgoSerializer(many=True, read_only=True)
    class Meta:
        model = RevisionProfesionalAmbiental
        exclude = ["organizacion"]
        read_only_fields = ["estado", "profesional", "profesional_nombre", "profesional_cargo", "fecha", "conclusion", "antecedentes_solicitados", "version", "created_at"]

    def validate(self, attrs):
        organization = self.context["organizacion"]
        references = [attrs.get(field) for field in ("evidencia", "observacion", "calculo", "indicador", "problematica", "intervencion", "expediente") if attrs.get(field)]
        if len(references) != 1:
            raise serializers.ValidationError("La revision debe referenciar exactamente un objeto.")
        item = references[0]
        owner_id = getattr(item, "organizacion_id", None) or item.problematica.organizacion_id
        if owner_id != organization.id:
            raise serializers.ValidationError("El objeto revisado pertenece a otra organizacion.")
        return attrs


class ExpedienteSerializer(serializers.ModelSerializer):
    problematica_titulo = serializers.CharField(source="problematica.titulo", read_only=True)
    ultima_revision = serializers.SerializerMethodField()
    informe_vigente = serializers.SerializerMethodField()
    def get_ultima_revision(self, obj):
        row = obj.revisiones_profesionales.order_by("-created_at").first()
        return {"id": row.id, "estado": row.estado, "fecha": row.fecha, "profesional": row.profesional_nombre} if row else None
    def get_informe_vigente(self, obj):
        row = obj.informes.exclude(estado="obsoleto").order_by("-version").first()
        return {"id": row.id, "version": row.version, "estado": row.estado, "checksum": row.checksum_sha256} if row else None
    class Meta:
        model = ExpedienteAmbiental
        fields = ["id", "problematica", "problematica_titulo", "version", "estado", "responsable", "referencias", "resumen_ejecutivo", "cerrado_por", "cerrado_at", "reabierto_por", "reabierto_at", "motivo_reapertura", "ultima_revision", "informe_vigente", "created_at"]
        read_only_fields = [field for field in fields if field not in {"problematica"}]


class SnapshotInformeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SnapshotInformeAmbiental
        fields = ["id", "contenido", "referencias", "created_at"]


class InformeSerializer(serializers.ModelSerializer):
    snapshot = SnapshotInformeSerializer(read_only=True)
    archivo_url = serializers.SerializerMethodField()
    def get_archivo_url(self, obj): return obj.archivo.url if obj.archivo else None
    class Meta:
        model = InformeAmbiental
        fields = ["id", "tipo", "actividad", "problematica", "intervencion", "expediente", "version", "estado", "generado_por", "fecha", "checksum_sha256", "archivo_url", "metadata", "validado_por", "validado_at", "snapshot", "created_at"]


class EventoAuditoriaSerializer(serializers.ModelSerializer):
    actor_nombre = serializers.CharField(source="actor.username", read_only=True)
    class Meta:
        model = EventoAuditoriaAmbiental
        fields = ["id", "tipo", "actor", "actor_nombre", "entidad", "referencia", "resumen", "metadata_auditable", "timestamp"]
