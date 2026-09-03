import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import Providers from "@/app/providers";
import AuthenticatedLayout from "@/app/layouts/AuthenticatedLayout";
import PlatformLoader from "@/shared/components/PlatformLoader";
import NotFoundPage from "@/shared/components/NotFoundPage";
import { ErrorState } from "@/shared/ui/Feedback";
import { useAuth } from "@/features/auth/context/AuthContext";
import { usePermissions } from "@/features/auth/hooks/usePermissions";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { useOperationalWorkspace } from "@/features/workspace/context/OperationalWorkspaceContext";
import { organizationDestination, resolveOrganizationAccess } from "@/features/organizaciones/context/organizationResolution";

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
const OnboardingPage = lazy(() => import("@/features/onboarding/pages/OnboardingPage"));
const PasswordLifecyclePage = lazy(() => import("@/features/onboarding/pages/PasswordLifecyclePage"));
const ReadyToStartPage = lazy(() => import("@/features/onboarding/pages/ReadyToStartPage"));
const StructureSettingsPage = lazy(() => import("@/features/onboarding/pages/StructureSettingsPage"));
const SecurityPage = lazy(() => import("@/features/onboarding/pages/SecurityPage"));
const VerificarObra = lazy(() => import("@/features/obras/pages/VerificarObra"));
const InicioPage = lazy(() => import("@/features/inicio/pages/InicioPage"));
const OperationalHome = lazy(() => import("@/features/workspace/pages/OperationalHome"));
const ObrasPage = lazy(() => import("@/features/obras/pages/ObrasPage"));
const ObraWorkspaceLayout = lazy(() => import("@/app/layouts/ObraWorkspaceLayout"));
const ObraResumenPage = lazy(() => import("@/features/obras/pages/ObraResumenPage"));
const ObraIndicatorsPage = lazy(() => import("@/features/obras/pages/ObraIndicatorsPage"));
const ReportsPage = lazy(() => import("@/features/reportes/pages/ReportsPage"));
const WorkCompliancePage = lazy(
  () =>
    import(
      "@/features/compliance/pages/WorkCompliancePage"
    )
);
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
const SettingsSectionPage = lazy(() => import("@/features/administracion/pages/SettingsSectionPage"));
const OrganizacionesPage = lazy(() => import("@/features/organizaciones/pages/OrganizacionesPage"));
const OrganizationSelectionPage = lazy(() => import("@/features/organizaciones/pages/OrganizationSelectionPage"));
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
const SaaSLayout = lazy(() => import("@/features/saas/components/SaaSLayout"));
const SaaSDashboardPage = lazy(() => import("@/features/saas/pages/SaaSDashboardPage"));
const SaaSOrganizationsPage = lazy(() => import("@/features/saas/pages/SaaSOrganizationsPage"));
const SaaSAuditPage = lazy(() => import("@/features/saas/pages/SaaSAuditPage"));
const OrganizationStructurePage = lazy(
  () =>
    import(
      "@/features/administracion/pages/OrganizationStructurePage"
    ),
);

