import { useCallback, useState } from "react";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import Navbar from "@/layouts/Navbar";
import Sidebar from "@/layouts/Sidebar";
import PlatformLoader from "@/shared/components/PlatformLoader";
import PresetComingSoon from "@/shared/components/PresetComingSoon";
import LoginPage from "@/features/auth/pages/LoginPage";
import { useAuth } from "@/features/auth/context/AuthContext";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { DEFAULT_PRESET_KEY, getActivePreset } from "@/presets/registry";

import DashboardPage from "@/core/dashboard/DashboardPage";
import IntelligencePage from "@/features/intelligence/pages/IntelligencePage";
import EmisionesView from "@/features/emisiones/EmisionesStableView";
import AccionesAmbientalesPage from "@/features/acciones/pages/AccionesAmbientalesPage";
import OperacionPage from "@/features/operacion/pages/OperacionPage";
import AdministracionPage from "@/features/administracion/pages/AdministracionPage";
import EvidenciasPage from "@/features/evidencias/pages/EvidenciasPage";
import ReportesView from "@/features/reportes/pages/ReportesView";
import ConstructorasView from "@/features/constructoras/pages/ConstructorasPage";
import ObrasView from "@/features/obras/pages/ObrasPage";
import EtapasObraView from "@/features/etapas/pages/EtapasPage";
import FactoresView from "@/features/factores/pages/FactoresPage";
import ImportacionesView from "@/features/importaciones/pages/ImportacionesPage";
import UsuariosPage from "@/features/usuarios/pages/UsuariosPage";
import ConfiguracionPage from "@/features/configuracion/pages/ConfiguracionPage";
import CentralOperativaPage from "@/core/central-operativa/pages/CentralOperativaPage";
import IngestaInteligentePage from "@/core/ingesta/pages/IngestaInteligentePage";
import ReportesRegulatoriosPage from "@/core/reportes-regulatorios/pages/ReportesRegulatoriosPage";
import CopilotoAmbientalPage from "@/core/copiloto/pages/CopilotoAmbientalPage";

import RecepcionTrozasPage from "@/presets/aserradero/pages/RecepcionTrozasPage";
import ProduccionAserraderoPage from "@/presets/aserradero/pages/ProduccionAserraderoPage";
import SecadoAserraderoPage from "@/presets/aserradero/pages/SecadoAserraderoPage";
import EnergiaAserraderoPage from "@/presets/aserradero/pages/EnergiaAserraderoPage";
import TransporteForestalPage from "@/presets/aserradero/pages/TransporteForestalPage";
import ResiduosSubproductosPage from "@/presets/aserradero/pages/ResiduosSubproductosPage";
import LotesForestalesPage from "@/presets/aserradero/pages/LotesForestalesPage";

const viewTransition = { duration: 0.24, ease: [0.22, 1, 0.36, 1] };

const placeholderViews = {
  flota: ["Flota", "Administra vehículos, capacidad, estado operativo y atributos relevantes para emisiones."],
  viajes: ["Viajes", "Registra viajes, cargas, origen, destino y actividad logística asociada."],
  combustible: ["Combustible", "Controla consumos, cargas, rendimiento y conciliación con viajes o flota."],
  rutas: ["Rutas", "Gestiona rutas frecuentes, kilometraje, tramos críticos y oportunidades de optimización."],
  mantenciones: ["Mantenciones", "Planifica mantenciones y relaciónalas con eficiencia y disponibilidad."],
};

