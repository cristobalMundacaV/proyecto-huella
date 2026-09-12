import { api } from "@/shared/services/api";

function base(organizacionId) {
  return `/ai/${encodeURIComponent(organizacionId)}/conversations`;
}

export async function listConversations(organizacionId) {
  const response = await api.get(`${base(organizacionId)}/`);
  return response.data.conversaciones;
}

export async function createConversation(organizacionId, { obraId } = {}) {
  const response = await api.post(`${base(organizacionId)}/`, obraId ? { obra_id: obraId } : {});
  return response.data;
}

export async function getConversation(organizacionId, conversationId) {
  const response = await api.get(`${base(organizacionId)}/${conversationId}/`);
  return response.data;
}

export async function sendMessage(organizacionId, conversationId, content) {
  const response = await api.post(`${base(organizacionId)}/${conversationId}/messages/`, { content });
  return response.data;
}
