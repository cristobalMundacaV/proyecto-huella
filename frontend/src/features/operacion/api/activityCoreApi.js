import { api } from "@/shared/services/api";

const base = (id) => `/organizaciones/${encodeURIComponent(id)}`;
export const getActividades = async (id, params = {}) => (await api.get(`${base(id)}/actividades-operacionales/`, { params })).data;
export const getActividad = async (id, actividadId) => (await api.get(`${base(id)}/actividades-operacionales/${actividadId}/`)).data;
export const createActividad = async (id, payload) => (await api.post(`${base(id)}/actividades-operacionales/`, payload)).data;
export const getFuentes = async (id) => (await api.get(`${base(id)}/fuentes-datos/`)).data;
export const createFuente = async (id, payload) => (await api.post(`${base(id)}/fuentes-datos/`, payload)).data;
export const createObservacion = async (id, actividadId, payload) => (await api.post(`${base(id)}/actividades-operacionales/${actividadId}/observaciones/`, payload)).data;
