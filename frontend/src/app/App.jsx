import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Database,
  Factory,
  Leaf,
  Menu,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import Sidebar from "@/layouts/Sidebar";
import EmptyState from "@/shared/components/EmptyState";
import KpiCard from "@/shared/components/KpiCard";
import ExecutiveSummary from "@/features/dashboard/components/ExecutiveSummary";
import EmisionesView from "@/features/emisiones/EmisionesView";
import EmpresasView from "@/features/empresas/pages/EmpresasPage";
import EvidenciasPage from "@/features/evidencias/pages/EvidenciasPage";
import ConfiguracionPage from "@/features/configuracion/pages/ConfiguracionPage";
import FactoresView from "@/features/factores/pages/FactoresPage";
import ImportacionesView from "@/features/importaciones/pages/ImportacionesPage";
import LotesView from "@/features/lotes/pages/LotesPage";
import UnidadesOperativasView from "@/features/unidades/pages/UnidadesPage";
import ReportesView from "@/features/reportes/pages/ReportesView";
import {
  getEmpresaDashboard,
  getEmpresaEmisiones,
  getEmpresaEstado,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { optimizeScenario } from "@/features/dashboard/utils/optimizer";
import { calculateRiskProfile } from "@/features/dashboard/utils/risk";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";

const viewTransition = {
  duration: 0.24,
  ease: [0.22, 1, 0.36, 1],
};

const woodReductionSteps = [
  {
    title: "Optimizar rutas de despacho y transporte",
    detail:
      "Planificar mejor los recorridos, evitar viajes vacíos, combinar cargas y priorizar rutas más cortas o con menos tráfico para reducir kilómetros recorridos y consumo de combustible.",
  },
  {
    title: "Mejorar eficiencia de maquinaria y camiones",
    detail:
      "Implementar mantención preventiva, utilizar neumáticos adecuados, mantener los motores correctamente calibrados y reducir el tiempo de ralentí.",
  },
  {
    title: "Controlar conduccion y operacion",
    detail:
      "Capacitar operadores para reducir aceleraciones bruscas, tiempos muertos y uso ineficiente de la maquinaria.",
  },
  {
    title: "Renovar flota gradualmente",
    detail:
      "Cambiar camiones o maquinaria antigua por modelos mas eficientes.",
  },
  {
    title: "Usar combustibles de menor emision",
    detail:
      "Evaluar biodiesel, diesel renovable u otras mezclas compatibles segun disponibilidad y costo.",
  },
  {
    title: "Electrificar operaciones internas especificas",
    detail:
      "Priorizar gruas, equipos de patio, montacargas o vehiculos livianos cuando sea viable.",
  },
  {
    title: "Planificar mejor cosecha y acopio",
    detail:
      "Acercar puntos de acopio, reducir movimientos internos y evitar traslados repetidos.",
  },
  {
    title: "Medir litros por actividad",
    detail:
      "Separar consumo por cosecha, despacho, transporte, maquinaria y vehiculos.",
  },
];

function App() {
  const [data, setData] = useState(null);
  const [dashboardError, setDashboardError] = useState("");
  const [dashboardEmissionKpis, setDashboardEmissionKpis] = useState(null);
  const [companyStatus, setCompanyStatus] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeView, setActiveView] = useState("dashboard");
  const [empresaCreateSignal, setEmpresaCreateSignal] = useState(0);
  const { activeEmpresa, activeEmpresaId, loadingEmpresas } = useEmpresaActiva();

  const handleSetActiveView = useCallback((view, options = {}) => {
    setActiveView(view);
    if (options.openCreateEmpresa) {
      setEmpresaCreateSignal((currentSignal) => currentSignal + 1);
    }
  }, []);

  const applyDashboardData = useCallback((dashboardData) => {
    setData(dashboardData);
    setDashboardError("");
  }, []);

  const refreshInternalDashboard = useCallback(async () => {
    if (!activeEmpresaId) {
      setData(null);
      setDashboardEmissionKpis(null);
      setCompanyStatus(null);
      return null;
    }

    const [dashboardResult, estadoResult, emissionsResult] = await Promise.allSettled([
      getEmpresaDashboard(activeEmpresaId, { light: "1" }),
      getEmpresaEstado(activeEmpresaId),
      getEmpresaEmisiones(activeEmpresaId, { page: 1, page_size: 1 }),
    ]);

    if (dashboardResult.status === "fulfilled") {
      applyDashboardData(dashboardResult.value);
    }

    if (estadoResult.status === "fulfilled") {
      setCompanyStatus(estadoResult.value);
    }

    if (emissionsResult.status === "fulfilled") {
      setDashboardEmissionKpis(emissionsResult.value?.kpis || null);
    } else {
      setDashboardEmissionKpis(null);
    }

    if (dashboardResult.status === "rejected" && estadoResult.status === "rejected") {
      throw dashboardResult.reason || estadoResult.reason;
    }

    return dashboardResult.status === "fulfilled" ? dashboardResult.value : null;
  }, [activeEmpresaId, applyDashboardData]);

  useEffect(() => {
    if (activeView !== "dashboard" || !activeEmpresaId) {
      if (!activeEmpresaId) {
        setData(null);
        setDashboardEmissionKpis(null);
        setCompanyStatus(null);
      }

      return;
    }

    let isCancelled = false;

    const loadDashboard = async () => {
      try {
        const [dashboardResult, estadoResult, emissionsResult] = await Promise.allSettled([
          getEmpresaDashboard(activeEmpresaId, { light: "1" }),
          getEmpresaEstado(activeEmpresaId),
          getEmpresaEmisiones(activeEmpresaId, { page: 1, page_size: 1 }),
        ]);

        if (!isCancelled) {
          if (dashboardResult.status === "fulfilled") {
            applyDashboardData(dashboardResult.value);
          }

          if (estadoResult.status === "fulfilled") {
            setCompanyStatus(estadoResult.value);
          }

          if (emissionsResult.status === "fulfilled") {
            setDashboardEmissionKpis(emissionsResult.value?.kpis || null);
          } else {
            setDashboardEmissionKpis(null);
          }

          if (dashboardResult.status === "rejected" && estadoResult.status === "rejected") {
            throw dashboardResult.reason || estadoResult.reason;
          }
        }
      } catch (error) {
        if (!isCancelled) {
          setDashboardError(
            error.response?.data?.error || "No se pudieron cargar los datos de la empresa activa."
          );
        }
      }
    };

    loadDashboard();

    return () => {
      isCancelled = true;
    };
  }, [activeEmpresaId, activeView, applyDashboardData]);

  const handleExportReport = () => {
    window.print();
  };

  const dashboardTotalEmissions = Number(data?.total_emisiones || 0);
  const dashboardStoredCarbon = Number(data?.co2_almacenado_total || 0);
  const dashboardHasRows = Array.isArray(data?.datos) && data.datos.length > 0;

  const recommendedScenario = useMemo(() => {
    if (dashboardHasRows) {
      return optimizeScenario(data.datos || []);
    }

    if (!dashboardTotalEmissions) {
      return null;
    }

    const estimatedReductionPct = 25;
    return {
      currentTotal: dashboardTotalEmissions,
      simulatedTotal: dashboardTotalEmissions * (1 - estimatedReductionPct / 100),
      reductionPct: estimatedReductionPct,
      dieselReduction: 0,
      electricityIncrease: 0,
      rows: [],
    };
  }, [dashboardHasRows, dashboardTotalEmissions, data]);

  if (loadingEmpresas) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        Cargando empresas...
      </div>
    );
  }

  if (!activeEmpresa && activeView === "emisiones") {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col lg:flex-row">
        <div className="hidden lg:block">
          <Sidebar
            activeView={activeView}
            onSetActiveView={handleSetActiveView}
            systemStatus={companyStatus}
          />
        </div>
        <section className="flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-12 overflow-y-auto">
          <EmisionesView onSetActiveView={handleSetActiveView} />
        </section>
      </main>
    );
  }

  if (!activeEmpresa) {
      // Show the empresas page and open the create modal so the user can create a company
      return (
        <div className="min-h-screen bg-slate-950 text-white p-6 sm:p-10">
          <EmpresasView onSetActiveView={handleSetActiveView} initialOpenCreate={true} />
        </div>
      );
    }

    if (!data) {
      return (
        <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
          {dashboardError || "Cargando tablero de empresa..."}
        </div>
      );
    }
