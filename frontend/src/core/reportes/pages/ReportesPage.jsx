import { useEffect, useMemo, useState } from "react";
import { BarChart3, Database, RefreshCcw } from "lucide-react";

import Toast from "@/shared/components/Toast";
import { getConstructoraDashboard, getEmpresaRegistrosAmbientales } from "@/shared/services/api";
import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { DEFAULT_PRESET_KEY, getActivePreset } from "@/presets/registry";
import { construccionReport } from "@/presets/construccion/report";
import { aserraderoReport } from "@/presets/aserradero/report";
import { transporteReport } from "@/presets/transporte/report";
import { industrialReport } from "@/presets/industrial/report";
import { normalizeReportRows } from "@/presets/shared/reportConfig";

import ReportCharts from "../components/ReportCharts";
import ReportExportActions from "../components/ReportExportActions";
import ReportFiltersModal from "../components/ReportFiltersModal";
import ReportHero from "../components/ReportHero";
import ReportKpiGrid from "../components/ReportKpiGrid";
import ReportTable from "../components/ReportTable";

const reportByPreset = {
  construccion: construccionReport,
  aserradero: aserraderoReport,
  transporte: transporteReport,
  industrial: industrialReport,
};

const defaultFilters = {
  fecha_inicio: "",
  fecha_fin: "",
  agrupacion: "mes",
};

