import { useEffect, useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { Activity, AlertTriangle, CalendarDays, Filter, Gauge, TrendingDown, TrendingUp } from "lucide-react";
import { getReporteEmisionesTiempo } from "../../../shared/services/api";
import Pagination from "@/shared/components/Pagination";
import Toast from "@/shared/components/Toast";

const rowsPerPage = 10;
const CATEGORY_ORDER = [
  "combustible",
  "transporte",
  "electricidad",
  "agua",
  "materiales",
  "residuos",
  "otros",
];

const CATEGORY_CONFIG = {
  combustible: { label: "Combustible", color: "#f59e0b" },
  transporte: { label: "Transporte", color: "#60a5fa" },
  electricidad: { label: "Electricidad", color: "#22d3ee" },
  agua: { label: "Agua", color: "#14b8a6" },
  materiales: { label: "Materiales", color: "#a78bfa" },
  residuos: { label: "Residuos", color: "#fb7185" },
  otros: { label: "Otros", color: "#94a3b8" },
};

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function resolveCategoryKey(category) {
  const normalized = normalizeText(category);

  if (normalized.includes("combust")) return "combustible";
  if (normalized.includes("transport")) return "transporte";
  if (normalized.includes("electric")) return "electricidad";
  if (normalized.includes("agua")) return "agua";
  if (normalized.includes("material")) return "materiales";
  if (normalized.includes("residu")) return "residuos";

  return "otros";
}

function ReportChartTooltip({ active, payload, label, labelPrefix = "Periodo" }) {
  if (!active || !payload?.length) {
    return null;
  }

  const first = payload[0];
  const value = Number(first?.value || 0);

  return (
    <div className="max-w-[280px] rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 shadow-[var(--shadow-card)] backdrop-blur-sm">
      <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--text-muted)]">{labelPrefix}</p>
      <p className="text-sm font-semibold text-[var(--text-main)]">{label || "Sin etiqueta"}</p>
      <p className="mt-1 text-sm font-bold text-[#075985]">{formatNumber(value)} kg CO2e</p>
    </div>
  );
}

