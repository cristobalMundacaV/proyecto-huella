from datetime import timedelta

from django.db.models import Q, Sum
from django.utils import timezone

from apps.iot.models import RegistroSensor

from ..models import EvidenciaObra, Obra, RegistroEmision
from .local_advisor import generar_analisis_local

try:
    from .ai_advisor import generar_analisis_ia
except Exception:
    generar_analisis_ia = None


def to_float(value):
    return float(value or 0)


def build_iot_context(constructora_id=None, hours=24):
    since = timezone.now() - timedelta(hours=hours)
    queryset = RegistroSensor.objects.select_related("dispositivo", "constructora", "obra", "etapa").filter(
        timestamp_sensor__gte=since
    )
    if constructora_id:
        queryset = queryset.filter(
            Q(constructora__constructora_id=constructora_id)
            | Q(constructora__nombre__iexact=constructora_id)
        ).distinct()

    total = queryset.aggregate(total=Sum("co2e_estimado"))["total"]
    por_tipo = {
        item["tipo"]: to_float(item["total"])
        for item in queryset.values("tipo").annotate(total=Sum("co2e_estimado")).order_by("-total")
    }
    top_dispositivos = [
        {
            "dispositivo_id": item["dispositivo__dispositivo_id"],
            "nombre": item["dispositivo__nombre"],
            "emisiones_kg_co2e": round(to_float(item["total"]), 3),
        }
        for item in queryset.values("dispositivo__dispositivo_id", "dispositivo__nombre")
        .annotate(total=Sum("co2e_estimado"))
        .order_by("-total")[:5]
    ]
    ultimo = queryset.order_by("-timestamp_sensor").first()
    return {
        "ventana_horas": hours,
        "registros_iot": queryset.count(),
        "emisiones_iot_kg_co2e": round(to_float(total), 3),
        "emisiones_iot_por_tipo": por_tipo,
        "top_dispositivos_iot": top_dispositivos,
        "ultima_lectura_iot": ultimo.timestamp_sensor.isoformat() if ultimo else None,
    }


def build_recommendation_context(payload):
    constructora_id = payload.get("constructora_id") or payload.get("constructora")
    obra_codigo = payload.get("obra_codigo") or payload.get("codigo_obra")
    hours = int(payload.get("iot_hours") or payload.get("horas_iot") or 24)

    registros = RegistroEmision.objects.select_related("constructora", "obra", "etapa")
    obras = Obra.objects.all()
    evidencias = EvidenciaObra.objects.all()

    if constructora_id:
        filtro_constructora = Q(constructora__constructora_id=constructora_id) | Q(constructora__nombre__iexact=constructora_id)
        registros = registros.filter(filtro_constructora).distinct()
        obras = obras.filter(filtro_constructora).distinct()
        evidencias = evidencias.filter(filtro_constructora).distinct()

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
    superficie_total = sum(to_float(obra.superficie_m2) for obra in obras)
    registros_count = registros.count()
    registros_con_evidencia = registros.filter(evidencias__isnull=False).distinct().count()
    cobertura = None if registros_count == 0 else round((registros_con_evidencia / registros_count) * 100, 2)

    context = {
        "constructora_id": constructora_id,
        "obra_codigo": obra_codigo,
        "total_emisiones": round(total, 3),
        "emisiones_totales": round(total, 3),
        "categoria_critica": categoria_critica,
        "fuente_critica": top_fuentes[0]["fuente_emision"] if top_fuentes else "Sin datos",
        "top_fuentes_criticas": top_fuentes,
        "emisiones_por_categoria": por_categoria,
        "intensidad_carbono": None if superficie_total <= 0 else round(total / superficie_total, 3),
        "evidencia_respaldada": "Pendiente de vinculacion" if cobertura is None else cobertura,
        "registros_count": registros_count,
        "evidencias_count": evidencias.count(),
    }
    context.update(build_iot_context(constructora_id=constructora_id, hours=hours))
    return context


def generate_recommendations(payload):
    context = build_recommendation_context(payload)
    if generar_analisis_ia:
        try:
            return {"engine": "ia", "context": context, "recommendation": generar_analisis_ia(context)}
        except Exception as exc:
            context["ai_error"] = str(exc)
    return {"engine": "local", "context": context, "recommendation": generar_analisis_local(context)}