function ReportesPage({ activeConstructora: propActiveConstructora, activeConstructoraId: propActiveConstructoraId, onSetActiveView }) {
  const context = useConstructoraActiva();
  const activeConstructora = propActiveConstructora || context.activeConstructora;
  const activeConstructoraId = propActiveConstructoraId || context.activeConstructoraId;
  const activePreset = getActivePreset(activeConstructora?.preset || DEFAULT_PRESET_KEY);
  const reportConfig = reportByPreset[activePreset.key] || construccionReport;
  const [allRows, setAllRows] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const [filters, setFilters] = useState(defaultFilters);
  const [draftFilters, setDraftFilters] = useState(defaultFilters);
  const [isFiltersModalOpen, setIsFiltersModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadReport = async (showLoading = true) => {
    if (!activeConstructoraId) return;
    try {
      if (showLoading) setLoading(true);
      setError("");
      const [recordsResult, dashboardResult] = await Promise.allSettled([
        getEmpresaRegistrosAmbientales(activeConstructoraId),
        getConstructoraDashboard(activeConstructoraId, { light: "1" }),
      ]);

      if (recordsResult.status === "fulfilled") {
        setAllRows(normalizeReportRows(recordsResult.value));
      } else {
        setAllRows([]);
      }

      if (dashboardResult.status === "fulfilled") {
        setDashboardData(dashboardResult.value);
      } else {
        setDashboardData(null);
      }

      if (recordsResult.status === "rejected" && dashboardResult.status === "rejected") {
        throw recordsResult.reason || dashboardResult.reason;
      }
    } catch (requestError) {
      setError(requestError.response?.data?.error || "No se pudieron cargar los registros para construir el reporte.");
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    setAllRows([]);
    setDashboardData(null);
    setFilters(defaultFilters);
    setDraftFilters(defaultFilters);
    if (!activeConstructoraId) return undefined;
    loadReport(true);
    const intervalId = window.setInterval(() => loadReport(false), 10000);
    return () => window.clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConstructoraId, activePreset.key]);

  const report = useMemo(
    () =>
      reportConfig.buildReport(allRows, filters, {
        activeConstructora,
        activePreset,
        dashboardData,
        filters,
      }),
    [activeConstructora, activePreset, allRows, dashboardData, filters, reportConfig]
  );

  const exportPayload = useMemo(
    () =>
      reportConfig.buildExportPayload(report, {
        activeConstructora,
        activePreset,
        filters,
      }),
    [activeConstructora, activePreset, filters, report, reportConfig]
  );

  function openFiltersModal() {
    setDraftFilters(filters);
    setIsFiltersModalOpen(true);
  }

  function applyFilters() {
    setFilters({
      fecha_inicio: draftFilters.fecha_inicio || "",
      fecha_fin: draftFilters.fecha_fin || "",
      agrupacion: draftFilters.agrupacion || "mes",
    });
    setIsFiltersModalOpen(false);
  }

  function clearFilters() {
    setDraftFilters(defaultFilters);
    setFilters(defaultFilters);
    setIsFiltersModalOpen(false);
  }

  if (!activeConstructoraId) {
    return (
      <main className="mx-auto max-w-7xl text-[var(--text-main)]">
        <h1 className="text-4xl font-black">Reportes</h1>
        <div className="mt-8 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-8 text-center text-[var(--text-muted)]">
          Selecciona o crea una empresa para revisar reportes temporales.
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-8 text-[var(--text-main)]">
      <Toast
        message={loading ? "Cargando reportes..." : ""}
        loading={loading}
        onClose={() => undefined}
        toastKey={loading ? "report-loading" : "report-idle"}
      />

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-[var(--secondary)]">Reporte adaptativo</p>
          <h1 className="mt-2 text-3xl font-black sm:text-4xl">Reportes</h1>
          <p className="mt-2 text-[var(--text-muted)]">
            Analiza tendencias, fuentes criticas y registros con lenguaje del preset activo.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <ReportExportActions exportPayload={exportPayload} report={report} reportConfig={reportConfig} />
          <button
            onClick={() => loadReport(true)}
            className="inline-flex items-center gap-2 rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-4 py-3 text-sm font-bold text-[#075985] shadow-[0_12px_24px_rgba(15,23,42,0.05)]"
          >
            <RefreshCcw size={18} />
            Actualizar
          </button>
        </div>
      </div>

      {isFiltersModalOpen && (
        <ReportFiltersModal
          draftFilters={draftFilters}
          groupingOptions={reportConfig.groupingOptions}
          onApply={applyFilters}
          onChange={setDraftFilters}
          onClear={clearFilters}
          onClose={() => setIsFiltersModalOpen(false)}
        />
      )}

      {error && (
        <div className="rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-6 text-[#B42318]">
          {error}
        </div>
      )}

      <ReportHero
        activeConstructora={activeConstructora}
        filters={filters}
        onOpenFilters={openFiltersModal}
        preset={activePreset}
        report={report}
        reportConfig={reportConfig}
      />

      {!loading && !report.rows.length ? (
        <EmptyReportState
          message={report.emptyMessage}
          onImport={() => onSetActiveView?.("importaciones")}
          onPrimary={() => onSetActiveView?.(report.primaryModuleView || "emisiones")}
          preset={activePreset}
        />
      ) : (
        <>
          <ReportKpiGrid kpis={report.kpis} />
          <ReportCharts report={report} reportConfig={reportConfig} />
          <ReportTable report={report} reportConfig={reportConfig} />
        </>
      )}
    </main>
  );
}

function EmptyReportState({ message, onImport, onPrimary, preset }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[linear-gradient(135deg,#FFFFFF_0%,#F8FAFC_45%,#ECFDF5_100%)] p-8 text-center shadow-[var(--shadow-card)]">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl border border-[#A7F3D0] bg-[#ECFDF5] text-[#047857]">
        <BarChart3 size={28} />
      </div>
      <p className="mt-5 text-xs font-black uppercase tracking-[0.16em] text-[var(--primary-dark)]">
        Sin datos para {preset.name}
      </p>
      <h2 className="mt-2 text-2xl font-black text-[var(--text-main)]">No hay registros en el periodo seleccionado</h2>
      <p className="mx-auto mt-3 max-w-2xl text-sm font-medium leading-7 text-[var(--text-muted)]">
        {message}
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <button
          onClick={onImport}
          className="inline-flex items-center gap-2 rounded-2xl border border-[#A7F3D0] bg-[#ECFDF5] px-5 py-3 text-sm font-black text-[#047857] shadow-[0_12px_24px_rgba(15,23,42,0.06)]"
        >
          <Database size={17} />
          Ir a Importacion de datos
        </button>
        <button
          onClick={onPrimary}
          className="inline-flex items-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_12px_24px_rgba(14,124,102,0.18)]"
        >
          Activar modulo operativo
        </button>
      </div>
    </section>
  );
}

export default ReportesPage;
