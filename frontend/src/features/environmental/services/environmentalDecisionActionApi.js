import { api } from "@/shared/services/api";

function priorityPath(organizacionId, priorityId, suffix) {
  return `/environmental/decisions/priorities/${encodeURIComponent(organizacionId)}/${encodeURIComponent(priorityId)}/${suffix}/`;
}

export async function getDecisionActionPreview(organizacionId, priorityId) {
  return (await api.get(priorityPath(organizacionId, priorityId, "action-preview"))).data;
}

export async function createActionFromDecision(organizacionId, priorityId, payload) {
  return (await api.post(priorityPath(organizacionId, priorityId, "create-action"), payload)).data;
}
