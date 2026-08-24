import { api } from "@/shared/services/api";

export const getSaaSDashboard = async () => (await api.get("/saas/resumen/")).data;
export const getSaaSOrganization = async (id) => (await api.get(`/saas/organizaciones/${encodeURIComponent(id)}/`)).data;
export const updateSaaSOrganization = async (id, payload) => (await api.patch(`/saas/organizaciones/${encodeURIComponent(id)}/`, payload)).data;
export const runSaaSAction = async (id, action, payload = {}) => (await api.post(`/saas/organizaciones/${encodeURIComponent(id)}/acciones/`, { action, ...payload })).data;
export const getSaaSAudit = async () => (await api.get("/saas/auditoria/")).data;
export const createSaaSOrganization = async (payload) => (await api.post("/organizaciones/", payload)).data;
