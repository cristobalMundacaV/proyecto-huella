import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import ReportesView from "./ReportesView";

function ReportesPage() {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();

  return <ReportesView activeConstructora={activeConstructora} activeConstructoraId={activeConstructoraId} />;
}

export default ReportesPage;
