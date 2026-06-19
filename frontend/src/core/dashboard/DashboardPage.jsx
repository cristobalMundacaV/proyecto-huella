import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, Database, Factory } from "lucide-react";

import ExecutiveSummary from "@/features/dashboard/components/ExecutiveSummary";
import RealtimeIotMonitoring from "@/features/dashboard/components/RealtimeIotMonitoring";
import { calculateRiskProfile } from "@/features/dashboard/utils/risk";
import { optimizeScenario } from "@/features/dashboard/utils/optimizer";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import KpiCard from "@/shared/components/KpiCard";
import PlatformLoader from "@/shared/components/PlatformLoader";
import {
  getConstructoraDashboard,
  getConstructoraEmisiones,
  getConstructoraEstado,
  getEmpresaRegistrosAmbientales,
} from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";
import { DEFAULT_PRESET_KEY, getActivePreset, getPreset } from "@/presets/registry";

const DASHBOARD_REFRESH_INTERVAL_MS = 10000;

const normalizeRows = (input) => {
  const list = Array.isArray(input)
    ? input
    : input?.results || input?.data || input?.datos || input?.registros || input?.registros_emision || [];

  return list.map((row) => ({
    ...row,
    emisiones: Number(row?.emisiones ?? row?.emisiones_kg_co2e ?? row?.total_emisiones ?? row?.co2e ?? 0) || 0,
    metadata: row?.metadata && typeof row.metadata === "object" ? row.metadata : {},
  }));
};

