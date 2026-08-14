import IntelligencePanel from "../components/IntelligencePanel";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import ProblemWorkspaceV2 from "@/features/problematicas/components/ProblemWorkspaceV2";
import ProfessionalReviewWorkspace from "@/features/professional/components/ProfessionalReviewWorkspace";

function IntelligencePage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  return <><IntelligencePanel initialScope="dashboard" /><ProblemWorkspaceV2 organizationId={activeOrganizacionId}/><ProfessionalReviewWorkspace organizationId={activeOrganizacionId}/></>;
}

export default IntelligencePage;
