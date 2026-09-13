import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, CalendarDays, CheckCircle2, Download, FileBarChart2, Search, TriangleAlert } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState, ErrorState } from "@/shared/ui";
import ContextContentSkeleton from "@/shared/components/ContextContentSkeleton";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { obraReportExcelUrl, obraReportPdfUrl } from "@/features/obras/services/obraDashboardApi";
import { getReportsCenterOverview } from "../services/reportesApi";

const date = (value) => value ? new Intl.DateTimeFormat("es-CL", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(`${value}T12:00:00`)) : "Sin fecha";
const idOf = (row) => row.work.id || row.work.obra_id;
const ready = (row) => Boolean(row.dashboard?.readiness?.listo_para_reporte);
const stateMeta = (row) => {
  if (row.unavailable) return { label: "No disponible", classes: "border-slate-200 bg-slate-100 text-slate-700" };
  if (ready(row)) return { label: "Listo para reportar", classes: "border-emerald-200 bg-emerald-50 text-emerald-800" };
  return { label: row.dashboard?.estado_ejecutivo?.label || "Preparación pendiente", classes: "border-amber-200 bg-amber-50 text-amber-800" };
};

export default function ReportsCenterPage() {
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ status: "loading", rows: [] });
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("todos");
  const load = useCallback(() => {
    if (!activeOrganizacionId) return;
    setState({ status: "loading", rows: [] });
    getReportsCenterOverview(activeOrganizacionId)
      .then((rows) => setState({ status: "ready", rows }))
      .catch(() => setState({ status: "error", rows: [] }));
  }, [activeOrganizacionId]);
  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => state.rows.filter((row) => {
    const matches = String(row.work.nombre || row.work.codigo_obra || "").toLowerCase().includes(query.toLowerCase());
    return matches && (filter === "todos" || (filter === "listos" ? ready(row) : !ready(row)));
  }), [filter, query, state.rows]);
  const readyCount = state.rows.filter(ready).length;
  const pendingCount = state.rows.length - readyCount;

  if (state.status === "loading") return <ContextContentSkeleton charts={0} kpis={3} />;
  if (state.status === "error") return <ErrorState title="No pudimos cargar el centro de reportes" description="La información no fue reemplazada por estados estimados." onRetry={load} />;

  return <main className="space-y-6">
    <section className="overflow-hidden rounded-[30px] border border-emerald-800/20 bg-[linear-gradient(135deg,#064e3b_0%,#066657_58%,#0f766e_100%)] p-6 text-white shadow-[0_20px_50px_rgba(6,78,59,0.18)] sm:p-8">
      <div className="grid gap-7 lg:grid-cols-[1fr_auto] lg:items-end"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-200">Salida ejecutiva</p><h1 className="mt-2 text-3xl font-black sm:text-4xl">Centro de reportes</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-emerald-50/85">Controla qué períodos están listos y genera informes consistentes para cada obra de {activeOrganizacion?.nombre || "tu organización"}.</p></div><div className="grid grid-cols-2 gap-3"><HeroMetric label="Listos" value={readyCount} /><HeroMetric label="Pendientes" value={pendingCount} /></div></div>
    </section>

    {!state.rows.length ? <EmptyState icon={FileBarChart2} title="Todavía no hay obras para reportar" description="Crea una obra y registra información ambiental para habilitar su primer informe." primaryAction={<Link className="font-bold text-emerald-700" to="/obras">Ir a Obras</Link>} /> : <>
      <section className="grid gap-3 sm:grid-cols-3"><Summary icon={FileBarChart2} label="Informes por obra" value={state.rows.length} tone="emerald" /><Summary icon={CheckCircle2} label="Períodos listos" value={readyCount} tone="teal" /><Summary icon={TriangleAlert} label="Requieren preparación" value={pendingCount} tone="amber" /></section>
      <section className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-[0_12px_35px_rgba(15,23,42,0.05)]">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between"><div><h2 className="text-xl font-black text-slate-950">Informes ambientales</h2><p className="mt-1 text-sm text-slate-600">Readiness real del período móvil de tres meses.</p></div><div className="flex flex-col gap-2 sm:flex-row"><label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3"><Search size={16} className="text-slate-500" /><span className="sr-only">Buscar obra</span><input className="min-h-10 bg-transparent text-sm outline-none" placeholder="Buscar obra" value={query} onChange={(event) => setQuery(event.target.value)} /></label><select className="min-h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="todos">Todos los estados</option><option value="listos">Listos</option><option value="pendientes">Pendientes</option></select></div></div>
        <div className="mt-5 space-y-3">{visible.map((row) => <ReportRow key={idOf(row)} row={row} organizationId={activeOrganizacionId} />)}{!visible.length && <p className="rounded-2xl bg-slate-50 p-6 text-center text-sm text-slate-600">No hay informes que coincidan con la búsqueda.</p>}</div>
      </section>
      <section className="rounded-[24px] border border-cyan-100 bg-cyan-50/55 p-5"><h2 className="font-black text-slate-950">Reportes recientes</h2><p className="mt-1 text-sm text-slate-600">Las salidas se generan bajo demanda desde el mismo motor del dashboard. La fecha de generación queda determinada al descargar el PDF o Excel.</p></section>
    </>}
  </main>;
}

