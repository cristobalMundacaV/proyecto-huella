import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, Database, Factory } from "lucide-react";

import ExecutiveSummary from "@/features/dashboard/components/ExecutiveSummary";
import RealtimeIotMonitoring from "@/features/dashboard/components/RealtimeIotMonitoring";
import { calculateRiskProfile } from "@/features/dashboard/utils/risk";
import { optimizeScenario } from "@/features/dashboard/utils/optimizer";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import KpiCard from "@/shared/components/KpiCard";
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
      <div className="flex min-h-[60vh] items-center justify-center rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-main)] shadow-[var(--shadow-card)]">
        Cargando tablero de empresa...
      </div>
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
        <KpiCard icon={<Database />} title="Evidencia respaldada" value={data?.evidencia_respaldada || "Pendiente de vinculación"} />
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

function normalizeCopy(copy) {
  return {
    ...emptyOperationalCopy,
    ...(copy || {}),
    actions: Array.isArray(copy?.actions) ? copy.actions : [],
    evidence: Array.isArray(copy?.evidence) ? copy.evidence : [],
    metrics: Array.isArray(copy?.metrics) ? copy.metrics : [],
  };
}

function OperationalIntelligenceModule({ data, intelligence, items, total, environmentalStatus }) {
  const categoryOrder = intelligence.categoryOrder || [];
  const categoryIntelligence = intelligence.categoryIntelligence || {};
  const getCategoryLabel =
    intelligence.getOperationalCategoryLabel ||
    ((category) => intelligence.categoryDisplayNames?.[category] || category || "Sin categoria");
  const getCategoryAccentStyle = intelligence.getCategoryAccentStyle || (() => "");
  const orderedItems = useMemo(() => {
    const itemMap = new Map(items.map((item) => [item.category, item]));
    return categoryOrder.map((category) => itemMap.get(category) || { category, emissions: 0, pct: 0 });
  }, [categoryOrder, items]);

  const defaultCategory = useMemo(() => {
    const topItem = orderedItems.reduce((best, item) => {
      if (!best) return item;
      if ((item.pct || 0) > (best.pct || 0)) return item;
      if ((item.pct || 0) === (best.pct || 0) && (item.emissions || 0) > (best.emissions || 0)) return item;
      return best;
    }, null);
    return topItem?.category || categoryOrder[0] || "Otros";
  }, [categoryOrder, orderedItems]);

  const [selectedCategory, setSelectedCategory] = useState(defaultCategory);

  useEffect(() => {
    setSelectedCategory((currentCategory) =>
      orderedItems.some((item) => item.category === currentCategory) ? currentCategory : defaultCategory
    );
  }, [defaultCategory, orderedItems]);

  const selectedItem = orderedItems.find((item) => item.category === selectedCategory) || orderedItems[0] || { category: "Otros", emissions: 0, pct: 0 };
  const selectedCopy = normalizeCopy(categoryIntelligence[selectedItem.category] || categoryIntelligence.Otros);
  const documentationNote = buildDocumentationNote(selectedCopy.evidence, data?.evidencia_respaldada || 0, selectedCopy.metrics);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl space-y-2">
          <p className="text-xs font-black uppercase tracking-[0.28em] text-[var(--text-muted)]">Inteligencia operativa</p>
          <h2 className="text-2xl font-black tracking-tight text-[var(--text-main)] sm:text-3xl">Módulo integrado de decisión ambiental</h2>
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
        <OperationalDetailCard
          title={getCategoryLabel(selectedItem.category)}
          subtitle={selectedCopy.relevanceLabel}
          amountLabel="Emisiones de la categoría"
          amount={`${formatNumber(selectedItem.emissions, 1)} kg CO2e`}
          percent={`${formatNumber(selectedItem.pct || 0, 1)}% del total`}
          diagnosisLabel="Diagnóstico operativo"
          copy={selectedCopy}
          documentationNote={documentationNote}
        />
        <InteractiveBars
          emptyMessage="No hay registros de emision suficientes."
          items={orderedItems}
          onSelect={(item) => setSelectedCategory(item.category)}
          renderDetail={(item) =>
            item.category === selectedItem.category
              ? "Foco actual"
              : item.pct > 0
                ? "Disponible para intervención"
                : "Monitoreo sin emisiones"
          }
          renderKey={(item) => item.category}
          renderLabel={(item) => getCategoryLabel(item.category)}
          renderValue={(item) => `${formatNumber(item.emissions, 1)} kg CO2e`}
          selectedKey={selectedItem.category}
          total={total}
          title="Fuente de datos interactiva"
          eyebrow="Emisiones por categoría"
          description="Selecciona una categoría para actualizar la inteligencia."
          activeClassName={getCategoryAccentStyle(selectedItem.category)}
        />
      </div>
    </section>
  );
}

