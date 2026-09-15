import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, CalendarDays, FileCheck2, Factory, Gauge, Leaf, TrendingDown, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { CZMetricCard, CZSection, EmptyState } from "@/shared/ui";
import { formatNumber, formatPercent } from "@/shared/utils/formatters";
import { REPORT_CATEGORY_COLORS } from "../utils/reportAdapters";

const emission = (value) => value === null || value === undefined ? "Sin datos" : `${formatNumber(value)} kg CO2e`;
const trend = (variation) => variation === null ? { label: "Sin comparación", tone: "text-slate-700", Icon: Gauge } : variation > 0 ? { label: "Al alza", tone: "text-rose-700", Icon: TrendingUp } : variation < 0 ? { label: "A la baja", tone: "text-emerald-700", Icon: TrendingDown } : { label: "Sin variación", tone: "text-slate-700", Icon: Gauge };

const TOOLTIP_STYLE = {
  contentStyle: { borderRadius: 12, border: "1px solid var(--border-default)", boxShadow: "var(--shadow-card-v1)", fontSize: 12, fontWeight: 700, padding: "8px 12px" },
  labelStyle: { fontWeight: 900, marginBottom: 4, color: "var(--text-primary)" },
  itemStyle: { padding: 0 },
};

export function ExecutiveSummary({ report, workName }) {
  const behavior = trend(report.variation);
  const title = !report.records ? "Aún no existe una lectura de emisiones para este período" : report.variation === null ? "La obra ya cuenta con una base ambiental consolidada" : report.variation > 0 ? "Las emisiones recientes aumentaron y requieren atención" : report.variation < 0 ? "Las emisiones recientes disminuyeron" : "Las emisiones recientes se mantienen estables";
  return <CZSection className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
    <div className="flex flex-col"><p className="text-xs font-black uppercase tracking-[0.15em] text-emerald-700">Resumen ejecutivo</p><div className="flex flex-1 flex-col justify-center"><h2 className="mt-2 max-w-3xl text-2xl font-black leading-tight sm:text-3xl">{title}</h2><p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">{report.records ? `${workName} registra ${emission(report.total)} en ${report.records} resultados ambientales trazables dentro del período seleccionado.` : `No hay resultados en kg CO2e disponibles para ${workName} bajo el filtro actual. La ausencia de datos no se interpreta como cero.`}</p>
      <ul className="mt-5 space-y-2 text-sm text-[var(--text-secondary)]">
        <li className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />{report.dominantSource ? `La fuente prioritaria es ${report.dominantSource.name}, con ${formatPercent(report.dominantSource.percentage)} del total.` : "No hay una fuente prioritaria determinable."}</li>
        <li className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-500" />{report.dominantCategory ? `${report.dominantCategory.name} concentra la mayor contribución ambiental del período.` : "No existe distribución por categoría disponible."}</li>
        <li className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500" />{report.excludedRecords ? `${report.excludedRecords} resultados con otras unidades quedaron fuera de la suma para no mezclar magnitudes.` : "Todos los resultados incluidos utilizan una unidad compatible con CO2e."}</li>
      </ul></div>
    </div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
      <SummarySignal icon={behavior.Icon} label="Comportamiento reciente" value={behavior.label} tone={behavior.tone} />
      <SummarySignal icon={AlertTriangle} label="Fuente prioritaria" value={report.dominantSource?.name || "Sin datos"} tone="text-blue-700" />
      <SummarySignal icon={Factory} label="Etapa prioritaria" value="Sin etapa informada" tone="text-slate-700" />
      <SummarySignal icon={CalendarDays} label="Período con mayor emisión" value={report.peak?.label || "Sin datos"} tone="text-orange-700" />
    </div>
  </CZSection>;
}

function SummarySignal({ icon: Icon, label, value, tone }) {
  return <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] px-4 py-3">
    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white shadow-sm"><Icon aria-hidden="true" className={tone} size={16} /></span>
    <div className="min-w-0"><p className="text-[10px] font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">{label}</p><p className={`mt-1 truncate font-black ${tone}`}>{value}</p></div>
  </div>;
}

