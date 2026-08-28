from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import RutaOperacional, ViajeOperacional
from .capture import capture_observation
from ..selectors.transport import completed_journeys

CONCEPTS = {
    "distancia": ("distancia_recorrida_km", "km"),
    "carga": ("masa_transportada_t", "t"),
    "combustible": ("combustible_consumido_l", "L"),
}


def _value(journey, kind):
    observation = getattr(journey, f"observacion_{kind}")
    return observation.valor_numerico if observation else None


def journey_metrics(journey):
    distance, load, fuel = (
        _value(journey, key) for key in ("distancia", "carga", "combustible")
    )
    tkm = (
        distance * load
        if distance is not None
        and load is not None
        and journey.observacion_distancia.unidad == "km"
        and journey.observacion_carga.unidad == "t"
        else None
    )
    capacity = journey.vehiculo.capacidad_carga
    utilization = None
    if (
        load is not None
        and capacity is not None
        and capacity > 0
        and journey.observacion_carga.unidad == journey.vehiculo.unidad_capacidad_carga
    ):
        utilization = load / capacity * Decimal("100")
    return {
        "distancia_km": distance,
        "carga_t": load,
        "combustible_l": fuel,
        "toneladas_km": tkm,
        "utilizacion_carga_pct": utilization,
    }


def transport_indicators(organization, start=None, end=None, work=None):
    rows = completed_journeys(organization, start, end, work)
    total_km = loaded_km = empty_km = tonnes = tkm = fuel = Decimal("0")
    utilizations = []
    count = empty_count = 0
    route_empty = {}
    for journey in rows:
        count += 1
        values = journey_metrics(journey)
        distance = values["distancia_km"]
        if distance is not None:
            total_km += distance
            if journey.estado_carga == "vacio":
                empty_km += distance
            elif journey.estado_carga in {"cargado", "parcialmente_cargado"}:
                loaded_km += distance
        if journey.estado_carga == "vacio" and journey.tipo_trayecto == "retorno":
            empty_count += 1
            if journey.ruta_id:
                route_empty[journey.ruta.codigo] = (
                    route_empty.get(journey.ruta.codigo, 0) + 1
                )
        if values["carga_t"] is not None:
            tonnes += values["carga_t"]
        if values["toneladas_km"] is not None:
            tkm += values["toneladas_km"]
        if values["combustible_l"] is not None:
            fuel += values["combustible_l"]
        if values["utilizacion_carga_pct"] is not None:
            utilizations.append(values["utilizacion_carga_pct"])
    empty_pct = empty_km / total_km * Decimal("100") if total_km else None
    average = (
        sum(utilizations, Decimal("0")) / len(utilizations) if utilizations else None
    )
    opportunities = []
    if empty_count:
        opportunities.append(
            {
                "tipo": "retornos_vacios",
                "severidad": "informativa",
                "valor": empty_count,
                "unidad": "viajes",
            }
        )
    if average is not None:
        opportunities.append(
            {
                "tipo": "utilizacion_capacidad",
                "severidad": "informativa",
                "valor": average,
                "unidad": "%",
            }
        )
    for route, occurrences in route_empty.items():
        if occurrences > 1:
            opportunities.append(
                {
                    "tipo": "ruta_repetida_retorno_vacio",
                    "severidad": "informativa",
                    "ruta": route,
                    "valor": occurrences,
                    "unidad": "viajes",
                }
            )
    return {
        "km_totales": total_km,
        "km_con_carga": loaded_km,
        "km_sin_carga": empty_km,
        "porcentaje_km_vacios": empty_pct,
        "tonelaje_transportado": tonnes,
        "toneladas_km": tkm,
        "utilizacion_media_capacidad": average,
        "combustible_total": fuel,
        "numero_viajes": count,
        "retornos_vacios": empty_count,
        "oportunidades": opportunities,
    }


@transaction.atomic
def save_journey_observations(
    journey, source, values, evidence=None, evidence_version=None
):
    if source and source.organizacion_id != journey.organizacion_id:
        raise ValidationError("La fuente pertenece a otra organizacion.")
    for kind, value in values.items():
        if value is None:
            continue
        concept, unit = CONCEPTS[kind]
        observation = capture_observation(
            channel="manual",
            organization=journey.organizacion,
            activity=journey.actividad,
            source=source,
            concept=concept,
            numeric_value=value,
            unit=unit,
            timestamp=journey.fecha_llegada or journey.fecha_salida,
            evidence=evidence,
            evidence_version=evidence_version,
        )
        setattr(journey, f"observacion_{kind}", observation)
    journey.save()
    return journey


def create_route(organization, data):
    route = RutaOperacional(organizacion=organization, **data)
    route.full_clean()
    route.save()
    return route


@transaction.atomic
def save_journey(instance, organization, data):
    values = {key: data.pop(key, None) for key in CONCEPTS}
    source = data.pop("fuente", None)
    for field, value in data.items():
        setattr(instance, field, value)
    instance.organizacion = organization
    instance.full_clean()
    instance.save()
    return save_journey_observations(instance, source, values) if source else instance
