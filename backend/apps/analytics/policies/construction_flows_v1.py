from dataclasses import dataclass

from django.core.exceptions import ObjectDoesNotExist

from ..models import ActividadOperacional, Observacion


@dataclass(frozen=True)
class ConstructionFlowContract:
    key: str
    activity_types: frozenset[str]
    required_observation_groups: tuple[frozenset[str], ...]
    optional_observations: frozenset[str]
    accepted_units: tuple[str, ...]
    required_context: str
    typical_evidence: tuple[str, ...]
    lifecycle_optional: bool = False


CONSTRUCTION_V1_FLOW_CONTRACTS = {
    "combustibles": ConstructionFlowContract(
        key="combustibles",
        activity_types=frozenset(
            {
                ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE,
                ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE_ESTACIONARIO,
            }
        ),
        required_observation_groups=(
            frozenset({"combustible_consumido", "combustible_consumido_l"}),
        ),
        optional_observations=frozenset({"horas_operacion", "distancia_recorrida_km"}),
        accepted_units=("L", "m3", "kg", "t"),
        required_context="environmental_flow",
        typical_evidence=("factura_combustible", "documento_origen"),
    ),
    "maquinaria": ConstructionFlowContract(
        key="maquinaria",
        activity_types=frozenset({ActividadOperacional.Tipo.OPERACION_MAQUINARIA}),
        required_observation_groups=(frozenset({"horas_operacion"}),),
        optional_observations=frozenset(
            {"combustible_consumido", "combustible_consumido_l", "rendimiento"}
        ),
        accepted_units=("h", "L", "m3"),
        required_context="asset",
        typical_evidence=("registro_maquinaria", "factura_combustible"),
    ),
    "transporte": ConstructionFlowContract(
        key="transporte",
        activity_types=frozenset({ActividadOperacional.Tipo.TRANSPORTE}),
        required_observation_groups=(frozenset({"distancia_recorrida_km"}),),
        optional_observations=frozenset(
            {"masa_transportada_t", "combustible_consumido_l"}
        ),
        accepted_units=("km", "t", "kg", "L"),
        required_context="journey",
        typical_evidence=("documento_transporte", "guia_despacho"),
    ),
    "materiales": ConstructionFlowContract(
        key="materiales",
        activity_types=frozenset({ActividadOperacional.Tipo.MOVIMIENTO_MATERIAL}),
        required_observation_groups=(),
        optional_observations=frozenset({"cantidad_material"}),
        accepted_units=("material.unidad_base",),
        required_context="material_event",
        typical_evidence=(
            "factura_material",
            "guia_despacho",
            "ficha_tecnica_material",
        ),
        lifecycle_optional=True,
    ),
    "energia": ConstructionFlowContract(
        key="energia",
        activity_types=frozenset(
            {
                ActividadOperacional.Tipo.CONSUMO_ENERGIA,
                ActividadOperacional.Tipo.GENERACION_ENERGIA,
            }
        ),
        required_observation_groups=(
            frozenset({"consumo_energia", "energia_generada"}),
        ),
        optional_observations=frozenset({"energia_autoconsumida", "energia_exportada"}),
        accepted_units=("kWh", "MWh"),
        required_context="environmental_flow",
        typical_evidence=("boleta_electrica", "registro_produccion"),
    ),
    "agua": ConstructionFlowContract(
        key="agua",
        activity_types=frozenset({ActividadOperacional.Tipo.CONSUMO_AGUA}),
        required_observation_groups=(frozenset({"consumo_agua"}),),
        optional_observations=frozenset({"caudal", "lectura_medidor"}),
        accepted_units=("L", "m3"),
        required_context="environmental_flow",
        typical_evidence=("documento_origen", "registro_produccion"),
    ),
    "residuos": ConstructionFlowContract(
        key="residuos",
        activity_types=frozenset({ActividadOperacional.Tipo.GESTION_RESIDUO}),
        required_observation_groups=(frozenset({"cantidad_residuo"}),),
        optional_observations=frozenset({"tipo_residuo", "peligrosidad"}),
        accepted_units=("kg", "t", "m3"),
        required_context="environmental_flow",
        typical_evidence=("registro_retiro_residuos", "ticket_pesaje"),
    ),
}


def _has_context(activity, context):
    if context == "asset":
        return activity.activos.exists()
    relation = {
        "journey": "viaje",
        "material_event": "evento_material",
        "environmental_flow": "registro_flujo_ambiental",
    }.get(context)
    if not relation:
        return True
    try:
        getattr(activity, relation)
    except ObjectDoesNotExist:
        return False
    return True


def capture_completeness(activity, contract):
    missing = []
    if activity.tipo not in contract.activity_types:
        missing.append("actividad_tipo")
    if not _has_context(activity, contract.required_context):
        missing.append(contract.required_context)
    observations = activity.observaciones.exclude(estado=Observacion.Estado.RECHAZADA)
    concepts = set(observations.values_list("concepto", flat=True))
    for alternatives in contract.required_observation_groups:
        if not concepts.intersection(alternatives):
            missing.append("observacion:" + "|".join(sorted(alternatives)))
    return {
        "estado": "completo" if not missing else "incompleto",
        "faltantes": missing,
        "elegibilidad_calculo": "delegada",
    }
