import { api } from "./api";

export async function getIntelligenceRecommendations(payload = {}) {
  const response = await api.post("/intelligence/recommendations/", payload);
  return response.data;
}
