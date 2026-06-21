import { api } from "@/shared/services/api";

export async function getEnvironmentalExecutiveReport(constructoraId) {
  const response = await api.get(`/environmental/executive-report/${encodeURIComponent(constructoraId)}/`);
  return response.data;
}
