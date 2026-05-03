from .services.factor_classifier import (
    FACTOR_CATEGORIES,
    classify_factor,
    infer_categoria,
    normalize_categoria,
    normalize_key,
    normalize_text,
)


def normalize_activity_key(value):
    return normalize_key(value)


def format_activity_display_name(value):
    text = str(value or "").strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def infer_factor_category(*values):
    actividad = values[0] if values else ""
    unidad = values[1] if len(values) > 1 else None
    fuente = values[2] if len(values) > 2 else None
    return infer_categoria(actividad, unidad, fuente)


def normalize_factor_category(value, *fallback_values):
    return normalize_categoria(value) or infer_factor_category(*fallback_values)


def strip_accents(value):
    return normalize_text(value)
