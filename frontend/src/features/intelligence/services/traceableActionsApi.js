import { api } from "@/shared/services/api";

function constructoraPath(id, path = "") {
  return `/constructoras/${encodeURIComponent(id)}${path}`;
}

export async function getTraceableActions(constructoraId) {
  return (await api.get(constructoraPath(constructoraId, "/acciones-ambientales/"))).data;
}

export async function createTraceableAction(constructoraId, payload) {
  return (await api.post(constructoraPath(constructoraId, "/acciones-ambientales/"), payload)).data;
}

export async function updateTraceableAction(constructoraId, actionId, payload) {
  return (await api.patch(constructoraPath(constructoraId, `/acciones-ambientales/${encodeURIComponent(actionId)}/`), payload)).data;
}

export async function deleteTraceableAction(constructoraId, actionId) {
  await api.delete(constructoraPath(constructoraId, `/acciones-ambientales/${encodeURIComponent(actionId)}/`));
}
