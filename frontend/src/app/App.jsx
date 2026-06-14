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
import PresetComingSoon from "@/shared/components/PresetComingSoon";
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
import RecepcionTrozasPage from "@/presets/aserradero/pages/RecepcionTrozasPage";
import ProduccionAserraderoPage from "@/presets/aserradero/pages/ProduccionAserraderoPage";
import SecadoAserraderoPage from "@/presets/aserradero/pages/SecadoAserraderoPage";
import EnergiaAserraderoPage from "@/presets/aserradero/pages/EnergiaAserraderoPage";
import TransporteForestalPage from "@/presets/aserradero/pages/TransporteForestalPage";
import ResiduosSubproductosPage from "@/presets/aserradero/pages/ResiduosSubproductosPage";
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
import { DEFAULT_PRESET_KEY, getActivePreset, getPreset } from "@/presets/registry";

const viewTransition = {
  duration: 0.24,
  ease: [0.22, 1, 0.36, 1],
};

const DASHBOARD_REFRESH_INTERVAL_MS = 10000;

const presetPlaceholderViews = {
  recepcion_trozas: {
    title: "Recepcion de trozas",
    description: "Modulo para registrar origen, volumen, humedad y trazabilidad inicial de las trozas antes de entrar al proceso productivo.",
    items: ["Lotes de recepcion", "Origen y proveedor", "Volumen, humedad y especie"],
  },
  produccion: {
    title: "Produccion",
    description: "Modulo para organizar turnos, rendimiento, mermas y conversion de materia prima en productos del aserradero.",
    items: ["Turnos productivos", "Rendimiento por linea", "Mermas y productos terminados"],
  },
  secado: {
    title: "Secado",
    description: "Modulo para controlar ciclos de secado, consumo energetico, humedad final y eficiencia operacional.",
    items: ["Ciclos de secado", "Consumo energetico", "Humedad final y rechazos"],
  },
  energia: {
    title: "Energia",
    description: "Modulo para separar consumos electricos, termicos y combustibles asociados a la operacion del preset.",
    items: ["Consumos por fuente", "Medidores y periodos", "Indicadores de eficiencia"],
  },
  transporte_forestal: {
    title: "Transporte forestal",
    description: "Modulo para medir traslados forestales, distancias, cargas y consumo asociado a abastecimiento o despacho.",
    items: ["Viajes forestales", "Carga y distancia", "Combustible por traslado"],
  },
  residuos_subproductos: {
    title: "Residuos / Subproductos",
    description: "Modulo para trazabilidad de aserrin, corteza, despuntes, valorizacion y residuos no aprovechados.",
    items: ["Subproductos valorizados", "Residuos por destino", "Evidencia de retiro o uso"],
  },
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
  const [data, setData] = useState(null);
  const [dashboardError, setDashboardError] = useState("");
  const [dashboardEmissionKpis, setDashboardEmissionKpis] = useState(null);
  const [companyStatus, setCompanyStatus] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeView, setActiveView] = useState("dashboard");
  const [ConstructoraCreateSignal, setConstructoraCreateSignal] = useState(0);
  const { loadingAuth, user } = useAuth();
  const { activeConstructora, activeConstructoraId, loadingConstructoras } = useConstructoraActiva();
  const activePreset = getActivePreset(activeConstructora?.preset || "construccion");
  const dashboardIntelligence = activePreset.intelligence || getPreset(DEFAULT_PRESET_KEY).intelligence;

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
const emisionesPorActividad = data?.emisiones_por_fuente_emision ?? {};
const emisionesPorEtapa =
  data?.emisiones_por_etapa ?? data?.emisiones_por_unidad ?? {};

