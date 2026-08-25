import { useEffect, useMemo, useState } from "react";
import { Activity, Eye, Filter, Search } from "lucide-react";
import { useOutletContext } from "react-router-dom";
import { Drawer, EmptyState, ErrorState, Input, Pagination, SearchInput, SectionHeader, Select, StatusBadge, TableBody, TableCell, TableHead, TableShell } from "@/shared/ui";
import { formatDateTime } from "@/shared/utils/formatters";

const PAGE_SIZE = 12;
const human = (value, fallback = "No informado") => String(value || fallback).replaceAll("_", " ");
const actor = (event) => event.actor_nombre || event.usuario_nombre || event.actor || event.usuario || "Sistema Carbono Zero";
const origin = (event) => event.origen || event.fuente || event.modulo || "Plataforma";
const entity = (event) => event.entidad || event.metadata?.entidad || "obra";
const category = (event) => {
  const type = String(event.tipo || "").toLowerCase();
  if (type.includes("evidencia") || type.includes("documento") || type.includes("validado")) return "Evidencias";
  if (type.includes("import") || type.includes("corregido") || type.includes("rechazado")) return "Importaciones";
  if (type.includes("lectura") || type.includes("actividad")) return "Lecturas";
  if (type.includes("indicador") || type.includes("resultado")) return "Indicadores";
  if (type.includes("cumpl") || type.includes("cierre")) return "Cumplimiento";
  if (type.includes("alerta")) return "Alertas";
  if (type.includes("proble")) return "Problemas";
  if (type.includes("accion")) return "Acciones";
  return "Configuración";
};
const categoryTone = (value) => ({ Evidencias: "success", Importaciones: "info", Lecturas: "info", Indicadores: "success", Cumplimiento: "info", Alertas: "warning", Problemas: "danger", Acciones: "info", Configuración: "neutral" })[value] || "neutral";
const statusTone = (value) => ["rechazado", "error", "vencido"].includes(String(value).toLowerCase()) ? "danger" : ["pendiente", "abierta", "observada"].includes(String(value).toLowerCase()) ? "warning" : "success";
const objectValue = (value) => value && typeof value === "object" && !Array.isArray(value);
const hasValues = (value) => objectValue(value) && Object.keys(value).length > 0;
const printable = (value) => value === null || value === undefined || value === "" ? "Sin información" : typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);

function DetailField({ label, value }) {
  return <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"><dt className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">{label}</dt><dd className="mt-1 text-sm font-semibold text-slate-900">{value}</dd></div>;
}

function Snapshot({ title, value, tone }) {
  return <section className={`rounded-2xl border p-4 ${tone === "before" ? "border-slate-200 bg-slate-50" : "border-emerald-200 bg-emerald-50/70"}`}><p className={`text-xs font-black uppercase tracking-[0.14em] ${tone === "before" ? "text-slate-600" : "text-emerald-800"}`}>{title}</p><div className="mt-3 space-y-2">{Object.entries(value).map(([key, item]) => <div key={key} className="grid gap-1 border-t border-black/5 pt-2 text-sm sm:grid-cols-[140px_1fr]"><b className="capitalize text-slate-600">{human(key)}</b><pre className="whitespace-pre-wrap break-words font-sans text-slate-900">{printable(item)}</pre></div>)}</div></section>;
}

