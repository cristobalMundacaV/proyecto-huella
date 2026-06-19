import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, BarChart3, Database, Factory, Leaf, Radar } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import RealtimeIotMonitoring from "@/features/dashboard/components/RealtimeIotMonitoring";
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
import { DEFAULT_PRESET_KEY, getActivePreset } from "@/presets/registry";

const DASHBOARD_REFRESH_INTERVAL_MS = 12000;

const tooltipContentStyle = {
  backgroundColor: "#FCFDFC",
  border: "1px solid #B7C6BD",
  borderRadius: "12px",
  color: "#1F2937",
  boxShadow: "0 12px 28px rgba(15, 23, 42, 0.12)",
};

const normalizeRows = (input) => {
  const rows = Array.isArray(input)
    ? input
    : input?.results || input?.data || input?.datos || input?.registros || input?.registros_emision || [];

  return rows.map((row) => ({
    ...row,
    metadata: row?.metadata && typeof row.metadata === "object" ? row.metadata : {},
    emisiones: Number(row?.emisiones ?? row?.emisiones_kg_co2e ?? row?.total_emisiones ?? row?.co2e ?? 0) || 0,
    categoria_visible: row?.categoria || row?.categoria_visible || row?.metadata?.aserradero_category || "Otros",
    etapa_visible: row?.etapa_nombre || row?.etapa || row?.metadata?.module || "Sin etapa",
    obra_visible: row?.obra_nombre || row?.codigo_obra || row?.obra_codigo || row?.metadata?.lote || "Sin unidad",
    fuente_visible: row?.fuente_emision || row?.actividad || "Sin fuente",
  }));
};

function groupBy(rows, key, outputKey = "name") {
  return Object.values(
    rows.reduce((accumulator, row) => {
      const label = row[key] || "Sin datos";
      const current = accumulator[label] || { [outputKey]: label, emisiones: 0, registros: 0 };
      current.emisiones += Number(row.emisiones || 0);
      current.registros += 1;
      accumulator[label] = current;
      return accumulator;
    }, {})
  ).sort((left, right) => right.emisiones - left.emisiones);
}

