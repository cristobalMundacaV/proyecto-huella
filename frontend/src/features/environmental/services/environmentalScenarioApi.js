import { api } from "@/shared/services/api";

export async function getEnvironmentalScenarios(organizacionId) {
  return (await api.get(`/environmental/scenarios/${encodeURIComponent(organizacionId)}/`)).data;
}
