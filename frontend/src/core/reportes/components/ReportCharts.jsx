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

import { formatReportNumber } from "@/presets/shared/reportConfig";

function ReportCharts({ report, reportConfig }) {
  const categoryData = report.categorias.map((item) => ({
    ...item,
    name: reportConfig.categoryConfig?.[item.label]?.label || item.label,
    color: reportConfig.categoryConfig?.[item.label]?.color || "#475569",
  }));

  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <ChartCard title="Serie temporal" description="Evolución de emisiones según la agrupación seleccionada.">
        {report.serie.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={report.serie} margin={{ top: 12, right: 16, left: 0, bottom: 4 }}>
              <defs>
                <linearGradient id="reportAreaGradientAdaptive" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0891B2" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#0891B2" stopOpacity={0.04} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="4 4" stroke="#B8C6BE" opacity={0.85} />
              <XAxis dataKey="label" tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }} />
              <YAxis tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }} tickFormatter={(value) => formatReportNumber(value)} width={72} />
              <Tooltip content={<ReportTooltip labelPrefix="Periodo" />} />
              <Area type="monotone" dataKey="emisiones" stroke="#0891B2" strokeWidth={2.5} fill="url(#reportAreaGradientAdaptive)" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChart text="Se necesita más de un periodo para visualizar tendencia temporal." />
        )}
      </ChartCard>

      <ChartCard title="Distribución por categoría" description="Comparativo por categoría del preset activo.">
        {categoryData.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={categoryData} margin={{ top: 10, right: 10, left: 0, bottom: 24 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="#B8C6BE" opacity={0.85} />
              <XAxis dataKey="name" tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }} interval={0} angle={-22} textAnchor="end" height={62} />
              <YAxis tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }} tickFormatter={(value) => formatReportNumber(value)} width={72} />
              <Tooltip cursor={false} content={<ReportTooltip labelPrefix="Categoría" />} />
              <Bar dataKey="emisiones" radius={[8, 8, 0, 0]}>
                {categoryData.map((item) => <Cell key={item.key} fill={item.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChart text="No hay categorías con emisiones en este periodo." />
        )}
      </ChartCard>

      <ChartCard title="Distribución por módulo operativo" description="Agrupación por etapa, módulo o proceso según preset.">
        {report.modules.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={report.modules.slice(0, 8)} layout="vertical" margin={{ top: 8, right: 16, left: 28, bottom: 8 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="#B8C6BE" opacity={0.85} />
              <XAxis type="number" tick={{ fill: "#475569", fontSize: 12, fontWeight: 600 }} tickFormatter={(value) => formatReportNumber(value)} />
              <YAxis type="category" dataKey="label" tick={{ fill: "#475569", fontSize: 11, fontWeight: 700 }} width={120} />
              <Tooltip cursor={false} content={<ReportTooltip labelPrefix="Módulo" />} />
              <Bar dataKey="emisiones" radius={[0, 8, 8, 0]} fill="#0F766E" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChart text="No hay módulos operativos para visualizar." />
        )}
      </ChartCard>

      <ChartCard title="Fuentes críticas" description="">
        {report.fuentes.length ? (
          <div className="space-y-3">
            {report.fuentes.slice(0, 4).map((item) => (
              <div key={item.label} className="rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-bold text-[var(--text-main)]">{item.label}</p>
                  <p className="font-black text-sky-700">{formatReportNumber(item.emisiones)} kg CO2e</p>
                </div>
                <p className="mt-1 text-xs font-semibold text-[var(--text-muted)]">{item.registros} registros</p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyChart text="No hay fuentes críticas en este periodo." />
        )}
      </ChartCard>
    </section>
  );
}

function ChartCard({ children, description, title }) {
  return (
    <div className="rounded-3xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[0_18px_45px_var(--shadow)]">
      <h2 className="text-xl font-black text-[var(--text-main)]">{title}</h2>
      {description ? <p className="mt-1 text-sm text-[var(--text-muted)]">{description}</p> : null}
      <div className="mt-6 h-[320px] min-h-[320px]">{children}</div>
    </div>
  );
}

function EmptyChart({ text }) {
  return (
    <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-[var(--bg-surface)] px-6 text-center text-sm text-[var(--text-muted)]">
      {text}
    </div>
  );
}

function ReportTooltip({ active, payload, label, labelPrefix }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="max-w-[280px] rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--text-muted)]">{labelPrefix}</p>
      <p className="text-sm font-semibold text-[var(--text-main)]">{label || "Sin etiqueta"}</p>
      <p className="mt-1 text-sm font-black text-[#075985]">{formatReportNumber(payload[0]?.value)} kg CO2e</p>
    </div>
  );
}

export default ReportCharts;
