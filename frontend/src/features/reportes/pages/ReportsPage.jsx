import { useMemo, useState } from "react";
import { Download, Filter, RefreshCw } from "lucide-react";
import { Link, useOutletContext } from "react-router-dom";
import { Alert, Button, CZPageHero, EmptyState, Input } from "@/shared/ui";
import { formatDate } from "@/shared/utils/formatters";
import { buildEnvironmentalReport } from "../utils/reportAdapters";
import { CategoryGrid, ClosingActions, CriticalSources, ExecutiveSummary, ReportCharts, ReportKpis, SourceParticipation } from "../components/ReportBlocks";

export default function ReportsPage() {
  const workspace = useOutletContext();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filters, setFilters] = useState({ from: "", to: "" });
  const report = useMemo(() => buildEnvironmentalReport(Array.isArray(workspace.impacts) ? workspace.impacts : [], filters), [filters, workspace.impacts]);
  const workName = workspace.obra?.nombre || "Esta obra";
  const impactsError = workspace.resourceErrors?.impacts;
  const periodLabel = filters.from || filters.to
    ? `${filters.from ? formatDate(filters.from) : "Inicio"} – ${filters.to ? formatDate(filters.to) : "Hoy"}`
    : "Todo el período";

  const refresh = () => window.location.reload();
  const exportReport = () => window.print();

  return <main className="space-y-4 pb-4 print:bg-white">
    <CZPageHero>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-200">Inteligencia ambiental</p>
          <h1 className="mt-2 text-3xl font-black leading-tight sm:text-4xl">Reportes</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-emerald-50/85">Analiza la evolución ambiental de la obra, detecta períodos críticos y convierte los resultados en decisiones de mejora.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <HeroPill>{workName}</HeroPill>
            <HeroPill>{periodLabel}</HeroPill>
            <HeroPill>{report.records} resultados trazables</HeroPill>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 print:hidden">
          <Button leftIcon={Filter} onClick={() => setFiltersOpen((value) => !value)} variant="secondary">Filtros</Button>
          <Button leftIcon={RefreshCw} onClick={refresh} variant="secondary">Actualizar</Button>
          <Button leftIcon={Download} onClick={exportReport}>Exportar reporte</Button>
        </div>
      </div>
    </CZPageHero>

    {filtersOpen && <section className="grid gap-4 rounded-[var(--radius-card)] border border-emerald-100 bg-emerald-50/50 p-5 sm:grid-cols-[1fr_1fr_auto] sm:items-end print:hidden">
      <Input label="Desde" onChange={(event) => setFilters((current) => ({ ...current, from: event.target.value }))} type="date" value={filters.from} />
      <Input label="Hasta" onChange={(event) => setFilters((current) => ({ ...current, to: event.target.value }))} type="date" value={filters.to} />
      <Button onClick={() => setFilters({ from: "", to: "" })} variant="secondary">Limpiar filtros</Button>
    </section>}

    {impactsError ? <Alert title="No fue posible cargar los resultados ambientales" tone="danger">El reporte no reemplaza el error por cifras vacías. Actualiza la vista para volver a intentarlo.</Alert> : <>
      <ExecutiveSummary report={report} workName={workName} />
      <ReportKpis report={report} />
      {!report.records ? <EmptyState description="No existen resultados ambientales gobernados para construir este reporte. La ausencia de información no se presenta como una huella igual a cero." guidance="Agrega evidencia o registra información operacional para habilitar cálculos trazables." primaryAction={<Link className="inline-flex min-h-11 items-center rounded-xl bg-emerald-700 px-4 text-sm font-bold text-white" to="../evidencias">Agregar evidencia</Link>} secondaryAction={<Link className="inline-flex min-h-11 items-center rounded-xl px-4 text-sm font-bold text-emerald-900" to="../operacion/energia">Registrar información</Link>} suggestions={["0 resultados trazables", "Sin fuente prioritaria", "Sin comparación temporal"]} title="Sin lectura disponible en el período" /> : <>
        <CategoryGrid categories={report.categories} total={report.total} />
        <SourceParticipation report={report} />
        <CriticalSources report={report} />
        <ReportCharts report={report} />
      </>}
      <ClosingActions onOpenFilters={() => setFiltersOpen(true)} />
    </>}
  </main>;
}

function HeroPill({ children }) { return <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-white backdrop-blur">{children}</span>; }