const dashboardRows = Array.isArray(data?.datos) ? data.datos : [];

const emisionesPorEmpresa = data?.emisiones_por_empresa ?? {};
const emisionesPorActividad = data?.emisiones_por_actividad ?? {};
const emisionesPorUnidad =
  data?.emisiones_por_unidad_operativa ?? data?.emisiones_por_unidad ?? {};

const actividades = Object.entries(emisionesPorActividad).map(
  ([actividad, emisiones]) => ({
    actividad,
    emisiones,
  })
);

const unidades = Object.entries(emisionesPorUnidad).map(
  ([unidad, emisiones]) => ({
    unidad,
    emisiones,
  })
);

const actividadCritica = actividades[0]?.actividad || "Sin datos";
const unidadCritica = data?.unidad_critica || unidades[0]?.unidad || "Sin datos";
const safeDashboardData = {
  ...data,
  datos: dashboardRows,
  emisiones_por_empresa: emisionesPorEmpresa,
  emisiones_por_actividad: emisionesPorActividad,
  total_emisiones: data?.total_emisiones ?? 0,
};

const riskProfile = calculateRiskProfile(safeDashboardData, recommendedScenario);
const dieselReductionImpactKg = dashboardEmissionKpis
  ? Number(dashboardEmissionKpis.emisiones_totales || 0) *
    (Number(dashboardEmissionKpis.porcentaje_diesel || 0) / 100) *
    0.25
  : null;
const dieselReductionEquivalentKm =
  dieselReductionImpactKg != null ? dieselReductionImpactKg * 4 : null;

