export { getObraExportCsvUrl, getObraExportJsonUrl, getObraFichaTecnicaUrl } from "@/shared/services/api";

import { getOrganizationWorks } from "@/features/obras/services/workspaceApi";
import { getObraDashboard } from "@/features/obras/services/obraDashboardApi";

export async function getReportsCenterOverview(organizationId) {
  const response = await getOrganizationWorks(organizationId);
  const works = Array.isArray(response) ? response : response?.results || [];
  const dashboards = await Promise.allSettled(works.map((work) =>
    getObraDashboard(organizationId, work.id || work.obra_id, { relative_months: 3 })
  ));
  return works.map((work, index) => ({
    work,
    dashboard: dashboards[index].status === "fulfilled" ? dashboards[index].value : null,
    unavailable: dashboards[index].status === "rejected",
  }));
}
