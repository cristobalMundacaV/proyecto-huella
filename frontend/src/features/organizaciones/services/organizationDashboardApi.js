import { api } from "@/shared/services/api";

/** Single call to the organization (portfolio) motor — aggregates every
 * obra's own `obra_environmental_dashboard`, never a second calculation
 * path computed in the frontend. */
export async function getOrganizationDashboard(organizationId, params = {}) {
  return (
    await api.get(`/organizaciones/${encodeURIComponent(organizationId)}/dashboard-portafolio/`, { params })
  ).data;
}