function ProviderBoundary() { return <Providers><Outlet /></Providers>; }
function RequireAuth() { const { loadingAuth, user } = useAuth(); const location = useLocation(); if (loadingAuth) return <PlatformLoader fullScreen title="Iniciando sesión" />; return user ? <Outlet /> : <Navigate to="/login" replace state={{ returnTo: location.pathname + location.search }} />; }
function NoOrganizationState() { return <main className="flex min-h-screen items-center justify-center bg-slate-100 p-5"><ErrorState title="Tu cuenta no tiene una organización" description="Solicita a un administrador que vincule tu cuenta a una organización para poder continuar." /></main>; }
function LoginRoute() { const { loadingAuth, user } = useAuth(); const location = useLocation(); const organizationState = useOrganizacionActiva(); if (loadingAuth) return <PlatformLoader fullScreen title="Iniciando sesión" />; if (!user) return <LoginPage />; if (user.is_superuser) return <Navigate to="/saas" replace />; const access = resolveOrganizationAccess({ status: organizationState.organizationResolutionStatus, organizations: organizationState.organizaciones, activeOrganization: organizationState.activeOrganizacion }); if (access === "resolving") return <PlatformLoader fullScreen title="Preparando tu organización" />; if (access === "error") return <ErrorState title="No pudimos cargar tu organización" description={organizationState.errorOrganizaciones} onRetry={() => organizationState.refreshOrganizaciones().catch(() => undefined)} />; if (access === "no-organization") return <NoOrganizationState />; if (access === "selection-required") return <Navigate to="/seleccionar-organizacion" replace />; return <Navigate to={organizationDestination(organizationState.activeOrganizacion, location.state?.returnTo || "/inicio")} replace />; }
function RequireOrganization() { const organizationState = useOrganizacionActiva(); const access = resolveOrganizationAccess({ status: organizationState.organizationResolutionStatus, organizations: organizationState.organizaciones, activeOrganization: organizationState.activeOrganizacion }); if (access === "resolving") return <PlatformLoader fullScreen title="Cargando empresas" />; if (access === "error") return <ErrorState title="No pudimos cargar tu organización" description={organizationState.errorOrganizaciones} onRetry={() => organizationState.refreshOrganizaciones().catch(() => undefined)} />; if (access === "no-organization") return <NoOrganizationState />; return access === "selection-required" ? <Navigate to="/seleccionar-organizacion" replace /> : <Outlet />; }
function RequireOnboardingComplete() { const { user } = useAuth(); const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva(); const membership = user?.organizaciones?.find((item) => String(item.organizacion_id) === String(activeOrganizacionId)); return membership?.rol === "admin" && activeOrganizacion?.onboarding_completado === false ? <Navigate to="/onboarding" replace /> : <Outlet />; }
function RequireOperationalWorkspace() { const { loading } = useOperationalWorkspace(); if (loading) return <PlatformLoader fullScreen title="Preparando el contexto operacional" />; return <Outlet />; }
function ContextualHome() { const { activeWorkspace } = useOperationalWorkspace(); const { activeOrganizacion } = useOrganizacionActiva(); const operational = activeWorkspace && !["medio_ambiente", "gestion_obra"].includes(activeWorkspace.area.tipo); if (operational) return <OperationalHome />; return Number(activeOrganizacion?.registros_count || 0) === 0 ? <ReadyToStartPage /> : <InicioPage />; }
function OrganizationRoute() { const { activeOrganizacion } = useOrganizacionActiva(); return <OrganizacionesPage initialOpenCreate={!activeOrganizacion} />; }
function RequireCapability({ permission, children }) { const { can } = usePermissions(); return can(permission) ? children : <ErrorState title="Sin permisos" description="No tienes permisos para acceder a este módulo en la organización activa." />; }
function RequireSuperuser({ children }) { const { user } = useAuth(); return user?.is_superuser ? children : <ErrorState title="Acceso restringido" description="Esta sección pertenece exclusivamente a la administración global de Carbono Zero." />; }

