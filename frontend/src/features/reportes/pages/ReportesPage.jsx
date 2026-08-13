import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import ReportesView from "./ReportesView";

function ReportesPage() {
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();

  return <ReportesView activeOrganizacion={activeOrganizacion} activeOrganizacionId={activeOrganizacionId} />;
}

export default ReportesPage;
