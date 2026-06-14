import { useCallback, useEffect, useMemo, useState } from "react";

import RealtimeIotMonitoring from "@/features/dashboard/components/RealtimeIotMonitoring";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import {
  getConstructoraDashboard,
  getConstructoraEmisiones,
  getConstructoraEstado,
  getEmpresaRegistrosAmbientales,
} from "@/shared/services/api";
import { DEFAULT_PRESET_KEY, getActivePreset } from "@/presets/registry";
import { construccionDashboard } from "@/presets/construccion/dashboard";
import { aserraderoDashboard } from "@/presets/aserradero/dashboard";
import { transporteDashboard } from "@/presets/transporte/dashboard";
import { industrialDashboard } from "@/presets/industrial/dashboard";
import {
  getCriticalCategory,
  getCriticalModule,
  getRecordsWithoutFactor,
  groupByCategory,
  groupByMetadataModule,
  normalizeEmissionRows,
  sumEmissions,
} from "@/presets/shared/dashboardConfig";

import PresetCriticalDrivers from "./PresetCriticalDrivers";
import PresetExecutiveHeader from "./PresetExecutiveHeader";
import PresetKpiGrid from "./PresetKpiGrid";
import PresetOperationalSummary from "./PresetOperationalSummary";
import PresetRecommendationPanel from "./PresetRecommendationPanel";

const DASHBOARD_REFRESH_INTERVAL_MS = 10000;

const dashboardByPreset = {
  construccion: construccionDashboard,
  aserradero: aserraderoDashboard,
  transporte: transporteDashboard,
  industrial: industrialDashboard,
};

