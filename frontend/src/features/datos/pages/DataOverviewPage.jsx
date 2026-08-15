import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, FileText, UploadCloud } from "lucide-react";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Card, CardContent, ErrorState, LoadingState, PageHeader, StatusBadge } from "@/shared/ui";
import { listEvidence, listImports } from "../services/dataApi";

export default function DataOverviewPage() {
  const { activeOrganizacionId } = useOrganizacionActiva();
  const [state, setState] = useState({ loading: true, evidence: [], imports: [], errors: [] });
  useEffect(() => { let current = true; setState({ loading: true, evidence: [], imports: [], errors: [] }); Promise.allSettled([listEvidence(activeOrganizacionId), listImports(activeOrganizacionId)]).then(([evidence, imports]) => { if (!current) return; setState({ loading: false, evidence: evidence.status === "fulfilled" ? evidence.value : [], imports: imports.status === "fulfilled" ? imports.value : [], errors: [evidence, imports].filter((item) => item.status === "rejected") }); }); return () => { current = false; }; }, [activeOrganizacionId]);
  if (state.loading) return <LoadingState label="Cargando centro de datos" />;
  const pending = state.imports.filter((item) => !["confirmada", "completada"].includes(item.estado));
  return <main className="space-y-6"><PageHeader eyebrow="Datos" title="Centro de datos" description="Revisa qué información está entrando y qué requiere atención." />
    {state.errors.length === 2 && <ErrorState description="No fue posible cargar evidencias ni importaciones." />}
    {state.errors.length === 1 && <p className="rounded-xl bg-[var(--warning-bg)] p-3 text-sm">Una fuente no está disponible; el resto de la información se mantiene visible.</p>}
    <div className="grid gap-4 md:grid-cols-2"><Card><CardContent><FileText className="text-[var(--brand-primary)]" /><h2 className="mt-3 text-xl font-bold">Evidencias</h2><p className="mt-1 text-sm text-[var(--text-muted)]">{state.evidence.length} documentos registrados.</p><Link className="mt-4 inline-flex items-center gap-2 font-bold text-[var(--brand-primary)]" to="/datos/evidencias">Explorar evidencias <ArrowRight size={16} /></Link></CardContent></Card><Card><CardContent><UploadCloud className="text-[var(--brand-primary)]" /><h2 className="mt-3 text-xl font-bold">Importaciones</h2><p className="mt-1 text-sm text-[var(--text-muted)]">{pending.length} procesos requieren atención.</p><Link className="mt-4 inline-flex items-center gap-2 font-bold text-[var(--brand-primary)]" to="/datos/importaciones">Gestionar importaciones <ArrowRight size={16} /></Link></CardContent></Card></div>
    {!!pending.length && <Card><CardContent><h2 className="font-bold">Requieren tu revisión</h2><div className="mt-3 space-y-2">{pending.slice(0, 5).map((item) => <Link key={item.id} className="flex items-center justify-between rounded-xl border p-3" to={`/datos/importaciones/${item.id}`}><span>{item.version_evidencia_detalle?.nombre_original || item.fuente_nombre || "Importación"}</span><StatusBadge label={item.estado.replaceAll("_", " ")} /></Link>)}</div></CardContent></Card>}
  </main>;
}
