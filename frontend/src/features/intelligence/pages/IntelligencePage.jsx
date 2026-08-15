import IntelligencePanel from "../components/IntelligencePanel";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import ProfessionalReviewWorkspace from "@/features/professional/components/ProfessionalReviewWorkspace";
import EnvironmentalKnowledge from "@/features/knowledge/components/EnvironmentalKnowledge";

function IntelligencePage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  return <><IntelligencePanel initialScope="dashboard" /><ProfessionalReviewWorkspace organizationId={activeOrganizacionId}/><EnvironmentalKnowledge organizationId={activeOrganizacionId}/></>;
}

export default IntelligencePage;
