import { useEffect, useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { getReporteEmisionesTiempo } from "../../../shared/services/api";

function formatNumber(value, decimals = 1) {
  const n = Number(value || 0);
  return n.toLocaleString("es-CL", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function KpiCard({ label, value, subtext, tone = "default" }) {
  const toneClass =
    tone === "danger"
      ? "border-rose-400/20 bg-rose-400/10 text-rose-100"
      : tone === "success"
      ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-100"
      : tone === "warning"
      ? "border-amber-400/20 bg-amber-400/10 text-amber-100"
      : "border-slate-700 bg-slate-900/60 text-slate-100";

  return (
    <div className={`rounded-2xl border p-5 ${toneClass}`}>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-3 text-2xl font-black">{value}</p>
      {subtext && <p className="mt-2 text-sm text-slate-400">{subtext}</p>}
    </div>
  );
}

export default function ReportesView({ activeEmpresaId, activeEmpresa }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [filters, setFilters] = useState({
    agrupacion: "mes",
    fecha_inicio: "",
    fecha_fin: "",
    unidad_id: "",
    categoria: "",
    actividad: "",
  });

  async function loadReport() {
    if (!activeEmpresaId) return;

    try {
      setLoading(true);
      setError("");
      const result = await getReporteEmisionesTiempo(activeEmpresaId, filters);
      setData(result);
    } catch (err) {
      console.error(err);
      setError("No se pudo cargar el reporte temporal.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeEmpresaId]);

  const kpis = data?.kpis || {};
  const serie = data?.serie_temporal || [];
  const categorias = data?.por_categoria || [];
  const rows = data?.rows || [];
  const insights = data?.insights || [];

    const tendenciaTone = useMemo(() => {
    const tendencia = String(kpis.tendencia || "").toLowerCase();

    if (tendencia === "al alza") return "danger";
    if (tendencia === "a la baja") return "success";
    if (tendencia === "estable") return "default";

    return "warning";
    }, [kpis.tendencia]);

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
    <main className="mx-auto max-w-7xl px-6 py-10 text-slate-100">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-bold uppercase tracking-wide text-emerald-300">
            Reporte temporal
          </p>
          <h1 className="text-4xl font-black">Reportes</h1>
          <p className="mt-2 text-slate-400">
            Evolución temporal de emisiones de la empresa activa.
          </p>
          <p className="mt-2 text-sm text-cyan-200">
            Empresa activa: {activeEmpresa?.nombre || activeEmpresaId}
          </p>
        </div>

        <button
          disabled
          className="rounded-xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-400"
        >
          Exportar reporte
        </button>
      </header>

      <section className="mt-8 rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-400">
              Fecha inicio
            </label>
            <input
              type="date"
              value={filters.fecha_inicio}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, fecha_inicio: e.target.value }))
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
              value={filters.fecha_fin}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, fecha_fin: e.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3"
            />
          </div>

          <div>
            <label className="text-xs uppercase tracking-wide text-slate-400">
              Agrupación
            </label>
            <select
              value={filters.agrupacion}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, agrupacion: e.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3"
            >
              <option value="dia">Día</option>
              <option value="mes">Mes</option>
              <option value="anio">Año</option>
            </select>
          </div>
        </div>

        <div className="mt-5 flex gap-3">
          <button
            onClick={loadReport}
            className="rounded-xl bg-emerald-500 px-5 py-3 text-sm font-black text-slate-950"
          >
            Aplicar filtros
          </button>

          <button
            onClick={() =>
              setFilters({
                agrupacion: "mes",
                fecha_inicio: "",
                fecha_fin: "",
                unidad_id: "",
                categoria: "",
                actividad: "",
              })
            }
            className="rounded-xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-300"
          >
            Limpiar
          </button>
        </div>
      </section>

      {loading && (
        <div className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          Cargando reporte...
        </div>
      )}

      {error && (
        <div className="mt-8 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-200">
          {error}
        </div>
      )}

      {data && (
        <>
          <section className="mt-8 grid gap-4 md:grid-cols-3">
            <KpiCard
              label="Emisiones del periodo"
              value={`${formatNumber(kpis.emisiones_totales_periodo)} kg CO2e`}
            />
            <KpiCard
              label="Tendencia"
              value={kpis.tendencia || "Sin datos"}
              subtext={`${formatNumber(kpis.variacion_periodo)}% vs periodo anterior`}
              tone={tendenciaTone}
            />
            <KpiCard
              label="Periodo crítico"
              value={kpis.periodo_mayor_emision || "Sin datos"}
              subtext={`${formatNumber(kpis.emisiones_periodo_mayor)} kg CO2e`}
              tone="warning"
            />
            <KpiCard
              label="Actividad crítica"
              value={kpis.actividad_critica_periodo || "Sin datos"}
            />
            <KpiCard
              label="Unidad crítica"
              value={kpis.unidad_critica_periodo || "Sin datos"}
            />
            <KpiCard
              label="Promedio por periodo"
              value={`${formatNumber(kpis.promedio_periodo)} kg CO2e`}
            />
          </section>

          <section className="mt-8 rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-6">
            <p className="text-sm font-bold uppercase text-cyan-300">
              Lectura ejecutiva del periodo
            </p>

            <div className="mt-4 space-y-2 text-slate-100">
              {insights.map((insight, index) => (
                <p key={index}>{insight}</p>
              ))}
            </div>
          </section>

          <section className="mt-8 grid gap-6 lg:grid-cols-2">
            <div className="rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
              <h2 className="text-xl font-black">Emisiones en el tiempo</h2>

              <div className="mt-6 h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={serie}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                    <XAxis dataKey="label" />
                    <YAxis />
                    <Tooltip />
                    <Area
                      type="monotone"
                      dataKey="emisiones"
                      strokeWidth={2}
                      fillOpacity={0.25}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
              <h2 className="text-xl font-black">Emisiones por categoría</h2>

              <div className="mt-6 h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={categorias}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                    <XAxis dataKey="categoria" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="emisiones" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <section className="mt-8 rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="text-xl font-black">Detalle temporal de emisiones</h2>
            <p className="mt-1 text-sm text-slate-400">
              {rows.length} registros encontrados.
            </p>

            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[1100px]">
                <thead>
                  <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-400">
                    <th className="px-4 py-3 text-left">Fecha</th>
                    <th className="px-4 py-3 text-left">Periodo</th>
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
                  {rows.map((row, index) => (
                    <tr
                      key={`${row.fecha}-${row.actividad}-${index}`}
                      className="border-b border-slate-800/70"
                    >
                      <td className="px-4 py-3">{row.fecha}</td>
                      <td className="px-4 py-3">{row.periodo}</td>
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
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </main>
  );
}