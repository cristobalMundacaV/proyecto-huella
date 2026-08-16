import { Activity } from "lucide-react";
import { useOutletContext } from "react-router-dom";
import { transportMetrics } from "@/features/operacion/utils/operationSelectors";
import { EmptyState, KpiCard, SectionHeader } from "@/shared/ui";

const label = (value) => String(value ?? "Sin información").replaceAll("_", " ");

function indicatorRows(indicators) {
  const transport = transportMetrics(indicators?.transporte)
    .filter((metric) => metric.value !== null && metric.value !== undefined)
    .map((metric) => ({ name: metric.label, value: metric.value, unit: metric.unit, helper: "Transporte operacional" }));
  const flows = (Array.isArray(indicators?.flujos) ? indicators.flujos : [])
    .filter((metric) => metric?.estrategia_agregacion === "suma" && metric.total !== null && metric.total !== undefined)
    .map((metric) => ({ name: `${label(metric.flujo)} · ${label(metric.concepto)}`, value: metric.total, unit: metric.unidad || undefined, helper: "Flujo ambiental" }));
  return [...transport, ...flows];
}

export default function ObraIndicatorsPage() {
  const { indicators, resourceErrors = {} } = useOutletContext();
  const rows = resourceErrors.indicators ? [] : indicatorRows(indicators);

  return <section className="space-y-4">
    <SectionHeader title="Indicadores" description="Señales disponibles para esta unidad, sin recalcular resultados en la interfaz." />
    {resourceErrors.indicators ? <p className="text-sm text-[var(--text-muted)]">Indicadores no disponibles en este momento.</p> : rows.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {rows.map((item, index) => <KpiCard key={`${item.name}-${index}`} label={item.name} value={item.value} unit={item.unit} helper={item.helper} icon={Activity} />)}
    </div> : <EmptyState title="Sin indicadores disponibles" description="Esta unidad todavía no tiene señales disponibles." />}
  </section>;
}
