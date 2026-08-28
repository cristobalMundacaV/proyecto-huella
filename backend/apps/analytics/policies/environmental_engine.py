from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentalClassification:
    state: str
    category: str | None
    reason: str
    source: str


def classify_environmental_context(
    *, fuel_classification=None, declared_flow=None, declared_domain=None
):
    if fuel_classification:
        return EnvironmentalClassification(
            state=fuel_classification.get("estado", "requiere_clasificacion"),
            category=fuel_classification.get("categoria"),
            reason=fuel_classification.get("razon", "Clasificacion de combustible."),
            source="fuel_classification",
        )
    if declared_flow:
        return EnvironmentalClassification(
            state="clasificado",
            category=declared_flow,
            reason="La actividad posee un flujo ambiental declarado y validado.",
            source="environmental_flow_record",
        )
    if declared_domain:
        return EnvironmentalClassification(
            state="contextual",
            category=declared_domain,
            reason="La actividad coincide con un contrato operacional explicito.",
            source="domain_contract",
        )
    return EnvironmentalClassification(
        state="sin_clasificar",
        category=None,
        reason="No existe contexto ambiental confirmado para clasificar la actividad.",
        source="none",
    )
