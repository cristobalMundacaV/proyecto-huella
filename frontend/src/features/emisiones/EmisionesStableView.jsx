import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Factory,
  Layers3,
  Leaf,
  Loader2,
  PackageCheck,
  Route,
  Search,
  Target,
  X,
} from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { createTraceableAction } from "@/features/intelligence/services/traceableActionsApi";
import EmptyState from "@/shared/components/EmptyState";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { getOrganizacionEmisiones } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

const tooltipContentStyle = {
  backgroundColor: "#FCFDFC",
  border: "1px solid #B7C6BD",
  borderRadius: "12px",
  color: "#1F2937",
  boxShadow: "0 12px 28px rgba(15, 23, 42, 0.12)",
};

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function todayPlus(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function normalizeRows(input) {
  const rows = Array.isArray(input)
    ? input
    : input?.rows || input?.results || input?.datos || input?.registros || input?.registros_emision || [];

  return rows.map((row) => {
    const metadata = row?.metadata && typeof row.metadata === "object" ? row.metadata : {};
    const loteVisible = metadata.lote || metadata.lote_id || row?.lote_forestal_id || row?.lote_id;

    return {
      ...row,
      metadata,
      emisiones: Number(row?.emisiones ?? row?.emisiones_kg_co2e ?? row?.total_emisiones ?? row?.co2e ?? 0) || 0,
      categoria_visible: row?.categoria || row?.categoria_visible || "Otros",
      etapa_visible: row?.etapa_nombre || row?.etapa || metadata.module || "Sin etapa asociada",
      obra_visible: loteVisible || row?.obra_nombre || row?.codigo_obra || row?.obra_codigo || "Sin obra asociada",
      fuente_visible: row?.fuente_emision || row?.actividad || "Sin fuente",
    };
  });
}

function groupBy(rows, key, labelKey = "name") {
  return Object.values(
    rows.reduce((accumulator, row) => {
      const label = row[key] || "Sin datos";
      const current = accumulator[label] || { [labelKey]: label, emisiones: 0, registros: 0 };
      current.emisiones += Number(row.emisiones || 0);
      current.registros += 1;
      accumulator[label] = current;
      return accumulator;
    }, {})
  ).sort((left, right) => right.emisiones - left.emisiones);
}

function categoryBucket(category) {
  const normalized = normalizeText(category);
  if (normalized.includes("material") || normalized.includes("materia")) return "materiales";
  if (normalized.includes("transporte") || normalized.includes("ruta")) return "transporte";
  if (normalized.includes("energia") || normalized.includes("combustible")) return "energia";
  if (normalized.includes("maquinaria") || normalized.includes("proceso") || normalized.includes("produccion")) return "procesos";
  if (normalized.includes("residuo") || normalized.includes("agua")) return "cierre";
  return "otros";
}

function rowLoteId(row = {}) {
  const metadata = row.metadata && typeof row.metadata === "object" ? row.metadata : {};
  return metadata.lote || metadata.lote_id || metadata.lote_forestal || row.lote_id || row.lote_forestal_id || "";
}

function rowObraCodigo(row = {}) {
  const metadata = row.metadata && typeof row.metadata === "object" ? row.metadata : {};
  return row.codigo_obra || row.obra_codigo || metadata.codigo_obra || metadata.obra_codigo || metadata.obra || "";
}

function buildLifecycleUnits(rows, totalEmissions) {
  const grouped = rows.reduce((accumulator, row) => {
    const key = row.obra_visible || "Sin unidad";
    const current = accumulator[key] || {
      unidad: key,
      emisiones: 0,
      registros: 0,
      materiales: 0,
      transporte: 0,
      energia: 0,
      procesos: 0,
      cierre: 0,
      otros: 0,
      fuentes: {},
      etapas: {},
      rows: [],
      loteId: "",
      obraCodigo: "",
      registroId: "",
    };

    const value = Number(row.emisiones || 0);
    const bucket = categoryBucket(row.categoria_visible);
    current.emisiones += value;
    current.registros += 1;
    current[bucket] += value;
    current.fuentes[row.fuente_visible] = (current.fuentes[row.fuente_visible] || 0) + value;
    current.etapas[row.etapa_visible] = (current.etapas[row.etapa_visible] || 0) + value;
    current.rows.push(row);
    if (!current.loteId) current.loteId = rowLoteId(row);
    if (!current.obraCodigo) current.obraCodigo = rowObraCodigo(row);
    if (!current.registroId && row.id) current.registroId = row.id;
    accumulator[key] = current;
    return accumulator;
  }, {});

  return Object.values(grouped)
    .map((unit) => {
      const topSource = Object.entries(unit.fuentes).sort((a, b) => b[1] - a[1])[0];
      const topStage = Object.entries(unit.etapas).sort((a, b) => b[1] - a[1])[0];
      const share = totalEmissions > 0 ? (unit.emisiones / totalEmissions) * 100 : 0;
      const coverage = [unit.materiales, unit.transporte, unit.energia, unit.procesos, unit.cierre].filter((value) => value > 0).length;

      return {
        ...unit,
        participacion: share,
        coberturaCiclo: coverage,
        fuenteCritica: topSource?.[0] || "Sin fuente",
        etapaCritica: topStage?.[0] || "Sin etapa",
      };
    })
    .sort((left, right) => right.emisiones - left.emisiones);
}

function sortedEntries(object = {}) {
  return Object.entries(object).sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0));
}

