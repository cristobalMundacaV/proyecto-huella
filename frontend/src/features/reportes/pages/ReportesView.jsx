import { useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Factory,
  Filter,
  Flame,
  Gauge,
  Layers3,
  RefreshCcw,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import Pagination from "@/shared/components/Pagination";
import Toast from "@/shared/components/Toast";
import { getConstructoraRegistrosEmision } from "@/shared/services/api";

const rowsPerPage = 10;
const CATEGORY_ORDER = [
  "Materiales",
  "Energia",
  "Maquinaria",
  "Residuos",
  "Transporte",
  "Agua",
  "Procesos externos",
  "Otros",
];

const CATEGORY_CONFIG = {
  Materiales: { label: "Materiales", color: "#EA580C" },
  Energia: { label: "Energía", color: "#7C3AED" },
  Maquinaria: { label: "Maquinaria", color: "#65A30D" },
  Residuos: { label: "Residuos", color: "#059669" },
  Transporte: { label: "Transporte", color: "#2563EB" },
  Agua: { label: "Agua", color: "#0891B2" },
  "Procesos externos": { label: "Procesos externos", color: "#DB2777" },
  Otros: { label: "Otros", color: "#475569" },
};

function formatNumber(value, decimals = 1) {
  const n = Number(value || 0);
  return n.toLocaleString("es-CL", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function normalizeCategory(category) {
  const normalized = normalizeText(category);
  if (normalized.includes("material")) return "Materiales";
  if (normalized.includes("energia") || normalized.includes("electric")) return "Energia";
  if (normalized.includes("maquinaria") || normalized.includes("equipo")) return "Maquinaria";
  if (normalized.includes("residuo")) return "Residuos";
  if (normalized.includes("transport")) return "Transporte";
  if (normalized.includes("agua")) return "Agua";
  if (normalized.includes("proceso")) return "Procesos externos";
  return "Otros";
}

function parseRecordDate(value) {
  if (!value) return null;
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function toDateInputValue(date) {
  if (!date) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDate(value) {
  const date = parseRecordDate(value);
  if (!date) return "Sin fecha";
  return date.toLocaleDateString("es-CL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function getBucket(registro, agrupacion) {
  const date = parseRecordDate(registro.fecha);
  if (!date) {
    return { key: "sin-fecha", label: "Sin fecha" };
  }

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  if (agrupacion === "dia") {
    return { key: `${year}-${month}-${day}`, label: formatDate(registro.fecha) };
  }

  if (agrupacion === "anio") {
    return { key: String(year), label: String(year) };
  }

  const label = date.toLocaleDateString("es-CL", {
    month: "short",
    year: "2-digit",
  });
  return { key: `${year}-${month}`, label };
}

function getEmissionValue(registro) {
  return Number(registro.emisiones_kg_co2e || registro.emisiones || 0);
}

function groupEmissions(registros, resolver) {
  const grouped = new Map();
  registros.forEach((registro) => {
    const key = resolver(registro) || "Sin datos";
    const current = grouped.get(key) || { name: key, emisiones: 0, registros: 0 };
    current.emisiones += getEmissionValue(registro);
    current.registros += 1;
    grouped.set(key, current);
  });
  return Array.from(grouped.values()).sort((a, b) => b.emisiones - a.emisiones);
}

function buildTemporalSerie(registros, agrupacion) {
  const grouped = new Map();

  registros.forEach((registro) => {
    const bucket = getBucket(registro, agrupacion);
    const current = grouped.get(bucket.key) || {
      key: bucket.key,
      label: bucket.label,
      emisiones: 0,
      registros: 0,
    };
    current.emisiones += getEmissionValue(registro);
    current.registros += 1;
    grouped.set(bucket.key, current);
  });

  return Array.from(grouped.values()).sort((a, b) => String(a.key).localeCompare(String(b.key)));
}

function buildCategoryChartData(registros) {
  const grouped = new Map();

  CATEGORY_ORDER.forEach((category) => {
    grouped.set(category, {
      categoria: CATEGORY_CONFIG[category]?.label || category,
      categoriaKey: category,
      emisiones: 0,
      color: CATEGORY_CONFIG[category]?.color || "#475569",
    });
  });

  registros.forEach((registro) => {
    const category = normalizeCategory(registro.categoria);
    const current = grouped.get(category) || {
      categoria: category,
      categoriaKey: category,
      emisiones: 0,
      color: CATEGORY_CONFIG[category]?.color || "#475569",
    };
    current.emisiones += getEmissionValue(registro);
    grouped.set(category, current);
  });

  return Array.from(grouped.values())
    .filter((item) => item.emisiones > 0)
    .sort((a, b) => b.emisiones - a.emisiones);
}

function buildReport(registros, filters, activeConstructora) {
  const filtered = registros
    .filter((registro) => {
      const date = parseRecordDate(registro.fecha);
      if (filters.fecha_inicio && (!date || date < parseRecordDate(filters.fecha_inicio))) return false;
      if (filters.fecha_fin && (!date || date > parseRecordDate(filters.fecha_fin))) return false;
      return true;
    })
    .sort((a, b) => String(b.fecha || "").localeCompare(String(a.fecha || "")) || Number(b.id || 0) - Number(a.id || 0));

  const serie = buildTemporalSerie(filtered, filters.agrupacion || "mes");
  const categorias = buildCategoryChartData(filtered);
  const bySource = groupEmissions(filtered, (registro) => registro.fuente_emision || "Sin fuente");
  const byStage = groupEmissions(filtered, (registro) => registro.etapa_nombre || "Sin etapa");
  const total = filtered.reduce((sum, registro) => sum + getEmissionValue(registro), 0);
  const maxPeriod = serie.reduce((best, item) => (!best || item.emisiones > best.emisiones ? item : best), null);
  const lastPeriod = serie[serie.length - 1];
  const previousPeriod = serie[serie.length - 2];
  const variation = previousPeriod?.emisiones > 0
    ? ((Number(lastPeriod?.emisiones || 0) - previousPeriod.emisiones) / previousPeriod.emisiones) * 100
    : 0;
  const absVariation = Math.abs(variation);
  let tendencia = "Sin datos";
  if (serie.length >= 2) {
    if (absVariation <= 3) tendencia = "Estable";
    else tendencia = variation > 0 ? "Al alza" : "A la baja";
  }

  return {
    constructora_nombre: activeConstructora?.nombre || "La constructora",
    registros: filtered,
    serie,
    categorias,
    kpis: {
      emisiones_totales_periodo: total,
      tendencia,
      variacion_periodo: variation,
      periodo_mayor_emision: maxPeriod?.label || "Sin datos",
      emisiones_periodo_mayor: maxPeriod?.emisiones || 0,
      fuente_critica_periodo: bySource[0]?.name || "Sin datos",
      fuente_critica_emisiones: bySource[0]?.emisiones || 0,
      unidad_critica_periodo: byStage[0]?.name || "Sin datos",
      unidad_critica_emisiones: byStage[0]?.emisiones || 0,
      promedio_periodo: serie.length ? total / serie.length : 0,
      registros_count: filtered.length,
    },
    insights: buildReportInsights({ total, tendencia, bySource, byStage, categorias, maxPeriod }),
  };
}

function buildReportInsights({ total, tendencia, bySource, byStage, categorias, maxPeriod }) {
  if (!total) {
    return [
      "Aún no existen emisiones registradas para el período seleccionado.",
      "Carga registros o amplía el rango de fechas para generar una lectura ejecutiva.",
      "El reporte se activará automáticamente cuando existan datos válidos.",
    ];
  }

  const topCategory = categorias[0];
  const topSource = bySource[0];
  const topStage = byStage[0];
  const trendText = tendencia === "A la baja"
    ? "La tendencia mejora; conviene sostener las acciones que explican la reducción."
    : tendencia === "Al alza"
    ? "La tendencia sube; conviene intervenir el foco crítico antes de que el período cierre con mayor impacto."
    : "La tendencia se mantiene estable; conviene reforzar control semanal para evitar desvíos.";

  return [
    `${trendText}`,
    `La fuente prioritaria es ${topSource?.name || "Sin datos"}, con ${formatNumber(topSource?.emisiones || 0)} kg CO2e.`,
    `La etapa con mayor impacto es ${topStage?.name || "Sin datos"}; el período más alto es ${maxPeriod?.label || "Sin datos"}.`,
    `La categoría dominante es ${topCategory?.categoria || "Sin datos"}, por lo que debe guiar la primera decisión de reducción.`,
  ];
}

function buildHeroTitle({ trend, total }) {
  if (!total) return "Aún no hay emisiones para analizar en este período";
  if (trend === "A la baja") return "Las emisiones bajan, pero el foco crítico sigue activo";
  if (trend === "Al alza") return "Las emisiones aumentaron y requieren intervención";
  if (trend === "Estable") return "Las emisiones se mantienen estables bajo seguimiento";
  return "Estado general de emisiones del período analizado";
}

function buildHeroParagraph({ companyName, kpis }) {
  const total = Number(kpis.emisiones_totales_periodo || 0);
  if (!total) {
    return `${companyName} no registra emisiones dentro del período seleccionado. Ajusta los filtros o carga registros de emisión para activar la lectura temporal.`;
  }

  const variacion = Number(kpis.variacion_periodo || 0);
  const variacionAbs = formatNumber(Math.abs(variacion));
  const trend = kpis.tendencia;
  let trendText = "sin comparación suficiente contra el período anterior";

  if (trend === "A la baja") trendText = `con una disminución de ${variacionAbs}% frente al período anterior`;
  if (trend === "Al alza") trendText = `con un aumento de ${variacionAbs}% frente al período anterior`;
  if (trend === "Estable") trendText = `con una variación controlada de ${variacionAbs}%`;

  return `${companyName} emitió ${formatNumber(total)} kg CO2e en el período analizado, ${trendText}. La fuente prioritaria es ${kpis.fuente_critica_periodo} y la etapa con mayor impacto es ${kpis.unidad_critica_periodo}.`;
}

function getTrendTone(tendencia) {
  if (tendencia === "Al alza") return "danger";
  if (tendencia === "A la baja") return "success";
  if (tendencia === "Estable") return "warning";
  return "info";
}

function KpiCard({ icon, label, value, subtext, tone = "neutral" }) {
  const toneClass = getKpiTone(tone);

  return (
    <article className={`premium-card premium-card-interactive relative min-h-[150px] overflow-hidden rounded-3xl border p-5 shadow-[0_14px_34px_rgba(15,23,42,0.08)] transition hover:-translate-y-0.5 ${toneClass.card}`}>
      <div className={`absolute inset-x-6 top-0 h-1.5 rounded-b-full ${toneClass.accent}`} />
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-2xl border bg-white ${toneClass.icon}`}>
          {icon}
        </div>
        <p className="text-xs font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">{label}</p>
      </div>
      <div className="mt-5 flex min-h-[48px] items-center">
        <p className={`text-2xl font-black leading-tight ${toneClass.value}`}>{value}</p>
      </div>
      {subtext && <p className="mt-2 text-sm font-semibold text-[var(--text-muted)]">{subtext}</p>}
    </article>
  );
}

function getKpiTone(tone) {
  const tones = {
    danger: { card: "border-[#FDA4AF] bg-[#FFF1F2]", icon: "border-[#FDA4AF] text-[#BE123C]", value: "text-[#BE123C]", accent: "bg-[#E11D48]" },
    success: { card: "border-[#86EFAC] bg-[#ECFDF3]", icon: "border-[#86EFAC] text-[#047857]", value: "text-[#047857]", accent: "bg-[#059669]" },
    warning: { card: "border-[#FDBA74] bg-[#FFF7ED]", icon: "border-[#FDBA74] text-[#C2410C]", value: "text-[#C2410C]", accent: "bg-[#EA580C]" },
    info: { card: "border-[#93C5FD] bg-[#EFF6FF]", icon: "border-[#93C5FD] text-[#1D4ED8]", value: "text-[#1D4ED8]", accent: "bg-[#2563EB]" },
    neutral: { card: "border-[#CBD5E1] bg-white", icon: "border-[#CBD5E1] text-[#334155]", value: "text-[var(--text-main)]", accent: "bg-[#475569]" },
  };
  return tones[tone] || tones.neutral;
}

function ReportChartTooltip({ active, payload, label, labelPrefix = "Período" }) {
  if (!active || !payload?.length) return null;
  const value = Number(payload[0]?.value || 0);

  return (
    <div className="max-w-[280px] rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--text-muted)]">{labelPrefix}</p>
      <p className="text-sm font-semibold text-[var(--text-main)]">{label || "Sin etiqueta"}</p>
      <p className="mt-1 text-sm font-black text-[#075985]">{formatNumber(value)} kg CO2e</p>
    </div>
  );
}

function EmptyReportState({ onOpenFilters }) {
  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[linear-gradient(135deg,#FFFFFF_0%,#F8FAFC_45%,#ECFDF5_100%)] p-8 text-center shadow-[var(--shadow-card)]">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl border border-[#A7F3D0] bg-[#ECFDF5] text-[#047857]">
        <BarChart3 size={28} />
      </div>
      <p className="mt-5 text-xs font-black uppercase tracking-[0.16em] text-[var(--primary-dark)]">Sin datos para reportar</p>
      <h2 className="mt-2 text-2xl font-black text-[var(--text-main)]">No hay emisiones en el período seleccionado</h2>
      <p className="mx-auto mt-3 max-w-2xl text-sm font-medium leading-7 text-[var(--text-muted)]">
        El módulo de reportes se construye desde los registros reales de emisión de la constructora activa. Amplía el rango de fechas o carga registros para visualizar tendencias, KPIs y detalle temporal.
      </p>
      <button
        onClick={onOpenFilters}
        className="mt-6 inline-flex items-center gap-2 rounded-2xl border border-[#A7F3D0] bg-[#ECFDF5] px-5 py-3 text-sm font-black text-[#047857] shadow-[0_12px_24px_rgba(15,23,42,0.06)]"
      >
        <Filter size={17} />
        Revisar filtros
      </button>
    </section>
  );
}

function ReportesHeroEjecutivo({ kpis, activeConstructora, insights }) {
  const title = buildHeroTitle({ trend: kpis.tendencia, total: kpis.emisiones_totales_periodo });
  const summary = buildHeroParagraph({
    companyName: activeConstructora?.nombre || "La constructora",
    kpis,
  });
  const trendTone = getTrendTone(kpis.tendencia);

  return (
    <section className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)] sm:p-7">
      <div className="grid gap-6 lg:grid-cols-[1.45fr_0.9fr] lg:items-start">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--secondary)]">Resumen ejecutivo</p>
          <h2 className="mt-3 text-3xl font-black leading-tight text-[var(--text-main)] md:text-4xl">{title}</h2>
          <p className="mt-4 max-w-3xl text-base leading-7 text-[var(--text-muted)]">{summary}</p>
          <ul className="mt-5 space-y-2 text-sm font-medium text-[var(--secondary)]">
            {insights.slice(0, 4).map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[var(--primary)]" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
          <HeroBadge label="Comportamiento del período" value={kpis.tendencia || "Sin datos"} tone={trendTone} />
          <HeroBadge label="Fuente prioritaria" value={kpis.fuente_critica_periodo || "Sin datos"} tone="info" />
          <HeroBadge label="Etapa prioritaria" value={kpis.unidad_critica_periodo || "Sin datos"} tone="info" />
          <HeroBadge label="Período con mayor emisión" value={kpis.periodo_mayor_emision || "Sin datos"} tone="warning" />
        </div>
      </div>
    </section>
  );
}

function HeroBadge({ label, value, tone = "info" }) {
  const toneClass = getKpiTone(tone);
  return (
    <div className={`rounded-2xl border p-4 ${toneClass.card}`}>
      <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className={`mt-1 text-sm font-black leading-snug ${toneClass.value}`}>{value}</p>
    </div>
  );
}

export default function ReportesView({ activeConstructoraId, activeConstructora }) {
  const defaultFilters = useMemo(() => ({
    fecha_inicio: "",
    fecha_fin: "",
    agrupacion: "mes",
  }), []);

  const [allRegistros, setAllRegistros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState(defaultFilters);
  const [draftFilters, setDraftFilters] = useState(defaultFilters);
  const [currentPage, setCurrentPage] = useState(1);
  const currentPageRef = useRef(1);
  const [isFiltersModalOpen, setIsFiltersModalOpen] = useState(false);

  async function loadReport(showLoading = true) {
    if (!activeConstructoraId) return;
    try {
      if (showLoading) setLoading(true);
      setError("");
      const registrosData = await getConstructoraRegistrosEmision(activeConstructoraId);
      const normalized = Array.isArray(registrosData) ? registrosData : registrosData?.results || [];
      setAllRegistros(normalized);
    } catch (requestError) {
      console.error(requestError);
      setError("No se pudieron cargar los registros de emisión para construir el reporte.");
    } finally {
      if (showLoading) setLoading(false);
    }
  }

  useEffect(() => {
    setAllRegistros([]);
    setCurrentPage(1);
    if (!activeConstructoraId) return;
    loadReport(true);
    const intervalId = window.setInterval(() => loadReport(false), 10000);
    return () => window.clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConstructoraId]);

  useEffect(() => {
    currentPageRef.current = currentPage;
  }, [currentPage]);

  const report = useMemo(
    () => buildReport(allRegistros, filters, activeConstructora),
    [allRegistros, filters, activeConstructora]
  );
  const kpis = report.kpis;
  const serie = report.serie;
  const categoryChartData = report.categorias;
  const hasEnoughTemporalData = serie.length >= 2;
  const totalRows = report.registros.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const visibleRows = report.registros.slice((safeCurrentPage - 1) * rowsPerPage, safeCurrentPage * rowsPerPage);
  const hasFilteredData = totalRows > 0;

  useEffect(() => {
    if (currentPage > totalPages) setCurrentPage(totalPages);
  }, [currentPage, totalPages]);

  function openFiltersModal() {
    setDraftFilters(filters);
    setIsFiltersModalOpen(true);
  }

  function closeFiltersModal() {
    setIsFiltersModalOpen(false);
  }

  function applyFiltersFromModal() {
    setFilters({
      fecha_inicio: draftFilters.fecha_inicio || "",
      fecha_fin: draftFilters.fecha_fin || "",
      agrupacion: draftFilters.agrupacion || "mes",
    });
    setCurrentPage(1);
    setIsFiltersModalOpen(false);
  }

  function clearFiltersFromModal() {
    setDraftFilters(defaultFilters);
    setFilters(defaultFilters);
    setCurrentPage(1);
    setIsFiltersModalOpen(false);
  }

  const renderTemporalDot = (props) => {
    const { cx, cy, payload } = props || {};
    if (cx == null || cy == null) return null;
    const isCritical = String(payload?.label || "") === String(kpis.periodo_mayor_emision || "");
    return (
      <circle
        cx={cx}
        cy={cy}
        r={isCritical ? 5 : 3}
        fill={isCritical ? "#E11D48" : "#0891B2"}
        stroke="#fff"
        strokeWidth={1.5}
      />
    );
  };

  if (!activeConstructoraId) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-10 text-[var(--text-main)]">
        <h1 className="text-4xl font-black">Reportes</h1>
        <div className="mt-8 rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-8 text-center text-[var(--text-muted)]">
          Selecciona o crea una constructora para revisar reportes temporales de emisiones.
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-8 px-4 py-8 text-[var(--text-main)] sm:px-6 lg:px-10 lg:py-12">
      <Toast
        message={loading ? "Cargando reportes..." : ""}
        loading={loading}
        onClose={() => undefined}
        toastKey={loading ? "report-loading" : "report-idle"}
      />

      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-[var(--secondary)]">Reporte temporal</p>
          <h1 className="mt-2 text-3xl font-bold sm:text-4xl">Reportes</h1>
          <p className="mt-2 text-[var(--text-muted)]">
            Analiza la evolución de emisiones, detecta períodos críticos y convierte los resultados en decisiones de mejora.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={openFiltersModal}
            className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200/70 bg-[linear-gradient(180deg,rgba(236,253,243,1),rgba(220,252,231,0.94))] px-5 py-3 text-sm font-bold text-[var(--secondary)] shadow-[0_12px_24px_rgba(15,23,42,0.05)] transition hover:-translate-y-px"
          >
            <Filter size={18} />
            Filtros
          </button>
          <button
            onClick={() => loadReport(true)}
            className="inline-flex items-center gap-2 rounded-2xl border border-[#B8D6DE] bg-[var(--info-bg)] px-5 py-3 text-sm font-bold text-[#075985] shadow-[0_12px_24px_rgba(15,23,42,0.05)] transition hover:-translate-y-px"
          >
            <RefreshCcw size={18} />
            Actualizar
          </button>
          <button
            disabled
            className="rounded-2xl border border-[var(--primary)]/20 bg-[linear-gradient(180deg,rgba(14,124,102,0.95),rgba(9,92,76,0.98))] px-5 py-3 text-sm font-bold text-white shadow-[0_14px_28px_rgba(14,124,102,0.22)] opacity-90"
          >
            Exportar reporte
          </button>
        </div>
      </header>

      {isFiltersModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-2xl">
            <div className="mb-5 flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--secondary)]">Filtros</p>
                <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">Configurar reporte</h2>
              </div>
              <button onClick={closeFiltersModal} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-xs font-bold text-[var(--text-muted)]">
                Cerrar
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <label className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
                Fecha inicio
                <input
                  type="date"
                  value={draftFilters.fecha_inicio}
                  onChange={(e) => setDraftFilters((prev) => ({ ...prev, fecha_inicio: e.target.value }))}
                  className="mt-2 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)]"
                />
              </label>

              <label className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
                Fecha fin
                <input
                  type="date"
                  value={draftFilters.fecha_fin}
                  onChange={(e) => setDraftFilters((prev) => ({ ...prev, fecha_fin: e.target.value }))}
                  className="mt-2 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)]"
                />
              </label>

              <label className="text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
                Agrupación
                <select
                  value={draftFilters.agrupacion}
                  onChange={(e) => setDraftFilters((prev) => ({ ...prev, agrupacion: e.target.value }))}
                  className="mt-2 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-[var(--text-main)]"
                >
                  <option value="dia">Día</option>
                  <option value="mes">Mes</option>
                  <option value="anio">Año</option>
                </select>
              </label>
            </div>

            {allRegistros.length > 0 && (
              <div className="mt-4 rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-sm font-semibold text-[var(--text-muted)]">
                Rango disponible: {formatDate(allRegistros[allRegistros.length - 1]?.fecha)} a {formatDate(allRegistros[0]?.fecha)}.
              </div>
            )}

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button onClick={clearFiltersFromModal} className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-5 py-3 text-sm font-bold text-[#475467]">
                Limpiar
              </button>
              <button onClick={applyFiltersFromModal} className="rounded-xl bg-[var(--primary-dark)] px-5 py-3 text-sm font-black text-white">
                Aplicar filtros
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-[#F1B8B8] bg-[var(--danger-bg)] p-6 text-[#B42318]">
          {error}
        </div>
      )}

      {!loading && !hasFilteredData ? (
        <EmptyReportState onOpenFilters={openFiltersModal} />
      ) : (
        <>
          <ReportesHeroEjecutivo kpis={kpis} activeConstructora={activeConstructora} insights={report.insights} />

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <KpiCard icon={<Flame size={21} />} label="Emisiones del período" value={`${formatNumber(kpis.emisiones_totales_periodo)} kg CO2e`} tone="danger" />
            <KpiCard icon={kpis.tendencia === "A la baja" ? <TrendingDown size={21} /> : <TrendingUp size={21} />} label="Comportamiento del período" value={kpis.tendencia || "Sin datos"} subtext={`${formatNumber(kpis.variacion_periodo)}% vs período anterior`} tone={getTrendTone(kpis.tendencia)} />
            <KpiCard icon={<CalendarDays size={21} />} label="Período con mayor emisión" value={kpis.periodo_mayor_emision || "Sin datos"} subtext={`${formatNumber(kpis.emisiones_periodo_mayor)} kg CO2e`} tone="warning" />
            <KpiCard icon={<AlertTriangle size={21} />} label="Fuente prioritaria" value={kpis.fuente_critica_periodo || "Sin datos"} subtext={`${formatNumber(kpis.fuente_critica_emisiones)} kg CO2e`} tone="warning" />
            <KpiCard icon={<Factory size={21} />} label="Etapa prioritaria" value={kpis.unidad_critica_periodo || "Sin datos"} subtext={`${formatNumber(kpis.unidad_critica_emisiones)} kg CO2e`} tone="info" />
            <KpiCard icon={<Gauge size={21} />} label="Emisión promedio" value={`${formatNumber(kpis.promedio_periodo)} kg CO2e`} subtext="Promedio por período agrupado" tone="neutral" />
          </section>

          <section className="mt-8 grid gap-6 lg:grid-cols-2">
            <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[0_18px_45px_var(--shadow)]">
              <h2 className="text-xl font-black text-[var(--text-main)]">Emisiones en el tiempo</h2>
              <p className="mt-1 text-sm text-[var(--text-muted)]">Evolución de emisiones según el período filtrado.</p>

              {!hasEnoughTemporalData ? (
                <div className="mt-6 flex h-[320px] min-h-[320px] items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] px-6 text-center text-[var(--text-muted)]">
                  Se necesita más de un período para visualizar tendencia temporal. Cambia la agrupación o amplía el rango.
                </div>
              ) : (
                <div className="mt-6 h-[320px] min-h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={serie} margin={{ top: 12, right: 16, left: 0, bottom: 4 }}>
                      <defs>
                        <linearGradient id="reportAreaGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0891B2" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="#0891B2" stopOpacity={0.04} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="4 4" stroke="#B8C6BE" opacity={0.85} />
                      <XAxis dataKey="label" tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }} tickMargin={8} axisLine={{ stroke: "#64748B" }} tickLine={{ stroke: "#64748B" }} />
                      <YAxis tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }} tickFormatter={(value) => formatNumber(value)} width={72} axisLine={{ stroke: "#64748B" }} tickLine={{ stroke: "#64748B" }} />
                      <Tooltip cursor={{ stroke: "#0891B2", strokeOpacity: 0.3 }} content={<ReportChartTooltip labelPrefix="Período" />} />
                      <Area type="monotone" dataKey="emisiones" name="Emisiones" stroke="#0891B2" strokeWidth={2.5} fill="url(#reportAreaGradient)" fillOpacity={1} dot={renderTemporalDot} activeDot={renderTemporalDot} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[0_18px_45px_var(--shadow)]">
              <h2 className="text-xl font-black text-[var(--text-main)]">Emisiones por categoría</h2>
              <p className="mt-1 text-sm text-[var(--text-muted)]">Comparativo por categoría para detectar el foco ambiental principal.</p>

              <div className="mt-6 h-[320px] min-h-[320px]">
                {categoryChartData.length === 0 ? (
                  <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] text-sm text-[var(--text-muted)]">
                    No hay categorías con emisiones registradas para el período seleccionado.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={categoryChartData} margin={{ top: 10, right: 10, left: 0, bottom: 24 }}>
                      <CartesianGrid strokeDasharray="4 4" stroke="#B8C6BE" opacity={0.85} />
                      <XAxis dataKey="categoria" tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }} interval={0} angle={-22} textAnchor="end" height={62} axisLine={{ stroke: "#64748B" }} tickLine={{ stroke: "#64748B" }} />
                      <YAxis tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }} tickFormatter={(value) => formatNumber(value)} width={72} axisLine={{ stroke: "#64748B" }} tickLine={{ stroke: "#64748B" }} />
                      <Tooltip cursor={false} content={<ReportChartTooltip labelPrefix="Categoría" />} />
                      <Bar dataKey="emisiones" radius={[8, 8, 0, 0]} activeBar={{ stroke: "#e2e8f0", strokeWidth: 2 }}>
                        {categoryChartData.map((item) => <Cell key={item.categoriaKey} fill={item.color} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>

              {categoryChartData.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-[var(--text-muted)]">
                  {categoryChartData.map((item) => (
                    <span key={`${item.categoriaKey}-legend`} className="inline-flex items-center gap-2 rounded-full border px-3 py-1 font-semibold shadow-[0_8px_18px_rgba(15,23,42,0.05)]" style={{ backgroundColor: `${item.color}14`, borderColor: `${item.color}33`, color: "var(--text-main)" }}>
                      <span className="h-2.5 w-2.5 rounded-full shadow-sm" style={{ backgroundColor: item.color }} />
                      {item.categoria}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </section>

          <section className="mt-8 rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[0_18px_45px_var(--shadow)]">
            <h2 className="text-xl font-black text-[var(--text-main)]">Detalle temporal de emisiones</h2>
            <p className="mt-1 text-sm text-[var(--text-muted)]">{totalRows} registros encontrados.</p>

            <div className="mt-6 overflow-x-auto rounded-2xl border border-[var(--border)]">
              <table className="w-full min-w-[1050px]">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[var(--bg-surface)] text-xs uppercase tracking-wide text-[var(--text-muted)]">
                    <th className="px-4 py-3 text-left">Fecha</th>
                    <th className="px-4 py-3 text-left">Etapa</th>
                    <th className="px-4 py-3 text-left">Obra</th>
                    <th className="px-4 py-3 text-left">Categoría</th>
                    <th className="px-4 py-3 text-left">Fuente</th>
                    <th className="px-4 py-3 text-right">Cantidad</th>
                    <th className="px-4 py-3 text-left">Unidad</th>
                    <th className="px-4 py-3 text-right">Emisiones</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.map((row, index) => (
                    <tr key={`${row.fecha}-${row.fuente_emision}-${row.id || index}`} className="border-b border-[#E2E8F0] text-[#1F2937] hover:bg-[var(--bg-surface)]">
                      <td className="px-4 py-3 font-semibold">{formatDate(row.fecha)}</td>
                      <td className="px-4 py-3">{row.etapa_nombre || "Sin etapa"}</td>
                      <td className="px-4 py-3">{row.obra_nombre || row.obra_codigo || "-"}</td>
                      <td className="px-4 py-3">{normalizeCategory(row.categoria)}</td>
                      <td className="px-4 py-3 font-semibold">{row.fuente_emision || "Sin fuente"}</td>
                      <td className="px-4 py-3 text-right">{formatNumber(row.cantidad, 2)}</td>
                      <td className="px-4 py-3">{row.unidad || "-"}</td>
                      <td className="px-4 py-3 text-right font-black text-[#075985]">{formatNumber(getEmissionValue(row))} kg CO2e</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <Pagination currentPage={safeCurrentPage} itemLabel="registros" onPageChange={setCurrentPage} pageSize={rowsPerPage} totalItems={totalRows} />
          </section>
        </>
      )}
    </main>
  );
}
