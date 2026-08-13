import { api } from "@/shared/services/api";

export async function getEnvironmentalDecisionPriorities(organizacionId) {
  return (await api.get(`/environmental/decisions/priorities/${encodeURIComponent(organizacionId)}/`)).data;
}
