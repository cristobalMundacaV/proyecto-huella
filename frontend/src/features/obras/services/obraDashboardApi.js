import { api } from "@/shared/services/api";

function base(organizationId, workId) {
  return `/organizaciones/${encodeURIComponent(organizationId)}/obras/${encodeURIComponent(workId)}`;
}

export async function getObraDashboard(organizationId, workId, params = {}) {
  return (await api.get(`${base(organizationId, workId)}/dashboard-ambiental/`, { params })).data;
}

export async function getObraReadiness(organizationId, workId, params = {}) {
  return (await api.get(`${base(organizationId, workId)}/readiness-periodo/`, { params })).data;
}

function apiOrigin() {
  return api.defaults.baseURL || "/api";
}

export function obraReportPdfUrl(organizationId, workId, params = {}) {
  const query = new URLSearchParams(params).toString();
  return `${apiOrigin()}${base(organizationId, workId)}/informe-ambiental.pdf${query ? `?${query}` : ""}`;
}

export function obraReportExcelUrl(organizationId, workId, params = {}) {
  const query = new URLSearchParams(params).toString();
  return `${apiOrigin()}${base(organizationId, workId)}/informe-ambiental.xlsx${query ? `?${query}` : ""}`;
}
