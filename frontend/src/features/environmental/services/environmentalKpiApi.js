import { api } from "@/shared/services/api";

export async function getEnvironmentalKpis(organizacionId) {
  return (await api.get(`/environmental/kpis/${encodeURIComponent(organizacionId)}/`)).data;
}
