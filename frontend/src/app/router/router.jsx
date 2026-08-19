import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import Providers from "@/app/providers";
import AuthenticatedLayout from "@/app/layouts/AuthenticatedLayout";
import PlatformLoader from "@/shared/components/PlatformLoader";
import NotFoundPage from "@/shared/components/NotFoundPage";
import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";

const IntelligencePage = lazy(() => import("@/features/intelligence/pages/IntelligencePage"));
const CopilotoAmbientalPage = lazy(() => import("@/features/intelligence/pages/CopilotPage"));
const FactoresPage = lazy(() => import("@/core/factores/pages/FactoresPage"));
const GovernanceOverviewPage = lazy(() => import("@/features/professional/pages/GovernanceOverviewPage"));
const ReviewQueuePage = lazy(() => import("@/features/professional/pages/ReviewQueuePage"));
const DossiersPage = lazy(() => import("@/features/professional/pages/DossiersPage"));
const DossierDetailPage = lazy(() => import("@/features/professional/pages/DossierDetailPage"));
const QualityGovernancePage = lazy(() => import("@/features/professional/pages/QualityGovernancePage"));
const AuditPage = lazy(() => import("@/features/professional/pages/AuditPage"));
const KnowledgePage = lazy(() => import("@/features/professional/pages/KnowledgePage"));
const CarbonoZeroLanding = lazy(() => import("@/landing/CarbonoZeroLanding"));
const LoginPage = lazy(() => import("@/features/auth/pages/LoginPage"));
const VerificarObra = lazy(() => import("@/features/obras/pages/VerificarObra"));
const InicioPage = lazy(() => import("@/features/inicio/pages/InicioPage"));
const ObrasPage = lazy(() => import("@/features/obras/pages/ObrasPage"));
const ObraWorkspaceLayout = lazy(() => import("@/app/layouts/ObraWorkspaceLayout"));
const ObraResumenPage = lazy(() => import("@/features/obras/pages/ObraResumenPage"));
const ObraIndicatorsPage = lazy(() => import("@/features/obras/pages/ObraIndicatorsPage"));
const ObraTimelinePage = lazy(() => import("@/features/obras/pages/ObraTimelinePage"));
const DataOverviewPage = lazy(() => import("@/features/datos/pages/DataOverviewPage"));
const EvidencePage = lazy(() => import("@/features/datos/pages/EvidencePage"));
const EvidenceDetailPage = lazy(() => import("@/features/datos/pages/EvidenceDetailPage"));
const ImportsPage = lazy(() => import("@/features/datos/pages/ImportsPage"));
const ImportDetailPage = lazy(() => import("@/features/datos/pages/ImportDetailPage"));
const ActivosPage = lazy(() => import("@/features/activos/pages/ActivosPage"));
const SensoresPage = lazy(() => import("@/features/sensores/pages/SensoresPage"));
const SensorDetailPage = lazy(() => import("@/features/sensores/pages/SensorDetailPage"));
const OperationLayout = lazy(() => import("@/features/operacion/components/OperationLayout"));
const OperacionOverviewPage = lazy(() => import("@/features/operacion/pages/OperacionOverviewPage"));
const SectorDomainPage = lazy(() => import("@/features/operacion/pages/SectorDomainPage"));
const TransportPage = lazy(() => import("@/features/operacion/pages/TransportPage"));
const MaterialsPage = lazy(() => import("@/features/operacion/pages/MaterialsPage"));
const WastePage = lazy(() => import("@/features/operacion/pages/WastePage"));
const ProblemsPage = lazy(() => import("@/features/mejora/pages/ProblemsPage"));
const ProblemDetailPage = lazy(() => import("@/features/mejora/pages/ProblemDetailPage"));
const AdministracionPage = lazy(() => import("@/features/administracion/pages/AdministracionPage"));
const OrganizacionesPage = lazy(() => import("@/features/organizaciones/pages/OrganizacionesPage"));
const UsuariosPage = lazy(() => import("@/features/usuarios/pages/UsuariosPage"));
const ConfiguracionPage = lazy(() => import("@/features/configuracion/pages/ConfiguracionPage"));
const DiagnosticoAmbientalPage = lazy(() => import("@/features/diagnostico/pages/DiagnosticoAmbientalPage"));
const EtapasPage = lazy(() => import("@/features/etapas/pages/EtapasPage"));
const RecepcionTrozasPage = lazy(() => import("@/presets/aserradero/pages/RecepcionTrozasPage"));
const ProduccionAserraderoPage = lazy(() => import("@/presets/aserradero/pages/ProduccionAserraderoPage"));
const SecadoAserraderoPage = lazy(() => import("@/presets/aserradero/pages/SecadoAserraderoPage"));
const EnergiaAserraderoPage = lazy(() => import("@/presets/aserradero/pages/EnergiaAserraderoPage"));
const TransporteForestalPage = lazy(() => import("@/presets/aserradero/pages/TransporteForestalPage"));
const ResiduosSubproductosPage = lazy(() => import("@/presets/aserradero/pages/ResiduosSubproductosPage"));
const LotesForestalesPage = lazy(() => import("@/presets/aserradero/pages/LotesForestalesPage"));
const WorkDiagnosticPage = lazy(
  () =>
    import(
      "@/features/diagnostico/pages/WorkDiagnosticPage"
    ),
);

