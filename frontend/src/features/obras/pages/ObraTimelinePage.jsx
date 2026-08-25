import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, CalendarDays, Filter, Search } from "lucide-react";
import { Link, useOutletContext } from "react-router-dom";
import { EmptyState, ErrorState, Input, Pagination, SearchInput, SectionHeader, Select, Timeline, TimelineItem } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";

const PAGE_SIZE = 10;
const text = (value) => String(value || "").replaceAll("_", " ");
const dayKey = (value) => value ? new Date(value).toLocaleDateString("es-CL", { dateStyle: "long" }) : "Fecha no disponible";
const actor = (event) => event.actor_nombre || event.usuario_nombre || event.actor || event.usuario || "Sistema Carbono Zero";
const origin = (event) => event.origen || event.fuente || event.modulo || "Plataforma";

export default function ObraTimelinePage() {
  const { obra, timeline, resourceErrors = {} } = useOutletContext();
  const rows = useMemo(() => Array.isArray(timeline) ? timeline : [], [timeline]);
  const [filters, setFilters] = useState({ query: "", type: "", date: "", actor: "", order: "recent" });
  const [page, setPage] = useState(1);
  const workId = obra?.id || obra?.obra_id;
  const types = useMemo(() => [...new Set(rows.map((event) => event.tipo).filter(Boolean))].sort(), [rows]);
  const actors = useMemo(() => [...new Set(rows.map(actor).filter(Boolean))].sort(), [rows]);
  const filtered = useMemo(() => rows.filter((event) => {
    const haystack = `${event.titulo || ""} ${event.descripcion || ""} ${event.tipo || ""} ${actor(event)} ${origin(event)}`.toLowerCase();
    const eventDate = event.fecha ? String(event.fecha).slice(0, 10) : "";
    return (!filters.query || haystack.includes(filters.query.toLowerCase())) && (!filters.type || event.tipo === filters.type) && (!filters.date || eventDate === filters.date) && (!filters.actor || actor(event) === filters.actor);
  }).sort((left, right) => (filters.order === "recent" ? -1 : 1) * String(left.fecha || "").localeCompare(String(right.fecha || ""))), [filters, rows]);
  const visible = useMemo(() => filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [filtered, page]);
  const groups = useMemo(() => visible.reduce((result, event) => { const key = dayKey(event.fecha); const current = result.at(-1); if (current?.date === key) current.events.push(event); else result.push({ date: key, events: [event] }); return result; }, []), [visible]);

  useEffect(() => setPage(1), [filters, rows.length, workId]);

  return <section className="space-y-6">
    <section className="overflow-hidden rounded-[28px] border border-emerald-100 bg-[linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98))] p-6 shadow-[0_16px_40px_rgba(15,23,42,0.06)]"><SectionHeader eyebrow="TRAZABILIDAD AUDITABLE" title="Historial de la obra" description="Bitácora cronológica de cambios, documentos, datos, lecturas, alertas y decisiones registradas para esta obra." /><div className="mt-4 flex flex-wrap gap-2"><span className="rounded-full border border-emerald-200 bg-white px-3 py-1.5 text-xs font-bold text-emerald-900">{rows.length} eventos trazables</span><span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700">Origen y actor visibles cuando están informados</span></div></section>
    {resourceErrors.timeline ? <ErrorState title="Historial no disponible" description="No pudimos recuperar la bitácora auditable de esta obra." /> : rows.length ? <>
      <section className="rounded-[22px] border border-emerald-100 bg-emerald-50/45 p-5 shadow-sm"><div className="mb-4 flex items-center gap-2 text-sm font-black text-emerald-900"><Filter size={17} />Explorar la bitácora</div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5"><SearchInput label="Buscar" placeholder="Evento, descripción u origen" value={filters.query} onChange={(event) => setFilters((current) => ({ ...current, query: event.target.value }))} /><Select label="Tipo de evento" value={filters.type} onChange={(event) => setFilters((current) => ({ ...current, type: event.target.value }))}><option value="">Todos</option>{types.map((type) => <option key={type} value={type}>{text(type)}</option>)}</Select><Input type="date" label="Fecha" value={filters.date} onChange={(event) => setFilters((current) => ({ ...current, date: event.target.value }))} /><Select label="Usuario / origen" value={filters.actor} onChange={(event) => setFilters((current) => ({ ...current, actor: event.target.value }))}><option value="">Todos</option>{actors.map((name) => <option key={name}>{name}</option>)}</Select><Select label="Orden" value={filters.order} onChange={(event) => setFilters((current) => ({ ...current, order: event.target.value }))}><option value="recent">Más recientes</option><option value="oldest">Más antiguos</option></Select></div></section>
      {groups.length ? <div className="space-y-7">{groups.map((group) => <section key={group.date}><div className="mb-3 flex items-center gap-2 text-sm font-black capitalize text-slate-700"><CalendarDays size={16} className="text-emerald-700" />{group.date}</div><Timeline>{group.events.map((event, index) => <div key={`${event.tipo}-${event.referencia_id || event.id || index}`}><TimelineItem timestamp={formatDateTime(event.fecha)} type={event.tipo} label={text(event.tipo || "actividad")} title={event.titulo || text(event.tipo || "Evento registrado")} description={event.descripcion || "Evento registrado en la bitácora de la obra."} /><div className="-mt-2 mb-3 ml-[58px] flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500"><span><b>Actor:</b> {actor(event)}</span><span><b>Origen:</b> {origin(event)}</span>{(event.url || event.detalle_url) && <Link className="inline-flex items-center gap-1 font-bold text-emerald-700" to={event.url || event.detalle_url}>Ver detalle <ArrowRight size={13} /></Link>}</div></div>)}</Timeline></section>)}</div> : <EmptyState icon={Search} title="No encontramos eventos" description="No hay eventos que coincidan con los filtros seleccionados." guidance="Limpia o ajusta los filtros para volver a explorar la bitácora." />}
      <Pagination page={page} totalItems={filtered.length} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="eventos" />
    </> : <EmptyState icon={Activity} title="La bitácora está preparada" description="Todavía no existen eventos operacionales o ambientales registrados más allá de la creación inicial de la obra." guidance="Al agregar evidencias, importar datos, registrar lecturas o gestionar alertas, cada movimiento trazable aparecerá aquí." suggestions={["Evidencia agregada", "Dato importado", "Lectura registrada", "Alerta generada", "Cambio de estado"]} />}
  </section>;
}
