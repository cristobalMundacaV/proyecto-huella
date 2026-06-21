import { api } from "@/shared/services/api";

export async function getEnvironmentalScenarios(constructoraId) {
  return (await api.get(`/environmental/scenarios/${encodeURIComponent(constructoraId)}/`)).data;
}
