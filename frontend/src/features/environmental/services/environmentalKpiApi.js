import { api } from "@/shared/services/api";

export async function getEnvironmentalKpis(constructoraId) {
  return (await api.get(`/environmental/kpis/${encodeURIComponent(constructoraId)}/`)).data;
}
