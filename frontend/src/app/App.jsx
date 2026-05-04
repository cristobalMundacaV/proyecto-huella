import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Database,
  Factory,
  Menu,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AnimatePresence, motion } from "framer-motion";

import Sidebar from "@/layouts/Sidebar";
import ChartCard from "@/shared/components/ChartCard";
import DataTable from "@/shared/components/DataTable";
import EmptyState from "@/shared/components/EmptyState";
import KpiCard from "@/shared/components/KpiCard";
import AiAdvisor from "@/features/dashboard/components/AiAdvisor";
import ExecutiveSummary from "@/features/dashboard/components/ExecutiveSummary";
import EmisionesView from "@/features/emisiones/EmisionesView";
import EmpresasView from "@/features/empresas/pages/EmpresasPage";
import FactoresView from "@/features/factores/pages/FactoresPage";
import ImportacionesView from "@/features/importaciones/pages/ImportacionesPage";
import LotesView from "@/features/lotes/pages/LotesPage";
import UnidadesOperativasView from "@/features/unidades/pages/UnidadesPage";
import ReportesView from "@/features/reportes/pages/ReportesView";
import {
  api,
  getAiAdvisor,
  getEmpresaDashboard,
  getEmpresaEstado,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { optimizeScenario } from "@/features/dashboard/utils/optimizer";
import { calculateRiskProfile } from "@/features/dashboard/utils/risk";
import { useEmpresaActiva } from "@/features/empresas/context/EmpresaActivaContext";

const tooltipContentStyle = {
  backgroundColor: "#0F172A",
  border: "1px solid #1E293B",
  borderRadius: "12px",
  color: "#F8FAFC",
};

const horizontalActiveBarStyle = {
  fill: "#CBD5E1",
  fillOpacity: 0.55,
  radius: [0, 10, 10, 0],
};

const viewTransition = {
  duration: 0.24,
  ease: [0.22, 1, 0.36, 1],
};

function truncateChartLabel(value) {
  const text = String(value || "");
  return text.length > 28 ? `${text.slice(0, 28)}...` : text;
}

function getBarSizeForRowCount(rowCount) {
  if (rowCount <= 1) {
    return 34;
  }

  if (rowCount <= 2) {
    return 30;
  }

  if (rowCount <= 4) {
    return 24;
  }

  return 18;
}

function App() {
  const [data, setData] = useState(null);
  const [dashboardError, setDashboardError] = useState("");
  const [companyStatus, setCompanyStatus] = useState(null);
  const [aiAnalysis, setAiAnalysis] = useState("");
  const [aiSource, setAiSource] = useState("");
  const [loadingAi, setLoadingAi] = useState(false);
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
    setAiAnalysis("");
    setAiSource("");
  }, []);

  const refreshInternalDashboard = useCallback(async () => {
    if (!activeEmpresaId) {
      setData(null);
      setCompanyStatus(null);
      return null;
    }

    const [dashboardResponse, estadoResponse] = await Promise.all([
      getEmpresaDashboard(activeEmpresaId),
      getEmpresaEstado(activeEmpresaId),
    ]);

    applyDashboardData(dashboardResponse);
    setCompanyStatus(estadoResponse);
    return dashboardResponse;
  }, [activeEmpresaId, applyDashboardData]);

  useEffect(() => {
    if (activeView !== "dashboard" || !activeEmpresaId) {
      if (!activeEmpresaId) {
        setData(null);
        setCompanyStatus(null);
      }

      return;
    }

    let isCancelled = false;

    const loadDashboard = async () => {
      try {
        const [dashboardResponse, estadoResponse] = await Promise.all([
          getEmpresaDashboard(activeEmpresaId),
          getEmpresaEstado(activeEmpresaId),
        ]);
        if (!isCancelled) {
          applyDashboardData(dashboardResponse);
          setCompanyStatus(estadoResponse);
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

  const recommendedScenario = useMemo(
    () => (data ? optimizeScenario(data.datos || []) : null),
    [data]
  );

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

const empresas = Object.entries(emisionesPorEmpresa).map(
  ([empresa, emisiones]) => ({
    empresa,
    emisiones,
  })
);

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

const empresaBarSize = getBarSizeForRowCount(empresas.length);
const actividadBarSize = getBarSizeForRowCount(actividades.length);
const unidadBarSize = getBarSizeForRowCount(unidades.length);

const empresaCritica = data?.empresa_critica || data?.empresa_nombre || empresas[0]?.empresa || "Sin datos";
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

const validationSummary = {
  records: dashboardRows.length,
  errors: 0,
  activities: new Set(dashboardRows.map((row) => row.actividad)).size,
};
  const formatTooltipValue = (value) => [
    `${formatNumber(value)} kg CO2e`,
    "Emisiones",
  ];

  const handleAiAnalysis = async () => {
    try {
      setLoadingAi(true);
      const response = await getAiAdvisor({
        total_emisiones: safeDashboardData.total_emisiones,
        unidad_critica: unidadCritica,
        actividad_critica: actividadCritica,
        simulacion: null,
        optimizacion: recommendedScenario,
      });

      setAiAnalysis(response.analisis);
      setAiSource(response.fuente);
    } catch (error) {
      console.error(error);
      setAiAnalysis(
        error.response?.data?.error || "No se pudo generar el analisis IA."
      );
      setAiSource("");
    } finally {
      setLoadingAi(false);
    }
  };

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
                <h1 className="text-3xl sm:text-4xl font-bold">Huella</h1>
                <p className="text-slate-400">
                  Inteligencia para medir, analizar y optimizar la huella de
                  carbono empresarial.
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
            empresaCritica={empresaCritica}
            unidadCritica={unidadCritica}
            optimizedScenario={recommendedScenario}
            riskProfile={riskProfile}
            validationSummary={validationSummary}
          />

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-4">
            <KpiCard
              icon={<Activity />}
              title="Emisiones Totales"
              value={`${formatNumber(safeDashboardData.total_emisiones)} kg CO2e`}
            />
            <KpiCard
              icon={<Factory />}
              title="Unidad Critica"
              value={unidadCritica}
            />
            <KpiCard
              icon={<AlertTriangle />}
              title="Actividad Critica"
              value={actividadCritica}
            />
            <KpiCard
              icon={<AlertTriangle />}
              title="Score de Riesgo"
              value={`${formatNumber(riskProfile.score, 0)}/100`}
              detail={riskProfile.label}
              tone={riskProfile}
            />
          </section>

          <section className="rounded-3xl bg-emerald-400/10 border border-emerald-400/20 p-4 sm:p-6">
            <h2 className="text-xl font-semibold mb-2">Insight automatico</h2>
            <p className="text-emerald-300">
              La actividad <strong>{actividadCritica}</strong> concentra el
              mayor impacto ambiental de los datos internos analizados.
            </p>
          </section>

          <AiAdvisor
            aiAnalysis={aiAnalysis}
            aiSource={aiSource}
            loadingAi={loadingAi}
            onGenerateAnalysis={handleAiAnalysis}
          />

          <section className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
            <ChartCard title="Emisiones por unidad operativa">
              <div className="h-64 sm:h-72 lg:h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={unidades}
                    layout="vertical"
                    margin={{ top: 10, right: 10, left: 24, bottom: 10 }}
                  >
                    <XAxis
                      type="number"
                      stroke="#94a3b8"
                      tickFormatter={formatNumber}
                    />
                    <YAxis
                      dataKey="unidad"
                      interval={0}
                      stroke="#94a3b8"
                      tick={{ fill: "#CBD5E1", fontSize: 11 }}
                      tickFormatter={truncateChartLabel}
                      type="category"
                      width={150}
                    />
                    <Tooltip
                      contentStyle={tooltipContentStyle}
                      cursor={false}
                      formatter={formatTooltipValue}
                      labelStyle={{ color: "#F8FAFC" }}
                      itemStyle={{ color: "#00D4AA" }}
                    />
                    <Bar
                      activeBar={horizontalActiveBarStyle}
                      dataKey="emisiones"
                      fill="#00D4AA"
                      barSize={unidadBarSize}
                      radius={[0, 10, 10, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard title="Emisiones por actividad">
              <div className="h-64 sm:h-72 lg:h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={actividades}
                    layout="vertical"
                    margin={{ top: 10, right: 10, left: 24, bottom: 10 }}
                  >
                    <XAxis
                      type="number"
                      stroke="#94a3b8"
                      tickFormatter={formatNumber}
                    />
                    <YAxis
                      dataKey="actividad"
                      interval={0}
                      stroke="#94a3b8"
                      tick={{ fill: "#CBD5E1", fontSize: 11 }}
                      tickFormatter={truncateChartLabel}
                      type="category"
                      width={150}
                    />
                    <Tooltip
                      contentStyle={tooltipContentStyle}
                      cursor={false}
                      formatter={formatTooltipValue}
                      labelStyle={{ color: "#F8FAFC" }}
                      itemStyle={{ color: "#00D4AA" }}
                    />
                    <Bar
                      activeBar={horizontalActiveBarStyle}
                      dataKey="emisiones"
                      fill="#38BDF8"
                      barSize={actividadBarSize}
                      radius={[0, 10, 10, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </section>

          <DataTable rows={safeDashboardData.datos} />
        </div>
        )}
          </motion.div>
        </AnimatePresence>
      </section>
    </main>
  );
}

export default App;
