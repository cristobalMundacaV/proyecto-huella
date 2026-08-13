import { api } from "@/shared/services/api";

export async function getEnvironmentalIngestionReadiness(organizacionId) {
  const response = await api.get(`/environmental/ingestion-readiness/${encodeURIComponent(organizacionId)}/`);
  return response.data;
}
