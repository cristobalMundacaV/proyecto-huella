import IntelligencePanel from "../components/IntelligencePanel";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import ProblemWorkspaceV2 from "@/features/problematicas/components/ProblemWorkspaceV2";

function IntelligencePage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  return <><IntelligencePanel initialScope="dashboard" /><ProblemWorkspaceV2 organizationId={activeOrganizacionId}/></>;
}

export default IntelligencePage;
