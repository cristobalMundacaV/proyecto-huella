"""Typed, deterministic requirement schema for MaterialApplicationProfile (MI-01A).

Only safe, explicit operators are allowed: numeric (eq/gte/lte/range),
categorical (equals/one_of) and boolean (is_true/is_false). No arbitrary
Python, no eval(), no dynamic expressions. Unit handling for numeric
requirements reuses unit_conversion.py exclusively; incompatible dimensions
are rejected rather than silently invented.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from .unit_conversion import UnitConversionError, convert_value

REQUIREMENT_TYPES = {"numeric", "categorical", "boolean"}

OPERATORS_BY_TYPE = {
    "numeric": {"eq", "gte", "lte", "range"},
    "categorical": {"equals", "one_of"},
    "boolean": {"is_true", "is_false"},
}


def _as_decimal(value, field_name):
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"El campo '{field_name}' debe ser numérico.")


def _validate_numeric_units_compatible(min_unit, max_unit):
    if not min_unit or not max_unit or min_unit == max_unit:
        return
    try:
        convert_value(Decimal("1"), min_unit, max_unit)
    except UnitConversionError as exc:
        raise ValidationError(
            f"Unidad incompatible en el rango del requisito: {exc}"
        )


def validate_requirement(raw, index=None):
    """Validate and normalize a single requirement dict."""

    label = f"Requisito #{index}" if index is not None else "Requisito"
    if not isinstance(raw, dict):
        raise ValidationError(f"{label}: debe ser un objeto.")

    key = raw.get("key")
    if not isinstance(key, str) or not key.strip():
        raise ValidationError(f"{label}: 'key' es obligatorio y debe ser texto.")

    req_type = raw.get("type")
    if req_type not in REQUIREMENT_TYPES:
        raise ValidationError(
            f"{label} ({key}): tipo inválido. Use numeric, categorical o boolean."
        )

    operator = raw.get("operator")
    allowed_operators = OPERATORS_BY_TYPE[req_type]
    if operator not in allowed_operators:
        raise ValidationError(
            f"{label} ({key}): operador '{operator}' inválido para tipo {req_type}. "
            f"Operadores permitidos: {sorted(allowed_operators)}."
        )

    critical = raw.get("critical", True)
    if not isinstance(critical, bool):
        raise ValidationError(f"{label} ({key}): 'critical' debe ser booleano.")

    normalized = {
        "key": key.strip(),
        "label": str(raw.get("label", "")).strip(),
        "type": req_type,
        "operator": operator,
        "critical": critical,
    }

    if req_type == "numeric":
        unit = raw.get("unit")
        if unit is not None and not isinstance(unit, str):
            raise ValidationError(f"{label} ({key}): 'unit' debe ser texto o nulo.")
        if operator == "range":
            if "min" not in raw or "max" not in raw:
                raise ValidationError(
                    f"{label} ({key}): el operador range requiere 'min' y 'max'."
                )
            min_value = _as_decimal(raw["min"], "min")
            max_value = _as_decimal(raw["max"], "max")
            min_unit = raw.get("min_unit", unit)
            max_unit = raw.get("max_unit", unit)
            if min_unit is not None and not isinstance(min_unit, str):
                raise ValidationError(f"{label} ({key}): 'min_unit' debe ser texto o nulo.")
            if max_unit is not None and not isinstance(max_unit, str):
                raise ValidationError(f"{label} ({key}): 'max_unit' debe ser texto o nulo.")
            _validate_numeric_units_compatible(min_unit, max_unit)
            if min_value >= max_value:
                raise ValidationError(
                    f"{label} ({key}): 'min' debe ser menor que 'max'."
                )
            normalized.update(
                {
                    "min": str(min_value),
                    "max": str(max_value),
                    "min_unit": min_unit,
                    "max_unit": max_unit,
                }
            )
        else:
            if "value" not in raw:
                raise ValidationError(
                    f"{label} ({key}): el operador {operator} requiere 'value'."
                )
            value = _as_decimal(raw["value"], "value")
            normalized.update({"value": str(value), "unit": unit})

    elif req_type == "categorical":
        if operator == "equals":
            value = raw.get("value")
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(
                    f"{label} ({key}): el operador equals requiere 'value' textual."
                )
            normalized["value"] = value.strip()
        else:  # one_of
            values = raw.get("values")
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(v, str) and v.strip() for v in values)
            ):
                raise ValidationError(
                    f"{label} ({key}): el operador one_of requiere 'values' como "
                    "lista no vacía de texto."
                )
            normalized["values"] = [v.strip() for v in values]

    else:  # boolean
        if "value" in raw and not isinstance(raw["value"], bool):
            raise ValidationError(f"{label} ({key}): 'value' debe ser booleano.")

    return normalized


def validate_requirements(raw_requirements):
    """Validate and normalize the full requirement list for a profile."""

    if raw_requirements is None:
        return []
    if not isinstance(raw_requirements, list):
        raise ValidationError("Los requisitos deben ser una lista.")

    normalized = []
    seen_keys = set()
    for index, raw in enumerate(raw_requirements):
        item = validate_requirement(raw, index)
        if item["key"] in seen_keys:
            raise ValidationError(
                f"Clave de requisito duplicada: '{item['key']}'."
            )
        seen_keys.add(item["key"])
        normalized.append(item)
    return normalized