function StageOperationalModule({ data, intelligence, items, total, environmentalStatus, riskProfile, processLabel }) {
  const stageOrder = intelligence.stageOrder || [];
  const stageIntelligence = intelligence.stageIntelligence || {};
  const getStageKey = intelligence.getOperationalStageKey || ((stage) => normalizeInsightText(stage).replace(/\s+/g, " "));
  const getStageLabel =
    intelligence.getOperationalStageLabel ||
    ((stage) => intelligence.stageDisplayNames?.[getStageKey(stage)] || stage || "Sin etapa");
  const getStageRelevance =
    intelligence.getStageOperationalRelevance ||
    (() => ({ label: "Monitoreo operativo", score: 0, summary: "Mantener monitoreo y depuracion de datos." }));
  const orderedItems = useMemo(() => {
    const itemMap = new Map(items.map((item) => [getStageKey(item.stage), item]));
    const orderedStages = stageOrder.map((stage) => itemMap.get(getStageKey(stage)) || { stage, emissions: 0, records: 0 });
    const knownStageKeys = new Set(orderedStages.map((item) => getStageKey(item.stage)));
    const extraStages = items.filter((item) => !knownStageKeys.has(getStageKey(item.stage)));
    return [...orderedStages, ...extraStages];
  }, [getStageKey, items, stageOrder]);

  const defaultStage = useMemo(() => {
    const topItem = orderedItems.reduce((best, item) => (!best || (item.emissions || 0) > (best.emissions || 0) ? item : best), null);
    return getStageKey(topItem?.stage || stageOrder[0] || "Sin etapa");
  }, [getStageKey, orderedItems, stageOrder]);

  const [selectedStage, setSelectedStage] = useState(defaultStage);

  useEffect(() => {
    setSelectedStage((currentStage) =>
      orderedItems.some((item) => getStageKey(item.stage) === currentStage) ? currentStage : defaultStage
    );
  }, [defaultStage, getStageKey, orderedItems]);

  const selectedItem = orderedItems.find((item) => getStageKey(item.stage) === selectedStage) || orderedItems[0] || { stage: "Sin etapa", emissions: 0, records: 0 };
  const selectedKey = getStageKey(selectedItem.stage);
  const selectedCopy = normalizeCopy(stageIntelligence[selectedKey] || stageIntelligence[Object.keys(stageIntelligence)[0]]);
  const documentationNote = buildDocumentationNote(selectedCopy.evidence, data?.evidencia_respaldada || 0, selectedCopy.metrics);
  const stageRank = Math.max(0, stageOrder.findIndex((stage) => getStageKey(stage) === selectedKey));
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
          <p className="text-xs font-black uppercase tracking-[0.28em] text-[var(--text-muted)]">Inteligencia por {processLabel.toLowerCase()}</p>
          <h2 className="text-2xl font-black tracking-tight text-[var(--text-main)] sm:text-3xl">Módulo operativo por proceso</h2>
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
        <OperationalDetailCard
          title={getStageLabel(selectedItem.stage)}
          subtitle={selectedCopy.relevanceLabel || relevance.label}
          amountLabel="Emisiones del proceso"
          amount={`${formatNumber(selectedItem.emissions, 1)} kg CO2e`}
          percent={`${formatNumber(total > 0 ? (selectedItem.emissions / total) * 100 : 0, 1)}% del total`}
          diagnosisLabel="Diagnóstico de la fase"
          copy={selectedCopy}
          documentationNote={documentationNote}
        />
        <InteractiveBars
          emptyMessage="Aún no hay procesos asociados a los registros."
          items={orderedItems}
          onSelect={(item) => setSelectedStage(getStageKey(item.stage))}
          renderDetail={(item, index) =>
            getStageKey(item.stage) === selectedStage
              ? "Proceso seleccionado"
              : item.emissions > 0
                ? stageIntelligence[getStageKey(item.stage)]?.relevanceLabel || `Proceso ${index + 1} de intervencion`
                : "Monitoreo sin emisiones"
          }
          renderKey={(item) => getStageKey(item.stage)}
          renderLabel={(item) => getStageLabel(item.stage)}
          renderValue={(item) => `${formatNumber(item.emissions, 1)} kg CO2e`}
          selectedKey={selectedStage}
          total={total}
          title="Análisis interactivo por proceso"
          eyebrow="Impacto de emisiones por proceso"
          description="Selecciona un proceso para visualizar su diagnóstico operativo, nivel de impacto y recomendaciones específicas."
        />
      </div>
    </section>
  );
}

