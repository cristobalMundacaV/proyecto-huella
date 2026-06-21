import { api } from "@/shared/services/api";

export async function getEnvironmentalRecommendations(constructoraId) {
  return (await api.get(`/environmental/recommendations/${encodeURIComponent(constructoraId)}/`)).data;
}
