from decimal import Decimal, InvalidOperation


class UnitConversionError(ValueError):
    """Raised when a deterministic physical conversion is unavailable."""


UNIT_ALIASES = {
    "l": "L",
    "litro": "L",
    "litros": "L",
    "litros diesel": "L",
    "m3": "m3",
    "m³": "m3",
    "kg": "kg",
    "t": "t",
    "ton": "t",
    "tonelada": "t",
    "toneladas": "t",
}

UNIT_DIMENSIONS = {
    "L": "volumen",
    "m3": "volumen",
    "kg": "masa",
    "t": "masa",
}

CONVERSION_FACTORS = {
    ("L", "m3"): Decimal("0.001"),
    ("m3", "L"): Decimal("1000"),
    ("kg", "t"): Decimal("0.001"),
    ("t", "kg"): Decimal("1000"),
}


def canonicalize_unit(unit):
    raw_unit = str(unit or "").strip()
    canonical = UNIT_ALIASES.get(raw_unit.casefold())
    if canonical is None:
        display_unit = raw_unit or "(vacía)"
        raise UnitConversionError(f"Unidad desconocida: {display_unit}.")
    return canonical


def convert_value(value, source_unit, target_unit):
    try:
        original_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise UnitConversionError(f"Valor numérico inválido: {value}.") from error

    raw_source = str(source_unit or "").strip()
    raw_target = str(target_unit or "").strip()
    if raw_source and raw_source.casefold() == raw_target.casefold():
        canonical = UNIT_ALIASES.get(raw_source.casefold(), raw_target)
        return {
            "valor_original": original_value,
            "unidad_original": canonical,
            "valor_normalizado": original_value,
            "unidad_normalizada": canonical,
            "conversion_aplicada": False,
            "regla": None,
            "factor_conversion": Decimal("1"),
        }

    source = canonicalize_unit(raw_source)
    target = canonicalize_unit(raw_target)
    if source == target:
        factor = Decimal("1")
        converted_value = original_value
        conversion_applied = False
        rule = None
    else:
        factor = CONVERSION_FACTORS.get((source, target))
        if factor is None or UNIT_DIMENSIONS[source] != UNIT_DIMENSIONS[target]:
            raise UnitConversionError(
                "Unidad incompatible: no existe una conversión segura "
                f"de {source} a {target}."
            )
        converted_value = original_value * factor
        conversion_applied = True
        rule = f"{source} → {target}"

    return {
        "valor_original": original_value,
        "unidad_original": source,
        "valor_normalizado": converted_value,
        "unidad_normalizada": target,
        "conversion_aplicada": conversion_applied,
        "regla": rule,
        "factor_conversion": factor,
    }
