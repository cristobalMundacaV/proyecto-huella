from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.iot.models import RegistroSensor

from ..models import EvidenciaObra, Obra, RegistroEmision
from .local_advisor import generar_analisis_local
from .recommendation_builder import build_structured_recommendations

try:
    from .ai_advisor import generar_analisis_ia
except Exception:
    generar_analisis_ia = None


def to_float(value):
    return float(value or 0)


def build_iot_context(organizacion_id=None, hours=24):
    since = timezone.now() - timedelta(hours=hours)
    queryset = RegistroSensor.objects.select_related("dispositivo", "organizacion", "obra", "etapa").filter(
        timestamp_sensor__gte=since
    )
    if organizacion_id:
        queryset = queryset.filter(
            Q(organizacion__organizacion_id=organizacion_id)
            | Q(organizacion__nombre__iexact=organizacion_id)
        ).distinct()

    por_tipo = {
        item["tipo"]: item["total"]
        for item in queryset.values("tipo").annotate(total=Count("id")).order_by("-total")
    }
    top_dispositivos = [
        {
            "dispositivo_id": item["dispositivo__dispositivo_id"],
            "nombre": item["dispositivo__nombre"],
            "lecturas": item["total"],
        }
        for item in queryset.values("dispositivo__dispositivo_id", "dispositivo__nombre")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    ]
    ultimo = queryset.order_by("-timestamp_sensor").first()
    return {
        "ventana_horas": hours,
        "registros_iot": queryset.count(),
        "lecturas_iot_por_tipo": por_tipo,
        "top_dispositivos_iot": top_dispositivos,
        "ultima_lectura_iot": ultimo.timestamp_sensor.isoformat() if ultimo else None,
    }


def build_top_stages(registros):
    return [
        {
            "etapa_id": item["etapa__etapa_id"],
            "etapa_nombre": item["etapa__nombre"] or "Sin etapa asociada",
            "emisiones_kg_co2e": round(to_float(item["total"]), 3),
        }
        for item in registros.values("etapa__etapa_id", "etapa__nombre")
        .annotate(total=Sum("emisiones_kg_co2e"))
        .order_by("-total")[:5]
    ]


def build_top_obras(registros):
    return [
        {
            "obra_codigo": item["obra__codigo_obra"],
            "obra_nombre": item["obra__nombre"] or "Sin obra asociada",
            "emisiones_kg_co2e": round(to_float(item["total"]), 3),
        }
        for item in registros.values("obra__codigo_obra", "obra__nombre")
        .annotate(total=Sum("emisiones_kg_co2e"))
        .order_by("-total")[:5]
    ]


def build_recommendation_context(payload):
    organizacion_id = payload.get("organizacion_id") or payload.get("organizacion")
    obra_codigo = payload.get("obra_codigo") or payload.get("codigo_obra")
    hours = int(payload.get("iot_hours") or payload.get("horas_iot") or 24)
    scope = payload.get("scope") or payload.get("area") or "dashboard"

    registros = RegistroEmision.objects.select_related("organizacion", "obra", "etapa")
    obras = Obra.objects.all()
    evidencias = EvidenciaObra.objects.all()

    if organizacion_id:
        filtro_organizacion = Q(organizacion__organizacion_id=organizacion_id) | Q(organizacion__nombre__iexact=organizacion_id)
        registros = registros.filter(filtro_organizacion).distinct()
        obras = obras.filter(filtro_organizacion).distinct()
        evidencias = evidencias.filter(filtro_organizacion).distinct()

    if obra_codigo:
        registros = registros.filter(obra__codigo_obra=obra_codigo)
        obras = obras.filter(codigo_obra=obra_codigo)
        evidencias = evidencias.filter(obra__codigo_obra=obra_codigo)

    total = to_float(registros.aggregate(total=Sum("emisiones_kg_co2e"))["total"])
    por_categoria = {
        item["categoria"]: to_float(item["total"])
        for item in registros.values("categoria").annotate(total=Sum("emisiones_kg_co2e")).order_by("-total")
    }
    categoria_critica = max(por_categoria, key=por_categoria.get, default="Sin datos")
    top_fuentes = [
        {
            "fuente_emision": item["fuente_emision"],
            "categoria": item["categoria"],
            "emisiones_kg_co2e": round(to_float(item["total"]), 3),
        }
        for item in registros.values("fuente_emision", "categoria")
        .annotate(total=Sum("emisiones_kg_co2e"))
        .order_by("-total")[:5]
    ]
    top_etapas = build_top_stages(registros)
    top_obras = build_top_obras(registros)
    superficie_total = sum(to_float(obra.superficie_m2) for obra in obras)
    registros_count = registros.count()
    registros_con_evidencia = registros.filter(evidencias__isnull=False).distinct().count()
    cobertura = None if registros_count == 0 else round((registros_con_evidencia / registros_count) * 100, 2)

    context = {
        "organizacion_id": organizacion_id,
        "obra_codigo": obra_codigo,
        "scope": scope,
        "total_emisiones": round(total, 3),
        "emisiones_totales": round(total, 3),
        "categoria_critica": categoria_critica,
        "fuente_critica": top_fuentes[0]["fuente_emision"] if top_fuentes else "Sin datos",
        "top_fuentes_criticas": top_fuentes,
        "emisiones_por_categoria": por_categoria,
        "obra_critica": top_obras[0]["obra_nombre"] if top_obras else "Sin obra critica",
        "top_obras_criticas": top_obras,
        "etapa_critica": top_etapas[0]["etapa_nombre"] if top_etapas else "Sin etapa critica",
        "top_etapas_criticas": top_etapas,
        "intensidad_carbono": None if superficie_total <= 0 else round(total / superficie_total, 3),
        "evidencia_respaldada": "Pendiente de vinculacion" if cobertura is None else cobertura,
        "registros_count": registros_count,
        "evidencias_count": evidencias.count(),
    }
    context.update(build_iot_context(organizacion_id=organizacion_id, hours=hours))
    return context


def generate_recommendations(payload):
    context = build_recommendation_context(payload)
    scope = context.get("scope") or "dashboard"
    structured = build_structured_recommendations(context, scope=scope)

    if generar_analisis_ia:
        try:
            return {
                "engine": "ia",
                "context": context,
                "recommendation": generar_analisis_ia(context),
                "structured": structured,
                "cards": structured["active_cards"],
                "actions": structured["actions"],
            }
        except Exception as exc:
            context["ai_error"] = str(exc)

    return {
        "engine": "local",
        "context": context,
        "recommendation": generar_analisis_local(context),
        "structured": structured,
        "cards": structured["active_cards"],
        "actions": structured["actions"],
    }