function DashboardPage({ onStatusChange }) {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const activePresetKey = activeConstructora?.preset || DEFAULT_PRESET_KEY;
  const activePreset = getActivePreset(activePresetKey);
  const dashboardConfig = dashboardByPreset[activePreset.key] || construccionDashboard;
  const [dashboardData, setDashboardData] = useState(null);
  const [emissionKpis, setEmissionKpis] = useState(null);
  const [ambientRecords, setAmbientRecords] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadDashboard = useCallback(async () => {
    if (!activeConstructoraId) {
      setDashboardData(null);
      setEmissionKpis(null);
      setAmbientRecords([]);
      onStatusChange?.(null);
      setLoading(false);
      return null;
    }

    setError("");
    setLoading(true);

    const [dashboardResult, estadoResult, emissionsResult, recordsResult] = await Promise.allSettled([
      getConstructoraDashboard(activeConstructoraId, { light: "1" }),
      getConstructoraEstado(activeConstructoraId),
      getConstructoraEmisiones(activeConstructoraId, { page: 1, page_size: 1 }),
      getEmpresaRegistrosAmbientales(activeConstructoraId),
    ]);

    if (dashboardResult.status === "fulfilled") {
      setDashboardData(dashboardResult.value);
    }

    if (estadoResult.status === "fulfilled") {
      onStatusChange?.(estadoResult.value);
    }

    if (emissionsResult.status === "fulfilled") {
      setEmissionKpis(emissionsResult.value?.kpis || null);
    } else {
      setEmissionKpis(null);
    }

    if (recordsResult.status === "fulfilled") {
      setAmbientRecords(normalizeEmissionRows(recordsResult.value));
    } else {
      setAmbientRecords([]);
    }

    if (dashboardResult.status === "rejected" && recordsResult.status === "rejected") {
      throw dashboardResult.reason || recordsResult.reason;
    }

    setLoading(false);
    return dashboardResult.status === "fulfilled" ? dashboardResult.value : null;
  }, [activeConstructoraId, onStatusChange]);

  useEffect(() => {
    let isCancelled = false;
    let timeoutId;

    const tick = async () => {
      if (document.visibilityState === "hidden") {
        timeoutId = window.setTimeout(tick, DASHBOARD_REFRESH_INTERVAL_MS);
        return;
      }

      try {
        await loadDashboard();
      } catch (requestError) {
        if (!isCancelled) {
          setError(requestError.response?.data?.error || "No se pudieron cargar los datos de la empresa activa.");
          setLoading(false);
        }
      } finally {
        if (!isCancelled) {
          timeoutId = window.setTimeout(tick, DASHBOARD_REFRESH_INTERVAL_MS);
        }
      }
    };

    tick();

    return () => {
      isCancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [loadDashboard]);

  const context = useMemo(() => {
    const dashboardRows = normalizeEmissionRows(dashboardData?.datos || []);
    const presetRows =
      activePreset.key === "construccion"
        ? dashboardRows
        : ambientRecords.filter((row) => row.metadata?.preset === activePreset.key);
    const rows = presetRows.length || activePreset.key !== "construccion" ? presetRows : dashboardRows;
    const totalEmissions =
      activePreset.key === "construccion"
        ? Number(dashboardData?.total_emisiones ?? sumEmissions(rows))
        : sumEmissions(rows);
    const categoryGroups = groupByCategory(rows);
    const moduleGroups = groupByMetadataModule(rows);

    return {
      activeConstructora,
      activePreset,
      ambientRecords,
      categoryGroups,
      criticalCategory: getCriticalCategory(rows),
      criticalModule: getCriticalModule(rows),
      dashboardData: dashboardData || {},
      emissionKpis,
      moduleGroups,
      recordsWithoutFactor: getRecordsWithoutFactor(rows),
      rows,
      totalEmissions,
    };
  }, [activeConstructora, activePreset, ambientRecords, dashboardData, emissionKpis]);

  const environmentalStatus = useMemo(() => getEnvironmentalStatus(context), [context]);
  const kpis = useMemo(() => dashboardConfig.kpis(context), [context, dashboardConfig]);
  const modules = useMemo(() => dashboardConfig.modules(context), [context, dashboardConfig]);
  const drivers = useMemo(() => dashboardConfig.criticalDrivers(context), [context, dashboardConfig]);
  const recommendation = useMemo(() => dashboardConfig.recommendationBuilder(context), [context, dashboardConfig]);

  if (loading && !dashboardData && !ambientRecords.length) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-main)] shadow-[var(--shadow-card)]">
        Cargando panel principal...
      </div>
    );
  }

  if (error && !context.rows.length) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-6 text-sm font-semibold text-rose-800">
        {error}
      </div>
    );
  }

  return (
    <div className="stagger-in mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <PresetExecutiveHeader
        activeConstructora={activeConstructora}
        dashboardConfig={dashboardConfig}
        environmentalStatus={environmentalStatus}
        onExport={() => window.print()}
        preset={activePreset}
      />

      <PresetKpiGrid kpis={kpis} />
      <PresetOperationalSummary modules={modules} preset={activePreset} />
      <PresetCriticalDrivers drivers={drivers} />
      <PresetRecommendationPanel recommendation={recommendation} />

      <RealtimeIotMonitoring activeConstructoraId={activeConstructoraId} />
    </div>
  );
}

function getEnvironmentalStatus(context) {
  if (!context.rows.length || !context.totalEmissions) {
    return {
      label: "Sin datos",
      detail: "Aun no hay registros suficientes.",
      className: "border-slate-300 bg-slate-100 text-slate-700",
    };
  }

  const maxShare =
    context.totalEmissions > 0
      ? Math.max(...context.categoryGroups.map((group) => ((group.emissions || 0) / context.totalEmissions) * 100), 0)
      : 0;
  const activeGroups = context.categoryGroups.filter((group) => group.emissions > 0).length;

  if (maxShare > 60) {
    return {
      label: "Critica",
      detail: "Una categoria o modulo concentra mas del 60% de la huella.",
      className: "border-rose-200 bg-rose-50 text-rose-700",
    };
  }

  if (context.recordsWithoutFactor.length > 0) {
    return {
      label: "Incompleta",
      detail: "Existen registros operativos sin factor de emision.",
      className: "border-amber-200 bg-amber-50 text-amber-700",
    };
  }

  if (activeGroups >= 3) {
    return {
      label: "En seguimiento",
      detail: "La huella esta distribuida en varias categorias operativas.",
      className: "border-sky-200 bg-sky-50 text-sky-700",
    };
  }

  return {
    label: "Inicial",
    detail: "Existen datos iniciales para comenzar gestion ambiental.",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  };
}

export default DashboardPage;
