import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import Providers from "@/app/providers";
import AuthenticatedLayout from "@/app/layouts/AuthenticatedLayout";
import ObraWorkspaceLayout, { ObraWorkspaceSection } from "@/app/layouts/ObraWorkspaceLayout";
import PlatformLoader from "@/shared/components/PlatformLoader";
import NotFoundPage from "@/shared/components/NotFoundPage";
import CarbonoZeroLanding from "@/landing/CarbonoZeroLanding";
import LoginPage from "@/features/auth/pages/LoginPage";
import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import VerificarObra from "@/features/obras/pages/VerificarObra";
import InicioPage from "@/features/inicio/pages/InicioPage";
import ObrasPage from "@/features/obras/pages/ObrasPage";
import ObraResumenPage from "@/features/obras/pages/ObraResumenPage";
import DataOverviewPage from "@/features/datos/pages/DataOverviewPage";
import EvidencePage from "@/features/datos/pages/EvidencePage";
import EvidenceDetailPage from "@/features/datos/pages/EvidenceDetailPage";
import ImportsPage from "@/features/datos/pages/ImportsPage";
import ImportDetailPage from "@/features/datos/pages/ImportDetailPage";
import ActivosPage from "@/features/activos/pages/ActivosPage";
import SensoresPage from "@/features/sensores/pages/SensoresPage";
import SensorDetailPage from "@/features/sensores/pages/SensorDetailPage";
import OperationLayout from "@/features/operacion/components/OperationLayout";
import OperacionOverviewPage from "@/features/operacion/pages/OperacionOverviewPage";
import SectorDomainPage from "@/features/operacion/pages/SectorDomainPage";
import TransportPage from "@/features/operacion/pages/TransportPage";
import MaterialsPage from "@/features/operacion/pages/MaterialsPage";
import WastePage from "@/features/operacion/pages/WastePage";
import IntelligencePage from "@/features/intelligence/pages/IntelligencePage";
import ProblemsPage from "@/features/mejora/pages/ProblemsPage";
import ProblemDetailPage from "@/features/mejora/pages/ProblemDetailPage";
import CopilotoAmbientalPage from "@/features/intelligence/pages/CopilotPage";
import FactoresPage from "@/features/factores/pages/FactoresPage";
import ReportesRegulatoriosPage from "@/core/reportes-regulatorios/pages/ReportesRegulatoriosPage";
import AdministracionPage from "@/features/administracion/pages/AdministracionPage";
import OrganizacionesPage from "@/features/organizaciones/pages/OrganizacionesPage";
import UsuariosPage from "@/features/usuarios/pages/UsuariosPage";
import ConfiguracionPage from "@/features/configuracion/pages/ConfiguracionPage";
import DiagnosticoAmbientalPage from "@/features/diagnostico/pages/DiagnosticoAmbientalPage";
import EtapasPage from "@/features/etapas/pages/EtapasPage";
import RecepcionTrozasPage from "@/presets/aserradero/pages/RecepcionTrozasPage";
import ProduccionAserraderoPage from "@/presets/aserradero/pages/ProduccionAserraderoPage";
import SecadoAserraderoPage from "@/presets/aserradero/pages/SecadoAserraderoPage";
import EnergiaAserraderoPage from "@/presets/aserradero/pages/EnergiaAserraderoPage";
import TransporteForestalPage from "@/presets/aserradero/pages/TransporteForestalPage";
import ResiduosSubproductosPage from "@/presets/aserradero/pages/ResiduosSubproductosPage";
import LotesForestalesPage from "@/presets/aserradero/pages/LotesForestalesPage";

function ProviderBoundary() { return <Providers><Outlet /></Providers>; }
function RequireAuth() { const { loadingAuth, user } = useAuth(); const location = useLocation(); if (loadingAuth) return <PlatformLoader fullScreen title="Iniciando sesión" />; return user ? <Outlet /> : <Navigate to="/login" replace state={{ returnTo: location.pathname + location.search }} />; }
function LoginRoute() { const { loadingAuth, user } = useAuth(); if (loadingAuth) return <PlatformLoader fullScreen title="Iniciando sesión" />; return user ? <Navigate to="/inicio" replace /> : <LoginPage />; }
function RequireOrganization() { const { activeOrganizacion, loadingOrganizaciones } = useOrganizacionActiva(); const { pathname } = useLocation(); if (loadingOrganizaciones) return <PlatformLoader fullScreen title="Cargando empresas" />; return !activeOrganizacion && pathname !== "/administracion/organizacion" ? <Navigate to="/administracion/organizacion" replace /> : <Outlet />; }
function OrganizationRoute() { const { activeOrganizacion } = useOrganizacionActiva(); return <OrganizacionesPage initialOpenCreate={!activeOrganizacion} />; }

