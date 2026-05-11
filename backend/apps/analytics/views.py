import logging
import csv
import json
from io import StringIO

from decimal import Decimal
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Empresa, EmisionLote
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q, Count, F, Sum as DBSum, ExpressionWrapper, DecimalField, IntegerField, Value, OuterRef, Subquery
from django.db.models.functions import Coalesce
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncYear, TruncDay
from collections import defaultdict
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

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
    UnidadOperativa,
    UsuarioEmpresa,
)
from .serializers import (
    DocumentoLoteSerializer,
    EvidenciaSerializer,
    EmisionLoteSerializer,
    EmpresaConfiguracionSerializer,
    EmpresaSerializer,
    EspecieMaderaSerializer,
    ExtraccionDocumentoSerializer,
    FactorEmisionSerializer,
    LoteSerializer,
    TransporteLoteSerializer,
    UnidadOperativaSerializer,
    UsuarioEmpresaCreateSerializer,
    UsuarioEmpresaSerializer,
)
from .services.carbono import calcular_balance_lote, calcular_carbono_almacenado
from .services.certificado import generar_certificado_lote_pdf
from .services.documentos import (
    extraer_documento_estructurado,
    extraer_texto_archivo,
)
from .services.confianza import calcular_confianza_lote
from .services.integraciones import construir_payload_lote_bim
from .services.ocr import aplicar_datos_validados, generar_extraccion_documento
from .services.pasaporte import calcular_pasaporte_lote
from .services.rutas import route_distance_km
from .services.activity_semantics import is_diesel_activity
from .services.verificacion import generar_resumen_verificacion
from .services.validador import ValidadorDatos
from .models import HistorialCambioLote
from .factores import FACTOR_CATEGORIES, normalize_activity_key
from apps.iot.models import LecturaSensor
from .services.importadores import (
    ImportadorActividadesLote,
    ImportadorEmpresas,
    ImportadorFactores,
    ImportadorLotes,
    ImportadorUnidadesOperativas,
)
from .services.empresa_completa_importer import ImportadorEmpresaCompleta
from .services.template_generator import generate_complete_import_template
from .services.decision_engine import (
    calculate_risk_profile,
    optimize_rows,
    simulate_rows,
    summarize_rows,
)
from .services.local_advisor import generar_analisis_local

try:
    from .services.ai_advisor import generar_analisis_ia
except Exception:
    generar_analisis_ia = None


logger = logging.getLogger(__name__)


IOT_ANALYTICS_WINDOW_HOURS = 24


IOT_TYPE_ANALYTICS = {
    LecturaSensor.Tipo.DIESEL_LITROS: {
        "actividad": "IoT - Diesel litros",
        "categoria": "Combustible",
    },
    LecturaSensor.Tipo.GASOLINA_LITROS: {
        "actividad": "IoT - Gasolina litros",
        "categoria": "Combustible",
    },
    LecturaSensor.Tipo.ELECTRICIDAD_KWH: {
        "actividad": "IoT - Electricidad kWh",
        "categoria": "Electricidad",
    },
    LecturaSensor.Tipo.HORAS_MAQUINARIA: {
        "actividad": "IoT - Horas maquinaria",
        "categoria": "Maquinaria",
    },
    LecturaSensor.Tipo.TEMPERATURA: {
        "actividad": "IoT - Temperatura",
        "categoria": "Condiciones ambientales",
    },
    LecturaSensor.Tipo.HUMEDAD: {
        "actividad": "IoT - Humedad",
        "categoria": "Condiciones ambientales",
    },
}


def get_iot_analytics_queryset(empresa, fecha_inicio=None, fecha_fin=None, unidad_nombre=None):
    desde = timezone.now() - timedelta(hours=IOT_ANALYTICS_WINDOW_HOURS)
    queryset = LecturaSensor.objects.filter(
        empresa__iexact=empresa.nombre,
        fecha_registro__gte=desde,
    )

    if fecha_inicio:
        queryset = queryset.filter(fecha_registro__date__gte=fecha_inicio)

    if fecha_fin:
        queryset = queryset.filter(fecha_registro__date__lte=fecha_fin)

    if unidad_nombre:
        queryset = queryset.filter(unidad_operativa__iexact=unidad_nombre)

    return queryset


def build_iot_analytics_row(lectura, empresa):
    metadata = IOT_TYPE_ANALYTICS.get(
        lectura.tipo,
        {"actividad": f"IoT - {lectura.tipo}", "categoria": "IoT"},
    )
    valor = float(lectura.valor or 0)
    emisiones = float(lectura.co2e_estimado or 0)
    factor = emisiones / valor if valor else 0

    return {
        "id": f"iot-{lectura.id}",
        "fecha": lectura.fecha_registro.date().isoformat(),
        "empresa": empresa.nombre,
        "empresa_id": empresa.empresa_id,
        "unidad_operativa": lectura.unidad_operativa or "Sin unidad",
        "unidad_nombre": lectura.unidad_operativa or "Sin unidad",
        "unidad_id": "",
        "tipo_unidad": "IoT",
        "actividad": metadata["actividad"],
        "actividad_key": lectura.tipo,
        "categoria": metadata["categoria"],
        "tipo_consumo_combustible": "",
        "cantidad": valor,
        "unidad": lectura.unidad,
        "factor_emision": factor,
        "emisiones": emisiones,
        "id_lote": "IoT",
        "tipo_asignacion": "simulacion_iot",
        "fuente_factor": "Sensor IoT simulado",
        "anio_factor": None,
        "es_iot": True,
        "sensor": lectura.sensor,
        "fecha_registro": lectura.fecha_registro.isoformat(),
    }


def build_iot_analytics_rows(empresa, fecha_inicio=None, fecha_fin=None, unidad_nombre=None):
    return [
        build_iot_analytics_row(lectura, empresa)
        for lectura in get_iot_analytics_queryset(
            empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            unidad_nombre=unidad_nombre,
        )
    ]


def add_group_value(grouped, key, value):
    label = key or "Sin datos"
    grouped[label] = grouped.get(label, 0) + float(value or 0)


def sort_grouped_desc(grouped):
    return dict(sorted(grouped.items(), key=lambda item: item[1], reverse=True))


def serialize_auth_user(user):
    if not user or not user.is_authenticated:
        return None

    empresas = UsuarioEmpresa.objects.select_related("empresa").filter(
        user=user,
        activo=True,
    )

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "nombre": user.get_full_name().strip() or user.username,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "empresas": [
            {
                "empresa_id": perfil.empresa.empresa_id,
                "empresa_nombre": perfil.empresa.nombre,
                "rol": perfil.rol,
            }
            for perfil in empresas
        ],
    }


@csrf_exempt
@api_view(["GET"])
def auth_me(request):
    return Response(
        {
            "authenticated": bool(request.user and request.user.is_authenticated),
            "user": serialize_auth_user(request.user),
            "has_users": User.objects.exists(),
        }
    )


