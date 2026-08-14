from decimal import Decimal


def compare_values(indicator, current, reference, comparable=None):
    if reference is None:
        return {"estado": "sin_base", "valor_actual": current, "valor_referencia": None, "calidad_comparacion": "sin_base"}
    difference = Decimal(current) - Decimal(reference)
    percentage = (difference / abs(Decimal(reference)) * Decimal("100")) if reference else None
    if difference == 0 or indicator.direccion_deseable == "neutral":
        direction = "estable"
    elif indicator.direccion_deseable == "menor_es_mejor":
        direction = "mejor" if difference < 0 else "peor"
    else:
        direction = "mejor" if difference > 0 else "peor"
    return {
        "estado": direction, "valor_actual": current, "valor_referencia": reference,
        "diferencia_absoluta": difference, "diferencia_porcentual": percentage,
        "direccion": direction, "periodo_comparado": comparable.pk if comparable else None,
        "calidad_comparacion": "comparable" if comparable else "referencia_directa",
    }
