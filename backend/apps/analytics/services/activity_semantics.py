import re
import unicodedata


def normalize_text(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    value = without_accents.lower()
    value = re.sub(r"[_\-\u2010-\u2015/]+", " ", value)
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _row_value(row, key):
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def _fields(row):
    categoria = normalize_text(_row_value(row, "categoria"))
    activity_key = normalize_text(
        _row_value(row, "activity_key") or _row_value(row, "actividad_key")
    )
    actividad = normalize_text(_row_value(row, "actividad"))
    unidad = normalize_text(_row_value(row, "unidad"))
    return categoria, activity_key, actividad, unidad


def is_diesel_activity(row):
    categoria, activity_key, actividad, _unidad = _fields(row)
    has_diesel = "diesel" in activity_key or "diesel" in actividad
    return has_diesel and (categoria in {"", "combustible"} or has_diesel)


def is_electricity_activity(row):
    categoria, activity_key, actividad, unidad = _fields(row)
    return (
        categoria == "electricidad"
        or "electricidad" in activity_key
        or "electricidad" in actividad
        or unidad == "kwh"
    )


def is_fuel_activity(row):
    categoria, activity_key, actividad, _unidad = _fields(row)
    return categoria == "combustible" or any(
        token in activity_key or token in actividad
        for token in ["diesel", "glp", "gas natural", "combustible", "combustion"]
    )


def is_transport_activity(row):
    categoria, activity_key, actividad, unidad = _fields(row)
    tokens = set(f"{activity_key} {actividad}".split())
    return (
        categoria == "transporte"
        or bool(tokens.intersection({"camion", "barco", "tren", "avion", "bus", "vehiculo"}))
        or "t km" in unidad
        or "km pasajero" in unidad
    )