export function ReportKpis({ report }) {
  const behavior = trend(report.variation);
  const totalConsidered = report.records + report.excludedRecords;
  const coverage = totalConsidered > 0 ? (report.records / totalConsidered) * 100 : null;
  const rows = [
    { icon: Leaf, label: "Emisiones del período", value: report.records ? report.total : null, unit: report.records ? "kg CO2e" : undefined, tone: "rose", supportingText: report.records ? `${report.records} resultados trazables` : "Sin lectura disponible" },
    { icon: behavior.Icon, label: "Variación reciente", value: report.variation === null ? null : Math.abs(report.variation), unit: report.variation === null ? undefined : "%", tone: report.variation > 0 ? "rose" : report.variation < 0 ? "emerald" : "neutral", supportingText: report.variation === null ? "Se requieren dos períodos" : `${behavior.label} vs. mes anterior` },
    { icon: Gauge, label: "Emisión promedio", value: report.records ? report.average : null, unit: report.records ? "kg CO2e" : undefined, tone: "neutral", supportingText: "Promedio por período agrupado" },
    { icon: AlertTriangle, label: "Categoría dominante", value: report.dominantCategory?.name || null, tone: "amber", supportingText: report.dominantCategory ? `${formatPercent(report.dominantCategory.percentage)} del período` : "Sin distribución disponible" },
    { icon: Factory, label: "Resultados trazables", value: report.records, tone: "blue", supportingText: report.excludedRecords ? `${report.excludedRecords} excluidos por unidad incompatible` : "Todos con unidad compatible" },
    { icon: CalendarDays, label: "Cobertura del set", value: coverage, unit: coverage === null ? undefined : "%", tone: "emerald", supportingText: "Resultados trazables sobre el total evaluado", progress: coverage },
  ];
  return <section aria-label="Indicadores del reporte" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{rows.map((row) => <CZMetricCard key={row.label} {...row} />)}</section>;
}

export function CategoryGrid({ categories, total }) {
  const withValue = [...categories].filter((row) => row.value > 0).sort((a, b) => b.value - a.value);
  const withoutValue = categories.filter((row) => row.value <= 0);
  return <CZSection>
    <Heading description="Las categorías se ordenan por contribución sin mezclar unidades ambientales incompatibles." eyebrow="Estado de emisiones" title="Distribución ambiental por categoría" />
    {withValue.length > 0
      ? <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{withValue.map((row) => <article className="relative overflow-hidden rounded-[var(--radius-card)] border border-[var(--border-default)] bg-white p-[var(--space-4)] text-center shadow-[var(--shadow-card-v1)]" key={row.name}><span className="absolute inset-x-0 top-0 h-1" style={{ background: REPORT_CATEGORY_COLORS[row.name] }} /><p className="text-[10px] font-black uppercase tracking-[0.13em] text-[var(--text-muted)]">{row.name}</p><p className="mt-4 text-xl font-black" style={{ color: REPORT_CATEGORY_COLORS[row.name] }}>{emission(row.value)}</p><p className="mt-2 text-xs font-bold text-[var(--text-secondary)]">{total > 0 ? formatPercent(row.percentage) : "0%"} del período</p></article>)}</div>
      : <EmptyState className="mt-4" description="Ninguna categoría concentra emisiones en el período seleccionado." title="Sin categorías con aporte" />}
    {withoutValue.length > 0 && <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-[var(--border-subtle)] pt-4"><span className="text-[10px] font-black uppercase tracking-[0.13em] text-[var(--text-muted)]">Sin aporte en el período:</span>{withoutValue.map((row) => <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] px-2.5 py-1 text-xs font-bold text-[var(--text-muted)]" key={row.name}><span aria-hidden="true" className="h-1.5 w-1.5 rounded-full" style={{ background: REPORT_CATEGORY_COLORS[row.name] }} />{row.name}</span>)}</div>}
  </CZSection>;
}

export function SourceParticipation({ report }) {
  const pie = report.sources.filter((row) => row.value > 0);
  return <section className="rounded-[var(--radius-panel)] border border-sky-100 bg-gradient-to-br from-white via-sky-50/40 to-white p-[var(--space-6)] shadow-[var(--shadow-card-v1)]"><Heading badge={report.dominantSource ? `Fuente dominante: ${report.dominantSource.name}` : undefined} description="El tamaño de cada segmento representa su contribución relativa dentro del período seleccionado." eyebrow="Lectura visual" title="Participación de emisiones por fuente" /><div className="mt-5 grid items-center gap-8 lg:grid-cols-[0.7fr_1.3fr]"><div className="relative h-72">{pie.length ? <ResponsiveContainer height="100%" width="100%"><PieChart><Pie data={pie} dataKey="value" innerRadius={72} nameKey="name" outerRadius={106} paddingAngle={1}>{pie.map((row) => <Cell fill={REPORT_CATEGORY_COLORS[row.category] || "#64748b"} key={row.name} />)}</Pie><Tooltip formatter={(value) => emission(value)} {...TOOLTIP_STYLE} /></PieChart></ResponsiveContainer> : <div className="flex h-full items-center justify-center text-sm text-[var(--text-muted)]">Sin distribución disponible</div>}<div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"><span className="text-[10px] font-black uppercase tracking-widest text-[var(--text-muted)]">Total</span><b className="mt-1 text-lg">{formatNumber(report.total)}</b><span className="text-xs text-[var(--text-muted)]">kg CO2e</span></div></div><div className="space-y-2.5">{report.sources.slice(0, 6).map((row) => <div className="rounded-[var(--radius-card)] border border-[var(--border-default)] bg-white p-4 shadow-[var(--shadow-flat)]" key={row.name}><div className="flex items-start justify-between gap-3"><div className="min-w-0"><b className="block truncate">{row.name}</b><p className="text-xs text-[var(--text-muted)]">{row.category}</p></div><div className="shrink-0 text-right"><b>{emission(row.value)}</b><p className="text-xs text-[var(--text-muted)]">{formatPercent(row.percentage)}</p></div></div><Progress color={REPORT_CATEGORY_COLORS[row.category]} value={row.percentage} /></div>)}</div></div></section>;
}