function ProviderBoundary() { return <Providers><Outlet /></Providers>; }
function RequireAuth() { const { loadingAuth, user } = useAuth(); const location = useLocation(); if (loadingAuth) return <PlatformLoader fullScreen title="Iniciando sesión" />; return user ? <Outlet /> : <Navigate to="/login" replace state={{ returnTo: location.pathname + location.search }} />; }
function LoginRoute() { const { loadingAuth, user } = useAuth(); if (loadingAuth) return <PlatformLoader fullScreen title="Iniciando sesión" />; return user ? <Navigate to="/inicio" replace /> : <LoginPage />; }
function RequireOrganization() { const { activeOrganizacion, loadingOrganizaciones } = useOrganizacionActiva(); const { pathname } = useLocation(); if (loadingOrganizaciones) return <PlatformLoader fullScreen title="Cargando empresas" />; return !activeOrganizacion && pathname !== "/administracion/organizacion" ? <Navigate to="/administracion/organizacion" replace /> : <Outlet />; }
function OrganizationRoute() { const { activeOrganizacion } = useOrganizacionActiva(); return <OrganizacionesPage initialOpenCreate={!activeOrganizacion} />; }

export default function AppRouter() {
  return <Suspense fallback={<PlatformLoader fullScreen title="Cargando módulo" />}><Routes>
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
          <Route path="indicadores" element={<ObraIndicatorsPage />} />
          <Route path="problemas" element={<ProblemsPage workScoped />} />
          <Route path="problemas/:problemId" element={<ProblemDetailPage workScoped />} />
          <Route path="evidencias" element={<EvidencePage workScoped />} />
          <Route path="timeline" element={<ObraTimelinePage />} />
          <Route
            path="diagnostico"
            element={<WorkDiagnosticPage />}
          />
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
        <Route path="gobernanza" element={<GovernanceOverviewPage />} />
        <Route path="gobernanza/revision" element={<ReviewQueuePage />} />
        <Route path="gobernanza/expedientes" element={<DossiersPage />} />
        <Route path="gobernanza/expedientes/:dossierId" element={<DossierDetailPage />} />
        <Route path="gobernanza/factores" element={<FactoresPage />} />
        <Route path="gobernanza/calidad" element={<QualityGovernancePage />} />
        <Route path="gobernanza/auditoria" element={<AuditPage />} />
        <Route path="gobernanza/conocimiento" element={<KnowledgePage />} />
        <Route path="gobernanza/informes" element={<DossiersPage />} />
        <Route path="administracion" element={<AdministracionPage />} /><Route path="administracion/organizacion" element={<OrganizationRoute />} /><Route path="administracion/usuarios" element={<UsuariosPage />} /><Route path="administracion/configuracion" element={<ConfiguracionPage />} /><Route path="administracion/diagnostico" element={<DiagnosticoAmbientalPage />} /><Route path="administracion/estructura" element={<EtapasPage />} />
        <Route path="operacion/recepcion-trozas" element={<RecepcionTrozasPage />} /><Route path="operacion/produccion" element={<ProduccionAserraderoPage />} /><Route path="operacion/secado" element={<SecadoAserraderoPage />} /><Route path="operacion/energia" element={<EnergiaAserraderoPage />} /><Route path="operacion/transporte-forestal" element={<TransporteForestalPage />} /><Route path="operacion/residuos-subproductos" element={<ResiduosSubproductosPage />} /><Route path="operacion/lotes-forestales" element={<LotesForestalesPage />} />
        <Route path="*" element={<NotFoundPage authenticated />} />
      </Route></Route></Route>
    </Route>
    <Route path="*" element={<NotFoundPage />} />
  </Routes></Suspense>;
}
