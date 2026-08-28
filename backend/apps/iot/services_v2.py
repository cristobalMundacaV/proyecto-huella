from django.db import transaction
from django.utils import timezone

from apps.analytics.models import FuenteDatos, Observacion
from apps.analytics.services.capture import capture_observation

from .models import CalibracionSensor, DispositivoSensor, LecturaSensorV2


def actualizar_estado_tecnico(sensor):
    latest = sensor.calibraciones.order_by("-fecha").first()
    if (
        latest
        and latest.fecha_proxima_calibracion
        and latest.fecha_proxima_calibracion < timezone.localdate()
    ):
        if sensor.estado != DispositivoSensor.Estado.CALIBRACION_VENCIDA:
            sensor.estado = DispositivoSensor.Estado.CALIBRACION_VENCIDA
            sensor.save(update_fields=["estado", "updated_at"])
    return sensor


@transaction.atomic
def registrar_calibracion(sensor, datos):
    calibracion = CalibracionSensor(sensor=sensor, **datos)
    calibracion.full_clean()
    calibracion.save()
    if calibracion.resultado == CalibracionSensor.Resultado.RECHAZADA:
        sensor.estado = DispositivoSensor.Estado.REQUIERE_REVISION
    elif (
        calibracion.fecha_proxima_calibracion
        and calibracion.fecha_proxima_calibracion < timezone.localdate()
    ):
        sensor.estado = DispositivoSensor.Estado.CALIBRACION_VENCIDA
    elif sensor.estado in {
        DispositivoSensor.Estado.REQUIERE_REVISION,
        DispositivoSensor.Estado.CALIBRACION_VENCIDA,
    }:
        sensor.estado = DispositivoSensor.Estado.OPERATIVO
    sensor.save(update_fields=["estado", "updated_at"])
    return calibracion


@transaction.atomic
def registrar_lectura(sensor, datos):
    sensor = actualizar_estado_tecnico(sensor)
    actividad = datos.get("actividad")
    if actividad and actividad.organizacion_id != sensor.organizacion_id:
        raise ValueError("La actividad pertenece a otra organizacion.")
    fuente = sensor.fuente_datos
    if not fuente:
        fuente, _ = FuenteDatos.objects.get_or_create(
            organizacion=sensor.organizacion,
            nombre=f"Sensor {sensor.dispositivo_id}",
            defaults={
                "tipo": FuenteDatos.Tipo.SENSOR,
                "identificador_externo": sensor.dispositivo_id,
            },
        )
        sensor.fuente_datos = fuente
        sensor.save(update_fields=["fuente_datos", "updated_at"])
    calidad = (
        LecturaSensorV2.CalidadTecnica.VALIDA
        if sensor.estado == DispositivoSensor.Estado.OPERATIVO
        else LecturaSensorV2.CalidadTecnica.REQUIERE_REVISION
    )
    lectura = LecturaSensorV2(sensor=sensor, calidad_tecnica=calidad, **datos)
    lectura.full_clean()
    lectura.save()
    observacion = capture_observation(
        channel="sensor",
        organization=sensor.organizacion,
        activity=actividad,
        source=fuente,
        concept=lectura.concepto,
        numeric_value=lectura.valor_numerico,
        unit=lectura.unidad,
        timestamp=lectura.timestamp,
        state=(
            Observacion.Estado.PENDIENTE
            if calidad == LecturaSensorV2.CalidadTecnica.REQUIERE_REVISION
            else Observacion.Estado.VALIDADA
        ),
    )
    lectura.observacion = observacion
    lectura.save(update_fields=["observacion"])
    sensor.last_seen_at = lectura.timestamp
    sensor.save(update_fields=["last_seen_at", "updated_at"])
    return lectura