export function CriticalSources({ report }) {
  const top = report.sources.slice(0, 5);
  return <CZSection id="top-fuentes">
    <Heading badge={`${Math.min(5, report.sources.length)} focos`} description="Estos focos concentran la mayor contribución y orientan las primeras decisiones de reducción." eyebrow="Fuentes críticas" title="Top 5 fuentes de mayor impacto" />
    <div className="mt-4 space-y-2.5">
      {top.map((row, index) => {
        const color = REPORT_CATEGORY_COLORS[row.category] || "#64748b";
        const isTop = index === 0;
        return <article className={`flex items-center gap-4 rounded-[var(--radius-card)] border p-4 transition ${isTop ? "shadow-[var(--shadow-card-v1)]" : "border-[var(--border-default)] bg-white"}`} key={row.name} style={isTop ? { borderColor: color, background: `${color}0d` } : undefined}>
          <span className={`flex shrink-0 items-center justify-center rounded-full font-black ${isTop ? "h-11 w-11 text-lg" : "h-9 w-9 text-sm"}`} style={{ background: `${color}1a`, border: `1px solid ${color}55`, color }}>#{index + 1}</span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <div className="min-w-0"><p className="text-[10px] font-black uppercase tracking-[0.13em] text-[var(--text-muted)]">{row.category}</p><h3 className={`truncate font-black ${isTop ? "text-lg" : "text-sm"}`} style={{ color }}>{row.name}</h3></div>
              <div className="shrink-0 text-right"><p className={`font-black ${isTop ? "text-lg" : "text-sm"}`}>{emission(row.value)}</p><p className="text-xs font-bold text-[var(--text-muted)]">{formatPercent(row.percentage)} del total</p></div>
            </div>
            <Progress color={color} value={row.percentage} />
          </div>
        </article>;
      })}
    </div>
  </CZSection>;
}

export function ReportCharts({ report }) {
  const categoryData = report.categories.filter((row) => row.value > 0);
  const dominantName = report.dominantCategory?.name;
  const sparseTimeline = report.timeline.length < 2;
  return <section className="grid gap-4 xl:grid-cols-2">
    <Chart description="Evolución mensual de los resultados filtrados." footnote={sparseTimeline ? "Aún no hay suficientes períodos para trazar una tendencia; se muestra el único dato disponible." : undefined} title="Emisiones en el tiempo">
      <ResponsiveContainer height="100%" width="100%">
        <AreaChart data={report.timeline} margin={{ top: 15, right: 10, left: 5, bottom: 5 }}>
          <defs><linearGradient id="reportArea" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#0891b2" stopOpacity={0.4} /><stop offset="100%" stopColor="#0891b2" stopOpacity={0.03} /></linearGradient></defs>
          <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" vertical={false} />
          <XAxis axisLine={false} dataKey="label" tickLine={false} tick={{ fontSize: 11, fontWeight: 700 }} />
          <YAxis axisLine={false} tick={{ fontSize: 11 }} tickFormatter={(value) => formatNumber(value, 0)} tickLine={false} width={64} />
          <Tooltip formatter={(value) => emission(value)} {...TOOLTIP_STYLE} />
          {report.peak && <ReferenceLine label={{ value: "Pico", position: "insideTopRight", fontSize: 10, fontWeight: 900, fill: "#0e7490" }} stroke="#0891b2" strokeDasharray="4 4" x={report.peak.label} />}
          <Area dataKey="value" fill="url(#reportArea)" name="Emisiones" stroke="#0891b2" strokeWidth={3} type="monotone" />
        </AreaChart>
      </ResponsiveContainer>
    </Chart>
    <Chart description="Comparación para detectar el foco ambiental principal." footnote={categoryData.length === 1 ? `${categoryData[0].name} concentra el total de las emisiones categorizadas del período.` : undefined} title="Emisiones por categoría">
      <ResponsiveContainer height="100%" width="100%">
        <BarChart data={categoryData} margin={{ top: 15, right: 10, left: 5, bottom: 5 }}>
          <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" vertical={false} />
          <XAxis angle={-15} axisLine={false} dataKey="name" height={58} interval={0} textAnchor="end" tick={{ fontSize: 11, fontWeight: 700 }} tickLine={false} />
          <YAxis axisLine={false} tick={{ fontSize: 11 }} tickFormatter={(value) => formatNumber(value, 0)} tickLine={false} width={64} />
          <Tooltip cursor={false} content={<CategoryBarTooltip />} />
          <Bar activeBar={{ fill: "#94a3b8" }} dataKey="value" name="Emisiones" radius={[8, 8, 0, 0]}>{categoryData.map((row) => <Cell fill={REPORT_CATEGORY_COLORS[row.name]} fillOpacity={row.name === dominantName ? 1 : 0.55} key={row.name} />)}</Bar>
        </BarChart>
      </ResponsiveContainer>
    </Chart>
  </section>;
}

