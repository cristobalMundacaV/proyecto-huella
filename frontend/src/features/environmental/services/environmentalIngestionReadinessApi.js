import { api } from "@/shared/services/api";

export async function getEnvironmentalIngestionReadiness(constructoraId) {
  const response = await api.get(`/environmental/ingestion-readiness/${encodeURIComponent(constructoraId)}/`);
  return response.data;
}
