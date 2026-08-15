import { api } from "@/shared/services/api";
export const getProblemContext = async (problemId) => (await api.get(`/context/problems/${problemId}/`)).data;
export const getProposals = async (problemId) => (await api.get(`/agent/problems/${problemId}/proposals/`)).data;
export const createProposal = async (problemId, message, references = []) => (await api.post(`/agent/problems/${problemId}/proposals/`, { mensaje: message, referencias_contextuales: references })).data;
export const sendFeedback = async (problemId, proposalId, decision, message = "") => (await api.post(`/agent/problems/${problemId}/proposals/${proposalId}/feedback/`, { decision, mensaje: message })).data;
export const confirmCommand = async (commandId) => (await api.post(`/agent/commands/${commandId}/confirm/`, { confirmado: true })).data;
