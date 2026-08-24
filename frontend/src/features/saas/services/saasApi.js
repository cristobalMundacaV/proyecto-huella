import { api } from "@/shared/services/api";

export const getSaaSDashboard = async () => (await api.get("/saas/resumen/")).data;
export const getSaaSOrganization = async (id) => (await api.get(`/saas/organizaciones/${encodeURIComponent(id)}/`)).data;
export const updateSaaSOrganization = async (id, payload) => (await api.patch(`/saas/organizaciones/${encodeURIComponent(id)}/`, payload)).data;
export const deleteSaaSOrganization = async (id) => (await api.delete(`/saas/organizaciones/${encodeURIComponent(id)}/`)).data;
export const runSaaSAction = async (id, action, payload = {}) => (await api.post(`/saas/organizaciones/${encodeURIComponent(id)}/acciones/`, { action, ...payload })).data;
export const assignSaaSAdmin = async (id, payload) => (await api.post(`/saas/organizaciones/${encodeURIComponent(id)}/administradores/`, payload)).data;
export const getSaaSAudit = async () => (await api.get("/saas/auditoria/")).data;
export const createSaaSOrganization = async (payload) => (await api.post("/organizaciones/", payload)).data;
export const provisionSaaSOrganization = async (payload) => (await api.post("/saas/organizaciones/provisionar/", payload)).data;
