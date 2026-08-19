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

  return <section className="space-y-6">
    <SectionHeader
      eyebrow="LECTURA AMBIENTAL"
      title="Indicadores"
      description="Consulta las señales ambientales y operacionales disponibles para esta obra."
    />
    {resourceErrors.indicators ? <p className="text-sm text-[var(--text-muted)]">Indicadores no disponibles en este momento.</p> : rows.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {rows.map((item, index) => <KpiCard key={`${item.name}-${index}`} label={item.name} value={item.value} unit={item.unit} helper={item.helper} icon={Activity} />)}
    </div> : <EmptyState
      icon={Activity}
      title="Aún no hay indicadores disponibles"
      description="Los indicadores aparecerán cuando existan datos suficientes y resultados gobernados para esta obra."
      className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
    />}
  </section>;
}