export default function AppRouter() {
  return <Routes>
    <Route path="/" element={<CarbonoZeroLanding />} />
    <Route path="/verificar/:codigo" element={<VerificarObra />} />
    <Route element={<ProviderBoundary />}>
      <Route path="/login" element={<LoginRoute />} />
      <Route element={<RequireAuth />}><Route element={<RequireOrganization />}><Route element={<AuthenticatedLayout />}>
        <Route index element={<Navigate to="/inicio" replace />} />
        <Route path="inicio" element={<InicioPage />} />
        <Route path="obras" element={<ObrasPage />} />
        <Route path="obras/:obraId" element={<ObraWorkspaceLayout />}>
          <Route index element={<Navigate to="resumen" replace />} />
          <Route path="resumen" element={<ObraResumenPage />} />
          <Route path="operacion" element={<OperationLayout />}>
            <Route index element={<OperacionOverviewPage />} />
            <Route path="energia" element={<SectorDomainPage domain="energia" />} />
            <Route path="agua" element={<SectorDomainPage domain="agua" />} />
            <Route path="combustibles" element={<SectorDomainPage domain="combustibles" />} />
            <Route path="transporte" element={<TransportPage />} />
            <Route path="materiales" element={<MaterialsPage />} />
            <Route path="residuos" element={<WastePage />} />
            <Route path="ruido" element={<SectorDomainPage domain="ruido" />} />
            <Route path="hidrica-suelo" element={<SectorDomainPage domain="hidrica-suelo" />} />
          </Route>
          <Route path="indicadores" element={<ObraWorkspaceSection title="Indicadores" description="Los indicadores conservan alcance de obra. La exploración profunda se completa en UX-05." />} />
          <Route path="problemas" element={<ProblemsPage workScoped />} />
          <Route path="problemas/:problemId" element={<ProblemDetailPage workScoped />} />
          <Route path="evidencias" element={<EvidencePage workScoped />} />
          <Route path="timeline" element={<ObraWorkspaceSection title="Timeline" description="El resumen presenta los eventos recientes reales de esta obra." />} />
          <Route path="informes" element={<ObraWorkspaceSection title="Informes" description="Los informes mantendrán este alcance de obra cuando se complete su experiencia especializada." />} />
        </Route>
        <Route path="datos" element={<DataOverviewPage />} />
        <Route path="datos/evidencias" element={<EvidencePage />} />
        <Route path="datos/evidencias/:evidenceId" element={<EvidenceDetailPage />} />
        <Route path="datos/importaciones" element={<ImportsPage />} />
        <Route path="datos/importaciones/:processId" element={<ImportDetailPage />} />
        <Route path="operacion/activos" element={<ActivosPage />} /><Route path="operacion/sensores" element={<SensoresPage />} /><Route path="operacion/sensores/:sensorId" element={<SensorDetailPage />} />
        <Route path="inteligencia" element={<IntelligencePage />} />
        <Route path="inteligencia/problemas" element={<ProblemsPage />} />
        <Route path="inteligencia/problemas/:problemId" element={<ProblemDetailPage />} />
        <Route path="inteligencia/acciones" element={<Navigate to="/inteligencia/problemas" replace />} />
        <Route path="inteligencia/copiloto" element={<CopilotoAmbientalPage />} />
        <Route path="gobernanza/factores" element={<FactoresPage />} /><Route path="gobernanza/informes" element={<ReportesRegulatoriosPage />} />
        <Route path="administracion" element={<AdministracionPage />} /><Route path="administracion/organizacion" element={<OrganizationRoute />} /><Route path="administracion/usuarios" element={<UsuariosPage />} /><Route path="administracion/configuracion" element={<ConfiguracionPage />} /><Route path="administracion/diagnostico" element={<DiagnosticoAmbientalPage />} /><Route path="administracion/estructura" element={<EtapasPage />} />
        <Route path="operacion/recepcion-trozas" element={<RecepcionTrozasPage />} /><Route path="operacion/produccion" element={<ProduccionAserraderoPage />} /><Route path="operacion/secado" element={<SecadoAserraderoPage />} /><Route path="operacion/energia" element={<EnergiaAserraderoPage />} /><Route path="operacion/transporte-forestal" element={<TransporteForestalPage />} /><Route path="operacion/residuos-subproductos" element={<ResiduosSubproductosPage />} /><Route path="operacion/lotes-forestales" element={<LotesForestalesPage />} />
        <Route path="*" element={<NotFoundPage authenticated />} />
      </Route></Route></Route>
    </Route>
    <Route path="*" element={<NotFoundPage />} />
  </Routes>;
}