function App() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeView, setActiveView] = useState("dashboard");
  const [constructoraCreateSignal, setConstructoraCreateSignal] = useState(0);
  const [companyStatus, setCompanyStatus] = useState(null);
  const { loadingAuth, user } = useAuth();
  const { activeConstructora, activeConstructoraId, loadingConstructoras } = useConstructoraActiva();
  const activePreset = getActivePreset(activeConstructora?.preset || DEFAULT_PRESET_KEY);

  const handleSetActiveView = useCallback((view, options = {}) => {
    setActiveView(view);
    if (options.openCreateConstructora) setConstructoraCreateSignal((value) => value + 1);
  }, []);

  if (loadingAuth) {
    return <PlatformLoader fullScreen title="Iniciando sesión" description="Estamos preparando tu espacio de gestión ambiental." />;
  }

  if (!user) return <LoginPage />;

  if (loadingConstructoras) {
    return <PlatformLoader fullScreen title="Cargando empresas" description="Estamos preparando empresas, presets y estado operativo." />;
  }

  if (!activeConstructora) {
    return (
      <div className="min-h-screen bg-[var(--bg-main)] p-6 text-[var(--text-main)] sm:p-10">
        <ConstructorasView onSetActiveView={handleSetActiveView} initialOpenCreate />
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[var(--bg-main)] text-[var(--text-main)]">
      <Navbar onSetActiveView={handleSetActiveView} onOpenMobileMenu={() => setMobileMenuOpen(true)} />

      {user?.is_demo && (
        <div className="fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-full border border-amber-300/30 bg-amber-300/10 px-4 py-2 text-xs font-bold uppercase tracking-wide text-amber-100 shadow-xl backdrop-blur">
          Modo demo: solo lectura
        </div>
      )}

      <div className="flex min-h-[calc(100vh-72px)] flex-col lg:flex-row">
        <div className="hidden lg:block">
          <Sidebar activeView={activeView} onSetActiveView={handleSetActiveView} systemStatus={companyStatus} />
        </div>

        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div className="fixed inset-0 z-50 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <button type="button" className="absolute inset-0 bg-slate-950/30 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} aria-label="Cerrar menú" />
              <motion.div className="absolute left-0 top-0 h-full w-[85vw] max-w-sm overflow-y-auto border-r border-white/10 bg-[var(--sidebar)] shadow-2xl" initial={{ x: "-100%" }} animate={{ x: 0 }} exit={{ x: "-100%" }} transition={viewTransition}>
                <button type="button" onClick={() => setMobileMenuOpen(false)} className="absolute right-4 top-4 rounded-2xl border border-white/10 bg-white/10 p-3 text-slate-200">
                  <X size={20} />
                </button>
                <Sidebar activeView={activeView} onSetActiveView={(view, options) => { handleSetActiveView(view, options); setMobileMenuOpen(false); }} systemStatus={companyStatus} />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        <section className="min-w-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
          <AnimatePresence mode="wait">
            <motion.div key={`${activeView}-${activeConstructoraId}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={viewTransition}>
              <ActiveView
                activeConstructora={activeConstructora}
                activeConstructoraId={activeConstructoraId}
                activePreset={activePreset}
                activeView={activeView}
                constructoraCreateSignal={constructoraCreateSignal}
                onSetActiveView={handleSetActiveView}
                onStatusChange={setCompanyStatus}
              />
            </motion.div>
          </AnimatePresence>
        </section>
      </div>
    </main>
  );
}

function ActiveView({ activeConstructora, activeConstructoraId, activePreset, activeView, constructoraCreateSignal, onSetActiveView, onStatusChange }) {
  if (activeView === "central_operativa") return <CentralOperativaPage />;
  if (activeView === "ingesta_inteligente") return <IngestaInteligentePage />;
  if (activeView === "reportes_regulatorios") return <ReportesRegulatoriosPage />;
  if (activeView === "copiloto_ambiental") return <CopilotoAmbientalPage />;
  if (activeView === "dashboard") return <DashboardPage onSetActiveView={onSetActiveView} onStatusChange={onStatusChange} />;
  if (activeView === "inteligencia") return <IntelligencePage />;
  if (activeView === "emisiones") return <EmisionesView onSetActiveView={onSetActiveView} />;
  if (activeView === "acciones") return <AccionesAmbientalesPage />;
  if (activeView === "operacion") return <OperacionPage />;
  if (activeView === "evidencias") return <EvidenciasPage />;
  if (activeView === "reportes") return <ReportesView activeConstructoraId={activeConstructoraId} activeConstructora={activeConstructora} onSetActiveView={onSetActiveView} />;
  if (activeView === "administracion") return <AdministracionPage onSetActiveView={onSetActiveView} openCreateSignal={constructoraCreateSignal} />;

  if (activeView === "constructoras") return <ConstructorasView onSetActiveView={onSetActiveView} openCreateSignal={constructoraCreateSignal} />;
  if (activeView === "obras") return <ObrasView />;
  if (activeView === "etapas") return <EtapasObraView />;
  if (activeView === "factores") return <FactoresView onSetActiveView={onSetActiveView} />;
  if (activeView === "importaciones") return <ImportacionesView />;
  if (activeView === "usuarios") return <UsuariosPage />;
  if (activeView === "configuracion") return <ConfiguracionPage />;
  if (activeView === "recepcion_trozas") return <RecepcionTrozasPage />;
  if (activeView === "produccion") return <ProduccionAserraderoPage />;
  if (activeView === "secado") return <SecadoAserraderoPage />;
  if (activeView === "energia") return <EnergiaAserraderoPage />;
  if (activeView === "transporte_forestal") return <TransporteForestalPage />;
  if (activeView === "lotes_forestales") return <LotesForestalesPage />;
  if (activeView === "residuos_subproductos") return <ResiduosSubproductosPage />;

  if (placeholderViews[activeView]) {
    const [title, description] = placeholderViews[activeView];
    return <PresetComingSoon title={title} description={description} presetName={activePreset.name} items={["Datos operacionales", "Indicadores ambientales", "Recomendaciones por proceso"]} />;
  }

  return <DashboardPage onSetActiveView={onSetActiveView} onStatusChange={onStatusChange} />;
}

export default App;
