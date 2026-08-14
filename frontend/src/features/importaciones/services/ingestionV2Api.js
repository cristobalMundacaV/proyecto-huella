import { api } from "@/shared/services/api";

const root = (id) => `/organizaciones/${encodeURIComponent(id)}/ingestas`;
export const createIngesta = async (id, file, fuenteNombre) => { const data = new FormData(); data.append("archivo", file); data.append("fuente_nombre", fuenteNombre); return (await api.post(`${root(id)}/`, data)).data; };
export const analyzeIngesta = async (id, ingestaId) => (await api.post(`${root(id)}/${ingestaId}/analizar/`)).data;
export const saveMapping = async (id, ingestaId, mapeos) => (await api.post(`${root(id)}/${ingestaId}/mapeo/`, { nombre: "Viajes", mapeos })).data;
export const getPreview = async (id, ingestaId) => (await api.get(`${root(id)}/${ingestaId}/preview/`)).data;
export const confirmIngesta = async (id, ingestaId) => (await api.post(`${root(id)}/${ingestaId}/confirmar/`)).data;
export const getIngestas = async (id) => (await api.get(`${root(id)}/`)).data;