function DashboardChart({ data, nameKey, title }) {
  const chartData = data.slice(0, 7);

  return (
    <section className="rounded-[30px] border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)] ring-1 ring-white/70">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Lectura ambiental</p>
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
              <Bar dataKey="emisiones" fill="#0F7C6D" radius={[0, 10, 10, 0]} />
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

function DashboardPage({ onStatusChange }) {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const activePreset = getActivePreset(activeConstructora?.preset || DEFAULT_PRESET_KEY);
  const [data, setData] = useState(null);
  const [ambientRecords, setAmbientRecords] = useState([]);
  const [emissionKpis, setEmissionKpis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refreshDashboard = useCallback(async (showLoading = false) => {
    if (!activeConstructoraId) {
      setData(null);
      setAmbientRecords([]);
      setEmissionKpis(null);
      onStatusChange?.(null);
      setLoading(false);
      return;
    }

    if (showLoading) setLoading(true);
    setError("");

    const [dashboardResult, estadoResult, emissionsResult, recordsResult] = await Promise.allSettled([
      getConstructoraDashboard(activeConstructoraId, { light: "1" }),
      getConstructoraEstado(activeConstructoraId),
      getConstructoraEmisiones(activeConstructoraId, { page: 1, page_size: 1 }),
      getEmpresaRegistrosAmbientales(activeConstructoraId),
    ]);

    const normalizedRecords = recordsResult.status === "fulfilled" ? normalizeRows(recordsResult.value) : [];

    if (dashboardResult.status === "fulfilled") setData(dashboardResult.value);
    if (emissionsResult.status === "fulfilled") setEmissionKpis(emissionsResult.value?.kpis || null);
    if (recordsResult.status === "fulfilled") setAmbientRecords(normalizedRecords);

    if (estadoResult.status === "fulfilled") {
      onStatusChange?.({
        ...estadoResult.value,
        registros_emision: normalizedRecords.length || estadoResult.value?.registros_emision || 0,
      });
    } else if (normalizedRecords.length) {
      onStatusChange?.({ registros_emision: normalizedRecords.length });
    }

    if (dashboardResult.status === "rejected" && recordsResult.status === "rejected") {
      throw dashboardResult.reason || recordsResult.reason;
    }

    if (showLoading) setLoading(false);
  }, [activeConstructoraId, onStatusChange]);

  useEffect(() => {
    let cancelled = false;
    let intervalId;

    async function load() {
      try {
        await refreshDashboard(true);
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError.response?.data?.error || "No se pudo cargar el tablero de la empresa.");
          setLoading(false);
        }
      }

      intervalId = window.setInterval(() => {
        refreshDashboard(false).catch(() => undefined);
      }, DASHBOARD_REFRESH_INTERVAL_MS);
    }

    load();

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [refreshDashboard]);

  const rows = useMemo(() => {
    const dashboardRows = normalizeRows(data?.datos || []);
    const scopedRows = activePreset.key === DEFAULT_PRESET_KEY
      ? dashboardRows
      : ambientRecords.filter((row) => row.metadata?.preset === activePreset.key || !row.metadata?.preset);
    return scopedRows.length ? scopedRows : dashboardRows;
  }, [activePreset.key, ambientRecords, data]);

  const totalEmissions = Number(emissionKpis?.emisiones_totales ?? data?.total_emisiones ?? rows.reduce((sum, row) => sum + row.emisiones, 0));
  const byCategory = useMemo(() => groupBy(rows, "categoria_visible", "categoria"), [rows]);
  const byStage = useMemo(() => groupBy(rows, "etapa_visible", "etapa"), [rows]);
  const bySource = useMemo(() => groupBy(rows, "fuente_visible", "fuente"), [rows]);
  const byUnit = useMemo(() => groupBy(rows, "obra_visible", "unidad"), [rows]);

  const criticalCategory = byCategory[0]?.categoria || data?.categoria_critica || "Sin datos";
  const criticalStage = byStage[0]?.etapa || data?.etapa_critica || data?.unidad_critica || "Sin datos";
  const criticalSource = bySource[0]?.fuente || data?.fuente_critica || "Sin datos";
  const criticalUnit = byUnit[0]?.unidad || data?.obra_critica || "Sin datos";
  const topShare = totalEmissions > 0 && bySource[0]?.emisiones ? (bySource[0].emisiones / totalEmissions) * 100 : 0;

  if (loading && !data && !ambientRecords.length) {
    return (
      <PlatformLoader
        title="Cargando tablero de empresa"
        description="Estamos preparando indicadores, focos críticos y recomendaciones ambientales."
      />
    );
  }

  if (error && !rows.length) {
    return <div className="rounded-3xl border border-rose-200 bg-rose-50 p-6 text-sm font-semibold text-rose-800">{error}</div>;
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6 sm:space-y-8">
      <section className="overflow-hidden rounded-[32px] border border-emerald-300/40 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.18),transparent_32%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] p-6 shadow-[0_28px_80px_rgba(15,118,110,0.14)] ring-1 ring-white/70">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="rounded-3xl border border-emerald-200 bg-white/80 p-4 text-emerald-800 shadow-sm">
              <Leaf size={28} />
            </div>
            <div>
              <p className="text-xs font-black uppercase tracking-[0.24em] text-emerald-700">Panel ambiental</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight text-[var(--text-main)] sm:text-4xl">
                Carbono Zero
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
                Convierte datos reales de {activePreset.unitPluralLabel.toLowerCase()} en medición, trazabilidad y decisiones para reducir emisiones durante la operación.
              </p>
            </div>
          </div>

          <div className="rounded-3xl border border-emerald-200 bg-white/80 p-4 text-sm shadow-sm">
            <p className="font-black text-emerald-900">Recomendación principal</p>
            <p className="mt-1 max-w-sm leading-6 text-slate-600">
              Prioriza {criticalSource} en {criticalStage}. Es el foco más relevante para transformar la medición en acción ambiental.
            </p>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <KpiCard icon={<Activity />} title="Emisiones totales" value={`${formatNumber(totalEmissions, 1)} kg CO₂e`} />
        <KpiCard icon={<Factory />} title={`${activePreset.unitLabel} crítica`} value={criticalUnit} />
        <KpiCard icon={<AlertTriangle />} title="Categoría crítica" value={criticalCategory} />
        <KpiCard icon={<Database />} title="Fuente crítica" value={criticalSource} />
        <KpiCard icon={<Radar />} title="Concentración principal" value={`${formatNumber(topShare, 1)}%`} />
        <KpiCard icon={<BarChart3 />} title="Registros analizados" value={formatNumber(rows.length, 0)} />
      </section>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <DashboardChart title="Emisiones por etapa" data={byStage} nameKey="etapa" />
        <DashboardChart title="Emisiones por fuente" data={bySource} nameKey="fuente" />
      </section>

      <RealtimeIotMonitoring activeConstructoraId={activeConstructoraId} />
    </main>
  );
}

export default DashboardPage;