function KpiCard({ icon, label, value, detail }) {
  return (
    <article className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-card)] p-5 text-center shadow-[var(--shadow-card)] ring-1 ring-white/70">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-200 bg-emerald-50 text-emerald-700 shadow-sm">
        {icon}
      </div>
      <p className="mt-4 text-xs font-black uppercase tracking-[0.18em] text-[var(--text-muted)]">{label}</p>
      <div className="mt-3 flex min-h-[46px] items-center justify-center text-2xl font-black leading-tight text-[var(--text-main)]">
        {value}
      </div>
      {detail && <p className="mt-2 text-xs font-semibold text-[var(--text-muted)]">{detail}</p>}
    </article>
  );
}

function HorizontalChart({ data, dataKey, nameKey, title }) {
  const chartData = data.slice(0, 8);

  return (
    <section className="rounded-[30px] border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)] ring-1 ring-white/70">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Distribución</p>
          <h3 className="text-xl font-black text-[var(--text-main)]">{title}</h3>
        </div>
        <BarChart3 className="text-emerald-700" />
      </div>

      <div className="h-72">
        {chartData.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 14, left: 58, bottom: 8 }}>
              <XAxis type="number" tickFormatter={(value) => formatNumber(value, 0)} />
              <YAxis
                dataKey={nameKey}
                interval={0}
                type="category"
                width={170}
                tick={{ fontSize: 11, fontWeight: 700 }}
                tickFormatter={(value) => String(value || "").length > 28 ? `${String(value).slice(0, 28)}...` : value}
              />
              <Tooltip
                contentStyle={tooltipContentStyle}
                formatter={(value) => [`${formatNumber(value, 1)} kg CO₂e`, "Emisiones"]}
              />
              <Bar dataKey={dataKey} fill="#059669" radius={[0, 10, 10, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-slate-200 text-sm font-semibold text-[var(--text-muted)]">
            Sin datos suficientes para graficar.
          </div>
        )}
      </div>
    </section>
  );
}

