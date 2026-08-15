import { api } from "@/shared/services/api";

const base = (id) => `/organizaciones/${encodeURIComponent(id)}/conocimiento`;
export const getKnowledgeCases = async (id) => (await api.get(`${base(id)}/casos/`)).data;
export const getKnowledgeAggregate = async (id, params = {}) => (await api.get(`${base(id)}/agregado/`, { params })).data;
