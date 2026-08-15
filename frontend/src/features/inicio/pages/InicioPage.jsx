import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Building2, FileCheck2, Plus, Upload } from "lucide-react";
import { Link } from "react-router-dom";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import WorkCard from "@/features/obras/components/WorkCard";
import { getInicioOverview } from "../services/inicioApi";
import { Card, CardContent, EmptyState, ErrorState, KpiCard, LoadingState, PageHeader, SectionHeader, StatusBadge, Timeline, TimelineItem } from "@/shared/ui";

const isOpen = (problem) => !["cerrada", "resuelta"].includes(problem.estado);
const evidencePending = (item) => ["pendiente", "observada", "en_revision"].includes(item.estado_documental || item.estado_validacion || item.estado_revision);
const formatDate = (value) => value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(value)) : "Fecha no disponible";

export default function InicioPage() {
  const { activeOrganizacion, activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ status: "loading", data: null });
  const load = useCallback(() => {
    if (!activeOrganizacionId) return;
    setState({ status: "loading", data: null });
    getInicioOverview(activeOrganizacionId).then((data) => setState({ status: "ready", data })).catch(() => setState({ status: "error", data: null }));
  }, [activeOrganizacionId]);
  useEffect(() => { load(); }, [load]);

  const data = state.data;
  const openProblems = useMemo(() => data?.problems.filter(isOpen) || [], [data]);
  const pendingEvidence = useMemo(() => data?.evidence.filter(evidencePending) || [], [data]);
  const contextByWork = useMemo(() => new Map((data?.workContexts || []).map((context) => [String(context.references?.work), context])), [data]);
  const attentionWorks = data?.works.filter((work) => ["requiere_atencion", "cierre_pendiente"].includes(contextByWork.get(String(work.id || work.obra_id))?.obra?.estado_ambiental)) || [];
  const recentEvents = (data?.workContexts || []).flatMap((context) => context.timeline || []).sort((a, b) => String(b.fecha).localeCompare(String(a.fecha))).slice(0, 5);

  if (state.status === "loading") return <LoadingState label="Preparando el centro de control" />;
  if (state.status === "error") return <ErrorState description="No fue posible reunir el estado ambiental de la organización." onRetry={load} />;

  return <div className="space-y-8">
    <PageHeader eyebrow={activeOrganizacion?.nombre || "Organización activa"} title="Centro de control ambiental" description="Revisa qué obras necesitan atención y entra directamente a su contexto operacional." actions={<Link className="inline-flex items-center gap-2 rounded-[var(--radius-md)] bg-[var(--brand-primary)] px-4 py-2.5 text-sm font-bold text-white" to="/datos/evidencias"><Plus size={18} />Agregar evidencia</Link>} />
    <section aria-label="Resumen operacional" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard icon={Building2} label="Obras activas" value={data.works.length || null} helper={!data.works.length ? "Sin obras registradas" : "En la organización activa"} />
      <KpiCard icon={AlertTriangle} label="Obras que requieren atención" value={attentionWorks.length || null} status="warning" helper={!attentionWorks.length ? "Sin alertas de obra disponibles" : "Incluye cierres pendientes"} />
      <KpiCard icon={AlertTriangle} label="Problemas abiertos" value={openProblems.length || null} status="danger" helper={!openProblems.length ? "Sin problemas abiertos" : "Requieren seguimiento"} />
      <KpiCard icon={FileCheck2} label="Evidencias por revisar" value={pendingEvidence.length || null} status="info" helper={!pendingEvidence.length ? "Sin pendientes documentales" : "Según estado documental"} />
    </section>

    <section><SectionHeader title="Estado de las obras" description="Una lectura breve para decidir dónde entrar." action={<Link className="text-sm font-bold text-[var(--brand-primary)]" to="/obras">Ver todas</Link>} />
      {data.works.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{data.works.slice(0, 6).map((work) => <WorkCard key={work.id || work.codigo_obra} work={work} context={contextByWork.get(String(work.id || work.obra_id))} />)}</div> : <EmptyState title="Aún no hay obras" description="Crea una obra para definir la frontera ambiental y comenzar su seguimiento." primaryAction={<Link className="font-bold text-[var(--brand-primary)]" to="/obras">Crear primera obra</Link>} />}
    </section>

    <div className="grid gap-6 xl:grid-cols-2">
      <Card><CardContent><SectionHeader title="Requiere tu atención" description="Pendientes reales de la organización activa." />
        {openProblems.length || pendingEvidence.length ? <ul className="space-y-3">{openProblems.slice(0, 4).map((problem) => <li key={`p-${problem.id}`} className="flex items-center justify-between gap-3 border-b border-[var(--border-subtle)] pb-3"><div><p className="font-bold">{problem.titulo}</p><p className="text-sm text-[var(--text-muted)]">Problema ambiental · {problem.categoria}</p></div><StatusBadge tone="warning">{problem.estado}</StatusBadge></li>)}{pendingEvidence.slice(0, 3).map((item) => <li key={`e-${item.id}`} className="flex items-center justify-between gap-3"><div><p className="font-bold">{item.nombre || "Evidencia"}</p><p className="text-sm text-[var(--text-muted)]">Dato documental por revisar</p></div><StatusBadge tone="info">En revisión</StatusBadge></li>)}</ul> : <p className="text-sm text-[var(--text-muted)]">No hay elementos pendientes disponibles.</p>}
      </CardContent></Card>
      <Card><CardContent><SectionHeader title="Actividad reciente" description="Últimos eventos registrados en las obras." />
        {recentEvents.length ? <Timeline>{recentEvents.map((event, index) => <TimelineItem key={`${event.tipo}-${event.referencia_id}-${index}`} timestamp={formatDate(event.fecha)} title={event.titulo} description={event.tipo.replaceAll("_", " ")} />)}</Timeline> : <p className="text-sm text-[var(--text-muted)]">Aún no existe actividad reciente.</p>}
      </CardContent></Card>
    </div>
    <section><SectionHeader title="Accesos rápidos" /><div className="flex flex-wrap gap-3"><Link className="inline-flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-2.5 text-sm font-bold" to="/datos/evidencias"><Upload size={17} />Agregar evidencia</Link><Link className="inline-flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-2.5 text-sm font-bold" to="/datos/importaciones">Importar datos</Link><Link className="inline-flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-2.5 text-sm font-bold" to="/obras">Ver obras</Link></div></section>
  </div>;
}