function LifecycleOverview({ activePreset, lifecycleUnits, onSelectUnit }) {
  const topUnits = lifecycleUnits.slice(0, 4);
  const label = ["forestal", "aserradero"].includes(activePreset) ? "lote/producto" : "obra/unidad";

  return (
    <section className="rounded-[30px] border border-emerald-200 bg-emerald-50/60 p-5 shadow-[var(--shadow-card)] ring-1 ring-white/70">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-800">Lectura de ciclo completo</p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-main)]">
            Huella acumulada por {label}
          </h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
            Esta lectura cruza materiales, transporte, energía, procesos y cierre para detectar qué unidad explica la mayor parte del impacto medido.
          </p>
        </div>
        <div className="rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm font-black text-emerald-800">
          {formatNumber(lifecycleUnits.length, 0)} unidades comparadas
        </div>
      </div>

      {topUnits.length ? (
        <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-2">
          {topUnits.map((unit) => (
            <button
              key={unit.unidad}
              type="button"
              onClick={() => onSelectUnit(unit)}
              className="rounded-3xl border border-white/70 bg-white/85 p-5 text-left shadow-[0_14px_32px_rgba(15,23,42,0.05)] transition hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-[0_20px_44px_rgba(15,118,110,0.12)]"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-700">{label}</p>
                  <h3 className="mt-1 text-xl font-black text-[var(--text-main)]">{unit.unidad}</h3>
                  <p className="mt-1 text-sm text-slate-600">
                    {formatNumber(unit.registros, 0)} registros · {formatNumber(unit.participacion, 1)}% de la huella total
                  </p>
                </div>
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-right">
                  <p className="text-xs font-black uppercase tracking-wide text-emerald-700">Total</p>
                  <p className="text-lg font-black text-emerald-900">{formatNumber(unit.emisiones, 1)} kg</p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5">
                <CycleMetric icon={<PackageCheck size={16} />} label="Materiales" value={unit.materiales} />
                <CycleMetric icon={<Route size={16} />} label="Transporte" value={unit.transporte} />
                <CycleMetric icon={<Activity size={16} />} label="Energía" value={unit.energia} />
                <CycleMetric icon={<Factory size={16} />} label="Procesos" value={unit.procesos} />
                <CycleMetric icon={<Leaf size={16} />} label="Cierre" value={unit.cierre + unit.otros} />
              </div>

              <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700">
                Fuente crítica: <strong>{unit.fuenteCritica}</strong>. Etapa crítica: <strong>{unit.etapaCritica}</strong>. Cobertura de ciclo: <strong>{unit.coberturaCiclo}/5 bloques</strong>.
              </div>
              <p className="mt-3 text-xs font-black uppercase tracking-[0.16em] text-emerald-700">Ver detalle de ciclo completo</p>
            </button>
          ))}
        </div>
      ) : (
        <div className="mt-5 rounded-2xl border border-dashed border-emerald-200 bg-white/70 p-6 text-center text-sm font-semibold text-[var(--text-muted)]">
          Aún no hay datos suficientes para comparar ciclo completo por unidad.
        </div>
      )}
    </section>
  );
}

function CycleMetric({ icon, label, value }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-3 text-center">
      <div className="mx-auto flex h-8 w-8 items-center justify-center rounded-xl bg-white text-emerald-700">
        {icon}
      </div>
      <p className="mt-2 text-[10px] font-black uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-black text-slate-900">{formatNumber(value, 1)}</p>
    </div>
  );
}

