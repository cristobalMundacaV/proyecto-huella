import logging
import csv
import json
from io import StringIO

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from .models import (
    DocumentoLote,
    EmisionLote,
    Empresa,
    EspecieMadera,
    ExtraccionDocumento,
    FactorEmision,
    Lote,
    UnidadOperativa,
)
from .serializers import (
    DocumentoLoteSerializer,
    EmisionLoteSerializer,
    EmpresaSerializer,
    EspecieMaderaSerializer,
    ExtraccionDocumentoSerializer,
    FactorEmisionSerializer,
    LoteSerializer,
    TransporteLoteSerializer,
    UnidadOperativaSerializer,
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
from .services.importadores import (
    ImportadorActividadesLote,
    ImportadorEmpresas,
    ImportadorFactores,
    ImportadorLotes,
    ImportadorUnidadesOperativas,
)
from .services.empresa_completa_importer import ImportadorEmpresaCompleta
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


def build_system_status():
    return {
        "factores": FactorEmision.objects.count(),
        "empresas": Empresa.objects.count(),
        "unidades": UnidadOperativa.objects.count(),
        "lotes": Lote.objects.count(),
        "actividades": EmisionLote.objects.count(),
        "evidencias": DocumentoLote.objects.count(),
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
    lotes = list(
        Lote.objects.select_related("empresa", "unidad_operativa").filter(
            Q(empresa=empresa) | Q(unidad_operativa__empresa=empresa)
        )
    )
    actividades_qs = list(EmisionLote.objects.select_related(
        "empresa",
        "unidad_operativa",
        "lote",
        "lote__empresa",
        "lote__unidad_operativa",
    ).filter(Q(empresa=empresa) | Q(lote__empresa=empresa) | Q(unidad_operativa__empresa=empresa)))

    rows = []
    emisiones_por_actividad = {}
    emisiones_por_categoria = {}
    emisiones_por_unidad = {}
    emisiones_por_empresa = {empresa.nombre: 0}
    emisiones_por_lote = {}
    total_emisiones = 0
    co2_almacenado_total = 0
    evidencias_count = 0
    pasaportes_count = 0

    for lote in lotes:
        balance = calcular_balance_lote(lote)
        pasaporte = calcular_pasaporte_lote(lote)
        co2_almacenado_total += float(balance["co2_almacenado_kg"] or 0)
        evidencias_count += lote.documentos.count()
        if pasaporte["estado_pasaporte"] != "Sin pasaporte":
            pasaportes_count += 1

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

    summary = {
        "total_emisiones": total_emisiones,
        "emisiones_por_empresa": emisiones_por_company_sorted,
        "emisiones_por_actividad": emisiones_por_activity_sorted,
        "datos": rows,
    }
    scenario_medio = summarize_rows(
        simulate_rows(rows, diesel_reduction=10, electricity_increase=0, selected_company=empresa.nombre)
    )
    scenario_optimo = optimize_rows(rows)
    risk = calculate_risk_profile(summary, scenario_optimo)

    return {
        "empresa_id": empresa.empresa_id,
        "empresa_nombre": empresa.nombre,
        "total_emisiones": total_emisiones,
        "emisiones_totales": total_emisiones,
        "co2_almacenado_total": co2_almacenado_total,
        "balance_neto_total": total_emisiones - co2_almacenado_total,
        "unidades_count": empresa.unidades_operativas.count(),
        "lotes_count": len(lotes),
        "actividades_count": len(rows),
        "evidencias_count": evidencias_count,
        "pasaportes_count": pasaportes_count,
        "actividad_critica": next(iter(emisiones_por_activity_sorted), "Sin datos"),
        "categoria_critica": next(iter(emisiones_por_category_sorted), "Sin datos"),
        "unidad_critica": next(iter(emisiones_por_unit_sorted), "Sin datos"),
        "riesgo": risk,
        "escenario_medio": scenario_medio,
        "escenario_optimo": scenario_optimo,
        "datos": rows,
        "emisiones_por_actividad": emisiones_por_activity_sorted,
        "emisiones_por_categoria": emisiones_por_category_sorted,
        "emisiones_por_unidad_operativa": emisiones_por_unit_sorted,
        "emisiones_por_lote": emisiones_por_lote,
    }


@api_view(["GET", "POST"])
def empresas(request):
    if request.method == "GET":
        queryset = Empresa.objects.prefetch_related(
            "unidades_operativas",
            "unidades_operativas__lotes",
            "unidades_operativas__actividades_emision",
            "lotes",
            "lotes__documentos",
            "lotes__actividades",
            "actividades_emision",
        )
        serializer = EmpresaSerializer(queryset, many=True)
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


@api_view(["GET"])
def empresa_dashboard(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    return Response(build_company_dashboard_response(empresa))


@api_view(["GET"])
def empresa_unidades(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    serializer = UnidadOperativaSerializer(
        empresa.unidades_operativas.select_related("empresa"),
        many=True,
    )
    return Response(serializer.data)


@api_view(["GET"])
def empresa_lotes(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    queryset = Lote.objects.select_related("empresa", "unidad_operativa").filter(
        Q(empresa=empresa) | Q(unidad_operativa__empresa=empresa)
    )
    serializer = LoteSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def empresa_actividades(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    queryset = EmisionLote.objects.select_related(
        "empresa",
        "unidad_operativa",
        "lote",
    ).filter(Q(empresa=empresa) | Q(lote__empresa=empresa) | Q(unidad_operativa__empresa=empresa))
    serializer = EmisionLoteSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def empresa_emisiones(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    actividades = list(
        EmisionLote.objects.select_related(
            "empresa",
            "unidad_operativa",
            "lote",
            "lote__empresa",
            "lote__unidad_operativa",
        ).filter(
            Q(empresa=empresa)
            | Q(lote__empresa=empresa)
            | Q(unidad_operativa__empresa=empresa)
        )
    )
    factor_keys = {
        (actividad.actividad_key, actividad.unidad)
        for actividad in actividades
        if actividad.actividad_key and actividad.unidad
    }
    factor_lookup = {}

    if factor_keys:
        factor_q = Q()
        for actividad_key, unidad in factor_keys:
            factor_q |= Q(actividad_key=actividad_key, unidad=unidad)

        for factor in FactorEmision.objects.filter(factor_q).order_by("-anio", "-updated_at"):
            factor_lookup.setdefault((factor.actividad_key, factor.unidad), factor)

    rows = []
    resumen_por_actividad = {}
    resumen_por_categoria = {}
    resumen_por_unidad = {}
    resumen_por_lote = {}
    diesel_total = 0.0

    for actividad in actividades:
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
                    actividad.fecha.isoformat()
                    if actividad.fecha
                    else actividad.created_at.date().isoformat()
                ),
                "empresa": empresa.nombre,
                "unidad_id": unidad_id,
                "unidad_nombre": unidad_nombre,
                "id_lote": id_lote,
                "actividad": actividad.actividad,
                "actividad_key": actividad.actividad_key,
                "categoria": categoria,
                "cantidad": float(actividad.cantidad or 0),
                "unidad": actividad.unidad,
                "factor_emision": float(actividad.factor_emision or 0),
                "emisiones": emisiones,
                "fuente_factor": factor.fuente if factor else "",
                "anio_factor": factor.anio if factor else None,
            }
        )

        resumen_por_actividad[actividad.actividad] = (
            resumen_por_actividad.get(actividad.actividad, 0.0) + emisiones
        )
        resumen_por_categoria[categoria] = resumen_por_categoria.get(categoria, 0.0) + emisiones
        resumen_por_unidad[(unidad_id, unidad_nombre)] = (
            resumen_por_unidad.get((unidad_id, unidad_nombre), 0.0) + emisiones
        )
        if id_lote:
            resumen_por_lote[id_lote] = resumen_por_lote.get(id_lote, 0.0) + emisiones
        if is_diesel_activity(
            {
                "actividad": actividad.actividad,
                "actividad_key": actividad.actividad_key,
                "categoria": categoria,
            }
        ):
            diesel_total += emisiones

    rows.sort(key=lambda row: row["emisiones"], reverse=True)
    total_emisiones = sum(row["emisiones"] for row in rows)

    def percentage(value):
        return (value / total_emisiones * 100) if total_emisiones else 0

    actividad_critica, actividad_critica_total = max(
        resumen_por_actividad.items(),
        key=lambda item: item[1],
        default=("Sin datos", 0),
    )
    categoria_critica = max(
        resumen_por_categoria.items(),
        key=lambda item: item[1],
        default=("Sin datos", 0),
    )[0]
    unidad_critica = max(
        resumen_por_unidad.items(),
        key=lambda item: item[1],
        default=(("", "Sin datos"), 0),
    )[0][1]
    lote_critico = max(
        resumen_por_lote.items(),
        key=lambda item: item[1],
        default=("Sin datos", 0),
    )[0]
    lotes_con_emisiones = [id_lote for id_lote, value in resumen_por_lote.items() if value > 0]

    return Response(
        {
            "empresa": {
                "id": empresa.empresa_id,
                "nombre": empresa.nombre,
            },
            "kpis": {
                "emisiones_totales": total_emisiones,
                "actividad_critica": actividad_critica,
                "categoria_critica": categoria_critica,
                "unidad_critica": unidad_critica,
                "lote_critico": lote_critico,
                "cantidad_actividades": len(rows),
                "cantidad_lotes_con_emisiones": len(lotes_con_emisiones),
                "promedio_emision_por_lote": (
                    total_emisiones / len(lotes_con_emisiones)
                    if lotes_con_emisiones
                    else 0
                ),
                "porcentaje_diesel": percentage(diesel_total),
                "porcentaje_top_actividad": percentage(actividad_critica_total),
                "actividades_sin_factor": sum(
                    1 for row in rows if not row["factor_emision"]
                ),
            },
            "resumen_por_categoria": [
                {
                    "categoria": categoria,
                    "emisiones": emisiones,
                    "porcentaje": percentage(emisiones),
                }
                for categoria, emisiones in sorted(
                    resumen_por_categoria.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ],
            "resumen_por_unidad": [
                {
                    "unidad_id": unidad_id,
                    "unidad_nombre": unidad_nombre,
                    "emisiones": emisiones,
                    "porcentaje": percentage(emisiones),
                }
                for (unidad_id, unidad_nombre), emisiones in sorted(
                    resumen_por_unidad.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ],
            "resumen_por_lote": [
                {
                    "id_lote": id_lote,
                    "emisiones": emisiones,
                    "porcentaje": percentage(emisiones),
                }
                for id_lote, emisiones in sorted(
                    resumen_por_lote.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ],
            "rows": rows,
        }
    )


@api_view(["GET"])
def empresa_evidencias(request, empresa_id):
    empresa = get_empresa_or_404(empresa_id)
    queryset = DocumentoLote.objects.select_related(
        "lote",
        "lote__empresa",
        "lote__unidad_operativa",
    ).filter(Q(lote__empresa=empresa) | Q(lote__unidad_operativa__empresa=empresa))
    serializer = DocumentoLoteSerializer(queryset, many=True, context={"request": request})
    return Response(serializer.data)


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
        queryset = Lote.objects.all()
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
    lote = get_object_or_404(Lote, id_lote=id_lote)
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
        fuente = "huella_engine"

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