export default function ObraTimelinePage() {
  const { obra, timeline, resourceErrors = {} } = useOutletContext();
  const rows = useMemo(() => Array.isArray(timeline) ? timeline : [], [timeline]);
  const [filters, setFilters] = useState({ query: "", type: "", date: "", source: "", order: "recent" });
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const workId = obra?.id || obra?.obra_id;
  const types = useMemo(() => [...new Set(rows.map((event) => event.tipo).filter(Boolean))].sort(), [rows]);
  const sources = useMemo(() => [...new Set(rows.flatMap((event) => [actor(event), origin(event)]).filter(Boolean))].sort(), [rows]);
  const filtered = useMemo(() => rows.filter((event) => {
    const haystack = `${event.titulo || ""} ${event.descripcion || ""} ${event.tipo || ""} ${actor(event)} ${origin(event)} ${entity(event)}`.toLowerCase();
    const eventDate = event.fecha ? String(event.fecha).slice(0, 10) : "";
    return (!filters.query || haystack.includes(filters.query.toLowerCase())) && (!filters.type || event.tipo === filters.type) && (!filters.date || eventDate === filters.date) && (!filters.source || actor(event) === filters.source || origin(event) === filters.source);
  }).sort((left, right) => (filters.order === "recent" ? -1 : 1) * String(left.fecha || "").localeCompare(String(right.fecha || ""))), [filters, rows]);
  const visible = useMemo(() => filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [filtered, page]);
  useEffect(() => setPage(1), [filters, rows.length, workId]);

  return <section className="space-y-6">
    <section className="overflow-hidden rounded-[28px] border border-emerald-100 bg-[linear-gradient(135deg,rgba(236,253,245,0.96),rgba(255,255,255,0.98))] p-6 shadow-[0_16px_40px_rgba(15,23,42,0.06)]"><SectionHeader eyebrow="TRAZABILIDAD AUDITABLE" title="Historial de la obra" description="Bitácora cronológica de cambios, documentos, datos, lecturas, alertas y decisiones registradas para esta obra." /><div className="mt-4 flex flex-wrap gap-2"><span className="rounded-full border border-emerald-200 bg-white px-3 py-1.5 text-xs font-bold text-emerald-900">{rows.length} eventos trazables</span><span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700">¿Qué ocurrió, cuándo, quién lo hizo y qué cambió?</span></div></section>

    {resourceErrors.timeline ? <ErrorState title="Historial no disponible" description="No pudimos recuperar la bitácora auditable de esta obra." /> : rows.length ? <>
      <section className="rounded-[22px] border border-emerald-100 bg-emerald-50/45 p-5 shadow-sm"><div className="mb-4 flex items-center justify-between gap-3"><div className="flex items-center gap-2 text-sm font-black text-emerald-900"><Filter size={17} />Explorar la bitácora</div><span className="text-xs font-bold text-slate-600">{filtered.length} resultado{filtered.length === 1 ? "" : "s"}</span></div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5"><SearchInput label="Buscar" placeholder="Evento, actor, origen o entidad" value={filters.query} onChange={(event) => setFilters((current) => ({ ...current, query: event.target.value }))} /><Select label="Tipo de evento" value={filters.type} onChange={(event) => setFilters((current) => ({ ...current, type: event.target.value }))}><option value="">Todos</option>{types.map((type) => <option key={type} value={type}>{human(type)}</option>)}</Select><Input type="date" label="Fecha" value={filters.date} onChange={(event) => setFilters((current) => ({ ...current, date: event.target.value }))} /><Select label="Usuario / origen" value={filters.source} onChange={(event) => setFilters((current) => ({ ...current, source: event.target.value }))}><option value="">Todos</option>{sources.map((name) => <option key={name}>{name}</option>)}</Select><Select label="Orden" value={filters.order} onChange={(event) => setFilters((current) => ({ ...current, order: event.target.value }))}><option value="recent">Más recientes</option><option value="oldest">Más antiguos</option></Select></div></section>

      {visible.length ? <><div className="max-h-[680px] overflow-auto rounded-[var(--radius-lg)]"><TableShell><TableHead className="sticky top-0 z-10"><tr><TableCell as="th" align="left">Fecha y hora</TableCell><TableCell as="th" align="left">Evento</TableCell><TableCell as="th">Tipo</TableCell><TableCell as="th" align="left">Actor</TableCell><TableCell as="th">Origen</TableCell><TableCell as="th">Estado</TableCell><TableCell as="th">Acciones</TableCell></tr></TableHead><TableBody columns={7}>{visible.map((event, index) => { const eventCategory = category(event); return <tr key={`${event.tipo}-${event.referencia_id || event.id || index}`}><TableCell align="left" className="whitespace-nowrap font-semibold">{formatDateTime(event.fecha)}</TableCell><TableCell align="left"><b className="block max-w-64 truncate">{event.titulo || human(event.tipo, "Evento registrado")}</b><span className="mt-0.5 block max-w-64 truncate text-xs text-slate-500">{event.descripcion || human(entity(event))}</span></TableCell><TableCell><StatusBadge tone={categoryTone(eventCategory)}>{eventCategory}</StatusBadge></TableCell><TableCell align="left"><span className="block max-w-44 truncate">{actor(event)}</span></TableCell><TableCell><span className="whitespace-nowrap text-xs font-semibold text-slate-600">{origin(event)}</span></TableCell><TableCell><StatusBadge tone={statusTone(event.estado || "registrado")}>{human(event.estado || "registrado")}</StatusBadge></TableCell><TableCell><button type="button" onClick={() => setSelected(event)} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 text-xs font-black text-emerald-800 transition hover:bg-emerald-700 hover:text-white"><Eye size={14} />Ver</button></TableCell></tr>; })}</TableBody></TableShell></div><Pagination page={page} totalItems={filtered.length} pageSize={PAGE_SIZE} onChange={setPage} itemLabel="eventos" /></> : <EmptyState icon={Search} title="No encontramos eventos" description="No hay eventos que coincidan con los filtros seleccionados." guidance="Limpia o ajusta los filtros para volver a explorar la bitácora." />}
    </> : <EmptyState icon={Activity} title="Aún no hay eventos registrados en esta obra" description="El historial mostrará cambios, documentos, datos, alertas y acciones registradas a lo largo de la operación." />}

    <Drawer open={Boolean(selected)} onClose={() => setSelected(null)} title="Detalle del evento">{selected && <div className="space-y-6"><div><StatusBadge tone={categoryTone(category(selected))}>{category(selected)}</StatusBadge><h3 className="mt-3 text-2xl font-black">{selected.titulo || human(selected.tipo, "Evento registrado")}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{selected.descripcion || "Este evento no incluye una descripción adicional."}</p></div><dl className="grid gap-3 sm:grid-cols-2"><DetailField label="Fecha y hora" value={formatDateTime(selected.fecha)} /><DetailField label="Actor" value={actor(selected)} /><DetailField label="Origen" value={origin(selected)} /><DetailField label="Estado" value={human(selected.estado || "registrado")} /><DetailField label="Entidad afectada" value={human(entity(selected))} /><DetailField label="Identificador" value={selected.entidad_id || selected.referencia_id || "No informado"} /></dl>{hasValues(selected.estado_anterior) && hasValues(selected.estado_nuevo) && <section><h3 className="mb-3 text-lg font-black">Cambios registrados</h3><div className="grid gap-3"><Snapshot title="Antes" value={selected.estado_anterior} tone="before" /><Snapshot title="Después" value={selected.estado_nuevo} tone="after" /></div></section>}{hasValues(selected.metadata) && <section><h3 className="mb-3 text-lg font-black">Referencias relacionadas</h3><div className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><pre className="whitespace-pre-wrap break-words text-xs leading-5 text-slate-700">{JSON.stringify(selected.metadata, null, 2)}</pre></div></section>}</div>}</Drawer>
  </section>;
}
