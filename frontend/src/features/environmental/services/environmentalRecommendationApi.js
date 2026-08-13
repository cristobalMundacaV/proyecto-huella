import { api } from "@/shared/services/api";

export async function getEnvironmentalRecommendations(organizacionId) {
  return (await api.get(`/environmental/recommendations/${encodeURIComponent(organizacionId)}/`)).data;
}
