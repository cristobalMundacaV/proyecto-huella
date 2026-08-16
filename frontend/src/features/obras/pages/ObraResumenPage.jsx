import { Activity, AlertTriangle, FileCheck2, ListChecks } from "lucide-react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import WorkStatus from "../components/WorkStatus";
import { Card, CardContent, KpiCard, SectionHeader, StatusBadge, Timeline, TimelineItem } from "@/shared/ui";
import { transportMetrics } from "@/features/operacion/utils/operationSelectors";

const label = (value) => String(value ?? "Sin información").replaceAll("_", " ");
const date = (value) => value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(value)) : "Fecha no disponible";

export const selectFeaturedIndicators = (indicators) => {
  const result = transportMetrics(indicators?.transporte)
    .filter((metric) => metric.value !== null && metric.value !== undefined)
    .map((metric) => ({ name: metric.label, value: metric.value, unit: metric.unit, helper: "Transporte operacional" }));

  for (const metric of Array.isArray(indicators?.flujos) ? indicators.flujos : []) {
    if (result.length >= 3) break;
    if (metric?.estrategia_agregacion !== "suma" || metric.total === null || metric.total === undefined) continue;
    result.push({ name: `${label(metric.flujo)} · ${label(metric.concepto)}`, value: metric.total, unit: metric.unidad || undefined, helper: "Flujo ambiental" });
  }
  return result.slice(0, 3);
};

export default function ObraResumenPage() {
  const { obraId } = useParams();
  const { obra, context, indicators, timeline, resourceErrors = {} } = useOutletContext();
  const diagnosis = context?.diagnostico_obra || {};
  const problems = Array.isArray(context?.problematicas_abiertas) ? context.problematicas_abiertas : [];
  const actions = (Array.isArray(context?.acciones_actuales) ? context.acciones_actuales : []).filter((item) => item.acciones__id);
  const evidence = context?.evidencia || {};
  const evidenceTotal = evidence.total ?? null;
  const featured = resourceErrors.indicators ? [] : selectFeaturedIndicators(indicators);
  const recentEvents = Array.isArray(timeline) ? timeline.slice(-3).reverse() : [];
  const coverage = Array.isArray(diagnosis.aplicabilidad) ? diagnosis.aplicabilidad : [];
  const stateSummary = problems.length
    ? `Hay ${problems.length} ${problems.length === 1 ? "problema abierto" : "problemas abiertos"}${actions.length ? ` y ${actions.length} ${actions.length === 1 ? "acción en seguimiento" : "acciones en seguimiento"}` : ""}.`
    : "No hay problemas abiertos registrados en la información disponible.";

  return <div className="space-y-7">
    <Card>
      <CardContent className="space-y-4">
        <SectionHeader title="Estado general" description="La señal ambiental principal de esta unidad." />
        <div className="flex flex-wrap items-center gap-3">
          <WorkStatus value={obra.estado_ambiental} />
          {obra.estado_ambiental === "cierre_pendiente" && <span className="text-sm font-semibold text-[var(--status-warning)]">El cierre ambiental sigue pendiente.</span>}
          {obra.estado_ambiental === "cerrada" && <span className="text-sm text-[var(--text-secondary)]">Cierre ambiental: {date(obra.fecha_cierre_ambiental)}</span>}
        </div>
        <p className="text-sm text-[var(--text-secondary)]">{stateSummary}</p>
      </CardContent>
    </Card>

    <section aria-label="Señales de gestión" className="grid gap-3 sm:grid-cols-3">
      <KpiCard
        icon={AlertTriangle}
        label="Problemas abiertos"
        value={problems.length}
        helper={problems.length ? "Requieren seguimiento" : "Sin problemas abiertos"}
        status={problems.length ? "warning" : "success"}
      />
      <KpiCard
        icon={ListChecks}
        label="Acciones en curso"
        value={actions.length}
        helper={actions.length ? "Gestionadas desde Problemas" : "Sin acciones activas"}
        status={actions.length ? "info" : undefined}
      />
      <KpiCard
        icon={FileCheck2}
        label="Evidencias"
        value={evidenceTotal ?? "No disponible"}
        helper={evidenceTotal === null ? "Conteo no disponible" : evidenceTotal === 0 ? "Sin evidencia vinculada" : `${evidence.versiones ?? 0} versiones documentales`}
      />
    </section>

    {problems.length > 0 && <section>
      <SectionHeader title="Requiere atención" description="Problemas abiertos que necesitan seguimiento." action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/problemas`}>Ver todos</Link>} />
      <Card><CardContent>
        <ul className="divide-y divide-[var(--border-subtle)]">
          {problems.slice(0, 3).map((problem) => <li key={problem.id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
            <div className="min-w-0">
              <p className="font-bold text-[var(--text-primary)]">{problem.titulo}</p>
              {problem.categoria && <p className="text-sm text-[var(--text-muted)]">{label(problem.categoria)}</p>}
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge tone="warning">{label(problem.estado)}</StatusBadge>
              <Link className="text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/problemas/${problem.id}`}>Ver problema</Link>
            </div>
          </li>)}
        </ul>
      </CardContent></Card>
    </section>}

    <section>
      <SectionHeader title="Indicadores destacados" description="Señales principales disponibles para esta unidad." action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/indicadores`}>Ver indicadores</Link>} />
      {resourceErrors.indicators ? <p className="text-sm text-[var(--text-muted)]">Indicadores no disponibles en este momento.</p> : featured.length ? <div className="grid gap-3 md:grid-cols-3">
        {featured.map((item) => <KpiCard key={item.name} label={item.name} value={item.value} unit={item.unit} helper={item.helper} icon={Activity} />)}
      </div> : <p className="text-sm text-[var(--text-muted)]">Sin indicadores disponibles para esta unidad.</p>}
    </section>

    <Card><CardContent>
      <SectionHeader title="Cobertura ambiental" description="Contexto secundario de aplicabilidad." />
      {coverage.length ? <div className="flex flex-wrap gap-2">
        {coverage.slice(0, 4).map((item) => <StatusBadge key={item.clave} tone={item.estado_obra === "aplica" ? "success" : "neutral"}>{label(item.clave)} · {label(item.estado_obra)}</StatusBadge>)}
        {coverage.length > 4 && <span className="self-center text-sm text-[var(--text-muted)]">+{coverage.length - 4} más</span>}
      </div> : <p className="text-sm text-[var(--text-muted)]">Sin información de cobertura disponible.</p>}
    </CardContent></Card>

    <section>
      <SectionHeader title="Actividad reciente" action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/timeline`}>Ver historial</Link>} />
      {resourceErrors.timeline ? <p className="text-sm text-[var(--text-muted)]">Historial no disponible en este momento.</p> : recentEvents.length ? <Timeline>
        {recentEvents.map((event, index) => <TimelineItem key={`${event.tipo}-${event.referencia_id}-${index}`} timestamp={date(event.fecha)} title={event.titulo || "Actividad registrada"} description={label(event.tipo)} />)}
      </Timeline> : <p className="text-sm text-[var(--text-muted)]">Sin eventos registrados.</p>}
    </section>
  </div>;
}
