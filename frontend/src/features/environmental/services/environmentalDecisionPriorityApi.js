import { api } from "@/shared/services/api";

export async function getEnvironmentalDecisionPriorities(constructoraId) {
  return (await api.get(`/environmental/decisions/priorities/${encodeURIComponent(constructoraId)}/`)).data;
}
