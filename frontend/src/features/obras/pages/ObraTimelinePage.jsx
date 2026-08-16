import { useOutletContext } from "react-router-dom";
import { EmptyState, SectionHeader, Timeline, TimelineItem } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";

export default function ObraTimelinePage() {
  const { timeline, resourceErrors = {} } = useOutletContext();
  const rows = Array.isArray(timeline) ? timeline : [];

  return <section className="space-y-4">
    <SectionHeader title="Historial" description="Actividad registrada para esta unidad." />
    {resourceErrors.timeline ? <p className="text-sm text-[var(--text-muted)]">Historial no disponible en este momento.</p> : rows.length ? <Timeline>
      {[...rows].reverse().map((event, index) => <TimelineItem
        key={`${event.tipo}-${event.referencia_id}-${index}`}
        timestamp={formatDateTime(event.fecha)}
        title={event.titulo || String(event.tipo || "Evento").replaceAll("_", " ")}
        description={event.descripcion || String(event.tipo || "").replaceAll("_", " ")}
      />)}
    </Timeline> : <EmptyState title="Sin eventos registrados" description="Aún no hay actividad para mostrar." />}
  </section>;
}