export default function AppRouter() {
  return <Suspense fallback={<PlatformLoader fullScreen title="Cargando módulo" />}><Routes>
    <Route path="/" element={<CarbonoZeroLanding />} />
    <Route path="/verificar/:codigo" element={<VerificarObra />} />
    <Route element={<ProviderBoundary />}>
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/activar-cuenta/:uid/:token" element={<PasswordLifecyclePage mode="activate" />} />
      <Route path="/recuperar-contrasena" element={<PasswordLifecyclePage mode="request" />} />
      <Route path="/restablecer-contrasena/:uid/:token" element={<PasswordLifecyclePage mode="reset" />} />
      <Route element={<RequireAuth />}>
        <Route path="seleccionar-organizacion" element={<OrganizationSelectionPage />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route path="saas" element={<RequireSuperuser><SaaSLayout /></RequireSuperuser>}><Route index element={<SaaSDashboardPage />} /><Route path="organizaciones" element={<SaaSOrganizationsPage />} /><Route path="auditoria" element={<SaaSAuditPage />} /></Route>
        <Route element={<RequireOrganization />}><Route element={<RequireOnboardingComplete />}><Route element={<RequireOperationalWorkspace />}><Route element={<AuthenticatedLayout />}>
          <Route path="inicio" element={<ContextualHome />} />
          <Route path="perfil/seguridad" element={<SecurityPage />} />
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
              <Route path="emisiones-atmosfericas" element={<SectorDomainPage domain="emisiones-atmosfericas" />} />
              <Route path="suelo" element={<SectorDomainPage domain="suelo" />} />
            </Route>
            <Route
              path="indicadores"
              element={<RequireCapability permission="indicators.view"><ObraIndicatorsPage /></RequireCapability>}
            />
            <Route path="reportes" element={<RequireCapability permission="reports.view"><ReportsPage /></RequireCapability>} />

            <Route
              path="cumplimiento"
              element={<RequireCapability permission="compliance.view"><WorkCompliancePage /></RequireCapability>}
            />

            <Route
              path="problemas"
              element={<RequireCapability permission="problems.view"><ProblemsPage workScoped /></RequireCapability>}
            />
            <Route path="problemas/:problemId" element={<ProblemDetailPage workScoped />} />
            <Route path="evidencias" element={<RequireCapability permission="evidence.view"><EvidencePage workScoped /></RequireCapability>} />
            <Route path="evidencias/:evidenceId" element={<RequireCapability permission="evidence.view"><EvidenceDetailPage /></RequireCapability>} />
            <Route path="timeline" element={<ObraTimelinePage />} />
            <Route
              path="diagnostico"
              element={<RequireCapability permission="environmental_profile.view"><WorkDiagnosticPage /></RequireCapability>}
            />
          </Route>
          <Route path="datos" element={<DataOverviewPage />} />
          <Route path="datos/evidencias" element={<RequireCapability permission="evidence.view"><EvidencePage /></RequireCapability>} />
          <Route path="datos/evidencias/:evidenceId" element={<EvidenceDetailPage />} />
          <Route path="datos/importaciones" element={<RequireCapability permission="imports.view"><ImportsPage /></RequireCapability>} />
          <Route path="datos/importaciones/:processId" element={<ImportDetailPage />} />
          <Route path="operacion/activos" element={<ActivosPage />} /><Route path="operacion/sensores" element={<SensoresPage />} /><Route path="operacion/sensores/:sensorId" element={<SensorDetailPage />} />
          <Route path="inteligencia" element={<IntelligencePage />} />
          <Route path="inteligencia/problemas" element={<ProblemsPage />} />
          <Route path="inteligencia/problemas/:problemId" element={<ProblemDetailPage />} />
          <Route path="inteligencia/acciones" element={<Navigate to="/inteligencia/problemas" replace />} />
          <Route path="inteligencia/copiloto" element={<CopilotoAmbientalPage />} />
          <Route path="gobernanza" element={<GovernanceOverviewPage />} />
          <Route path="gobernanza/revision" element={<RequireCapability permission="professional_review.execute"><ReviewQueuePage /></RequireCapability>} />
          <Route path="gobernanza/expedientes" element={<DossiersPage />} />
          <Route path="gobernanza/expedientes/:dossierId" element={<DossierDetailPage />} />
          <Route path="gobernanza/factores" element={<FactoresPage />} />
          <Route path="gobernanza/calidad" element={<QualityGovernancePage />} />
          <Route path="gobernanza/auditoria" element={<AuditPage />} />
          <Route path="gobernanza/conocimiento" element={<KnowledgePage />} />
          <Route path="gobernanza/informes" element={<DossiersPage />} />
          <Route path="administracion/estructura-operacional" element={<RequireCapability permission="settings.manage"><StructureSettingsPage /></RequireCapability>} />
          <Route path="administracion" element={<AdministracionPage />} /><Route path="administracion/organizacion" element={<OrganizationRoute />} /><Route path="administracion/equipo" element={<UsuariosPage />} /><Route path="administracion/usuarios" element={<Navigate to="/administracion/equipo" replace />} /><Route path="administracion/operacion" element={<SettingsSectionPage section="operacion" />} /><Route path="administracion/ambiental" element={<SettingsSectionPage section="ambiental" />} /><Route path="administracion/calculo" element={<SettingsSectionPage section="calculo" />} /><Route path="administracion/reportes" element={<SettingsSectionPage section="reportes" />} /><Route path="administracion/datos" element={<SettingsSectionPage section="datos" />} /><Route path="administracion/auditoria" element={<SettingsSectionPage section="auditoria" />} /><Route path="administracion/configuracion" element={<ConfiguracionPage />} /><Route path="administracion/diagnostico" element={<DiagnosticoAmbientalPage />} /><Route path="administracion/estructura" element={<EtapasPage />} />
          <Route
            path="administracion/estructura-organizacional"
            element={
              <OrganizationStructurePage />
            }
          />
          <Route path="operacion/recepcion-trozas" element={<RecepcionTrozasPage />} /><Route path="operacion/produccion" element={<ProduccionAserraderoPage />} /><Route path="operacion/secado" element={<SecadoAserraderoPage />} /><Route path="operacion/energia" element={<EnergiaAserraderoPage />} /><Route path="operacion/transporte-forestal" element={<TransporteForestalPage />} /><Route path="operacion/residuos-subproductos" element={<ResiduosSubproductosPage />} /><Route path="operacion/lotes-forestales" element={<LotesForestalesPage />} />
          <Route path="*" element={<NotFoundPage authenticated />} />
        </Route></Route></Route></Route></Route>
    </Route>
    <Route path="*" element={<NotFoundPage />} />
  </Routes></Suspense>;
}