const validationSummary = {
  records: dashboardRows.length,
  errors: 0,
  activities: new Set(dashboardRows.map((row) => row.actividad)).size,
};
const isDieselCriticalActivity = String(actividadCritica || "")
  .normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "")
  .toLowerCase()
  .includes("diesel");

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col lg:flex-row">
      <button
        type="button"
        onClick={() => setMobileMenuOpen(true)}
        className="fixed right-4 top-4 z-50 rounded-2xl border border-slate-700 bg-slate-900/90 p-3 text-slate-100 shadow-xl backdrop-blur lg:hidden"
      >
        <Menu size={22} />
      </button>

      <div className="hidden lg:block">
        <Sidebar
          activeView={activeView}
          onSetActiveView={handleSetActiveView}
          systemStatus={companyStatus}
        />
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
            className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          <motion.div
            className="absolute right-0 top-0 h-full w-[85vw] max-w-sm overflow-y-auto border-l border-slate-800 bg-slate-900 shadow-2xl"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
          >
            <button
              type="button"
              onClick={() => setMobileMenuOpen(false)}
              className="absolute right-4 top-4 rounded-2xl border border-slate-700 bg-slate-950 p-3 text-slate-200"
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

      <section className="flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-12 overflow-y-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={`${activeView}-${activeEmpresaId}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={viewTransition}
          >
        {activeView === "lotes" ? (
          <LotesView />
        ) : activeView === "empresas" ? (
          <EmpresasView
            onSetActiveView={handleSetActiveView}
            openCreateSignal={empresaCreateSignal}
          />
        ) : activeView === "unidades" ? (
          <UnidadesOperativasView />
        ) : activeView === "reportes" ? (
          <ReportesView 
              activeEmpresaId={activeEmpresaId}
              activeEmpresa={activeEmpresa}
          />
        ) : activeView === "emisiones" ? (
          <EmisionesView onSetActiveView={handleSetActiveView} />
        ) : activeView === "factores" ? (
          <FactoresView />
        ) : activeView === "evidencias" ? (
          <EvidenciasPage />
        ) : activeView === "configuracion" ? (
          <ConfiguracionPage />
        ) : activeView === "importaciones" ? (
          <ImportacionesView onImportConfirmed={refreshInternalDashboard} />
        ) : (

        <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
          <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-emerald-400/10 border border-emerald-400/20">
                <Database className="text-emerald-400" />
              </div>
              <div>
                <h1 className="text-3xl sm:text-4xl font-bold">Carbono Zero</h1>
                <p className="text-slate-400">
                  Convierte los datos operativos de tu empresa en decisiones claras
                  para medir, reducir y respaldar su huella de carbono.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleExportReport}
              className="w-full sm:w-fit rounded-2xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm font-bold text-slate-200 transition hover:border-emerald-400/30 hover:bg-emerald-400/10 hover:text-emerald-200"
            >
              Exportar reporte
            </button>
          </header>

          <ExecutiveSummary
            actividadCritica={actividadCritica}
            unidadCritica={unidadCritica}
            optimizedScenario={recommendedScenario}
            reductionEquivalentKm={dieselReductionEquivalentKm}
            riskProfile={riskProfile}
            validationSummary={validationSummary}
          />

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-4">
            <KpiCard
              icon={<Activity />}
              title="Emisiones totales"
              value={`${formatNumber(safeDashboardData.total_emisiones)} kg CO2e`}
            />
            <KpiCard
              icon={<Factory />}
              title="Unidad prioritaria"
              value={unidadCritica}
            />
            <KpiCard
              icon={<AlertTriangle />}
              title="Actividad prioritaria"
              value={actividadCritica}
            />
            <KpiCard
              icon={<Leaf />}
              title="Carbono almacenado"
              value={`${formatNumber(dashboardStoredCarbon)} kg`}
            />
          </section>

          <section className="rounded-3xl bg-emerald-400/10 border border-emerald-400/20 p-4 sm:p-6">
            <h2 className="text-xl font-semibold mb-2">Insight automático</h2>
            <p className="text-emerald-300 leading-6">
              La actividad <strong>{actividadCritica}</strong> concentra el
              mayor impacto ambiental de los datos internos analizados. Aunque el
              combustible sea inevitable, las emisiones pueden bajar con eficiencia
              operacional, optimizacion logistica, mantencion, renovacion tecnologica
              y combustibles alternativos.
            </p>
          </section>

          {isDieselCriticalActivity && (
            <section className="rounded-3xl border border-emerald-400/20 bg-slate-900 p-4 shadow-xl sm:p-6">
              <div className="mb-5">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Pasos a seguir
                </p>
                <h2 className="mt-1 text-xl font-bold text-slate-100">
                  Como reducir emisiones dentro de la operación.
                </h2>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {woodReductionSteps.map((step, index) => (
                  <div
                    key={step.title}
                    className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4"
                  >
                    <p className="text-xs font-bold text-emerald-300">
                      Paso {index + 1}
                    </p>
                    <h3 className="mt-2 text-sm font-bold text-slate-100">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      {step.detail}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
        )}
          </motion.div>
        </AnimatePresence>
      </section>
    </main>
  );
}

export default App;