function formatNumber(value, decimals = 1) {
  const n = Number(value || 0);
  return n.toLocaleString("es-CL", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function KpiCard({ icon, label, value, subtext, tone = "default" }) {
  const toneClass =
    tone === "danger"
      ? "border-rose-400/20 bg-rose-400/10 text-rose-100"
      : tone === "success"
      ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-100"
      : tone === "warning"
      ? "border-amber-400/20 bg-amber-400/10 text-amber-100"
      : "border-slate-700 bg-slate-900/60 text-slate-100";

  return (
    <div className={`rounded-3xl border p-5 ${toneClass}`}>
      <div className="mb-3 flex items-center gap-3">
        {icon ? <div className="opacity-90">{icon}</div> : null}
        <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      </div>
      <p className="mt-3 text-2xl font-black">{value}</p>
      {subtext && <p className="mt-2 text-sm text-slate-400">{subtext}</p>}
    </div>
  );
}

function normalizeTrend(value) {
  return normalizeText(value);
}

function buildHeroTitle({ trend, variacion }) {
  if (trend === "a la baja") {
    return "La tendencia mejora en este período, pero el foco crítico sigue activo";
  }

  if (trend === "al alza") {
    return "Las emisiones aumentaron y requieren intervencion";
  }

  if (trend === "estable") {
    if (Math.abs(Number(variacion || 0)) <= 3) {
      return "Las emisiones se mantienen controladas y estables";
    }
    return "El periodo se mantuvo estable, pero con ajustes pendientes";
  }

  return "Estado general de emisiones del periodo analizado";
}

function buildHeroParagraph({ companyName, kpis, trend }) {
  const total = formatNumber(kpis.emisiones_totales_periodo);
  const variacion = Number(kpis.variacion_periodo || 0);
  const variacionAbs = formatNumber(Math.abs(variacion));
  const actividad = kpis.actividad_critica_periodo || "la actividad principal";
  const unidad = kpis.unidad_critica_periodo || "la unidad principal";

  let trendText = "sin una tendencia clara";
  if (trend === "a la baja") {
    trendText = `con una disminucion de ${variacionAbs}% vs el período anterior`;
  } else if (trend === "al alza") {
    trendText = `con un aumento de ${variacionAbs}% vs el período anterior`;
  } else if (trend === "estable") {
    trendText = `manteniendose estable, con una variacion de ${variacionAbs}%`;
  }

  return `${companyName} emitió ${total} kg CO2e en el período analizado, ${trendText}. El principal foco sigue estando en ${actividad} y la unidad con mayor impacto es ${unidad}.`;
}

function buildHeroInsights({ trend, kpis }) {
  const actividad = kpis.actividad_critica_periodo || "Sin datos";
  const unidad = kpis.unidad_critica_periodo || "Sin datos";

  let recommendation = "Mantener seguimiento semanal para sostener el control del período.";
  if (trend === "al alza") {
    recommendation = "Priorizar acciones inmediatas en la actividad y unidad criticas para frenar el alza.";
  } else if (trend === "a la baja") {
    recommendation = "Consolidar las medidas actuales para sostener la reduccion observada.";
  }

  return [
    `Mejora observada: ${kpis.tendencia || "Sin datos"}`,
    `Foco a mantener bajo control: ${actividad}`,
    `Unidad prioritaria: ${unidad}. ${recommendation}`,
  ];
}

function HeroBadge({ label, value, tone = "default" }) {
  const toneClass =
    tone === "danger"
      ? "border-rose-400/30 bg-rose-400/10 text-rose-100"
      : tone === "success"
      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-100"
      : tone === "warning"
      ? "border-amber-400/30 bg-amber-400/10 text-amber-100"
      : "border-cyan-400/20 bg-slate-950/70 text-slate-100";

  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <p className="text-[11px] uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-sm font-bold leading-snug">{value || "Sin datos"}</p>
    </div>
  );
}

function ReportesHeroEjecutivo({ kpis, activeEmpresa }) {
  const trend = normalizeTrend(kpis.tendencia);
  const title = buildHeroTitle({ trend, variacion: kpis.variacion_periodo });
  const summary = buildHeroParagraph({
    companyName: activeEmpresa?.nombre || "La empresa",
    kpis,
    trend,
  });
  const insights = buildHeroInsights({ trend, kpis });

  return (
    <section className="rounded-3xl border border-cyan-400/30 bg-cyan-400/10 p-5 shadow-[0_0_40px_rgba(34,211,238,0.10)] sm:p-7">
      <div className="grid gap-6 lg:grid-cols-[1.45fr_0.9fr] lg:items-start">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-300">
            Resumen ejecutivo
          </p>
          <h2 className="mt-3 text-3xl font-black leading-tight text-slate-100 md:text-4xl">
            {title}
          </h2>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-200">{summary}</p>

          <ul className="mt-5 space-y-2 text-sm text-cyan-100">
            {insights.map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-cyan-300" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
          <HeroBadge label="Comportamiento del período" value={kpis.tendencia || "Sin datos"} tone={trend === "al alza" ? "danger" : trend === "a la baja" ? "success" : trend === "estable" ? "warning" : "default"} />
          <HeroBadge label="Actividad prioritaria" value={kpis.actividad_critica_periodo || "Sin datos"} tone="default" />
          <HeroBadge label="Unidad prioritaria" value={kpis.unidad_critica_periodo || "Sin datos"} tone="default" />
          <HeroBadge label="Período con mayor emisión" value={kpis.periodo_mayor_emision || "Sin datos"} tone="warning" />
        </div>
      </div>
    </section>
  );
}

export default function ReportesView({ activeEmpresaId, activeEmpresa }) {
  const defaultFilters = {
    agrupacion: "mes",
    fecha_inicio: "",
    fecha_fin: "",
    unidad_id: "",
    categoria: "",
    actividad: "",
  };

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsCount, setRowsCount] = useState(0);
  const [paginatedRows, setPaginatedRows] = useState([]);
  const [isFiltersModalOpen, setIsFiltersModalOpen] = useState(false);

  const [filters, setFilters] = useState(defaultFilters);
  const [draftFilters, setDraftFilters] = useState({
    fecha_inicio: "",
    fecha_fin: "",
    agrupacion: "mes",
  });

  async function loadReport(filtersToUse = filters) {
    if (!activeEmpresaId) return;

    try {
      setLoading(true);
      setError("");
      const result = await getReporteEmisionesTiempo(activeEmpresaId, {
        ...filtersToUse,
        page: 1,
        page_size: rowsPerPage,
      });
      setData(result);
      setCurrentPage(1);
      setPaginatedRows(result.rows || []);
      setRowsCount(result.rows_count || 0);
    } catch (err) {
      console.error(err);
      setError("No se pudo cargar el reporte temporal.");
    } finally {
      setLoading(false);
    }
  }

  async function loadRows(page = 1) {
    if (!activeEmpresaId) return;

    try {
      setLoading(true);
      setError("");
      const result = await getReporteEmisionesTiempo(activeEmpresaId, {
        ...filters,
        page,
        page_size: rowsPerPage,
      });

      setPaginatedRows(result.rows || []);
      setRowsCount(result.rows_count || 0);
      setCurrentPage(page);
    } catch (err) {
      console.error(err);
      setError("No se pudo cargar las filas del reporte.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeEmpresaId]);

  const kpis = useMemo(() => data?.kpis || {}, [data]);
  const serie = useMemo(() => data?.serie_temporal || [], [data]);
  const categorias = useMemo(() => data?.por_categoria || [], [data]);
  const rows = useMemo(() => data?.rows || [], [data]);
  const insights = useMemo(() => data?.insights || [], [data]);
  const complementaryInsights = useMemo(() => insights.slice(0, 3), [insights]);
  const totalPages = Math.max(1, Math.ceil(rowsCount / rowsPerPage));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const visibleRows = paginatedRows;

  const categoryChartData = useMemo(() => {
    const source = categorias.length > 0 ? categorias : rows;
    const grouped = new Map();

    CATEGORY_ORDER.forEach((key) => {
      grouped.set(key, {
        categoriaKey: key,
        categoria: CATEGORY_CONFIG[key].label,
        emisiones: 0,
        color: CATEGORY_CONFIG[key].color,
      });
    });

    source.forEach((item) => {
      const key = resolveCategoryKey(item?.categoria);
      const current = grouped.get(key);
      grouped.set(key, {
        ...current,
        emisiones: Number(current?.emisiones || 0) + Number(item?.emisiones || 0),
      });
    });

    return Array.from(grouped.values())
      .filter((item) => Number(item?.emisiones || 0) > 0)
      .sort((a, b) => Number(b?.emisiones || 0) - Number(a?.emisiones || 0));
  }, [categorias, rows]);

  const hasEnoughTemporalData = serie.length >= 2;

  const tendenciaTone = useMemo(() => {
    const tendencia = String(kpis.tendencia || "").toLowerCase();

    if (tendencia === "al alza") return "danger";
    if (tendencia === "a la baja") return "success";
    if (tendencia === "estable") return "default";

    return "warning";
  }, [kpis.tendencia]);

  function openFiltersModal() {
    setDraftFilters({
      fecha_inicio: filters.fecha_inicio || "",
      fecha_fin: filters.fecha_fin || "",
      agrupacion: filters.agrupacion || "mes",
    });
    setIsFiltersModalOpen(true);
  }

  function closeFiltersModal() {
    setIsFiltersModalOpen(false);
  }

  async function applyFiltersFromModal() {
    const nextFilters = {
      ...filters,
      fecha_inicio: draftFilters.fecha_inicio || "",
      fecha_fin: draftFilters.fecha_fin || "",
      agrupacion: draftFilters.agrupacion || "mes",
    };

    setFilters(nextFilters);
    setIsFiltersModalOpen(false);
    await loadReport(nextFilters);
  }

  async function clearFiltersFromModal() {
    setDraftFilters({ fecha_inicio: "", fecha_fin: "", agrupacion: "mes" });
    setFilters(defaultFilters);
    setIsFiltersModalOpen(false);
    await loadReport(defaultFilters);
  }

  // Render temporal dots, highlighting the critical period in red
  const renderTemporalDot = (props) => {
    const { cx, cy, payload } = props || {};
    if (cx == null || cy == null) return null;

    const critical = String(kpis.periodo_mayor_emision || "");
    const isCritical = String(payload?.label || "") === critical;

    const radius = isCritical ? 5 : 3;
    const fill = isCritical ? "#fb7185" : "#67e8f9"; // red for critical, cyan otherwise
    const stroke = isCritical ? "#fff" : "#0f172a";
    const strokeWidth = isCritical ? 1.5 : 1;

    return (
      <g>
        <circle cx={cx} cy={cy} r={radius} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
      </g>
    );
  };

  if (!activeEmpresaId) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-10 text-slate-100">
        <h1 className="text-4xl font-black">Reportes</h1>
        <div className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/60 p-8 text-center">
          Selecciona o crea una empresa para revisar reportes temporales de emisiones.
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-8 px-4 py-8 text-slate-100 sm:px-6 lg:px-10 lg:py-12">
      <Toast
        message={loading ? "Cargando..." : ""}
        loading={loading}
        onClose={() => undefined}
        toastKey={loading ? "report-loading" : "report-idle"}
      />

      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-cyan-300">
            Reporte temporal
          </p>
          <h1 className="mt-2 text-3xl font-bold sm:text-4xl">Reportes</h1>
          <p className="mt-2 text-slate-400">
            Analiza la evolución de emisiones, detecta períodos críticos y convierte los resultados en decisiones de mejora.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={openFiltersModal}
            className="inline-flex items-center gap-2 rounded-2xl border border-cyan-400/30 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/20"
          >
            <Filter size={18} />
            Filtros
          </button>
          <button
            disabled
            className="rounded-xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-400"
          >
            Exportar reporte
          </button>
        </div>
      </header>

      {isFiltersModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="mb-5 flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-300">
                  Filtros
                </p>
                <h2 className="mt-1 text-2xl font-black text-slate-100">Configurar reporte</h2>
              </div>
              <button
                onClick={closeFiltersModal}
                className="rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300"
              >
                Cerrar
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="text-xs uppercase tracking-wide text-slate-400">
                  Fecha inicio
                </label>
                <input
                  type="date"
                  value={draftFilters.fecha_inicio}
                  onChange={(e) =>
                    setDraftFilters((prev) => ({ ...prev, fecha_inicio: e.target.value }))
                  }
                  className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3"
                />
              </div>

              <div>
                <label className="text-xs uppercase tracking-wide text-slate-400">
                  Fecha fin
                </label>
                <input
                  type="date"
                  value={draftFilters.fecha_fin}
                  onChange={(e) =>
                    setDraftFilters((prev) => ({ ...prev, fecha_fin: e.target.value }))
                  }
                  className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3"
                />
              </div>

              <div>
                <label className="text-xs uppercase tracking-wide text-slate-400">
                  Agrupacion
                </label>
                <select
                  value={draftFilters.agrupacion}
                  onChange={(e) =>
                    setDraftFilters((prev) => ({ ...prev, agrupacion: e.target.value }))
                  }
                  className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3"
                >
                  <option value="dia">Dia</option>
                  <option value="mes">Mes</option>
                  <option value="anio">Anio</option>
                </select>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button
                onClick={clearFiltersFromModal}
                className="rounded-xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-300"
              >
                Limpiar
              </button>
              <button
                onClick={applyFiltersFromModal}
                className="rounded-xl bg-emerald-500 px-5 py-3 text-sm font-black text-slate-950"
              >
                Aplicar filtros
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-8 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      )}

      {data && (
        <>
          <ReportesHeroEjecutivo kpis={kpis} activeEmpresa={activeEmpresa} />

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <KpiCard
              label="Emisiones del período"
              value={`${formatNumber(kpis.emisiones_totales_periodo)} kg CO2e`}
            />
            <KpiCard
              label="Comportamiento del período"
              value={kpis.tendencia || "Sin datos"}
              subtext={`${formatNumber(kpis.variacion_periodo)}% vs período anterior`}
              tone={tendenciaTone}
            />
            <KpiCard
              label="Período con mayor emisión"
              value={kpis.periodo_mayor_emision || "Sin datos"}
              subtext={`${formatNumber(kpis.emisiones_periodo_mayor)} kg CO2e`}
              tone="warning"
            />
            <KpiCard
              label="Actividad prioritaria"
              value={kpis.actividad_critica_periodo || "Sin datos"}
            />
            <KpiCard
              label="Unidad prioritaria"
              value={kpis.unidad_critica_periodo || "Sin datos"}
            />
            <KpiCard
              label="Emisión promedio mensual"
              value={`${formatNumber(kpis.promedio_periodo)} kg CO2e`}
            />
          </section>

          <section className="mt-8 grid gap-6 lg:grid-cols-2">
            <div className="rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
              <h2 className="text-xl font-black">Emisiones en el tiempo</h2>
              <p className="mt-1 text-sm text-slate-400">
                Evolucion de emisiones del período filtrado.
              </p>

              {!hasEnoughTemporalData ? (
                <div className="mt-6 flex h-[320px] min-h-[320px] items-center justify-center rounded-2xl border border-slate-800 bg-slate-950/60 px-6 text-center text-slate-400">
                  Se necesita mas de un período para visualizar tendencia temporal.
                </div>
              ) : (
                <div className="mt-6 h-[320px] min-h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={serie}
                      margin={{ top: 12, right: 16, left: 0, bottom: 4 }}
                    >
                      <defs>
                        <linearGradient id="reportAreaGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.04} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="4 4" stroke="#B8C6BE" opacity={0.85} />
                      <XAxis
                        dataKey="label"
                        tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
                        tickMargin={8}
                        axisLine={{ stroke: "#64748B" }}
                        tickLine={{ stroke: "#64748B" }}
                      />
                      <YAxis
                        tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
                        tickFormatter={(value) => formatNumber(value)}
                        width={72}
                        axisLine={{ stroke: "#64748B" }}
                        tickLine={{ stroke: "#64748B" }}
                      />
                      <Tooltip
                        cursor={{ stroke: "#22d3ee", strokeOpacity: 0.3 }}
                        content={<ReportChartTooltip labelPrefix="Periodo" />}
                      />
                      <Area
                        type="monotone"
                        dataKey="emisiones"
                        name="Emisiones"
                        stroke="#22d3ee"
                        strokeWidth={2.5}
                        fill="url(#reportAreaGradient)"
                        fillOpacity={1}
                        dot={renderTemporalDot}
                        activeDot={renderTemporalDot}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
              <h2 className="text-xl font-black">Emisiones por categoría</h2>
              <p className="mt-1 text-sm text-slate-400">
                Comparativo por categoría para combustible, transporte, electricidad, agua, materiales y residuos.
              </p>

              <div className="mt-6 h-[320px] min-h-[320px]">
                {categoryChartData.length === 0 ? (
                  <div className="flex h-full items-center justify-center rounded-2xl border border-slate-800 bg-slate-950/40 text-sm text-slate-400">
                    No hay categorías con emisiones registradas para el período seleccionado.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={categoryChartData}
                      margin={{ top: 10, right: 10, left: 0, bottom: 24 }}
                    >
                      <CartesianGrid strokeDasharray="4 4" stroke="#B8C6BE" opacity={0.85} />
                      <XAxis
                        dataKey="categoria"
                        tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
                        interval={0}
                        angle={-22}
                        textAnchor="end"
                        height={62}
                        axisLine={{ stroke: "#64748B" }}
                        tickLine={{ stroke: "#64748B" }}
                      />
                      <YAxis
                        tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }}
                        tickFormatter={(value) => formatNumber(value)}
                        width={72}
                        axisLine={{ stroke: "#64748B" }}
                        tickLine={{ stroke: "#64748B" }}
                      />
                      <Tooltip
                        cursor={false}
                        content={<ReportChartTooltip labelPrefix="Categoria" />}
                      />
                      <Bar
                        dataKey="emisiones"
                        radius={[8, 8, 0, 0]}
                        activeBar={{ stroke: "#e2e8f0", strokeWidth: 2 }}
                      >
                        {categoryChartData.map((item) => (
                          <Cell key={item.categoriaKey} fill={item.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>

              {categoryChartData.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-300">
                  {categoryChartData.map((item) => (
                    <span
                      key={`${item.categoriaKey}-legend`}
                      className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950/70 px-3 py-1"
                    >
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      {item.categoria}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </section>

          <section className="mt-8 rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="text-xl font-black">Detalle temporal de emisiones</h2>
              <p className="mt-1 text-sm text-slate-400">
              {rowsCount} registros encontrados.
            </p>

            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[1100px]">
                <thead>
                  <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-400">
                    <th className="px-4 py-3 text-left">Fecha</th>
                    <th className="px-4 py-3 text-left">Unidad</th>
                    <th className="px-4 py-3 text-left">Lote</th>
                    <th className="px-4 py-3 text-left">Categoría</th>
                    <th className="px-4 py-3 text-left">Actividad</th>
                    <th className="px-4 py-3 text-right">Cantidad</th>
                    <th className="px-4 py-3 text-left">Unidad</th>
                    <th className="px-4 py-3 text-right">Emisiones</th>
                  </tr>
                </thead>

                <tbody>
                  {visibleRows.map((row, index) => (
                    <tr
                      key={`${row.fecha}-${row.actividad}-${index}`}
                      className="border-b border-slate-800/70 hover:bg-slate-800/35"
                    >
                      <td className="px-4 py-3">{row.fecha}</td>
                      <td className="px-4 py-3">{row.unidad_nombre}</td>
                      <td className="px-4 py-3">{row.id_lote || "-"}</td>
                      <td className="px-4 py-3">{row.categoria}</td>
                      <td className="px-4 py-3 font-semibold">{row.actividad}</td>
                      <td className="px-4 py-3 text-right">
                        {formatNumber(row.cantidad, 2)}
                      </td>
                      <td className="px-4 py-3">{row.unidad}</td>
                      <td className="px-4 py-3 text-right font-black text-cyan-200">
                        {formatNumber(row.emisiones)} kg CO2e
                      </td>
                    </tr>
                  ))}
                  {visibleRows.length === 0 && (
                    <tr>
                      <td className="px-4 py-8 text-center text-slate-400" colSpan={9}>
                        No hay registros para los filtros seleccionados.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <Pagination
              currentPage={safeCurrentPage}
              itemLabel="registros"
              onPageChange={(p) => loadRows(p)}
              pageSize={rowsPerPage}
              totalItems={rowsCount}
            />
          </section>
        </>
      )}
    </main>
  );
}
