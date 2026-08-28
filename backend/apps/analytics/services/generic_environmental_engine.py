from ..policies.construction_flows_v1 import capture_completeness
from ..policies.environmental_engine import classify_environmental_context
from ..selectors.environmental_engine import (
    activity_environmental_record,
    activity_provenance,
    usable_observation_count,
)
from .fuel_classification import activity_fuel_classification
from .methodology_selector import select_methodology


def _eligibility_projection(activity):
    selection = select_methodology(activity)
    selected = selection.get("seleccion")
    trace = None
    if selected:
        eligibility = selected["elegibilidad"]
        trace = {
            "methodology_version_id": selected["version_metodologia"].id,
            "formula_id": selected["formula"].id,
            "factor_version_id": (
                eligibility["factor_version"].id
                if eligibility.get("factor_version")
                else None
            ),
            "input_observation_ids": sorted(
                item[1].id for item in eligibility["inputs"].values()
            ),
            "warnings": list(eligibility["advertencias"]),
        }
    return {
        "state": selection["estado"],
        "reason": selection["razon"],
        "selected": trace,
        "discarded": list(selection["descartados"]),
    }


def project_environmental_activity(
    activity, *, domain_contract=None, include_eligibility=True
):
    environmental_record = activity_environmental_record(activity)
    fuel_classification = activity_fuel_classification(activity)
    classification = classify_environmental_context(
        fuel_classification=fuel_classification,
        declared_flow=(environmental_record.flujo if environmental_record else None),
        declared_domain=(domain_contract.key if domain_contract else None),
    )
    capture = (
        capture_completeness(activity, domain_contract)
        if domain_contract
        else {
            "estado": (
                "completo" if usable_observation_count(activity) else "incompleto"
            ),
            "faltantes": [] if usable_observation_count(activity) else ["observacion"],
            "elegibilidad_calculo": "delegada",
        }
    )
    return {
        "activity_id": activity.id,
        "organization_id": activity.organizacion_id,
        "work_id": activity.obra_id,
        "capture": capture,
        "classification": {
            "state": classification.state,
            "category": classification.category,
            "reason": classification.reason,
            "source": classification.source,
        },
        "environmental_context": {
            "record_id": environmental_record.id if environmental_record else None,
            "flow": environmental_record.flujo if environmental_record else None,
            "granularity": (
                environmental_record.granularidad if environmental_record else None
            ),
        },
        "provenance": activity_provenance(activity),
        "eligibility": (
            _eligibility_projection(activity)
            if include_eligibility
            else {"state": "no_evaluada", "reason": "Evaluacion no solicitada."}
        ),
        "calculation": None,
    }
