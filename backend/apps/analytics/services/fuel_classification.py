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

    try:
        record = activity.registro_flujo_ambiental
    except ObjectDoesNotExist:
        return None
    if record.flujo not in FUEL_FLOWS:
        return None
    return classify_fuel(record.destino_operacional, declared_flow=record.flujo)
from django.core.exceptions import ObjectDoesNotExist

