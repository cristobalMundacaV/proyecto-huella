from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from apps.iot.models import LecturaSensor

from .models import (
    DocumentoLote,
    Evidencia,
    EmisionLote,
    Empresa,
    EmpresaConfiguracion,
    EspecieMadera,
    ExtraccionDocumento,
    FactorEmision,
    Lote,
    TransporteLote,
    UnidadOperativa,
    UsuarioEmpresa,
    normalize_identifier,
)
from .services.carbono import calcular_balance_lote, calcular_carbono_almacenado
from .services.confianza import calcular_confianza_lote
from .services.pasaporte import calcular_pasaporte_lote


class EspecieMaderaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EspecieMadera
        fields = [
            "id",
            "nombre",
            "densidad_kg_m3",
            "porcentaje_carbono",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmpresaSerializer(serializers.ModelSerializer):
    unidades_count = serializers.SerializerMethodField()
    lotes_count = serializers.SerializerMethodField()
    actividades_count = serializers.SerializerMethodField()
    emisiones_totales_kg_co2e = serializers.SerializerMethodField()
    co2_almacenado_kg = serializers.SerializerMethodField()
    balance_neto_kg_co2e = serializers.SerializerMethodField()
    pasaportes_emitidos = serializers.SerializerMethodField()
    evidencias_count = serializers.SerializerMethodField()
    unidades_resumen = serializers.SerializerMethodField()
    lotes_resumen = serializers.SerializerMethodField()
    actividades_resumen = serializers.SerializerMethodField()
    evidencias_resumen = serializers.SerializerMethodField()
    unidad_inicial = serializers.SerializerMethodField()

    class Meta:
        model = Empresa
        fields = [
            "id",
            "empresa_id",
            "nombre",
            "rut",
            "region",
            "comuna",
            "direccion",
            "rubro",
            "activa",
            "email",
            "telefono",
            "contacto",
            "observaciones",
            "unidades_count",
            "lotes_count",
            "actividades_count",
            "emisiones_totales_kg_co2e",
            "co2_almacenado_kg",
            "balance_neto_kg_co2e",
            "pasaportes_emitidos",
            "evidencias_count",
            "unidades_resumen",
            "lotes_resumen",
            "actividades_resumen",
            "evidencias_resumen",
            "unidad_inicial",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "unidades_count",
            "lotes_count",
            "actividades_count",
            "emisiones_totales_kg_co2e",
            "co2_almacenado_kg",
            "balance_neto_kg_co2e",
            "pasaportes_emitidos",
            "evidencias_count",
            "unidades_resumen",
            "lotes_resumen",
            "actividades_resumen",
            "evidencias_resumen",
            "unidad_inicial",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        if not validated_data.get("empresa_id"):
            base_id = normalize_identifier(validated_data.get("nombre")) or "EMPRESA_GENERAL"
            empresa_id = base_id
            suffix = 2

            while Empresa.objects.filter(empresa_id=empresa_id).exists():
                empresa_id = f"{base_id}_{suffix}"
                suffix += 1

            validated_data["empresa_id"] = empresa_id

        empresa = super().create(validated_data)
        UnidadOperativa.objects.get_or_create(
            unidad_id=f"{empresa.empresa_id}_GENERAL",
            defaults={
                "empresa": empresa,
                "nombre": "Unidad General",
                "tipo": UnidadOperativa.Tipo.ADMINISTRACION,
            },
        )
        return empresa

    def _lotes(self, empresa):
        return list(empresa.lotes.all())

    def _actividades(self, empresa):
        return list(empresa.actividades_emision.all())

    def _iot_emisiones(self, empresa):
        desde = timezone.now() - timedelta(hours=24)
        agregados = LecturaSensor.objects.filter(
            empresa__iexact=empresa.nombre,
            fecha_registro__gte=desde,
        ).aggregate(total=Sum("co2e_estimado"))
        return float(agregados.get("total") or 0)

    def get_unidades_count(self, empresa):
        if self.context.get("is_list_view") and hasattr(empresa, "unidades_count_val"):
            return empresa.unidades_count_val
        return empresa.unidades_operativas.count()

    def get_lotes_count(self, empresa):
        if self.context.get("is_list_view") and hasattr(empresa, "lotes_count_val"):
            return empresa.lotes_count_val
        return empresa.lotes.count()

    def get_actividades_count(self, empresa):
        if self.context.get("is_list_view") and hasattr(empresa, "actividades_count_val"):
            return empresa.actividades_count_val
        return empresa.actividades_emision.count()

    def get_emisiones_totales_kg_co2e(self, empresa):
        # For list views we prefer using the annotated DB value when available
        # to avoid iterating related objects in Python (heavy). The view
        # annotates `emisiones_totales_val` when possible.
        if self.context.get("is_list_view"):
            annotated = getattr(empresa, "emisiones_totales_val", None)
            if annotated is not None:
                return float(annotated)
            return 0
        return sum((actividad.emisiones_kg_co2e for actividad in self._actividades(empresa)), 0) + self._iot_emisiones(empresa)

    def get_co2_almacenado_kg(self, empresa):
        if self.context.get("is_list_view"):
            annotated = getattr(empresa, "co2_almacenado_val", None)
            if annotated is not None:
                return float(annotated)
            return 0
        return sum(
            (calcular_carbono_almacenado(lote)["co2_almacenado_kg"] for lote in self._lotes(empresa)),
            0,
        )

    def get_balance_neto_kg_co2e(self, empresa):
        if self.context.get("is_list_view"):
            return self.get_emisiones_totales_kg_co2e(empresa) - self.get_co2_almacenado_kg(empresa)
        return self.get_emisiones_totales_kg_co2e(empresa) - self.get_co2_almacenado_kg(empresa)

    def get_pasaportes_emitidos(self, empresa):
        if self.context.get("is_list_view"):
            return 0
        return sum(
            1
            for lote in self._lotes(empresa)
            if calcular_pasaporte_lote(lote)["estado_pasaporte"] != "Sin pasaporte"
        )

    def get_evidencias_count(self, empresa):
        if self.context.get("is_list_view"):
            return 0
        return sum(lote.documentos.count() for lote in self._lotes(empresa))

    def get_unidades_resumen(self, empresa):
        if self.context.get("is_list_view"):
            return []
        return [
            {
                "id": unidad.id,
                "unidad_id": unidad.unidad_id,
                "nombre": unidad.nombre,
                "tipo": unidad.tipo,
                "region": unidad.region,
                "comuna": unidad.comuna,
                "activa": unidad.activa,
                "lotes_count": unidad.lotes.count(),
                "actividades_count": unidad.actividades_emision.count(),
                "emisiones_totales_kg_co2e": sum(
                    (actividad.emisiones_kg_co2e for actividad in unidad.actividades_emision.all()),
                    0,
                ),
            }
            for unidad in empresa.unidades_operativas.all()
        ]

    def get_lotes_resumen(self, empresa):
        if self.context.get("is_list_view"):
            return []
        lotes = []
        for lote in self._lotes(empresa):
            balance = calcular_balance_lote(lote)
            pasaporte = calcular_pasaporte_lote(lote)
            lotes.append(
                {
                    "id_lote": lote.id_lote,
                    "fecha": lote.fecha,
                    "unidad": lote.unidad_operativa.nombre if lote.unidad_operativa_id else "",
                    "especie": lote.especie,
                    "volumen_m3": lote.volumen_m3,
                    "emisiones_kg_co2e": balance["emisiones_generadas_kg_co2e"],
                    "co2_almacenado_kg": balance["co2_almacenado_kg"],
                    "balance_neto_kg_co2e": balance["balance_neto_kg_co2e"],
                    "estado_balance": balance["estado_balance"],
                    "estado_pasaporte": pasaporte["estado_pasaporte"],
                    "evidencias_count": lote.documentos.count(),
                }
            )
        return lotes

    def get_actividades_resumen(self, empresa):
        if self.context.get("is_list_view"):
            return []
        return [
            {
                "id": actividad.id,
                "actividad": actividad.actividad,
                "categoria": actividad.categoria,
                "cantidad": actividad.cantidad,
                "unidad": actividad.unidad,
                "fecha": actividad.fecha,
                "tipo_asignacion": actividad.tipo_asignacion,
                "lote": actividad.lote.id_lote if actividad.lote_id else "",
                "unidad_operativa": (
                    actividad.unidad_operativa.nombre
                    if actividad.unidad_operativa_id
                    else ""
                ),
                "emisiones_kg_co2e": actividad.emisiones_kg_co2e,
            }
            for actividad in self._actividades(empresa)
        ]

    def get_evidencias_resumen(self, empresa):
        if self.context.get("is_list_view"):
            return []
        evidencias = []
        for lote in self._lotes(empresa):
            for documento in lote.documentos.all():
                evidencias.append(
                    {
                        "id": documento.id,
                        "lote": lote.id_lote,
                        "tipo_documento": documento.get_tipo_documento_display(),
                        "estado_validacion": documento.get_estado_validacion_display(),
                        "fecha": documento.fecha,
                    }
                )
        return evidencias

    def get_unidad_inicial(self, empresa):
        if self.context.get("is_list_view"):
            return None
        unidad = empresa.unidades_operativas.order_by("created_at").first()
        if not unidad:
            return None

        return {
            "id": unidad.id,
            "unidad_id": unidad.unidad_id,
            "nombre": unidad.nombre,
            "tipo": unidad.tipo,
        }

class UsuarioEmpresaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    nombre = serializers.SerializerMethodField()
    empresa_id = serializers.CharField(source="empresa.empresa_id", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = UsuarioEmpresa
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "nombre",
            "email",
            "empresa_id",
            "empresa_nombre",
            "rol",
            "cargo",
            "activo",
            "created_at",
            "updated_at",
        ]

    def get_nombre(self, usuario_empresa):
        full_name = usuario_empresa.user.get_full_name().strip()
        return full_name or usuario_empresa.user.username


class UsuarioEmpresaCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    rol = serializers.ChoiceField(choices=UsuarioEmpresa.Rol.choices, default=UsuarioEmpresa.Rol.ANALISTA)
    cargo = serializers.CharField(max_length=120, required=False, allow_blank=True)
    activo = serializers.BooleanField(default=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este nombre.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value

    def create(self, validated_data):
        empresa = self.context["empresa"]
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        return UsuarioEmpresa.objects.create(
            user=user,
            empresa=empresa,
            rol=validated_data.get("rol", UsuarioEmpresa.Rol.ANALISTA),
            cargo=validated_data.get("cargo", ""),
            activo=validated_data.get("activo", True),
        )


class UnidadOperativaSerializer(serializers.ModelSerializer):
    empresa_id = serializers.CharField(source="empresa.empresa_id", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    lotes_count = serializers.SerializerMethodField()
    actividades_count = serializers.SerializerMethodField()
    emisiones_totales_kg_co2e = serializers.SerializerMethodField()
    pasaportes_count = serializers.SerializerMethodField()
    evidencias_count = serializers.SerializerMethodField()
    lotes_resumen = serializers.SerializerMethodField()
    actividades_resumen = serializers.SerializerMethodField()

    class Meta:
        model = UnidadOperativa
        fields = [
            "id",
            "unidad_id",
            "empresa",
            "empresa_id",
            "empresa_nombre",
            "nombre",
            "tipo",
            "region",
            "comuna",
            "direccion",
            "descripcion",
            "estado",
            "activa",
            "lotes_count",
            "actividades_count",
            "emisiones_totales_kg_co2e",
            "pasaportes_count",
            "evidencias_count",
            "lotes_resumen",
            "actividades_resumen",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "lotes_count",
            "actividades_count",
            "emisiones_totales_kg_co2e",
            "pasaportes_count",
            "evidencias_count",
            "lotes_resumen",
            "actividades_resumen",
            "created_at",
            "updated_at",
        ]

    def _lotes(self, unidad):
        return list(unidad.lotes.all())

    def _actividades(self, unidad):
        return list(unidad.actividades_emision.all())

    def get_lotes_count(self, unidad):
        return unidad.lotes.count()

    def get_actividades_count(self, unidad):
        return unidad.actividades_emision.count()

    def get_emisiones_totales_kg_co2e(self, unidad):
        return sum((actividad.emisiones_kg_co2e for actividad in self._actividades(unidad)), 0)

    def get_pasaportes_count(self, unidad):
        return sum(
            1
            for lote in self._lotes(unidad)
            if calcular_pasaporte_lote(lote)["estado_pasaporte"] != "Sin pasaporte"
        )

    def get_evidencias_count(self, unidad):
        return sum(lote.documentos.count() for lote in self._lotes(unidad))

    def get_lotes_resumen(self, unidad):
        rows = []
        for lote in self._lotes(unidad):
            balance = calcular_balance_lote(lote)
            rows.append(
                {
                    "id_lote": lote.id_lote,
                    "fecha": lote.fecha,
                    "especie": lote.especie,
                    "estado": lote.estado,
                    "emisiones_kg_co2e": balance["emisiones_generadas_kg_co2e"],
                    "balance_neto_kg_co2e": balance["balance_neto_kg_co2e"],
                    "evidencias_count": lote.documentos.count(),
                    "estado_pasaporte": calcular_pasaporte_lote(lote)["estado_pasaporte"],
                }
            )
        return rows

    def get_actividades_resumen(self, unidad):
        return [
            {
                "id": actividad.id,
                "fecha": actividad.fecha,
                "actividad": actividad.actividad,
                "categoria": actividad.categoria,
                "cantidad": actividad.cantidad,
                "unidad": actividad.unidad,
                "factor_emision": actividad.factor_emision,
                "emisiones_kg_co2e": actividad.emisiones_kg_co2e,
                "lote": actividad.lote.id_lote if actividad.lote_id else "",
            }
            for actividad in self._actividades(unidad)
        ]


class FactorEmisionSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = FactorEmision
        fields = [
            "id",
            "categoria",
            "actividad_key",
            "actividad",
            "unidad",
            "factor_emision",
            "anio",
            "descripcion",
            "metadata_clasificacion",
            "label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_label(self, factor):
        return f"{factor.actividad} | {factor.unidad} | {factor.anio}"


class EmisionLoteSerializer(serializers.ModelSerializer):
    factor_emision_id = serializers.PrimaryKeyRelatedField(
        queryset=FactorEmision.objects.all(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = EmisionLote
        fields = [
            "id",
            "empresa",
            "unidad_operativa",
            "lote",
            "actividad",
            "actividad_key",
            "categoria",
            "tipo_consumo_combustible",
            "factor_emision_id",
            "cantidad",
            "unidad",
            "fecha",
            "factor_emision",
            "origen_transporte",
            "destino_transporte",
            "origen_coords",
            "destino_coords",
            "distancia_km",
            "ruta_geometry",
            "emisiones_kg_co2e",
            "tipo_asignacion",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "categoria",
            "emisiones_kg_co2e",
            "tipo_asignacion",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        factor = attrs.pop("factor_emision_id", None)

        if factor:
            attrs["actividad"] = factor.actividad
            attrs["actividad_key"] = factor.actividad_key
            attrs["unidad"] = factor.unidad
            attrs["factor_emision"] = factor.factor_emision

        return attrs


class DocumentoLoteSerializer(serializers.ModelSerializer):
    archivo_url = serializers.SerializerMethodField()
    tipo_documento_label = serializers.CharField(
        source="get_tipo_documento_display",
        read_only=True,
    )
    estado_validacion_label = serializers.CharField(
        source="get_estado_validacion_display",
        read_only=True,
    )

    class Meta:
        model = DocumentoLote
        fields = [
            "id",
            "tipo_documento",
            "tipo_documento_label",
            "archivo",
            "archivo_url",
            "fecha",
            "estado_validacion",
            "estado_validacion_label",
            "created_at",
            "updated_at",
        ]


class EvidenciaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    empresa_codigo = serializers.CharField(source="empresa.empresa_id", read_only=True)
    unidad_nombre = serializers.CharField(source="unidad_operativa.nombre", read_only=True)
    unidad_codigo = serializers.CharField(source="unidad_operativa.unidad_id", read_only=True)
    lote_codigo = serializers.CharField(source="lote.id_lote", read_only=True)
    archivo_url = serializers.SerializerMethodField()
    alcance = serializers.CharField(read_only=False, required=False)
    estado_sistema = serializers.CharField(read_only=True)
    estado_revision = serializers.CharField(read_only=True)
    alcance_label = serializers.CharField(source="get_alcance_display", read_only=True)
    estado_sistema_label = serializers.CharField(source="get_estado_sistema_display", read_only=True)
    estado_revision_label = serializers.CharField(source="get_estado_revision_display", read_only=True)

    class Meta:
        model = Evidencia
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "empresa_codigo",
            "unidad_operativa",
            "unidad_nombre",
            "unidad_codigo",
            "lote",
            "lote_codigo",
            "emision",
            "tipo_documento",
            "nombre",
            "archivo",
            "archivo_url",
            "fecha_documento",
            "estado",
            "observaciones",
            "alcance",
            "alcance_label",
            "estado_sistema",
            "estado_sistema_label",
            "estado_revision",
            "estado_revision_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "empresa_codigo",
            "unidad_nombre",
            "unidad_codigo",
            "lote_codigo",
            "archivo_url",
            "created_at",
            "updated_at",
        ]

    def get_archivo_url(self, evidencia):
        request = self.context.get("request")
        if not evidencia.archivo:
            return ""
        if request:
            return request.build_absolute_uri(evidencia.archivo.url)
        return evidencia.archivo.url
        read_only_fields = [
            "id",
            "archivo_url",
            "tipo_documento_label",
            "estado_validacion_label",
            "created_at",
            "updated_at",
        ]

    def get_archivo_url(self, documento):
        if not documento.archivo:
            return ""

        request = self.context.get("request")
        url = documento.archivo.url

        if request:
            return request.build_absolute_uri(url)

        return url


class TransporteLoteSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        factor = (
            FactorEmision.objects.filter(actividad__iexact="diesel")
            .order_by("-anio", "-updated_at")
            .first()
        )

        if not factor:
            factor = (
                FactorEmision.objects.filter(actividad__icontains="diesel")
                .order_by("-anio", "-updated_at")
                .first()
            )

        if not factor:
            raise serializers.ValidationError(
                {
                    "factor_diesel": (
                        "No hay factor de emision diesel registrado. "
                        "Importa el factor antes de guardar transporte."
                    )
                }
            )

        attrs["factor_diesel"] = factor.factor_emision
        return attrs

    class Meta:
        model = TransporteLote
        fields = [
            "id",
            "vehiculo",
            "patente",
            "latitud",
            "longitud",
            "fecha_hora",
            "ruta",
            "distancia_km",
            "consumo_estimado_litro_km",
            "litros_combustible",
            "factor_diesel",
            "litros_calculados",
            "emisiones_transporte_kg_co2e",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "factor_diesel",
            "litros_calculados",
            "emisiones_transporte_kg_co2e",
            "created_at",
            "updated_at",
        ]


class ExtraccionDocumentoSerializer(serializers.ModelSerializer):
    estado_revision_label = serializers.CharField(
        source="get_estado_revision_display",
        read_only=True,
    )

    class Meta:
        model = ExtraccionDocumento
        fields = [
            "id",
            "documento",
            "texto_extraido",
            "datos_sugeridos",
            "datos_validados",
            "estado_revision",
            "estado_revision_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "documento",
            "texto_extraido",
            "datos_sugeridos",
            "datos_validados",
            "estado_revision",
            "estado_revision_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "litros_calculados",
            "emisiones_transporte_kg_co2e",
            "created_at",
            "updated_at",
        ]


class EmpresaMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            "id",
            "empresa_id",
            "nombre",
            "rut",
            "region",
            "comuna",
            "rubro",
            "activa",
        ]
        read_only_fields = fields


class EmpresaConfiguracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmpresaConfiguracion
        fields = "__all__"
        read_only_fields = ["id", "empresa", "created_at", "updated_at"]


class UnidadOperativaMiniSerializer(serializers.ModelSerializer):
    empresa_id = serializers.CharField(source="empresa.empresa_id", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = UnidadOperativa
        fields = [
            "id",
            "unidad_id",
            "empresa_id",
            "empresa_nombre",
            "nombre",
            "tipo",
            "region",
            "comuna",
            "direccion",
            "descripcion",
            "activa",
        ]
        read_only_fields = fields


class LoteSerializer(serializers.ModelSerializer):
    empresa = serializers.CharField(source="empresa_aserradero", required=False)
    empresa_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    unidad_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    empresa_operacional = EmpresaMiniSerializer(source="empresa", read_only=True)
    unidad_operativa_detalle = UnidadOperativaMiniSerializer(source="unidad_operativa", read_only=True)
    actividades = EmisionLoteSerializer(many=True, read_only=True)
    documentos = DocumentoLoteSerializer(many=True, read_only=True)
    transportes = TransporteLoteSerializer(many=True, read_only=True)
    emisiones_kg_co2e = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        read_only=True,
    )
    total_emisiones_kg_co2e = serializers.DecimalField(
        source="emisiones_kg_co2e",
        max_digits=14,
        decimal_places=3,
        read_only=True,
    )
    densidad_kg_m3 = serializers.SerializerMethodField()
    porcentaje_carbono = serializers.SerializerMethodField()
    masa_madera_kg = serializers.SerializerMethodField()
    carbono_almacenado_kg = serializers.SerializerMethodField()
    co2_almacenado_kg = serializers.SerializerMethodField()
    balance_neto_kg_co2e = serializers.SerializerMethodField()
    estado_balance = serializers.SerializerMethodField()
    descripcion_balance = serializers.SerializerMethodField()
    trazabilidad_score = serializers.SerializerMethodField()
    completitud_score = serializers.SerializerMethodField()
    factor_score = serializers.SerializerMethodField()
    balance_calculado = serializers.SerializerMethodField()
    pasaporte_score = serializers.SerializerMethodField()
    estado_pasaporte = serializers.SerializerMethodField()
    razon_pasaporte = serializers.SerializerMethodField()
    datos_completos_score = serializers.SerializerMethodField()
    documentos_adjuntos_score = serializers.SerializerMethodField()
    factores_validos_score = serializers.SerializerMethodField()
    trazabilidad_confianza_score = serializers.SerializerMethodField()
    confianza_score = serializers.SerializerMethodField()
    estado_confianza = serializers.SerializerMethodField()
    descripcion_confianza = serializers.SerializerMethodField()

    class Meta:
        model = Lote
        fields = [
            "id_lote",
            "empresa",
            "empresa_id",
            "unidad_id",
            "empresa_operacional",
            "unidad_operativa",
            "unidad_operativa_detalle",
            "empresa_aserradero",
            "fecha",
            "especie",
            "volumen_m3",
            "origen",
            "tipo_producto",
            "estado",
            "observaciones",
            "emisiones_kg_co2e",
            "total_emisiones_kg_co2e",
            "densidad_kg_m3",
            "porcentaje_carbono",
            "masa_madera_kg",
            "carbono_almacenado_kg",
            "co2_almacenado_kg",
            "balance_neto_kg_co2e",
            "estado_balance",
            "descripcion_balance",
            "trazabilidad_score",
            "completitud_score",
            "factor_score",
            "balance_calculado",
            "pasaporte_score",
            "estado_pasaporte",
            "razon_pasaporte",
            "datos_completos_score",
            "documentos_adjuntos_score",
            "factores_validos_score",
            "trazabilidad_confianza_score",
            "confianza_score",
            "estado_confianza",
            "descripcion_confianza",
            "actividades",
            "documentos",
            "transportes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "emisiones_kg_co2e",
            "total_emisiones_kg_co2e",
            "densidad_kg_m3",
            "porcentaje_carbono",
            "masa_madera_kg",
            "carbono_almacenado_kg",
            "co2_almacenado_kg",
            "balance_neto_kg_co2e",
            "estado_balance",
            "descripcion_balance",
            "trazabilidad_score",
            "completitud_score",
            "factor_score",
            "balance_calculado",
            "pasaporte_score",
            "estado_pasaporte",
            "razon_pasaporte",
            "datos_completos_score",
            "documentos_adjuntos_score",
            "factores_validos_score",
            "trazabilidad_confianza_score",
            "confianza_score",
            "estado_confianza",
            "descripcion_confianza",
            "actividades",
            "documentos",
            "transportes",
            "empresa_operacional",
            "unidad_operativa_detalle",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        empresa_id = attrs.pop("empresa_id", "")
        unidad_id = attrs.pop("unidad_id", "")
        if unidad_id:
            try:
                unidad = UnidadOperativa.objects.select_related("empresa").get(
                    unidad_id=unidad_id
                )
            except UnidadOperativa.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"unidad_id": "La unidad operativa no existe."}
                ) from exc
            attrs["unidad_operativa"] = unidad
            attrs["empresa"] = unidad.empresa
            attrs.setdefault("empresa_aserradero", unidad.empresa.nombre)
        elif empresa_id:
            try:
                attrs["empresa"] = Empresa.objects.get(empresa_id=empresa_id)
            except Empresa.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"empresa_id": "La empresa no existe."}
                ) from exc

        if "empresa_aserradero" not in attrs:
            raise serializers.ValidationError(
                {"empresa": "Este campo es requerido."}
            )
        especie = attrs.get("especie") or getattr(self.instance, "especie", None)

        if especie and not EspecieMadera.objects.filter(nombre__iexact=especie).exists():
            raise serializers.ValidationError(
                {"especie": "Selecciona una especie de madera registrada."}
            )

        return attrs

    def _carbono(self, lote):
        if not hasattr(lote, "_serializer_carbono"):
            lote._serializer_carbono = calcular_carbono_almacenado(lote)
        return lote._serializer_carbono

    def _balance(self, lote):
        if not hasattr(lote, "_serializer_balance"):
            lote._serializer_balance = calcular_balance_lote(lote)
        return lote._serializer_balance

    def _pasaporte(self, lote):
        if not hasattr(lote, "_serializer_pasaporte"):
            lote._serializer_pasaporte = calcular_pasaporte_lote(lote)
        return lote._serializer_pasaporte

    def _confianza(self, lote):
        if not hasattr(lote, "_serializer_confianza"):
            lote._serializer_confianza = calcular_confianza_lote(lote)
        return lote._serializer_confianza

    def get_densidad_kg_m3(self, lote):
        return self._carbono(lote)["densidad_kg_m3"]

    def get_porcentaje_carbono(self, lote):
        return self._carbono(lote)["porcentaje_carbono"]

    def get_masa_madera_kg(self, lote):
        return self._carbono(lote)["masa_madera_kg"]

    def get_carbono_almacenado_kg(self, lote):
        return self._carbono(lote)["carbono_almacenado_kg"]

    def get_co2_almacenado_kg(self, lote):
        return self._carbono(lote)["co2_almacenado_kg"]

    def get_balance_neto_kg_co2e(self, lote):
        return self._balance(lote)["balance_neto_kg_co2e"]

    def get_estado_balance(self, lote):
        return self._balance(lote)["estado_balance"]

    def get_descripcion_balance(self, lote):
        return self._balance(lote)["descripcion_balance"]

    def get_trazabilidad_score(self, lote):
        return self._pasaporte(lote)["trazabilidad_score"]

    def get_completitud_score(self, lote):
        return self._pasaporte(lote)["completitud_score"]

    def get_factor_score(self, lote):
        return self._pasaporte(lote)["factor_score"]

    def get_balance_calculado(self, lote):
        return self._pasaporte(lote)["balance_calculado"]

    def get_pasaporte_score(self, lote):
        return self._pasaporte(lote)["pasaporte_score"]

    def get_estado_pasaporte(self, lote):
        return self._pasaporte(lote)["estado_pasaporte"]

    def get_razon_pasaporte(self, lote):
        return self._pasaporte(lote)["razon_pasaporte"]

    def get_datos_completos_score(self, lote):
        return self._confianza(lote)["datos_completos_score"]

    def get_documentos_adjuntos_score(self, lote):
        return self._confianza(lote)["documentos_adjuntos_score"]

    def get_factores_validos_score(self, lote):
        return self._confianza(lote)["factores_validos_score"]

    def get_trazabilidad_confianza_score(self, lote):
        return self._confianza(lote)["trazabilidad_confianza_score"]

    def get_confianza_score(self, lote):
        return self._confianza(lote)["confianza_score"]

    def get_estado_confianza(self, lote):
        return self._confianza(lote)["estado_confianza"]

    def get_descripcion_confianza(self, lote):
        return self._confianza(lote)["descripcion_confianza"]
