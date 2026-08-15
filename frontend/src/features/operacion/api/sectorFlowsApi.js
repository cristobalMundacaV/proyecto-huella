import { api } from "@/shared/services/api";
const base = (id) => `/organizaciones/${encodeURIComponent(id)}`;
export const getEnvironmentalPoints = async (id) => (await api.get(`${base(id)}/puntos-ambientales/`)).data;
export const createEnvironmentalPoint = async (id, data) => (await api.post(`${base(id)}/puntos-ambientales/`, data)).data;
export const getSectorRecords = async (id, params = {}) => (await api.get(`${base(id)}/flujos-ambientales/`, { params })).data;
export const createSectorRecord = async (id, data) => (await api.post(`${base(id)}/flujos-ambientales/`, data)).data;
export const getSectorIndicators = async (id, params = {}) => (await api.get(`${base(id)}/flujos-ambientales/indicadores/`, { params })).data;