function OperationalDetailCard({ amount, amountLabel, copy, diagnosisLabel, documentationNote, percent, subtitle, title }) {
  return (
    <div className="rounded-[28px] border border-[color-mix(in_srgb,var(--primary)_16%,white)] bg-[linear-gradient(180deg,rgba(248,250,252,0.98),rgba(255,255,255,0.99))] p-5 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-6">
      <div className="flex flex-col gap-3 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex-1 space-y-2 text-center sm:pr-6 sm:text-left">
          <h3 className="text-2xl font-black tracking-tight text-[var(--text-main)]">{title}</h3>
          <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">{subtitle}</p>
        </div>
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 shadow-[0_8px_18px_rgba(15,23,42,0.04)]">
          <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{amountLabel}</p>
          <p className="mt-1 text-3xl font-black text-[var(--text-main)]">{amount}</p>
          <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">{percent}</p>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
        <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">{diagnosisLabel}</p>
        <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">{copy.diagnosis}</p>
      </div>

      <div className="mt-5 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
        <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">Acciones recomendadas</p>
        <ul className="mt-3 space-y-2 text-sm leading-6 text-[var(--text-main)]">
          {copy.actions.map((action) => (
            <li key={action} className="flex gap-2">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--primary)]" />
              <span>{action}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-100/80 p-4 shadow-[0_8px_18px_rgba(15,23,42,0.03)]">
        <p className="text-xs font-black uppercase tracking-wide text-[var(--text-muted)]">Documentación requerida</p>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {documentationNote.label}: {documentationNote.text}
        </p>
      </div>

      <div className="mt-5 rounded-2xl border border-[color-mix(in_srgb,var(--primary)_18%,white)] bg-[linear-gradient(180deg,rgba(236,253,245,0.9),rgba(255,255,255,0.98))] p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
        <p className="text-xs font-black uppercase tracking-wide text-[var(--primary-dark)]">Siguiente paso recomendado</p>
        <p className="mt-2 text-sm leading-6 text-[var(--text-main)]">{copy.nextStep}</p>
      </div>
    </div>
  );
}

function InteractiveBars({ activeClassName, description, emptyMessage, eyebrow, items, onSelect, renderDetail, renderKey, renderLabel, renderValue, selectedKey, title, total }) {
  return (
    <div className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-card)] p-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-5">
      <div className="border-b border-[var(--border)] pb-4">
        <p className="whitespace-nowrap text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)] sm:text-[11px]">{eyebrow}</p>
        <h3 className="mt-2 text-xl font-black text-[var(--text-main)]">{title}</h3>
        <p className="mt-2 max-w-2xl text-sm font-semibold leading-6 text-[var(--text-muted)]">{description}</p>
      </div>
      <div className="mt-4 space-y-3">
        {items.map((item, index) => {
          const key = renderKey(item);
          const pct = total > 0 ? ((item.emissions || 0) / total) * 100 : item.pct || 0;
          return (
            <MetricBar
              key={key}
              label={renderLabel(item)}
              pct={pct}
              value={renderValue(item)}
              detail={renderDetail(item, index)}
              badge={key === selectedKey ? "SELECCIONADA" : null}
              activeClassName={activeClassName}
              isActive={key === selectedKey}
              onClick={() => onSelect(item)}
            />
          );
        })}
        {!total && <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-main)] p-4 text-sm text-[var(--text-muted)]">{emptyMessage}</p>}
      </div>
    </div>
  );
}

