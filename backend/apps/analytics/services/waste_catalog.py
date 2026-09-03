from rest_framework.exceptions import ValidationError

from ..models import RegistroFlujoAmbiental


CONSTRUCTION_WASTE_CATALOG_VERSION = 1
CONSTRUCTION_WASTE_TYPES = (
    ("hormigon_ceramicos", "Hormigón, ladrillos y cerámicos"),
    ("madera", "Madera"),
    ("metales", "Metales"),
    ("vidrio", "Vidrio"),
    ("plasticos", "Plásticos"),
    ("papel_carton", "Papel y cartón"),
    ("yeso", "Yeso"),
    ("tierras_escombros", "Tierras y escombros"),
    ("mezclados_construccion", "Residuos mezclados de construcción"),
    ("aceites_lubricantes", "Aceites y lubricantes"),
    ("pinturas_solventes", "Pinturas y solventes"),
    ("envases_contaminados", "Envases contaminados"),
    ("baterias", "Baterías"),
    ("otro", "Otro"),
)

VALUED_WASTE_DESTINATIONS = frozenset(
    {
        RegistroFlujoAmbiental.DestinoOperacional.REUTILIZACION,
        RegistroFlujoAmbiental.DestinoOperacional.RECICLAJE,
        RegistroFlujoAmbiental.DestinoOperacional.VALORIZACION,
        RegistroFlujoAmbiental.DestinoOperacional.SUBPRODUCTO_REUTILIZADO,
    }
)

WASTE_INDICATOR_SERIES = {
    "masa_generada": {
        "codigo": "residuos-masa-generada",
        "nombre": "Masa de residuos generada",
        "unidad_base": "kg",
        "dimension": "masa",
        "destinos": "todos",
        "direccion_deseable": "menor_es_mejor",
    },
    "masa_valorizada": {
        "codigo": "residuos-masa-valorizada",
        "nombre": "Masa de residuos valorizada",
        "unidad_base": "kg",
        "dimension": "masa",
        "destinos": VALUED_WASTE_DESTINATIONS,
        "direccion_deseable": "mayor_es_mejor",
    },
    "tasa_valorizacion_masa": {
        "codigo": "residuos-tasa-valorizacion-masa",
        "nombre": "Tasa de valorización en masa",
        "unidad_base": "%",
        "dimension": "masa",
        "formula": "masa_valorizada / masa_generada * 100",
        "direccion_deseable": "mayor_es_mejor",
    },
    "volumen_generado": {
        "codigo": "residuos-volumen-generado",
        "nombre": "Volumen de residuos generado",
        "unidad_base": "m3",
        "dimension": "volumen",
        "destinos": "todos",
        "direccion_deseable": "menor_es_mejor",
    },
}


def construction_waste_types():
    return [
        {"value": value, "label": label, "catalog_version": CONSTRUCTION_WASTE_CATALOG_VERSION}
        for value, label in CONSTRUCTION_WASTE_TYPES
    ]


def is_valued_waste_destination(destination):
    return destination in VALUED_WASTE_DESTINATIONS


def validate_waste_dimensions(classification, waste_type, custom_detail=""):
    classifications = {
        value for value, _ in RegistroFlujoAmbiental.ClasificacionResiduo.choices
    }
    types = {value for value, _ in CONSTRUCTION_WASTE_TYPES}
    errors = {}
    if classification not in classifications:
        errors["clasificacion_residuo"] = "Selecciona si el residuo es peligroso o no peligroso."
    if waste_type not in types:
        errors["tipo_residuo"] = "Selecciona un tipo de residuo válido."
    if waste_type == "otro" and not str(custom_detail or "").strip():
        errors["tipo_residuo_otro"] = "Describe el tipo de residuo cuando seleccionas Otro."
    if waste_type != "otro" and custom_detail:
        errors["tipo_residuo_otro"] = "El detalle custom sólo corresponde al tipo Otro."
    if errors:
        raise ValidationError(errors)
