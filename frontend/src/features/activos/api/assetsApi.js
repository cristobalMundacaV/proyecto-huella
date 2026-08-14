import { api } from "@/shared/services/api";
const base = (id) => `/organizaciones/${encodeURIComponent(id)}`;
export const getAssets = async (id, params={}) => (await api.get(`${base(id)}/activos/`, {params})).data;
export const createAsset = async (id, data) => (await api.post(`${base(id)}/activos/`, data)).data;
export const updateAsset = async (id, assetId, data) => (await api.patch(`${base(id)}/activos/${assetId}/`, data)).data;
export const createMaintenance = async (id, assetId, data) => (await api.post(`${base(id)}/activos/${assetId}/mantenimientos/`, data)).data;
export const createCondition = async (id, assetId, data) => (await api.post(`${base(id)}/activos/${assetId}/condiciones/`, data)).data;
