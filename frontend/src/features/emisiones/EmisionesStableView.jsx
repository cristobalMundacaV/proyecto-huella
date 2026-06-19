import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, BarChart3, Factory, Layers3, Search, Target } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import EmptyState from "@/shared/components/EmptyState";
import PlatformLoader from "@/shared/components/PlatformLoader";
import { getConstructoraEmisiones } from "@/shared/services/api";
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

function normalizeRows(input) {
  const rows = Array.isArray(input)
    ? input
    : input?.rows || input?.results || input?.datos || input?.registros || input?.registros_emision || [];

  return rows.map((row) => ({
    ...row,
    emisiones: Number(row?.emisiones ?? row?.emisiones_kg_co2e ?? row?.total_emisiones ?? row?.co2e ?? 0) || 0,
    categoria_visible: row?.categoria || row?.categoria_visible || "Otros",
    etapa_visible: row?.etapa_nombre || row?.etapa || "Sin etapa asociada",
    obra_visible: row?.obra_nombre || row?.codigo_obra || row?.obra_codigo || "Sin obra asociada",
    fuente_visible: row?.fuente_emision || row?.actividad || "Sin fuente",
  }));
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

function EmisionesStableView() {
  const { activeConstructora, activeConstructoraId } = useConstructoraActiva();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!activeConstructoraId) return;
      try {
        setLoading(true);
        setError("");
        const response = await getConstructoraEmisiones(activeConstructoraId);
        if (!cancelled) setData(response);
      } catch (requestError) {
        if (!cancelled) setError(requestError.response?.data?.error || "No se pudieron cargar las emisiones.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [activeConstructoraId]);

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

  const criticalCategory = byCategory[0]?.categoria || data?.kpis?.categoria_critica || "Sin datos";
  const criticalStage = byStage[0]?.etapa || data?.kpis?.unidad_critica || data?.kpis?.etapa_critica || "Sin datos";
  const criticalSource = bySource[0]?.fuente || data?.kpis?.fuente_critica || "Sin datos";
  const sourceShare = totalEmissions > 0 && bySource[0]?.emisiones ? (bySource[0].emisiones / totalEmissions) * 100 : 0;

  if (!activeConstructoraId) {
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
              Emisiones de {activeConstructora?.nombre || "la empresa"}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">
              Esta vista identifica las fuentes, etapas y categorías que explican la huella para priorizar acciones de gestión ambiental.
            </p>
          </div>

          <div className="rounded-3xl border border-emerald-200 bg-white/80 p-4 text-sm shadow-sm">
            <p className="font-black text-emerald-900">Lectura de huella</p>
            <p className="mt-1 max-w-sm leading-6 text-slate-600">
              {criticalSource !== "Sin datos"
                ? `La fuente ${criticalSource} concentra ${formatNumber(sourceShare, 1)}% del impacto medido. Revisa cantidad, factor y etapa antes de intervenir fuentes menores.`
                : "Carga registros válidos para identificar una fuente crítica y priorizar acciones de reducción."}
            </p>
          </div>
        </div>
      </section>

      {error && <p className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-bold text-rose-800">{error}</p>}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard icon={<Activity />} label="Emisiones totales" value={`${formatNumber(totalEmissions, 1)} kg CO₂e`} />
        <KpiCard icon={<Layers3 />} label="Categoría crítica" value={criticalCategory} />
        <KpiCard icon={<Factory />} label="Etapa prioritaria" value={criticalStage} />
        <KpiCard icon={<Target />} label="Fuente crítica" value={criticalSource} detail={`${formatNumber(sourceShare, 1)}% del total`} />
      </section>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <HorizontalChart title="Emisiones por etapa" data={byStage} nameKey="etapa" dataKey="emisiones" />
        <HorizontalChart title="Emisiones por fuente" data={bySource} nameKey="fuente" dataKey="emisiones" />
      </section>

      <section className="rounded-[30px] border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow-card)] ring-1 ring-white/70">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">Trazabilidad ambiental</p>
            <h2 className="text-2xl font-black text-[var(--text-main)]">Registros que explican la huella</h2>
            <p className="mt-1 text-sm text-[var(--text-muted)]">{formatNumber(filteredRows.length, 0)} registros encontrados.</p>
          </div>

          <label className="relative block w-full max-w-md">
            <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar fuente, etapa, obra o categoría"
              className="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-slate-900 outline-none transition focus:border-emerald-400/60"
            />
          </label>
        </div>

        {!rows.length ? (
          <EmptyState
            title="Aún no hay registros de emisión."
            description="Carga datos de materiales, transporte, maquinaria, energía, agua o residuos para activar el análisis ambiental."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] table-fixed border-collapse text-sm">
              <thead>
                <tr className="border-b border-emerald-100 bg-emerald-50/70 text-xs font-black uppercase tracking-[0.14em] text-emerald-900">
                  <th className="px-3 py-3 text-left">Obra</th>
                  <th className="px-3 py-3 text-left">Etapa</th>
                  <th className="px-3 py-3 text-left">Categoría</th>
                  <th className="px-3 py-3 text-left">Fuente</th>
                  <th className="px-3 py-3 text-right">Emisiones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredRows.slice(0, 12).map((row, index) => (
                  <tr key={`${row.id || row.fuente_visible}-${index}`} className="bg-white/70 transition hover:bg-emerald-50/50">
                    <td className="px-3 py-3 font-bold text-slate-800">{row.obra_visible}</td>
                    <td className="px-3 py-3 text-slate-600">{row.etapa_visible}</td>
                    <td className="px-3 py-3 text-slate-600">{row.categoria_visible}</td>
                    <td className="px-3 py-3 text-slate-600">{row.fuente_visible}</td>
                    <td className="px-3 py-3 text-right font-black text-emerald-800">{formatNumber(row.emisiones, 1)} kg CO₂e</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {filteredRows.length > 12 && (
          <p className="mt-4 rounded-2xl bg-[var(--bg-surface)] p-3 text-center text-sm font-semibold text-[var(--text-muted)]">
            Mostrando los 12 registros más relevantes. La tabla completa se integrará en Gestión de Huella con filtros avanzados.
          </p>
        )}
      </section>
    </main>
  );
}

export default EmisionesStableView;