function CriticalDriversPanel({ categoryItems, intelligence, processPluralLabel, stageItems, total }) {
  const getCategoryLabel =
    intelligence.getOperationalCategoryLabel ||
    ((category) => intelligence.categoryDisplayNames?.[category] || category || "Sin categoria");
  const getStageKey = intelligence.getOperationalStageKey || ((stage) => normalizeInsightText(stage).replace(/\s+/g, " "));
  const getStageLabel =
    intelligence.getOperationalStageLabel ||
    ((stage) => intelligence.stageDisplayNames?.[getStageKey(stage)] || stage || "Sin etapa");
  const topCategories = categoryItems.filter((item) => item.emissions > 0).slice(0, 3);
  const topStages = stageItems.filter((item) => item.emissions > 0).slice(0, 3);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-premium)] sm:p-6">
      <div className="flex flex-col gap-3 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.24em] text-[var(--text-muted)]">Fuentes críticas</p>
          <h2 className="mt-1 text-2xl font-black tracking-tight text-[var(--text-main)]">Top 3 de mayor impacto</h2>
        </div>
        <p className="max-w-2xl text-sm leading-6 text-[var(--text-muted)]">
          El sistema prioriza las tres categorías y los tres {processPluralLabel.toLowerCase()} con mayor impacto para orientar la lectura ejecutiva.
        </p>
      </div>

      <div className="mt-5 space-y-5">
        <CriticalGroup title="Categorías con mayor huella" eyebrow="Top 3 por categorías" items={topCategories} total={total} getLabel={(item) => getCategoryLabel(item.category)} getValue={(item) => item.emissions} />
        <CriticalGroup title={`${processPluralLabel} con mayor impacto`} eyebrow={`Top 3 por ${processPluralLabel.toLowerCase()}`} items={topStages} total={total} getLabel={(item) => getStageLabel(item.stage)} getValue={(item) => item.emissions} />
      </div>
    </section>
  );
}

function CriticalGroup({ eyebrow, getLabel, getValue, items, title, total }) {
  return (
    <div className="rounded-[28px] border border-[var(--border)] bg-[linear-gradient(180deg,rgba(248,250,252,0.98),rgba(255,255,255,0.99))] p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.22em] text-[var(--text-muted)]">{eyebrow}</p>
          <h3 className="mt-1 text-lg font-black text-[var(--text-main)]">{title}</h3>
        </div>
        <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-3 py-1 text-[11px] font-black uppercase tracking-wide text-[var(--primary-dark)]">
          {items.length} KPI
        </span>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
        {items.length ? (
          items.map((item, index) => (
            <CriticalKpiCard
              key={`${getLabel(item)}-${index}`}
              accent={index}
              label={getLabel(item)}
              value={`${formatNumber(getValue(item), 1)} kg CO2e`}
              percent={total > 0 ? (getValue(item) / total) * 100 : 0}
              rank={index + 1}
            />
          ))
        ) : (
          <p className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-4 text-sm text-[var(--text-muted)] lg:col-span-3">No hay registros de emision suficientes.</p>
        )}
      </div>
    </div>
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
        <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-[var(--primary-dark)]">Top {rank}</span>
        <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">{formatNumber(percent || 0, 1)}%</span>
      </div>
      <div className="mt-5 flex min-h-[132px] flex-col items-center justify-center text-center">
        <p className="text-sm font-bold uppercase tracking-[0.16em] text-[var(--text-muted)]">{label}</p>
        <p className="mt-3 text-3xl font-black tracking-tight text-[var(--text-main)]">{value}</p>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${Math.max(4, Math.min(100, percent || 0))}%` }} />
      </div>
      <p className="mt-3 text-center text-xs font-semibold text-[var(--text-muted)]">Impacto sobre la empresa: {formatNumber(percent || 0, 1)}%</p>
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
      className={`premium-card-interactive w-full rounded-2xl border p-4 text-left ${onClick ? "cursor-pointer" : ""} ${
        isActive
          ? activeClassName || "border-[var(--primary)]/45 bg-[var(--success-bg)] shadow-[0_14px_28px_rgba(14,124,102,0.14)] ring-1 ring-[var(--primary)]/15"
          : "border-[var(--border)] bg-[var(--bg-card)]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-[var(--text-main)]">{label}</p>
            {badge && <span className="rounded-full border border-[var(--primary)]/15 bg-[var(--success-bg)] px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wide text-[var(--primary-dark)]">{badge}</span>}
          </div>
          {detail && <p className="mt-1 text-xs text-[var(--text-muted)]">{detail}</p>}
        </div>
        <div className="text-right">
          <p className="font-bold text-[#075985]">{value}</p>
          <p className="text-xs text-[var(--text-muted)]">{formatNumber(pct || 0, 1)}%</p>
        </div>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${isActive ? "bg-[var(--primary-dark)]" : "bg-[var(--primary)]"}`} style={{ width: `${Math.max(0, Math.min(100, pct || 0))}%` }} />
      </div>
    </Component>
  );
}

export default DashboardPage;
