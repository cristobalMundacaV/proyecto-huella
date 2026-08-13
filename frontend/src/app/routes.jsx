import OrganizacionesPage from "@/features/organizaciones/pages/OrganizacionesPage";
import EvidenciasPage from "@/features/evidencias/pages/EvidenciasPage";
import ConfiguracionPage from "@/features/configuracion/pages/ConfiguracionPage";
import FactoresPage from "@/features/factores/pages/FactoresPage";
import ImportacionesPage from "@/features/importaciones/pages/ImportacionesPage";
import ObrasPage from "@/features/obras/pages/ObrasPage";
import ReportesPage from "@/features/reportes/pages/ReportesPage";
import EtapasPage from "@/features/etapas/pages/EtapasPage";
import ReportesRegulatoriosPage from "@/core/reportes-regulatorios/pages/ReportesRegulatoriosPage";
import CopilotoAmbientalPage from "@/core/copiloto/pages/CopilotoAmbientalPage";

export const appRoutes = {
  reportes_regulatorios: ReportesRegulatoriosPage,
  copiloto_ambiental: CopilotoAmbientalPage,
  organizaciones: OrganizacionesPage,
  evidencias: EvidenciasPage,
  configuracion: ConfiguracionPage,
  factores: FactoresPage,
  importaciones: ImportacionesPage,
  obras: ObrasPage,
  reportes: ReportesPage,
  etapas: EtapasPage,
};
