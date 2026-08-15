import { Activity, AlertTriangle, FileCheck2, Gauge, ListChecks } from "lucide-react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { statusLabel, statusTone } from "../components/WorkStatus";
import { Card, CardContent, KpiCard, SectionHeader, StatusBadge, Timeline, TimelineItem } from "@/shared/ui";

const label = (value) => String(value || "No determinado").replaceAll("_", " ");
const date = (value) => value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(value)) : "Fecha no disponible";
const flattenIndicators = (indicators) => {
  const result = [];
  Object.entries(indicators || {}).forEach(([group, value]) => {
    if (!value || typeof value !== "object" || ["alcance", "corporativo"].includes(group)) return;
    Object.entries(value).forEach(([key, metric]) => {
      if (["number", "string"].includes(typeof metric) && key !== "id") result.push({ name: `${label(group)} · ${label(key)}`, value: metric });
    });
  });
  return result.slice(0, 6);
};

export default function ObraResumenPage() {
  const { obraId } = useParams();
  const { obra, context, indicators, timeline } = useOutletContext();
  const diagnosis = context.diagnostico_obra || {};
  const problems = context.problematicas_abiertas || [];
  const actions = (context.acciones_actuales || []).filter((item) => item.acciones__id);
  const evidence = context.evidencia || {};
  const featured = flattenIndicators(indicators);
  return <div className="space-y-7">
    <section aria-label="Resumen de obra" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard icon={Gauge} label="Indicadores disponibles" value={featured.length || null} helper={!featured.length ? "Sin señales disponibles" : "Señales operacionales compactas"} />
      <KpiCard icon={AlertTriangle} label="Problemas abiertos" value={problems.length || null} status="warning" helper={!problems.length ? "Sin problemas abiertos" : "Dentro del alcance de la obra"} />
      <KpiCard icon={ListChecks} label="Acciones actuales" value={actions.length || null} status="info" helper={!actions.length ? "Sin acciones activas" : "Vinculadas a problemas abiertos"} />
      <KpiCard icon={FileCheck2} label="Evidencias" value={evidence.total || null} helper={evidence.total ? `${evidence.versiones || 0} versiones documentales` : "Sin evidencia vinculada"} />
    </section>

    <div className="grid gap-6 xl:grid-cols-2">
      <Card><CardContent><SectionHeader title="Estado ambiental" description="Estado propio de la obra, separado de las capacidades organizacionales." />
        <div className="flex flex-wrap gap-2"><StatusBadge tone={statusTone(obra.estado_ambiental)}>{statusLabel(obra.estado_ambiental)}</StatusBadge><StatusBadge tone="info">Perfil: {obra.perfil_ambiental || "No determinado"}</StatusBadge><StatusBadge tone="neutral">Diagnóstico: {label(diagnosis.estado)}</StatusBadge></div>
        {obra.estado_ambiental === "cierre_pendiente" && <p className="mt-4 text-sm text-[var(--status-warning)]">El cierre ambiental continúa pendiente; no se presenta como obra cerrada.</p>}
        {obra.estado_ambiental === "cerrada" && <p className="mt-4 text-sm text-[var(--text-secondary)]">Cierre ambiental: {obra.fecha_cierre_ambiental || "Fecha no disponible"}</p>}
      </CardContent></Card>
      <Card><CardContent><SectionHeader title="Cobertura ambiental" description="Aplicabilidad determinada para esta obra." />
        {diagnosis.aplicabilidad?.length ? <ul className="grid gap-2 sm:grid-cols-2">{diagnosis.aplicabilidad.map((item) => <li key={item.clave} className="flex items-center justify-between gap-2 rounded-[var(--radius-md)] bg-[var(--bg-surface-subtle)] p-3 text-sm"><span className="font-bold">{label(item.clave)}</span><StatusBadge tone={item.estado_obra === "aplica" ? "success" : "neutral"}>{label(item.estado_obra)}</StatusBadge></li>)}</ul> : <p className="text-sm text-[var(--text-muted)]">No hay capacidades determinadas para esta obra.</p>}
      </CardContent></Card>
    </div>

    <section><SectionHeader title="Indicadores destacados" description="Máximo seis señales entregadas por el endpoint de esta obra." action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/indicadores`}>Ver indicadores</Link>} />
      {featured.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{featured.map((item) => <KpiCard key={item.name} label={item.name} value={item.value} icon={Activity} />)}</div> : <p className="text-sm text-[var(--text-muted)]">Sin indicadores disponibles para esta obra.</p>}
    </section>

    <div className="grid gap-6 xl:grid-cols-2">
      <Card><CardContent><SectionHeader title="Problemas abiertos" action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/problemas`}>Ver problemas</Link>} />{problems.length ? <ul className="space-y-3">{problems.slice(0, 5).map((problem) => <li key={problem.id} className="border-b border-[var(--border-subtle)] pb-3"><div className="flex justify-between gap-3"><p className="font-bold">{problem.titulo}</p><StatusBadge tone="warning">{label(problem.estado)}</StatusBadge></div><p className="text-sm text-[var(--text-muted)]">{label(problem.categoria)}</p></li>)}</ul> : <p className="text-sm text-[var(--text-muted)]">Sin problemas abiertos.</p>}</CardContent></Card>
      <Card><CardContent><SectionHeader title="Acciones activas" description="Una acción existente no se presenta como resultado comprobado." />{actions.length ? <ul className="space-y-3">{actions.slice(0, 5).map((action) => <li key={action.acciones__id} className="flex justify-between gap-3"><span className="font-bold">{action.acciones__titulo}</span><StatusBadge tone="info">{label(action.acciones__estado)}</StatusBadge></li>)}</ul> : <p className="text-sm text-[var(--text-muted)]">No hay acciones activas vinculadas.</p>}</CardContent></Card>
    </div>

    <div className="grid gap-6 xl:grid-cols-2">
      <Card><CardContent><SectionHeader title="Datos y evidencia" action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/evidencias`}>Ver evidencia</Link>} /><p className="text-3xl font-black">{evidence.total || 0}</p><p className="mt-1 text-sm text-[var(--text-muted)]">evidencias · {evidence.versiones || 0} versiones</p>{!evidence.total && <p className="mt-4 text-sm text-[var(--text-muted)]">Aún no hay respaldo documental vinculado.</p>}</CardContent></Card>
      <Card><CardContent><SectionHeader title="Actividad reciente" action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to={`/obras/${obraId}/timeline`}>Ver timeline</Link>} />{timeline.length ? <Timeline>{timeline.slice(-5).reverse().map((event, index) => <TimelineItem key={`${event.tipo}-${event.referencia_id}-${index}`} timestamp={date(event.fecha)} title={event.titulo} description={label(event.tipo)} />)}</Timeline> : <p className="text-sm text-[var(--text-muted)]">Sin eventos registrados.</p>}</CardContent></Card>
    </div>
  </div>;
}
