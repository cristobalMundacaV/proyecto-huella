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
import KpiCard from "@/shared/components/KpiCard";
import LoginPage from "@/features/auth/pages/LoginPage";
import ExecutiveSummary from "@/features/dashboard/components/ExecutiveSummary";
import RealtimeIotMonitoring from "@/features/dashboard/components/RealtimeIotMonitoring";
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
import {
  getConstructoraDashboard,
  getConstructoraEmisiones,
  getConstructoraEstado,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { optimizeScenario } from "@/features/dashboard/utils/optimizer";
import { calculateRiskProfile } from "@/features/dashboard/utils/risk";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { useAuth } from "@/features/auth/context/AuthContext";
import {
  constructionCategories,
  getConstructionCategoryLabel,
} from "@/features/obras/utils/constructionEmissionCategories";

const viewTransition = {
  duration: 0.24,
  ease: [0.22, 1, 0.36, 1],
};

const DASHBOARD_REFRESH_INTERVAL_MS = 10000;

const categoryInsightRules = {
  Materiales:
    "Materiales concentra el mayor impacto ambiental. Revisa hormigón, acero, áridos y proveedores para evaluar alternativas de menor carbono incorporado.",
  Transporte:
    "Transporte aparece como foco critico. Evalúa proveedores más cercanos, consolidación de viajes y reducción de kilómetros recorridos.",
  Maquinaria:
    "Maquinaria concentra emisiones relevantes. Controlar ralentí­, consumo por equipo y mantención puede reducir el impacto operativo.",
  Energia:
    "Energia es una fuente relevante. Revisa uso de generadores, consumo electrico y posibilidades de conexion temporal a red.",
  Residuos:
    "Residuos aparece como foco de impacto. Separar residuos valorizables y mejorar trazabilidad de retiro puede reducir disposición final.",
  Agua:
    "Agua requiere seguimiento operativo. Monitorear consumo por etapa ayuda a detectar desviaciones y mejorar eficiencia.",
  Otros:
    "Agrega registros de emision para identificar las fuentes criticas de la obra.",
};

const worksiteReductionSteps = [
  {
    title: "Optimizar rutas de despacho y transporte",
    detail:
      "Planificar mejor los recorridos, evitar viajes vací­os, combinar cargas y priorizar rutas más cortas o con menos tráfico para reducir kilómetros recorridos y consumo de combustible.",
  },
  {
    title: "Mejorar eficiencia de maquinaria y camiones",
    detail:
      "Implementar mantención preventiva, utilizar neumáticos adecuados, mantener los motores correctamente calibrados y reducir el tiempo de ralentí­.",
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
    title: "Planificar mejor logistica y secuencia de obra",
    detail:
      "Acercar puntos de logistica, reducir movimientos internos y evitar traslados repetidos entre frentes.",
  },
  {
    title: "Medir litros por frente",
    detail:
      "Separar consumo por preparacion, transporte, maquinaria, energia y residuos.",
  },
];

function App() {
  const [data, setData] = useState(null);
  const [dashboardError, setDashboardError] = useState("");
  const [dashboardEmissionKpis, setDashboardEmissionKpis] = useState(null);
  const [companyStatus, setCompanyStatus] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeView, setActiveView] = useState("dashboard");
  const [ConstructoraCreateSignal, setConstructoraCreateSignal] = useState(0);
  const { loadingAuth, user } = useAuth();
  const { activeConstructora, activeConstructoraId, loadingConstructoras } = useConstructoraActiva();

  const handleSetActiveView = useCallback((view, options = {}) => {
    setActiveView(view);
    if (options.openCreateConstructora) {
      setConstructoraCreateSignal((currentSignal) => currentSignal + 1);
    }
  }, []);

  const applyDashboardData = useCallback((dashboardData) => {
    setData(dashboardData);
    setDashboardError("");
  }, []);

  const refreshInternalDashboard = useCallback(async () => {
    if (!activeConstructoraId) {
      setData(null);
      setDashboardEmissionKpis(null);
      setCompanyStatus(null);
      return null;
    }

    const [dashboardResult, estadoResult, emissionsResult] = await Promise.allSettled([
      getConstructoraDashboard(activeConstructoraId, { light: "1" }),
      getConstructoraEstado(activeConstructoraId),
      getConstructoraEmisiones(activeConstructoraId, { page: 1, page_size: 1 }),
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
  }, [activeConstructoraId, applyDashboardData]);

  useEffect(() => {
    if (activeView !== "dashboard" || !activeConstructoraId) {
      if (!activeConstructoraId) {
        window.setTimeout(() => {
          setData(null);
          setDashboardEmissionKpis(null);
          setCompanyStatus(null);
        }, 0);
      }

      return;
    }

    let isCancelled = false;
    let timeoutId;

    const loadDashboard = async () => {
      if (document.visibilityState === "hidden") {
        timeoutId = window.setTimeout(loadDashboard, DASHBOARD_REFRESH_INTERVAL_MS);
        return;
      }

      try {
        const [dashboardResult, estadoResult, emissionsResult] = await Promise.allSettled([
          getConstructoraDashboard(activeConstructoraId, { light: "1" }),
          getConstructoraEstado(activeConstructoraId),
          getConstructoraEmisiones(activeConstructoraId, { page: 1, page_size: 1 }),
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
            error.response?.data?.error || "No se pudieron cargar los datos de la constructora activa."
          );
        }
      } finally {
        if (!isCancelled) {
          timeoutId = window.setTimeout(loadDashboard, DASHBOARD_REFRESH_INTERVAL_MS);
        }
      }
    };

    loadDashboard();

    return () => {
      isCancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [activeConstructoraId, activeView, applyDashboardData]);

  const handleExportReport = () => {
    window.print();
  };

  const dashboardTotalEmissions = Number(data?.total_emisiones || 0);
  const dashboardStoredCarbon = Number(data?.balance_ambiental_total || 0);
  const dashboardHasRows = Array.isArray(data?.datos) && data.datos.length > 0;

  const recommendedScenario = useMemo(() => {
    if (dashboardHasRows) {
      const optimized = optimizeScenario(data.datos || []);
      return {
        ...optimized,
        currentTotal: dashboardTotalEmissions,
        simulatedTotal: dashboardTotalEmissions * (1 - Number(optimized.reductionPct || 0) / 100),
      };
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

  if (!activeConstructora) {
      // Show the constructoras page and open the create modal so the user can create a company
      return (
        <div className="min-h-screen bg-[var(--bg-main)] p-6 text-[var(--text-main)] sm:p-10">
          <ConstructorasView onSetActiveView={handleSetActiveView} initialOpenCreate={true} />
        </div>
      );
    }

    if (!data) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[var(--bg-main)] text-[var(--text-main)]">
          {dashboardError || "Cargando tablero de constructora..."}
        </div>
      );
    }
const dashboardRows = Array.isArray(data?.datos) ? data.datos : [];

const emisionesPorConstructora = data?.emisiones_por_Constructora ?? {};
const emisionesPorActividad = data?.emisiones_por_fuente_emision ?? data?.top_fuentes_criticas ?? {};
const emisionesPorEtapa =
  data?.emisiones_por_etapa ?? data?.emisiones_por_unidad ?? {};

const registros_emision = Array.isArray(emisionesPorActividad)
  ? emisionesPorActividad.map((item) => ({
      fuente_emision: item.fuente_emision || item.source || "Sin fuente",
      emisiones: item.emisiones_kg_co2e || item.emisiones || 0,
      categoria: item.categoria || "Otros",
      obra: item.obra || item.work || item.obra_nombre || "Obra principal",
      etapa: item.obra_etapa || item.stage || item.etapa || "Sin etapa",
    }))
  : Object.entries(emisionesPorActividad).map(([fuente_emision, emisiones]) => ({
      fuente_emision,
      emisiones,
    }));

const etapas = Object.entries(emisionesPorEtapa).map(
  ([unidad, emisiones]) => ({
    unidad,
    emisiones,
  })
);

const fuenteCritica = data?.fuente_critica || registros_emision[0]?.fuente_emision || "Sin datos";
const unidadCritica = data?.etapa_critica || etapas[0]?.unidad || "Sin datos";
const safeDashboardData = {
  ...data,
  datos: dashboardRows,
  emisiones_por_Constructora: emisionesPorConstructora,
  emisiones_por_fuente_emision: emisionesPorActividad,
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
  registros: new Set(dashboardRows.map((row) => row.fuente_emision)).size,
};
const isDieselcriticalSource = String(fuenteCritica || "")
  .normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "")
  .toLowerCase()
  .includes("diesel");
const rowsWithCategories = dashboardRows.map((row) => ({
  ...row,
  categoria_visible: getConstructionCategoryLabel(row.categoria, row.fuente_emision),
}));
const totalEmissions = Number(safeDashboardData.total_emisiones || 0);
const emissionsByWork = Object.values(
  rowsWithCategories.reduce((accumulator, row) => {
    const workCode = row.codigo_obra || row.obra_codigo || row.obra_nombre || row.obra || "Obra principal";
    const current = accumulator[workCode] || {
      name: workCode,
      emissions: 0,
      surface: Number(row.superficie_m2 || row.superficie || 0),
      records: 0,
    };

    current.emissions += Number(row.emisiones || row.emisiones_kg_co2e || 0);
    current.records += 1;
    if (!current.surface) {
      current.surface = Number(row.superficie_m2 || row.superficie || 0);
    }
    accumulator[workCode] = current;
    return accumulator;
  }, {})
).sort((left, right) => right.emissions - left.emissions);
const criticalWork = emissionsByWork[0]?.name || "Sin datos";
const totalDeclaredSurface = emissionsByWork.reduce(
  (total, work) => total + Number(work.surface || 0),
  0
);
const backendCarbonIntensity = Number(data?.intensidad_carbono);
const carbonIntensity =
  Number.isFinite(backendCarbonIntensity) && backendCarbonIntensity > 0
    ? backendCarbonIntensity
    : totalDeclaredSurface > 0
      ? totalEmissions / totalDeclaredSurface
      : null;
const categoryDistribution = constructionCategories
  .map((category) => {
    const emissions = rowsWithCategories.reduce(
      (total, row) =>
        row.categoria_visible === category
          ? total + Number(row.emisiones || row.emisiones_kg_co2e || 0)
          : total,
      0
    );
    return {
      category,
      emissions,
      pct: totalEmissions > 0 ? (emissions / totalEmissions) * 100 : 0,
    };
  })
  .sort((left, right) => right.emissions - left.emissions);
const criticalCategory = categoryDistribution.find((item) => item.emissions > 0)?.category || "Sin datos";
const categoryInsight =
  totalEmissions > 0
    ? categoryInsightRules[criticalCategory] || categoryInsightRules.Otros
    : categoryInsightRules.Otros;
const emissionsByStage = Object.values(
  rowsWithCategories.reduce((accumulator, row) => {
    const stage = row.etapa_nombre || row.etapa || "Sin etapa";
    const current = accumulator[stage] || { stage, emissions: 0, records: 0 };
    current.emissions += Number(row.emisiones || row.emisiones_kg_co2e || 0);
    current.records += 1;
    accumulator[stage] = current;
    return accumulator;
  }, {})
).sort((left, right) => right.emissions - left.emissions);
const topSources = Object.values(
  rowsWithCategories.reduce((accumulator, row) => {
    const source = row.fuente_emision || "Sin fuente";
    const key = `${source}|${row.categoria_visible}|${row.codigo_obra || ""}|${row.etapa_nombre || ""}`;
    const current = accumulator[key] || {
      source,
      category: row.categoria_visible || "Otros",
      work: row.codigo_obra || row.obra_codigo || row.obra_nombre || row.obra || "Obra principal",
      stage: row.etapa_nombre || row.etapa || "Sin etapa",
      emissions: 0,
    };
    current.emissions += Number(row.emisiones || row.emisiones_kg_co2e || 0);
    accumulator[key] = current;
    return accumulator;
  }, {})
)
  .sort((left, right) => right.emissions - left.emissions)
  .slice(0, 5);
const environmentalStatus = getEnvironmentalStatus({
  categoryDistribution,
  evidenceBacked: null,
  rows: rowsWithCategories,
  totalEmissions,
});

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

      <section className="flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-12 overflow-y-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={`${activeView}-${activeConstructoraId}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={viewTransition}
          >
        {activeView === "obras" ? (
          <ObrasView />
        ) : activeView === "constructoras" ? (
          <ConstructorasView
            onSetActiveView={handleSetActiveView}
            openCreateSignal={ConstructoraCreateSignal}
          />
        ) : activeView === "etapas" ? (
          <EtapasObraView />
        ) : activeView === "reportes" ? (
          <ReportesView 
              activeConstructoraId={activeConstructoraId}
              activeConstructora={activeConstructora}
          />
        ) : activeView === "emisiones" ? (
          <EmisionesView onSetActiveView={handleSetActiveView} />
        ) : activeView === "factores" ? (
          <FactoresView />
        ) : activeView === "evidencias" ? (
          <EvidenciasPage />
        ) : activeView === "usuarios" ? (
          <UsuariosPage />
        ) : activeView === "configuracion" ? (
          <ConfiguracionPage />
        ) : activeView === "importaciones" ? (
          <ImportacionesView onImportConfirmed={refreshInternalDashboard} />
        ) : (

        <div className="stagger-in max-w-7xl mx-auto space-y-6 sm:space-y-8">
          <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl border border-emerald-200/80 bg-[linear-gradient(180deg,rgba(236,253,243,1),rgba(209,250,229,0.9))] p-3 shadow-[0_14px_30px_rgba(14,124,102,0.14)] ring-1 ring-white/70">
                <Database className="text-[var(--primary-dark)]" />
              </div>
              <div>
                <h1 className="text-3xl font-black tracking-tight sm:text-4xl">
                  Carbono Zero
                </h1>
                <p className="text-[var(--text-muted)]">
                  Convierte datos reales de obra en medición, trazabilidad y decisiones para reducir emisiones durante la ejecución del proyecto.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleExportReport}
              className="premium-button-primary inline-flex w-full items-center justify-center rounded-2xl px-5 py-3 text-sm font-bold shadow-[0_16px_32px_rgba(14,124,102,0.22)] sm:w-fit"
            >
              Exportar reporte
            </button>
          </header>

          <ExecutiveSummary
            fuenteCritica={fuenteCritica}
            unidadCritica={unidadCritica}
            optimizedScenario={recommendedScenario}
            reductionEquivalentKm={dieselReductionEquivalentKm}
            riskProfile={riskProfile}
            validationSummary={validationSummary}
          />

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-3">
            <KpiCard
              icon={<Activity />}
              title="Emisiones totales"
              value={`${formatNumber(totalEmissions)} kg CO2e`}
            />
            <KpiCard
              icon={<Factory />}
              title="Obra critica"
              value={criticalWork}
            />
            <KpiCard
              icon={<AlertTriangle />}
              title="Categorí­a critica"
              value={criticalCategory}
            />
            <KpiCard
              icon={<AlertTriangle />}
              title="Fuente critica"
              value={fuenteCritica}
            />
            <KpiCard
              icon={<Database />}
              title="Evidencia respaldada"
              value="Pendiente de vinculación"
            />
            <KpiCard
              icon={<Factory />}
              title="Intensidad de carbono"
              value={
                carbonIntensity != null
                  ? `${formatNumber(carbonIntensity, 2)} kg CO2e/m²`
                  : "Pendiente de superficie"
              }
            />
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-[0.95fr_1.05fr]">
            <InsightPanel
              environmentalStatus={environmentalStatus}
              insight={categoryInsight}
            />
            <DistributionPanel
              items={categoryDistribution}
              title="Emisiones por categorí­a"
              total={totalEmissions}
            />
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <StagePanel items={emissionsByStage} total={totalEmissions} />
            <TopSourcesPanel items={topSources} total={totalEmissions} />
          </section>

          <RealtimeIotMonitoring activeConstructoraId={activeConstructoraId} />

          {isDieselcriticalSource && (
            <section className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] ring-1 ring-white/40 sm:p-6">
              <div className="mb-5">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Pasos a seguir
                </p>
                <h2 className="mt-1 text-xl font-bold text-[var(--text-main)]">
                  Como reducir emisiones dentro de la operación.
                </h2>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {worksiteReductionSteps.map((step, index) => (
                  <div
                    key={step.title}
                    className="rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] p-4"
                  >
                    <p className="text-xs font-bold text-[var(--primary-dark)]">
                      Paso {index + 1}
                    </p>
                    <h3 className="mt-2 text-sm font-bold text-[var(--text-main)]">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
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

function getEnvironmentalStatus({ categoryDistribution, evidenceBacked, rows, totalEmissions }) {
  if (!rows.length || !totalEmissions) {
    return {
      label: "Sin datos",
      detail: "Aún no hay registros suficientes.",
      className: "border-slate-300 bg-slate-100 text-slate-700",
    };
  }

  const maxShare = Math.max(...categoryDistribution.map((item) => item.pct || 0), 0);
  const activeCategories = categoryDistribution.filter((item) => item.emissions > 0).length;

  if (evidenceBacked != null && evidenceBacked >= 50 && maxShare <= 50) {
    return {
      label: "Controlada",
      detail: "Sin concentración dominante y con documentación suficiente.",
      className: "border-[var(--border)] bg-[var(--success-bg)] text-[var(--primary-dark)]",
    };
  }

  if (maxShare > 60) {
    return {
      label: "critica",
      detail: "Una categorí­a concentra más del 60% de las emisiones.",
      className: "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]",
    };
  }

  if (activeCategories >= 3) {
    return {
      label: "En seguimiento",
      detail: "Existen registros distribuidos en varias categorí­as.",
      className: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
    };
  }

  return {
    label: "Inicial",
    detail: "Existen registros, pero aún falta trazabilidad por categorí­a.",
    className: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
  };
}

function InsightPanel({ environmentalStatus, insight }) {
  return (
    <section className="premium-card premium-card-interactive rounded-2xl bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] ring-1 ring-white/40 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
            Insight automático
          </p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--text-main)]">
            Acción prioritaria
          </h2>
        </div>
        <div className={`premium-card-interactive rounded-2xl border px-4 py-3 text-sm font-bold ${environmentalStatus.className}`}>
          <p>Estado ambiental de la obra</p>
          <p className="mt-1 text-lg">{environmentalStatus.label}</p>
        </div>
      </div>
      <p className="mt-4 leading-6 text-[var(--text-muted)]">{insight}</p>
      <p className="mt-3 text-sm font-medium text-[var(--text-muted)]">
        {environmentalStatus.detail}
      </p>
    </section>
  );
}

function DistributionPanel({ items, title, total }) {
  return (
    <section className="premium-card premium-card-interactive rounded-2xl bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] ring-1 ring-white/40 sm:p-6">
      <h2 className="text-xl font-semibold text-[var(--text-main)]">{title}</h2>
      <div className="mt-5 space-y-3">
        {items.map((item) => (
          <MetricBar
            key={item.category}
            label={item.category}
            pct={item.pct}
            value={`${formatNumber(item.emissions, 1)} kg CO2e`}
          />
        ))}
        {!total && (
          <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-sm text-[var(--text-muted)]">
            No hay registros de emision suficientes.
          </p>
        )}
      </div>
    </section>
  );
}

function StagePanel({ items, total }) {
  return (
    <section className="premium-card premium-card-interactive rounded-2xl bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] ring-1 ring-white/40 sm:p-6">
      <h2 className="text-xl font-semibold text-[var(--text-main)]">
        Emisiones por etapa de obra
      </h2>
      <div className="mt-5 space-y-3">
        {items.length ? (
          items.map((item) => (
            <MetricBar
              key={item.stage}
              detail={`${formatNumber(item.records, 0)} registros`}
              label={item.stage}
              pct={total > 0 ? (item.emissions / total) * 100 : 0}
              value={`${formatNumber(item.emissions, 1)} kg CO2e`}
            />
          ))
        ) : (
          <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-sm text-[var(--text-muted)]">
            Aún no hay etapas o frentes asociados a los registros.
          </p>
        )}
      </div>
    </section>
  );
}

function TopSourcesPanel({ items, total }) {
  return (
    <section className="premium-card premium-card-interactive rounded-2xl bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] ring-1 ring-white/40 sm:p-6">
      <h2 className="text-xl font-semibold text-[var(--text-main)]">Fuentes criticas</h2>
      <div className="mt-5 overflow-x-auto">
        <table className="premium-table w-full min-w-[720px] text-sm">
          <thead className="border-b border-[var(--border)] text-left text-[var(--text-muted)]">
            <tr>
              <th className="py-3 pr-4">Fuente de emision</th>
              <th className="px-4 py-3">Categorí­a</th>
              <th className="px-4 py-3">Obra / etapa</th>
              <th className="px-4 py-3 text-right">Emisiones kg CO2e</th>
              <th className="py-3 pl-4 text-right">% total</th>
            </tr>
          </thead>
          <tbody>
            {items.length ? (
              items.map((item) => (
                <tr key={`${item.source}-${item.work}-${item.stage}`} className="border-b border-[var(--border)] hover:bg-[var(--success-bg)]/60">
                  <td className="py-3 pr-4 font-semibold text-[var(--text-main)]">{item.source}</td>
                  <td className="px-4 py-3 text-[var(--text-muted)]">{item.category}</td>
                  <td className="px-4 py-3 text-[var(--text-muted)]">
                    {item.work} / {item.stage}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-[#075985]">
                    {formatNumber(item.emissions, 1)}
                  </td>
                  <td className="py-3 pl-4 text-right text-[var(--text-muted)]">
                    {formatNumber(total > 0 ? (item.emissions / total) * 100 : 0, 1)}%
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="5" className="py-8 text-center text-[var(--text-muted)]">
                  No hay registros de emision suficientes.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function MetricBar({ detail, label, pct, value }) {
  return (
    <div className="premium-card-interactive rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-[var(--text-main)]">{label}</p>
          {detail && <p className="mt-1 text-xs text-[var(--text-muted)]">{detail}</p>}
        </div>
        <div className="text-right">
          <p className="font-bold text-[#075985]">{value}</p>
          <p className="text-xs text-[var(--text-muted)]">{formatNumber(pct || 0, 1)}%</p>
        </div>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-[var(--primary)]"
          style={{ width: `${Math.max(0, Math.min(100, pct || 0))}%` }}
        />
      </div>
    </div>
  );
}
