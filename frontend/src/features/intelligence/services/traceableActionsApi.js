import { api } from "@/shared/services/api";

function organizacionPath(id, path = "") {
  return `/organizaciones/${encodeURIComponent(id)}${path}`;
}

export async function getTraceableActionsSummary(organizacionId) {
  return (await api.get(organizacionPath(organizacionId, "/acciones-ambientales/resumen/"))).data;
}

export async function getTraceableActions(organizacionId) {
  return (await api.get(organizacionPath(organizacionId, "/acciones-ambientales/"))).data;
}

export async function createTraceableAction(organizacionId, payload) {
  return (await api.post(organizacionPath(organizacionId, "/acciones-ambientales/"), payload)).data;
}

export async function updateTraceableAction(organizacionId, actionId, payload) {
  return (await api.patch(organizacionPath(organizacionId, `/acciones-ambientales/${encodeURIComponent(actionId)}/`), payload)).data;
}

export async function deleteTraceableAction(organizacionId, actionId) {
  await api.delete(organizacionPath(organizacionId, `/acciones-ambientales/${encodeURIComponent(actionId)}/`));
}
