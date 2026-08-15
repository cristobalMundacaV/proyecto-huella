from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status

from apps.analytics.models import ActividadOperacional

from .models import DispositivoSensor, LecturaSensor, RegistroSensor
from .services_v2 import registrar_lectura


class SensorIngestionError(Exception):
    def __init__(self, message, http_status=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.http_status = http_status
        super().__init__(message)


TIPO_ALIASES = {
    "diesel": LecturaSensor.Tipo.DIESEL_LITROS,
    "diesel_l": LecturaSensor.Tipo.DIESEL_LITROS,
    "diesel_litros": LecturaSensor.Tipo.DIESEL_LITROS,
    "gasolina": LecturaSensor.Tipo.GASOLINA_LITROS,
    "gasolina_l": LecturaSensor.Tipo.GASOLINA_LITROS,
    "gasolina_litros": LecturaSensor.Tipo.GASOLINA_LITROS,
    "electricidad": LecturaSensor.Tipo.ELECTRICIDAD_KWH,
    "energia": LecturaSensor.Tipo.ELECTRICIDAD_KWH,
    "kwh": LecturaSensor.Tipo.ELECTRICIDAD_KWH,
    "electricidad_kwh": LecturaSensor.Tipo.ELECTRICIDAD_KWH,
    "horas": LecturaSensor.Tipo.HORAS_MAQUINARIA,
    "horas_maquina": LecturaSensor.Tipo.HORAS_MAQUINARIA,
    "horas_maquinaria": LecturaSensor.Tipo.HORAS_MAQUINARIA,
    "horas_encendido": LecturaSensor.Tipo.HORAS_ENCENDIDO,
    "agua": LecturaSensor.Tipo.AGUA_LITROS,
    "agua_l": LecturaSensor.Tipo.AGUA_LITROS,
    "agua_litros": LecturaSensor.Tipo.AGUA_LITROS,
    "gps": LecturaSensor.Tipo.GPS_EVENTO,
    "gps_evento": LecturaSensor.Tipo.GPS_EVENTO,
    "temperatura": LecturaSensor.Tipo.TEMPERATURA,
    "humedad": LecturaSensor.Tipo.HUMEDAD,
}


def normalizar_tipo_sensor(value):
    key = str(value or "").strip().lower()
    tipo = TIPO_ALIASES.get(key, key)
    validos = {choice[0] for choice in LecturaSensor.Tipo.choices}
    if tipo not in validos:
        raise SensorIngestionError(f"Tipo de lectura no soportado: {value}")
    return tipo


def parse_sensor_timestamp(value):
    if not value:
        return timezone.now()
    parsed = parse_datetime(str(value))
    if parsed is None:
        raise SensorIngestionError("timestamp debe venir en formato ISO-8601.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def decimal_from_payload(value, field_name="value"):
    if value is None or value == "":
        raise SensorIngestionError(f"{field_name} es obligatorio.")
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise SensorIngestionError(f"{field_name} debe ser numerico.") from exc
    if parsed < 0:
        raise SensorIngestionError(f"{field_name} no puede ser negativo.")
    return parsed


def resolve_device(payload):
    dispositivo_id = payload.get("device_id") or payload.get("dispositivo_id") or payload.get("sensor")
    if not dispositivo_id:
        raise SensorIngestionError("device_id es obligatorio para registrar telemetria.")
    dispositivo = (
        DispositivoSensor.objects.select_related(
            "organizacion",
            "obra",
            "etapa",
            "factor_emision_default",
        )
        .filter(dispositivo_id=str(dispositivo_id).strip())
        .first()
    )
    if not dispositivo:
        raise SensorIngestionError("Dispositivo sensor no registrado.", status.HTTP_404_NOT_FOUND)
    if not dispositivo.activo:
        raise SensorIngestionError("Dispositivo sensor inactivo.", status.HTTP_403_FORBIDDEN)
    api_key = payload.get("api_key") or payload.get("token")
    if not dispositivo.verify_api_key(api_key):
        raise SensorIngestionError("API key de sensor invalida.", status.HTTP_403_FORBIDDEN)
    return dispositivo


def sanitize_payload(payload):
    sanitized = dict(payload)
    sanitized.pop("api_key", None)
    sanitized.pop("token", None)
    return sanitized


@transaction.atomic
def procesar_lectura_sensor(payload):
    dispositivo = resolve_device(payload)
    tipo = normalizar_tipo_sensor(payload.get("type") or payload.get("tipo"))
    valor = decimal_from_payload(payload.get("value") if "value" in payload else payload.get("valor"))
    timestamp = parse_sensor_timestamp(payload.get("timestamp") or payload.get("fecha") or payload.get("fecha_registro"))
    external_id = str(payload.get("external_id") or payload.get("message_id") or "").strip()

    if external_id:
        existente = (
            RegistroSensor.objects.select_related("registro_emision", "dispositivo")
            .filter(dispositivo=dispositivo, external_id=external_id)
            .first()
        )
        if existente:
            return existente, False

    registro = RegistroSensor.objects.create(
        external_id=external_id,
        dispositivo=dispositivo,
        organizacion=dispositivo.organizacion,
        obra=dispositivo.obra,
        etapa=dispositivo.etapa,
        tipo=tipo,
        valor=valor,
        unidad=payload.get("unit") or payload.get("unidad") or "",
        timestamp_sensor=timestamp,
        metadata=payload.get("metadata") or {},
        raw_payload=sanitize_payload(payload),
    )

    actividad = None
    actividad_id = payload.get("actividad") or payload.get("actividad_id")
    if actividad_id:
        actividad = ActividadOperacional.objects.filter(
            pk=actividad_id, organizacion=dispositivo.organizacion
        ).first()
        if not actividad:
            raise SensorIngestionError("La actividad no pertenece a la organizacion del sensor.")
    metadata_tecnica = dict(payload.get("metadata") or {})
    metadata_tecnica.update({
        "registro_sensor_id": registro.id,
        "external_id": external_id,
        "raw_payload": registro.raw_payload,
    })
    lectura_v2 = registrar_lectura(dispositivo, {
        "actividad": actividad,
        "timestamp": timestamp,
        "concepto": tipo,
        "valor_numerico": valor,
        "unidad": registro.unidad,
        "metadata_tecnica": metadata_tecnica,
    })
    registro.lectura_v2 = lectura_v2
    registro.estado_procesamiento = RegistroSensor.EstadoProcesamiento.HECHO_OPERACIONAL
    registro.save(update_fields=["lectura_v2", "estado_procesamiento"])

    dispositivo.mark_seen()
    return registro, True


def procesar_payload_ingesta(payload):
    lecturas = payload.get("lecturas") or payload.get("readings")
    if lecturas is None:
        lecturas = [payload]

    resultados = []
    for lectura in lecturas:
        merged = dict(lectura)
        if payload.get("api_key") and not merged.get("api_key"):
            merged["api_key"] = payload.get("api_key")
        if payload.get("device_id") and not merged.get("device_id"):
            merged["device_id"] = payload.get("device_id")
        if payload.get("dispositivo_id") and not merged.get("dispositivo_id"):
            merged["dispositivo_id"] = payload.get("dispositivo_id")
        registro, created = procesar_lectura_sensor(merged)
        resultados.append({"registro": registro, "created": created})

    return resultados
