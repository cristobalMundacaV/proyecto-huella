from datetime import timedelta

from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.analytics.models import Constructora, EtapaObra, Obra

from .models import DispositivoSensor, RegistroSensor
from .serializers import DispositivoSensorSerializer, RegistroSensorSerializer
from .services import SensorIngestionError, procesar_payload_ingesta


def resolve_constructora(request):
    constructora_id = request.query_params.get("constructora_id") or request.query_params.get("constructora")
    if not constructora_id:
        return None
    return (
        Constructora.objects.filter(constructora_id=constructora_id).first()
        or Constructora.objects.filter(nombre__iexact=constructora_id).first()
    )


def top_emisiones(queryset, group_field):
    return (
        queryset.values(group_field)
        .annotate(emisiones=Sum("co2e_estimado"))
        .order_by("-emisiones", group_field)
        .first()
    )


def normalize_relation_payload(data):
    payload = data.copy()

    constructora_codigo = payload.pop("constructora_id", None) or payload.pop("constructora_codigo", None)
    if constructora_codigo:
        constructora = get_object_or_404(Constructora, constructora_id=str(constructora_codigo).strip())
        payload["constructora"] = constructora.id

    obra_codigo = payload.pop("obra_codigo", None)
    if obra_codigo:
        obra = get_object_or_404(Obra, codigo_obra=str(obra_codigo).strip())
        payload["obra"] = obra.id
        payload["constructora"] = obra.constructora_id

    etapa_codigo = payload.pop("etapa_codigo", None) or payload.pop("etapa_id", None)
    if etapa_codigo and not str(etapa_codigo).isdigit():
        etapa = get_object_or_404(EtapaObra, etapa_id=str(etapa_codigo).strip())
        payload["etapa"] = etapa.id
        payload.setdefault("constructora", etapa.constructora_id)

    return payload


@api_view(["GET", "POST"])
def dispositivos(request):
    if request.method == "GET":
        queryset = DispositivoSensor.objects.select_related(
            "constructora", "obra", "etapa", "factor_emision_default"
        )
        constructora = resolve_constructora(request)
        if constructora:
            queryset = queryset.filter(constructora=constructora)
        activo = request.query_params.get("activo")
        if activo not in (None, ""):
            queryset = queryset.filter(activo=str(activo).lower() in {"1", "true", "si", "yes"})
        return Response(DispositivoSensorSerializer(queryset, many=True).data)

    serializer = DispositivoSensorSerializer(data=normalize_relation_payload(request.data))
    serializer.is_valid(raise_exception=True)
    dispositivo = serializer.save()
    return Response(DispositivoSensorSerializer(dispositivo).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
def dispositivo_detail(request, dispositivo_id):
    dispositivo = get_object_or_404(
        DispositivoSensor.objects.select_related("constructora", "obra", "etapa", "factor_emision_default"),
        dispositivo_id=dispositivo_id,
    )
    if request.method == "GET":
        return Response(DispositivoSensorSerializer(dispositivo).data)

    serializer = DispositivoSensorSerializer(
        dispositivo,
        data=normalize_relation_payload(request.data),
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    return Response(DispositivoSensorSerializer(serializer.save()).data)


@csrf_exempt
@api_view(["POST"])
def ingesta(request):
    payload = {"lecturas": request.data} if isinstance(request.data, list) else dict(request.data)
    sensor_key = request.headers.get("X-Sensor-Key")
    if sensor_key and not payload.get("api_key"):
        payload["api_key"] = sensor_key

    try:
        resultados = procesar_payload_ingesta(payload)
    except SensorIngestionError as exc:
        return Response({"error": exc.message}, status=exc.http_status)

    registros = [item["registro"] for item in resultados]
    created = sum(1 for item in resultados if item["created"])
    return Response(
        {
            "recibidos": len(registros),
            "creados": created,
            "duplicados": len(registros) - created,
            "registros": RegistroSensorSerializer(registros, many=True).data,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["GET"])
def registros_sensor(request):
    queryset = RegistroSensor.objects.select_related(
        "dispositivo", "constructora", "obra", "etapa", "registro_emision"
    ).order_by("-timestamp_sensor", "-received_at")
    constructora = resolve_constructora(request)
    if constructora:
        queryset = queryset.filter(constructora=constructora)

    dispositivo_id = request.query_params.get("device_id") or request.query_params.get("dispositivo_id")
    if dispositivo_id:
        queryset = queryset.filter(dispositivo__dispositivo_id=dispositivo_id)

    tipo = request.query_params.get("tipo") or request.query_params.get("type")
    if tipo:
        queryset = queryset.filter(tipo=tipo)

    limit = min(int(request.query_params.get("limit", 100)), 500)
    return Response(RegistroSensorSerializer(queryset[:limit], many=True).data)


@api_view(["GET"])
def kpis_operacionales(request):
    queryset = RegistroSensor.objects.all()
    constructora = resolve_constructora(request)
    if constructora:
        queryset = queryset.filter(constructora=constructora)

    ultimas_24h = queryset.filter(timestamp_sensor__gte=timezone.now() - timedelta(hours=24))
    agregados = ultimas_24h.aggregate(emisiones_totales=Sum("co2e_estimado"), consumo_promedio=Avg("valor"))
    tipo_top = top_emisiones(ultimas_24h, "tipo")
    dispositivo_top = top_emisiones(ultimas_24h, "dispositivo__dispositivo_id")
    ultima = ultimas_24h.order_by("-timestamp_sensor").first()

    return Response(
        {
            "total_registros_24h": ultimas_24h.count(),
            "emisiones_24h_kg_co2e": float(agregados["emisiones_totales"] or 0),
            "consumo_promedio_24h": float(agregados["consumo_promedio"] or 0),
            "dispositivos_activos_24h": ultimas_24h.values("dispositivo").distinct().count(),
            "tipo_mayor_emision_24h": tipo_top["tipo"] if tipo_top else None,
            "tipo_mayor_emision_24h_kg_co2e": float(tipo_top["emisiones"] or 0) if tipo_top else 0,
            "dispositivo_mayor_emision_24h": dispositivo_top["dispositivo__dispositivo_id"] if dispositivo_top else None,
            "dispositivo_mayor_emision_24h_kg_co2e": float(dispositivo_top["emisiones"] or 0) if dispositivo_top else 0,
            "ultima_actualizacion": ultima.timestamp_sensor.isoformat() if ultima else None,
        }
    )