function DashboardPage({ onStatusChange }) {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const activePreset = getActivePreset(activeConstructora?.preset || DEFAULT_PRESET_KEY);
  const dashboardIntelligence = activePreset.intelligence || getPreset(DEFAULT_PRESET_KEY).intelligence;
  const [data, setData] = useState(null);
  const [ambientRecords, setAmbientRecords] = useState([]);
  const [dashboardError, setDashboardError] = useState("");
  const [dashboardEmissionKpis, setDashboardEmissionKpis] = useState(null);
  const [loading, setLoading] = useState(true);

  const applyDashboardData = useCallback((dashboardData) => {
    setData(dashboardData);
    setDashboardError("");
  }, []);

  const refreshDashboard = useCallback(async () => {
    if (!activeConstructoraId) {
      setData(null);
      setAmbientRecords([]);
      setDashboardEmissionKpis(null);
      onStatusChange?.(null);
      setLoading(false);
      return null;
    }

    setLoading(true);

    const [dashboardResult, estadoResult, emissionsResult, recordsResult] = await Promise.allSettled([
      getConstructoraDashboard(activeConstructoraId, { light: "1" }),
      getConstructoraEstado(activeConstructoraId),
      getConstructoraEmisiones(activeConstructoraId, { page: 1, page_size: 1 }),
      getEmpresaRegistrosAmbientales(activeConstructoraId),
    ]);

    if (dashboardResult.status === "fulfilled") {
      applyDashboardData(dashboardResult.value);
    }

    if (estadoResult.status === "fulfilled") {
      onStatusChange?.(estadoResult.value);
    }

    if (emissionsResult.status === "fulfilled") {
      setDashboardEmissionKpis(emissionsResult.value?.kpis || null);
    } else {
      setDashboardEmissionKpis(null);
    }

    if (recordsResult.status === "fulfilled") {
      setAmbientRecords(normalizeRows(recordsResult.value));
    } else {
      setAmbientRecords([]);
    }

    if (dashboardResult.status === "rejected" && recordsResult.status === "rejected") {
      throw dashboardResult.reason || recordsResult.reason;
    }

    setLoading(false);
    return dashboardResult.status === "fulfilled" ? dashboardResult.value : null;
  }, [activeConstructoraId, applyDashboardData, onStatusChange]);

  useEffect(() => {
    let isCancelled = false;
    let timeoutId;

    const loadDashboard = async () => {
      if (document.visibilityState === "hidden") {
        timeoutId = window.setTimeout(loadDashboard, DASHBOARD_REFRESH_INTERVAL_MS);
        return;
      }

      try {
        await refreshDashboard();
      } catch (error) {
        if (!isCancelled) {
          setDashboardError(error.response?.data?.error || "No se pudieron cargar los datos de la empresa activa.");
          setLoading(false);
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
  }, [refreshDashboard]);

  const dashboardModel = useMemo(() => {
    const dashboardRows = normalizeRows(data?.datos || []);
    const scopedPresetRows =
      activePreset.key === DEFAULT_PRESET_KEY
        ? dashboardRows
        : ambientRecords.filter((row) => row.metadata?.preset === activePreset.key);
    const rows = scopedPresetRows.length ? scopedPresetRows : dashboardRows;
    const totalEmissions =
      activePreset.key === DEFAULT_PRESET_KEY
        ? Number(data?.total_emisiones ?? rows.reduce((sum, row) => sum + row.emisiones, 0))
        : rows.reduce((sum, row) => sum + row.emisiones, 0);

    const safeDashboardData = {
      ...(data || {}),
      datos: rows,
      emisiones_por_Constructora: data?.emisiones_por_Constructora ?? {},
      emisiones_por_fuente_emision: data?.emisiones_por_fuente_emision ?? {},
      total_emisiones: totalEmissions,
    };

    const rowsWithCategories = rows.map((row) => ({
      ...row,
      categoria_visible:
        dashboardIntelligence.resolveCategoryLabel?.(row.categoria, row.fuente_emision, row.metadata) ||
        dashboardIntelligence.getOperationalCategoryLabel?.(row.metadata?.aserradero_category || row.categoria) ||
        row.metadata?.aserradero_category ||
        row.categoria ||
        "Otros",
    }));

    const dashboardCategories =
      dashboardIntelligence.categoryOrder?.length ? dashboardIntelligence.categoryOrder : activePreset.categories || [];

    const categoryDistribution = dashboardCategories
      .map((category) => {
        const emissions = rowsWithCategories.reduce(
          (total, row) => (row.categoria_visible === category ? total + row.emisiones : total),
          0
        );
        return {
          category,
          emissions,
          pct: totalEmissions > 0 ? (emissions / totalEmissions) * 100 : 0,
        };
      })
      .sort((left, right) => right.emissions - left.emissions);

    const emissionsByStage = Object.values(
      rowsWithCategories.reduce((accumulator, row) => {
        const stage = row.etapa_nombre || row.metadata?.module || row.etapa || "Sin etapa";
        const current = accumulator[stage] || { stage, emissions: 0, records: 0 };
        current.emissions += row.emisiones;
        current.records += 1;
        accumulator[stage] = current;
        return accumulator;
      }, {})
    ).sort((left, right) => right.emissions - left.emissions);

    const emissionsByWork = Object.values(
      rowsWithCategories.reduce((accumulator, row) => {
        const workCode = row.obra_nombre || row.codigo_obra || row.metadata?.lote || row.obra || "Sin unidad";
        const current = accumulator[workCode] || {
          name: workCode,
          emissions: 0,
          surface: Number(row.superficie_m2 || row.superficie || 0),
          records: 0,
        };
        current.emissions += row.emisiones;
        current.records += 1;
        if (!current.surface) current.surface = Number(row.superficie_m2 || row.superficie || 0);
        accumulator[workCode] = current;
        return accumulator;
      }, {})
    ).sort((left, right) => right.emissions - left.emissions);

    const registrosEmision = rowsWithCategories.map((row) => ({
      fuente_emision: row.fuente_emision,
      emisiones: row.emisiones,
    }));
    const fuenteCritica = data?.fuente_critica || rowsWithCategories.sort((a, b) => b.emisiones - a.emisiones)[0]?.fuente_emision || "Sin datos";
    const unidadCritica = data?.etapa_critica || emissionsByStage[0]?.stage || "Sin datos";
    const criticalWork = activePreset.key === DEFAULT_PRESET_KEY ? data?.obra_critica || emissionsByWork[0]?.name : emissionsByWork[0]?.name;
    const criticalCategory = categoryDistribution.find((item) => item.emissions > 0)?.category || "Sin datos";
    const totalDeclaredSurface = emissionsByWork.reduce((total, work) => total + Number(work.surface || 0), 0);
    const carbonIntensity = totalDeclaredSurface > 0 ? totalEmissions / totalDeclaredSurface : null;

    return {
      carbonIntensity,
      categoryDistribution,
      criticalCategory,
      criticalWork: criticalWork || "Sin datos",
      emissionsByStage,
      fuenteCritica,
      registrosEmision,
      rows: rowsWithCategories,
      safeDashboardData,
      totalEmissions,
      unidadCritica,
      validationSummary: {
        records: rowsWithCategories.length,
        errors: 0,
        registros: new Set(rowsWithCategories.map((row) => row.fuente_emision)).size,
      },
    };
  }, [activePreset, ambientRecords, dashboardIntelligence, data]);

  const recommendedScenario = useMemo(() => {
    if (dashboardModel.rows.length) {
      const optimized = optimizeScenario(dashboardModel.rows || []);
      return {
        ...optimized,
        currentTotal: dashboardModel.totalEmissions,
        simulatedTotal: dashboardModel.totalEmissions * (1 - Number(optimized.reductionPct || 0) / 100),
      };
    }

    if (!dashboardModel.totalEmissions) return null;

    const estimatedReductionPct = 25;
    return {
      currentTotal: dashboardModel.totalEmissions,
      simulatedTotal: dashboardModel.totalEmissions * (1 - estimatedReductionPct / 100),
      reductionPct: estimatedReductionPct,
      dieselReduction: 0,
      electricityIncrease: 0,
      rows: [],
    };
  }, [dashboardModel.rows, dashboardModel.totalEmissions]);

  const riskProfile = useMemo(
    () => calculateRiskProfile(dashboardModel.safeDashboardData, recommendedScenario),
    [dashboardModel.safeDashboardData, recommendedScenario]
  );

  const dieselReductionImpactKg = dashboardEmissionKpis
    ? Number(dashboardEmissionKpis.emisiones_totales || 0) *
    (Number(dashboardEmissionKpis.porcentaje_diesel || 0) / 100) *
    0.25
    : null;
  const dieselReductionEquivalentKm = dieselReductionImpactKg != null ? dieselReductionImpactKg * 4 : null;
  const environmentalStatus = getEnvironmentalStatus({
    categoryDistribution: dashboardModel.categoryDistribution,
    evidenceBacked: null,
    rows: dashboardModel.rows,
    totalEmissions: dashboardModel.totalEmissions,
  });
  const isDieselCriticalSource = String(dashboardModel.fuenteCritica || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .includes("diesel");

  if (loading && !data && !ambientRecords.length) {
    return (
      <PlatformLoader
        title="Cargando tablero de empresa"
        description="Estamos preparando indicadores, focos críticos y recomendaciones ambientales."
      />
    );
  }

  if (dashboardError && !dashboardModel.rows.length) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-6 text-sm font-semibold text-rose-800">
        {dashboardError}
      </div>
    );
  }

  return (
    <div className="stagger-in mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-emerald-200/80 bg-[linear-gradient(180deg,rgba(236,253,243,1),rgba(209,250,229,0.9))] p-3 shadow-[0_14px_30px_rgba(14,124,102,0.14)] ring-1 ring-white/70">
            <Database className="text-[var(--primary-dark)]" />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight sm:text-4xl">Carbono Zero</h1>
            <p className="text-[var(--text-muted)]">
              Convierte datos reales de {activePreset.unitPluralLabel.toLowerCase()} en medición, trazabilidad y decisiones para reducir emisiones durante la operación.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => window.print()}
          className="premium-button-primary inline-flex w-full items-center justify-center rounded-2xl px-5 py-3 text-sm font-bold shadow-[0_16px_32px_rgba(14,124,102,0.22)] sm:w-fit"
        >
          Exportar reporte
        </button>
      </header>

      <ExecutiveSummary
        fuenteCritica={dashboardModel.fuenteCritica}
        unidadCritica={dashboardModel.unidadCritica}
        optimizedScenario={recommendedScenario}
        reductionEquivalentKm={dieselReductionEquivalentKm}
        riskProfile={riskProfile}
        validationSummary={dashboardModel.validationSummary}
      />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-3">
        <KpiCard icon={<Activity />} title="Emisiones totales" value={`${formatNumber(dashboardModel.totalEmissions)} kg CO2e`} />
        <KpiCard icon={<Factory />} title={`${activePreset.unitLabel} critica`} value={dashboardModel.criticalWork} />
        <KpiCard icon={<AlertTriangle />} title="Categoría critica" value={dashboardModel.criticalCategory} />
        <KpiCard icon={<AlertTriangle />} title="Fuente critica" value={dashboardModel.fuenteCritica} />
        <KpiCard
          icon={<Database />}
          title="Evidencia respaldada"
          value={
            data?.evidencia_respaldada !== undefined && data?.evidencia_respaldada !== null
              ? Number(data.evidencia_respaldada)
              : 0
          }
        />
        <KpiCard
          icon={<Factory />}
          title="Intensidad de carbono"
          value={
            dashboardModel.carbonIntensity != null
              ? `${formatNumber(dashboardModel.carbonIntensity, 2)} kg CO2e/m²`
              : "Pendiente de superficie"
          }
        />
      </section>

      <OperationalIntelligenceModule
        data={dashboardModel.safeDashboardData}
        intelligence={dashboardIntelligence}
        items={dashboardModel.categoryDistribution}
        total={dashboardModel.totalEmissions}
        environmentalStatus={environmentalStatus}
        riskProfile={riskProfile}
      />

      <StageOperationalModule
        data={dashboardModel.safeDashboardData}
        intelligence={dashboardIntelligence}
        items={dashboardModel.emissionsByStage}
        total={dashboardModel.totalEmissions}
        environmentalStatus={environmentalStatus}
        riskProfile={riskProfile}
        processLabel={activePreset.processLabel}
      />

      <CriticalDriversPanel
        categoryItems={dashboardModel.categoryDistribution}
        intelligence={dashboardIntelligence}
        stageItems={dashboardModel.emissionsByStage}
        total={dashboardModel.totalEmissions}
        processPluralLabel={activePreset.processPluralLabel}
      />

      <RealtimeIotMonitoring activeConstructoraId={activeConstructoraId} />

      {isDieselCriticalSource && Boolean(dashboardIntelligence.reductionSteps?.length) && (
        <section className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 shadow-[var(--shadow-card)] ring-1 ring-white/40 sm:p-6">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Pasos a seguir</p>
            <h2 className="mt-1 text-xl font-bold text-[var(--text-main)]">Como reducir emisiones dentro de la operación.</h2>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {(dashboardIntelligence.reductionSteps || []).map((step, index) => {
              const stepTitle = typeof step === "string" ? `Paso recomendado ${index + 1}` : step.title;
              const stepDetail = typeof step === "string" ? step : step.detail;
              return (
                <div key={`${stepTitle}-${index}`} className="rounded-2xl border border-[var(--border)] bg-[var(--success-bg)] p-4">
                  <p className="text-xs font-bold text-[var(--primary-dark)]">Paso {index + 1}</p>
                  <h3 className="mt-2 text-sm font-bold text-[var(--text-main)]">{stepTitle}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{stepDetail}</p>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
