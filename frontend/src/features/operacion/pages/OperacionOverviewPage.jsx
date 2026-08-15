import { Droplets, Fuel, LandPlot, Package, Trash2, Truck, Volume2, Zap } from "lucide-react";
import { useOutletContext } from "react-router-dom";
import OperationDomainCard from "../components/OperationDomainCard";
import { additiveMetrics, applicability, domainRecords, domainState, transportMetrics } from "../utils/operationSelectors";
import { formatDate } from "@/shared/utils/formatters";

const domains = [
  ["energia", "Energía", Zap], ["agua", "Agua", Droplets], ["combustibles", "Combustibles", Fuel],
  ["transporte", "Transporte", Truck], ["materiales", "Materiales", Package], ["residuos", "Residuos", Trash2],
  ["ruido", "Ruido", Volume2], ["hidrica-suelo", "Hídrica y suelo", LandPlot],
];

export default function OperacionOverviewPage() {
  const { context, indicators, operation } = useOutletContext();
  return <section><h2 className="text-2xl font-bold">Resumen operacional</h2><p className="mt-1 text-sm text-[var(--text-muted)]">Selecciona un dominio para revisar sus datos y trazabilidad.</p>
    <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">{domains.map(([key, title, icon]) => {
      if (key === "transporte") {
        const records = operation.journeys || [];
        const latest = records.toSorted((left, right) => String(right.fecha_salida).localeCompare(String(left.fecha_salida)))[0];
        return <OperationDomainCard key={key} icon={icon} title={title} to="transporte" state={domainState({ applicabilityState: applicability(context, "transporte"), records })} metric={transportMetrics(operation.transport)[0]} detail={latest ? `Último viaje: ${formatDate(latest.fecha_salida)}` : undefined} />;
      }
      if (key === "materiales") {
        const records = operation.materialEvents || [];
        const latest = records.toSorted((left, right) => String(right.fecha_hora).localeCompare(String(left.fecha_hora)))[0];
        return <OperationDomainCard key={key} icon={icon} title={title} to="materiales" state={domainState({ applicabilityState: applicability(context, "materiales"), records })} metric={records.length ? { value: records.length, unit: "eventos" } : null} detail={latest ? `Último evento: ${formatDate(latest.fecha_hora)}` : undefined} />;
      }
      const records = domainRecords(operation.records, key);
      const metrics = additiveMetrics(indicators, key);
      const ambiguous = metrics.some((metric) => metric.registros_ambiguos > 0);
      const latest = records.toSorted((left, right) => String(right.periodo_inicio).localeCompare(String(left.periodo_inicio)))[0];
      return <OperationDomainCard key={key} icon={icon} title={title} to={key} state={domainState({ applicabilityState: applicability(context, key === "hidrica-suelo" ? "gestion_hidrica_suelo" : key), records, ambiguous })} metric={metrics[0] && metrics[0].total !== null ? { value: metrics[0].total, unit: metrics[0].unidad } : null} detail={latest ? `Último período: ${formatDate(latest.periodo_inicio)}` : undefined} />;
    })}</div>
  </section>;
}
