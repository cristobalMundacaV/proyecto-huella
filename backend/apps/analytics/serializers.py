from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    AlertaCumplimientoAmbiental,
    ConfiguracionOrganizacion,
    Organizacion,
    DocumentoAmbiental,
    EspecieMadera,
    EtapaObra,
    EvidenciaObra,
    FactorEmision,
    LimiteNormativoAmbiental,
    LoteForestal,
    MaterialConstruccion,
    Obra,
    RegistroEmision,
    TransporteLoteForestal,
    TransporteObra,
    UsuarioOrganizacion,
    VariableAmbientalExtraida,
)
from .services.forestal_carbono import calcular_balance_neto_lote


def normalize_carbon_percentage(value):
    if value is not None and value > 1:
        return value / 100
    return value


class OrganizacionSerializer(serializers.ModelSerializer):
    etapas_count = serializers.IntegerField(source="etapas.count", read_only=True)
    obras_count = serializers.IntegerField(source="obras.count", read_only=True)
    registros_count = serializers.IntegerField(source="registros_emision.count", read_only=True)
    evidencias_count = serializers.IntegerField(source="evidencias.count", read_only=True)

    class Meta:
        model = Organizacion
        fields = [
            "id",
            "organizacion_id",
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


class UsuarioOrganizacionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    nombre = serializers.SerializerMethodField()
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)
    organizacion_nombre = serializers.CharField(source="organizacion.nombre", read_only=True)

    class Meta:
        model = UsuarioOrganizacion
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "nombre",
            "email",
            "organizacion_id",
            "organizacion_nombre",
            "rol",
            "cargo",
            "activo",
            "created_at",
            "updated_at",
        ]

    def get_nombre(self, usuario_organizacion):
        full_name = usuario_organizacion.user.get_full_name().strip()
        return full_name or usuario_organizacion.user.username


class UsuarioOrganizacionCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    rol = serializers.ChoiceField(choices=UsuarioOrganizacion.Rol.choices, default=UsuarioOrganizacion.Rol.ANALISTA)
    cargo = serializers.CharField(max_length=120, required=False, allow_blank=True)
    activo = serializers.BooleanField(default=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este nombre.")
        return value

    def create(self, validated_data):
        organizacion = self.context["organizacion"]
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        return UsuarioOrganizacion.objects.create(
            user=user,
            organizacion=organizacion,
            rol=validated_data.get("rol", UsuarioOrganizacion.Rol.ANALISTA),
            cargo=validated_data.get("cargo", ""),
            activo=validated_data.get("activo", True),
        )


class ConfiguracionOrganizacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionOrganizacion
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class EtapaObraSerializer(serializers.ModelSerializer):
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)
    organizacion_nombre = serializers.CharField(source="organizacion.nombre", read_only=True)
    registros_count = serializers.IntegerField(source="registros_emision.count", read_only=True)

    class Meta:
        model = EtapaObra
        fields = [
            "id",
            "etapa_id",
            "organizacion",
            "organizacion_id",
            "organizacion_nombre",
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
        read_only_fields = ["id", "organizacion_id", "organizacion_nombre", "registros_count", "created_at", "updated_at"]


class ObraSerializer(serializers.ModelSerializer):
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)
    organizacion_nombre = serializers.CharField(source="organizacion.nombre", read_only=True)
    etapa_principal_nombre = serializers.CharField(source="etapa_principal.nombre", read_only=True)
    emisiones_kg_co2e = serializers.DecimalField(max_digits=18, decimal_places=3, read_only=True)
    registros_count = serializers.IntegerField(source="registros_emision.count", read_only=True)
    evidencias_count = serializers.IntegerField(source="evidencias.count", read_only=True)

    class Meta:
        model = Obra
        fields = [
            "id",
            "codigo_obra",
            "organizacion",
            "organizacion_id",
            "organizacion_nombre",
            "etapa_principal",
            "etapa_principal_nombre",
            "nombre",
            "tipo_proyecto",
            "perfil_ambiental",
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
            "organizacion_id",
            "organizacion_nombre",
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
            "preset",
            "module",
            "actividad",
            "actividad_key",
            "categoria",
            "unidad",
            "factor_emision",
            "fuente",
            "anio",
            "alcance",
            "descripcion",
            "metadata",
            "activo",
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
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)
    organizacion_nombre = serializers.CharField(source="organizacion.nombre", read_only=True)
    obra_codigo = serializers.CharField(source="obra.codigo_obra", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    etapa_nombre = serializers.CharField(source="etapa.nombre", read_only=True)
    evidencia_asociada = serializers.SerializerMethodField()
    lote_forestal_id = serializers.CharField(source="lote_forestal.lote_id", read_only=True)
    actividad = serializers.CharField(source="fuente_emision", required=False)

    class Meta:
        model = RegistroEmision
        extra_kwargs = {"fuente_emision": {"required": False}}
        fields = [
            "id",
            "organizacion",
            "organizacion_id",
            "organizacion_nombre",
            "obra",
            "obra_codigo",
            "obra_nombre",
            "etapa",
            "etapa_nombre",
            "lote_forestal",
            "lote_forestal_id",
            "categoria",
            "actividad",
            "fuente_emision",
            "actividad_key",
            "factor_emision_id",
            "cantidad",
            "unidad",
            "factor_emision",
            "emisiones_kg_co2e",
            "fecha",
            "proveedor",
            "numero_documento",
            "area_operacional",
            "unidad_operacional",
            "identificador_externo",
            "tipo_ingreso",
            "fuente_ingreso",
            "estado_validacion",
            "fingerprint",
            "fingerprint_nucleo",
            "estado_gobernanza",
            "registro_canonico",
            "contabilizable",
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
            "organizacion_id",
            "organizacion_nombre",
            "obra_codigo",
            "obra_nombre",
            "etapa_nombre",
            "lote_forestal_id",
            "actividad_key",
            "fingerprint",
            "fingerprint_nucleo",
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
        if self.instance is None:
            for field in ("fecha", "cantidad", "unidad", "fuente_emision", "categoria"):
                if attrs.get(field) in (None, ""):
                    raise serializers.ValidationError({field: "Este campo es requerido."})
            if attrs["cantidad"] <= 0:
                raise serializers.ValidationError({"cantidad": "Debe ser mayor que cero."})
            attrs["unidad"] = attrs["unidad"].strip()
            if not attrs["unidad"]:
                raise serializers.ValidationError({"unidad": "Este campo es requerido."})
        return attrs

    def create(self, validated_data):
        from .services.environmental_records import create_environmental_record

        organizacion = validated_data.pop("organizacion", None)
        tipo_ingreso = validated_data.pop("tipo_ingreso", RegistroEmision.TipoIngreso.MANUAL)
        fuente_ingreso = validated_data.pop("fuente_ingreso", "") or tipo_ingreso
        try:
            return create_environmental_record(
                validated_data,
                organizacion=organizacion,
                tipo_ingreso=tipo_ingreso,
                fuente_ingreso=fuente_ingreso,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(getattr(exc, "message_dict", {"detail": exc.messages}))

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
    lote_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)
    organizacion_nombre = serializers.CharField(source="organizacion.nombre", read_only=True)
    obra_codigo = serializers.CharField(source="obra.codigo_obra", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    etapa_nombre = serializers.CharField(source="etapa.nombre", read_only=True)
    registros_fuente = serializers.SerializerMethodField()
    lote_forestal_id = serializers.CharField(source="lote_forestal.lote_id", read_only=True)

    class Meta:
        model = EvidenciaObra
        fields = [
            "id",
            "organizacion",
            "organizacion_id",
            "organizacion_nombre",
            "obra",
            "obra_codigo",
            "obra_nombre",
            "etapa",
            "etapa_nombre",
            "registros_emision",
            "registros_fuente",
            "lote_forestal",
            "lote_forestal_id",
            "lote_id",
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
            "organizacion_id",
            "organizacion_nombre",
            "obra_codigo",
            "obra_nombre",
            "etapa_nombre",
            "registros_fuente",
            "lote_forestal_id",
            "archivo_url",
            "texto_extraido",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        lote_id = attrs.pop("lote_id", "")
        metadata = attrs.get("metadata_extraccion")
        if isinstance(metadata, str):
            import json

            try:
                metadata = json.loads(metadata)
                attrs["metadata_extraccion"] = metadata
            except json.JSONDecodeError:
                metadata = {}
        organizacion = attrs.get("organizacion") or getattr(self.instance, "organizacion", None)
        if lote_id and organizacion and not attrs.get("lote_forestal"):
            lote = LoteForestal.objects.filter(organizacion=organizacion, lote_id=lote_id.strip()).first()
            if lote:
                attrs["lote_forestal"] = lote
        return attrs

    def get_registros_fuente(self, evidencia):
        return list(evidencia.registros_emision.values_list("fuente_emision", flat=True))

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


class EspecieMaderaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EspecieMadera
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_porcentaje_carbono(self, value):
        value = normalize_carbon_percentage(value)
        if value <= 0:
            raise serializers.ValidationError("El porcentaje de carbono debe ser mayor a 0.")
        return value

    def validate_densidad_kg_m3(self, value):
        if value <= 0:
            raise serializers.ValidationError("La densidad debe ser mayor a 0.")
        return value


class TransporteLoteForestalSerializer(serializers.ModelSerializer):
    lote_id = serializers.CharField(source="lote_forestal.lote_id", read_only=True)
    registro_emision_id = serializers.IntegerField(source="registro_emision.id", read_only=True)

    class Meta:
        model = TransporteLoteForestal
        fields = [
            "id",
            "lote_forestal",
            "lote_id",
            "fecha",
            "vehiculo",
            "patente",
            "conductor",
            "origen",
            "destino",
            "distancia_km",
            "litros_diesel",
            "consumo_estimado_litro_km",
            "factor_diesel",
            "emisiones_transporte_kg_co2e",
            "registro_emision",
            "registro_emision_id",
            "observaciones",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "lote_id",
            "emisiones_transporte_kg_co2e",
            "registro_emision",
            "registro_emision_id",
            "created_at",
            "updated_at",
        ]

    def validate_distancia_km(self, value):
        if value <= 0:
            raise serializers.ValidationError("La distancia debe ser mayor a 0.")
        return value

    def validate_litros_diesel(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Los litros diesel deben ser mayores a 0.")
        return value


class LoteForestalSerializer(serializers.ModelSerializer):
    cantidad_registros_emision = serializers.IntegerField(source="registros_emision.count", read_only=True)
    cantidad_transportes = serializers.IntegerField(source="transportes.count", read_only=True)
    cantidad_evidencias = serializers.IntegerField(source="evidencias.count", read_only=True)

    class Meta:
        model = LoteForestal
        fields = [
            "id",
            "lote_id",
            "organizacion",
            "fecha",
            "especie",
            "volumen_m3",
            "origen",
            "destino",
            "tipo_producto",
            "densidad_kg_m3",
            "porcentaje_carbono",
            "estado",
            "observaciones",
            "metadata",
            "cantidad_registros_emision",
            "cantidad_transportes",
            "cantidad_evidencias",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "cantidad_registros_emision",
            "cantidad_transportes",
            "cantidad_evidencias",
            "created_at",
            "updated_at",
        ]

    def validate_volumen_m3(self, value):
        if value <= 0:
            raise serializers.ValidationError("El volumen debe ser mayor a 0.")
        return value

    def validate_densidad_kg_m3(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("La densidad debe ser mayor a 0.")
        return value

    def validate_porcentaje_carbono(self, value):
        value = normalize_carbon_percentage(value)
        if value is not None and value <= 0:
            raise serializers.ValidationError("El porcentaje de carbono debe ser mayor a 0.")
        return value


class LoteForestalDetailSerializer(LoteForestalSerializer):
    emisiones_generadas_kg_co2e = serializers.SerializerMethodField()
    co2_almacenado_kg = serializers.SerializerMethodField()
    balance_neto_kg_co2e = serializers.SerializerMethodField()
    estado_balance = serializers.SerializerMethodField()
    descripcion_balance = serializers.SerializerMethodField()
    calculo_completo = serializers.SerializerMethodField()
    campos_faltantes = serializers.SerializerMethodField()
    registros_emision = serializers.SerializerMethodField()
    transportes = TransporteLoteForestalSerializer(many=True, read_only=True)
    evidencias = serializers.SerializerMethodField()

    class Meta(LoteForestalSerializer.Meta):
        fields = LoteForestalSerializer.Meta.fields + [
            "emisiones_generadas_kg_co2e",
            "co2_almacenado_kg",
            "balance_neto_kg_co2e",
            "estado_balance",
            "descripcion_balance",
            "calculo_completo",
            "campos_faltantes",
            "registros_emision",
            "transportes",
            "evidencias",
        ]

    def _balance(self, lote):
        if not hasattr(lote, "_balance_cache"):
            lote._balance_cache = calcular_balance_neto_lote(lote)
        return lote._balance_cache

    def get_emisiones_generadas_kg_co2e(self, lote):
        return self._balance(lote)["emisiones_generadas_kg_co2e"]

    def get_co2_almacenado_kg(self, lote):
        return self._balance(lote)["co2_almacenado_kg"]

    def get_balance_neto_kg_co2e(self, lote):
        return self._balance(lote)["balance_neto_kg_co2e"]

    def get_estado_balance(self, lote):
        return self._balance(lote)["estado_balance"]

    def get_descripcion_balance(self, lote):
        return self._balance(lote)["descripcion_balance"]

    def get_calculo_completo(self, lote):
        return self._balance(lote)["calculo_completo"]

    def get_campos_faltantes(self, lote):
        return self._balance(lote)["campos_faltantes"]

    def get_registros_emision(self, lote):
        registros = lote.registros_emision.order_by("-fecha", "-created_at")
        return RegistroEmisionSerializer(registros, many=True).data

    def get_evidencias(self, lote):
        return EvidenciaObraSerializer(lote.evidencias.order_by("-created_at"), many=True, context=self.context).data


class DocumentoAmbientalSerializer(serializers.ModelSerializer):
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)
    organizacion_nombre = serializers.CharField(source="organizacion.nombre", read_only=True)
    obra_nombre = serializers.CharField(source="obra.nombre", read_only=True)
    etapa_nombre = serializers.CharField(source="etapa.nombre", read_only=True)
    archivo_url = serializers.SerializerMethodField()
    variables_count = serializers.IntegerField(source="variables_extraidas.count", read_only=True)
    registros_ids = serializers.SerializerMethodField()

    class Meta:
        model = DocumentoAmbiental
        fields = [
            "id",
            "organizacion",
            "organizacion_id",
            "organizacion_nombre",
            "obra",
            "obra_nombre",
            "etapa",
            "etapa_nombre",
            "registros_emision",
            "registros_ids",
            "tipo_documento",
            "industria",
            "nombre",
            "fecha_documento",
            "periodo_inicio",
            "periodo_fin",
            "fuente_origen",
            "archivo",
            "archivo_url",
            "estado_procesamiento",
            "estado_validacion",
            "resumen",
            "metadata",
            "variables_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organizacion_id",
            "organizacion_nombre",
            "obra_nombre",
            "etapa_nombre",
            "archivo_url",
            "variables_count",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        organizacion = attrs.get("organizacion") or getattr(self.instance, "organizacion", None) or self.context.get("organizacion")
        if organizacion:
            for field in ["obra", "etapa"]:
                value = attrs.get(field)
                if value and value.organizacion_id != organizacion.id:
                    raise serializers.ValidationError({field: "Debe pertenecer a la empresa activa."})
            for registro in attrs.get("registros_emision", []):
                if registro.organizacion_id != organizacion.id:
                    raise serializers.ValidationError({"registros_emision": "Deben pertenecer a la empresa activa."})
        return attrs

    def get_archivo_url(self, documento):
        if not documento.archivo:
            return ""
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(documento.archivo.url)
        return documento.archivo.url

    def get_registros_ids(self, documento):
        return list(documento.registros_emision.values_list("id", flat=True))


class LimiteNormativoAmbientalSerializer(serializers.ModelSerializer):
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)

    class Meta:
        model = LimiteNormativoAmbiental
        fields = [
            "id",
            "organizacion",
            "organizacion_id",
            "industria",
            "variable_id",
            "nombre",
            "normativa",
            "limite",
            "unidad",
            "comparador",
            "region",
            "tipo_instalacion",
            "vigencia_desde",
            "vigencia_hasta",
            "fuente_normativa",
            "validado",
            "activo",
            "descripcion",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organizacion_id", "created_at", "updated_at"]


class VariableAmbientalExtraidaSerializer(serializers.ModelSerializer):
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)
    documento_nombre = serializers.CharField(source="documento.nombre", read_only=True)
    documento_tipo = serializers.CharField(source="documento.tipo_documento", read_only=True)

    class Meta:
        model = VariableAmbientalExtraida
        fields = [
            "id",
            "documento",
            "documento_nombre",
            "documento_tipo",
            "organizacion",
            "organizacion_id",
            "variable_id",
            "nombre",
            "categoria",
            "valor",
            "unidad",
            "fecha_medicion",
            "punto_medicion",
            "limite_aplicable",
            "unidad_limite",
            "estado_cumplimiento",
            "porcentaje_sobre_limite",
            "confianza_extraccion",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "documento_nombre",
            "documento_tipo",
            "organizacion_id",
            "estado_cumplimiento",
            "porcentaje_sobre_limite",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        organizacion = attrs.get("organizacion") or getattr(self.instance, "organizacion", None) or self.context.get("organizacion")
        documento = attrs.get("documento") or getattr(self.instance, "documento", None)
        if organizacion and documento and documento.organizacion_id != organizacion.id:
            raise serializers.ValidationError({"documento": "Debe pertenecer a la empresa activa."})
        return attrs


class AlertaCumplimientoAmbientalSerializer(serializers.ModelSerializer):
    organizacion_id = serializers.CharField(source="organizacion.organizacion_id", read_only=True)
    documento_nombre = serializers.CharField(source="documento.nombre", read_only=True)
    variable_nombre = serializers.CharField(source="variable.nombre", read_only=True)
    variable_id_codigo = serializers.CharField(source="variable.variable_id", read_only=True)

    class Meta:
        model = AlertaCumplimientoAmbiental
        fields = [
            "id",
            "organizacion",
            "organizacion_id",
            "documento",
            "documento_nombre",
            "variable",
            "variable_nombre",
            "variable_id_codigo",
            "severidad",
            "tipo_alerta",
            "titulo",
            "descripcion",
            "estado",
            "accion_sugerida",
            "normativa",
            "fecha_evento",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organizacion",
            "organizacion_id",
            "documento",
            "documento_nombre",
            "variable",
            "variable_nombre",
            "variable_id_codigo",
            "severidad",
            "tipo_alerta",
            "titulo",
            "descripcion",
            "accion_sugerida",
            "normativa",
            "fecha_evento",
            "metadata",
            "created_at",
            "updated_at",
        ]
