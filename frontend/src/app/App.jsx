import { useCallback, useState } from "react";
import { Menu, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import DashboardPage from "@/core/dashboard/DashboardPage";
import Sidebar from "@/layouts/Sidebar";
import PresetComingSoon from "@/shared/components/PresetComingSoon";
import LoginPage from "@/features/auth/pages/LoginPage";
import EmisionesView from "@/features/emisiones/EmisionesView";
import ConstructorasView from "@/features/constructoras/pages/ConstructorasPage";
import EvidenciasPage from "@/features/evidencias/pages/EvidenciasPage";
import ConfiguracionPage from "@/features/configuracion/pages/ConfiguracionPage";
import FactoresView from "@/features/factores/pages/FactoresPage";
import ImportacionesView from "@/features/importaciones/pages/ImportacionesPage";
import ObrasView from "@/features/obras/pages/ObrasPage";
import EtapasObraView from "@/features/etapas/pages/EtapasPage";
import ReportesView from "@/features/reportes/pages/ReportesView";
import UsuariosPage from "@/features/usuarios/pages/UsuariosPage";
import RecepcionTrozasPage from "@/presets/aserradero/pages/RecepcionTrozasPage";
import ProduccionAserraderoPage from "@/presets/aserradero/pages/ProduccionAserraderoPage";
import SecadoAserraderoPage from "@/presets/aserradero/pages/SecadoAserraderoPage";
import EnergiaAserraderoPage from "@/presets/aserradero/pages/EnergiaAserraderoPage";
import TransporteForestalPage from "@/presets/aserradero/pages/TransporteForestalPage";
import ResiduosSubproductosPage from "@/presets/aserradero/pages/ResiduosSubproductosPage";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { useAuth } from "@/features/auth/context/AuthContext";
import { DEFAULT_PRESET_KEY, getActivePreset } from "@/presets/registry";

const viewTransition = {
  duration: 0.24,
  ease: [0.22, 1, 0.36, 1],
};

const presetPlaceholderViews = {
  flota: {
    title: "Flota",
    description: "Modulo para administrar vehiculos, capacidad, estado operativo y atributos relevantes para emisiones.",
    items: ["Vehiculos y capacidad", "Estado operativo", "Clasificacion por tipo"],
  },
  viajes: {
    title: "Viajes",
    description: "Modulo para registrar viajes, cargas, origen, destino y actividad logistica asociada.",
    items: ["Origen y destino", "Carga transportada", "Eventos por viaje"],
  },
  combustible: {
    title: "Combustible",
    description: "Modulo para controlar consumos, cargas, rendimiento y conciliacion con viajes o unidades de flota.",
    items: ["Cargas de combustible", "Rendimiento por unidad", "Conciliacion operacional"],
  },
  rutas: {
    title: "Rutas",
    description: "Modulo para gestionar rutas frecuentes, kilometraje, tramos criticos y oportunidades de optimizacion.",
    items: ["Rutas frecuentes", "Kilometraje por tramo", "Oportunidades de optimizacion"],
  },
  mantenciones: {
    title: "Mantenciones",
    description: "Modulo para planificar mantenciones, registrar intervenciones y relacionarlas con eficiencia y disponibilidad.",
    items: ["Plan de mantencion", "Intervenciones realizadas", "Disponibilidad de flota"],
  },
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
    if (options.openCreateConstructora) {
      setConstructoraCreateSignal((currentSignal) => currentSignal + 1);
    }
  }, []);

  if (loadingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-main)] text-[var(--text-main)]">
        Cargando sesion...
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  if (loadingConstructoras) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-main)] text-[var(--text-main)]">
        Cargando constructoras...
      </div>
    );
  }

  if (!activeConstructora && activeView === "emisiones") {
    return (
      <main className="flex min-h-screen flex-col bg-[var(--bg-main)] text-[var(--text-main)] lg:flex-row">
        <div className="hidden lg:block">
          <Sidebar activeView={activeView} onSetActiveView={handleSetActiveView} systemStatus={companyStatus} />
        </div>
        <section className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-10 lg:py-12">
          <EmisionesView onSetActiveView={handleSetActiveView} />
        </section>
      </main>
    );
  }

  if (!activeConstructora) {
    return (
      <div className="min-h-screen bg-[var(--bg-main)] p-6 text-[var(--text-main)] sm:p-10">
        <ConstructorasView onSetActiveView={handleSetActiveView} initialOpenCreate />
      </div>
    );
  }

  return (
    <main className="flex min-h-screen flex-col bg-[var(--bg-main)] text-[var(--text-main)] lg:flex-row">
      <button
        type="button"
        onClick={() => setMobileMenuOpen(true)}
        className="fixed right-4 top-4 z-50 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)]/95 p-3 text-[var(--text-main)] shadow-[var(--shadow-card)] backdrop-blur lg:hidden"
      >
        <Menu size={22} />
      </button>

      {user?.is_demo && (
        <div className="fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-full border border-amber-300/30 bg-amber-300/10 px-4 py-2 text-xs font-bold uppercase tracking-wide text-amber-100 shadow-xl backdrop-blur">
          Modo demo: solo lectura
        </div>
      )}

      <div className="hidden lg:block">
        <Sidebar activeView={activeView} onSetActiveView={handleSetActiveView} systemStatus={companyStatus} />
      </div>

      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            className="fixed inset-0 z-50 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            <motion.div
              className="absolute inset-0 bg-slate-950/30 backdrop-blur-sm"
              onClick={() => setMobileMenuOpen(false)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />

            <motion.div
              className="absolute right-0 top-0 h-full w-[85vw] max-w-sm overflow-y-auto border-l border-white/10 bg-[var(--sidebar)] shadow-2xl"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
            >
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="absolute right-4 top-4 rounded-2xl border border-white/10 bg-white/10 p-3 text-slate-200"
              >
                <X size={20} />
              </button>

              <Sidebar
                activeView={activeView}
                onSetActiveView={(view, options) => {
                  handleSetActiveView(view, options);
                  setMobileMenuOpen(false);
                }}
                systemStatus={companyStatus}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <section className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-10 lg:py-12">
        <AnimatePresence mode="wait">
          <motion.div
            key={`${activeView}-${activeConstructoraId}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={viewTransition}
          >
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
    </main>
  );
}

function ActiveView({
  activeConstructora,
  activeConstructoraId,
  activePreset,
  activeView,
  constructoraCreateSignal,
  onSetActiveView,
  onStatusChange,
}) {
  if (activeView === "dashboard") {
    return <DashboardPage onStatusChange={onStatusChange} />;
  }

  if (activeView === "obras") return <ObrasView />;

  if (activeView === "constructoras") {
    return (
      <ConstructorasView
        onSetActiveView={onSetActiveView}
        openCreateSignal={constructoraCreateSignal}
      />
    );
  }

  if (activeView === "etapas") return <EtapasObraView />;
  if (activeView === "reportes") {
    return (
      <ReportesView
        activeConstructoraId={activeConstructoraId}
        activeConstructora={activeConstructora}
        onSetActiveView={onSetActiveView}
      />
    );
  }
  if (activeView === "emisiones") return <EmisionesView onSetActiveView={onSetActiveView} />;
  if (activeView === "factores") return <FactoresView />;
  if (activeView === "evidencias") return <EvidenciasPage />;
  if (activeView === "usuarios") return <UsuariosPage />;
  if (activeView === "configuracion") return <ConfiguracionPage />;
  if (activeView === "importaciones") return <ImportacionesView />;
  if (activeView === "recepcion_trozas") return <RecepcionTrozasPage />;
  if (activeView === "produccion") return <ProduccionAserraderoPage />;
  if (activeView === "secado") return <SecadoAserraderoPage />;
  if (activeView === "energia") return <EnergiaAserraderoPage />;
  if (activeView === "transporte_forestal") return <TransporteForestalPage />;
  if (activeView === "residuos_subproductos") return <ResiduosSubproductosPage />;

  if (presetPlaceholderViews[activeView]) {
    return (
      <PresetComingSoon
        title={presetPlaceholderViews[activeView].title}
        description={presetPlaceholderViews[activeView].description}
        presetName={activePreset.name}
        items={presetPlaceholderViews[activeView].items}
      />
    );
  }

  return <DashboardPage onStatusChange={onStatusChange} />;
}

export default App;
