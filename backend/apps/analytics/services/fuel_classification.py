from django.core.exceptions import ObjectDoesNotExist

from ..models import ActividadOperacional


STATIONARY_DESTINATIONS = {
    "generador": "El combustible fue destinado a un generador.",
    "calefaccion": "El combustible fue destinado a calefacción.",
}

MOBILE_DESTINATIONS = {
    "vehiculo": "El combustible fue destinado a un vehículo.",
}

AMBIGUOUS_DESTINATIONS = {
    "maquinaria",
    "equipo_menor",
    "otro",
}

FUEL_FLOWS = {
    "combustible",
    "combustible_estacionario",
    "combustible_movil",
}


def classify_fuel(destination, declared_flow=None):
    destination = str(destination or "").strip().casefold()
    declared_flow = str(declared_flow or "").strip().casefold()

    if destination in STATIONARY_DESTINATIONS:
        category = "combustion_estacionaria"
        reason = STATIONARY_DESTINATIONS[destination]
    elif destination in MOBILE_DESTINATIONS:
        category = "combustion_movil"
        reason = MOBILE_DESTINATIONS[destination]
    elif destination in AMBIGUOUS_DESTINATIONS:
        return {
            "estado": "requiere_clasificacion",
            "categoria": None,
            "alcance": 1,
            "razon": (
                f"El destino {destination} no permite determinar de forma segura "
                "si la fuente es móvil o estacionaria."
            ),
            "regla": f"destino_operacional={destination}",
        }
    else:
        return {
            "estado": "requiere_clasificacion",
            "categoria": None,
            "alcance": 1,
            "razon": "El uso del combustible no tiene una clasificación ambiental segura.",
            "regla": f"destino_operacional={destination or 'sin_clasificar'}",
        }

    expected_flow = {
        "combustion_estacionaria": "combustible_estacionario",
        "combustion_movil": "combustible_movil",
    }[category]
    if declared_flow in FUEL_FLOWS and declared_flow not in {
        "combustible",
        expected_flow,
    }:
        return {
            "estado": "requiere_revision",
            "categoria": category,
            "alcance": 1,
            "razon": (
                f"El destino indica {category.replace('_', ' ')}, pero el registro "
                f"histórico declara {declared_flow}."
            ),
            "regla": f"destino_operacional={destination}",
        }

    return {
        "estado": "clasificado",
        "categoria": category,
        "alcance": 1,
        "razon": reason,
        "regla": f"destino_operacional={destination}",
    }


def activity_fuel_classification(activity):
    metadata = activity.metadata if isinstance(activity.metadata, dict) else {}
    classification = metadata.get("clasificacion_ambiental")
    if isinstance(classification, dict):
        return classification

    if activity.tipo == ActividadOperacional.Tipo.TRANSPORTE:
        vehicle = activity_vehicle(activity)
        if vehicle is None:
            return {
                "estado": "requiere_clasificacion",
                "categoria": None,
                "alcance": 1,
                "razon": "La actividad de transporte no tiene un vehiculo asociado.",
                "regla": "actividad.tipo=transporte;viaje.vehiculo",
            }
        if not str(vehicle.combustible or "").strip():
            return {
                "estado": "requiere_clasificacion",
                "categoria": None,
                "alcance": 1,
                "razon": "El vehiculo asociado al viaje no informa combustible.",
                "regla": "actividad.tipo=transporte;viaje.vehiculo.combustible",
            }
        return {
            "estado": "clasificado",
            "categoria": "combustion_movil",
            "alcance": 1,
            "razon": "El combustible corresponde al vehiculo asociado al viaje.",
            "regla": "actividad.tipo=transporte;viaje.vehiculo",
        }

    try:
        record = activity.registro_flujo_ambiental
    except ObjectDoesNotExist:
        return None
    if record.flujo not in FUEL_FLOWS:
        return None
    return classify_fuel(record.destino_operacional, declared_flow=record.flujo)


def activity_fuel_type(activity):
    if activity.tipo == ActividadOperacional.Tipo.TRANSPORTE:
        vehicle = activity_vehicle(activity)
        return str(vehicle.combustible or "").strip().casefold() if vehicle else ""
    try:
        record = activity.registro_flujo_ambiental
    except ObjectDoesNotExist:
        return ""
    if record.flujo not in FUEL_FLOWS:
        return ""
    return str(record.tipo_recurso or "").strip().casefold()


def activity_vehicle(activity):
    """Resolve the real vehicle specialization without fabricating transport data."""
    try:
        journey = activity.viaje
    except ObjectDoesNotExist:
        journey = None
    if journey is not None:
        return journey.vehiculo

    asset = activity.activos.filter(tipo="vehiculo").select_related("vehiculo").first()
    if asset is None:
        return None
    try:
        return asset.vehiculo
    except ObjectDoesNotExist:
        return None
