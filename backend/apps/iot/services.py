from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status

from apps.analytics.models import FactorEmision, RegistroEmision
from apps.analytics.services.environmental_records import create_environmental_record

from .models import DispositivoSensor, LecturaSensor, RegistroSensor


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


CATEGORIA_POR_TIPO = {
    LecturaSensor.Tipo.DIESEL_LITROS: RegistroEmision.Categoria.MAQUINARIA,
    LecturaSensor.Tipo.GASOLINA_LITROS: RegistroEmision.Categoria.MAQUINARIA,
    LecturaSensor.Tipo.ELECTRICIDAD_KWH: RegistroEmision.Categoria.ENERGIA,
    LecturaSensor.Tipo.HORAS_MAQUINARIA: RegistroEmision.Categoria.MAQUINARIA,
    LecturaSensor.Tipo.HORAS_ENCENDIDO: RegistroEmision.Categoria.MAQUINARIA,
    LecturaSensor.Tipo.AGUA_LITROS: RegistroEmision.Categoria.AGUA,
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


def resolve_factor(payload, dispositivo, tipo):
    factor_id = payload.get("factor_id") or payload.get("factor_emision_id")
    if factor_id:
        return FactorEmision.objects.filter(pk=factor_id, activo=True).first()

    if dispositivo.factor_emision_default_id:
        return dispositivo.factor_emision_default

    actividad_key = payload.get("actividad_key")
    if actividad_key:
        return (
            FactorEmision.objects.filter(
                preset=dispositivo.organizacion.preset,
                actividad_key=actividad_key,
                activo=True,
            )
            .order_by("-anio")
            .first()
        )

    unidad = payload.get("unit") or payload.get("unidad") or LecturaSensor.UNIDADES_POR_TIPO.get(tipo, "")
    categoria = CATEGORIA_POR_TIPO.get(tipo)
    if not categoria:
        return None

    return (
        FactorEmision.objects.filter(
            preset=dispositivo.organizacion.preset,
            unidad=unidad,
            activo=True,
        )
        .filter(categoria__in=[categoria, "Combustible", "Energia", "Maquinaria"])
        .order_by("-anio")
        .first()
    )


def should_create_emission(payload, tipo, factor):
    explicit = payload.get("crear_registro_emision")
    if explicit is not None:
        return str(explicit).strip().lower() in {"1", "true", "si", "yes"}
    if tipo in {
        LecturaSensor.Tipo.TEMPERATURA,
        LecturaSensor.Tipo.HUMEDAD,
        LecturaSensor.Tipo.GPS_EVENTO,
    }:
        return False
    factor_value = factor.factor_emision if factor else LecturaSensor.FACTORES_CO2E.get(tipo, Decimal("0"))
    return factor_value > 0


def sanitize_payload(payload):
    sanitized = dict(payload)
    sanitized.pop("api_key", None)
    sanitized.pop("token", None)
    return sanitized


def build_emission_metadata(registro_sensor, payload):
    metadata = dict(payload.get("metadata") or {})
    metadata.update(
        {
            "origen": "iot_sensor",
            "dispositivo_id": registro_sensor.dispositivo.dispositivo_id,
            "registro_sensor_id": registro_sensor.id,
            "external_id": registro_sensor.external_id,
            "timestamp_sensor": registro_sensor.timestamp_sensor.isoformat(),
            "raw_payload": registro_sensor.raw_payload,
        }
    )
    return metadata


def build_fuente_emision(dispositivo, tipo, payload):
    fuente = payload.get("fuente_emision") or payload.get("source")
    if fuente:
        return str(fuente).strip()
    tipo_label = dict(LecturaSensor.Tipo.choices).get(tipo, tipo)
    return f"{dispositivo.nombre} - {tipo_label}"


def create_registro_emision_from_sensor(registro_sensor, payload):
    factor = registro_sensor.factor_emision_usado or Decimal("0")
    if factor <= 0:
        return None

    return create_environmental_record(
        {
        "obra": registro_sensor.obra,
        "etapa": registro_sensor.etapa,
        "categoria": CATEGORIA_POR_TIPO.get(
            registro_sensor.tipo,
            RegistroEmision.Categoria.OTROS,
        ),
        "fuente_emision": build_fuente_emision(
            registro_sensor.dispositivo,
            registro_sensor.tipo,
            payload,
        ),
        "cantidad": registro_sensor.valor,
        "unidad": registro_sensor.unidad,
        "factor_emision": factor,
        "fecha": registro_sensor.timestamp_sensor.date(),
        "identificador_externo": registro_sensor.external_id,
        "metadata": build_emission_metadata(registro_sensor, payload),
        "observaciones": "Registro generado automaticamente desde sensor IoT.",
        "estado_validacion": RegistroEmision.EstadoValidacion.VALIDADO,
        },
        organizacion=registro_sensor.organizacion,
        tipo_ingreso=RegistroEmision.TipoIngreso.SENSOR_IOT,
        fuente_ingreso=registro_sensor.dispositivo.dispositivo_id,
    )


@transaction.atomic
def procesar_lectura_sensor(payload):
    dispositivo = resolve_device(payload)
    tipo = normalizar_tipo_sensor(payload.get("type") or payload.get("tipo"))
    valor = decimal_from_payload(payload.get("value") if "value" in payload else payload.get("valor"))
    factor = resolve_factor(payload, dispositivo, tipo)
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
        factor_catalogo=factor,
        factor_emision_usado=factor.factor_emision if factor else LecturaSensor.FACTORES_CO2E.get(tipo, Decimal("0")),
        timestamp_sensor=timestamp,
        metadata=payload.get("metadata") or {},
        raw_payload=sanitize_payload(payload),
    )

    if should_create_emission(payload, tipo, factor):
        try:
            registro_emision = create_registro_emision_from_sensor(registro, payload)
            if registro_emision:
                registro.registro_emision = registro_emision
                registro.estado_procesamiento = RegistroSensor.EstadoProcesamiento.CONSOLIDADO
                registro.save(update_fields=["registro_emision", "estado_procesamiento"])
            else:
                registro.estado_procesamiento = RegistroSensor.EstadoProcesamiento.SOLO_TELEMETRIA
                registro.save(update_fields=["estado_procesamiento"])
        except Exception as exc:
            registro.estado_procesamiento = RegistroSensor.EstadoProcesamiento.ERROR
            registro.error_procesamiento = str(exc)
            registro.save(update_fields=["estado_procesamiento", "error_procesamiento"])
            raise
    else:
        registro.estado_procesamiento = RegistroSensor.EstadoProcesamiento.SOLO_TELEMETRIA
        registro.save(update_fields=["estado_procesamiento"])

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
