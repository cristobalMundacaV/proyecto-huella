import { useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { EmptyState, Pagination, SectionHeader, Timeline, TimelineItem } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";

export default function ObraTimelinePage() {
  const { obra, timeline, resourceErrors = {} } = useOutletContext();
  const rows = useMemo(
    () => (Array.isArray(timeline) ? timeline : []),
    [timeline],
  );
  const [page, setPage] = useState(1);
  const orderedRows = useMemo(() => [...rows].reverse(), [rows]);
  const visibleRows = useMemo(() => orderedRows.slice((page - 1) * 8, page * 8), [orderedRows, page]);
  const workId = obra?.id || obra?.obra_id;

  useEffect(() => { setPage(1); }, [rows.length, workId]);

  return <section className="space-y-6">
    <SectionHeader
      eyebrow="TRAZABILIDAD"
      title="Historial"
      description="Revisa la evolución de la obra y los eventos registrados a lo largo del tiempo."
    />
    {resourceErrors.timeline ? <p className="text-sm text-[var(--text-muted)]">Historial no disponible en este momento.</p> : rows.length ? <><Timeline>
      {visibleRows.map((event, index) => <TimelineItem
        key={`${event.tipo}-${event.referencia_id}-${index}`}
        timestamp={formatDateTime(event.fecha)}
        type={event.tipo}
        label={String(event.tipo || "Actividad").replaceAll("_", " ")}
        title={event.titulo || String(event.tipo || "Evento").replaceAll("_", " ")}
        description={event.descripcion || String(event.tipo || "").replaceAll("_", " ")}
      />)}
    </Timeline><Pagination page={page} totalItems={rows.length} pageSize={8} onChange={setPage} itemLabel="eventos" /></> : <EmptyState
      title="Aún no hay eventos registrados"
      description="Los cambios, registros y decisiones relevantes de esta obra aparecerán aquí conforme exista actividad trazable."
      className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
    />}
  </section>;
}
