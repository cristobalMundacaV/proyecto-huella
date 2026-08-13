import { api } from "@/shared/services/api";

function organizacionPath(organizacionId, path = "") {
  return `/organizaciones/${encodeURIComponent(organizacionId)}${path}`;
}

export async function getEnvironmentalDocuments(organizacionId) {
  return (await api.get(organizacionPath(organizacionId, "/documentos-ambientales/"))).data;
}

export async function createEnvironmentalDocument(organizacionId, payload) {
  return (await api.post(organizacionPath(organizacionId, "/documentos-ambientales/"), payload)).data;
}

export async function updateEnvironmentalDocument(organizacionId, documentId, payload) {
  return (await api.patch(organizacionPath(organizacionId, `/documentos-ambientales/${encodeURIComponent(documentId)}/`), payload)).data;
}

export async function deleteEnvironmentalDocument(organizacionId, documentId) {
  await api.delete(organizacionPath(organizacionId, `/documentos-ambientales/${encodeURIComponent(documentId)}/`));
}

export async function getEnvironmentalVariables(organizacionId) {
  return (await api.get(organizacionPath(organizacionId, "/variables-ambientales/"))).data;
}

export async function createEnvironmentalVariable(organizacionId, payload) {
  return (await api.post(organizacionPath(organizacionId, "/variables-ambientales/"), payload)).data;
}

export async function updateEnvironmentalVariable(organizacionId, variableId, payload) {
  return (await api.patch(organizacionPath(organizacionId, `/variables-ambientales/${encodeURIComponent(variableId)}/`), payload)).data;
}

export async function getEnvironmentalLimits(organizacionId) {
  return (await api.get(organizacionPath(organizacionId, "/limites-ambientales/"))).data;
}

export async function createEnvironmentalLimit(organizacionId, payload) {
  return (await api.post(organizacionPath(organizacionId, "/limites-ambientales/"), payload)).data;
}

export async function updateEnvironmentalLimit(organizacionId, limitId, payload) {
  return (await api.patch(organizacionPath(organizacionId, `/limites-ambientales/${encodeURIComponent(limitId)}/`), payload)).data;
}

export async function getComplianceAlerts(organizacionId) {
  return (await api.get(organizacionPath(organizacionId, "/alertas-cumplimiento/"))).data;
}

export async function updateComplianceAlert(organizacionId, alertId, payload) {
  return (await api.patch(organizacionPath(organizacionId, `/alertas-cumplimiento/${encodeURIComponent(alertId)}/`), payload)).data;
}

export async function getEnvironmentalComplianceSummary(organizacionId) {
  return (await api.get(organizacionPath(organizacionId, "/cumplimiento-ambiental/resumen/"))).data;
}
