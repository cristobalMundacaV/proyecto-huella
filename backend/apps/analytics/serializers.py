from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    ConfiguracionConstructora,
    Constructora,
    EtapaObra,
    EvidenciaObra,
    FactorEmision,
    MaterialConstruccion,
    Obra,
    RegistroEmision,
    TransporteObra,
    UsuarioConstructora,
)


class ConstructoraSerializer(serializers.ModelSerializer):
    etapas_count = serializers.IntegerField(source="etapas.count", read_only=True)
    obras_count = serializers.IntegerField(source="obras.count", read_only=True)
    registros_count = serializers.IntegerField(source="registros_emision.count", read_only=True)
    evidencias_count = serializers.IntegerField(source="evidencias.count", read_only=True)

    class Meta:
        model = Constructora
        fields = [
            "id",
            "constructora_id",
            "nombre",
            "rut",
            "region",
            "comuna",
            "direccion",
            "rubro",
            "preset",
            "activa",
            "email",
            "telefono",
            "contacto",
            "observaciones",
            "etapas_count",
            "obras_count",
            "registros_count",
            "evidencias_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "etapas_count",
            "obras_count",
            "registros_count",
            "evidencias_count",
            "created_at",
            "updated_at",
        ]


class UsuarioConstructoraSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    nombre = serializers.SerializerMethodField()
    constructora_id = serializers.CharField(source="constructora.constructora_id", read_only=True)
    constructora_nombre = serializers.CharField(source="constructora.nombre", read_only=True)

    class Meta:
        model = UsuarioConstructora
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "nombre",
            "email",
            "constructora_id",
            "constructora_nombre",
            "rol",
            "cargo",
            "activo",
            "created_at",
            "updated_at",
        ]

    def get_nombre(self, usuario_constructora):
        full_name = usuario_constructora.user.get_full_name().strip()
        return full_name or usuario_constructora.user.username


class UsuarioConstructoraCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    rol = serializers.ChoiceField(choices=UsuarioConstructora.Rol.choices, default=UsuarioConstructora.Rol.ANALISTA)
    cargo = serializers.CharField(max_length=120, required=False, allow_blank=True)
    activo = serializers.BooleanField(default=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este nombre.")
        return value

    def create(self, validated_data):
        constructora = self.context["constructora"]
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        return UsuarioConstructora.objects.create(
            user=user,
            constructora=constructora,
            rol=validated_data.get("rol", UsuarioConstructora.Rol.ANALISTA),
            cargo=validated_data.get("cargo", ""),
            activo=validated_data.get("activo", True),
        )


class ConfiguracionConstructoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionConstructora
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class EtapaObraSerializer(serializers.ModelSerializer):
    constructora_id = serializers.CharField(source="constructora.constructora_id", read_only=True)
    constructora_nombre = serializers.CharField(source="constructora.nombre", read_only=True)
    registros_count = serializers.IntegerField(source="registros_emision.count", read_only=True)

    class Meta:
        model = EtapaObra
        fields = [
            "id",
            "etapa_id",
            "constructora",
            "constructora_id",
            "constructora_nombre",
            "nombre",
            "tipo",
            "region",
            "comuna",
            "direccion",
            "descripcion",
            "estado",
            "activa",
            "registros_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "constructora_id", "constructora_nombre", "registros_count", "created_at", "updated_at"]


class ObraSerializer(serializers.ModelSerializer):
    constructora_id = serializers.CharField(source="constructora.constructora_id", read_only=True)
    constructora_nombre = serializers.CharField(source="constructora.nombre", read_only=True)
    etapa_principal_nombre = serializers.CharField(source="etapa_principal.nombre", read_only=True)
    emisiones_kg_co2e = serializers.DecimalField(max_digits=18, decimal_places=3, read_only=True)
    registros_count = serializers.IntegerField(source="registros_emision.count", read_only=True)
    evidencias_count = serializers.IntegerField(source="evidencias.count", read_only=True)

    class Meta:
        model = Obra
        fields = [
            "id",
            "codigo_obra",
            "constructora",
            "constructora_id",
            "constructora_nombre",
            "etapa_principal",
            "etapa_principal_nombre",
            "nombre",
            "tipo_proyecto",
            "fecha_inicio",
            "fecha_termino_estimada",
            "superficie_m2",
            "ubicacion",
            "region",
            "comuna",
            "mandante",
            "estado",
            "descripcion",
            "emisiones_kg_co2e",
            "registros_count",
            "evidencias_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "constructora_id",
            "constructora_nombre",
            "etapa_principal_nombre",
            "emisiones_kg_co2e",
            "registros_count",
            "evidencias_count",
            "created_at",
            "updated_at",
        ]


class FactorEmisionSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = FactorEmision
        fields = [
            "id",
            "actividad",
            "actividad_key",
            "categoria",
            "unidad",
            "factor_emision",
            "fuente",
            "anio",
            "alcance",
            "descripcion",
            "label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "actividad_key", "label", "created_at", "updated_at"]

    def get_label(self, factor):
        return f"{factor.actividad} | {factor.categoria} | {factor.unidad}"


class MaterialConstruccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialConstruccion
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class RegistroEmisionSerializer(serializers.ModelSerializer):
    factor_emision_id = serializers.PrimaryKeyRelatedField(queryset=FactorEmision.objects.all(), required=False, write_only=True)
    constructora_id = serializers.CharField(source="constructora.constructora_id", read_only=True)
    constructora_nombre = serializers.CharField(source="constructora.nombre", read_only=True)
    obra_codigo = serializers.CharField(source="obra.codigo_obra", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    etapa_nombre = serializers.CharField(source="etapa.nombre", read_only=True)
    evidencia_asociada = serializers.SerializerMethodField()

    class Meta:
        model = RegistroEmision
        fields = [
            "id",
            "constructora",
            "constructora_id",
            "constructora_nombre",
            "obra",
            "obra_codigo",
            "obra_nombre",
            "etapa",
            "etapa_nombre",
            "categoria",
            "fuente_emision",
            "actividad_key",
            "factor_emision_id",
            "cantidad",
            "unidad",
            "factor_emision",
            "emisiones_kg_co2e",
            "fecha",
            "proveedor",
            "origen_transporte",
            "destino_transporte",
            "distancia_km",
            "ruta_geometry",
            "metadata",
            "observaciones",
            "evidencia_asociada",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "constructora_id",
            "constructora_nombre",
            "obra_codigo",
            "obra_nombre",
            "etapa_nombre",
            "actividad_key",
            "emisiones_kg_co2e",
            "evidencia_asociada",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        factor = attrs.pop("factor_emision_id", None)
        if factor:
            attrs["fuente_emision"] = factor.actividad
            attrs["actividad_key"] = factor.actividad_key
            attrs["categoria"] = factor.categoria
            attrs["unidad"] = factor.unidad
            attrs["factor_emision"] = factor.factor_emision
        return attrs

    def get_evidencia_asociada(self, registro):
        evidencia = registro.evidencias.order_by("-created_at").first()
        if not evidencia:
            return None
        return {
            "id": evidencia.id,
            "nombre": evidencia.nombre,
            "tipo_evidencia": evidencia.tipo_evidencia,
            "estado_documental": evidencia.estado_documental,
        }


class EvidenciaObraSerializer(serializers.ModelSerializer):
    archivo_url = serializers.SerializerMethodField()
    constructora_id = serializers.CharField(source="constructora.constructora_id", read_only=True)
    constructora_nombre = serializers.CharField(source="constructora.nombre", read_only=True)
    obra_codigo = serializers.CharField(source="obra.codigo_obra", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    etapa_nombre = serializers.CharField(source="etapa.nombre", read_only=True)
    registro_fuente = serializers.CharField(source="registro_emision.fuente_emision", read_only=True)

    class Meta:
        model = EvidenciaObra
        fields = [
            "id",
            "constructora",
            "constructora_id",
            "constructora_nombre",
            "obra",
            "obra_codigo",
            "obra_nombre",
            "etapa",
            "etapa_nombre",
            "registro_emision",
            "registro_fuente",
            "tipo_evidencia",
            "estado_documental",
            "fecha_documento",
            "archivo",
            "archivo_url",
            "nombre",
            "observaciones",
            "texto_extraido",
            "metadata_extraccion",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "constructora_id",
            "constructora_nombre",
            "obra_codigo",
            "obra_nombre",
            "etapa_nombre",
            "registro_fuente",
            "archivo_url",
            "texto_extraido",
            "metadata_extraccion",
            "created_at",
            "updated_at",
        ]

    def get_archivo_url(self, evidencia):
        if not evidencia.archivo:
            return ""
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(evidencia.archivo.url)
        return evidencia.archivo.url


class TransporteObraSerializer(serializers.ModelSerializer):
    obra_codigo = serializers.CharField(source="obra.codigo_obra", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    etapa_nombre = serializers.CharField(source="etapa.nombre", read_only=True)

    class Meta:
        model = TransporteObra
        fields = [
            "id",
            "obra",
            "obra_codigo",
            "obra_nombre",
            "etapa",
            "etapa_nombre",
            "vehiculo",
            "patente",
            "origen",
            "destino",
            "origen_coords",
            "destino_coords",
            "distancia_km",
            "consumo_estimado_litro_km",
            "litros_combustible",
            "emisiones_kg_co2e",
            "fecha_hora",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "obra_codigo",
            "obra_nombre",
            "etapa_nombre",
            "emisiones_kg_co2e",
            "created_at",
            "updated_at",
        ]