function LifecycleDetailModal({ activePreset, actionStatus, onClose, onCreateAction, totalEmissions, unit }) {
  const label = ["forestal", "aserradero"].includes(activePreset) ? "lote/producto" : "obra/unidad";
  const rows = [...(unit.rows || [])].sort((left, right) => String(right.fecha || "").localeCompare(String(left.fecha || "")));
  const topSources = sortedEntries(unit.fuentes).slice(0, 5);
  const topStages = sortedEntries(unit.etapas).slice(0, 5);
  const share = totalEmissions > 0 ? (unit.emisiones / totalEmissions) * 100 : 0;
  const actionFocus = unit.transporte >= unit.materiales && unit.transporte >= unit.energia
    ? "Revisar rutas, distancia real, consolidación de viajes y consumo por kilómetro."
    : unit.materiales >= unit.energia
      ? "Revisar materiales críticos, proveedores y respaldo documental de compras."
      : "Revisar consumo energético, horarios de operación y equipos de mayor demanda.";

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/35 px-4 py-6 backdrop-blur-sm">
      <div className="relative max-h-[92vh] w-full max-w-6xl overflow-y-auto rounded-[32px] border border-emerald-100 bg-white p-5 shadow-[0_30px_90px_rgba(15,23,42,0.22)] sm:p-6">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-2xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm hover:bg-slate-50"
          aria-label="Cerrar detalle de ciclo completo"
        >
          <X size={18} />
        </button>

        <div className="mb-6 pr-12">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-emerald-700">Detalle de ciclo completo</p>
          <h2 className="mt-2 text-3xl font-black tracking-tight text-[var(--text-main)]">{unit.unidad}</h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-[var(--text-muted)]">
            Lectura del {label} desde sus registros ambientales: composición por bloque, focos críticos, timeline operacional y acciones sugeridas.
          </p>
        </div>

        <section className="grid grid-cols-1 gap-4 lg:grid-cols-4">
          <SummaryCard icon={<Leaf size={18} />} label="Huella total" value={`${formatNumber(unit.emisiones, 1)} kg`} detail={`${formatNumber(share, 1)}% del total`} />
          <SummaryCard icon={<BarChart3 size={18} />} label="Registros" value={formatNumber(unit.registros, 0)} detail="datos analizados" />
          <SummaryCard icon={<Target size={18} />} label="Fuente crítica" value={unit.fuenteCritica} detail={unit.etapaCritica} />
          <SummaryCard icon={<Layers3 size={18} />} label="Cobertura" value={`${unit.coberturaCiclo}/5`} detail="bloques del ciclo" />
        </section>

        <section className="mt-5 rounded-3xl border border-emerald-200 bg-emerald-50/70 p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-800">Acción sugerida</p>
              <h3 className="mt-1 text-xl font-black text-[var(--text-main)]">Prioriza el bloque dominante antes de optimizar detalles menores</h3>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">{actionFocus}</p>
              {actionStatus?.message ? (
                <p className={`mt-3 rounded-2xl border px-3 py-2 text-xs font-black ${actionStatus.type === "success" ? "border-emerald-200 bg-white text-emerald-800" : "border-rose-200 bg-rose-50 text-rose-700"}`}>
                  {actionStatus.message}
                </p>
              ) : null}
            </div>
            <div className="flex shrink-0 flex-col gap-2">
              <button
                type="button"
                onClick={() => onCreateAction(unit, actionFocus)}
                disabled={actionStatus?.loading}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[var(--primary)] px-5 py-3 text-sm font-black text-white shadow-[0_14px_30px_rgba(15,124,109,0.18)] hover:bg-[var(--primary-dark)] disabled:opacity-60"
              >
                {actionStatus?.loading ? <Loader2 className="animate-spin" size={17} /> : <CheckCircle2 size={17} />}
                Crear acción trazable
              </button>
              <AlertTriangle className="mx-auto text-emerald-700" size={28} />
            </div>
          </div>
        </section>

        <section className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-600">Composición del ciclo</p>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
              <CycleMetric icon={<PackageCheck size={16} />} label="Materiales" value={unit.materiales} />
              <CycleMetric icon={<Route size={16} />} label="Transporte" value={unit.transporte} />
              <CycleMetric icon={<Activity size={16} />} label="Energía" value={unit.energia} />
              <CycleMetric icon={<Factory size={16} />} label="Procesos" value={unit.procesos} />
              <CycleMetric icon={<Leaf size={16} />} label="Cierre" value={unit.cierre + unit.otros} />
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-5">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-600">Ranking crítico</p>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-1">
              <RankingList title="Fuentes" rows={topSources} />
              <RankingList title="Etapas" rows={topStages} />
            </div>
          </div>
        </section>

        <section className="mt-5 rounded-3xl border border-slate-200 bg-white p-5">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-600">Timeline operacional</p>
              <h3 className="text-xl font-black text-[var(--text-main)]">Últimos registros que explican esta huella</h3>
            </div>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-black text-slate-600">
              {formatNumber(rows.length, 0)} registros
            </span>
          </div>

          <div className="space-y-3">
            {rows.slice(0, 8).map((row, index) => (
              <div key={`${row.id || row.fuente_visible}-${index}`} className="grid gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4 sm:grid-cols-[140px_1fr_auto] sm:items-center">
                <p className="text-sm font-black text-slate-700">{row.fecha || "Sin fecha"}</p>
                <div>
                  <p className="font-black text-[var(--text-main)]">{row.fuente_visible}</p>
                  <p className="text-sm text-slate-600">{row.categoria_visible} · {row.etapa_visible}</p>
                </div>
                <p className="text-right text-sm font-black text-emerald-800">{formatNumber(row.emisiones, 1)} kg</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function SummaryCard({ detail, icon, label, value }) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-4 shadow-[0_12px_28px_rgba(15,23,42,0.05)]">
      <div className="flex items-center gap-2 text-emerald-700">
        {icon}
        <p className="text-xs font-black uppercase tracking-[0.14em]">{label}</p>
      </div>
      <p className="mt-2 line-clamp-2 text-xl font-black text-[var(--text-main)]">{value}</p>
      {detail ? <p className="mt-1 text-xs font-bold text-[var(--text-muted)]">{detail}</p> : null}
    </article>
  );
}

function RankingList({ rows, title }) {
  return (
    <div>
      <h4 className="text-sm font-black text-[var(--text-main)]">{title}</h4>
      <div className="mt-2 space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2 text-sm">
            <span className="font-bold text-slate-700">{label}</span>
            <span className="font-black text-emerald-800">{formatNumber(value, 1)} kg</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function EmisionesStableView({ onSetActiveView }) {
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [selectedLifecycleUnit, setSelectedLifecycleUnit] = useState(null);
  const [actionStatus, setActionStatus] = useState({ loading: false, message: "", type: "" });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!activeOrganizacionId) return;
      try {
        setLoading(true);
        setError("");
        const response = await getOrganizacionEmisiones(activeOrganizacionId);
        if (!cancelled) setData(response);
      } catch (requestError) {
        if (!cancelled) setError(requestError.response?.data?.error || "No se pudieron cargar las emisiones.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    setSelectedLifecycleUnit(null);
    setActionStatus({ loading: false, message: "", type: "" });
    load();

    return () => {
      cancelled = true;
    };
  }, [activeOrganizacionId]);

  const rows = useMemo(() => normalizeRows(data), [data]);
  const filteredRows = useMemo(() => {
    const query = normalizeText(search);
    if (!query) return rows;
    return rows.filter((row) => normalizeText([
      row.fuente_visible,
      row.categoria_visible,
      row.etapa_visible,
      row.obra_visible,
      row.unidad,
    ].join(" ")).includes(query));
  }, [rows, search]);

  const totalEmissions = Number(data?.kpis?.emisiones_totales ?? data?.total_emisiones ?? rows.reduce((sum, row) => sum + row.emisiones, 0));
  const byCategory = useMemo(() => groupBy(rows, "categoria_visible", "categoria"), [rows]);
  const byStage = useMemo(() => groupBy(rows, "etapa_visible", "etapa"), [rows]);
  const bySource = useMemo(() => groupBy(rows, "fuente_visible", "fuente"), [rows]);
  const lifecycleUnits = useMemo(() => buildLifecycleUnits(rows, totalEmissions), [rows, totalEmissions]);

  const criticalCategory = byCategory[0]?.categoria || data?.kpis?.categoria_critica || "Sin datos";
  const criticalStage = byStage[0]?.etapa || data?.kpis?.unidad_critica || data?.kpis?.etapa_critica || "Sin datos";
  const criticalSource = bySource[0]?.fuente || data?.kpis?.fuente_critica || "Sin datos";
  const sourceShare = totalEmissions > 0 && bySource[0]?.emisiones ? (bySource[0].emisiones / totalEmissions) * 100 : 0;

  async function handleCreateLifecycleAction(unit, actionFocus) {
    if (!activeOrganizacionId || !unit) return;
    try {
      setActionStatus({ loading: true, message: "", type: "" });
      const payload = {
        title: `Reducir huella crítica en ${unit.unidad}`,
        description: actionFocus,
        responsible: "Equipo ambiental",
        dueDate: todayPlus(14),
        status: "pendiente",
        source: "Gestión de huella · Ciclo completo",
        evidence: "Registro operativo, respaldo documental y evidencia asociada al foco crítico.",
        trackingKpi: `kg CO₂e en ${unit.fuenteCritica}`,
        sourceCardId: "lifecycle_detail",
        obraCodigo: unit.obraCodigo || "",
        loteId: unit.loteId || "",
        registroId: unit.registroId || "",
        metadata: {
          origin: "emisiones_lifecycle_detail",
          unidad: unit.unidad,
          fuente_critica: unit.fuenteCritica,
          etapa_critica: unit.etapaCritica,
          emisiones_kg_co2e: unit.emisiones,
          participacion_pct: unit.participacion,
          cobertura_ciclo: unit.coberturaCiclo,
        },
      };
      await createTraceableAction(activeOrganizacionId, payload);
      setActionStatus({ loading: false, message: "Acción creada y enviada al tablero de Acciones.", type: "success" });
    } catch (requestError) {
      setActionStatus({
        loading: false,
        message: requestError?.response?.data?.error || "No se pudo crear la acción trazable.",
        type: "error",
      });
    }
  }

  if (!activeOrganizacionId) {
    return (
      <EmptyState
        title="Selecciona una empresa para revisar su huella."
        description="La gestión de emisiones trabaja sobre una empresa activa para identificar focos críticos, etapas prioritarias y acciones de reducción."
      />
    );
  }

  if (loading && !data) {
    return <PlatformLoader title="Cargando emisiones" description="Estamos preparando huella, focos críticos y recomendaciones ambientales." />;
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6">
      <section className="overflow-hidden rounded-[32px] border border-emerald-300/40 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.20),transparent_32%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] p-6 shadow-[0_28px_80px_rgba(15,118,110,0.14)] ring-1 ring-white/70">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.24em] text-emerald-700">Gestión de huella</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
              Emisiones de {activeOrganizacion?.nombre || "la empresa"}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
              Esta vista identifica fuentes, etapas, categorías y unidades completas para priorizar acciones de gestión ambiental.
            </p>
          </div>

          <div className="rounded-3xl border border-emerald-200 bg-white/80 p-4 text-sm shadow-sm">
            <p className="font-black text-emerald-900">Lectura de huella</p>
            <p className="mt-1 max-w-sm leading-6 text-slate-600">
              {criticalSource !== "Sin datos"
                ? `La fuente ${criticalSource} explica ${formatNumber(sourceShare, 1)}% de la huella registrada.`
                : "Aún no hay suficientes datos para determinar una fuente crítica."}
            </p>
            {onSetActiveView ? (
              <button type="button" onClick={() => onSetActiveView("acciones")} className="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-xs font-black text-emerald-800 hover:bg-emerald-100">
                Ver acciones trazables
              </button>
            ) : null}
          </div>
        </div>
      </section>

      {error && (
        <div className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-sm font-bold text-rose-800">
          {error}
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard icon={<Leaf size={22} />} label="Huella total" value={`${formatNumber(totalEmissions, 1)} kg`} detail="CO₂e registrado" />
        <KpiCard icon={<Target size={22} />} label="Fuente crítica" value={criticalSource} detail={`${formatNumber(sourceShare, 1)}% del total`} />
        <KpiCard icon={<Layers3 size={22} />} label="Etapa prioritaria" value={criticalStage} detail="unidad de mayor impacto" />
        <KpiCard icon={<Activity size={22} />} label="Categoría crítica" value={criticalCategory} detail="bloque dominante" />
      </section>

      <LifecycleOverview
        activePreset={activeOrganizacion?.preset}
        lifecycleUnits={lifecycleUnits}
        onSelectUnit={(unit) => {
          setActionStatus({ loading: false, message: "", type: "" });
          setSelectedLifecycleUnit(unit);
        }}
      />

      <section className="rounded-[30px] border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)] ring-1 ring-white/70">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Explorador</p>
            <h2 className="text-2xl font-black text-[var(--text-main)]">Registros de huella</h2>
            <p className="mt-1 text-sm text-[var(--text-muted)]">Filtra por fuente, categoría, etapa o unidad para revisar el detalle operacional.</p>
          </div>
          <label className="relative block w-full max-w-md">
            <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar fuente, etapa, categoría o unidad"
              className="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-slate-900 outline-none transition focus:border-emerald-400/60"
            />
          </label>
        </div>

        <div className="mt-5 overflow-hidden rounded-2xl border border-[var(--border)]">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-black uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Fecha</th>
                <th className="px-4 py-3">Unidad</th>
                <th className="px-4 py-3">Fuente</th>
                <th className="px-4 py-3">Categoría</th>
                <th className="px-4 py-3 text-right">Emisiones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filteredRows.slice(0, 12).map((row, index) => (
                <tr key={`${row.id || row.fuente_visible}-${index}`} className="hover:bg-emerald-50/40">
                  <td className="px-4 py-3 font-bold text-slate-700">{row.fecha || "Sin fecha"}</td>
                  <td className="px-4 py-3 text-slate-600">{row.obra_visible}</td>
                  <td className="px-4 py-3 font-bold text-[var(--text-main)]">{row.fuente_visible}</td>
                  <td className="px-4 py-3 text-slate-600">{row.categoria_visible}</td>
                  <td className="px-4 py-3 text-right font-black text-emerald-800">{formatNumber(row.emisiones, 1)} kg</td>
                </tr>
              ))}
              {!filteredRows.length && (
                <tr>
                  <td colSpan="5" className="px-4 py-8 text-center text-sm font-semibold text-[var(--text-muted)]">
                    No hay registros que coincidan con la búsqueda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <HorizontalChart data={bySource} dataKey="emisiones" nameKey="fuente" title="Fuentes principales" />
        <HorizontalChart data={byCategory} dataKey="emisiones" nameKey="categoria" title="Categorías" />
        <HorizontalChart data={byStage} dataKey="emisiones" nameKey="etapa" title="Etapas / módulos" />
      </div>

      {selectedLifecycleUnit ? (
        <LifecycleDetailModal
          activePreset={activeOrganizacion?.preset}
          actionStatus={actionStatus}
          onClose={() => setSelectedLifecycleUnit(null)}
          onCreateAction={handleCreateLifecycleAction}
          totalEmissions={totalEmissions}
          unit={selectedLifecycleUnit}
        />
      ) : null}
    </main>
  );
}

export default EmisionesStableView;