@csrf_exempt
@api_view(["POST"])
def auth_login(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""

    user = authenticate(request, username=username, password=password)

    if not user:
        return Response(
            {"error": "Credenciales invalidas."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not user.is_active:
        return Response(
            {"error": "El usuario esta inactivo."},
            status=status.HTTP_403_FORBIDDEN,
        )

    login(request, user)
    return Response({"authenticated": True, "user": serialize_auth_user(user)})


@csrf_exempt
@api_view(["POST"])
def auth_logout(request):
    logout(request)
    return Response({"authenticated": False})


@csrf_exempt
@api_view(["POST"])
def auth_bootstrap(request):
    if User.objects.exists():
        return Response(
            {"error": "El usuario inicial ya fue creado."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    email = (request.data.get("email") or "").strip()
    first_name = (request.data.get("first_name") or "").strip()
    last_name = (request.data.get("last_name") or "").strip()

    if not username or len(password) < 8:
        return Response(
            {"error": "Ingresa usuario y una clave de al menos 8 caracteres."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    first_empresa = Empresa.objects.order_by("nombre").first()
    if first_empresa:
        UsuarioEmpresa.objects.create(
            user=user,
            empresa=first_empresa,
            rol=UsuarioEmpresa.Rol.ADMIN,
            cargo="Administrador",
        )

    login(request, user)
    return Response({"authenticated": True, "user": serialize_auth_user(user)})


@csrf_exempt
@api_view(["GET", "POST"])
def empresa_usuarios(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)

    if request.method == "GET":
        usuarios = UsuarioEmpresa.objects.select_related("user", "empresa").filter(
            empresa=empresa,
        )
        return Response(UsuarioEmpresaSerializer(usuarios, many=True).data)

    serializer = UsuarioEmpresaCreateSerializer(
        data=request.data,
        context={"empresa": empresa},
    )
    serializer.is_valid(raise_exception=True)
    usuario_empresa = serializer.save()
    return Response(
        UsuarioEmpresaSerializer(usuario_empresa).data,
        status=status.HTTP_201_CREATED,
    )


def build_system_status():
    return {
        "factores": FactorEmision.objects.count(),
        "empresas": Empresa.objects.count(),
        "unidades": UnidadOperativa.objects.count(),
        "lotes": Lote.objects.count(),
        "actividades": EmisionLote.objects.count(),
        "evidencias": DocumentoLote.objects.count() + Evidencia.objects.count(),
    }


def build_system_state_response():
    return {
        "empresas": Empresa.objects.count(),
        "factores_globales": FactorEmision.objects.count(),
    }


def get_empresa_or_404(empresa_id):
    return get_object_or_404(
        Empresa.objects.prefetch_related(
            "unidades_operativas",
            "lotes",
            "lotes__documentos",
            "lotes__actividades",
            "actividades_emision",
        ),
        empresa_id=empresa_id,
    )


def build_company_state_response(empresa):
    lotes = Lote.objects.filter(Q(empresa=empresa) | Q(unidad_operativa__empresa=empresa))
    actividades = EmisionLote.objects.filter(
        Q(empresa=empresa) | Q(lote__empresa=empresa) | Q(unidad_operativa__empresa=empresa)
    )
    evidencias = DocumentoLote.objects.filter(lote__in=lotes)
    pasaportes = sum(
        1
        for lote in lotes.select_related("empresa", "unidad_operativa")
        if calcular_pasaporte_lote(lote)["estado_pasaporte"] != "Sin pasaporte"
    )

    return {
        "empresa_id": empresa.empresa_id,
        "unidades": empresa.unidades_operativas.count(),
        "lotes": lotes.count(),
        "actividades": actividades.count(),
        "evidencias": evidencias.count(),
        "pasaportes": pasaportes,
    }


def build_company_dashboard_response(empresa):
    lotes_qs = Lote.objects.select_related("empresa", "unidad_operativa").filter(
        Q(empresa=empresa) | Q(unidad_operativa__empresa=empresa)
    )

    actividades_qs = EmisionLote.objects.select_related(
        "empresa",
        "unidad_operativa",
        "lote",
        "lote__empresa",
        "lote__unidad_operativa",
    ).filter(Q(empresa=empresa) | Q(lote__empresa=empresa) | Q(unidad_operativa__empresa=empresa))

    rows = []
    emisiones_por_actividad = {}
    emisiones_por_categoria = {}
    emisiones_por_unidad = {}
    emisiones_por_empresa = {empresa.nombre: 0}
    emisiones_por_lote = {}
    total_emisiones = 0

    # Calcular CO2 almacenado total con una sola agregacion en BD.
    # Primero usa valores del lote; si faltan, toma densidad/carbono de la especie.
    especie_densidad = EspecieMadera.objects.filter(
        nombre__iexact=OuterRef("especie")
    ).values("densidad_kg_m3")[:1]
    especie_porcentaje_carbono = EspecieMadera.objects.filter(
        nombre__iexact=OuterRef("especie")
    ).values("porcentaje_carbono")[:1]
    densidad_expr = Coalesce(
        F("densidad_kg_m3"),
        Subquery(especie_densidad, output_field=DecimalField(max_digits=8, decimal_places=3)),
        Value(Decimal("0.0")),
        output_field=DecimalField(max_digits=8, decimal_places=3),
    )
    porcentaje_carbono_expr = Coalesce(
        F("porcentaje_carbono"),
        Subquery(
            especie_porcentaje_carbono,
            output_field=DecimalField(max_digits=5, decimal_places=4),
        ),
        Value(Decimal("0.0")),
        output_field=DecimalField(max_digits=5, decimal_places=4),
    )
    masa_expr = ExpressionWrapper(
        Coalesce(F("volumen_m3"), Value(Decimal("0.0"))) * densidad_expr,
        output_field=DecimalField(max_digits=18, decimal_places=6),
    )
    carbono_expr = ExpressionWrapper(
        masa_expr * porcentaje_carbono_expr,
        output_field=DecimalField(max_digits=18, decimal_places=8),
    )
    CO2_FACTOR = Decimal("3.67")
    co2_expr = ExpressionWrapper(
        carbono_expr * Value(CO2_FACTOR),
        output_field=DecimalField(max_digits=20, decimal_places=6),
    )

    co2_agg = lotes_qs.annotate(_co2=co2_expr).aggregate(total_co2=DBSum("_co2"))
    co2_almacenado_total = float(co2_agg.get("total_co2") or 0)

    # Evidencias totales y conteo de lotes
    evidencias_count = DocumentoLote.objects.filter(lote__in=lotes_qs).count()
    lotes_count = lotes_qs.count()

    # Pasaportes (heuristica): lotes con actividades y balance de carbono calculable.
    pasaportes_count = (
        lotes_qs.annotate(
            densidad_calc=densidad_expr,
            porcentaje_carbono_calc=porcentaje_carbono_expr,
        )
        .filter(
            Q(volumen_m3__isnull=False)
            & Q(densidad_calc__gt=0)
            & Q(porcentaje_carbono_calc__gt=0)
            & Q(actividades__isnull=False)
        )
        .distinct()
        .count()
    )

    for actividad in actividades_qs:
        emisiones = float(actividad.emisiones_kg_co2e or 0)
        lote = actividad.lote
        unidad_obj = actividad.unidad_operativa or getattr(lote, "unidad_operativa", None)
        empresa_obj = actividad.empresa or getattr(lote, "empresa", None) or empresa
        total_emisiones += emisiones
        rows.append(
            {
                "empresa": empresa_obj.nombre if empresa_obj else empresa.nombre,
                "empresa_id": empresa_obj.empresa_id if empresa_obj else empresa.empresa_id,
                "unidad_operativa": unidad_obj.nombre if unidad_obj else "Sin unidad",
                "unidad_id": unidad_obj.unidad_id if unidad_obj else "",
                "tipo_unidad": unidad_obj.tipo if unidad_obj else "Sin tipo",
                "actividad": actividad.actividad,
                "actividad_key": actividad.actividad_key,
                "categoria": actividad.categoria or "Otros",
                "cantidad": float(actividad.cantidad or 0),
                "unidad": actividad.unidad,
                "factor_emision": float(actividad.factor_emision or 0),
                "emisiones": emisiones,
                "fecha": (
                    actividad.fecha.isoformat()
                    if actividad.fecha
                    else actividad.created_at.date().isoformat()
                ),
                "id_lote": lote.id_lote if lote else "",
                "tipo_asignacion": actividad.tipo_asignacion,
            }
        )
        emisiones_por_actividad[actividad.actividad] = emisiones_por_actividad.get(actividad.actividad, 0) + emisiones
        emisiones_por_categoria[actividad.categoria or "Otros"] = emisiones_por_categoria.get(actividad.categoria or "Otros", 0) + emisiones
        unidad_label = unidad_obj.nombre if unidad_obj else "Sin unidad"
        emisiones_por_unidad[unidad_label] = emisiones_por_unidad.get(unidad_label, 0) + emisiones
        empresa_label = empresa_obj.nombre if empresa_obj else empresa.nombre
        emisiones_por_empresa[empresa_label] = emisiones_por_empresa.get(empresa_label, 0) + emisiones
        if lote:
            emisiones_por_lote[lote.id_lote] = emisiones_por_lote.get(lote.id_lote, 0) + emisiones

    iot_rows = build_iot_analytics_rows(empresa)
    for row in iot_rows:
        emisiones = float(row.get("emisiones") or 0)
        total_emisiones += emisiones
        rows.append(row)
        add_group_value(emisiones_por_actividad, row.get("actividad"), emisiones)
        add_group_value(emisiones_por_categoria, row.get("categoria"), emisiones)
        add_group_value(emisiones_por_unidad, row.get("unidad_nombre"), emisiones)
        add_group_value(emisiones_por_empresa, empresa.nombre, emisiones)

    emisiones_por_activity_sorted = dict(
        sorted(emisiones_por_actividad.items(), key=lambda item: item[1], reverse=True)
    )
    emisiones_por_category_sorted = dict(
        sorted(emisiones_por_categoria.items(), key=lambda item: item[1], reverse=True)
    )
    emisiones_por_unit_sorted = dict(
        sorted(emisiones_por_unidad.items(), key=lambda item: item[1], reverse=True)
    )
    emisiones_por_company_sorted = dict(
        sorted(emisiones_por_empresa.items(), key=lambda item: item[1], reverse=True)
    )

    # Build summary without running simulate/optimize (heavy operations moved to separate endpoints)
    return {
        "empresa_id": empresa.empresa_id,
        "empresa_nombre": empresa.nombre,
        "total_emisiones": total_emisiones,
        "emisiones_totales": total_emisiones,
        "co2_almacenado_total": co2_almacenado_total,
        "balance_neto_total": total_emisiones - co2_almacenado_total,
        "unidades_count": empresa.unidades_operativas.count(),
        "lotes_count": lotes_count,
        "actividades_count": len(rows),
        "lecturas_iot_count": len(iot_rows),
        "emisiones_iot_24h": sum(float(row.get("emisiones") or 0) for row in iot_rows),
        "evidencias_count": evidencias_count,
        "pasaportes_count": pasaportes_count,
        "actividad_critica": next(iter(emisiones_por_activity_sorted), "Sin datos"),
        "categoria_critica": next(iter(emisiones_por_category_sorted), "Sin datos"),
        "unidad_critica": next(iter(emisiones_por_unit_sorted), "Sin datos"),
        "datos": rows,
        "emisiones_por_actividad": emisiones_por_activity_sorted,
        "emisiones_por_categoria": emisiones_por_category_sorted,
        "emisiones_por_unidad_operativa": emisiones_por_unit_sorted,
        "emisiones_por_lote": emisiones_por_lote,
    }


@api_view(["GET", "POST"])
def empresas(request):
    if request.method == "GET":
        unidades_count = (
            UnidadOperativa.objects.filter(empresa=OuterRef("pk"))
            .values("empresa")
            .annotate(total=Count("pk"))
            .values("total")
        )
        lotes_count = (
            Lote.objects.filter(empresa=OuterRef("pk"))
            .values("empresa")
            .annotate(total=Count("pk"))
            .values("total")
        )
        actividades_stats = (
            EmisionLote.objects.filter(empresa=OuterRef("pk"))
            .values("empresa")
            .annotate(
                total=Count("pk"),
                emisiones=Coalesce(
                    DBSum("emisiones_kg_co2e"),
                    Value(0, output_field=DecimalField()),
                ),
            )
        )
        especie_densidad = EspecieMadera.objects.filter(
            nombre__iexact=OuterRef("especie")
        ).values("densidad_kg_m3")[:1]
        especie_porcentaje_carbono = EspecieMadera.objects.filter(
            nombre__iexact=OuterRef("especie")
        ).values("porcentaje_carbono")[:1]
        densidad_expr = Coalesce(
            F("densidad_kg_m3"),
            Subquery(especie_densidad, output_field=DecimalField(max_digits=8, decimal_places=3)),
            Value(Decimal("0.0")),
            output_field=DecimalField(max_digits=8, decimal_places=3),
        )
        porcentaje_carbono_expr = Coalesce(
            F("porcentaje_carbono"),
            Subquery(
                especie_porcentaje_carbono,
                output_field=DecimalField(max_digits=5, decimal_places=4),
            ),
            Value(Decimal("0.0")),
            output_field=DecimalField(max_digits=5, decimal_places=4),
        )
        co2_lote_expr = ExpressionWrapper(
            Coalesce(F("volumen_m3"), Value(Decimal("0.0")))
            * densidad_expr
            * porcentaje_carbono_expr
            * Value(Decimal("3.67")),
            output_field=DecimalField(max_digits=20, decimal_places=6),
        )
        co2_lotes_stats = (
            Lote.objects.filter(empresa=OuterRef("pk"))
            .annotate(co2_almacenado_calc=co2_lote_expr)
            .values("empresa")
            .annotate(
                total=Coalesce(
                    DBSum("co2_almacenado_calc"),
                    Value(0, output_field=DecimalField()),
                )
            )
            .values("total")
        )
        queryset = Empresa.objects.annotate(
            unidades_count_val=Coalesce(
                Subquery(unidades_count, output_field=IntegerField()),
                Value(0, output_field=IntegerField()),
            ),
            lotes_count_val=Coalesce(
                Subquery(lotes_count, output_field=IntegerField()),
                Value(0, output_field=IntegerField()),
            ),
            actividades_count_val=Coalesce(
                Subquery(actividades_stats.values("total"), output_field=IntegerField()),
                Value(0, output_field=IntegerField()),
            ),
            emisiones_totales_val=Coalesce(
                Subquery(actividades_stats.values("emisiones"), output_field=DecimalField()),
                Value(0, output_field=DecimalField()),
            ),
            co2_almacenado_val=Coalesce(
                Subquery(co2_lotes_stats, output_field=DecimalField()),
                Value(0, output_field=DecimalField()),
            ),
        )
        serializer = EmpresaSerializer(
            queryset,
            many=True,
            context={"is_list_view": True}
        )
        return Response(serializer.data)

    serializer = EmpresaSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PATCH", "DELETE"])
def empresa_detail(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)

    if request.method == "GET":
        return Response(EmpresaSerializer(empresa).data)

    if request.method == "DELETE":
        with transaction.atomic():
            EmisionLote.objects.filter(
                Q(empresa=empresa)
                | Q(unidad_operativa__empresa=empresa)
                | Q(lote__empresa=empresa)
            ).delete()
            Lote.objects.filter(empresa=empresa).delete()
            UnidadOperativa.objects.filter(empresa=empresa).delete()
            empresa.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = EmpresaSerializer(empresa, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def empresa_estado(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    return Response(build_company_state_response(empresa))


def build_empresa_configuracion_response(empresa, configuracion):
    return {
        "empresa": {
            "nombre": empresa.nombre,
            "empresa_id": empresa.empresa_id,
            "rut": empresa.rut,
            "rubro": empresa.rubro,
            "region": empresa.region,
            "comuna": empresa.comuna,
            "direccion": empresa.direccion,
            "contacto": empresa.contacto,
            "email": empresa.email,
            "telefono": empresa.telefono,
            "observaciones": empresa.observaciones,
        },
        "calculo": {
            "unidad_emisiones": configuracion.unidad_emisiones,
            "unidad_volumen_madera": configuracion.unidad_volumen_madera,
            "porcentaje_carbono_default": float(configuracion.porcentaje_carbono_default),
            "densidad_madera_default": float(configuracion.densidad_madera_default),
            "factor_electrico_default": configuracion.factor_electrico_default,
            "region_electrica_default": configuracion.region_electrica_default,
            "redondeo_decimales": configuracion.redondeo_decimales,
            "mostrar_balance_neto": configuracion.mostrar_balance_neto,
            "permitir_co2_almacenado": configuracion.permitir_co2_almacenado,
        },
        "importaciones": {
            "modo_importacion": configuracion.modo_importacion,
            "crear_unidades_automaticamente": configuracion.crear_unidades_automaticamente,
            "crear_lotes_automaticamente": configuracion.crear_lotes_automaticamente,
            "permitir_actividades_sin_factor": configuracion.permitir_actividades_sin_factor,
            "actualizar_registros_existentes": configuracion.actualizar_registros_existentes,
            "bloquear_duplicados": configuracion.bloquear_duplicados,
            "requerir_unidad_lote": configuracion.requerir_unidad_lote,
            "requerir_lote_actividad": configuracion.requerir_lote_actividad,
            "permitir_evidencias_sin_vinculo": configuracion.permitir_evidencias_sin_vinculo,
        },
        "pasaporte": {
            "pasaporte_activo": configuracion.pasaporte_activo,
            "requiere_balance_favorable": configuracion.pasaporte_requiere_balance_favorable,
            "requiere_evidencia": configuracion.pasaporte_requiere_evidencia,
            "requiere_trazabilidad": configuracion.pasaporte_requiere_trazabilidad,
            "score_verde": configuracion.score_pasaporte_verde,
            "score_plus": configuracion.score_pasaporte_plus,
            "score_confianza_minimo": configuracion.score_confianza_minimo,
        },
        "evidencias": {
            "requerida_pasaporte": configuracion.evidencia_requerida_pasaporte,
            "requerida_lotes_criticos": configuracion.evidencia_requerida_lotes_criticos,
            "umbral_lote_critico": float(configuracion.umbral_lote_critico),
            "permitir_empresa": configuracion.permitir_evidencia_empresa,
            "permitir_unidad": configuracion.permitir_evidencia_unidad,
            "permitir_lote": configuracion.permitir_evidencia_lote,
            "permitir_emision": configuracion.permitir_evidencia_emision,
            "formatos_permitidos": configuracion.formatos_evidencia_permitidos,
            "max_file_size_mb": configuracion.max_file_size_mb,
        },
        "reportes": {
            "agrupacion_default": configuracion.reporte_agrupacion_default,
            "periodo_default": configuracion.reporte_periodo_default,
            "mostrar_categoria": configuracion.reporte_mostrar_categoria,
            "mostrar_unidad": configuracion.reporte_mostrar_unidad,
            "mostrar_tabla": configuracion.reporte_mostrar_tabla,
            "unidad_visual_emisiones": configuracion.reporte_unidad_visual_emisiones,
            "lectura_ejecutiva": configuracion.reporte_lectura_ejecutiva,
            "equivalencias": configuracion.reporte_equivalencias,
        },
        "updated_at": configuracion.updated_at,
    }


@api_view(["GET", "PUT"])
def empresa_configuracion(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    configuracion, _ = EmpresaConfiguracion.objects.get_or_create(empresa=empresa)

    if request.method == "GET":
        return Response(build_empresa_configuracion_response(empresa, configuracion))

    data = request.data or {}
    empresa_data = data.get("empresa") or {}
    for field in ["nombre", "rut", "rubro", "region", "comuna", "direccion", "contacto", "email", "telefono", "observaciones"]:
        if field in empresa_data:
            setattr(empresa, field, empresa_data.get(field) or "")
    empresa.save()

    flat_payload = {}
    flat_payload.update(data.get("calculo") or {})
    flat_payload.update(data.get("importaciones") or {})

    pasaporte_data = data.get("pasaporte") or {}
    flat_payload.update({
        "pasaporte_activo": pasaporte_data.get("pasaporte_activo"),
        "pasaporte_requiere_balance_favorable": pasaporte_data.get("requiere_balance_favorable"),
        "pasaporte_requiere_evidencia": pasaporte_data.get("requiere_evidencia"),
        "pasaporte_requiere_trazabilidad": pasaporte_data.get("requiere_trazabilidad"),
        "score_pasaporte_verde": pasaporte_data.get("score_verde"),
        "score_pasaporte_plus": pasaporte_data.get("score_plus"),
        "score_confianza_minimo": pasaporte_data.get("score_confianza_minimo"),
    })

    evidencias_data = data.get("evidencias") or {}
    flat_payload.update({
        "evidencia_requerida_pasaporte": evidencias_data.get("requerida_pasaporte"),
        "evidencia_requerida_lotes_criticos": evidencias_data.get("requerida_lotes_criticos"),
        "umbral_lote_critico": evidencias_data.get("umbral_lote_critico"),
        "permitir_evidencia_empresa": evidencias_data.get("permitir_empresa"),
        "permitir_evidencia_unidad": evidencias_data.get("permitir_unidad"),
        "permitir_evidencia_lote": evidencias_data.get("permitir_lote"),
        "permitir_evidencia_emision": evidencias_data.get("permitir_emision"),
        "formatos_evidencia_permitidos": evidencias_data.get("formatos_permitidos"),
        "max_file_size_mb": evidencias_data.get("max_file_size_mb"),
    })

    reportes_data = data.get("reportes") or {}
    flat_payload.update({
        "reporte_agrupacion_default": reportes_data.get("agrupacion_default"),
        "reporte_periodo_default": reportes_data.get("periodo_default"),
        "reporte_mostrar_categoria": reportes_data.get("mostrar_categoria"),
        "reporte_mostrar_unidad": reportes_data.get("mostrar_unidad"),
        "reporte_mostrar_tabla": reportes_data.get("mostrar_tabla"),
        "reporte_unidad_visual_emisiones": reportes_data.get("unidad_visual_emisiones"),
        "reporte_lectura_ejecutiva": reportes_data.get("lectura_ejecutiva"),
        "reporte_equivalencias": reportes_data.get("equivalencias"),
    })

    flat_payload = {key: value for key, value in flat_payload.items() if value is not None}
    serializer = EmpresaConfiguracionSerializer(configuracion, data=flat_payload, partial=True)
    if serializer.is_valid():
        serializer.save()
        configuracion.refresh_from_db()
        return Response(build_empresa_configuracion_response(empresa, configuracion))

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def empresa_dashboard(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    # If client requests a light response, return aggregated KPIs without heavy processing
    light = (request.GET.get("light") or "").lower() in ("1", "true", "yes")
    debug = (request.GET.get("debug") or "").lower() in ("1", "true", "yes")
    if light:
        # Aggregations performed in DB for speed
        t0 = __import__("time").perf_counter()
        actividades_qs = EmisionLote.objects.filter(
            Q(empresa=empresa) | Q(lote__empresa=empresa) | Q(unidad_operativa__empresa=empresa)
        )
        total_agg = actividades_qs.aggregate(total=Sum("emisiones_kg_co2e"))
        total_emisiones = float(total_agg.get("total") or 0)
        lotes_qs = Lote.objects.filter(Q(empresa=empresa) | Q(unidad_operativa__empresa=empresa))
        especie_densidad = EspecieMadera.objects.filter(
            nombre__iexact=OuterRef("especie")
        ).values("densidad_kg_m3")[:1]
        especie_porcentaje_carbono = EspecieMadera.objects.filter(
            nombre__iexact=OuterRef("especie")
        ).values("porcentaje_carbono")[:1]
        densidad_expr = Coalesce(
            F("densidad_kg_m3"),
            Subquery(especie_densidad, output_field=DecimalField(max_digits=8, decimal_places=3)),
            Value(Decimal("0.0")),
            output_field=DecimalField(max_digits=8, decimal_places=3),
        )
        porcentaje_carbono_expr = Coalesce(
            F("porcentaje_carbono"),
            Subquery(
                especie_porcentaje_carbono,
                output_field=DecimalField(max_digits=5, decimal_places=4),
            ),
            Value(Decimal("0.0")),
            output_field=DecimalField(max_digits=5, decimal_places=4),
        )
        co2_expr = ExpressionWrapper(
            Coalesce(F("volumen_m3"), Value(Decimal("0.0")))
            * densidad_expr
            * porcentaje_carbono_expr
            * Value(Decimal("3.67")),
            output_field=DecimalField(max_digits=20, decimal_places=6),
        )
        co2_agg = lotes_qs.annotate(_co2=co2_expr).aggregate(total_co2=DBSum("_co2"))
        co2_almacenado_total = float(co2_agg.get("total_co2") or 0)

        emisiones_por_actividad = {
            item["actividad"] or "Sin actividad": float(item["emisiones"] or 0)
            for item in actividades_qs.values("actividad")
            .annotate(emisiones=Sum("emisiones_kg_co2e"))
            .order_by("-emisiones")
        }

        emisiones_por_categoria = {
            item["categoria"] or "Sin categoria": float(item["emisiones"] or 0)
            for item in actividades_qs.values("categoria")
            .annotate(emisiones=Sum("emisiones_kg_co2e"))
            .order_by("-emisiones")
        }

        emisiones_por_unidad = {
            item["unidad_nombre"] or "Sin unidad": float(item["emisiones"] or 0)
            for item in actividades_qs.values(unidad_nombre=F("unidad_operativa__nombre"))
            .annotate(emisiones=Sum("emisiones_kg_co2e"))
            .order_by("-emisiones")
        }

        iot_rows = build_iot_analytics_rows(empresa)
        emisiones_iot = sum(float(row.get("emisiones") or 0) for row in iot_rows)
        total_emisiones += emisiones_iot
        for row in iot_rows:
            emisiones = float(row.get("emisiones") or 0)
            add_group_value(emisiones_por_actividad, row.get("actividad"), emisiones)
            add_group_value(emisiones_por_categoria, row.get("categoria"), emisiones)
            add_group_value(emisiones_por_unidad, row.get("unidad_nombre"), emisiones)

        actividades_count = actividades_qs.count()
        t1 = __import__("time").perf_counter()
        payload = {
            "empresa_id": empresa.empresa_id,
            "empresa_nombre": empresa.nombre,
            "total_emisiones": total_emisiones,
            "co2_almacenado_total": co2_almacenado_total,
            "balance_neto_total": total_emisiones - co2_almacenado_total,
            "actividades_count": actividades_count + len(iot_rows),
            "lecturas_iot_count": len(iot_rows),
            "emisiones_iot_24h": emisiones_iot,
            "emisiones_por_actividad": sort_grouped_desc(emisiones_por_actividad),
            "emisiones_por_categoria": sort_grouped_desc(emisiones_por_categoria),
            "emisiones_por_unidad_operativa": sort_grouped_desc(emisiones_por_unidad),
            "datos": iot_rows,
        }
        if debug:
            payload["_timings"] = {"aggregation_seconds": t1 - t0}

        return Response(payload)
    # Full dashboard (non-light) — build response but avoid heavy simulations/optimizations
    t_start = __import__("time").perf_counter()
    resp = build_company_dashboard_response(empresa)
    t_end = __import__("time").perf_counter()
    if debug:
        resp["_timings"] = {"build_seconds": t_end - t_start}
    return Response(resp)


@api_view(["GET"])
def empresa_unidades(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    queryset = empresa.unidades_operativas.select_related("empresa")
    unidad_id = request.query_params.get("unidad_id")
    include_detail = (request.query_params.get("detail") or "").lower() in ("1", "true", "yes")

    if unidad_id:
        unidad_filter = Q(unidad_id=unidad_id)
        if str(unidad_id).isdigit():
            unidad_filter |= Q(id=int(unidad_id))
        queryset = queryset.filter(unidad_filter)

    if include_detail:
        serializer = UnidadOperativaSerializer(
            queryset.prefetch_related(
                "lotes",
                "lotes__actividades",
                "lotes__documentos",
                "actividades_emision",
                "actividades_emision__lote",
            ),
            many=True,
        )
        return Response(serializer.data)

    actividades_unidad = (
        EmisionLote.objects.filter(unidad_operativa=OuterRef("pk"))
        .values("unidad_operativa")
        .annotate(total=DBSum("emisiones_kg_co2e"))
        .values("total")[:1]
    )

    rows = (
        queryset.annotate(
            lotes_count_val=Count("lotes", distinct=True),
            actividades_count_val=Count("actividades_emision", distinct=True),
            evidencias_count_val=Count("lotes__documentos", distinct=True),
            emisiones_totales_val=Coalesce(
                Subquery(
                    actividades_unidad,
                    output_field=DecimalField(max_digits=18, decimal_places=3),
                ),
                Value(Decimal("0.0")),
                output_field=DecimalField(max_digits=18, decimal_places=3),
            ),
        )
        .values(
            "id",
            "unidad_id",
            "empresa_id",
            "empresa__empresa_id",
            "empresa__nombre",
            "nombre",
            "tipo",
            "region",
            "comuna",
            "direccion",
            "descripcion",
            "activa",
            "lotes_count_val",
            "actividades_count_val",
            "evidencias_count_val",
            "emisiones_totales_val",
            "created_at",
            "updated_at",
        )
        .order_by("empresa__nombre", "nombre")
    )

    payload = [
        {
            "id": row["id"],
            "unidad_id": row["unidad_id"],
            "empresa": row["empresa_id"],
            "empresa_id": row["empresa__empresa_id"],
            "empresa_nombre": row["empresa__nombre"],
            "nombre": row["nombre"],
            "tipo": row["tipo"],
            "region": row["region"],
            "comuna": row["comuna"],
            "direccion": row["direccion"],
            "descripcion": row["descripcion"],
            "activa": row["activa"],
            "lotes_count": row["lotes_count_val"],
            "actividades_count": row["actividades_count_val"],
            "emisiones_totales_kg_co2e": row["emisiones_totales_val"] or 0,
            "pasaportes_count": 0,
            "evidencias_count": row["evidencias_count_val"],
            "lotes_resumen": [],
            "actividades_resumen": [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]

    return Response(payload)


@api_view(["GET"])
def empresa_lotes(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    queryset = Lote.objects.select_related("empresa", "unidad_operativa").filter(
        Q(empresa=empresa) | Q(unidad_operativa__empresa=empresa)
    )

    especie_densidad = EspecieMadera.objects.filter(nombre__iexact=OuterRef("especie")).values(
        "densidad_kg_m3"
    )[:1]
    especie_porcentaje_carbono = EspecieMadera.objects.filter(
        nombre__iexact=OuterRef("especie")
    ).values("porcentaje_carbono")[:1]
    densidad_expr = Coalesce(
        F("densidad_kg_m3"),
        Subquery(especie_densidad, output_field=DecimalField(max_digits=8, decimal_places=3)),
        Value(Decimal("0.0")),
        output_field=DecimalField(max_digits=8, decimal_places=3),
    )
    porcentaje_carbono_expr = Coalesce(
        F("porcentaje_carbono"),
        Subquery(
            especie_porcentaje_carbono,
            output_field=DecimalField(max_digits=5, decimal_places=4),
        ),
        Value(Decimal("0.0")),
        output_field=DecimalField(max_digits=5, decimal_places=4),
    )
    masa_expr = ExpressionWrapper(
        Coalesce(F("volumen_m3"), Value(Decimal("0.0"))) * densidad_expr,
        output_field=DecimalField(max_digits=18, decimal_places=6),
    )
    carbono_expr = ExpressionWrapper(
        masa_expr * porcentaje_carbono_expr,
        output_field=DecimalField(max_digits=20, decimal_places=8),
    )
    co2_expr = ExpressionWrapper(
        carbono_expr * Value(Decimal("3.67")),
        output_field=DecimalField(max_digits=20, decimal_places=6),
    )
    balance_neto_expr = ExpressionWrapper(
        Coalesce(
            DBSum("actividades__emisiones_kg_co2e"),
            Value(Decimal("0.0")),
            output_field=DecimalField(max_digits=14, decimal_places=3),
        )
        - co2_expr,
        output_field=DecimalField(max_digits=20, decimal_places=6),
    )

    rows = (
        queryset.annotate(
            emisiones_total=Coalesce(
                DBSum("actividades__emisiones_kg_co2e"),
                Value(Decimal("0.0")),
                output_field=DecimalField(max_digits=14, decimal_places=3),
            ),
            masa_madera_calc=masa_expr,
            co2_almacenado_calc=co2_expr,
            balance_neto_calc=balance_neto_expr,
        )
        .values(
            "id_lote",
            "empresa_aserradero",
            "fecha",
            "especie",
            "volumen_m3",
            "origen",
            "estado",
            "observaciones",
            "emisiones_total",
            "masa_madera_calc",
            "co2_almacenado_calc",
            "balance_neto_calc",
        )
        .order_by("-fecha", "-id_lote")
    )

    payload = [
        {
            "id_lote": row.get("id_lote"),
            "empresa_aserradero": row.get("empresa_aserradero"),
            "fecha": row.get("fecha"),
            "especie": row.get("especie"),
            "volumen_m3": row.get("volumen_m3"),
            "origen": row.get("origen"),
            "estado": row.get("estado"),
            "observaciones": row.get("observaciones"),
            "emisiones_kg_co2e": row.get("emisiones_total") or 0,
            "total_emisiones_kg_co2e": row.get("emisiones_total") or 0,
            "masa_madera_kg": row.get("masa_madera_calc") or 0,
            "co2_almacenado_kg": row.get("co2_almacenado_calc") or 0,
            "balance_neto_kg_co2e": row.get("balance_neto_calc") or 0,
        }
        for row in rows
    ]

    return Response(payload)


@api_view(["GET"])
def empresa_actividades(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    queryset = EmisionLote.objects.select_related(
        "empresa",
        "unidad_operativa",
        "lote",
    ).filter(Q(empresa=empresa) | Q(lote__empresa=empresa) | Q(unidad_operativa__empresa=empresa)).order_by("-created_at")
    paginator = PageNumberPagination()
    try:
        paginator.page_size = int(request.query_params.get("page_size", 50))
    except Exception:
        paginator.page_size = 50

    page = paginator.paginate_queryset(queryset, request)
    serializer = EmisionLoteSerializer(page, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
def empresa_emisiones(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    # Use DB aggregations for KPIs and provide paginated rows
    debug = (request.GET.get("debug") or "").lower() in ("1", "true", "yes")
    t0 = __import__("time").perf_counter()
    actividades_qs = EmisionLote.objects.select_related(
        "empresa",
        "unidad_operativa",
        "lote",
        "lote__empresa",
        "lote__unidad_operativa",
    ).filter(
        Q(empresa=empresa) | Q(lote__empresa=empresa) | Q(unidad_operativa__empresa=empresa)
    )

    total_emisiones = float(actividades_qs.aggregate(total=Sum("emisiones_kg_co2e"))["total"] or 0)

    actividad_top = (
        actividades_qs.values("actividad").annotate(emisiones=Sum("emisiones_kg_co2e")).order_by("-emisiones").first()
    ) or {"actividad": "Sin datos", "emisiones": 0}

    categoria_top = (
        actividades_qs.values("categoria").annotate(emisiones=Sum("emisiones_kg_co2e")).order_by("-emisiones").first()
    ) or {"categoria": "Sin datos", "emisiones": 0}

    unidad_top = (
        actividades_qs.values(unidad_nombre=F("unidad_operativa__nombre")).annotate(emisiones=Sum("emisiones_kg_co2e")).order_by("-emisiones").first()
    ) or {"unidad_nombre": "Sin datos", "emisiones": 0}

    lote_top = (
        actividades_qs.values(id_lote=F("lote__id_lote")).annotate(emisiones=Sum("emisiones_kg_co2e")).order_by("-emisiones").first()
    ) or {"id_lote": "Sin datos", "emisiones": 0}

    emisiones_por_actividad = [
        {
            "actividad": item.get("actividad") or "Sin actividad",
            "emisiones": float(item.get("emisiones") or 0),
        }
        for item in actividades_qs.values("actividad")
        .annotate(emisiones=Sum("emisiones_kg_co2e"))
        .order_by("-emisiones")
    ]
    emisiones_por_unidad = [
        {
            "unidad": item.get("unidad_nombre") or "Sin unidad",
            "emisiones": float(item.get("emisiones") or 0),
        }
        for item in actividades_qs.values(unidad_nombre=F("unidad_operativa__nombre"))
        .annotate(emisiones=Sum("emisiones_kg_co2e"))
        .order_by("-emisiones")
    ]

    iot_rows = build_iot_analytics_rows(empresa)
    emisiones_iot = sum(float(row.get("emisiones") or 0) for row in iot_rows)
    total_emisiones += emisiones_iot

    actividad_totals = {
        item["actividad"]: float(item["emisiones"] or 0)
        for item in emisiones_por_actividad
    }
    unidad_totals = {
        item["unidad"]: float(item["emisiones"] or 0)
        for item in emisiones_por_unidad
    }
    categoria_totals = {
        item["categoria"] or "Sin categoria": float(item["emisiones"] or 0)
        for item in actividades_qs.values("categoria")
        .annotate(emisiones=Sum("emisiones_kg_co2e"))
        .order_by("-emisiones")
    }

    for row in iot_rows:
        emisiones = float(row.get("emisiones") or 0)
        add_group_value(actividad_totals, row.get("actividad"), emisiones)
        add_group_value(unidad_totals, row.get("unidad_nombre"), emisiones)
        add_group_value(categoria_totals, row.get("categoria"), emisiones)

    emisiones_por_actividad = [
        {"actividad": actividad, "emisiones": emisiones}
        for actividad, emisiones in sort_grouped_desc(actividad_totals).items()
    ]
    emisiones_por_unidad = [
        {"unidad": unidad, "emisiones": emisiones}
        for unidad, emisiones in sort_grouped_desc(unidad_totals).items()
    ]
    categoria_top = (
        {"categoria": next(iter(sort_grouped_desc(categoria_totals)), "Sin datos"), "emisiones": next(iter(sort_grouped_desc(categoria_totals).values()), 0)}
        if categoria_totals
        else {"categoria": "Sin datos", "emisiones": 0}
    )
    actividad_top = emisiones_por_actividad[0] if emisiones_por_actividad else {"actividad": "Sin datos", "emisiones": 0}
    unidad_top = (
        {"unidad_nombre": emisiones_por_unidad[0]["unidad"], "emisiones": emisiones_por_unidad[0]["emisiones"]}
        if emisiones_por_unidad
        else {"unidad_nombre": "Sin datos", "emisiones": 0}
    )

    actividades_count = actividades_qs.count() + len(iot_rows)

    # Paginate rows
    paginator = PageNumberPagination()
    try:
        paginator.page_size = int(request.query_params.get("page_size", 50))
    except Exception:
        paginator.page_size = 50

    qs_rows = actividades_qs.order_by("-emisiones_kg_co2e")
    page = paginator.paginate_queryset(qs_rows, request)

    # Fetch factor lookup only for page
    factor_keys = {(a.actividad_key, a.unidad) for a in page if a.actividad_key and a.unidad}
    factor_lookup = {}
    if factor_keys:
        factor_q = Q()
        for actividad_key, unidad in factor_keys:
            factor_q |= Q(actividad_key=actividad_key, unidad=unidad)
        for factor in FactorEmision.objects.filter(factor_q).order_by("-anio", "-updated_at"):
            factor_lookup.setdefault((factor.actividad_key, factor.unidad), factor)

    diesel_total = 0.0
    actividades_sin_factor = actividades_qs.filter(
        Q(factor_emision__isnull=True) | Q(factor_emision=0)
    ).count()

    for actividad in actividades_qs.values(
        "actividad",
        "actividad_key",
        "categoria",
        "emisiones_kg_co2e",
    ):
        if is_diesel_activity(
            {
                "actividad": actividad.get("actividad"),
                "actividad_key": actividad.get("actividad_key"),
                "categoria": actividad.get("categoria") or "Sin categoria",
            }
        ):
            diesel_total += float(actividad.get("emisiones_kg_co2e") or 0)

    diesel_total += sum(
        float(row.get("emisiones") or 0)
        for row in iot_rows
        if row.get("actividad_key") in {
            LecturaSensor.Tipo.DIESEL_LITROS,
            LecturaSensor.Tipo.GASOLINA_LITROS,
        }
    )

    rows = []
    for actividad in page:
        lote = actividad.lote
        unidad_obj = actividad.unidad_operativa or getattr(lote, "unidad_operativa", None)
        emisiones = float(actividad.emisiones_kg_co2e or 0)
        categoria = actividad.categoria or "Sin categoria"
        unidad_nombre = unidad_obj.nombre if unidad_obj else "Sin unidad"
        unidad_id = unidad_obj.unidad_id if unidad_obj else ""
        id_lote = lote.id_lote if lote else ""
        factor = factor_lookup.get((actividad.actividad_key, actividad.unidad))

        rows.append(
            {
                "id": actividad.id,
                "fecha": (
                    actividad.fecha.isoformat() if actividad.fecha else actividad.created_at.date().isoformat()
                ),
                "empresa": empresa.nombre,
                "unidad_id": unidad_id,
                "unidad_nombre": unidad_nombre,
                "id_lote": id_lote,
                "actividad": actividad.actividad,
                "actividad_key": actividad.actividad_key,
                "categoria": categoria,
                "tipo_consumo_combustible": actividad.tipo_consumo_combustible,
                "cantidad": float(actividad.cantidad or 0),
                "unidad": actividad.unidad,
                "factor_emision": float(actividad.factor_emision or 0),
                "emisiones": emisiones,
                "fuente_factor": factor.fuente if factor else "",
                "anio_factor": factor.anio if factor else None,
            }
        )

    if request.query_params.get("page", "1") in ("1", ""):
        rows = sorted(
            iot_rows + rows,
            key=lambda row: (
                1 if row.get("es_iot") else 0,
                str(row.get("fecha_registro") or row.get("fecha") or ""),
            ),
            reverse=True,
        )[: paginator.page_size]

    lotes_con_emisiones_count = actividades_qs.values("lote__id_lote").annotate(total=Sum("emisiones_kg_co2e")).filter(total__gt=0).count()

    def percentage(value):
        return (float(value or 0) / total_emisiones * 100) if total_emisiones else 0

    t1 = __import__("time").perf_counter()

    payload = paginator.get_paginated_response(rows).data
    payload["count"] = int(payload.get("count") or 0) + len(iot_rows)
    payload.update(
        {
            "empresa": {"id": empresa.empresa_id, "nombre": empresa.nombre},
            "emisiones_por_actividad": emisiones_por_actividad,
            "emisiones_por_unidad": emisiones_por_unidad,
            "kpis": {
                "emisiones_totales": total_emisiones,
                "actividad_critica": actividad_top.get("actividad") or "Sin datos",
                "categoria_critica": categoria_top.get("categoria") or "Sin datos",
                "unidad_critica": unidad_top.get("unidad_nombre") or "Sin datos",
                "lote_critico": lote_top.get("id_lote") or "Sin datos",
                "cantidad_actividades": actividades_count,
                "lecturas_iot_count": len(iot_rows),
                "emisiones_iot_24h": emisiones_iot,
                "cantidad_lotes_con_emisiones": lotes_con_emisiones_count,
                "promedio_emision_por_lote": (total_emisiones / lotes_con_emisiones_count) if lotes_con_emisiones_count else 0,
                "porcentaje_diesel": percentage(diesel_total),
                "porcentaje_top_actividad": percentage(actividad_top.get("emisiones") or 0),
                "actividades_sin_factor": actividades_sin_factor,
            },
        }
    )

    if debug:
        payload["_timings"] = {"total_seconds": t1 - t0}

    return Response(payload)


@api_view(["GET"])
def empresa_evidencias(request, empresa_id):
    empresa = Empresa.objects.filter(empresa_id=empresa_id).first()
    if not empresa:
        return Response({"error": "Empresa no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    queryset = Evidencia.objects.select_related(
        "empresa",
        "unidad_operativa",
        "lote",
        "emision",
    ).filter(empresa=empresa)

    tipo = (request.query_params.get("tipo") or "").strip()
    estado_f = (request.query_params.get("estado") or "").strip()
    estado_sistema = (request.query_params.get("estado_sistema") or "").strip()
    estado_revision = (request.query_params.get("estado_revision") or "").strip()
    alcance = (request.query_params.get("alcance") or "").strip()
    lote_id = (request.query_params.get("lote_id") or "").strip()
    unidad_id = (request.query_params.get("unidad_id") or "").strip()
    search = (request.query_params.get("search") or "").strip()

    if tipo:
        queryset = queryset.filter(tipo_documento=tipo)
    if estado_f:
        queryset = queryset.filter(Q(estado=estado_f) | Q(estado_sistema=estado_f) | Q(estado_revision=estado_f))
    if estado_sistema:
        queryset = queryset.filter(estado_sistema=estado_sistema)
    if estado_revision:
        queryset = queryset.filter(estado_revision=estado_revision)
    if alcance:
        queryset = queryset.filter(alcance=alcance)
    if lote_id:
        queryset = queryset.filter(lote__id_lote=lote_id)
    if unidad_id:
        queryset = queryset.filter(unidad_operativa__unidad_id=unidad_id)
    if search:
        queryset = queryset.filter(
            Q(nombre__icontains=search)
            | Q(observaciones__icontains=search)
            | Q(lote__id_lote__icontains=search)
            | Q(unidad_operativa__unidad_id__icontains=search)
            | Q(unidad_operativa__nombre__icontains=search)
        )

    serializer = EvidenciaSerializer(queryset.order_by("-created_at"), many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def crear_evidencia_empresa(request, empresa_id):
    empresa = Empresa.objects.filter(empresa_id=empresa_id).first()
    if not empresa:
        return Response({"error": "Empresa no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    lote_id = (request.data.get("lote_id") or "").strip()
    unidad_id = (request.data.get("unidad_id") or "").strip()
    emision_id = request.data.get("emision_id")
    alcance = (request.data.get("alcance") or Evidencia.Alcance.EMPRESA).strip()
    if alcance not in {choice[0] for choice in Evidencia.Alcance.choices}:
        return Response({"error": "El alcance indicado no es valido."}, status=status.HTTP_400_BAD_REQUEST)

    lote = None
    unidad = None
    emision = None

    estado_sistema = Evidencia.EstadoSistema.SIN_VINCULO
    estado_revision = Evidencia.EstadoRevision.SIN_REVISION

    # Evaluate according to alcance rules
    if alcance == Evidencia.Alcance.LOTE:
        if not lote_id:
            return Response({"error": "Debes indicar un ID de lote para alcance 'lote'"}, status=status.HTTP_400_BAD_REQUEST)
        lote = Lote.objects.filter(Q(empresa=empresa) | Q(unidad_operativa__empresa=empresa), id_lote=lote_id).first()
        if not lote:
            return Response(
                {"error": "El lote no existe dentro de la empresa activa"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if lote.unidad_operativa_id:
            unidad = lote.unidad_operativa
        estado_sistema = Evidencia.EstadoSistema.VINCULADA
    elif alcance == Evidencia.Alcance.UNIDAD:
        if not unidad_id:
            return Response({"error": "Debes indicar un ID de unidad para alcance 'unidad'"}, status=status.HTTP_400_BAD_REQUEST)
        unidad = UnidadOperativa.objects.filter(empresa=empresa, unidad_id=unidad_id).first()
        if not unidad:
            return Response(
                {"error": "La unidad no existe dentro de la empresa activa"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        estado_sistema = Evidencia.EstadoSistema.VINCULADA
    elif alcance == Evidencia.Alcance.EMISION:
        if emision_id in (None, ""):
            return Response({"error": "Debes indicar una ID de emisión para alcance 'emision'"}, status=status.HTTP_400_BAD_REQUEST)
        emision = EmisionLote.objects.filter(
            Q(empresa=empresa) | Q(lote__empresa=empresa) | Q(unidad_operativa__empresa=empresa),
            id=emision_id,
        ).first()
        if not emision:
            return Response({"error": "La emisión no existe dentro de la empresa activa"}, status=status.HTTP_400_BAD_REQUEST)
        # inferir lote/unidad desde la emisión si están presentes
        if emision.lote_id:
            lote = emision.lote
            if lote.unidad_operativa_id:
                unidad = lote.unidad_operativa
        elif emision.unidad_operativa_id:
            unidad = emision.unidad_operativa
        estado_sistema = Evidencia.EstadoSistema.VINCULADA
    elif alcance == Evidencia.Alcance.TRANSPORTE:
        # lote_id opcional; si se provee se valida; si no, se deja vinculada a empresa
        if lote_id:
            lote = Lote.objects.filter(Q(empresa=empresa) | Q(unidad_operativa__empresa=empresa), id_lote=lote_id).first()
            if not lote:
                return Response({"error": "El lote no existe dentro de la empresa activa"}, status=status.HTTP_400_BAD_REQUEST)
            if lote.unidad_operativa_id:
                unidad = lote.unidad_operativa
            estado_sistema = Evidencia.EstadoSistema.VINCULADA
        else:
            estado_sistema = Evidencia.EstadoSistema.CORPORATIVA
    else:
        # alcance = empresa (por defecto)
        estado_sistema = Evidencia.EstadoSistema.CORPORATIVA

    # note: validation and inference done above per alcance

    payload = {
        "nombre": request.data.get("nombre"),
        "tipo_documento": request.data.get("tipo_documento"),
        "archivo": request.data.get("archivo"),
        "fecha_documento": request.data.get("fecha_documento") or None,
        "observaciones": request.data.get("observaciones") or "",
        "unidad_operativa": unidad.id if unidad else None,
        "lote": lote.id if lote else None,
        "emision": emision.id if emision else None,
        "alcance": alcance,
        "estado": Evidencia.Estado.PENDIENTE,
    }

    serializer = EvidenciaSerializer(data=payload, context={"request": request})
    if serializer.is_valid():
        serializer.save(
            empresa=empresa,
            estado_sistema=estado_sistema,
            estado_revision=estado_revision,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def evidencias_kpis_empresa(request, empresa_id):
    empresa = Empresa.objects.filter(empresa_id=empresa_id).first()
    if not empresa:
        return Response({"error": "Empresa no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    evidencias = Evidencia.objects.filter(empresa=empresa)
    total_evidencias = evidencias.count()
    lotes_empresa = Lote.objects.filter(Q(empresa=empresa) | Q(unidad_operativa__empresa=empresa))
    total_lotes = lotes_empresa.count()
    lotes_con_evidencia = evidencias.exclude(lote__isnull=True).values("lote").distinct().count()
    lotes_sin_evidencia = max(total_lotes - lotes_con_evidencia, 0)

    cobertura_documental = (lotes_con_evidencia / total_lotes * 100) if total_lotes else 0

    score_respaldo = cobertura_documental

    por_estado_sistema = {
        item["estado_sistema"]: item["total"]
        for item in evidencias.values("estado_sistema").annotate(total=Count("id")).order_by("-total")
    }
    por_revision = {
        item["estado_revision"]: item["total"]
        for item in evidencias.values("estado_revision").annotate(total=Count("id")).order_by("-total")
    }
    por_alcance = {
        item["alcance"]: item["total"]
        for item in evidencias.values("alcance").annotate(total=Count("id")).order_by("-total")
    }
    por_tipo = {
        item["tipo_documento"]: item["total"]
        for item in evidencias.values("tipo_documento").annotate(total=Count("id")).order_by("-total")
    }

    return Response(
        {
            "total_evidencias": total_evidencias,
            "total_lotes": total_lotes,
            "lotes_con_evidencia": lotes_con_evidencia,
            "lotes_sin_evidencia": lotes_sin_evidencia,
            "cobertura_documental": round(cobertura_documental, 2),
            "score_respaldo": round(score_respaldo, 2),
            "corporativas": por_estado_sistema.get(Evidencia.EstadoSistema.CORPORATIVA, 0),
            "vinculadas": por_estado_sistema.get(Evidencia.EstadoSistema.VINCULADA, 0),
            "sin_vinculo": por_estado_sistema.get(Evidencia.EstadoSistema.SIN_VINCULO, 0),
            "sin_revisar": por_revision.get(Evidencia.EstadoRevision.SIN_REVISION, 0),
            "por_estado_sistema": por_estado_sistema,
            "por_revision": por_revision,
            "por_alcance": por_alcance,
            "por_tipo": por_tipo,
        }
    )


@api_view(["GET"])
def empresa_reportes(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    return Response(
        {
            "empresa_id": empresa.empresa_id,
            "empresa_nombre": empresa.nombre,
            "dashboard": build_company_dashboard_response(empresa),
            "estado": build_company_state_response(empresa),
        }
    )


@api_view(["GET", "POST"])
def unidades_operativas(request):
    if request.method == "GET":
        queryset = UnidadOperativa.objects.select_related("empresa").all()
        empresa_id = request.query_params.get("empresa_id")
        if empresa_id:
            queryset = queryset.filter(empresa__empresa_id=empresa_id)
        serializer = UnidadOperativaSerializer(queryset, many=True)
        return Response(serializer.data)

    serializer = UnidadOperativaSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
def lotes(request):
    if request.method == "GET":
        queryset = Lote.objects.select_related(
            "empresa",
            "unidad_operativa",
            "unidad_operativa__empresa",
        ).prefetch_related("actividades", "documentos", "transportes")
        empresa_id = request.query_params.get("empresa_id")
        if empresa_id:
            queryset = queryset.filter(Q(empresa__empresa_id=empresa_id) | Q(unidad_operativa__empresa__empresa_id=empresa_id))
        serializer = LoteSerializer(queryset, many=True)
        return Response(serializer.data)

    serializer = LoteSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def especies_madera(request):
    serializer = EspecieMaderaSerializer(EspecieMadera.objects.all(), many=True)
    return Response(serializer.data)


@api_view(["GET"])
def factores_emision(request):
    serializer = FactorEmisionSerializer(FactorEmision.objects.all(), many=True)
    return Response(serializer.data)


@api_view(["GET"])
def factores_catalogo(request):
    q = (request.query_params.get("q") or "").strip()
    categoria = (request.query_params.get("categoria") or "").strip()
    factores = FactorEmision.objects.all()

    if categoria:
        factores = factores.filter(categoria__iexact=categoria)

    if q:
        q_key = normalize_activity_key(q)
        factores = factores.filter(
            Q(actividad__icontains=q)
            | Q(actividad_key__icontains=q_key)
            | Q(unidad__icontains=q)
            | Q(fuente__icontains=q)
        )

    catalogo = {category: [] for category in FACTOR_CATEGORIES}
    for factor in factores:
        catalogo.setdefault(factor.categoria, []).append(
            FactorEmisionSerializer(factor).data
        )

    return Response(catalogo)


@api_view(["GET"])
def lote_detail(request, id_lote):
    lote = get_object_or_404(
        Lote.objects.select_related(
            "empresa",
            "unidad_operativa",
            "unidad_operativa__empresa",
        ).prefetch_related("actividades", "documentos", "transportes"),
        id_lote=id_lote,
    )
    serializer = LoteSerializer(lote)
    return Response(serializer.data)


@api_view(["GET"])
def lote_carbono(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    carbono = calcular_carbono_almacenado(lote)
    balance = calcular_balance_lote(lote)
    pasaporte = calcular_pasaporte_lote(lote)

    return Response(
        {
            **carbono,
            **balance,
            **pasaporte,
        }
    )


@api_view(["GET"])
def lote_pasaporte(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    return Response(calcular_pasaporte_lote(lote))


@api_view(["GET"])
def lote_confianza(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    return Response(calcular_confianza_lote(lote))


def build_public_verification_url(request, id_lote):
    origin = request.headers.get("Origin", "")
    frontend_base_url = settings.PUBLIC_FRONTEND_URL or origin

    if frontend_base_url:
        return f"{frontend_base_url.rstrip('/')}/verificar/{id_lote}"

    return request.build_absolute_uri(f"/verificar/{id_lote}")


@api_view(["GET"])
def lote_certificado(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    verification_url = build_public_verification_url(request, lote.id_lote)
    pdf_bytes = generar_certificado_lote_pdf(lote, verification_url)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="pasaporte-verde-{lote.id_lote}.pdf"'
    )
    return response


@api_view(["GET"])
def verificar_lote(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    return Response(generar_resumen_verificacion(lote))


@api_view(["GET"])
def historial_lote(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    paginator = PageNumberPagination()
    try:
        paginator.page_size = int(request.query_params.get("page_size", 20))
    except Exception:
        paginator.page_size = 20

    qs = HistorialCambioLote.objects.filter(lote=lote).order_by("-created_at")
    page = paginator.paginate_queryset(qs, request)

    def build_change_items(entry):
        changes = []
        keys = list((entry.normalized_payload or {}).keys())

        for key in keys:
            prev = (
                HistorialCambioLote.objects.filter(lote=entry.lote, created_at__lt=entry.created_at)
                .order_by("-created_at")
                .first()
            )
            prev_val = None
            if prev and prev.normalized_payload:
                prev_val = prev.normalized_payload.get(key)

            new_val = (entry.normalized_payload or {}).get(key)
            changes.append({"field": key, "previous": prev_val, "new": new_val})

        return changes

    results = []
    for entry in page:
        results.append(
            {
                "extraccion_id": entry.extraccion_id,
                "id": entry.pk,
                "tipo": entry.tipo,
                "fuente": entry.fuente,
                "usuario": entry.usuario,
                "changes": build_change_items(entry),
                "raw_payload": entry.raw_payload,
                "normalized_payload": entry.normalized_payload,
                "metadata": entry.metadata,
                "created_at": entry.created_at,
            }
        )

    return paginator.get_paginated_response(results)


@api_view(["POST"])
def calcular_distancia_ruta(request):
    origen = (request.data.get("origen") or "").strip()
    destino = (request.data.get("destino") or "").strip()
    origen_coords = request.data.get("origen_coords")
    destino_coords = request.data.get("destino_coords")

    if not origen or not destino:
        return Response(
            {"error": "Debes indicar origen y destino"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        return Response(route_distance_km(origen, destino, origen_coords, destino_coords))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def documento_extraer_texto(request):
    archivo = request.FILES.get("file")

    if not archivo:
        texto = (request.data.get("texto") or "").strip()

        if not texto:
            return Response(
                {"error": "Debes enviar un archivo o texto"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"texto_extraido": texto, "formato": "texto", "requiere_ocr": False}
        )

    return Response(extraer_texto_archivo(archivo))


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def documento_extraer_json(request):
    archivo = request.FILES.get("file")
    texto = (request.data.get("texto") or "").strip()

    if archivo:
        texto = extraer_texto_archivo(archivo)["texto_extraido"]

    if not texto:
        return Response(
            {"error": "Debes enviar un archivo o texto"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(extraer_documento_estructurado(texto))


@api_view(["POST"])
def documento_extraer_texto_por_id(request, documento_id):
    documento = get_object_or_404(DocumentoLote, pk=documento_id)
    return Response(extraer_texto_archivo(documento.archivo))


@api_view(["POST"])
def documento_extraer_json_por_id(request, documento_id):
    documento = get_object_or_404(DocumentoLote, pk=documento_id)
    texto = extraer_texto_archivo(documento.archivo)["texto_extraido"]
    return Response(extraer_documento_estructurado(texto))


@api_view(["GET"])
def integracion_lote(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    return Response(construir_payload_lote_bim(lote))


@api_view(["GET"])
def integracion_lote_json(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    payload = construir_payload_lote_bim(lote)
    response = HttpResponse(
        json.dumps(payload, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="{lote.id_lote}-bim.json"'
    return response


@api_view(["GET"])
def integracion_lote_csv(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    payload = construir_payload_lote_bim(lote)
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "lote",
            "producto",
            "volumen_m3",
            "emisiones_kgco2e",
            "co2_almacenado",
            "balance_neto",
            "pasaporte",
            "estado_confianza",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "lote": payload["lote"],
            "producto": payload["producto"],
            "volumen_m3": payload["volumen_m3"],
            "emisiones_kgco2e": payload["emisiones_kgco2e"],
            "co2_almacenado": payload["co2_almacenado"],
            "balance_neto": payload["balance_neto"],
            "pasaporte": payload["pasaporte"],
            "estado_confianza": payload["estado_confianza"],
        }
    )
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{lote.id_lote}-bim.csv"'
    return response


@api_view(["GET"])
def integracion_lote_ficha_tecnica(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    payload = construir_payload_lote_bim(lote)
    return Response(
        {
            "lote": payload["lote"],
            "producto": payload["producto"],
            "ficha_tecnica": payload["ficha_tecnica"],
            "bim": payload["bim"],
        }
    )


@api_view(["POST"])
def lote_actividad(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)
    serializer = EmisionLoteSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(lote=lote)
        lote.refresh_from_db()
        return Response(LoteSerializer(lote).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def lote_documentos(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)

    if request.method == "GET":
        serializer = DocumentoLoteSerializer(
            lote.documentos.all(),
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    serializer = DocumentoLoteSerializer(
        data=request.data,
        context={"request": request},
    )

    if serializer.is_valid():
        documento = serializer.save(lote=lote)
        return Response(
            DocumentoLoteSerializer(
                documento,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
def lote_transportes(request, id_lote):
    lote = get_object_or_404(Lote, id_lote=id_lote)

    if request.method == "GET":
        serializer = TransporteLoteSerializer(lote.transportes.all(), many=True)
        return Response(serializer.data)

    serializer = TransporteLoteSerializer(data=request.data)

    if serializer.is_valid():
        transporte = serializer.save(lote=lote)
        return Response(
            TransporteLoteSerializer(transporte).data,
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def documento_ocr(request, documento_id):
    documento = get_object_or_404(DocumentoLote, pk=documento_id)
    resultado = generar_extraccion_documento(documento)
    extraccion = ExtraccionDocumento.objects.create(
        documento=documento,
        texto_extraido=resultado["texto_extraido"],
        datos_sugeridos=resultado["datos_sugeridos"],
    )

    # Registrar en historial como Dato extraído (fuente: ia/heuristica)
    HistorialCambioLote.objects.create(
        lote=documento.lote,
        tipo=HistorialCambioLote.TipoCambio.EXTRAIDO,
        fuente=resultado.get("fuente", "ia"),
        documento=documento,
        extraccion=extraccion,
        raw_payload=resultado.get("datos_sugeridos") or {},
        normalized_payload={},
        metadata={"texto_len": len(resultado.get("texto_extraido", ""))},
    )

    return Response(
        ExtraccionDocumentoSerializer(extraccion).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def extraccion_validar(request, extraccion_id):
    extraccion = get_object_or_404(ExtraccionDocumento, pk=extraccion_id)
    datos_validados = request.data.get("datos_validados") or request.data
    aplicar_calculo = request.data.get("aplicar_calculo", True)
    resultado = ValidadorDatos.validar_extraccion(
        extraccion, datos_validados, usuario=request.user.username if request.user and request.user.is_authenticated else None, aplicar_calculo=aplicar_calculo
    )

    return Response(
        {
            "extraccion": ExtraccionDocumentoSerializer(extraccion).data,
            "actividades_creadas": resultado.get("actividades_creadas", 0),
            "lote": LoteSerializer(extraccion.documento.lote).data,
            "carbono": resultado.get("carbono"),
            "balance": resultado.get("balance"),
            "pasaporte": resultado.get("pasaporte"),
        }
    )


@api_view(["POST"])
def extraccion_rechazar(request, extraccion_id):
    extraccion = get_object_or_404(ExtraccionDocumento, pk=extraccion_id)
    extraccion.estado_revision = ExtraccionDocumento.EstadoRevision.RECHAZADO
    extraccion.save(update_fields=["estado_revision", "updated_at"])

    return Response(ExtraccionDocumentoSerializer(extraccion).data)


def safe_error_response(exc, user_message="No se pudo procesar la solicitud", status=400):
    logger.exception("API error: %s", exc)
    return Response({"error": user_message}, status=status)


def build_empty_dashboard_response(source="internal"):
    return {
        "source": source,
        "total_emisiones": 0,
        "cantidad_registros": 0,
        "empresas": 0,
        "actividades": 0,
        "empresa_critica": "Sin datos",
        "unidad_critica": "Sin datos",
        "tipo_unidad_critica": "Sin datos",
        "actividad_critica": "Sin datos",
        "categoria_critica": "Sin datos",
        "emisiones_por_empresa": {},
        "emisiones_por_unidad_operativa": {},
        "emisiones_por_tipo_unidad": {},
        "emisiones_por_actividad": {},
        "emisiones_por_categoria": {},
        "ranking_lotes": [],
        "diesel_presente": False,
        "score_riesgo": 0,
        "potencial_reduccion": 0,
        "datos": [],
        "system_status": build_system_status(),
    }


def build_internal_dashboard_response():
    actividades = EmisionLote.objects.select_related(
        "empresa",
        "unidad_operativa",
        "lote",
        "lote__empresa",
        "lote__unidad_operativa",
    ).all()

    if not actividades.exists():
        return build_empty_dashboard_response()

    rows = []
    emisiones_por_empresa = {}
    emisiones_por_unidad = {}
    emisiones_por_tipo_unidad = {}
    emisiones_por_actividad = {}
    emisiones_por_categoria = {}
    emisiones_por_lote = {}

    for actividad in actividades:
        lote = actividad.lote
        emisiones = float(actividad.emisiones_kg_co2e or 0)
        empresa_obj = actividad.empresa or getattr(lote, "empresa", None)
        unidad_obj = actividad.unidad_operativa or getattr(lote, "unidad_operativa", None)
        empresa = (
            empresa_obj.nombre
            if empresa_obj
            else lote.empresa_aserradero
            if lote
            else "Sin empresa"
        )
        unidad = unidad_obj.nombre if unidad_obj else "Sin unidad"
        tipo_unidad = unidad_obj.tipo if unidad_obj else "Sin tipo"
        actividad_nombre = actividad.actividad
        categoria = actividad.categoria or "Otros"

        rows.append(
            {
                "empresa": empresa,
                "empresa_id": empresa_obj.empresa_id if empresa_obj else "",
                "unidad_operativa": unidad,
                "unidad_id": unidad_obj.unidad_id if unidad_obj else "",
                "tipo_unidad": tipo_unidad,
                "actividad": actividad_nombre,
                "actividad_key": actividad.actividad_key,
                "categoria": categoria,
                "cantidad": float(actividad.cantidad or 0),
                "unidad": actividad.unidad,
                "factor_emision": float(actividad.factor_emision or 0),
                "emisiones": emisiones,
                "fecha": (
                    actividad.fecha.isoformat()
                    if actividad.fecha
                    else actividad.created_at.date().isoformat()
                ),
                "id_lote": lote.id_lote if lote else "",
                "tipo_asignacion": actividad.tipo_asignacion,
            }
        )
        emisiones_por_empresa[empresa] = emisiones_por_empresa.get(empresa, 0) + emisiones
        emisiones_por_unidad[unidad] = emisiones_por_unidad.get(unidad, 0) + emisiones
        emisiones_por_tipo_unidad[tipo_unidad] = (
            emisiones_por_tipo_unidad.get(tipo_unidad, 0) + emisiones
        )
        emisiones_por_actividad[actividad_nombre] = (
            emisiones_por_actividad.get(actividad_nombre, 0) + emisiones
        )
        emisiones_por_categoria[categoria] = (
            emisiones_por_categoria.get(categoria, 0) + emisiones
        )
        if lote:
            emisiones_por_lote[lote.id_lote] = emisiones_por_lote.get(lote.id_lote, 0) + emisiones

    emisiones_por_empresa = dict(
        sorted(emisiones_por_empresa.items(), key=lambda item: item[1], reverse=True)
    )
    emisiones_por_actividad = dict(
        sorted(emisiones_por_actividad.items(), key=lambda item: item[1], reverse=True)
    )
    emisiones_por_unidad = dict(
        sorted(emisiones_por_unidad.items(), key=lambda item: item[1], reverse=True)
    )
    emisiones_por_tipo_unidad = dict(
        sorted(emisiones_por_tipo_unidad.items(), key=lambda item: item[1], reverse=True)
    )
    emisiones_por_categoria = dict(
        sorted(emisiones_por_categoria.items(), key=lambda item: item[1], reverse=True)
    )
    ranking_lotes = [
        {"id_lote": id_lote, "emisiones": emisiones}
        for id_lote, emisiones in sorted(
            emisiones_por_lote.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]
    total_emisiones = sum(row["emisiones"] for row in rows)
    summary = {
        "source": "internal",
        "total_emisiones": total_emisiones,
        "cantidad_registros": len(rows),
        "empresas": len(emisiones_por_empresa),
        "actividades": len(emisiones_por_actividad),
        "empresa_critica": next(iter(emisiones_por_empresa), "Sin datos"),
        "unidad_critica": next(iter(emisiones_por_unidad), "Sin datos"),
        "tipo_unidad_critica": next(iter(emisiones_por_tipo_unidad), "Sin datos"),
        "actividad_critica": next(iter(emisiones_por_actividad), "Sin datos"),
        "categoria_critica": next(iter(emisiones_por_categoria), "Sin datos"),
        "emisiones_por_empresa": emisiones_por_empresa,
        "emisiones_por_unidad_operativa": emisiones_por_unidad,
        "emisiones_por_tipo_unidad": emisiones_por_tipo_unidad,
        "emisiones_por_actividad": emisiones_por_actividad,
        "emisiones_por_categoria": emisiones_por_categoria,
        "ranking_lotes": ranking_lotes,
        "diesel_presente": any(is_diesel_activity(row) for row in rows),
        "potencial_reduccion": 0,
        "datos": rows,
        "system_status": build_system_status(),
    }
    risk = calculate_risk_profile(summary)
    summary["score_riesgo"] = risk["score"]
    summary["perfil_riesgo"] = risk

    return summary


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_factores_preview(request):
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se recibio ningun archivo"}, status=400)

    try:
        return Response(ImportadorFactores.previsualizar(archivo))
    except ValueError as exc:
        return safe_error_response(exc, user_message=str(exc), status=400)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo previsualizar el importador de factores",
            status=400,
        )


@api_view(["POST"])
def import_factores_confirm(request):
    try:
        batch_id = request.data.get("batch_id")
        rows = request.data.get("rows")
        summary = ImportadorFactores.confirmar(rows=rows, batch_id=batch_id)
        return Response(summary)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudieron guardar los factores",
            status=400,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_unidades_preview(request):
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se recibio ningun archivo"}, status=400)

    try:
        return Response(ImportadorUnidadesOperativas.previsualizar(archivo))
    except ValueError as exc:
        return safe_error_response(exc, user_message=str(exc), status=400)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo previsualizar el importador de unidades",
            status=400,
        )


@api_view(["POST"])
def import_unidades_confirm(request):
    try:
        batch_id = request.data.get("batch_id")
        rows = request.data.get("rows")
        summary = ImportadorUnidadesOperativas.confirmar(rows=rows, batch_id=batch_id)
        return Response(summary)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudieron guardar las unidades operativas",
            status=400,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_empresas_preview(request):
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se recibio ningun archivo"}, status=400)

    try:
        return Response(ImportadorEmpresas.previsualizar(archivo))
    except ValueError as exc:
        return safe_error_response(exc, user_message=str(exc), status=400)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo previsualizar el importador de empresas",
            status=400,
        )


@api_view(["POST"])
def import_empresas_confirm(request):
    try:
        batch_id = request.data.get("batch_id")
        rows = request.data.get("rows")
        summary = ImportadorEmpresas.confirmar(rows=rows, batch_id=batch_id)
        return Response(summary)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudieron guardar las empresas",
            status=400,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_lotes_preview(request):
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se recibio ningun archivo"}, status=400)

    try:
        return Response(ImportadorLotes.previsualizar(archivo))
    except ValueError as exc:
        return safe_error_response(exc, user_message=str(exc), status=400)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo previsualizar el importador de lotes",
            status=400,
        )


@api_view(["POST"])
def import_lotes_confirm(request):
    try:
        batch_id = request.data.get("batch_id")
        rows = request.data.get("rows")
        summary = ImportadorLotes.confirmar(rows=rows, batch_id=batch_id)
        return Response(summary)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudieron guardar los lotes",
            status=400,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_actividades_preview(request):
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se recibio ningun archivo"}, status=400)

    try:
        return Response(ImportadorActividadesLote.previsualizar(archivo))
    except ValueError as exc:
        return safe_error_response(exc, user_message=str(exc), status=400)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo previsualizar el importador de actividades",
            status=400,
        )


@api_view(["POST"])
def import_actividades_confirm(request):
    try:
        batch_id = request.data.get("batch_id")
        rows = request.data.get("rows")
        summary = ImportadorActividadesLote.confirmar(rows=rows, batch_id=batch_id)
        return Response(summary)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudieron guardar las actividades",
            status=400,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def empresa_import_unidades_preview(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se recibio ningun archivo"}, status=400)

    try:
        return Response(ImportadorUnidadesOperativas.previsualizar(archivo, empresa_activa=empresa))
    except ValueError as exc:
        return safe_error_response(exc, user_message=str(exc), status=400)


@api_view(["POST"])
def empresa_import_unidades_confirm(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    try:
        batch_id = request.data.get("batch_id")
        rows = request.data.get("rows")
        summary = ImportadorUnidadesOperativas.confirmar(
            rows=rows,
            batch_id=batch_id,
            empresa_activa=empresa,
        )
        return Response(summary)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudieron guardar las unidades operativas",
            status=400,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def empresa_import_lotes_preview(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se recibio ningun archivo"}, status=400)

    try:
        return Response(ImportadorLotes.previsualizar(archivo, empresa_activa=empresa))
    except ValueError as exc:
        return safe_error_response(exc, user_message=str(exc), status=400)


@api_view(["POST"])
def empresa_import_lotes_confirm(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    try:
        batch_id = request.data.get("batch_id")
        rows = request.data.get("rows")
        summary = ImportadorLotes.confirmar(
            rows=rows,
            batch_id=batch_id,
            empresa_activa=empresa,
        )
        return Response(summary)
    except Exception as exc:
        return safe_error_response(exc, user_message="No se pudieron guardar los lotes", status=400)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def empresa_import_actividades_preview(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se recibio ningun archivo"}, status=400)

    try:
        return Response(ImportadorActividadesLote.previsualizar(archivo, empresa_activa=empresa))
    except ValueError as exc:
        return safe_error_response(exc, user_message=str(exc), status=400)


@api_view(["POST"])
def empresa_import_actividades_confirm(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    try:
        batch_id = request.data.get("batch_id")
        rows = request.data.get("rows")
        summary = ImportadorActividadesLote.confirmar(
            rows=rows,
            batch_id=batch_id,
            empresa_activa=empresa,
        )
        return Response(summary)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudieron guardar las actividades",
            status=400,
        )


@api_view(["GET"])
def download_import_template(request):
    """Descarga una plantilla XLSX para importación completa de empresa."""
    try:
        template_buffer = generate_complete_import_template()
        response = HttpResponse(
            template_buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename="plantilla_importacion_empresa.xlsx"'
        return response
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo generar la plantilla de importación",
            status=400,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_empresa_completa_preview(request):
    """Preview de importación de empresa completa con todas las hojas (empresa, unidades, lotes, actividades, factores)."""
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se recibio ningun archivo"}, status=400)

    try:
        return Response(ImportadorEmpresaCompleta.previsualizar(archivo))
    except ValueError as exc:
        return safe_error_response(exc, user_message=str(exc), status=400)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo previsualizar el archivo de empresa completa",
            status=400,
        )


@api_view(["POST"])
def import_empresa_completa_confirm(request):
    """Confirma la importación completa de empresa."""
    try:
        batch_id = request.data.get("batch_id")
        if not batch_id:
            raise ValueError("batch_id es requerido")
        
        resultado = ImportadorEmpresaCompleta.confirmar(batch_id)
        return Response(resultado)
    except ValueError as exc:
        return safe_error_response(exc, user_message=str(exc), status=400)
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo confirmar la importación de empresa completa",
            status=400,
        )


@api_view(["GET"])
def dashboard_data(request):
    try:
        return Response(build_internal_dashboard_response())
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo cargar el dataset base",
            status=400,
        )


@api_view(["GET"])
def sistema_estado(request):
    return Response(build_system_state_response())


@api_view(["POST"])
def ai_advisor(request):
    try:
        if generar_analisis_ia:
            analisis = generar_analisis_ia(request.data)
            fuente = "openai"
        else:
            raise RuntimeError("OpenAI no disponible")
    except Exception:
        analisis = generar_analisis_local(request.data)
        fuente = "carbono_zero_engine"

    return Response({"analisis": analisis, "fuente": fuente})


@api_view(["POST"])
def simulate_dashboard_data(request):
    rows = request.data.get("rows") or []

    if not rows:
        return Response({"error": "Debes enviar filas para simular"}, status=400)

    try:
        simulated_rows = simulate_rows(
            rows,
            diesel_reduction=request.data.get("diesel_reduction", 0),
            electricity_increase=request.data.get("electricity_increase", 0),
            selected_company=request.data.get("selected_company", "Todas"),
        )
        return Response(summarize_rows(simulated_rows))
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo ejecutar la simulacion",
            status=400,
        )


@api_view(["POST"])
def optimize_dashboard_data(request):
    rows = request.data.get("rows") or []

    if not rows:
        return Response({"error": "Debes enviar filas para optimizar"}, status=400)

    try:
        return Response(optimize_rows(rows))
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo optimizar el escenario",
            status=400,
        )


@api_view(["GET"])
def empresa_decision_optimo(request, empresa_id):
    """Construct rows server-side for a company and run the optimizer (on-demand).
    This endpoint is heavy and should be called only when user requests automatic optimization.
    """
    empresa = get_empresa_or_404(empresa_id)
    debug = (request.GET.get("debug") or "").lower() in ("1", "true", "yes")

    t0 = __import__("time").perf_counter()
    actividades_qs = EmisionLote.objects.select_related(
        "empresa",
        "unidad_operativa",
        "lote",
    ).filter(Q(empresa=empresa) | Q(lote__empresa=empresa) | Q(unidad_operativa__empresa=empresa))

    rows = []
    for actividad in actividades_qs:
        lote = actividad.lote
        unidad_obj = actividad.unidad_operativa or getattr(lote, "unidad_operativa", None)
        empresa_obj = actividad.empresa or getattr(lote, "empresa", None) or empresa
        emisiones = float(actividad.emisiones_kg_co2e or 0)
        rows.append(
            {
                "empresa": empresa_obj.nombre if empresa_obj else empresa.nombre,
                "empresa_id": empresa_obj.empresa_id if empresa_obj else empresa.empresa_id,
                "unidad_operativa": unidad_obj.nombre if unidad_obj else "Sin unidad",
                "unidad_id": unidad_obj.unidad_id if unidad_obj else "",
                "actividad": actividad.actividad,
                "actividad_key": actividad.actividad_key,
                "categoria": actividad.categoria or "Otros",
                "cantidad": float(actividad.cantidad or 0),
                "unidad": actividad.unidad,
                "factor_emision": float(actividad.factor_emision or 0),
                "emisiones": emisiones,
                "fecha": (
                    actividad.fecha.isoformat() if actividad.fecha else actividad.created_at.date().isoformat()
                ),
                "id_lote": lote.id_lote if lote else "",
                "tipo_asignacion": actividad.tipo_asignacion,
            }
        )

    t1 = __import__("time").perf_counter()

    # Run optimizer (heavy) and measure
    t_opt0 = __import__("time").perf_counter()
    optimized = optimize_rows(rows)
    t_opt1 = __import__("time").perf_counter()

    result = {"optimized": optimized}
    if debug:
        result["_timings"] = {
            "rows_build_seconds": t1 - t0,
            "optimize_seconds": t_opt1 - t_opt0,
            "total_seconds": (t_opt1 - t0),
        }

    return Response(result)


@api_view(["POST"])
def risk_score_data(request):
    summary = request.data.get("summary") or request.data
    optimized_scenario = request.data.get("optimized_scenario")

    try:
        return Response(calculate_risk_profile(summary, optimized_scenario))
    except Exception as exc:
        return safe_error_response(
            exc,
            user_message="No se pudo calcular el perfil de riesgo",
            status=400,
        )

@api_view(["GET"])
def reporte_emisiones_tiempo(request, empresa_id):
    """
    Reporte temporal de emisiones por empresa.
    Agrupa emisiones por día, mes o año según query param.
    """

    agrupacion = request.GET.get("agrupacion", "mes")
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    unidad_id = request.GET.get("unidad_id")
    categoria = request.GET.get("categoria")
    actividad_query = request.GET.get("actividad")
    empresa = get_object_or_404(Empresa, empresa_id=empresa_id)

    # Ajusta estos nombres si tu modelo se llama distinto
    actividades = EmisionLote.objects.filter(
        Q(lote__empresa__empresa_id=empresa_id)
        | Q(unidad_operativa__empresa__empresa_id=empresa_id)
        | Q(empresa__empresa_id=empresa_id)
    ).select_related("lote", "unidad_operativa", "empresa")

    if fecha_inicio:
        actividades = actividades.filter(fecha__gte=fecha_inicio)

    if fecha_fin:
        actividades = actividades.filter(fecha__lte=fecha_fin)

    if unidad_id:
        actividades = actividades.filter(unidad_operativa__unidad_id=unidad_id)

    if categoria:
        actividades = actividades.filter(categoria__iexact=categoria)

    if actividad_query:
        actividades = actividades.filter(actividad__icontains=actividad_query)

    # Usar agregaciones en BD en lugar de iterar todo en memoria
    # Emisiones totales
    total_agg = actividades.aggregate(total=Sum("emisiones_kg_co2e"))
    emisiones_totales = float(total_agg.get("total") or 0)

    unidad_nombre_iot = None
    if unidad_id:
        unidad_filter = Q(unidad_id=unidad_id)
        if str(unidad_id).isdigit():
            unidad_filter |= Q(id=int(unidad_id))
        unidad_obj = UnidadOperativa.objects.filter(unidad_filter, empresa=empresa).first()
        unidad_nombre_iot = unidad_obj.nombre if unidad_obj else "__sin_unidad_iot__"

    iot_rows = build_iot_analytics_rows(
        empresa,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        unidad_nombre=unidad_nombre_iot,
    )

    if categoria:
        categoria_normalizada = str(categoria).strip().lower()
        iot_rows = [
            row
            for row in iot_rows
            if str(row.get("categoria") or "").strip().lower() == categoria_normalizada
        ]

    if actividad_query:
        actividad_normalizada = str(actividad_query).strip().lower()
        iot_rows = [
            row
            for row in iot_rows
            if actividad_normalizada in str(row.get("actividad") or "").strip().lower()
        ]

    emisiones_iot = sum(float(row.get("emisiones") or 0) for row in iot_rows)
    emisiones_totales += emisiones_iot

    # Serie temporal: agrupar por día/mes/año usando funciones de truncado
    if agrupacion == "dia":
        trunc_fn = TruncDay
        label_fmt = lambda d: d.strftime("%d-%m-%Y")
        periodo_key_fmt = lambda d: d.strftime("%Y-%m-%d")
    elif agrupacion == "anio":
        trunc_fn = TruncYear
        label_fmt = lambda d: d.strftime("%Y")
        periodo_key_fmt = lambda d: d.strftime("%Y")
    else:
        trunc_fn = TruncMonth
        label_fmt = lambda d: d.strftime("%b %Y")
        periodo_key_fmt = lambda d: d.strftime("%Y-%m")

    serie_qs = (
        actividades.annotate(periodo=trunc_fn("fecha"))
        .values("periodo")
        .annotate(emisiones=Sum("emisiones_kg_co2e"), actividades=Count("id"), lotes=Count("lote__id_lote", distinct=True))
        .order_by("periodo")
    )

    serie_temporal = []
    for item in serie_qs:
        periodo_dt = item.get("periodo")
        serie_temporal.append({
            "periodo": periodo_key_fmt(periodo_dt),
            "label": label_fmt(periodo_dt),
            "emisiones": round(float(item.get("emisiones") or 0), 2),
            "actividades": int(item.get("actividades") or 0),
            "lotes": int(item.get("lotes") or 0),
        })

    serie_por_periodo = {item["periodo"]: item for item in serie_temporal}
    for row in iot_rows:
        row_date = datetime.fromisoformat(row["fecha"])
        if agrupacion == "dia":
            periodo_key = row_date.strftime("%Y-%m-%d")
            label = row_date.strftime("%d-%m-%Y")
        elif agrupacion == "anio":
            periodo_key = row_date.strftime("%Y")
            label = row_date.strftime("%Y")
        else:
            periodo_key = row_date.strftime("%Y-%m")
            label = row_date.strftime("%b %Y")

        current = serie_por_periodo.setdefault(
            periodo_key,
            {
                "periodo": periodo_key,
                "label": label,
                "emisiones": 0,
                "actividades": 0,
                "lotes": 0,
            },
        )
        current["emisiones"] = round(
            float(current["emisiones"] or 0) + float(row.get("emisiones") or 0),
            2,
        )
        current["actividades"] = int(current["actividades"] or 0) + 1

    serie_temporal = sorted(serie_por_periodo.values(), key=lambda item: item["periodo"])

    periodo_mayor = None
    periodo_menor = None

    if serie_temporal:
        periodo_mayor = max(serie_temporal, key=lambda x: x["emisiones"])
        periodo_menor = min(serie_temporal, key=lambda x: x["emisiones"])

    if len(serie_temporal) >= 2:
        anterior = serie_temporal[-2]["emisiones"]
        ultimo = serie_temporal[-1]["emisiones"]

        if anterior > 0:
            variacion = ((ultimo - anterior) / anterior) * 100
        else:
            variacion = 0

        if variacion > 5:
            tendencia = "Al alza"
        elif variacion < -5:
            tendencia = "A la baja"
        else:
            tendencia = "Estable"
    else:
        variacion = 0
        tendencia = "Sin comparación"

    # Por categoria/unidad/actividad usando agregaciones en DB
    por_categoria_qs = (
        actividades.values("categoria").annotate(emisiones=Sum("emisiones_kg_co2e")).order_by("-emisiones")
    )
    por_categoria = [
        {
            "categoria": item.get("categoria") or "Sin categoría",
            "emisiones": round(float(item.get("emisiones") or 0), 2),
            "porcentaje": round((float(item.get("emisiones") or 0) / emisiones_totales) * 100, 1) if emisiones_totales else 0,
        }
        for item in por_categoria_qs
    ]

    por_unidad_qs = (
        actividades.values(unidad_nombre=F("unidad_operativa__nombre")).annotate(emisiones=Sum("emisiones_kg_co2e")).order_by("-emisiones")
    )
    categoria_totals = {
        item["categoria"]: float(item["emisiones"] or 0)
        for item in por_categoria
    }
    for row in iot_rows:
        add_group_value(categoria_totals, row.get("categoria"), row.get("emisiones"))
    por_categoria = [
        {
            "categoria": categoria_label,
            "emisiones": round(float(emisiones or 0), 2),
            "porcentaje": round((float(emisiones or 0) / emisiones_totales) * 100, 1) if emisiones_totales else 0,
        }
        for categoria_label, emisiones in sort_grouped_desc(categoria_totals).items()
    ]

    por_unidad = [
        {
            "unidad_nombre": item.get("unidad_nombre") or "Sin unidad",
            "emisiones": round(float(item.get("emisiones") or 0), 2),
            "porcentaje": round((float(item.get("emisiones") or 0) / emisiones_totales) * 100, 1) if emisiones_totales else 0,
        }
        for item in por_unidad_qs
    ]

    por_actividad_qs = (
        actividades.values("actividad").annotate(emisiones=Sum("emisiones_kg_co2e")).order_by("-emisiones")
    )
    unidad_totals = {
        item["unidad_nombre"]: float(item["emisiones"] or 0)
        for item in por_unidad
    }
    for row in iot_rows:
        add_group_value(unidad_totals, row.get("unidad_nombre"), row.get("emisiones"))
    por_unidad = [
        {
            "unidad_nombre": unidad_label,
            "emisiones": round(float(emisiones or 0), 2),
            "porcentaje": round((float(emisiones or 0) / emisiones_totales) * 100, 1) if emisiones_totales else 0,
        }
        for unidad_label, emisiones in sort_grouped_desc(unidad_totals).items()
    ]

    por_actividad = [
        {
            "actividad": item.get("actividad") or "Sin actividad",
            "emisiones": round(float(item.get("emisiones") or 0), 2),
            "porcentaje": round((float(item.get("emisiones") or 0) / emisiones_totales) * 100, 1) if emisiones_totales else 0,
        }
        for item in por_actividad_qs
    ]
    actividad_totals = {
        item["actividad"]: float(item["emisiones"] or 0)
        for item in por_actividad
    }
    for row in iot_rows:
        add_group_value(actividad_totals, row.get("actividad"), row.get("emisiones"))
    por_actividad = [
        {
            "actividad": actividad_label,
            "emisiones": round(float(emisiones or 0), 2),
            "porcentaje": round((float(emisiones or 0) / emisiones_totales) * 100, 1) if emisiones_totales else 0,
        }
        for actividad_label, emisiones in sort_grouped_desc(actividad_totals).items()
    ]

    actividad_critica = por_actividad[0]["actividad"] if por_actividad else "Sin datos"
    unidad_critica = por_unidad[0]["unidad_nombre"] if por_unidad else "Sin datos"

    cantidad_periodos = len(serie_temporal)
    promedio_periodo = emisiones_totales / cantidad_periodos if cantidad_periodos else 0

    insights = []

    if emisiones_totales == 0:
        insights.append("Esta empresa aún no tiene emisiones registradas para el periodo seleccionado.")
    else:
        if tendencia == "Al alza":
            insights.append(f"Las emisiones muestran una tendencia al alza de {round(variacion, 1)}%.")
        elif tendencia == "A la baja":
            insights.append(f"Las emisiones disminuyeron {abs(round(variacion, 1))}% respecto al periodo anterior.")
        elif tendencia == "Estable":
            insights.append("Las emisiones se mantienen relativamente estables entre periodos.")
        else:
            insights.append("Se necesita más de un periodo para calcular una tendencia.")

        if actividad_critica != "Sin datos":
            insights.append(f"La actividad crítica del periodo es {actividad_critica}.")

        if unidad_critica != "Sin datos":
            insights.append(f"La unidad operativa con mayor carga de emisiones es {unidad_critica}.")

    # Soporte de paginacion de filas para carga paulatina
    page = int(request.GET.get("page", 1) or 1)
    page_size = int(request.GET.get("page_size", 0) or 0)

    rows = []
    rows_count = 0
    if page_size > 0:
        # seleccionar solo las filas paginadas
        rows_qs = actividades.order_by("-fecha").values(
            "fecha",
            "unidad_operativa__nombre",
            "lote__id_lote",
            "categoria",
            "actividad",
            "cantidad",
            "unidad",
            "emisiones_kg_co2e",
        )
        rows_count = actividades.count() + len(iot_rows)
        start = (page - 1) * page_size
        end = start + page_size
        official_rows = []
        for item in rows_qs:
            rows.append({
                "fecha": item.get("fecha").strftime("%Y-%m-%d") if item.get("fecha") else None,
                "periodo": None,
                "unidad_nombre": item.get("unidad_operativa__nombre") or "Sin unidad",
                "id_lote": item.get("lote__id_lote") or "-",
                "categoria": item.get("categoria") or "Sin categoría",
                "actividad": item.get("actividad") or "Sin actividad",
                "cantidad": float(item.get("cantidad") or 0),
                "unidad": item.get("unidad") or "",
                "emisiones": round(float(item.get("emisiones_kg_co2e") or 0), 2),
            })
        official_rows = rows
        rows = []
        all_rows = sorted(
            official_rows + iot_rows,
            key=lambda row: str(row.get("fecha_registro") or row.get("fecha") or ""),
            reverse=True,
        )
        for item in all_rows[start:end]:
            rows.append({
                "fecha": item.get("fecha"),
                "periodo": None,
                "unidad_nombre": item.get("unidad_nombre") or item.get("unidad_operativa") or "Sin unidad",
                "id_lote": item.get("id_lote") or "-",
                "categoria": item.get("categoria") or "Sin categoria",
                "actividad": item.get("actividad") or "Sin actividad",
                "cantidad": float(item.get("cantidad") or 0),
                "unidad": item.get("unidad") or "",
                "emisiones": round(float(item.get("emisiones") or 0), 2),
                "es_iot": bool(item.get("es_iot")),
            })

    else:
        # cuando page_size == 0 no devolvemos filas (cliente puede solicitarlas paginadas)
        rows = []
        rows_count = actividades.count() + len(iot_rows)

    response = {
        "empresa": {
            "id": empresa_id,
        },
        "filtros": {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "unidad_id": unidad_id,
            "categoria": categoria,
            "actividad": actividad_query,
            "agrupacion": agrupacion,
        },
        "kpis": {
            "emisiones_totales_periodo": round(emisiones_totales, 2),
            "periodo_mayor_emision": periodo_mayor["periodo"] if periodo_mayor else "Sin datos",
            "emisiones_periodo_mayor": periodo_mayor["emisiones"] if periodo_mayor else 0,
            "periodo_menor_emision": periodo_menor["periodo"] if periodo_menor else "Sin datos",
            "emisiones_periodo_menor": periodo_menor["emisiones"] if periodo_menor else 0,
            "variacion_periodo": round(variacion, 1),
            "tendencia": tendencia,
            "actividad_critica_periodo": actividad_critica,
            "unidad_critica_periodo": unidad_critica,
            "promedio_periodo": round(promedio_periodo, 2),
            "lecturas_iot_count": len(iot_rows),
            "emisiones_iot_24h": round(emisiones_iot, 2),
        },
        "serie_temporal": serie_temporal,
        "por_categoria": por_categoria,
        "por_unidad": por_unidad,
        "por_actividad": por_actividad,
        "rows": rows,
        "rows_count": rows_count,
        "page": page,
        "page_size": page_size,
        "insights": insights,
    }

    return Response(response, status=status.HTTP_200_OK)
