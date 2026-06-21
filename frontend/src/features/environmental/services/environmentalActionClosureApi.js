import { api } from "@/shared/services/api";

function actionPath(actionId, suffix) {
  return `/environmental/actions/${encodeURIComponent(actionId)}/${suffix}/`;
}

export async function getActionClosureStatus(actionId) {
  return (await api.get(actionPath(actionId, "closure-status"))).data;
}

export async function attachEvidenceToAction(actionId, payload) {
  return (await api.post(actionPath(actionId, "attach-evidence"), payload)).data;
}

export async function closeEnvironmentalAction(actionId, payload) {
  return (await api.post(actionPath(actionId, "close"), payload)).data;
}