function CategoryBarTooltip({ active, label, payload }) {
  if (!active || !payload?.length) return null;
  return <div className="rounded-xl border border-[var(--border-default)] bg-white px-3 py-2 shadow-[var(--shadow-card-v1)]"><p className="text-xs font-bold text-[var(--text-secondary)]">{label}</p><p className="mt-1 flex items-baseline gap-1"><span className="text-sm font-black text-teal-700">{formatNumber(payload[0].value)}</span><span className="text-xs font-bold text-slate-500">kg CO2e</span></p></div>;
}

export function ClosingActions({ onOpenFilters }) {
  const items = [
    { icon: FileCheck2, title: "Validar cobertura documental del período", description: "Confirma que cada resultado cuenta con evidencia trazable antes de dar el período por cerrado.", action: <Link className="text-xs font-black text-emerald-800" to="../evidencias">Ir a evidencias →</Link> },
    { icon: AlertTriangle, title: "Revisar fuentes de mayor impacto", description: "Prioriza intervenciones sobre las fuentes que concentran la mayor contribución ambiental del período.", action: <a className="text-xs font-black text-emerald-800" href="#top-fuentes">Ver top 5 →</a> },
    { icon: CalendarDays, title: "Comparar comportamiento con el período anterior", description: "Ajusta el filtro de fechas para contrastar la evolución reciente con el período previo.", action: onOpenFilters ? <button className="text-xs font-black text-emerald-800" onClick={onOpenFilters} type="button">Abrir filtros →</button> : null },
  ];
  return <CZSection className="bg-gradient-to-r from-emerald-50 to-cyan-50">
    <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">Cierre del reporte</p>
    <h2 className="mt-1 text-xl font-black">Qué hacer con este reporte</h2>
    <div className="mt-4 grid gap-3 md:grid-cols-3">
      {items.map((item) => <div className="rounded-[var(--radius-card)] border border-emerald-200/60 bg-white/80 p-4" key={item.title}>
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-emerald-700 shadow-sm"><item.icon aria-hidden="true" size={18} /></span>
        <h3 className="mt-3 text-sm font-black leading-5 text-[var(--text-primary)]">{item.title}</h3>
        <p className="mt-1.5 text-xs leading-5 text-[var(--text-secondary)]">{item.description}</p>
        {item.action && <div className="mt-3">{item.action}</div>}
      </div>)}
    </div>
  </CZSection>;
}

function Chart({ title, description, footnote, children }) { return <article className="rounded-[var(--radius-panel)] border border-[var(--border-default)] bg-white p-[var(--space-5)] shadow-[var(--shadow-card-v1)]"><h3 className="text-lg font-black">{title}</h3><p className="mt-1 text-xs text-[var(--text-muted)]">{description}</p><div className="mt-5 h-80">{children}</div>{footnote && <p className="mt-2 text-[11px] font-semibold leading-4 text-[var(--text-muted)]">{footnote}</p>}</article>; }
function Progress({ value, color }) { return <div className="mt-3 h-2 overflow-hidden rounded-[var(--radius-pill)] bg-slate-100"><div className="h-full rounded-[var(--radius-pill)] transition-[width] duration-[var(--motion-standard)]" style={{ width: `${Math.min(100, Math.max(0, value))}%`, background: color }} /></div>; }
function Heading({ eyebrow, title, description, badge }) { return <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[10px] font-black uppercase tracking-[0.14em] text-emerald-700">{eyebrow}</p><h2 className="mt-1 text-xl font-black">{title}</h2><p className="mt-1 max-w-3xl text-xs leading-5 text-[var(--text-muted)]">{description}</p></div>{badge && <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-black text-sky-800">{badge}</span>}</div>; }
