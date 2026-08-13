import { api } from "@/shared/services/api";

export async function getEnvironmentalExecutiveReport(organizacionId) {
  const response = await api.get(`/environmental/executive-report/${encodeURIComponent(organizacionId)}/`);
  return response.data;
}
