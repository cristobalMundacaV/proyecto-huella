from ..policies.construction_flows_v1 import CONSTRUCTION_V1_FLOW_CONTRACTS
from .generic_environmental_engine import project_environmental_activity


def project_construction_activity(activity, flow_key, *, include_eligibility=True):
    contract = CONSTRUCTION_V1_FLOW_CONTRACTS[flow_key]
    return project_environmental_activity(
        activity,
        domain_contract=contract,
        include_eligibility=include_eligibility,
    )
