import { api } from "@/shared/services/api";

const root = (id) => `/organizaciones/${encodeURIComponent(id)}/ingestas`;
export const createIngesta = async (id, file, fuenteNombre, options = {}) => { const data = new FormData(); data.append("archivo", file); data.append("fuente_nombre", fuenteNombre); data.append("tipo_ingesta", "tabular"); data.append("destino_operacional", options.destino || "actividad_generica"); if (options.flujo) data.append("flujo", options.flujo); return (await api.post(`${root(id)}/`, data)).data; };
export const analyzeIngesta = async (id, ingestaId) => (await api.post(`${root(id)}/${ingestaId}/analizar/`)).data;
export const saveMapping = async (id, ingestaId, mapeos, options = {}) => (await api.post(`${root(id)}/${ingestaId}/mapeo/`, { nombre: "Mapeo ambiental", mapeos, destino_operacional: options.destino, flujo: options.flujo, contexto: options.contexto || {} })).data;
export const getPreview = async (id, ingestaId) => (await api.get(`${root(id)}/${ingestaId}/preview/`)).data;
export const confirmIngesta = async (id, ingestaId) => (await api.post(`${root(id)}/${ingestaId}/confirmar/`)).data;
export const getIngestas = async (id) => (await api.get(`${root(id)}/`)).data;
