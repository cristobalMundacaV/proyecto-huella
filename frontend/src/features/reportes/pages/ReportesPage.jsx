import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";
import ReportesView from "./ReportesView";

function ReportesPage() {
  const { activeEmpresa, activeEmpresaId } = useEmpresaActiva();

  return <ReportesView activeEmpresa={activeEmpresa} activeEmpresaId={activeEmpresaId} />;
}

export default ReportesPage;
