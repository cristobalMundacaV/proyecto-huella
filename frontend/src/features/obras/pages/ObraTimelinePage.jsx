import { useOutletContext } from "react-router-dom";
import { EmptyState, SectionHeader, Timeline, TimelineItem } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";

export default function ObraTimelinePage() {
  const { timeline, resourceErrors = {} } = useOutletContext();
  const rows = Array.isArray(timeline) ? timeline : [];

  return <section className="space-y-6">
    <SectionHeader
      eyebrow="TRAZABILIDAD"
      title="Historial"
      description="Revisa la evolución de la obra y los eventos registrados a lo largo del tiempo."
    />
    {resourceErrors.timeline ? <p className="text-sm text-[var(--text-muted)]">Historial no disponible en este momento.</p> : rows.length ? <Timeline>
      {[...rows].reverse().map((event, index) => <TimelineItem
        key={`${event.tipo}-${event.referencia_id}-${index}`}
        timestamp={formatDateTime(event.fecha)}
        title={event.titulo || String(event.tipo || "Evento").replaceAll("_", " ")}
        description={event.descripcion || String(event.tipo || "").replaceAll("_", " ")}
      />)}
    </Timeline> : <EmptyState
      title="Aún no hay eventos registrados"
      description="Los cambios, registros y decisiones relevantes de esta obra aparecerán aquí conforme exista actividad trazable."
      className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
    />}
  </section>;
}
