import { useMemo, useState } from "react";
import { Download, Filter, RefreshCw, Sparkles } from "lucide-react";
import { useOutletContext } from "react-router-dom";
import { Alert, Button, EmptyState, Input } from "@/shared/ui";
import { buildEnvironmentalReport } from "../utils/reportAdapters";
import { CategoryGrid, CriticalSources, ExecutiveSummary, ReportCharts, ReportKpis, SourceParticipation } from "../components/ReportBlocks";

export default function ReportsPage() {
  const workspace = useOutletContext();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filters, setFilters] = useState({ from: "", to: "" });
  const report = useMemo(() => buildEnvironmentalReport(Array.isArray(workspace.impacts) ? workspace.impacts : [], filters), [filters, workspace.impacts]);
  const workName = workspace.obra?.nombre || "Esta obra";
  const impactsError = workspace.resourceErrors?.impacts;

  const refresh = () => window.location.reload();
  const exportReport = () => window.print();

  return <main className="space-y-6 print:bg-white">
    <section className="relative overflow-hidden rounded-[30px] bg-gradient-to-br from-emerald-950 via-emerald-800 to-teal-700 p-7 text-white shadow-[0_22px_60px_rgba(6,78,59,0.24)] sm:p-8">
      <div aria-hidden="true" className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-cyan-300/20 blur-3xl" />
      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between"><div><p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-200">Inteligencia ambiental</p><h1 className="mt-2 text-3xl font-black sm:text-4xl">Reportes</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-emerald-50/90 sm:text-base">Analiza la evolución ambiental de la obra, detecta períodos críticos y convierte los resultados en decisiones de mejora.</p><div className="mt-5 flex flex-wrap gap-2"><span className="rounded-full border border-white/20 bg-white/10 px-3 py-2 text-xs font-bold">{workName}</span><span className="rounded-full border border-white/20 bg-white/10 px-3 py-2 text-xs font-bold">{report.records} resultados trazables</span></div></div><div className="flex flex-wrap gap-2 print:hidden"><Button variant="secondary" leftIcon={Filter} onClick={() => setFiltersOpen((value) => !value)}>Filtros</Button><Button variant="secondary" leftIcon={RefreshCw} onClick={refresh}>Actualizar</Button><Button leftIcon={Download} onClick={exportReport}>Exportar reporte</Button></div></div>
    </section>

    {filtersOpen && <section className="grid gap-4 rounded-[22px] border border-emerald-100 bg-emerald-50/50 p-5 sm:grid-cols-[1fr_1fr_auto] sm:items-end print:hidden"><Input type="date" label="Desde" value={filters.from} onChange={(event) => setFilters((current) => ({ ...current, from: event.target.value }))} /><Input type="date" label="Hasta" value={filters.to} onChange={(event) => setFilters((current) => ({ ...current, to: event.target.value }))} /><Button variant="secondary" onClick={() => setFilters({ from: "", to: "" })}>Limpiar filtros</Button></section>}

    {impactsError ? <Alert tone="danger" title="No fue posible cargar los resultados ambientales">El reporte no reemplaza el error por cifras vacías. Actualiza la vista para volver a intentarlo.</Alert> : <>
      <ExecutiveSummary report={report} workName={workName} />
      <ReportKpis report={report} />
      {!report.records ? <EmptyState title="Sin emisiones disponibles en el período" description="Ajusta los filtros o incorpora resultados ambientales gobernados. La ausencia de información no se presenta como una huella igual a cero." /> : <>
        <CategoryGrid categories={report.categories} total={report.total} />
        <SourceParticipation report={report} />
        <CriticalSources report={report} />
        <ReportCharts report={report} />
      </>}
      <section className="rounded-[24px] border border-emerald-200 bg-gradient-to-r from-emerald-50 to-cyan-50 p-6"><div className="flex items-start gap-4"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-emerald-700 shadow-sm"><Sparkles aria-hidden="true" size={21} /></span><div><p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">Próxima lectura ejecutiva</p><h2 className="mt-1 text-xl font-black">Trazabilidad, calidad y decisiones verificables</h2><p className="mt-2 max-w-4xl text-sm leading-6 text-[var(--text-secondary)]">La estructura queda preparada para incorporar calidad del dato, problemáticas prioritarias y seguimiento de acciones sin alterar la lectura consolidada ni inventar conclusiones.</p></div></div></section>
    </>}
  </main>;
}
