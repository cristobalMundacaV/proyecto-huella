import { api } from "@/shared/services/api";

function constructoraPath(constructoraId, path = "") {
  return `/constructoras/${encodeURIComponent(constructoraId)}${path}`;
}

export async function getEnvironmentalDocuments(constructoraId) {
  return (await api.get(constructoraPath(constructoraId, "/documentos-ambientales/"))).data;
}

export async function createEnvironmentalDocument(constructoraId, payload) {
  return (await api.post(constructoraPath(constructoraId, "/documentos-ambientales/"), payload)).data;
}

export async function updateEnvironmentalDocument(constructoraId, documentId, payload) {
  return (await api.patch(constructoraPath(constructoraId, `/documentos-ambientales/${encodeURIComponent(documentId)}/`), payload)).data;
}

export async function deleteEnvironmentalDocument(constructoraId, documentId) {
  await api.delete(constructoraPath(constructoraId, `/documentos-ambientales/${encodeURIComponent(documentId)}/`));
}

export async function getEnvironmentalVariables(constructoraId) {
  return (await api.get(constructoraPath(constructoraId, "/variables-ambientales/"))).data;
}

export async function createEnvironmentalVariable(constructoraId, payload) {
  return (await api.post(constructoraPath(constructoraId, "/variables-ambientales/"), payload)).data;
}

export async function updateEnvironmentalVariable(constructoraId, variableId, payload) {
  return (await api.patch(constructoraPath(constructoraId, `/variables-ambientales/${encodeURIComponent(variableId)}/`), payload)).data;
}

export async function getEnvironmentalLimits(constructoraId) {
  return (await api.get(constructoraPath(constructoraId, "/limites-ambientales/"))).data;
}

export async function createEnvironmentalLimit(constructoraId, payload) {
  return (await api.post(constructoraPath(constructoraId, "/limites-ambientales/"), payload)).data;
}

export async function updateEnvironmentalLimit(constructoraId, limitId, payload) {
  return (await api.patch(constructoraPath(constructoraId, `/limites-ambientales/${encodeURIComponent(limitId)}/`), payload)).data;
}

export async function getComplianceAlerts(constructoraId) {
  return (await api.get(constructoraPath(constructoraId, "/alertas-cumplimiento/"))).data;
}

export async function updateComplianceAlert(constructoraId, alertId, payload) {
  return (await api.patch(constructoraPath(constructoraId, `/alertas-cumplimiento/${encodeURIComponent(alertId)}/`), payload)).data;
}

export async function getEnvironmentalComplianceSummary(constructoraId) {
  return (await api.get(constructoraPath(constructoraId, "/cumplimiento-ambiental/resumen/"))).data;
}