const registros_emision = Object.entries(emisionesPorActividad).map(
  ([fuente_emision, emisiones]) => ({
    fuente_emision,
    emisiones,
  })
);

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
  categoria_visible:
    dashboardIntelligence.resolveCategoryLabel?.(row.categoria, row.fuente_emision) ||
    row.categoria ||
    "Otros",
}));
const totalEmissions = Number(safeDashboardData.total_emisiones || 0);
const emissionsByWork = Object.values(
  rowsWithCategories.reduce((accumulator, row) => {
    const workCode = row.codigo_obra || row.obra || "Sin obra";
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
const carbonIntensity =
  totalDeclaredSurface > 0 ? totalEmissions / totalDeclaredSurface : null;
const dashboardCategories =
  dashboardIntelligence.categoryOrder?.length
    ? dashboardIntelligence.categoryOrder
    : activePreset.categories || [];
const categoryDistribution = dashboardCategories
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
        ) : activeView === "recepcion_trozas" ? (
          <RecepcionTrozasPage />
        ) : activeView === "produccion" ? (
          <ProduccionAserraderoPage />
        ) : activeView === "secado" ? (
          <SecadoAserraderoPage />
        ) : activeView === "energia" ? (
          <EnergiaAserraderoPage />
        ) : activeView === "transporte_forestal" ? (
          <TransporteForestalPage />
        ) : activeView === "residuos_subproductos" ? (
          <ResiduosSubproductosPage />
        ) : presetPlaceholderViews[activeView] ? (
          <PresetComingSoon
            title={presetPlaceholderViews[activeView].title}
            description={presetPlaceholderViews[activeView].description}
            presetName={activePreset.name}
            items={presetPlaceholderViews[activeView].items}
          />
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
                  Convierte datos reales de {activePreset.unitPluralLabel.toLowerCase()} en medición, trazabilidad y decisiones para reducir emisiones durante la operación.
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
              title={`${activePreset.unitLabel} critica`}
              value={criticalWork}
            />
            <KpiCard
              icon={<AlertTriangle />}
              title="Categoría critica"
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

          <OperationalIntelligenceModule
            data={safeDashboardData}
            intelligence={dashboardIntelligence}
            items={categoryDistribution}
            total={totalEmissions}
            environmentalStatus={environmentalStatus}
            riskProfile={riskProfile}
          />

          <section className="grid grid-cols-1 gap-4">
            <StageOperationalModule
              data={safeDashboardData}
              intelligence={dashboardIntelligence}
              items={emissionsByStage}
              total={totalEmissions}
              environmentalStatus={environmentalStatus}
              riskProfile={riskProfile}
            />
          </section>

          <CriticalDriversPanel
            categoryItems={categoryDistribution}
            intelligence={dashboardIntelligence}
            stageItems={emissionsByStage}
            total={totalEmissions}
          />

          <RealtimeIotMonitoring activeConstructoraId={activeConstructoraId} />

          {isDieselcriticalSource && Boolean(dashboardIntelligence.reductionSteps?.length) && (
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
                {(dashboardIntelligence.reductionSteps || []).map((step, index) => (
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
      label: "Crítica",
      detail: "Una categoría concentra más del 60% de las emisiones.",
      className: "border-[#F1B8B8] bg-[var(--danger-bg)] text-[#B42318]",
    };
  }

  if (activeCategories >= 3) {
    return {
      label: "En seguimiento",
      detail: "Existen registros distribuidos en varias categorías.",
      className: "border-[#B8D6DE] bg-[var(--info-bg)] text-[#075985]",
    };
  }

  return {
    label: "Inicial",
    detail: "Existen registros, pero aún falta trazabilidad por categoría.",
    className: "border-[#E1C56F] bg-[var(--warning-bg)] text-[#7A4F00]",
  };
}

const normalizeInsightText = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

function buildDocumentationNote(requiredItems = [], evidenceCoverage = 0, metrics = []) {
  const coverage = Number(evidenceCoverage || 0);
  const referenceItems = requiredItems.slice(0, 3);
  const referenceMetrics = metrics.slice(0, 2);
  const metricClause = referenceMetrics.length ? ` El sistema valida internamente ${referenceMetrics.join(", ")}.` : "";

  if (!referenceItems.length) {
    return {
      label: "Sin requerimientos documentales",
      text: "El sistema puede procesar la información con la evidencia disponible.",
    };
  }

  if (coverage >= 80) {
    return {
      label: "Diagnóstico respaldado",
      text: `La evidencia disponible permite sostener la lectura operativa con ${referenceItems.join(", ")}.${metricClause}`,
    };
  }

  if (coverage >= 50) {
    return {
      label: "Respaldo parcial",
      text: `El sistema aún debe contrastar ${referenceItems.join(", ")} para cerrar el diagnóstico.${metricClause}`,
    };
  }

  return {
    label: "Falta documentación",
    text: `El sistema no puede emitir un diagnóstico claro. Falta: ${referenceItems.join(", ")}.${metricClause}`,
  };
}

const emptyOperationalCopy = {
  relevanceLabel: "Monitoreo operativo",
  diagnosis: "Aun no hay inteligencia operativa configurada para este preset.",
  actions: [],
  evidence: [],
  metrics: [],
  nextStep: "Configura la inteligencia del preset para definir el siguiente paso operativo.",
};

function OperationalIntelligenceModule({ data, intelligence, items, total, environmentalStatus, riskProfile }) {
  const categoryOrder = intelligence.categoryOrder || [];
  const categoryIntelligence = intelligence.categoryIntelligence || {};
  const getCategoryLabel =
    intelligence.getOperationalCategoryLabel || ((category) => intelligence.categoryDisplayNames?.[category] || category || "Sin categoria");
  const getCategoryAccentStyle = intelligence.getCategoryAccentStyle || (() => "");
  const orderedItems = useMemo(() => {
    const itemMap = new Map(items.map((item) => [item.category, item]));

    return categoryOrder.map((category) => {
      const item = itemMap.get(category);

      return (
        item || {
          category,
          emissions: 0,
          pct: 0,
        }
      );
    });
  }, [categoryOrder, items]);

  const defaultCategory = useMemo(() => {
    const topItem = orderedItems.reduce((best, item) => {
      if (!best) {
        return item;
      }

      if ((item.pct || 0) > (best.pct || 0)) {
        return item;
      }

      if ((item.pct || 0) === (best.pct || 0) && (item.emissions || 0) > (best.emissions || 0)) {
        return item;
      }

      return best;
    }, null);

    return topItem?.category || categoryOrder[0] || "Otros";
  }, [categoryOrder, orderedItems]);

  const [selectedCategory, setSelectedCategory] = useState(defaultCategory);

  useEffect(() => {
    setSelectedCategory((currentCategory) =>
      orderedItems.some((item) => item.category === currentCategory)
        ? currentCategory
        : defaultCategory
    );
  }, [defaultCategory, orderedItems]);

  const selectedItem =
    orderedItems.find((item) => item.category === selectedCategory) ||
    orderedItems[0] || {
      category: categoryOrder[0] || "Otros",
      emissions: 0,
      pct: 0,
    };

  const selectedCopy = categoryIntelligence[selectedItem.category] || categoryIntelligence.Otros || emptyOperationalCopy;
  const documentationNote = buildDocumentationNote(
    selectedCopy.evidence,
    data?.evidencia_respaldada || 0,
    selectedCopy.metrics
  );

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl space-y-2">
          <p className="text-xs font-black uppercase tracking-[0.28em] text-[var(--text-muted)]">
            Inteligencia operativa
          </p>
          <h2 className="text-2xl font-black tracking-tight text-[var(--text-main)] sm:text-3xl">
            Módulo integrado de decisión ambiental
          </h2>
          <p className="max-w-2xl text-sm leading-6 text-[var(--text-muted)] sm:text-[15px]">
            Selecciona una categoría para interpretar su impacto, priorizar acciones, validar evidencia y definir el siguiente paso operativo.
          </p>
        </div>

        <div className={`rounded-2xl border px-4 py-3 text-sm font-bold ${environmentalStatus.className}`}>
          <p className="text-xs uppercase tracking-wide opacity-80">Estado ambiental general</p>
          <p className="mt-1 text-lg">{environmentalStatus.label}</p>
          <p className="mt-1 max-w-xs text-sm font-medium opacity-85">{environmentalStatus.detail}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-[28px] border border-[color-mix(in_srgb,var(--primary)_16%,white)] bg-[linear-gradient(180deg,rgba(248,250,252,0.98),rgba(255,255,255,0.99))] p-5 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-6">
          <div className="flex flex-col gap-3 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex-1 space-y-2 text-center sm:pr-6 sm:text-left">
              <div>
                <h3 className="text-2xl font-black tracking-tight text-[var(--text-main)]">
                  {getCategoryLabel(selectedItem.category)}
                </h3>
                <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
                  {selectedCopy.relevanceLabel}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 shadow-[0_8px_18px_rgba(15,23,42,0.04)]">
              <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
                Emisiones de la categoría
              </p>
              <p className="mt-1 text-3xl font-black text-[var(--text-main)]">
                {formatNumber(selectedItem.emissions, 1)} kg CO2e
              </p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
                {formatNumber(selectedItem.pct || 0, 1)}% del total
              </p>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)] sm:col-span-2">
              <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
                Diagnóstico operativo
              </p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">
                {selectedCopy.diagnosis}
              </p>
            </div>
          </div>

          <div className="mt-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
              Acciones recomendadas
            </p>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-[var(--text-main)]">
              {selectedCopy.actions.map((action) => (
                <li key={action} className="flex gap-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-100/80 p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
              Documentación requerida
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {documentationNote.label}: {documentationNote.text}
            </p>
          </div>

          <div className="mt-5 rounded-2xl border border-[color-mix(in_srgb,var(--primary)_18%,white)] bg-[linear-gradient(180deg,rgba(236,253,245,0.9),rgba(255,255,255,0.98))] p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--primary-dark)]">
              Siguiente paso recomendado
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">
              {selectedCopy.nextStep}
            </p>
          </div>
        </div>

        <div className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-5">
          <div className="border-b border-[var(--border)] pb-4">
            <p className="whitespace-nowrap text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)] sm:text-[11px]">
              Emisiones por categoría
            </p>
            <h3 className="mt-2 text-xl font-black text-[var(--text-main)]">
              Fuente de datos interactiva
            </h3>
            <p className="mt-2 max-w-2xl text-sm font-semibold leading-6 text-[var(--text-muted)]">
              Selecciona una categoría para actualizar la inteligencia.
            </p>
          </div>

          <div className="mt-4 space-y-3">
            {orderedItems.map((item) => (
              <MetricBar
                key={item.category}
                label={getCategoryLabel(item.category)}
                pct={item.pct}
                value={`${formatNumber(item.emissions, 1)} kg CO2e`}
                detail={
                  item.category === selectedItem.category
                    ? "Foco actual"
                    : item.pct > 0
                      ? "Disponible para intervención"
                      : "Monitoreo sin emisiones"
                }
                activeClassName={getCategoryAccentStyle(item.category)}
                isActive={item.category === selectedItem.category}
                onClick={() => setSelectedCategory(item.category)}
              />
            ))}

            {!total && (
              <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-4 text-sm text-[var(--text-muted)]">
                No hay registros de emision suficientes.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function StageOperationalModule({ data, intelligence, items, total, environmentalStatus, riskProfile }) {
  const stageOrder = intelligence.stageOrder || [];
  const stageIntelligence = intelligence.stageIntelligence || {};
  const getStageKey =
    intelligence.getOperationalStageKey || ((stage) => normalizeInsightText(stage).replace(/\s+/g, " "));
  const getStageLabel =
    intelligence.getOperationalStageLabel || ((stage) => intelligence.stageDisplayNames?.[getStageKey(stage)] || stage || "Sin etapa");
  const getStageRelevance =
    intelligence.getStageOperationalRelevance ||
    (() => ({ label: "Monitoreo operativo", score: 0, summary: "Mantener monitoreo y depuracion de datos." }));
  const orderedItems = useMemo(() => {
    const itemMap = new Map(items.map((item) => [getStageKey(item.stage), item]));

    const orderedStages = stageOrder.map((stage) => {
      const item = itemMap.get(getStageKey(stage));

      return (
        item || {
          stage,
          emissions: 0,
          records: 0,
        }
      );
    });

    const knownStageKeys = new Set(orderedStages.map((item) => getStageKey(item.stage)));
    const extraStages = items.filter((item) => !knownStageKeys.has(getStageKey(item.stage)));

    return [...orderedStages, ...extraStages];
  }, [getStageKey, items, stageOrder]);

  const defaultStage = useMemo(() => {
    const topItem = orderedItems.reduce((best, item) => {
      if (!best) {
        return item;
      }

      if ((item.emissions || 0) > (best.emissions || 0)) {
        return item;
      }

      return best;
    }, null);

    return getStageKey(topItem?.stage || stageOrder[0] || "Sin etapa");
  }, [getStageKey, orderedItems, stageOrder]);

  const [selectedStage, setSelectedStage] = useState(defaultStage);

  useEffect(() => {
    setSelectedStage((currentStage) =>
      orderedItems.some((item) => getStageKey(item.stage) === currentStage)
        ? currentStage
        : defaultStage
    );
  }, [defaultStage, orderedItems]);

  const selectedItem =
    orderedItems.find((item) => getStageKey(item.stage) === selectedStage) ||
    orderedItems[0] || {
      stage: stageOrder[0] || "Sin etapa",
      emissions: 0,
      records: 0,
    };

  const selectedKey = getStageKey(selectedItem.stage);
  const selectedCopy = stageIntelligence[selectedKey] || stageIntelligence[Object.keys(stageIntelligence)[0]] || emptyOperationalCopy;
  const documentationNote = buildDocumentationNote(
    selectedCopy.evidence,
    data?.evidencia_respaldada || 0,
    selectedCopy.metrics
  );
  const stageRank = Math.max(
    0,
    stageOrder.findIndex((stage) => getStageKey(stage) === selectedKey)
  );
  const relevance = getStageRelevance({
    emissions: selectedItem.emissions,
    pct: total > 0 ? (selectedItem.emissions / total) * 100 : 0,
    total,
    evidenceCoverage: data?.evidencia_respaldada || 0,
    environmentalLabel: environmentalStatus.label,
    stageRank,
    potentialReduction: riskProfile?.factors?.potentialReduction || 0,
  });

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl space-y-2">
          <p className="text-xs font-black uppercase tracking-[0.28em] text-[var(--text-muted)]">
            Inteligencia por etapa
          </p>
          <h2 className="text-2xl font-black tracking-tight text-[var(--text-main)] sm:text-3xl">
            Módulo operativo por proceso
          </h2>
          <p className="max-w-2xl text-sm leading-6 text-[var(--text-muted)] sm:text-[15px]">
            Selecciona un proceso para interpretar su impacto, priorizar acciones, validar evidencia y decidir el siguiente avance operativo.
          </p>
        </div>

        <div className={`rounded-2xl border px-4 py-3 text-sm font-bold ${environmentalStatus.className}`}>
          <p className="text-xs uppercase tracking-wide opacity-80">Estado operativo general</p>
          <p className="mt-1 text-lg">{environmentalStatus.label}</p>
          <p className="mt-1 max-w-xs text-sm font-medium opacity-85">{environmentalStatus.detail}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-[28px] border border-[color-mix(in_srgb,var(--primary)_16%,white)] bg-[linear-gradient(180deg,rgba(248,250,252,0.98),rgba(255,255,255,0.99))] p-5 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-6">
          <div className="flex flex-col gap-3 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex-1 space-y-2 text-center sm:pr-6 sm:text-left">
              <div>
                <h3 className="text-2xl font-black tracking-tight text-[var(--text-main)]">
                  {getStageLabel(selectedItem.stage)}
                </h3>
                <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
                  {selectedCopy.relevanceLabel}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 shadow-[0_8px_18px_rgba(15,23,42,0.04)]">
              <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
                Emisiones de la etapa
              </p>
              <p className="mt-1 text-3xl font-black text-[var(--text-main)]">
                {formatNumber(selectedItem.emissions, 1)} kg CO2e
              </p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
                {formatNumber(total > 0 ? (selectedItem.emissions / total) * 100 : 0, 1)}% del total
              </p>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)] sm:col-span-2">
              <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
                Diagnóstico de la fase
              </p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">
                {selectedCopy.diagnosis}
              </p>
            </div>
          </div>

          <div className="mt-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
              Acciones recomendadas
            </p>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-[var(--text-main)]">
              {selectedCopy.actions.map((action) => (
                <li key={action} className="flex gap-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-100/80 p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">
              Documentación requerida
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {documentationNote.label}: {documentationNote.text}
            </p>
          </div>

          <div className="mt-5 rounded-2xl border border-[color-mix(in_srgb,var(--primary)_18%,white)] bg-[linear-gradient(180deg,rgba(236,253,245,0.9),rgba(255,255,255,0.98))] p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
            <p className="text-xs font-black uppercase tracking-wide text-[var(--primary-dark)]">
              Siguiente paso recomendado
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">
              {selectedCopy.nextStep}
            </p>
          </div>
        </div>

        <div className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-5">
          <div className="border-b border-[var(--border)] pb-4">
            <p className="whitespace-nowrap text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)] sm:text-[11px]">
              Impacto de emisiones por proceso
            </p>
            <h3 className="mt-2 text-xl font-black text-[var(--text-main)]">
              Análisis interactivo por proceso
            </h3>
            <p className="mt-2 max-w-2xl text-sm font-semibold leading-6 text-[var(--text-muted)]">
              Selecciona un proceso para visualizar su diagnóstico operativo, nivel de impacto y recomendaciones específicas.
            </p>
          </div>

          <div className="mt-4 space-y-3">
            {orderedItems.map((item, index) => {
              const itemKey = getStageKey(item.stage);
              const itemCopy = stageIntelligence[itemKey];
              return (
                <MetricBar
                  key={item.stage}
                  label={getStageLabel(item.stage)}
                  pct={total > 0 ? (item.emissions / total) * 100 : 0}
                  value={`${formatNumber(item.emissions, 1)} kg CO2e`}
                  detail={
                    item.stage === selectedItem.stage
                      ? "Proceso seleccionado"
                      : item.emissions > 0
                        ? itemCopy?.relevanceLabel || `Proceso ${index + 1} de intervencion`
                        : "Monitoreo sin emisiones"
                  }
                  badge={item.stage === selectedItem.stage ? "SELECCIONADA" : null}
                  isActive={item.stage === selectedItem.stage}
                  onClick={() => setSelectedStage(itemKey)}
                />
              );
            })}

            {!total && (
              <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-4 text-sm text-[var(--text-muted)]">
                Aún no hay procesos asociados a los registros.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function CriticalDriversPanel({ categoryItems, intelligence, stageItems, total }) {
  const getCategoryLabel =
    intelligence.getOperationalCategoryLabel || ((category) => intelligence.categoryDisplayNames?.[category] || category || "Sin categoria");
  const getStageKey =
    intelligence.getOperationalStageKey || ((stage) => normalizeInsightText(stage).replace(/\s+/g, " "));
  const getStageLabel =
    intelligence.getOperationalStageLabel || ((stage) => intelligence.stageDisplayNames?.[getStageKey(stage)] || stage || "Sin etapa");
  const topCategories = categoryItems.slice(0, 3);
  const topStages = stageItems.slice(0, 3);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="flex flex-col gap-3 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.24em] text-[var(--text-muted)]">
            Fuentes críticas
          </p>
          <h2 className="mt-1 text-2xl font-black tracking-tight text-[var(--text-main)]">
            Top 3 de mayor impacto
          </h2>
        </div>
        <p className="max-w-2xl text-sm leading-6 text-[var(--text-muted)]">
          El sistema prioriza las tres categorías y los tres procesos con mayor impacto para orientar la lectura ejecutiva.
        </p>
      </div>

      <div className="mt-5 space-y-5">
        <div className="rounded-[28px] border border-[var(--border)] bg-[linear-gradient(180deg,rgba(248,250,252,0.98),rgba(255,255,255,0.99))] p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.22em] text-[var(--text-muted)]">
                Top 3 por categorías
              </p>
              <h3 className="mt-1 text-lg font-black text-[var(--text-main)]">
                Categorías con mayor huella
              </h3>
            </div>
            <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-3 py-1 text-[11px] font-black uppercase tracking-wide text-[var(--primary-dark)]">
              {topCategories.length} KPI
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
            {topCategories.length ? (
              topCategories.map((item, index) => (
                <CriticalKpiCard
                  key={item.category}
                  accent={index}
                  label={getCategoryLabel(item.category)}
                  value={`${formatNumber(item.emissions, 1)} kg CO2e`}
                  percent={total > 0 ? (item.emissions / total) * 100 : 0}
                  rank={index + 1}
                />
              ))
            ) : (
              <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-sm text-[var(--text-muted)] lg:col-span-3">
                No hay registros de emision suficientes.
              </p>
            )}
          </div>
        </div>

        <div className="rounded-[28px] border border-[var(--border)] bg-[linear-gradient(180deg,rgba(248,250,252,0.98),rgba(255,255,255,0.99))] p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.22em] text-[var(--text-muted)]">
                Top 3 por procesos
              </p>
              <h3 className="mt-1 text-lg font-black text-[var(--text-main)]">
                Procesos con mayor impacto
              </h3>
            </div>
            <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-3 py-1 text-[11px] font-black uppercase tracking-wide text-[var(--primary-dark)]">
              {topStages.length} KPI
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
            {topStages.length ? (
              topStages.map((item, index) => (
                <CriticalKpiCard
                  key={item.stage}
                  accent={index}
                  label={getStageLabel(item.stage)}
                  value={`${formatNumber(item.emissions, 1)} kg CO2e`}
                  percent={total > 0 ? (item.emissions / total) * 100 : 0}
                  rank={index + 1}
                />
              ))
            ) : (
              <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-sm text-[var(--text-muted)] lg:col-span-3">
                Aún no hay procesos asociados a los registros.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function CriticalKpiCard({ accent = 0, label, percent, rank, value }) {
  const accentClasses = [
    "from-emerald-50 via-white to-white ring-emerald-200/50",
    "from-cyan-50 via-white to-white ring-cyan-200/50",
    "from-amber-50 via-white to-white ring-amber-200/50",
  ];

  const accentClass = accentClasses[accent] || accentClasses[0];

  return (
    <article className={`relative overflow-hidden rounded-[24px] border bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] p-4 shadow-[0_10px_24px_rgba(15,23,42,0.05)] ring-1 ${accentClass}`}>
      <div className="flex items-start justify-between gap-3">
        <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-[var(--primary-dark)]">
          Top {rank}
        </span>
        <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">
          {formatNumber(percent || 0, 1)}%
        </span>
      </div>

      <div className="mt-5 flex min-h-[132px] flex-col items-center justify-center text-center">
        <p className="text-sm font-bold uppercase tracking-[0.16em] text-[var(--text-muted)]">
          {label}
        </p>
        <p className="mt-3 text-3xl font-black tracking-tight text-[var(--text-main)]">
          {value}
        </p>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-[var(--primary)]"
          style={{ width: `${Math.max(4, Math.min(100, percent || 0))}%` }}
        />
      </div>

      <p className="mt-3 text-center text-xs font-semibold text-[var(--text-muted)]">
        Impacto sobre la empresa: {formatNumber(percent || 0, 1)}%
      </p>
    </article>
  );
}

function MetricBar({ activeClassName, badge, detail, isActive, label, onClick, pct, value }) {
  const Component = onClick ? "button" : "div";

  return (
    <Component
      type={onClick ? "button" : undefined}
      onClick={onClick}
      aria-pressed={onClick ? Boolean(isActive) : undefined}
      className={`premium-card-interactive w-full rounded-2xl border p-4 text-left ${
        onClick ? "cursor-pointer" : ""
      } ${
        isActive
          ? activeClassName || "border-[var(--primary)]/45 bg-[var(--success-bg)] shadow-[0_14px_28px_rgba(14,124,102,0.14)] ring-1 ring-[var(--primary)]/15"
          : "border-[var(--border)] bg-[var(--bg-card)]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-[var(--text-main)]">{label}</p>
            {badge && (
              <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wide text-[var(--primary-dark)]">
                {badge}
              </span>
            )}
          </div>
          {detail && <p className="mt-1 text-xs text-[var(--text-muted)]">{detail}</p>}
        </div>
        <div className="text-right">
          <p className="font-bold text-[#075985]">{value}</p>
          <p className="text-xs text-[var(--text-muted)]">{formatNumber(pct || 0, 1)}%</p>
        </div>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full rounded-full ${
            isActive ? "bg-[var(--primary-dark)]" : "bg-[var(--primary)]"
          }`}
          style={{ width: `${Math.max(0, Math.min(100, pct || 0))}%` }}
        />
      </div>
    </Component>
  );
}
