import { api } from "@/shared/services/api";

function priorityPath(constructoraId, priorityId, suffix) {
  return `/environmental/decisions/priorities/${encodeURIComponent(constructoraId)}/${encodeURIComponent(priorityId)}/${suffix}/`;
}

export async function getDecisionActionPreview(constructoraId, priorityId) {
  return (await api.get(priorityPath(constructoraId, priorityId, "action-preview"))).data;
}

export async function createActionFromDecision(constructoraId, priorityId, payload) {
  return (await api.post(priorityPath(constructoraId, priorityId, "create-action"), payload)).data;
}