function HeroMetric({ label, value }) { return <div className="min-w-28 rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur"><p className="text-xs font-bold text-emerald-100">{label}</p><p className="mt-1 text-3xl font-black">{value}</p></div>; }
function Summary({ icon: Icon, label, value, tone }) { const colors = { emerald: "border-emerald-200 bg-emerald-50 text-emerald-800", teal: "border-teal-200 bg-teal-50 text-teal-800", amber: "border-amber-200 bg-amber-50 text-amber-800" }; return <article className={`rounded-2xl border p-4 ${colors[tone]}`}><Icon size={18} /><p className="mt-3 text-xs font-black uppercase tracking-wider opacity-75">{label}</p><p className="mt-1 text-2xl font-black">{value}</p></article>; }
function ReportRow({ row, organizationId }) {
  const id = idOf(row); const dashboard = row.dashboard; const meta = stateMeta(row); const period = dashboard?.period; const coverage = dashboard?.readiness?.cobertura_registros_pct;
  return <article className="grid gap-4 rounded-2xl border border-slate-200 bg-slate-50/60 p-4 lg:grid-cols-[minmax(190px,1.25fr)_minmax(170px,.8fr)_minmax(140px,.65fr)_auto] lg:items-center">
    <div><span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-black ${meta.classes}`}>{meta.label}</span><h3 className="mt-2 text-base font-black text-slate-950">{row.work.nombre || row.work.codigo_obra || "Obra sin nombre"}</h3><p className="mt-1 text-xs text-slate-500">{row.work.codigo_obra || "Informe ambiental de obra"}</p></div>
    <div><p className="flex items-center gap-1.5 text-xs font-black uppercase tracking-wider text-slate-500"><CalendarDays size={14} /> Período</p><p className="mt-2 text-sm font-bold text-slate-800">{period ? `${date(period.start)} — ${date(period.end)}` : "No disponible"}</p></div>
    <div><p className="text-xs font-black uppercase tracking-wider text-slate-500">Readiness</p><p className="mt-2 text-lg font-black text-slate-950">{coverage == null ? "Sin cobertura" : `${coverage}%`}</p><p className="text-xs text-slate-500">{dashboard?.readiness?.pendientes?.length || 0} pendientes</p></div>
    <div className="flex flex-wrap gap-2 lg:justify-end"><Link className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-3 py-2 text-xs font-black text-white" to={`/obras/${id}/reportes`}>Abrir <ArrowRight size={13} /></Link><a aria-label={`Descargar PDF de ${row.work.nombre || "obra"}`} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold" href={obraReportPdfUrl(organizationId, id, { relative_months: 3 })}><Download size={13} /> PDF</a><a aria-label={`Descargar Excel de ${row.work.nombre || "obra"}`} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold" href={obraReportExcelUrl(organizationId, id, { relative_months: 3 })}><Download size={13} /> Excel</a></div>
  </article>;
}
